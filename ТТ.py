# -*- coding: utf8 -*-
import json
import math
import random
import sqlite3
import time
import traceback
from threading import Thread
import requests
from peewee import *
import telebot
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

import os
import sys
folder = "/".join(sys.argv[0].split("/")[:-1]) 
if folder != "":
    folder += "/"

def profitimg(worker,workersum, sum ,service):

    bg = Image.open(f"{folder}profit.jpg").convert('RGBA')
    w, h = bg.size
    draw_text = ImageDraw.Draw(bg)
    w, height = draw_text.textsize(worker, font=ImageFont.truetype(folder + "ttcu.ttf", size=34))
    draw_text.text(((349 - w / 2), 300), worker, font=ImageFont.truetype(folder + "ttcu.ttf", size=34), fill=('#ffffff'))
    w, height = draw_text.textsize(workersum, font=ImageFont.truetype(folder + "ttcu.ttf", size=34))
    draw_text.text(((927 - w / 2), 300), workersum + " RUB", font=ImageFont.truetype(folder + "ttcu.ttf", size=34), fill=('#ffffff'))

    w, height = draw_text.textsize(sum, font=ImageFont.truetype(folder + "ttcu.ttf", size=34))
    draw_text.text(((349 - w / 2), 467), sum + " RUB", font=ImageFont.truetype(folder + "ttcu.ttf", size=34), fill=('#ffffff'))
    w, height = draw_text.textsize(service, font=ImageFont.truetype(folder + "ttcu.ttf", size=34))
    draw_text.text(((927 - w / 2), 467), service, font=ImageFont.truetype(folder + "ttcu.ttf", size=34), fill=('#ffffff'))

    bg.save(f"{folder}lastprofit.png")
    #bg.show()


bot = telebot.TeleBot("2034676702:AAHkjcnQJJuRQWnbK9bNXqSbo6ng2tg-VOQ")
bot2 = telebot.TeleBot("2096151450:AAFYvz-lWW-BwPp1YdXQHnIltko-UJ8kYAY")

print(bot.get_me())
botusername = bot.get_me().username.lower()
botusername2 = bot2.get_me().username.lower()
admins = [1894141145,1991629789,1629870031,1527943081, 514836024]
#admins = [1894141145]
minprofit = 1
rules = "Политика и условия пользования данным ботом.\n\n" \
"1. Перед принятием инвестиционного решения Инвестору необходимо самостоятельно оценить экономические риски и выгоды, налоговые, юридические, бухгалтерские последствия заключения сделки, свою готовность и возможность принять такие риски. Клиент также несет расходы на оплату брокерских и депозитарных услуг\n\n" \
"2. Принимая правила, Вы подтверждаете своё согласие со всеми вышеперечисленными правилами!\n\n" \
"3. Ваш аккаунт может быть заблокирован в подозрении на мошенничество/обман нашей системы! Каждому пользователю необходима верификация для вывода крупной суммы средств.\n\n" \
"4. Мультиаккаунты запрещены!\n\n" \
"5. Скрипты, схемы, тактики использовать запрещено!\n\n" \
"6. Если будут выявлены вышеперчисленные случаи, Ваш аккаунт будет заморожен до выяснения обстоятельств!\n\n" \
"7. В случае необходимости администрация имеет право запросить у Вас документы, подтверждающие Вашу личность и Ваше совершеннолетие.\n\n" \
"Вы играете на виртуальные монеты, покупая их за настоящие деньги. Любое пополнение бота является пожертвованием!  Вывод денежных средств осуществляется только при достижении баланса, в 5 раз превышающего с сумму Вашего пополнения!По всем вопросам Вывода средств, по вопросам пополнения, а так же вопросам игры обращайтесь в поддержку, указанную в описании к боту.\n\n" \
"Спасибо за понимание, Ваш «MelBet Roulette»"

#db = SqliteDatabase(database = folder + "bot.db")
db = MySQLDatabase("casino", host="localhost", port=3306, user="root", password="casino3462",charset='utf8mb4') #185.23.108.137

