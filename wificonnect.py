import gc, network
import uasyncio as asyncio
gc.collect()                                #Очищаем RAM

config = {}                                 #Основное хранилище настроек
config['DEBUG'] = True                      #Разрешаем отладочные сообщения
config['MODE_WiFi'] = 'ST'                  #Режим работы WiFi AP или ST
config['ssid'] = 'w2234'                    #SSID для подключения к WiFi
#config['ssid'] = 'BOILER_CONTROLLER'               #SSID для подключения к WiFi
#config['wf_pass'] = 'tinywind994'          #Пароль для подключения к WiFi
config['wf_pass'] = 'Fedex##54'             #Пароль для подключения к WiFi
config['WIFI_AP'] = ('192.168.4.1', '255.255.255.0', '192.168.4.1', '208.67.222.222')
config['IP'] = None                         #Дефолтный IP адрес
config['no_wifi'] = True                    #Интернет отключен(значение True)
config['Uptime'] = 0                        #Время работы контроллера
config['MemFree'] = None
config['MemAvailab'] = None
config['FREQ'] = None
config['RTC_TIME'] = (0, 1, 1, 0, 0, 0, 0, 0)
config['NTP_UPDATE'] = True
config['TEMP'] = None
config['PRESSURE'] = None
config['HUMIDITY'] = None


