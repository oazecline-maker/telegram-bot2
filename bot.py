# Название файла: bot.py

import json
import random
import asyncio
import os
from typing import Dict, Any, List, Optional
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, Filter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# =======================================================
# 1. КОНФИГУРАЦИЯ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ ВАШИ ДАННЫЕ)
# =======================================================
# !!! ЗАМЕНИТЕ ЭТОТ ТОКЕН НА ВАШ РЕАЛЬНЫЙ !!!
BOT_TOKEN = "8512963986:AAGIqyCBIoCVTpNdB6ROmsCoHMjsSQSQQJ4"  
# !!! ЗАМЕНИТЕ ЭТОТ ID НА ВАШ РЕАЛЬНЫЙ TELEGRAM ID !!!
ADMIN_ID = 1848493327

# НОРМАЛИЗУЕМ АДМИН ID В СТРОКУ
STR_ADMIN_ID = str(ADMIN_ID)


# =======================================================
# 2. СЛОВАРЬ ЛОКАЛИЗАЦИИ
# =======================================================

TEXTS = {
    "fsm_cancelled_generic": {
        "en": "Operation cancelled. Please select an option from the menu.",
        "ru": "Операция отменена. Пожалуйста, выберите опцию из меню."
    },
    "prompt_select_language": {
        "en": "🌐 Please select your language to continue with the bot.",
        "ru": "🌐 Пожалуйста, выберите ваш язык, чтобы продолжить работу с ботом."
    },
    "login_button": {
        "en": "🔑 Login",
        "ru": "🔑 Войти"
    },
    "welcome_back": {
        "en": "Welcome back, {nickname}!",
        "ru": "С возвращением, {nickname}!"
    },
    "welcome_admin": {
        "en": "Welcome Admin! Use the menu below to manage system.",
        "ru": "Добро пожаловать, Админ! Используйте меню для управления системой."
    },
    "language_set": {
        "en": "Language set to English. Please use the 'Login' button.",
        "ru": "Язык установлен на Русский. Пожалуйста, используйте кнопку 'Войти'."
    },
    "enter_id_code": {
        "en": "Please send your login ID (5-digit code).",
        "ru": "Пожалуйста, отправьте ваш код для входа (5-значный код)."
    },
    "already_logged_in_user": {
        "en": "You are already logged in.",
        "ru": "Вы уже вошли в систему."
    },
    "already_logged_in_admin": {
        "en": "You are already logged in as Admin.",
        "ru": "Вы уже вошли как Админ."
    },
    "logged_in_user": {
        "en": "Login successful. Welcome, {nickname}!",
        "ru": "Вход успешен. Добро пожаловать, {nickname}!"
    },
    "logged_in_admin": {
        "en": "Login successful. Welcome Admin!",
        "ru": "Вход успешен. Добро пожаловать, Админ!"
    },
    "id_not_found": {
        "en": "The ID you entered was not found or is already in use.",
        "ru": "Введенный код не найден или уже используется другим пользователем."
    },
     "try_login_again": {
        "en": "Please try to login again.",
        "ru": "Пожалуйста, попробуйте войти снова."
    },
    "logout_button": {
        "en": "🚪 Log Out",
        "ru": "🚪 Выйти"
    },
    "logged_out_user": {
        "en": "You have been logged out. Please use /start to begin a new session.",
        "ru": "Вы вышли из аккаунта. Пожалуйста, используйте /start, чтобы начать новую сессию."
    },
    "logged_out_admin": {
        "en": "Admin session cleared. Please use /start to begin a new session.",
        "ru": "Админ-сессия очищена. Пожалуйста, используйте /start, чтобы начать новую сессию."
    },
    "enter_nickname": {
        "en": "Enter a nickname for the new user, or press 'Cancel' below:", 
        "ru": "Введите никнейм для нового пользователя, или нажмите 'Отмена' ниже:" 
    },
    "id_created": {
        "en": "🎉 New ID created!\nNickname: `{nickname}`\nCode: `{code}`",
        "ru": "🎉 Новый ID создан!\nНикнейм: `{nickname}`\nКод: `{code}`"
    },
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Получает локализованный текст по ключу, с подстановкой переменных."""
    base_text = TEXTS.get(key, {}).get(lang, key)
    try:
        # Экранирование . и - в подставляемых значениях для HTML/MarkdownV2
        safe_kwargs = {k: str(v).replace('.', '\\.').replace('-', '\\-') for k, v in kwargs.items()}
        return base_text.format(**safe_kwargs)
    except Exception:
        return base_text


# =======================================================
# 3. ХРАНИЛИЩЕ (ФАЙЛОВАЯ СИСТЕМА)
# =======================================================
USERS: Dict[str, Dict[str, Any]] = {}
IDS: List[str] = []

def save_users():
    """Сохраняет данные пользователей."""
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(USERS, f, ensure_ascii=False, indent=2)

def save_ids():
    """Сохраняет список кодов."""
    with open("ids.json", "w", encoding="utf-8") as f:
        json.dump(IDS, f, ensure_ascii=False, indent=2)

def load_data():
    """Загружает данные из JSON файлов при запуске."""
    global USERS, IDS
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            USERS.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, EOFError):
        USERS = {}

    try:
        with open("ids.json", "r", encoding="utf-8") as f:
            IDS.extend(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, EOFError):
        IDS = []

def generate_short_code(length: int = 5) -> str:
    """Генерирует уникальный 5-значный код."""
    while True:
        code = "".join(random.choices("0123456789", k=length))
        if code not in IDS and code not in USERS and code != STR_ADMIN_ID:
            return code

load_data()

# =======================================================
# 4. FSM (Машина конечных состояний)
# =======================================================

class UserStates(StatesGroup):
    waiting_for_language_choice = State()
    waiting_for_login_id = State()

class AdminStates(StatesGroup):
    waiting_for_nick_for_new_id = State()
    
# =======================================================
# 5. СЛУЖЕБНЫЕ ФУНКЦИИ, ФИЛЬТРЫ И УДАЛЕНИЕ СООБЩЕНИЙ
# =======================================================
router = Router()

def is_admin(user_id: int) -> bool:
    """Проверяет права администратора."""
    uid = str(user_id)
    if uid == STR_ADMIN_ID:
        return True
    if uid in USERS and USERS[uid].get("admin"):
        return True
    return False

def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает данные пользователя по его Telegram ID."""
    return USERS.get(str(user_id))

def get_user_lang(user_id: int) -> str:
    """Получает язык пользователя, по умолчанию 'ru'."""
    user_data = get_user_data(user_id)
    return user_data.get("language", "ru") if user_data and user_data.get("language") else "ru" 

class AdminFilter(Filter):
    """Кастомный фильтр для защиты команд администратора."""
    async def __call__(self, message: types.Message) -> bool:
        return is_admin(message.from_user.id)
        
async def delete_and_track_message(msg: types.Message, state: FSMContext, bot: Bot, text: str, reply_markup: Optional = None, parse_mode: str = "HTML") -> types.Message:
    """
    Удаляет предыдущее сообщение бота и сообщение пользователя,
    отправляет новое и сохраняет его ID.
    """
    data = await state.get_data()
    last_bot_msg_id = data.get("last_bot_msg_id")

    if last_bot_msg_id:
        try:
            await bot.delete_message(chat_id=msg.chat.id, message_id=last_bot_msg_id)
        except Exception:
            pass
    
    # Удаление сообщения пользователя, если это не команда
    if msg.text and not msg.text.startswith('/'): 
        try:
            await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id) 
        except Exception:
            pass
            
    try:
        new_msg = await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        # В случае ошибки парсинга, пробуем отправить как простой текст
        print(f"Error sending message with {parse_mode}: {e}. Retrying with plain text.")
        new_msg = await msg.answer(text, reply_markup=reply_markup)
        
    await state.update_data(last_bot_msg_id=new_msg.message_id) 
    
    return new_msg
    