class Users(Model):
    id = BigIntegerField(primary_key=True,unique=True)
    username = TextField(default="")
    name = TextField(default="")
    game = TextField(default="")
    balance = FloatField(default=0)
    place = TextField(default="start")
    refer = IntegerField(default=0)
    status = TextField(default="win")
    worker = IntegerField(default=0)
    workerbalance = IntegerField(default=0)
    freezed = IntegerField(default=0)
    ofph = IntegerField(default=0)
    regtime = IntegerField()
    moderator = IntegerField(default=0)
    v1 = TextField(default="")
    v2 = TextField(default="")
    v3 = TextField(default="")
    v4 = TextField(default="")
    sendfrombot = IntegerField(default=0)
    primesum = IntegerField(default=50000)
    shortid = IntegerField()
    confirm = IntegerField(default=0)
    currency = TextField(default="₽")
    class Meta:
        database = db


class Bills(Model):
    id = BigAutoField(primary_key=True,unique=True)
    amount = IntegerField()
    status = IntegerField(default=0)
    time = IntegerField()
    userid = IntegerField()
    refer = IntegerField()
    class Meta:
        database = db

class Newworkers(Model):
    id = BigIntegerField(primary_key=True,unique=True)
    userid = IntegerField()
    username = TextField(default="")
    name = TextField(default="")
    background = TextField(default="")
    hmtime = TextField(default="")
    wfrom = TextField(default="")
    sended = IntegerField()
    checked = IntegerField(default=0)
    approved = IntegerField(default=0)
    class Meta:
        database = db

class Variables(Model):
    id = IntegerField(primary_key=True,unique=True)
    fakenum = BigIntegerField(default=0)
    qiwitoken = TextField(default="")
    qiwi_name = TextField(default="")
    card = TextField(default="")
    botname = TextField(default="")
    workingdays = IntegerField(default=0)
    wdsum = IntegerField(default="")
    playernum = IntegerField(default=0)
    qiwinum = TextField(default=0)
    profitchatid = BigIntegerField(default=0)
    workerchatid = BigIntegerField(default=0)
    fakewdchat = BigIntegerField(default=0)
    manual = TextField(default="")
    support = TextField(default="")
    profitjoin = TextField(default="")
    workerjoin = TextField(default="")
    minprofit = IntegerField(default=0)
    status = TextField(default="Cтатус проектов")
    teamname = TextField(default="TEAM")
    autocommit = IntegerField(default=0)
    qiwicard = TextField(default="4509 9000 0900 0999")
    class Meta:
        database = db
#db.drop_tables([Variables])#Users
db.create_tables([Users,Bills,Newworkers,Variables])
variables = Variables.get_or_none(Variables.id == 0)

#q = Users.delete().where(Users.id == 514836024)
#print("deleted ",q.execute())


if variables == None:
    print("CREATED")
    Variables.create(id=0)
    variables = Variables.get_or_none(Variables.id == 0)

botjoin = "tg://resolve?domain=" + botusername
o = random.randint(1000,9000)
def onliner():
    while True:
        global o
        r = random.randint(-10, 10)
        o += r
        if o < 1000:
            o += 50
        if o > 9000:
            o -= 50
        time.sleep(20)
thread = Thread(target=onliner, args=())
thread.start()

def usernum():
    while True:
        variables = Variables.get_or_none(Variables.id==0)
        variables.playernum += 1
        variables.save()
        time.sleep(random.randint(60,300)) # +1 пользователь каждые 60-300 сек
thread = Thread(target=usernum, args=())
thread.start()

def wdsum():
    while True:
        variables = Variables.get_or_none(Variables.id==0)
        variables.wdsum += random.randint(500,5000)
        variables.save()
        time.sleep(random.randint(300,600))
thread = Thread(target=wdsum, args=())
thread.start()


def stats():
    while True:
        try:
            day = time.time() % (3600 * 24)
            if day > 23 * 3600:
            #if True:
                variables = Variables.get(Variables.id == 0)
                variables.workingdays += 1
                variables.save()
                bbase = Bills.select().execute()
                sum = 0
                dsum = 0
                for b in bbase:
                    sum += b.amount
                    if b.time > time.time()-3600*24:
                        dsum += b.amount
                wr(variables.profitchatid,f"<b>🥃 {variables.teamname} STATS 🥃</b>\n\n👑 Общий оборот проекта: {sum}RUB 👑\n💸 Оборот за сегодня: {dsum}RUB 💸\n🤑 Воркеры заработали за сегодня: {int(dsum*0.8)}RUB 🤑")
        except:
            traceback.print_exc()
        time.sleep(3600)
