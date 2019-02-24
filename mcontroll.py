import gc, network, json
import uasyncio as asyncio
from machine import I2C, Pin, PWM, freq, ADC
from wificonnect import WiFiControl
from i2c_ds3231 import DS3231
from term_adc import READ_TERM
from time import mktime
import math
from webapp import app, read_write_config, bool_to_str, setting_update, read_write_root
gc.collect()                                                            # Очищаем RAM

# Базовый класс
class Main(WiFiControl):
    def __init__(self):
        super().__init__()
        self.wifi_led = Pin(2, Pin.OUT, value = 1)              # Pin2, светодиод на плате контроллера
        self.i2c = I2C(scl=Pin(14), sda=Pin(12), freq=400000)   # Pin12 и 14 i2c шина
        self.heat = PWM(Pin(5), freq=1000, duty=0)              #Pin5, управление нагревом бойлера
        self.default_on = Pin(14, Pin.IN)                       # Pin14, кнопка для сброса настроек в дефолт
        self.adc = ADC(0)                                       # Pin0 Аналоговый вход
        # Дефолтные настройки, если файла config.txt не обнаружено в системе
        self.default = {}
        self.default['DEBUG'] = True             # Разрешаем отладочный сообщения
        self.default['MODE_WiFi'] = 'AP'         # Включаем точку доступа
        self.default['ssid'] = 'HEAT_CONTROL'    # Устанавливаем имя точки доступа
        self.default['wf_pass'] = 'roottoor'     # Пароль для точки доступа
        self.default['timezone'] = 3             # Временная зона
        self.default['DST'] = True               # Разрешаем переход с летнего на зимнее время
        self.default['T_WATER'] = 30.0           # Температура в бойлере
        self.default['TIME_ON'] = (0, 0, 0, 5, 0, 0, 0, 0)  # Время включения нагрева бойлера 05:00
        self.default['TIME_OFF'] = (0, 0, 0, 6, 0, 0, 0, 0) # Время выключения нагрева бойлера 06:00
        self.default['WORK_ALL'] = False         # Постоянный нагрев бойлера выключен
        self.default['WORK_TABLE'] = False       # Работа по расписнию
        self.default['ONE-TIME'] = False         # Одноразовое включение
        self.default['BALANCE_R'] = 98500.0      # Балансный резистор в схеме (ом)
        self.default['THERMISTOR_R'] = 100000.0  # Номинал терморезистора (ом)
        self.default['A'] = 3.354016e-03         # Коеффициент А терморезистора
        self.default['B'] = 2.460382e-04         # Коеффициент B терморезистора
        self.default['C'] = 3.405377e-06         # Коеффициент C терморезистора
        self.default['D'] = 1.034240e-07         # Коеффициент D терморезистора
        self.default['K'] = 5.29                 # Погрешность терморезистора %
        # Дефолтный хещ логина и пароля для web admin (root:root)
        self.default_web = str(b'0242c0436daa4c241ca8a793764b7dfb50c223121bb844cf49be670a3af4dd18')
        self.config['DEBUG'] = True                     # Разрешаем отладочный сообщения
        self.config['WEB_Port'] = 80                    # Порт на котором работает web приложение
        self.config['ADR_RTC'] = 0x68                   # Адрес RTC DS3231
        self.config['WIFI_AP'] = ('192.168.4.1', '255.255.255.0', '192.168.4.1', '208.67.222.222')
        self.config['IP'] = None                        # Дефолтный IP адрес
        self.config['no_wifi'] = True                   # Интернет отключен(значение True)
        self.config['Uptime'] = 0                       # Время работы контроллера
        self.config['RTC_TIME'] = (0, 1, 1, 0, 0, 0, 0, 0) # Дефолтное время
        self.config['NTP_UPDATE'] = True                # Разрешаем обновление по NTP
        self.config['MemFree'] = None
        self.config['MemAvailab'] = None
        self.config['FREQ'] = None
        self.config['TEMP'] = 0
        self.config['PWM'] = 0
        self.config['POWER'] = (0, 1000, 800, 650, 500, 300, 200)
        self.config['SET_T'] = (0.00, 15.00, 10.00, 5.00, 2.00, 1.00)
        self.config['T_ON'] = 0
        self.config['T_OFF'] = 0
        self.config['NOW'] = 0
        self.config['DPRINT'] = self.dprint

        # Eсли нет файла config.txt или нажата кнопка сброса в дефолт, создаем файл config.txt
        if self.exists('config.txt') == False or not self.default_on(): 
            self.dprint('Create new config.txt file')
            read_write_config(cfg=self.default)
        # Eсли нет файла root.txt или нажата кнопка сброса в дефолт, создаем его
        if self.exists('root.txt') == False or not self.default_on(): 
            self.dprint('Create new root.txt file')
            read_write_root(passwd=self.default_web)
        # Читаем настройки из файла config.txt
        conf = read_write_config()
        # Обновляем настройки полученные из файла config.txt
        self.config['DEBUG'] = conf['DEBUG']
        self.config['MODE_WiFi'] = conf['MODE_WiFi']
        self.config['ssid'] = conf['ssid']
        self.config['wf_pass'] = conf['wf_pass']
        self.config['TIMEZONE'] = conf['timezone']
        self.config['DST'] = conf['DST']
        self.config['T_WATER'] = conf['T_WATER']
        self.config['TIME_ON'] = conf['TIME_ON']
        self.config['TIME_OFF'] = conf['TIME_OFF']
        self.config['WORK_ALL'] = conf['WORK_ALL']
        self.config['WORK_TABLE'] = conf['WORK_TABLE']
        self.config['ONE-TIME'] = conf['ONE-TIME']
        self.config['BALANCE_R'] = conf['BALANCE_R']
        self.config['THERMISTOR_R'] = conf['THERMISTOR_R']
        self.config['A'] = conf['A']
        self.config['B'] = conf['B']
        self.config['C'] = conf['C']
        self.config['D'] = conf['D']
        self.config['K'] = conf['K']
        gc.collect()                                                    # Очищаем RAM
        # Начальные настройки сети AP или ST
        if self.config['MODE_WiFi'] == 'AP':
            self._ap_if = network.WLAN(network.AP_IF)
            self.config['WIFI'] = self._ap_if
        elif self.config['MODE_WiFi'] == 'ST':
            self._sta_if = network.WLAN(network.STA_IF)
            self.config['WIFI'] = self._sta_if
        # Настройка для работы с RTC
        self.config['RTC'] = DS3231(self.i2c, 
                       self.config['ADR_RTC'], self.config['TIMEZONE'])
        self.rtc = self.config['RTC']
        self.temp = READ_TERM(self.adc, self.config['BALANCE_R'], 
                       self.config['THERMISTOR_R'], self.config['A'], 
                       self.config['B'], self.config['C'], d=self.config['D'], 
                       k=self.config['K'])
        
        loop = asyncio.get_event_loop()
        loop.create_task(self._heartbeat())                             # Индикация подключения WiFi
        loop.create_task(self._dataupdate())                            # Обновление информации и часы
        loop.create_task(self._start_web_app())                         # Включаем WEB приложение
        
    
    # Запуск WEB приложения
    async def _start_web_app(self):
        """Run/Work Web App"""
        while True:
            gc.collect()                                                    # Очищаем RAM
            await asyncio.sleep(5)
            if not self.config['no_wifi'] or self.config['MODE_WiFi'] == 'AP':
                self.ip = self.config['WIFI'].ifconfig()[0]
                self.dprint('WebAPP: Running...')
                app.run(debug=self.config['DEBUG'], host =self.ip, port=self.config['WEB_Port'])


    # Управление нагревом, простое сравнивание температуры
    def heat_work(self):
        t = self.config['T_WATER'] - self.config['TEMP']
        if t <=  self.config['SET_T'][0]:
            self.config['PWM'] = self.config['POWER'][0]
        elif t >= self.config['SET_T'][1]:
            self.config['PWM'] = self.config['POWER'][1]
        elif t >= self.config['SET_T'][2]:
            self.config['PWM'] = self.config['POWER'][2]
        elif t >= self.config['SET_T'][3]:
            self.config['PWM'] = self.config['POWER'][3]
        elif t >= self.config['SET_T'][4]:
            self.config['PWM'] = self.config['POWER'][4]
        elif t >= self.config['SET_T'][5]:
            self.config['PWM'] = self.config['POWER'][5]
        elif t < self.config['SET_T'][5]:
            self.config['PWM'] = self.config['POWER'][6]
        t = 0
        return self.config['PWM']

    # Управление временем нагрева воды в бойлере
    def time_on_off(self):
        rtc = self.config['RTC_TIME']
        ton = self.config['TIME_ON']
        toff = self.config['TIME_OFF']
        self.config['NOW'] = mktime(rtc)
        self.config['T_ON'] = mktime((rtc[0], rtc[1], rtc[2], ton[3], ton[4], 0, 0, 0))
        dt = rtc[2] + 1 if ton[3] > toff[3] else rtc[2] # Если вкл > выкл, значит выкл на след день
        self.config['T_OFF'] = mktime((rtc[0], rtc[1], dt, toff[3], toff[4], 0, 0, 0))
        if self.config['T_ON'] <= self.config['NOW'] and self.config['NOW'] <= self.config['T_OFF']:
            return True
        elif self.config['T_ON'] < self.config['NOW'] and self.config['NOW'] > self.config['T_OFF']: 
            return False


    async def _dataupdate(self):
        while True:
            # RTC Update
            self.config['RTC_TIME'] = self.rtc.datetime()
            rtc = self.config['RTC_TIME']
            # Проверка летнего или зименего времени каждую минуту в 30с
            if rtc[5] == 30: 
                self.rtc.settime('dht')
            # Если у нас режим подключения к точке доступа и если есть соединение, подводим часы по NTP
            if self.config['MODE_WiFi'] == 'ST' and not self.config['no_wifi']:
                # Подводка часов по NTP каждые сутки в 22:00:00
                if rtc[3] == 22 and rtc[4] == 5 and rtc[5] < 3 and self.config['NTP_UPDATE']:
                        self.config['NTP_UPDATE'] = False
                        self.rtc.settime('ntp')
                        await asyncio.sleep(1)
                        self.config['NTP_UPDATE'] = True
            # Data Update
            self.config['TEMP'] = round(self.temp.value, 2) # Обновляем данные о температуре воды в бойлере
            # Управление нагревом воды в бойлере
            if self.config['WORK_ALL']:
                self.heat.duty(self.heat_work())
            elif self.config['WORK_TABLE'] and self.time_on_off():
                self.heat.duty(self.heat_work())
            elif self.config['ONE-TIME'] and self.time_on_off():
                self.heat.duty(self.heat_work())
                if self.config['NOW'] == self.config['T_OFF'] - 2:
                    setting_update(workmod='offall')
            else:
                self.config['PWM'] = self.config['POWER'][0]
                self.heat.duty(self.config['PWM'])
            await asyncio.sleep(1)


    # Индикация подключения WiFi
    async def _heartbeat(self):
        while True:
            if self.config['no_wifi'] and self.config['MODE_WiFi'] == 'ST':
                self.wifi_led(not self.wifi_led())      # Быстрое мигание, если соединение отсутствует
                await asyncio.sleep_ms(200)
            elif not self.config['no_wifi'] and self.config['MODE_WiFi'] == 'ST':
                self.wifi_led(0)                        # Редкое мигание при подключении
                await asyncio.sleep_ms(50)
                self.wifi_led(1)
                await asyncio.sleep_ms(5000)
            else:
                self.wifi_led(0)                        # Два быстрых миганиения при AP Mode
                await asyncio.sleep_ms(50)
                self.wifi_led(1)
                await asyncio.sleep_ms(50)
                self.wifi_led(0)
                await asyncio.sleep_ms(50)
                self.wifi_led(1)
                await asyncio.sleep_ms(5000)


    async def _run_main_loop(self):                                     # Бесконечный цикл
        while True:
            if self.config['DEBUG']:
                self.config['MemFree'] = str(round(gc.mem_free()/1024, 2))
                self.config['MemAvailab'] = str(round(gc.mem_alloc()/1024, 2))
                self.config['FREQ'] = str(freq()/1000000)
                ton = self.config['TIME_ON']
                toff = self.config['TIME_OFF']
                if self.config['MODE_WiFi'] == 'ST':
                    wifi = 'connect' if not self.config['no_wifi'] else 'disconnect'
                else:
                    wifi = 'AP mode'
                rtc = self.config['RTC_TIME']
            gc.collect()                                                # Очищаем RAM
            try:
                self.dprint('################# DEBUG MESSAGE ##########################')
                self.dprint('Uptime:', str(self.config['Uptime'])+' min')
                self.dprint('Date: {:0>2d}-{:0>2d}-{:0>2d}'.format(rtc[0], rtc[1], rtc[2]))
                self.dprint('Time: {:0>2d}:{:0>2d}:{:0>2d}'.format(rtc[3], rtc[4], rtc[5]))
                self.dprint('WiFi:', wifi)
                self.dprint('IP:', self.config['IP'])
                self.dprint('Water temp: {:.2f}\'C'.format(self.config['TEMP']))
                self.dprint('Temp Set: {:.2f}\'C'.format(self.config['T_WATER']))
                self.dprint('Continuous work: {}'.format(bool_to_str(self.config['WORK_ALL'])))
                self.dprint('Scheduled operat: {}'.format(bool_to_str(self.config['WORK_TABLE'])))
                self.dprint('One-time activat: {}'.format(bool_to_str(self.config['ONE-TIME'])))
                self.dprint('On time: {:0>2d}:{:0>2d}'.format(ton[3], ton[4]))
                self.dprint('Off time: {:0>2d}:{:0>2d}'.format(toff[3], toff[4]))
                self.dprint('Actual power:', '{}%'.format(str(int(self.config['PWM']/10))))
                self.dprint('MemFree:', '{}Kb'.format(self.config['MemFree']))
                self.dprint('MemAvailab:', '{}Kb'.format(self.config['MemAvailab']))
                self.dprint('FREQ:', '{}MHz'.format(self.config['FREQ']))
                self.dprint('################# DEBUG MESSAGE END ######################')
            except Exception as e:
                self.dprint('Exception occurred: ', e)
            self.config['Uptime'] += 1
            await asyncio.sleep(60)


    async def main(self):
        while True:
            try:
                await self.connect()
                await self._run_main_loop()
            except Exception as e:
                self.dprint('Global communication failure: ', e)
                await asyncio.sleep(20)


gc.collect()                                                            # Очищаем RAM
def_main = Main()
loop = asyncio.get_event_loop()
loop.run_until_complete(def_main.main())