# =======================================================
# 6. КНОПКИ (Меню)
# =======================================================

def language_choice_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇬🇧 English")]],
        resize_keyboard=True
    )

def login_menu(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text("login_button", lang))]],
        resize_keyboard=True
    )

def main_menu(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text("logout_button", lang))]],
        resize_keyboard=True
    )

def admin_menu(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Create ID")],
            [KeyboardButton(text=get_text("logout_button", lang))]
        ],
        resize_keyboard=True
    )

def cancel_inline_markup(lang: str):
    # Используем RU текст для "Cancel" по умолчанию (на англ. это "Cancel")
    cancel_text = "❌ Отмена" if lang == "ru" else "❌ Cancel"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=cancel_text, callback_data="cancel_fsm")]]
    )

# =======================================================
# 7. ХЭНДЛЕРЫ
# =======================================================

@router.message(Command("start", "menu"))
async def start(msg: types.Message, state: FSMContext, bot: Bot):
    
    await state.clear() 
    uid = str(msg.from_user.id)
    
    # 1. Инициализация пользователя
    if uid not in USERS:
        USERS[uid] = {
            "language": None, 
            "nickname": msg.from_user.full_name or "New User", 
            "admin": uid == STR_ADMIN_ID, 
            "balance": 0
        }
        if msg.from_user.username:
             USERS[uid]["username"] = msg.from_user.username
        save_users()
        
    # 2. Если язык не выбран, принудительный выбор
    if USERS[uid].get("language") is None:
        await delete_and_track_message(msg, state, bot, get_text("prompt_select_language", lang="en"), reply_markup=language_choice_menu())
        await state.set_state(UserStates.waiting_for_language_choice)
        return
            
    # 3. Приветствие
    lang = USERS[uid]["language"] 

    if is_admin(msg.from_user.id):
        await delete_and_track_message(msg, state, bot, get_text("welcome_admin", lang=lang), reply_markup=admin_menu(lang))
        return
        
    # Проверка, вошел ли пользователь по коду 
    if "original_code" in USERS[uid]:
        await delete_and_track_message(msg, state, bot, get_text("welcome_back", lang=lang, nickname=USERS[uid].get('nickname', 'User')), reply_markup=main_menu(lang))
    else:
        # Пользователь инициализирован, но не вошел в систему
        await delete_and_track_message(msg, state, bot, get_text("language_set", lang=lang), reply_markup=login_menu(lang))