#Базовый класс
class WiFiBase:
    def __init__(self, config):
        self.config = config
        if self.config['MODE_WiFi'] == 'AP':
            self._ap_if = network.WLAN(network.AP_IF)
            self.config['WIFI'] = self._ap_if
        elif self.config['MODE_WiFi'] == 'ST':
            self._sta_if = network.WLAN(network.STA_IF)
            self.config['WIFI'] = self._sta_if


    #Выводим отладочные сообщения
    def dprint(self, *args):
        if self.config['DEBUG']:
            print(*args)


    #Настройка для режима Точка доступа и подключения к сети WiFi
    def _con(self):
        if self.config['MODE_WiFi'] == 'AP':
            self.config['WIFI'].active(True)
            #Устанавливаем SSID и пароль для подключения к Точке доступа
            self.config['WIFI'].config(essid=self.config['ssid'], password=self.config['wf_pass'])
            #Устанавливаем статический IP адрес, шлюз, dns
            self.config['WIFI'].ifconfig(self.config['WIFI_AP'])
        elif self.config['MODE_WiFi'] == 'ST':
            self.config['WIFI'].active(True)
            network.phy_mode(1) # network.phy_mode = MODE_11B
            #Подключаемся к WiFi сети
            self.config['WIFI'].connect(self.config['ssid'], self.config['wf_pass'])

    
    #Выводим сообщения об ошибках соединения
    def _error_con(self):
        #Соединение не установлено...
        if self.config['WIFI'].status() == network.STAT_CONNECT_FAIL:
            self.dprint('WiFi: Failed due to other problems')
        #Соединение не установлено, причина не найдена точка доступа
        if self.config['WIFI'].status() == network.STAT_NO_AP_FOUND:
            self.dprint('WiFi: Failed because no access point replied')
        #Соединение не установлено, не верный пароль
        if self.config['WIFI'].status() == network.STAT_WRONG_PASSWORD:
            self.dprint('WiFi: Failed due to incorrect password')


    #Подключение к сети WiFi или поднятие точки доступа
    async def connect_wf(self):
        if self.config['MODE_WiFi'] == 'AP': #Если точка доступа
            self.dprint('WiFi AP Mode!')
            self._con() #Настройка для режима Точка доступа и подключения к сети WiFi
            if self.config['WIFI'].status() == -1:
                self.dprint('WiFi: AP Mode OK!')
                self.config['IP'] = self.config['WIFI'].ifconfig()[0]
                self.dprint('WiFi:', self.config['IP'])
                self.config['no_wifi'] = False
        elif self.config['MODE_WiFi'] == 'ST': #Если подключаемся к сети
            self.dprint('Connecting to WiFi...')
            self._con() #Настройка для режима Точка доступа и подключения к сети WiFi
            if self.config['WIFI'].status() == network.STAT_CONNECTING:
                self.dprint('WiFi: Waiting for connection to...')
            # Задержка на соединение, если не успешно, будет выдана одна из ошибок
            # Выполнение условия проверяем каждую секунду, задержка для получения IP адреса от DHCP
            while self.config['WIFI'].status() == network.STAT_CONNECTING:
                await asyncio.sleep(1)
            #Соединение успешно установлено
            if self.config['WIFI'].status() == network.STAT_GOT_IP:
                self.dprint('WiFi: Connection successfully!')
                self.config['IP'] = self.config['WIFI'].ifconfig()[0]
                self.dprint('WiFi:', self.config['IP'])
                self.config['no_wifi'] = False #Сообщаем, что соединение успешно установлено
            #Если соединение по каким-то причинам не установлено
            if not self.config['WIFI'].isconnected():
                self.config['no_wifi'] = True #Сообщаем, что соединение не установлено
                self.dprint('WiFi: Connection unsuccessfully!')
            self._error_con() #Выводим сообщения, о причинах отсутствия соединения


    #Переподключаемся к сети WiFi
    async def reconnect(self):
        self.dprint('Reconnecting to WiFi...')
        #Сбрасываем IP адрес к виду 0.0.0.0
        self.config['IP'] = self.config['WIFI'].ifconfig()[0]
        #Разрываем соединение, если они не разорвано
        self.config['WIFI'].disconnect()
        await asyncio.sleep(1)
        self._con() #Настройка для режима Точка доступа и подключения к сети WiFi
        # Задержка на соединение, если не успешно, будет выдана одна из ошибок
        # Выполнение условия проверяем каждые 20 милисекунд, задержка для получения IP адреса от DHCP
        while self.config['WIFI'].status() == network.STAT_CONNECTING:
            await asyncio.sleep_ms(20)
        #Если соединение установлено
        if self.config['WIFI'].status() == network.STAT_GOT_IP:
            #Сохраняем новый IP адрес
            self.config['IP'] = self.config['WIFI'].ifconfig()[0]
            self.config['no_wifi'] = False #Сообщаем, что соединение успешно установлено
            self.dprint('WiFi: Reconnecting successfully!')
            self.dprint('WiFi:', self.config['IP'])
        self._error_con() #Выводим сообщения, о причинах отсутствия соединения
        #Если по какой-то причине соединение не установлено
        if not self.config['WIFI'].isconnected():
            self.config['no_wifi'] = True #Сообщаем, что соединение не установлено
            self.dprint('WiFi: Reconnecting unsuccessfully!')
        await asyncio.sleep(1)


class WiFiControl(WiFiBase):
    def __init__(self):
        super().__init__(config)


    #Проверка соединения с Интернетом
    async def _check_wf(self):
        while True:
            if not self.config['no_wifi']:                      #Если оединение установлено
                if self.config['WIFI'].status() == network.STAT_GOT_IP: #Проверяем наличие соединения
                    await asyncio.sleep(1)
                else:                                                   #Если соединение отсутсвует или оборвано
                    await asyncio.sleep(1)
                    self.config['no_wifi'] = True               #Сообщаем, что соединение оборвано
            else:                                                       #Если соединение отсутсвует
                await asyncio.sleep(1)
                await self.reconnect()                                  #Переподключаемся
        await asyncio.sleep(1)
        gc.collect() 


    #Подключаемся к WiFi или поднимаем точку доступа
    async def connect(self):
        await self.connect_wf()                                         #Подключение или точка доступа, зависит от настройки
        if self.config['MODE_WiFi'] == 'ST':
            loop = asyncio.get_event_loop()
            loop.create_task(self._check_wf())
        elif self.config['MODE_WiFi'] == 'AP':
            gc.collect() 
