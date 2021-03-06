## ESP8266-ADC-Thermistor

[![micropython](https://user-images.githubusercontent.com/13176091/53680744-4dfcc080-3ce8-11e9-94e1-c7985181d6a5.png)](https://micropython.org/)

Небольшая библиотека для работы микроконтроллера ESP8266 с терморезиторами.

В библиотеке используется [уравне́ние Сте́йнхарта — Ха́рта](https://ru.wikipedia.org/wiki/%D0%A3%D1%80%D0%B0%D0%B2%D0%BD%D0%B5%D0%BD%D0%B8%D0%B5_%D0%A1%D1%82%D0%B5%D0%B9%D0%BD%D1%85%D0%B0%D1%80%D1%82%D0%B0_%E2%80%94_%D0%A5%D0%B0%D1%80%D1%82%D0%B0)

![steinhart-hart-small](https://user-images.githubusercontent.com/13176091/53685133-95527380-3d1f-11e9-8fc6-d7467c0e244d.png)

***
### Схема включения терморезисторов

Терморезистор подключен к шине положительного питания

![schematic_esp8266-v1](https://user-images.githubusercontent.com/13176091/53684833-2115d100-3d1b-11e9-91cd-5c94ca4d8e01.png)

Терморезистор подключен к земле

![schematic_esp8266-v2](https://user-images.githubusercontent.com/13176091/53684841-46a2da80-3d1b-11e9-8fdc-c765e0ad1d5a.png)

Библиотека тестировалась с терморезисторами номиналом 10к и 100к

Для термозеисторов номиналом 10к использовались коэффициенты.
```bash
A = 0.001129148
B = 0.000234125
C = 0,000000088
```
Для терморезисторов номиналом 100к использовались коэффициенты (Например, фирмы [VISHAY](https://www.vishay.com/docs/29053/ntcappnote.pdf)).
```bash
A = 3.354016e-03
B = 2.460382e-04
C = 3.405377e-06
D = 1.034240e-07
```
Если коэффициент D не исполььзуется, он должен быть передан как ```D=False``` или же просто опущен

### Использование библиотеки
```python
from term_adc import READ_TERM
from machine import ADC

A = 3.354016e-03         # Коеффициент А терморезистора
B = 2.460382e-04          # Коеффициент B терморезистора
C = 3.405377e-06          # Коеффициент C терморезистора
D = 1.034240e-07          # Коеффициент D терморезистора
K = 5.29                  # Погрешность терморезистора %
BALANCE_R = 98500.0       # Балансный резистор в схеме (ом)
THERMISTOR_R = 100000.0   # Номинал терморезистора (ом)

adc = ADC(0)
t = READ_TERM(adc, BALANCE_R, THERMISTOR_R, A, B, C, K, d=D)

t.values

```