@router.message(F.text.in_({"🇷🇺 Русский", "🇬🇧 English"}), UserStates.waiting_for_language_choice)
async def process_language_choice(msg: types.Message, state: FSMContext, bot: Bot):
    
    uid = str(msg.from_user.id)
    lang = "ru" if msg.text == "🇷🇺 Русский" else "en"
    
    USERS[uid]["language"] = lang
    save_users()
    
    await state.set_state(None)
    
    if is_admin(msg.from_user.id):
        await delete_and_track_message(msg, state, bot, get_text("welcome_admin", lang=lang), reply_markup=admin_menu(lang))
        return
        
    await delete_and_track_message(msg, state, bot, get_text("language_set", lang=lang), reply_markup=login_menu(lang))


# ========== ЛОГИН (FSM) ==========

@router.message(F.text.regexp(r"🔑 Login|🔑 Войти"))
async def process_id_start(msg: types.Message, state: FSMContext, bot: Bot):
    uid = str(msg.from_user.id)
    lang = get_user_lang(msg.from_user.id)
    
    # 1. Проверка авторизации
    if is_admin(msg.from_user.id):
        await delete_and_track_message(msg, state, bot, get_text("already_logged_in_admin", lang=lang), reply_markup=admin_menu(lang))
        return
        
    if "original_code" in USERS[uid]:
        await delete_and_track_message(msg, state, bot, get_text("already_logged_in_user", lang=lang), reply_markup=main_menu(lang))
        return
        
    # 2. Запрос кода
    await delete_and_track_message(msg, state, bot, get_text("enter_id_code", lang=lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserStates.waiting_for_login_id)


@router.message(UserStates.waiting_for_login_id)
async def get_id(msg: types.Message, state: FSMContext, bot: Bot):
    code_entered = msg.text.strip()
    uid = str(msg.from_user.id)
    lang = get_user_lang(msg.from_user.id) 

    if code_entered in USERS and len(code_entered) < 7: 
        
        target_user_data = USERS[code_entered].copy()
        
        # === ЛОГИКА ПРИВЯЗКИ ===
        target_user_data["original_code"] = code_entered 
        USERS[uid].update(target_user_data)
        
        if msg.from_user.username:
             USERS[uid]["username"] = msg.from_user.username
        USERS[uid]["nickname"] = target_user_data.get("nickname") or msg.from_user.full_name or "User"
        
        if code_entered in IDS:
            IDS.remove(code_entered)
        if code_entered in USERS:
             del USERS[code_entered] 
        
        save_ids()
        save_users()
        # =======================
        
        lang = USERS[uid]["language"] or get_user_lang(msg.from_user.id) 
        await state.set_state(None)
        
        if is_admin(msg.from_user.id):
            await delete_and_track_message(msg, state, bot, get_text("logged_in_admin", lang=lang), reply_markup=admin_menu(lang))
        else:
            await delete_and_track_message(msg, state, bot, get_text("logged_in_user", lang=lang, nickname=USERS[uid]['nickname']), reply_markup=main_menu(lang))
            
    else: 
        await state.set_state(None)
        text = get_text("id_not_found", lang=lang) + "\n" + get_text("try_login_again", lang=lang)
        await delete_and_track_message(msg, state, bot, text, reply_markup=login_menu(lang))


# ========== ВЫХОД (LOG OUT) ==========

@router.message(F.text.regexp(r"🚪 Log Out|🚪 Выйти"))
async def log_out(msg: types.Message, state: FSMContext, bot: Bot):
    uid = str(msg.from_user.id)
    lang = get_user_lang(msg.from_user.id)
    
    await state.clear()
    
    msg_text = get_text("logged_out_user", lang=lang)
    reply_markup = login_menu(lang)
    
    if uid in USERS:
        # Для обычных пользователей
        if not is_admin(msg.from_user.id) and "original_code" in USERS[uid]:
            del USERS[uid]["original_code"]
            
        elif is_admin(msg.from_user.id):
            # Для всех админов
             if uid != STR_ADMIN_ID:
                USERS[uid]["admin"] = False
             msg_text = get_text("logged_out_admin", lang=lang)
            
        save_users()
        
    await delete_and_track_message(msg, state, bot, msg_text, reply_markup=reply_markup)


# ========== АДМИН: СОЗДАНИЕ ID (FSM) ==========

@router.message(F.text == "➕ Create ID", AdminFilter())
async def create_id_start(msg: types.Message, state: FSMContext, bot: Bot):
    lang = get_user_lang(msg.from_user.id)
    text = get_text("enter_nickname", lang=lang)
    markup = cancel_inline_markup(lang)
    await delete_and_track_message(msg, state, bot, text, reply_markup=markup)
    await state.set_state(AdminStates.waiting_for_nick_for_new_id)

@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm_command(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    
    lang = get_user_lang(call.from_user.id)
    
    try:
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None) 
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass 
        
    await call.answer(get_text("fsm_cancelled_generic", lang).split(".")[0])
    
    await state.clear()
    
    markup = admin_menu(lang) if is_admin(call.from_user.id) else login_menu(lang) # После отмены админ возвращается в админ-меню.
    
    # Отправляем новое сообщение с подтверждением отмены и новым меню
    await call.message.answer(get_text("fsm_cancelled_generic", lang=lang), reply_markup=markup) 


@router.message(AdminStates.waiting_for_nick_for_new_id)
async def get_nickname(msg: types.Message, state: FSMContext, bot: Bot):
    lang = get_user_lang(msg.from_user.id)
    new_nickname = msg.text.strip()
    
    new_code = generate_short_code()

    # 1. Создаем новый аккаунт
    USERS[new_code] = {
        "nickname": new_nickname, 
        "balance": 0, 
        "admin": False, 
        "language": "ru" 
    }
    IDS.append(new_code)
        
    save_users()
    save_ids()

    # 2. Сбрасываем состояние и отправляем результат
    await state.clear()
    
    # Используем MarkdownV2 для форматирования ```code```
    text = get_text("id_created", lang=lang, nickname=new_nickname, code=new_code)
    await delete_and_track_message(msg, state, bot, text, reply_markup=admin_menu(lang), parse_mode="MarkdownV2")
    
# =======================================================
# 8. ЗАПУСК БОТА
# =======================================================

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    if STR_ADMIN_ID not in USERS:
        USERS[STR_ADMIN_ID] = {"nickname": "Main Admin", "balance": 0, "admin": True, "language": "ru"}
        save_users()
        
    print("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
    except Exception as e:
        print(f"An error occurred in the main loop: {e}")
