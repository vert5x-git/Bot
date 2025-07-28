import telebot
from telebot import types
import random
import time
import requests
import string # Для генерации промокодов

# --- Настройки бота ---
BOT_TOKEN = "8333111223:AAFDHMtpGkrNV3CVeAwUHkEIkYcNtbxY5fQ"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН БОТА
CRYPTO_PAY_API_TOKEN = "436989:AA06bTX8FJ1NC5lO3EkJERAGxdHj2K21Kv0"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН CRYPTO PAY API
CRYPTO_PAY_API_URL = "https://pay.crypt.bot/api/" # Базовый URL Crypto Pay API

# --- ID Основных Администраторов ---
# ВАЖНО: Добавьте сюда свой Telegram ID, чтобы получить доступ к админ-функциям.
# Узнать свой ID можно у @userinfobot в Telegram.
# Эти ID всегда имеют полный доступ и могут выдавать/отзывать админки другим.
SUPER_ADMIN_IDS = [7692185941] # ЗАМЕНИТЕ ЭТИ ID НА РЕАЛЬНЫЕ ID ГЛАВНЫХ АДМИНИСТРАТОРОВ

bot = telebot.TeleBot(BOT_TOKEN)

# --- Глобальные хранилища данных (ВНИМАНИЕ: данные теряются при перезапуске!) ---
# Для продакшена нужна база данных!
user_balances = {} # {chat_id: {"balance": 0, "ton_balance": 0, "has_premium": False, "donations_count": 0, "is_admin": False}}
promocodes = {}    # {code: {"type": "currency/ton", "amount": 0, "uses_left": 0}}
chat_treasury = {"balance": 0}

# Временное хранилище для состояний пользователей (для многошаговых команд)
user_states = {} # {chat_id: {"state": "waiting_for_promo_code", "data": {}}}

# --- Эмодзи для событий ---
EMOJI_MINES_START = "💣"
EMOJI_MINES_WIN = "🎉"
EMOJI_MINES_LOSE = "💥"
EMOJI_CUBE_START = "🎲"
EMOJI_CUBE_WIN = "✨"
EMOJI_CUBE_LOSE = "😢"
EMOJI_COIN_FLIP = "🪙"
EMOJI_HIGHER_LOWER = "🔢"
EMOJI_SLOT_MACHINE = "🎰"
EMOJI_PREMIUM_GRANTED = "🌟"
EMOJI_PREMIUM_FEATURE = "👑"
EMOJI_ADMIN_PANEL = "⚙️"
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_BALANCE = "💰"
EMOJI_TON = "💎"
EMOJI_TOP = "🏆"
EMOJI_TREASURY = "🏦"
EMOJI_PROMOCODE = "🎁"
EMOJI_BROADCAST = "📢"

# --- Хелперы для работы с балансом и данными пользователя ---
def get_user_data(chat_id):
    if chat_id not in user_balances:
        user_balances[chat_id] = {
            "balance": 1000, # Начальный баланс для новых пользователей
            "ton_balance": 0,
            "has_premium": False,
            "donations_count": 0,
            "is_admin": chat_id in SUPER_ADMIN_IDS # Супер-админы всегда админы
        }
    return user_balances[chat_id]

def update_balance(chat_id, amount):
    user_data = get_user_data(chat_id)
    user_data["balance"] += amount

def update_ton_balance(chat_id, amount):
    user_data = get_user_data(chat_id)
    user_data["ton_balance"] += amount

def has_premium(chat_id):
    return get_user_data(chat_id).get("has_premium", False)

def is_admin(chat_id):
    return get_user_data(chat_id).get("is_admin", False)

def is_super_admin(chat_id):
    return chat_id in SUPER_ADMIN_IDS

# --- Функции для парсинга ставок с алиасами ---
def parse_bet_amount(message_text, chat_id):
    text = message_text.lower().strip()
    user_data = get_user_data(chat_id)
    
    if text == 'все':
        return user_data["balance"]
    elif text.endswith('к'):
        try:
            amount_k = float(text[:-1])
            return int(amount_k * 1000)
        except ValueError:
            return None
    else:
        try:
            return int(text)
        except ValueError:
            return None

# --- Главное меню ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    chat_id = message.chat.id
    get_user_data(chat_id) # Инициализируем данные для нового пользователя
    user_data = get_user_data(chat_id)

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Сапер 💣'),
        types.KeyboardButton('Кубики 🎲'),
        types.KeyboardButton('Монетка 🪙'),
        types.KeyboardButton('Больше/Меньше 🔢'),
        types.KeyboardButton('Слоты 🎰'),
        types.KeyboardButton('Донат/Привилегии ✨')
    )
    markup.add(
        types.KeyboardButton('Баланс 💰'), # Новая кнопка
        types.KeyboardButton('Мои привилегии 👑'), # Новая кнопка
        types.KeyboardButton('Топ игроков 🏆') # Новая кнопка
    )
    markup.add(types.KeyboardButton('Промокод 🎁')) # Новая кнопка
    
    # Добавляем админ-кнопку, если пользователь - админ
    if is_admin(chat_id):
        markup.add(types.KeyboardButton('Админ-панель ⚙️'))

    bot.send_message(chat_id, "Привет! Выбери игру или опцию:", reply_markup=markup)