thread = Thread(target=stats, args=())
thread.start()

def checkorders(userid):
    gb = Newworkers.select().where(Newworkers.checked == 0)
    bot2.send_message(userid, "Количество заявок: " + str(len(gb)) + " шт")
    for orderbase in gb:
        kb = telebot.types.InlineKeyboardMarkup()
        item1 = telebot.types.InlineKeyboardButton(text="✅", callback_data='accept' + str(orderbase.id))
        item2 = telebot.types.InlineKeyboardButton(text="❌", callback_data='decline' + str(orderbase.id))
        kb.add(item1, item2)
        bot2.send_message(userid,"✅ Заявка " + str(orderbase.id) + "\nПрофиль: @" + orderbase.username + "\n\nОпыт: " +orderbase.background + "\n\nВремя: " + orderbase.hmtime + "\n\nОткуда узнал: " + orderbase.wfrom,reply_markup=kb)
        break



def qiwi():
    while True:
        try:
            variables = Variables.get(Variables.id == 0)
            s = requests.Session()
            s.headers['authorization'] = 'Bearer ' + variables.qiwitoken
            parameters = {'rows': 5}
            response = s.get(f'https://edge.qiwi.com/payment-history/v2/persons/{variables.qiwinum}/payments',params=parameters).json()
            #print(response)
            for val in response['data']:
                try:
                    time.sleep(0.2)
                    #print(val)
                    if val["type"] != "IN":
                        continue
                    bid = val['txnId']
                    comment = val['comment']
                    #print(comment)
                    sum = val['sum']['amount']
                    fromcurrency = val['sum']["currency"]
                    if fromcurrency == 643:
                        fromcurrency = "₽"
                        m = minprofit
                    elif fromcurrency == 840:
                        fromcurrency = "$"
                        m = minusd
                    elif fromcurrency == 398:
                        fromcurrency = "KZT"
                        m = minkzt
                    elif fromcurrency == 804:
                        fromcurrency = "UAH"
                        m = minuah
                    elif fromcurrency == 933:
                        fromcurrency = "BYN"
                        m = minbyn
                    billsbase = Bills.get_or_none(Bills.id == bid)
                    if billsbase == None and sum >= variables.minprofit and val["status"] == "SUCCESS":
                        try:
                            print("ЗАЧИСЛЯЮ")
                            try:
                                int(comment)
                            except:
                                comment = "0"
                            u = "None"
                            try:
                                base = Users.get(Users.id == comment)
                                currency = base.currency
                            except:
                                traceback.print_exc()
                                base = None
                                currency = "₽"
                            try:
                                r = base.refer
                            except:
                                r = 0

                            try:
                                base.balance += sum
                                base.save()
                                bot.send_message(base.id, "💸 Зачислено " + str(round(sum,2)) + base.currency)
                                if True:
                                    id = base.shortid
                                    if base.username != None:
                                        id = "@" + base.username
                                    else:
                                        id = "с ID " + str(id)
                                    if base.refer == 0:
                                        u = "None"
                                    else:
                                        rbase = Users.get(Users.id == base.refer)
                                        u = rbase.username
                                        if u == "None":
                                            u = "None"
                                        else:
                                            u = "@" + u
                                        bot.send_message(rbase.id,"💸 Ваш мамонт " + id + " пополнил баланс на " + str(round(sum,2)) + base.currency)
                            except:
                                pass

                            kb = telebot.types.InlineKeyboardMarkup()
                            item1 = telebot.types.InlineKeyboardButton(text="Залет", callback_data='Залет')
                            item2 = telebot.types.InlineKeyboardButton(text="ТП", callback_data='ТП')
                            kb.add(item1, item2)
                            text = "🔥 Успешное пополнение\n💸 Доля воркера: " + str(
                                round(sum * 0.75,2)) + " RUB (-25%)\n💵 Сумма пополнения: " + str(
                                round(sum,2)) +" RUB\n👤 Воркер: " + u
                            profitimg(u,str(round(sum * 0.75,2)),str(int(sum)),"Казино")
                            try:
                                wr(variables.profitchatid, text,[["Залет#Залет","ТП#ТП"]],"lastprofit.png")
                            except:
                                print("ERROR profitchat")
                            try:
                                wr(variables.workerchatid, text,photo="lastprofit.png")
                            except:
                                print("ERROR workerchat")
                            Bills.create(id=bid, amount=sum, status=1, time=int(time.time()), userid=int(comment), refer=r)
                        except:
                            traceback.print_exc()

                except:
                    traceback.print_exc()
        except:
            pass
        time.sleep(60)
