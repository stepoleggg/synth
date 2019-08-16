import pygame
import pygame.midi
import pyaudio
import numpy as np

p = pyaudio.PyAudio()

#базовые параметры
fs = 44100 #сэмпл рейт
buffer_size = 128 #размер буфера в сэмплах
volume_master = 0.2 #коэффициент громкости для мастер-канала

#массив значений нот, содержащий громкости нажатия, фазы каждой ноты и громкости нажатия при уже отпущенной клавише 
#(используется чтобы избежать щелчка)
keys = np.zeros((128,3))

#функции различных типов волн
#square wave
def square(buffer):
    return buffer % 2*np.pi < np.pi
#saw wave
saw = lambda x: (x % 2*np.pi)/2
#sin wave
sin = np.sin

#функция осциллятора, период 2Pi радиан
def osc(buffer):
    return sin(buffer)

#расчет синусоид в буфере
def callback(in_data, frame_count, time_info, status):
    #global buffer_pred
    #задаем начальные значения буфера (нули)
    buffer = np.zeros(buffer_size, dtype=np.float32)
    #обходим каждре значение в наборе нот
    for key, v in enumerate(keys):
        #клавиша нажата
        if v[0] > 0:
            #получаем частоту ноты в герцах
            f = 440*((2**(1.0/12))**(key-69))
            phase = v[1]
            #получаем буфер для одной ноты
            d = (osc(2*np.pi*np.arange(phase*buffer_size, (phase+1)*buffer_size)*f/fs)*v[0]).astype(np.float32)
            keys[key][1] = phase+1
            #добавляем буфер к общему буферу всех нот
            buffer = np.add(buffer,d)
        #клавишу отпустили
        if v[0] == 0 and v[1] > 0:
            f = 440*((2**(1.0/12))**(key-69))
            phase = v[1]
            #расчет такой фазы, чтобы синусоида попала в ноль, и не было щелчка
            x = int((1 - phase*buffer_size*f/fs % 1)*fs/f)
            #print(x, (phase*buffer_size+x)*f/fs)
            #если частота низкая и нельзя закончить синусоиду в пределах буфера
            if x+1 > buffer_size:
                d = (osc(2*np.pi*np.arange(phase*buffer_size, phase*buffer_size+buffer_size)*f/fs)*v[2]).astype(np.float32)
                keys[key][1] = phase+1
            #заканчиваем в пределах буфера
            else:
                d1 = (osc(2*np.pi*np.arange(phase*buffer_size, phase*buffer_size+x+1)*f/fs)*v[2]).astype(np.float32)
                d2 = np.zeros(buffer_size-x-1, dtype = np.float32)
                d = np.concatenate((d1,d2))
                keys[key][1] = 0
            buffer = np.add(buffer,d)
    #умножаем на коэффициент общей громкости, чтобы не было перегруза на общем канале
    buffer*=volume_master
    return (buffer, pyaudio.paContinue)

#открываем поток для звуков
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=fs,
                output=True,
                frames_per_buffer = buffer_size,
                stream_callback=callback)



#устанавливаем pygame
pygame.init()
pygame.midi.init()
 
#список миди-девайсов
for x in range( 0, pygame.midi.get_count() ):
    print(pygame.midi.get_device_info(x))
 
#выбор миди-устройства
inp = pygame.midi.Input(1)

while True:
    if inp.poll():
        #чтение миди информации
        message = inp.read(1)
        event, key, val, _ = message[0][0]
        volume = val/127
        #записываем во 2ую ячейку предыдущее значение громкости (чтобы при отпускании знать, с какой амплитудой было нажатие)
        keys[key][2] = keys[key][0]
        keys[key][0] = volume
        if volume > 0:
            keys[key][1] = 0
    pygame.time.wait(1)
stream.stop_stream()
p.terminate()