# --- Баланс ---
@bot.message_handler(regexp='^Баланс 💰$|^б$|^баланс$')
def show_balance(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    bot.send_message(chat_id,
                     f"{EMOJI_BALANCE} Ваш текущий баланс: **{user_data['balance']:.2f} монет**\n"
                     f"{EMOJI_TON} Ваш TON-баланс: **{user_data['ton_balance']:.2f} TON**",
                     parse_mode='Markdown')

# --- Мои привилегии (бывшая "Эксклюзивная функция") ---
@bot.message_handler(regexp='Мои привилегии 👑')
def show_my_privileges(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    
    premium_status = "Активна 🌟" if user_data["has_premium"] else "Неактивна ❌"
    admin_status = "Да ✅" if user_data["is_admin"] else "Нет ⛔"
    
    bot.send_message(chat_id,
                     f"{EMOJI_PREMIUM_FEATURE} **Ваши привилегии:**\n"
                     f"  Премиум-статус: **{premium_status}**\n"
                     f"  Статус администратора: **{admin_status}**\n"
                     f"  Всего донатов: **{user_data['donations_count']}**\n\n"
                     f"**Премиум-бонусы:**\n"
                     f"  - Увеличенные коэффициенты в играх (пока не реализовано)\n"
                     f"  - Секретная фраза дня: '{random.choice(['Удача улыбается смелым!', 'Сегодня твой день!', 'Верь в свои силы!'])}'",
                     parse_mode='Markdown')

# --- Промокоды ---
@bot.message_handler(regexp='Промокод 🎁')
def promo_code_entry(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f"{EMOJI_PROMOCODE} Введите промокод:")
    user_states[chat_id] = {"state": "waiting_for_promo_code"} # Сохраняем состояние
    bot.register_next_step_handler(message, process_promo_code)

def process_promo_code(message):
    chat_id = message.chat.id
    if user_states.get(chat_id, {}).get("state") != "waiting_for_promo_code":
        return # Игнорируем, если состояние не то

    entered_code = message.text.strip().upper()
    user_data = get_user_data(chat_id)

    if entered_code in promocodes:
        promo_info = promocodes[entered_code]
        if promo_info["uses_left"] > 0:
            if promo_info["type"] == "currency":
                update_balance(chat_id, promo_info["amount"])
                bot.send_message(chat_id, f"{EMOJI_SUCCESS} Промокод активирован! Вы получили **{promo_info['amount']} монет**.")
            elif promo_info["type"] == "ton":
                update_ton_balance(chat_id, promo_info["amount"])
                bot.send_message(chat_id, f"{EMOJI_SUCCESS} Промокод активирован! Вы получили **{promo_info['amount']} TON**.")
            
            promo_info["uses_left"] -= 1
            if promo_info["uses_left"] == 0:
                del promocodes[entered_code] # Удаляем, если все использования исчерпаны
            bot.send_message(chat_id, f"Ваш текущий баланс: {user_data['balance']} монет, {user_data['ton_balance']} TON.", parse_mode='Markdown')
        else:
            bot.send_message(chat_id, f"{EMOJI_ERROR} Этот промокод уже использован или его срок действия истек.")
    else:
        bot.send_message(chat_id, f"{EMOJI_ERROR} Промокод **{entered_code}** не найден или недействителен.", parse_mode='Markdown')
    
    del user_states[chat_id] # Очищаем состояние
    send_welcome(message) # Возвращаемся в главное меню

# --- Топ игроков ---
@bot.message_handler(regexp='Топ игроков 🏆')
def show_top_players(message):
    chat_id = message.chat.id
    # Получаем всех пользователей, у которых есть баланс
    sorted_users = sorted([
        (uid, data["balance"]) for uid, data in user_balances.items()
    ], key=lambda x: x[1], reverse=True) # Сортируем по балансу по убыванию

    top_text = f"{EMOJI_TOP} **Топ 10 игроков по балансу:**\n\n"
    for i, (user_id, balance) in enumerate(sorted_users[:10]):
        # Пытаемся получить имя пользователя. В реальном проекте, имя хранилось бы в БД
        # или использовался бы get_chat для получения имени, но это асинхронно
        # и может быть медленно для большого количества пользователей.
        # Для простоты, используем chat_id.
        top_text += f"{i+1}. Пользователь `{user_id}`: **{balance:.2f} монет**\n"
    
    if not sorted_users:
        top_text += "Пока нет игроков в топе."
        
    bot.send_message(chat_id, top_text, parse_mode='Markdown')

# --- Helper function for setting bets ---
def prompt_for_bet(message, game_type_key, next_step_function):
    bot.send_message(message.chat.id, f"Введите вашу ставку для игры {game_type_key} (например, 100, 5к, или все):")
    bot.register_next_step_handler(message, next_step_function)

def process_bet(message, game_type, start_game_func):
    chat_id = message.chat.id
    bet = parse_bet_amount(message.text, chat_id)
    user_data = get_user_data(chat_id)

    if bet is None or bet <= 0:
        bot.send_message(chat_id, "Некорректная ставка. Пожалуйста, введите положительное число, '1к' или 'все'.")
        # Re-prompt for bet for the specific game
        if game_type == "mines":
            mines_set_bet_prompt(message)
        elif game_type == "dice":
            dice_set_bet_prompt(message)
        elif game_type == "coin_flip":
            coin_flip_set_bet_prompt(message)
        elif game_type == "higher_lower":
            higher_lower_set_bet_prompt(message)
        elif game_type == "slot_machine":
            slot_machine_set_bet_prompt(message)
        return

    if bet > user_data["balance"]:
        bot.send_message(chat_id, f"{EMOJI_ERROR} У вас недостаточно средств для такой ставки. Ваш баланс: {user_data['balance']:.2f} монет.")
        # Re-prompt for bet
        if game_type == "mines":
            mines_set_bet_prompt(message)
        elif game_type == "dice":
            dice_set_bet_prompt(message)
        elif game_type == "coin_flip":
            coin_flip_set_bet_prompt(message)
        elif game_type == "higher_lower":
            higher_lower_set_bet_prompt(message)
        elif game_type == "slot_machine":
            slot_machine_set_bet_prompt(message)
        return

    # Обновляем или создаем запись для пользователя, сохраняя привилегии
    user_data.update({"current_bet": bet, "game_type": game_type})
    bot.send_message(chat_id, f"Ваша ставка для {game_type} установлена на: {bet}.")
    start_game_func(message) # Go back to game menu

# --- Mines Game (unchanged logic, only start menu and bet handling refer to the new structure) ---
@bot.message_handler(regexp='Сапер 💣')
def mines_start_menu(message):
    bot.send_message(message.chat.id, f"{EMOJI_MINES_START} Добро пожаловать в игру Сапер! Хотите сыграть или изменить ставку?")
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Играть в Сапер'),
        types.KeyboardButton('Ввести ставку (Сапер)')
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(regexp='Ввести ставку (Сапер)')
def mines_set_bet_prompt(message):
    prompt_for_bet(message, "Сапер", lambda msg: process_bet(msg, "mines", mines_start_menu))

@bot.message_handler(regexp='Играть в Сапер')
def start_mines_game(message):
    chat_id = message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("current_bet", 0) <= 0 or user_balances[chat_id].get("game_type") != "mines":
        bot.send_message(chat_id, "Пожалуйста, установите ставку для игры Сапер, используя кнопку 'Ввести ставку (Сапер)'.")
        mines_start_menu(message)
        return

    user_data = get_user_data(chat_id)
    bet = user_data["current_bet"]
    update_balance(chat_id, -bet) # Списываем ставку

    mines_count = random.randint(3, 8)
    field_size = 5
    total_cells = field_size * field_size
    mine_positions = random.sample(range(total_cells), mines_count)
    mine_field = ['⬜' for _ in range(total_cells)]
    for pos in mine_positions:
        mine_field[pos] = '💣'

    user_data.update({
        "game_type": "mines",
        "mines_revealed": [],
        "mines_count": mines_count,
        "mine_field": mine_field,
        "current_win": 0,
        "revealed_safe_cells": 0
    })

    bot.send_message(chat_id, f"Игра Сапер началась! На поле {mines_count} мин. Откройте ячейки, чтобы найти безопасные.")
    send_mines_field(chat_id)

def send_mines_field(chat_id):
    game_data = user_balances[chat_id]
    field = game_data["mine_field"]
    revealed = game_data["mines_revealed"]

    markup = types.InlineKeyboardMarkup()
    buttons = []

    for i in range(len(field)):
        if i % 5 == 0 and i != 0:
            markup.add(*buttons)
            buttons = []

        if i in revealed:
            buttons.append(types.InlineKeyboardButton(field[i], callback_data=f"mines_click_{i}"))
        else:
            buttons.append(types.InlineKeyboardButton('❓', callback_data=f"mines_click_{i}"))
    markup.add(*buttons)

    revealed_safe = game_data["revealed_safe_cells"]
    coefficient = 1.0 + (revealed_safe * 0.25)
    # Привилегия: если есть премиум, увеличить коэф
    if has_premium(chat_id):
        coefficient += 0.1 # Небольшой бонус к коэффициенту

    text = f"Ваша ставка: {game_data['current_bet']}\n"
    text += f"Открыто безопасных ячеек: {revealed_safe}\n"
    text += f"Текущий коэффициент: {coefficient:.2f}\n"
    text += f"Текущий выигрыш: {game_data['current_bet'] * coefficient:.2f} монет\n\n"
    text += "Нажмите на ячейку, чтобы открыть ее:"

    cash_out_markup = types.InlineKeyboardMarkup()
    cash_out_button = types.InlineKeyboardButton("Забрать выигрыш 💰", callback_data="mines_cash_out")
    cash_out_markup.add(cash_out_button)

    bot.send_message(chat_id, text, reply_markup=markup)
    if game_data["revealed_safe_cells"] > 0:
        bot.send_message(chat_id, "Хотите забрать выигрыш?", reply_markup=cash_out_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('mines_click_'))
def mines_callback_query(call):
    chat_id = call.message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("game_type") != "mines":
        bot.answer_callback_query(call.id, "Эта игра неактивна или уже завершена.")
        return

    index = int(call.data.split('_')[2])
    game_data = user_balances[chat_id]
    mine_field = game_data["mine_field"]

    if index in game_data["mines_revealed"]:
        bot.answer_callback_query(call.id, "Эта ячейка уже открыта.")
        return

    game_data["mines_revealed"].append(index)

    if mine_field[index] == '💣':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"{EMOJI_MINES_LOSE} Вы попали на мину! Игра окончена.\n"
                                                                                          f"Ваш баланс: {get_user_data(chat_id)['balance']:.2f} монет.")
        # Удаляем временные игровые данные
        game_data["game_type"] = ""
        send_welcome(call.message)
    else:
        game_data["revealed_safe_cells"] += 1
        total_safe_cells = len(mine_field) - game_data["mines_count"]

        coefficient = 1.0 + (game_data["revealed_safe_cells"] * 0.25)
        if has_premium(chat_id):
            coefficient += 0.1
        game_data["current_win"] = game_data["current_bet"] * coefficient

        if game_data["revealed_safe_cells"] == total_safe_cells:
            final_win = game_data["current_bet"] * coefficient
            update_balance(chat_id, final_win)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                  text=f"{EMOJI_MINES_WIN} Поздравляем! Вы открыли все безопасные ячейки! Ваш выигрыш: {final_win:.2f} монет!\n"
                                       f"Ваш баланс: {get_user_data(chat_id)['balance']:.2f} монет.")
            game_data["game_type"] = ""
            send_welcome(call.message)
        else:
            current_bet = game_data["current_bet"]
            current_win = game_data["current_win"]
            
            field_representation = ""
            for i in range(len(mine_field)):
                if i in game_data["mines_revealed"]:
                    field_representation += mine_field[i] + " "
                else:
                    field_representation += "❓ "
                if (i + 1) % 5 == 0:
                    field_representation += "\n"
            
            updated_text = (
                f"Ваша ставка: {current_bet}\n"
                f"Открыто безопасных ячеек: {game_data['revealed_safe_cells']}\n"
                f"Текущий коэффициент: {coefficient:.2f}\n"
                f"Текущий выигрыш: {current_win:.2f} монет\n\n"
                f"Нажмите на ячейку, чтобы открыть ее:\n{field_representation}"
            )
            
            markup = types.InlineKeyboardMarkup()
            buttons = []
            for i in range(len(mine_field)):
                if i % 5 == 0 and i != 0:
                    markup.add(*buttons)
                    buttons = []
                if i in game_data["mines_revealed"]:
                    buttons.append(types.InlineKeyboardButton(mine_field[i], callback_data=f"mines_click_{i}"))
                else:
                    buttons.append(types.InlineKeyboardButton('❓', callback_data=f"mines_click_{i}"))
            markup.add(*buttons)
            
            cash_out_markup = types.InlineKeyboardMarkup()
            cash_out_button = types.InlineKeyboardButton("Забрать выигрыш 💰", callback_data="mines_cash_out")
            cash_out_markup.add(cash_out_button)

            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                  text=updated_text, reply_markup=markup)
            
            # В реальном проекте лучше редактировать существующее сообщение с кнопкой вывода
            # Вместо отправки нового каждый раз
            bot.send_message(chat_id, "Хотите забрать выигрыш?", reply_markup=cash_out_markup)


            bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'mines_cash_out')
