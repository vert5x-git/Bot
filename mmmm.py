import telebot
from telebot import types
import random
import time
import requests
import string # Для генерации промокодов

# --- Настройки бота ---
BOT_TOKEN = "YOUR_BOT_TOKEN"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН БОТА
CRYPTO_PAY_API_TOKEN = "YOUR_CRYPTO_PAY_API_TOKEN"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН CRYPTO PAY API
CRYPTO_PAY_API_URL = "https://pay.crypt.bot/api/" # Базовый URL Crypto Pay API

# --- ID Основных Администраторов ---
# ВАЖНО: Добавьте сюда свой Telegram ID, чтобы получить доступ к админ-функциям.
# Узнать свой ID можно у @userinfobot в Telegram.
# Эти ID всегда имеют полный доступ и могут выдавать/отзывать админки другим.
SUPER_ADMIN_IDS = [123456789] # ЗАМЕНИТЕ ЭТИ ID НА РЕАЛЬНЫЕ ID ГЛАВНЫХ АДМИНИСТРАТОРОВ

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
    if chat_id n