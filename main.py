from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from config1 import id
from config1 import ikb2, sn, s, CHANNELS, showChannels, logs_chat,min_bet,max_bet
from asyncio import sleep
from aiocryptopay import AioCryptoPay
import random
import math
import asyncio
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation



# FOR ENDWAY ❤️


def PayKb1():
  keyboard = types.InlineKeyboardMarkup()
  b2 = types.InlineKeyboardButton("Сделать ставку", url=ikb2)
  keyboard.add(b2)
  return keyboard

storage = MemoryStorage()
bot = Bot(token='7962807673:AAEquG8uwyd28wGPKXfML-aLnleBbpH7XJY')
dp = Dispatcher(bot,
                storage=storage)
crypto = AioCryptoPay(token="421202:AAZ11lN3Rdl0PXWTBC6KmIDyfadtMeCt9DE")

PayKb = types.InlineKeyboardButton("Сделать ставку", url=ikb2)


games = ['краш']
@dp.channel_post_handler()
async def handle_translation(message: types.Message):
    print(message)
    if message.chat.id == message.chat.id:
        check = ''
        prefix = "($"
        text = message.text
        entata = message.entities
        cb_winid = entata[0].user.id
        name = entata[0].user.first_name
        comment = message.text.split('💬 ')
        try:
            comment_data = comment[1]
        except:
            comment_data = comment[0]
        STAVKA = comment_data.replace('💬', '')
        STAVKA = STAVKA.lower()
        
        stt = text[text.index(prefix) + len(prefix):].strip()
        value = stt.replace(').', '').replace(f"\n", "").replace(f"{comment_data}", "").replace('💬', '')
        if float(value) < min_bet:
            print('Ставка меньше минималки')
            return
        if float(value) > max_bet:
            print('Ставка больше максимальной')
            return
        basa = message.entities
        cb_winid = basa[0].user.id
        words = message.text.split()
        await bot.edit_message_text(text='[✅] Ваша ставка принята в работу!', message_id=message.message_id, chat_id=message.chat.id)
        await bot.send_message(message.chat.id,
                               f"[💎] Новая ставка!\n<blockquote>Никнейм игрока:{name}</blockquote>\n"
                               f"<blockquote>Сумма ставки: {value}$</blockquote>\n"
                               f"<blockquote>Ставка на: {STAVKA}</blockquote>",
                               parse_mode='HTML')
        await log(f"[💎] Новая ставка!\n<blockquote>Никнейм игрока:{name}</blockquote>\n"
                               f"<blockquote>Сумма ставки: {value}$</blockquote>\n"
                               f"<blockquote>Ставка на: {STAVKA}</blockquote>")
    if 'краш' in STAVKA:
        msg = await bot.send_message(message.chat.id, "<blockquote>Игра началась!</blockquote>",parse_mode="HTML")
        a = float(value)
        b = float(comment_data.split(' ')[1])
        coef = generate_random(b)
        now_coef = 1.0

            
        x_vals, y_vals, crash_point = generate_data(coef)
        line, axhline, text, watermark = create_plot(x_vals, y_vals, crash_point)

           
        writer = animation.FFMpegWriter(fps=20)
        ani = animation.FuncAnimation(plt.gcf(), animate, len(x_vals), fargs=(x_vals, y_vals, line, axhline, text, watermark, crash_point), interval=0.2, blit=True)
        ani.save('crash_game.mp4', writer=writer)

            
        kb = types.InlineKeyboardMarkup()
        kb.add(PayKb)
        if crash_point < b:
            result = f"<blockquote>К сожалению, вы проиграли. Итоговый коэффициент: {round(crash_point, 2)}x</blockquote>"
        else:
            rand = random.randint(1, 100000000)
            koma = float(a*b) * 0.95
            try:
              if koma < 1.00:
                  check = await crypto.create_check(asset='USDT',amount=koma,pin_to_user_id=cb_winid)
                  b2 = types.InlineKeyboardButton("Забрать", url=check.bot_check_url)
                  kb.add(b2)
              else:
                await crypto.transfer(spend_id=rand, user_id=cb_winid, asset='USDT', amount=koma)
            except Exception as e:
                print("В казне нет бабла")
            result = f"<blockquote>Поздравляем, вы выиграли! Итоговый коэффициент: {round(coef, 2)}x. Вы получили: {round(a * b, 2)}$</blockquote>"
        await bot.send_video(message.chat.id, open('crash_game.mp4', 'rb'), caption=result, parse_mode="HTML", reply_markup=kb)
    if not STAVKA in games and not 'краш' in STAVKA:
            rand = random.randint(1, 100000000)
            koma = float(value) * 0.95
            if koma < 1.00:
                check = await crypto.create_check(asset='USDT',amount=koma,pin_to_user_id=cb_winid)
                print(check)
            else:
              await crypto.transfer(spend_id=rand, user_id=cb_winid, asset='USDT', amount=koma)
            
            kb = types.InlineKeyboardMarkup()
            b2 = types.InlineKeyboardButton("Забрать", url=check.bot_check_url)
            kb.add(b2)
            kb.add(PayKb)
            await bot.send_message(message.chat.id,
                                   f"<blockquote>{name} Получите возврат с комиссией 25% и прочтите правила в закрепе! </blockquote>" 
                                   f"<a href='https://t.me/AnyBet_play_bot'>Реферальная программа 20%</a> | <a href='https://t.me/Tender_tc'>Техническая Поддержка</a> | <a href='https://t.me/AnyBet_play'>Новостной канал</a>"
                                   f"", reply_markup=kb,
                                   parse_mode='HTML')
            await log(
                      

                                   f"<blockquote>{name} Получите возврат с комиссией 25% и прочтите правила в закрепе! </blockquote>" 
                                   f"<a href='https://t.me/AnyBet_play_bot'>Реферальная программа 20%</a> | <a href='https://t.me/Tender_tc'>Техническая Поддержка</a> | <a href='https://t.me/AnyBet_play'>Новостной канал</a>"
                                   f"")
            
 