def mines_cash_out(call):
    chat_id = call.message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("game_type") != "mines":
        bot.answer_callback_query(call.id, "Эта игра неактивна или уже завершена.")
        return

    game_data = user_balances[chat_id]
    if game_data["revealed_safe_cells"] == 0:
        bot.answer_callback_query(call.id, "Вы пока ничего не выиграли.")
        return

    final_win = game_data["current_win"]
    update_balance(chat_id, final_win)
    bot.send_message(chat_id, f"{EMOJI_MINES_WIN} Вы забрали выигрыш: {final_win:.2f} монет!\n"
                               f"Ваш баланс: {get_user_data(chat_id)['balance']:.2f} монет.")
    game_data["game_type"] = ""
    send_welcome(call.message)

# --- Dice Game ---
@bot.message_handler(regexp='Кубики 🎲')
def dice_start_menu(message):
    bot.send_message(message.chat.id, f"{EMOJI_CUBE_START} Добро пожаловать в игру Кубики! Бросьте кубик или измените ставку?")
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Бросить кубик'),
        types.KeyboardButton('Ввести ставку (Кубики)')
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.message_handler(regexp='Ввести ставку (Кубики)')
def dice_set_bet_prompt(message):
    prompt_for_bet(message, "Кубики", lambda msg: process_bet(msg, "dice", dice_start_menu))