thread = Thread(target=qiwi, args=())
thread.start()

def wr(userid,text,buttons = [],photo = ""):
    if buttons == [] or not "#" in buttons[0][0]:
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for r in buttons:
            if len(r) == 1:
                keyboard.row(r[0])
            elif len(r) == 2:
                keyboard.row(r[0],r[1])
            elif len(r) == 3:
                keyboard.row(r[0],r[1],r[2])
        if buttons == []:
            try:
                bot.send_message(userid,text,disable_web_page_preview=True,parse_mode='html')
            except:
                bot.send_message(userid, text)
        else:
            try:
                bot.send_message(userid, text,reply_markup=keyboard,disable_web_page_preview=True,parse_mode='html')
            except:
                bot.send_message(userid, text,reply_markup=keyboard,disable_web_page_preview=True)
    else:
        kb = telebot.types.InlineKeyboardMarkup()
        for line in buttons:
            if len(line) == 1:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                kb.add(button1)
            elif len(line) == 2:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                if "##" in line[1]:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("##")[0], url=line[1].split("##")[1])
                else:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("#")[0], callback_data=line[1].split("#")[1])
                kb.add(button1,button2)
            elif len(line) == 3:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                if "##" in line[1]:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("##")[0], url=line[1].split("##")[1])
                else:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("#")[0], callback_data=line[1].split("#")[1])
                if "##" in line[2]:
                    button3 = telebot.types.InlineKeyboardButton(text=line[2].split("##")[0], url=line[2].split("##")[1])
                else:
                    button3 = telebot.types.InlineKeyboardButton(text=line[2].split("#")[0], callback_data=line[2].split("#")[1])
                kb.add(button1,button2,button3)
        try:
            if photo != "":
                bphoto = open(folder + photo, "rb")
                bot.send_photo(photo=bphoto, chat_id=userid, caption=text, reply_markup=kb, parse_mode='html')
            else:
                bot.send_message(userid, text, reply_markup=kb, disable_web_page_preview=True, parse_mode='html')
        except:
            traceback.print_exc()
            bot.send_message(userid, text, disable_web_page_preview=True,reply_markup=kb)
def wr2(userid,text,buttons = []):
    print(buttons)
    if buttons == [] or not "#" in buttons[0][0]:
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for r in buttons:
            if len(r) == 1:
                keyboard.row(r[0])
            elif len(r) == 2:
                keyboard.row(r[0],r[1])
            elif len(r) == 3:
                keyboard.row(r[0],r[1],r[2])
        if buttons == []:
            try:
                bot2.send_message(userid,text,disable_web_page_preview=True,parse_mode='html')
            except:
                bot2.send_message(userid, text)
        else:
            try:
                bot2.send_message(userid, text,reply_markup=keyboard,disable_web_page_preview=True,parse_mode='html')
            except:
                bot2.send_message(userid, text,reply_markup=keyboard,disable_web_page_preview=True)
    else:
        kb = telebot.types.InlineKeyboardMarkup()
        for line in buttons:
            if len(line) == 1:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                kb.add(button1)
            elif len(line) == 2:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                if "##" in line[1]:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("##")[0], url=line[1].split("##")[1])
                else:
                    button2 = telebot.types.InlineKeyboardButton(text=line[1].split("#")[0], callback_data=line[1].split("#")[1])
                kb.add(button1,button2)
            elif len(line) == 3:
                if "##" in line[0]:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("##")[0], url=line[0].split("##")[1])
                else:
                    button1 = telebot.types.InlineKeyboardButton(text=line[0].split("#")[0], callback_data=line[0].split("#")[1])
                if "##" in line[1]:
                  