async def log(text):
    pass
    
def generate_random(b):
    return random.uniform(1,15)

def generate_data(crash_point):
    x_vals = []
    y_vals = []
    x = 0
    while x < crash_point:
        x += 0.01
        y = math.exp(x)
        x_vals.append(x)
        y_vals.append(y)
    return x_vals, y_vals, crash_point

def create_plot(x_vals, y_vals, crash_point):
    plt.figure(figsize=(8, 4))
    plt.rcParams['axes.facecolor'] = '#000000'  
    plt.rcParams['figure.facecolor'] = '#000000'  
    line, = plt.plot(x_vals, y_vals, color='#ffd700', linewidth=2)
    axhline = plt.axhline(y=crash_point, color='#e74c3c', linestyle='-', linewidth=2)
    plt.xticks([])
    plt.yticks([])
    plt.xlim(0, crash_point + 0.1)
    plt.ylim(1, math.exp(crash_point))
    plt.grid(color='#ccc', linestyle='-', linewidth=1)
    plt.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)
    text = plt.text(0, 1, f'{crash_point:.2f}x', color='#ffffff', fontsize=16, fontweight='bold')
    watermark = plt.text(crash_point / 2, math.exp(crash_point) / 2, '@AnyBet_play', color='#ccc', fontsize=24, alpha=0.5, ha='center', va='center')

    return line, axhline, text, watermark


def animate(i, x_vals, y_vals, line, axhline, text, watermark, crash_point):
    line.set_data(x_vals[:i], y_vals[:i])
    axhline.set_ydata([math.exp(x_vals[i])] if i < len(x_vals) - 1 else [crash_point])
    text.set_position((x_vals[i], math.exp(x_vals[i])))
    text.set_text(f'{crash_point * (math.exp(x_vals[i]) / math.exp(crash_point)):.2f}x')
    return line, axhline, text, watermark

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)