@bot.message_handler(regexp='Бросить кубик')
def roll_dice(message):
    chat_id = message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("current_bet", 0) <= 0 or user_balances[chat_id].get("game_type") != "dice":
        bot.send_message(chat_id, "Пожалуйста, установите ставку для игры Кубики, используя кнопку 'Ввести ставку (Кубики)'.")
        dice_start_menu(message)
        return

    user_data = get_user_data(chat_id)
    user_bet = user_data["current_bet"]
    update_balance(chat_id, -user_bet) # Списываем ставку

    bot_roll = random.randint(1, 6)
    user_roll = random.randint(1, 6)

    bot.send_message(chat_id, f"Вы бросили: {user_roll}")
    bot.send_message(chat_id, f"Я бросил: {bot_roll}")

    if user_roll > bot_roll:
        win_amount = user_bet * 2
        update_balance(chat_id, win_amount)
        bot.send_message(chat_id, f"{EMOJI_CUBE_WIN} Поздравляю! Вы выиграли {win_amount:.2f} монет!\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")
    elif user_roll < bot_roll:
        bot.send_message(chat_id, f"{EMOJI_CUBE_LOSE} К сожалению, вы проиграли {user_bet:.2f} монет.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет. 😢")
    else:
        update_balance(chat_id, user_bet) # Возвращаем ставку
        bot.send_message(chat_id, f"Ничья! Ваша ставка {user_bet:.2f} монет возвращена.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")

    user_data["game_type"] = ""
    send_welcome(message)

# --- Coin Flip Game ---
@bot.message_handler(regexp='Монетка 🪙')
def coin_flip_start_menu(message):
    bot.send_message(message.chat.id, f"{EMOJI_COIN_FLIP} Добро пожаловать в игру Монетка! Орёл или Решка?")
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Бросить монетку'),
        types.KeyboardButton('Ввести ставку (Монетка)')
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(regexp='Ввести ставку (Монетка)')
def coin_flip_set_bet_prompt(message):
    prompt_for_bet(message, "Монетка", lambda msg: process_bet(msg, "coin_flip", coin_flip_start_menu))

@bot.message_handler(regexp='Бросить монетку')
def flip_coin_prompt(message):
    chat_id = message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("current_bet", 0) <= 0 or user_balances[chat_id].get("game_type") != "coin_flip":
        bot.send_message(chat_id, "Пожалуйста, установите ставку для игры Монетка, используя кнопку 'Ввести ставку (Монетка)'.")
        coin_flip_start_menu(message)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Орёл", callback_data="coin_flip_heads"),
        types.InlineKeyboardButton("Решка", callback_data="coin_flip_tails")
    )
    bot.send_message(chat_id, f"Ваша ставка: {user_balances[chat_id]['current_bet']}\n\nВыберите: Орёл или Решка?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('coin_flip_'))
def coin_flip_callback_query(call):
    chat_id = call.message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("game_type") != "coin_flip":
        bot.answer_callback_query(call.id, "Эта игра неактивна или уже завершена.")
        return

    user_data = get_user_data(chat_id)
    user_choice = call.data.split('_')[2]
    result = random.choice(["heads", "tails"])
    result_text = "Орёл" if result == "heads" else "Решка"
    user_choice_text = "Орёл" if user_choice == "heads" else "Решка"
    user_bet = user_data["current_bet"]
    update_balance(chat_id, -user_bet) # Списываем ставку

    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Вы выбрали: **{user_choice_text}**\nМонетка подброшена... и выпал(а) **{result_text}**!", parse_mode='Markdown')

    if user_choice == result:
        win_amount = user_bet * 1.95 # Slightly less than 2x for house edge
        update_balance(chat_id, win_amount)
        bot.send_message(chat_id, f"{EMOJI_CUBE_WIN} Поздравляем! Вы угадали и выиграли {win_amount:.2f} монет!\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")
    else:
        bot.send_message(chat_id, f"{EMOJI_CUBE_LOSE} К сожалению, вы не угадали и проиграли {user_bet:.2f} монет.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет. 😢")

    user_data["game_type"] = ""
    send_welcome(call.message)


# --- Higher or Lower Game ---
@bot.message_handler(regexp='Больше/Меньше 🔢')
def higher_lower_start_menu(message):
    bot.send_message(message.chat.id, f"{EMOJI_HIGHER_LOWER} Добро пожаловать в игру Больше/Меньше! Угадайте, будет ли следующее число больше или меньше.")
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Начать Больше/Меньше'),
        types.KeyboardButton('Ввести ставку (Больше/Меньше)')
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(regexp='Ввести ставку (Больше/Меньше)')
def higher_lower_set_bet_prompt(message):
    prompt_for_bet(message, "Больше/Меньше", lambda msg: process_bet(msg, "higher_lower", higher_lower_start_menu))

@bot.message_handler(regexp='Начать Больше/Меньше')
def start_higher_lower_game(message):
    chat_id = message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("current_bet", 0) <= 0 or user_balances[chat_id].get("game_type") != "higher_lower":
        bot.send_message(chat_id, "Пожалуйста, установите ставку для игры Больше/Меньше, используя кнопку 'Ввести ставку (Больше/Меньше)'.")
        higher_lower_start_menu(message)
        return

    user_data = get_user_data(chat_id)
    bet = user_data["current_bet"]
    update_balance(chat_id, -bet) # Списываем ставку

    first_number = random.randint(1, 100)
    user_data.update({
        "game_type": "higher_lower",
        "higher_lower_number": first_number
    })

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Больше", callback_data="hl_higher"),
        types.InlineKeyboardButton("Меньше", callback_data="hl_lower")
    )
    bot.send_message(chat_id, f"Текущее число: **{first_number}**. Ваша ставка: {user_data['current_bet']:.2f} монет\n\nСледующее число будет больше или меньше?", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('hl_'))
def higher_lower_callback_query(call):
    chat_id = call.message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("game_type") != "higher_lower":
        bot.answer_callback_query(call.id, "Эта игра неактивна или уже завершена.")
        return

    user_data = get_user_data(chat_id)
    user_choice = call.data.split('_')[1]
    current_number = user_data["higher_lower_number"]
    next_number = random.randint(1, 100)
    user_bet = user_data["current_bet"]

    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Текущее число: **{current_number}**. Вы выбрали: **{user_choice}**.\n\nСледующее число: **{next_number}**.", parse_mode='Markdown')

    win = False
    if user_choice == "higher" and next_number > current_number:
        win = True
    elif user_choice == "lower" and next_number < current_number:
        win = True
    elif next_number == current_number: # Tie
        update_balance(chat_id, user_bet) # Возвращаем ставку
        bot.send_message(chat_id, f"Ничья! Числа одинаковые. Ваша ставка {user_bet:.2f} монет возвращена.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")
        user_data["game_type"] = ""
        send_welcome(call.message)
        return

    if win:
        win_amount = user_bet * 1.9
        update_balance(chat_id, win_amount)
        bot.send_message(chat_id, f"{EMOJI_CUBE_WIN} Поздравляем! Вы угадали! Вы выиграли {win_amount:.2f} монет!\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")
    else:
        bot.send_message(chat_id, f"{EMOJI_CUBE_LOSE} К сожалению, вы не угадали и проиграли {user_bet:.2f} монет.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет. 😢")

    user_data["game_type"] = ""
    send_welcome(call.message)

# --- Slot Machine Game ---
@bot.message_handler(regexp='Слоты 🎰')
def slot_machine_start_menu(message):
    bot.send_message(message.chat.id, f"{EMOJI_SLOT_MACHINE} Добро пожаловать в Слоты! Совпадите 3 символа, чтобы выиграть!")
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('Крутить Слоты'),
        types.KeyboardButton('Ввести ставку (Слоты)')
    )
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(regexp='Ввести ставку (Слоты)')
def slot_machine_set_bet_prompt(message):
    prompt_for_bet(message, "Слоты", lambda msg: process_bet(msg, "slot_machine", slot_machine_start_menu))

@bot.message_handler(regexp='Крутить Слоты')
def spin_slot_machine(message):
    chat_id = message.chat.id
    if chat_id not in user_balances or user_balances[chat_id].get("current_bet", 0) <= 0 or user_balances[chat_id].get("game_type") != "slot_machine":
        bot.send_message(chat_id, "Пожалуйста, установите ставку для игры Слоты, используя кнопку 'Ввести ставку (Слоты)'.")
        slot_machine_start_menu(message)
        return

    user_data = get_user_data(chat_id)
    user_bet = user_data["current_bet"]
    update_balance(chat_id, -user_bet) # Списываем ставку

    symbols = ['🍒', '🍋', '🔔', '💎', '🍀', '🍓']

    sent_message = bot.send_message(chat_id, "Крутим...")
    for _ in range(3):
        spinning_symbols = [random.choice(symbols) for _ in range(3)]
        bot.edit_message_text(chat_id=chat_id, message_id=sent_message.message_id, text=f"Крутим...\n\n{' '.join(spinning_symbols)}")
        time.sleep(0.5)

    result = [random.choice(symbols) for _ in range(3)]
    bot.edit_message_text(chat_id=chat_id, message_id=sent_message.message_id, text=f"Результат:\n\n{' '.join(result)}")

    win_multiplier = 0
    if result[0] == result[1] == result[2]:
        if result[0] == '💎': win_multiplier = 10 # Jackpot
        elif result[0] == '🍀': win_multiplier = 7
        else: win_multiplier = 5 # Three of a kind
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win_multiplier = 2 # Two of a kind

    if win_multiplier > 0:
        win_amount = user_bet * win_multiplier
        update_balance(chat_id, win_amount)
        bot.send_message(chat_id, f"{EMOJI_CUBE_WIN} Поздравляем! Вы выиграли {win_amount:.2f} монет!\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет.")
    else:
        bot.send_message(chat_id, f"{EMOJI_CUBE_LOSE} К сожалению, вы проиграли {user_bet:.2f} монет.\n"
                                   f"Ваш баланс: {user_data['balance']:.2f} монет. 😢")

    user_data["game_type"] = ""
    send_welcome(message)


@bot.message_handler(regexp='Донат/Привилегии ✨')
def donation_menu(message):
    chat_id = message.chat.id
    user_data = get_user_data(chat_id)
    
    status = "Активна 🌟" if user_data["has_premium"] else "Неактивна ❌"
    donations = user_data["donations_count"]

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Донат 1 TON (премиум-статус)", callback_data="donate_1_ton"),
        types.InlineKeyboardButton("Донат 5 TON (супер-премиум)", callback_data="donate_5_ton"),
        types.InlineKeyboardButton("Проверить статус доната", callback_data="check_donation_status")
    )
    bot.send_message(chat_id,
                     f"Привет! Здесь ты можешь поддержать бота и получить привилегии.\n\n"
                     f"Твой премиум-статус: **{status}**\n"
                     f"Всего донатов: **{donations}**\n\n"
                     f"Выбери сумму для доната:",
                     parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('donate_'))
def handle_donate_callback(call):
    chat_id = call.message.chat.id
    amount_str = call.data.split('_')[1]
    amount = int(amount_str)
    
    headers = {
        "Content-Type": "application/json",
        "Crypto-Pay-API-Token": CRYPTO_PAY_API_TOKEN
    }
    payload = {
        "asset": "TON",
        "amount": amount,
        "description": f"Донат для бота ({amount} TON)",
        "external_id": f"user_{chat_id}_amount_{amount}_{int(time.time())}",
        "timeout_seconds": 3600,
        "allow_anonymous": True,
        "allow_comments": True
    }
    
    try:
        response = requests.post(f"{CRYPTO_PAY_API_URL}createInvoice", headers=headers, json=payload)
        response.raise_for_status()
        invoice_data = response.json()
        
        if invoice_data["ok"]:
            invoice_url = invoice_data["result"]["pay_url"]
            invoice_id = invoice_data["result"]["invoice_id"]
            
            # Сохраняем ID инвойса для проверки статуса
            user_data = get_user_data(chat_id)
            user_data["last_invoice_id"] = invoice_id
            user_data["last_invoice_amount"] = amount

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Оплатить Донат", url=invoice_url),
                types.InlineKeyboardButton("Я оплатил (проверить статус)", callback_data="check_donation_status")
            )
            bot.send_message(chat_id,
                             f"Для доната в **{amount} TON** перейди по ссылке ниже.\n\n"
                             f"**После оплаты обязательно нажми кнопку 'Я оплатил'**:",
                             parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(chat_id, f"{EMOJI_ERROR} Ошибка при создании инвойса: {invoice_data.get('error', 'Неизвестная ошибка')}")
            print(f"Crypto Pay API Error: {invoice_data}")
            
    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"{EMOJI_ERROR} Произошла ошибка при обращении к платежной системе. Попробуйте позже. ({e})")
        print(f"Request Error: {e}")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'check_donation_status')
def check_donation_status(call):
    chat_id = call.message.chat.id
    user_data = get_user_data(chat_id)
    
    if "last_invoice_id" not in user_data:
        bot.answer_callback_query(call.id, "Нет активных инвойсов для проверки.")
        return

    invoice_id = user_data["last_invoice_id"]
    expected_amount = user_data["last_invoice_amount"]

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_API_TOKEN
    }
    
    try:
        response = requests.post(f"{CRYPTO_PAY_API_URL}getInvoices", headers=headers, json={"invoice_ids": [invoice_id]})
        response.raise_for_status()
        invoices_data = response.json()
        
        if invoices_data["ok"] and invoices_data["result"]["items"]:
            invoice = invoices_data["result"]["items"][0]
            if invoice["status"] == "paid":
                if float(invoice["amount"]) >= expected_amount:
                    update_ton_balance(chat_id, float(invoice["amount"])) # Добавляем TON на баланс пользователя
                    user_data["has_premium"] = True
                    user_data["donations_count"] += 1
                    bot.send_message(chat_id, f"{EMOJI_SUCCESS} Донат успешно оплачен! Вы получили {float(invoice['amount']):.2f} TON и премиум-статус! Спасибо за поддержку!")
                    
                    del user_data["last_invoice_id"]
                    del user_data["last_invoice_amount"]
                    send_welcome(call.message)
                else:
                    bot.send_message(chat_id, f"{EMOJI_ERROR} Донат оплачен, но сумма {invoice['amount']} TON не соответствует ожидаемой {expected_amount} TON. Пожалуйста, свяжитесь с поддержкой.")
            elif invoice["status"] == "active":
                bot.send_message(chat_id, f"⏳ Инвойс еще активен, но пока не оплачен. Пожалуйста, завершите оплату.")
            elif invoice["status"] == "expired":
                bot.send_message(chat_id, f"{EMOJI_ERROR} Срок действия инвойса истек. Попробуйте снова.")
                del user_data["last_invoice_id"]
                del user_data["last_invoice_amount"]
            elif invoice["status"] == "cancelled":
                bot.send_message(chat_id, f"{EMOJI_ERROR} Инвойс был отменен. Попробуйте снова.")
                del user_data["last_invoice_id"]
                del user_data["last_invoice_amount"]
        else:
            bot.send_message(chat_id, f"{EMOJI_ERROR} Не удалось найти инвойс или произошла ошибка в Crypto Pay. Пожалуйста, убедитесь, что вы создали инвойс и попробуйте снова.")
            print(f"Crypto Pay API Error (getInvoices): {invoices_data}")
            
    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"{EMOJI_ERROR} Произошла ошибка при обращении к платежной системе. Попробуйте позже. ({e})")
        print(f"Request Error (getInvoices): {e}")

    bot.answer_callback_query(call.id)

---
### Админ-панель (полностью на инлайн-кнопках)

```python
# --- Админ-панель ---
@bot.message_handler(commands=['admin_panel'])
@bot.message_handler(regexp='Админ-панель ⚙️')
def admin_panel_menu(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "У вас нет прав администратора для доступа к этой панели. ⛔")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Управление пользователями 👥", callback_data="admin_users_menu"),
        types.InlineKeyboardButton("Промокоды 🎁", callback_data="admin_promocodes_menu"),
        types.InlineKeyboardButton("Казна Чата 🏦", callback_data="admin_treasury_menu"),
        types.InlineKeyboardButton("Общая статистика 📊", callback_data="admin_general_stats"),
        types.InlineKeyboardButton("Рассылка 📢", callback_data="admin_broadcast_menu"),
        types.InlineKeyboardButton("Закрыть админ-панель", callback_data="close_admin_panel")
    )
    bot.send_message(chat_id, f"{EMOJI_ADMIN_PANEL} **Добро пожаловать в админ-панель!**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback_query(call):
    chat_id = call.message.chat.id
    if not is_admin(chat_id):
        bot.answer_callback_query(call.id, "У вас нет прав администратора.")
        return
    
    action = call.data.split('_')[1]

    if action == "users_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Выдать привилегию ➕", callback_data="admin_grant_premium_prompt"),
            types.InlineKeyboardButton("Убрать привилегию ➖", callback_data="admin_revoke_premium_prompt"),
            types.InlineKeyboardButton("Выдать админку ✅", callback_data="admin_grant_admin_prompt"), # Новая
            types.InlineKeyboardButton("Убрать админку ❌", callback_data="admin_revoke_admin_prompt"), # Новая
            types.InlineKeyboardButton("Выдать монеты 💰", callback_data="admin_give_currency_prompt"), # Новая
            types.InlineKeyboardButton("Выдать TON 💎", callback_data="admin_give_ton_prompt"), # Новая
            types.InlineKeyboardButton("Посмотреть инфо о пользователе ℹ️", callback_data="admin_get_user_info_prompt"),
            types.InlineKeyboardButton("← Назад в Админ-панель", callback_data="admin_panel_back")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text="Выберите действие с пользователями:", reply_markup=markup)
    
    elif action == "promocodes_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Создать промокод ✨", callback_data="admin_create_promocode_prompt"),
            types.InlineKeyboardButton("Посмотреть промокоды 📜", callback_data="admin_view_promocodes"),
            types.InlineKeyboardButton("Удалить промокод 🗑️", callback_data="admin_delete_promocode_prompt"),
            types.InlineKeyboardButton("← Назад в Админ-панель", callback_data="admin_panel_back")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text="Управление промокодами:", reply_markup=markup)
    
    elif action == "treasury_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        treasury_balance = chat_treasury.get("balance", 0)
        markup.add(
            types.InlineKeyboardButton("Пополнить казну ➕", callback_data="admin_add_to_treasury_prompt"),
            types.InlineKeyboardButton("Вывести из казны ➖", callback_data="admin_remove_from_treasury_prompt"),
            types.InlineKeyboardButton("← Назад в Админ-панель", callback_data="admin_panel_back")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=f"{EMOJI_TREASURY} **Казна Чата:** {treasury_balance:.2f} монет.\nВыберите действие:", parse_mode='Markdown', reply_markup=markup)

    elif action == "general_stats":
        total_users = len(user_balances)
        premium_users = sum(1 for user_info in user_balances.values() if user_info.get("has_premium", False))
        admin_users = sum(1 for user_info in user_balances.values() if user_info.get("is_admin", False))
        total_donations_count = sum(user_info.get("donations_count", 0) for user_info in user_balances.values())

        stats_text = (
            f"**Общая статистика бота:**\n"
            f"  Всего пользователей: {total_users}\n"
            f"  Премиум-пользователей: {premium_users}\n"
            f"  Администраторов: {admin_users}\n"
            f"  Всего донатов (по счетчику): {total_donations_count}\n"
            f"  Баланс казны: {chat_treasury.get('balance', 0):.2f} монет"
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("← Назад в Админ-панель", callback_data="admin_panel_back"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=stats_text, parse_mode='Markdown', reply_markup=markup)

    elif action == "broadcast_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Начать рассылку ✉️", callback_data="admin_start_broadcast_prompt"),
            types.InlineKeyboardButton("← Назад в Админ-панель", callback_data="admin_panel_back")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=f"{EMOJI_BROADCAST} Рассылка сообщений всем пользователям бота.", reply_markup=markup)

    elif action == "panel_back":
        admin_panel_menu(call.message) # Возвращаемся к главному меню админки

    bot.answer_callback_query(call.id) # Подтверждаем обработку callback-запроса

@bot.callback_query_handler(func=lambda call: call.data == 'close_admin_panel')
def close_admin_panel_callback(call):
    chat_id = call.message.chat.id
    if not is_admin(chat_id):
        bot.answer_callback_query(call.id, "У вас нет прав администратора.")
        return
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Админ-панель закрыта. Возвращайтесь, когда понадобится.", reply_markup=None)
    send_welcome(call.message) # Возвращаемся в главное меню

# --- Админ: Управление пользователями (продолжение) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_grant_premium'))
def admin_grant_premium_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите Telegram ID пользователя, которому хотите выдать привилегию:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_grant_premium", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_grant_premium")
def process_admin_grant_premium(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        target_user_id = int(message.text)
        user_data = get_user_data(target_user_id)
        user_data["has_premium"] = True
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Пользователю `{target_user_id}` выдана премиум-привилегия.", parse_mode='Markdown')
        try: bot.send_message(target_user_id, f"{EMOJI_PREMIUM_GRANTED} Администратор выдал вам премиум-привилегию!")
        except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный ID пользователя. Пожалуйста, введите число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_revoke_premium'))
def admin_revoke_premium_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите Telegram ID пользователя, у которого хотите убрать привилегию:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_revoke_premium", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_revoke_premium")
def process_admin_revoke_premium(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        target_user_id = int(message.text)
        user_data = get_user_data(target_user_id)
        user_data["has_premium"] = False
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} У пользователя `{target_user_id}` убрана премиум-привилегия.", parse_mode='Markdown')
        try: bot.send_message(target_user_id, f"{EMOJI_ERROR} Администратор убрал вашу премиум-привилегию.")
        except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный ID пользователя. Пожалуйста, введите число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_grant_admin')) # Новая
def admin_grant_admin_prompt(call):
    chat_id = call.message.chat.id
    if not is_super_admin(chat_id): # Только супер-админ может выдавать админки
        bot.answer_callback_query(call.id, "Только супер-администратор может выдавать админки.")
        return
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите Telegram ID пользователя, которому хотите выдать админку:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_grant_admin", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_grant_admin")
def process_admin_grant_admin(message):
    chat_id = message.chat.id
    if not is_super_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        target_user_id = int(message.text)
        if target_user_id in SUPER_ADMIN_IDS:
             bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_ERROR} Пользователь `{target_user_id}` уже является супер-админом.", parse_mode='Markdown')
        else:
            user_data = get_user_data(target_user_id)
            user_data["is_admin"] = True
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                text=f"{EMOJI_SUCCESS} Пользователю `{target_user_id}` выдана админка.", parse_mode='Markdown')
            try: bot.send_message(target_user_id, f"{EMOJI_ADMIN_PANEL} Администратор выдал вам права администратора!")
            except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный ID пользователя. Пожалуйста, введите число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_revoke_admin')) # Новая
def admin_revoke_admin_prompt(call):
    chat_id = call.message.chat.id
    if not is_super_admin(chat_id):
        bot.answer_callback_query(call.id, "Только супер-администратор может отзывать админки.")
        return
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите Telegram ID пользователя, у которого хотите убрать админку:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_revoke_admin", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_revoke_admin")
def process_admin_revoke_admin(message):
    chat_id = message.chat.id
    if not is_super_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        target_user_id = int(message.text)
        if target_user_id in SUPER_ADMIN_IDS:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_ERROR} Невозможно отозвать админку у супер-админа `{target_user_id}`.", parse_mode='Markdown')
        elif target_user_id in user_balances:
            user_data = get_user_data(target_user_id)
            user_data["is_admin"] = False
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_SUCCESS} У пользователя `{target_user_id}` убрана админка.", parse_mode='Markdown')
            try: bot.send_message(target_user_id, f"{EMOJI_ERROR} Администратор убрал ваши права администратора.")
            except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_ERROR} Пользователь с ID `{target_user_id}` не найден в данных бота.", parse_mode='Markdown')
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный ID пользователя. Пожалуйста, введите число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_give_currency_prompt')) # Новая
def admin_give_currency_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите ID пользователя и сумму монет через пробел (например, `12345 1000`):",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_give_currency", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_give_currency")
def process_admin_give_currency(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        parts = message.text.split()
        target_user_id = int(parts[0])
        amount = float(parts[1])
        if amount <= 0: raise ValueError
        
        user_data = get_user_data(target_user_id)
        update_balance(target_user_id, amount)
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Пользователю `{target_user_id}` выдано `{amount:.2f}` монет.", parse_mode='Markdown')
        try: bot.send_message(target_user_id, f"{EMOJI_BALANCE} Администратор выдал вам **{amount:.2f} монет**! Ваш новый баланс: {user_data['balance']:.2f}.", parse_mode='Markdown')
        except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
    except (ValueError, IndexError):
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный формат. Используйте `ID_пользователя СУММА`.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_give_ton_prompt')) # Новая
def admin_give_ton_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите ID пользователя и сумму TON через пробел (например, `12345 1.5`):",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_give_ton", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_give_ton")
def process_admin_give_ton(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        parts = message.text.split()
        target_user_id = int(parts[0])
        amount = float(parts[1])
        if amount <= 0: raise ValueError
        
        user_data = get_user_data(target_user_id)
        update_ton_balance(target_user_id, amount)
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Пользователю `{target_user_id}` выдано `{amount:.2f}` TON.", parse_mode='Markdown')
        try: bot.send_message(target_user_id, f"{EMOJI_TON} Администратор выдал вам **{amount:.2f} TON**! Ваш новый TON-баланс: {user_data['ton_balance']:.2f}.", parse_mode='Markdown')
        except Exception as e: print(f"Could not notify user {target_user_id}: {e}")
    except (ValueError, IndexError):
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный формат. Используйте `ID_пользователя СУММА`.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_get_user_info_prompt'))
def admin_get_user_info_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите Telegram ID пользователя, информацию о котором хотите посмотреть:",

reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_users_menu")))
    user_states[chat_id] = {"state": "admin_waiting_get_user_info", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_get_user_info")
def process_admin_get_user_info(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        target_user_id = int(message.text)
        user_info = get_user_data(target_user_id) # Используем get_user_data для получения или инициализации
        
        premium_status = "Активна 🌟" if user_info.get("has_premium", False) else "Неактивна ❌"
        admin_status = "Да ✅" if user_info.get("is_admin", False) else "Нет ⛔"
        donations = user_info.get("donations_count", 0)
        balance = user_info.get("balance", 0)
        ton_balance = user_info.get("ton_balance", 0)

        info_text = (
            f"**Информация о пользователе ID `{target_user_id}`:**\n"
            f"  Баланс: {balance:.2f} монет\n"
            f"  TON-баланс: {ton_balance:.2f} TON\n"
            f"  Премиум-статус: {premium_status}\n"
            f"  Статус администратора: {admin_status}\n"
            f"  Количество донатов: {donations}"
        )
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=info_text, parse_mode='Markdown')
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный ID пользователя. Пожалуйста, введите число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_users_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

# --- Админ: Промокоды (продолжение) ---
def generate_promocode_code(length=8):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_create_promocode_prompt'))
def admin_create_promocode_prompt(call):
    chat_id = call.message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("На монеты 💰", callback_data="admin_create_promocode_currency"),
        types.InlineKeyboardButton("На TON 💎", callback_data="admin_create_promocode_ton"),
        types.InlineKeyboardButton("Отмена", callback_data="admin_promocodes_menu")
    )
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Какой тип промокода вы хотите создать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_create_promocode_'))
def admin_select_promocode_type(call):
    chat_id = call.message.chat.id
    promo_type = call.data.split('_')[-1] # currency или ton
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text=f"Введите сумму и количество использований через пробел (например, `100 5` для {promo_type}):",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_promocodes_menu")))
    user_states[chat_id] = {"state": "admin_waiting_create_promocode", "type": promo_type, "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_create_promocode")
def process_admin_create_promocode(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    promo_type = user_states[chat_id]["type"]
    try:
        parts = message.text.split()
        amount = float(parts[0])
        uses_left = int(parts[1])
        if amount <= 0 or uses_left <= 0: raise ValueError
        
        new_code = generate_promocode_code()
        promocodes[new_code] = {"type": promo_type, "amount": amount, "uses_left": uses_left}
        
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Промокод **`{new_code}`** успешно создан!\n"
                                   f"Тип: **{promo_type}**, Сумма: **{amount}**, Использований: **{uses_left}**.", parse_mode='Markdown')
    except (ValueError, IndexError):
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректный формат. Используйте `СУММА КОЛИЧЕСТВО_ИСПОЛЬЗОВАНИЙ`.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_promocodes_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_view_promocodes'))
def admin_view_promocodes(call):
    chat_id = call.message.chat.id
    if not is_admin(chat_id): return
    
    if not promocodes:
        text = "Активных промокодов нет."
    else:
        text = "**Активные промокоды:**\n"
        for code, info in promocodes.items():
            text += f"`{code}`: {info['amount']} {info['type']} (осталось {info['uses_left']} использ.)\n"
    
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("← Назад к Промокодам", callback_data="admin_promocodes_menu"))
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text=text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_delete_promocode_prompt'))
def admin_delete_promocode_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите промокод, который хотите удалить:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_promocodes_menu")))
    user_states[chat_id] = {"state": "admin_waiting_delete_promocode", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_delete_promocode")
def process_admin_delete_promocode(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    code_to_delete = message.text.strip().upper()
    
    if code_to_delete in promocodes:
        del promocodes[code_to_delete]
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Промокод `{code_to_delete}` успешно удален.", parse_mode='Markdown')
    else:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Промокод `{code_to_delete}` не найден.", parse_mode='Markdown')
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_promocodes_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

# --- Админ: Казна Чата ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_add_to_treasury_prompt'))
def admin_add_to_treasury_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите сумму монет, которую хотите добавить в казну:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_treasury_menu")))
    user_states[chat_id] = {"state": "admin_waiting_add_treasury", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_add_treasury")
def process_admin_add_to_treasury(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
        
        chat_treasury["balance"] = chat_treasury.get("balance", 0) + amount
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_SUCCESS} Добавлено {amount:.2f} монет в казну. Текущий баланс: {chat_treasury['balance']:.2f} монет.", parse_mode='Markdown')
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректная сумма. Пожалуйста, введите положительное число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_treasury_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_remove_from_treasury_prompt'))
def admin_remove_from_treasury_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите сумму монет, которую хотите вывести из казны:",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_treasury_menu")))
    user_states[chat_id] = {"state": "admin_waiting_remove_treasury", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_remove_treasury")
def process_admin_remove_from_treasury(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
        
        if chat_treasury.get("balance", 0) >= amount:
            chat_treasury["balance"] -= amount
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_SUCCESS} Выведено {amount:.2f} монет из казны. Текущий баланс: {chat_treasury['balance']:.2f} монет.", parse_mode='Markdown')
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                                  text=f"{EMOJI_ERROR} В казне недостаточно средств. Текущий баланс: {chat_treasury['balance']:.2f} монет.", parse_mode='Markdown')
    except ValueError:
        bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                              text=f"{EMOJI_ERROR} Некорректная сумма. Пожалуйста, введите положительное число.")
    del user_states[chat_id]
    admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_treasury_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

# --- Админ: Рассылка ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_start_broadcast_prompt'))
def admin_start_broadcast_prompt(call):
    chat_id = call.message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                          text="Введите сообщение для рассылки. **Все активные пользователи получат его.**",
                          reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Отмена", callback_data="admin_broadcast_menu")))
    user_states[chat_id] = {"state": "admin_waiting_broadcast_message", "message_id": call.message.message_id}

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("state") == "admin_waiting_broadcast_message")
def process_admin_broadcast(message):
    chat_id = message.chat.id
    if not is_admin(chat_id): return
    msg_to_edit_id = user_states[chat_id].get("message_id")
    
    broadcast_text = message.text
    sent_count = 0
    failed_count = 0

    bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                          text=f"{EMOJI_BROADCAST} Начинаю рассылку. Это может занять некоторое время...")
    
    for user_id in user_balances.keys():
        try:
            bot.send_message(user_id, f"{EMOJI_BROADCAST} **Сообщение от Администрации:**\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1
            time.sleep(0.1) # Небольшая задержка, чтобы избежать лимитов Telegram
        except Exception as e:
            failed_count += 1
            print(f"Failed to send broadcast to {user_id}: {e}")
            # Можно добавить логирование failed_count здесь

    bot.edit_message_text(chat_id=chat_id, message_id=msg_to_edit_id,
                          text=f"{EMOJI_SUCCESS} Рассылка завершена!\n"
                               f"Отправлено: {sent_count}\n"
                               f"Не удалось отправить: {failed_count}",
                               reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("← Назад к Рассылке", callback_data="admin_broadcast_menu")))
    del user_states[chat_id]
    # Возвращаемся в меню рассылки через callback для корректного отображения кнопок
    # admin_callback_query(types.CallbackQuery(id='dummy', from_user=message.from_user, chat_instance='', data='admin_broadcast_menu', message=types.Message(message_id=msg_to_edit_id, chat=message.chat)))

# --- Запуск бота ---
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)