#Бот версии 1.2
#Исправлена ошибка при передаче списка длиной более 4096 возникала отбражения из SQL списка пользователей, которые использовали бота (лога работы). 


# Бот версии 1.3
# В новой версии бота добавлены следующие функции:
# введен массив вознаграждение по УПК РФ по годам, выборка размера во#знаграждения сделана из массива. 

# Бот версии 1.4
# Добавлена информация о размере обязательных ежемесячных отчислений на нужды АПМ в с 01.01.2024

# Бот версии 1.5
# Добавлена информация о количестве обращения за выбранный период времени
# Исправлена ошибка в обработчике кнопки "О боте. Подсказка", более не выдается ошибка, а выводится текст, после чего появляетстьс кнопочное с предложением продолжить работу/закончить работу

# Бот версии 1.6
# Исправленые мелкие ошибки по коду, 
# Используется один правильный вызов save_user_data()
# 🔄 База данных подключается и закрывается автоматически
# 🎯 Убраны дублирующиеся импорты
# ✅ Исправлены ошибки в обработчиках кнопок
# 🚀 Код стал чище и устойчивее к сбоям

# Бот версии 1.8
# Исправленые мелкие ошибки по коду, добавлено инфа по ставкам с 01.10.2025 года

###########################################################################################################

# НАДО СДЕЛАТЬ БОТА В ПОЛНОМ ВИДЕ
# Бот версии 1.7
# Бот выдает Постановление Пленума ВС РФ от 19.12.2013 года № 42 О практике применения судами законодательства о процессуальных издержках по уголовным делам (с изменениями, внесенными постановлениями Пленума от 15 мая 2018 г. № 11 и от 15 декабря 2022 г. № 38)


###########################################################################################################

from config import API_TOKEN, admin_id
from messages import MESSAGE_about, Message_reward_2019, Message_reward_2020, Message_reward_2021
from messages import Message_reward_2022,Message_reward_2023, Message_reward_2024, Message_reward_2025
from messages import Message_reward_gpk_kas, Message_end, Message_reward_upk_opponent
from messages import Message_find_in_mo

########################################################################################################

import logging
import sqlite3
import asyncio

import os
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import types
from aiogram.exceptions import TelegramForbiddenError

import logging

from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database import init_db, db_fetch_all, save_user_data, save_user_attempt
from database import init_db, db_fetch_all, db_fetch_one, db_execute, save_user_data, save_user_attempt


from openpyxl import Workbook

########################################################################################################

# Загружаем чёрный список из файла
def load_blacklist(filename="blacklist.txt"):
    try:
        with open(filename, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

BLACKLIST = load_blacklist()

########################################################################################################

logger = logging.getLogger(__name__)

# Включаем логирование, чтобы не пропустить важные сообщения

#logging.basicConfig(level=logging.INFO)

# Создаём бота и диспетчер
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)  # Исправленная инициализация Dispatcher


# ===== Универсальная отправка PDF: если файла нет — не падаем, а пишем пользователю =====
async def send_pdf_or_stub(callback: CallbackQuery, filename: str, title: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)

    if not os.path.isfile(file_path):
        await callback.message.answer(
            f"📂 Файл *«{title}»* пока недоступен.\nОн будет добавлен позже.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return False

    file = FSInputFile(file_path)
    await callback.message.answer_document(
        document=file,
        caption=f"📄 Файл: *{title}*",
        parse_mode="Markdown"
    )
    await callback.answer()
    return True

########################################################################################################

# Обработчик callback для выбора периода
@dp.callback_query(F.data.startswith("period_"))
async def show_users_by_period(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split("_")[1]
    today = datetime.now().date()

    if period == "today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = start_date
        title = f"Список обращений за сегодня ({start_date}):"

    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-%d")
        end_date = start_date
        title = f"Список обращений за вчера ({start_date}):"

    elif period == "week":
        start = today - timedelta(days=6)
        start_date = start.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = f"Список обращений за последние 7 дней ({start_date} — {end_date}):"

    elif period == "month":
        start = today - timedelta(days=29)
        start_date = start.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = f"Список обращений за последние 30 дней ({start_date} — {end_date}):"

    else:
        await callback.answer("Неверный выбор периода!")
        return

    await callback.answer("Загрузка данных...")

    users = db_fetch_all("""
        SELECT user_id, username, full_name, date, time
        FROM user_data
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, time DESC
    """, (start_date, end_date))

    if not users:
        await callback.message.edit_text("Нет данных за выбранный период.")
        await state.clear()
        return

    response = f"{title}\n\n"

    for user in users:
        user_id, username, full_name, date, time = user
        response += (
            f"ID: {user_id}\n"
            f"Username: @{username if username else 'не указано'}\n"
            f"ФИО: {full_name}\n"
            f"Дата: {date}\n"
            f"Время: {time}\n\n"
        )

    parts = [response[i:i + 4000] for i in range(0, len(response), 4000)]

    for index, part in enumerate(parts):
        if index == 0:
            await callback.message.edit_text(part)
        else:
            await callback.message.answer(part)

    await callback.message.answer(
        f"Всего обращений за выбранный период: {len(users)}"
    )

    await state.clear()

########################################################################################################

# Состояния для выбора периода
class UserPeriod(StatesGroup):
    choosing_period = State()

def get_period_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data="period_today")],
            [InlineKeyboardButton(text="Вчера", callback_data="period_yesterday")],
            [InlineKeyboardButton(text="Последние 7 дней", callback_data="period_week")],
            [InlineKeyboardButton(text="Последние 30 дней", callback_data="period_month")]
        ]
    )

########################################################################################################

# Обработчик команды /users
@dp.message(Command("users"))
async def ask_period(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id == admin_id:
        await message.answer(
            "За какой период вывести информацию?",
            reply_markup=get_period_keyboard()
        )
        await state.set_state(UserPeriod.choosing_period)
    else:
        await message.answer("У вас нет доступа к этой команде.")

########################################################################################################

# Обработчик команды /stats

@dp.message(Command("stats"))
async def show_stats(message: Message):
    user_id = message.from_user.id

    if user_id != admin_id:
        await message.answer("У вас нет доступа к этой команде.")
        return

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    week_start_str = week_start.strftime("%Y-%m-%d")
    month_start_str = month_start.strftime("%Y-%m-%d")

    # Все обращения
    today_count = db_fetch_one(
        "SELECT COUNT(*) FROM user_data WHERE date = ?",
        (today_str,)
    )[0]

    yesterday_count = db_fetch_one(
        "SELECT COUNT(*) FROM user_data WHERE date = ?",
        (yesterday_str,)
    )[0]

    week_count = db_fetch_one(
        "SELECT COUNT(*) FROM user_data WHERE date BETWEEN ? AND ?",
        (week_start_str, today_str)
    )[0]

    month_count = db_fetch_one(
        "SELECT COUNT(*) FROM user_data WHERE date BETWEEN ? AND ?",
        (month_start_str, today_str)
    )[0]

    total_count = db_fetch_one(
        "SELECT COUNT(*) FROM user_data"
    )[0]

    blocked_count = db_fetch_one(
        "SELECT COUNT(*) FROM blocked_attempts"
    )[0]

    # Уникальные пользователи
    unique_today = db_fetch_one(
        "SELECT COUNT(DISTINCT user_id) FROM user_data WHERE date = ?",
        (today_str,)
    )[0]

    unique_yesterday = db_fetch_one(
        "SELECT COUNT(DISTINCT user_id) FROM user_data WHERE date = ?",
        (yesterday_str,)
    )[0]

    unique_week = db_fetch_one(
        "SELECT COUNT(DISTINCT user_id) FROM user_data WHERE date BETWEEN ? AND ?",
        (week_start_str, today_str)
    )[0]

    unique_month = db_fetch_one(
        "SELECT COUNT(DISTINCT user_id) FROM user_data WHERE date BETWEEN ? AND ?",
        (month_start_str, today_str)
    )[0]

    unique_total = db_fetch_one(
        "SELECT COUNT(DISTINCT user_id) FROM user_data"
    )[0]

    text = (
        "📊 *Статистика обращений бота*\n\n"

        "🔹 *Все обращения*\n"
        f"📅 Сегодня: *{today_count}*\n"
        f"📅 Вчера: *{yesterday_count}*\n"
        f"🗓 Последние 7 дней: *{week_count}*\n"
        f"🗓 Последние 30 дней: *{month_count}*\n"
        f"👥 Всего обращений: *{total_count}*\n\n"

        "🔹 *Уникальные пользователи*\n"
        f"👤 Сегодня: *{unique_today}*\n"
        f"👤 Вчера: *{unique_yesterday}*\n"
        f"👤 Последние 7 дней: *{unique_week}*\n"
        f"👤 Последние 30 дней: *{unique_month}*\n"
        f"👤 Всего уникальных: *{unique_total}*\n\n"

        f"🚫 Попыток заблокированных: *{blocked_count}*"
    )

    await message.answer(text, parse_mode="Markdown")

############################################################################################################

# Обработчик команды /export

@dp.message(Command("export"))
async def export_users_to_excel(message: Message):
    user_id = message.from_user.id

    if user_id != admin_id:
        await message.answer("У вас нет доступа к этой команде.")
        return

    rows = db_fetch_all("""
        SELECT user_id, username, full_name, chat_id, date, time
        FROM user_data
        ORDER BY date DESC, time DESC
    """)

    if not rows:
        await message.answer("Журнал обращений пуст.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Журнал обращений"

    # Заголовки
    ws.append(["user_id", "username", "full_name", "chat_id", "date", "time"])

    # Данные
    for row in rows:
        ws.append(row)

    file_name = "users_export.xlsx"
    wb.save(file_name)

    file = FSInputFile(file_name)
    await message.answer_document(
        document=file,
        caption="📄 Экспорт журнала обращений в Excel"
    )

    # удаляем файл после отправки
    if os.path.exists(file_name):
        os.remove(file_name)

############################################################################################################

# ===== Глобальный обработчик ошибок =====
@dp.error()
async def global_error_handler(event: types.ErrorEvent):
    exception = event.exception

    # Перехват BlockedUserException
    if isinstance(exception, BlockedUserException):
        logger.info("BlockedUserException: %s", exception)
        return True  # ошибка обработана, дальше не идём

    # Перехват Telegram Forbidden (бот заблокирован)
    if isinstance(exception, TelegramForbiddenError):
        logger.info("Bot blocked by user: %s", exception)
        return True

    # Остальные ошибки — логируем с трассировкой
    logger.exception("Unhandled exception: %s", exception)
    return False


############################################################################################################
class BlockedUserException(Exception):
    """Исключение для заблокированных пользователей"""
    pass


############################################################################################################

# ФУНКЦИЯ СКРЫТИЯ КНОПОК

async def hide_keyboard(callback: types.CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass



############################################################################################################
############################################################################################################
############################################################################################################

# обработчик команды /start

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

 
    # 1) Проверка чёрного списка
    if user_id in BLACKLIST:
        # 1a) Логируем попытку в БД
        save_user_attempt("user_data.db", user_id, username, full_name, chat_id, reason="blacklisted_start")

        # 1b) Сообщаем пользователю
        await message.answer("🚫 Вы заблокированы за нарушение правил пользования ботом.")

        # 1c) Уведомляем админа (короткое сообщение)
        try:
            admin_text = (
                f"⚠️ Blocked attempt detected\n"
                f"User: {full_name} (@{username or 'no-username'})\n"
                f"User ID: {user_id}\n"
                f"Chat ID: {chat_id}\n"
                f"Action: attempted /start while blacklisted"
            )
            await dp.bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception as e:
            logger.exception("Не удалось отправить уведомление админу: %s", e)

        # 1d) Поднимаем исключение — чтобы централизованный error-handler его обработал (и подавил трассировку)
        raise BlockedUserException(f"Пользователь {user_id} ({full_name}) попытался использовать бота")

    # 2) Сохраняем/обновляем карточку пользователя
    save_user_data(user_id, username, full_name, chat_id)
   
    # 3) Клавиатура главного меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ О боте. Подсказка", callback_data="about_choose")],
        [InlineKeyboardButton(text="💰 Размер взносов в АПМ", callback_data="razm_vzn")],
        [InlineKeyboardButton(text="📜 Решения Совета АПМ № 11, № 13, № 15", callback_data="resh_soveta")],
        [InlineKeyboardButton(text="📜 Рекомендации по защите прав адвокатов", callback_data="lawyer_protection")],
        [InlineKeyboardButton(text="🚕 Стоимость проезда", callback_data="cost")],
        [InlineKeyboardButton(text="💵 Размер вознаграждения", callback_data="reward")],
        [InlineKeyboardButton(text="🔍 Поиск подзащитного в МО", callback_data="find_in_mo")],
        # [InlineKeyboardButton(text="Окончить работу", callback_data="end_work")],
    ])

    await message.answer(f"Здравствуйте, {full_name}!\n\nВыберите опцию:", reply_markup=keyboard)

############################################################################################################

# Обработчик кнопки "О боте. Подсказка"

@dp.callback_query(F.data == "about_choose")
async def handle_about_choose(callback: CallbackQuery):

    new_text = MESSAGE_about["about_bot"]

    await callback.message.answer(new_text)
    await ask_more(callback)

###########################################################################################################

# Обработчик нажатия на кнопку "Размер взносов в АПМ и ФПА"

# Клавиатура с 4 кнопками

@dp.callback_query(F.data == "razm_vzn")
async def handle_razm_vzn(callback: types.CallbackQuery):
   
    # Убираем старые кнопки
    await hide_keyboard(callback)
   
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Размер взноса с 01.01.2024 по 31.03.2024', callback_data='razm_vzn_1')],
            [InlineKeyboardButton(text='Размер взноса с 01.04.2024 по 30.04.2025', callback_data='razm_vzn_2')],
            [InlineKeyboardButton(text='Размер взноса с 01.05.2025', callback_data='razm_vzn_3')],
            [InlineKeyboardButton(text='Размер взноса с 01.07.2025 по 31.03.2026 для приостановленных', callback_data='razm_vzn_3_1')]
            [InlineKeyboardButton(text='Размер взноса с 01.04.2026', callback_data='razm_vzn_4')]
            [InlineKeyboardButton(text='Размер взноса с 01.04.2026 до следующей конференции в 2027 году', callback_data='razm_vzn_4_1')]
        ]
    )
    await callback.message.answer("Выберите размер взноса:", reply_markup=keyboard)



@dp.callback_query(F.data.in_({"razm_vzn_1", "razm_vzn_2", "razm_vzn_3", "razm_vzn_3_1", "razm_vzn_4", "razm_vzn_4_1"}))
async def handle_vzn_amount(callback: types.CallbackQuery):
    
     # Удаляем предыдущие кнопки
    await hide_keyboard(callback)

    amounts = {
        "razm_vzn_1":   "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы составлял 1550 руб.",
        "razm_vzn_2":   "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы составлял 1700 руб.",
        "razm_vzn_3":   "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы составляет 1900 руб.",
        "razm_vzn_3_1": "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы, чей статус адвоката был приостановлен составляет 950 руб.",
        "razm_vzn_4":   "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы составляет 2100 руб.",
        "razm_vzn_4_1": "Размер обязательных отчислений (профессиональные расходы) на общие нужды Адвокатской палаты города Москвы, чей статус адвоката был приостановлен составляет 1050 руб.",
    }    

    if callback.data in amounts:
        response_text = amounts[callback.data]
        await callback.message.answer(response_text)

# В начале 2027 года можно будет включить инлайн кнопку 2027 года
# Если выбрана опция 2025 года, отправляем дополнительное сообщение
#    elif callback.data == "razm_vzn_4":
#        await callback.message.answer(
#        "ℹ Размер взноса будет известен после решения 24-й ежегодной конференции адвокатов "
#        "Адвокатской палаты города Москвы, которая состоится 03 апреля 2027 года."
#        )

    await ask_more(callback)  
    await callback.answer()

###########################################################################################################

# Обработчик нажатия на кнопку "Решения Совета АПМ № 11, № 13, № 15"

@dp.callback_query(lambda callback: callback.data == "resh_soveta")
async def handle_resh_soveta(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Решение Совета № 11", callback_data="resh_soveta_11")],
            [InlineKeyboardButton(text="📄 Решение Совета № 13", callback_data="resh_soveta_13")],
            [InlineKeyboardButton(text="📄 Решение Совета № 15", callback_data="resh_soveta_15")],            
        ]
    )
    await callback.message.edit_text("Выберите файл для загрузки:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda callback: callback.data == "resh_soveta_11")
async def handle_resh_soveta_11(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "_№ 11_Reshenie_Soveta.pdf", "Решение Совета АПМ № 11")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "resh_soveta_13")
async def handle_resh_soveta_13(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "_№ 13_Reshenie_Soveta.pdf", "Решение Совета АПМ № 13")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "resh_soveta_15")
async def handle_resh_soveta_15(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "_№ 15_Reshenie_Soveta.pdf", "Решение Совета АПМ № 15")
    await ask_more(callback)


@dp.callback_query(lambda query: query.data == "lawyer_protection")
async def lawyer_protection(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
            text="Вот ссылка на нужную вам страницу: https://www.advokatymoscow.ru/advocate/legislation/prof-rights-protection/normativnye-akty/13758/"
    )
    await ask_more(callback_query)
    await callback.answer()

###########################################################################################################

# Обработчик нажатия на кнопку "Стоимость проезда"
@dp.callback_query(lambda callback: callback.data == "cost")
async def handle_cost(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[           
            [InlineKeyboardButton(text="Узнать стоимость проезда", callback_data="cost_choose")],
            [InlineKeyboardButton(text="Получить справку о стоимости проезда", callback_data="cost_info")]
        ]
    )
    await callback.message.edit_text("Что вы хотите сделать?", reply_markup=keyboard)
    await callback.answer()

###########################################################################################################

# Обработчик кнопки "Узнать стоимость проезда"
@dp.callback_query(lambda callback: callback.data == "cost_choose")
async def handle_cost_choose(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2026 года", callback_data="cost_2026")],
            [InlineKeyboardButton(text="Стоимость проезда с 01.06.2025 года", callback_data="cost_2025_2")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2025 года", callback_data="cost_2025")],
            [InlineKeyboardButton(text="Стоимость проезда с 20.05.2024 года", callback_data="cost_2024")],
            [InlineKeyboardButton(text="Стоимость проезда с 15.10.2023 года", callback_data="cost_2023_2")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2023 года", callback_data="cost_2023")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2022 года", callback_data="cost_2022")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2021 года", callback_data="cost_2021")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2020 года", callback_data="cost_2020")]
        ]
    )
    await callback.message.edit_text("Выберите период для получения информации о стоимости проезда:", reply_markup=keyboard)
    await callback.answer()

###########################################################################################################

#Обработчик кнопки "Стоимости проезда с 02.01.2026 года"
@dp.callback_query(lambda callback: callback.data == "cost_2026")
async def handle_cost_2025(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2026 года: 90 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 01.06.2025 года"
@dp.callback_query(lambda callback: callback.data == "cost_2025_2")
async def handle_cost_2025(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 01.06.2025 года: 80 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 02.01.2025 года"
@dp.callback_query(lambda callback: callback.data == "cost_2025")
async def handle_cost_2025(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2025 года: 75 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 20.05.2024 года"
@dp.callback_query(lambda callback: callback.data == "cost_2024")
async def handle_cost_2024(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 20.05.2024 года: 70 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 15.10.2023 года"
@dp.callback_query(lambda callback: callback.data == "cost_2023_2")
async def handle_cost_2023_2(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 15.10.2023 года: 65 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 02.01.2023 года"
@dp.callback_query(lambda callback: callback.data == "cost_2023")
async def handle_cost_2023(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2023 года: 62 рубля.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 02.01.2022 года"
@dp.callback_query(lambda callback: callback.data == "cost_2022")
async def handle_cost_2022(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2022 года: 61 рубль.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 02.01.2021 года"
@dp.callback_query(lambda callback: callback.data == "cost_2021")
async def handle_cost_2021(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2021 года: 60 рублей.")
    await ask_more(callback)

#Обработчик кнопки "Стоимости проезда с 02.01.2020 года"
@dp.callback_query(lambda callback: callback.data == "cost_2020")
async def handle_cost_2020(callback: CallbackQuery):
    await callback.message.edit_text("Стоимость проезда с 02.01.2020 года: 57 рублей.")
    await ask_more(callback)

###########################################################################################################

# Обработчик кнопки "Получить справку о стоимости проезда"
@dp.callback_query(lambda callback: callback.data == "cost_info")
async def handle_cost_info(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2026 года", callback_data="info_2026")],
            [InlineKeyboardButton(text="Стоимость проезда с 01.06.2025 года", callback_data="info_2025_2")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2025 года", callback_data="info_2025")],
            [InlineKeyboardButton(text="Стоимость проезда с 20.05.2024 года", callback_data="info_2024")],
            [InlineKeyboardButton(text="Стоимость проезда с 15.10.2023 года", callback_data="info_2023_2")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2023 года", callback_data="info_2023_1")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2022 года", callback_data="info_2022")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2021 года", callback_data="info_2021")],
            [InlineKeyboardButton(text="Стоимость проезда с 02.01.2020 года", callback_data="info_2020")]
        ]
    )
    
    await callback.message.edit_text("Выберите файл для загрузки:", reply_markup=keyboard)
    await callback.answer()

###########################################################################################################
# обработчики кнопок для выдачи файла со стоимостью проезда

@dp.callback_query(lambda callback: callback.data == "info_2026")
async def handle_info_2026(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2026.pdf", "Проезд 2026")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2025_2")
async def handle_info_2025_2(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2025-2.pdf", "Проезд 2025-2")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2025")
async def handle_info_2025(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2025.pdf", "Проезд 2025")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2024")
async def handle_info_2024(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2024.pdf", "Проезд 2024")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2023_2")
async def handle_info_2023_2(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2023-2.pdf", "Проезд 2023-2")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2023_1")
async def handle_info_2023_1(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2023-1.pdf", "Проезд 2023-1")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2022")
async def handle_info_2022(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2022.pdf", "Проезд 2022")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2021")
async def handle_info_2021(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2021.pdf", "Проезд 2021")
    await ask_more(callback)


@dp.callback_query(lambda callback: callback.data == "info_2020")
async def handle_info_2020(callback: CallbackQuery):
    await send_pdf_or_stub(callback, "Проезд_2020.pdf", "Проезд 2020")
    await ask_more(callback)


@dp.callback_query(F.data == "find_in_mo")
async def handle_find_in_mo(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем клавиатуру
    new_text = Message_find_in_mo  # Предполагаем, что это переменная с текстом
    await callback.message.answer(new_text)  # Отправляем текст
    await ask_more(callback)  # Следующий шаг, например, вывод меню

###########################################################################################################

# Обработчик нажатия на кнопку "Размер вознаграждения"

@dp.callback_query(lambda callback: callback.data == "reward")
async def handle_reward(callback: CallbackQuery):
    main_reward_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Скачать таблицу вознаграждений по УПК РФ 2022-2026 года",
                callback_data="reward_pdf"                
            )],
           
            [InlineKeyboardButton(
                text="Вознаграждение по УПК РФ как защитника",
                callback_data="reward_upk"
            )],
            [InlineKeyboardButton(
                text="Вознаграждение по УПК РФ со стороны потерпевшего",
                callback_data="reward_upk_opponent"
            )],
            [InlineKeyboardButton(
                text="Вознаграждение по ГПК РФ/КАС РФ",
                callback_data="reward_gpk_kas"        
            )]
        ]
    )

    await callback.message.edit_text(
        "Какую информацию желаете получить:",
        reply_markup=main_reward_keyboard
    )
    await callback.answer()

# Обработчик кнопки "Скачать таблицу вознаграждений по УПК 2022-2026 года

@dp.callback_query(lambda callback: callback.data == "reward_pdf")
async def handle_reward_pdf(callback: CallbackQuery):
    import os
    from aiogram.types import FSInputFile

    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        base_dir,
        "Вознаграждения адвоката по 51 за 2022-2026 года.pdf"
    )

    if not os.path.isfile(file_path):
        await callback.message.answer(
            "📂 Файл пока недоступен.",
        )
        await callback.answer()
        return

    file = FSInputFile(file_path)

    await callback.message.answer_document(
        document=file,
        caption="Таблица вознаграждений адвоката по ст. 51 УПК РФ (2022–2026 гг.)"
    )

    await callback.answer()
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение по УПК РФ как защитника
@dp.callback_query(lambda callback: callback.data == "reward_upk")
async def show_rewards(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите год вознаграждения:", reply_markup=reward_keyboard)
    await callback.answer()
    
# Завершение обработки кнопки "Вознаграждение по УПК РФ со строне потерпевшего"
@dp.callback_query(lambda callback: callback.data == "reward_upk_opponent")
async def show_rewards(callback: types.CallbackQuery):
      new_text = Message_reward_upk_opponent
      await callback.message.edit_text(new_text)
      await callback.answer()
      await ask_more(callback)

###########################################################################################################

# Клавиатура с кнопками вознаграждений по годам
reward_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Вознаграждение за 2019 год", callback_data="reward_2019")],
        [InlineKeyboardButton(text="Вознаграждение за 2020 год", callback_data="reward_2020")],
        [InlineKeyboardButton(text="Вознаграждение за 2021 год", callback_data="reward_2021")],
        [InlineKeyboardButton(text="Вознаграждение с 01.10.2022 года", callback_data="reward_2022")],
        [InlineKeyboardButton(text="Вознаграждение с 01.10.2023 года", callback_data="reward_2023")],
        [InlineKeyboardButton(text="Вознаграждение с 01.10.2024 года", callback_data="reward_2024")],
        [InlineKeyboardButton(text="Вознаграждение с 01.10.2025 года", callback_data="reward_2025")]
    ]
)

# Обработчик кнопки "Вознаграждение за 2019 год"
@dp.callback_query(lambda callback: callback.data == "reward_2019")
async def handle_reward_2019(callback: CallbackQuery):
    new_text = Message_reward_2019
    await callback.message.edit_text(new_text) 
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение за 2020 год"
@dp.callback_query(lambda callback: callback.data == "reward_2020")
async def handle_cost_2020(callback: CallbackQuery):
    new_text = Message_reward_2020
    await callback.message.edit_text(new_text) 
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение за 2021 год"
@dp.callback_query(lambda callback: callback.data == "reward_2021")
async def handle_cost_2021(callback: CallbackQuery):
    new_text = Message_reward_2021
    await callback.message.edit_text(new_text) 
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение за 2022 год"
@dp.callback_query(lambda callback: callback.data == "reward_2022")
async def handle_cost_2022(callback: CallbackQuery):
    new_text = Message_reward_2022
    await callback.message.edit_text(new_text)
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение за 2023 год"
@dp.callback_query(lambda callback: callback.data == "reward_2023")
async def handle_cost_2023(callback: CallbackQuery):
    new_text = Message_reward_2023    
    await callback.message.edit_text(new_text)
    await ask_more(callback)

# Обработчик кнопки "Вознаграждение за 2024 год"
@dp.callback_query(lambda callback: callback.data == "reward_2024")
async def handle_cost_2024(callback: CallbackQuery):
    new_text = Message_reward_2024
    await callback.message.edit_text(new_text)
    await ask_more(callback)


# Обработчик кнопки "Вознаграждение за 2025 год"
@dp.callback_query(lambda callback: callback.data == "reward_2025")
async def handle_cost_2024(callback: CallbackQuery):
    new_text = Message_reward_2025
    await callback.message.edit_text(new_text)
    await ask_more(callback)

###########################################################################################################

# Обработчик кнопки "Вознаграждение по ГПК РФ/КАС РФ"
@dp.callback_query(lambda callback: callback.data == "reward_gpk_kas")
async def show_rewards(callback: types.CallbackQuery):
      new_text = Message_reward_gpk_kas
      await callback.message.edit_text(new_text)
      await callback.answer()
      await ask_more(callback)

##########################################################################################################

# Обработчик кнопки "Алгоритм поиска задержанного в МО"
@dp.callback_query(lambda callback: callback.data == "find_in_mo")
async def show_rewards(callback: types.CallbackQuery):
    await callback.answer()
    await ask_more(callback)
 
##########################################################################################################

# Обработчик меню "Еще желаете информацию?"
    
async def ask_more(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, хочу", callback_data="yes_more")],
            [InlineKeyboardButton(text="❌ Нет, не хочу", callback_data="no_more")]
        ]
    )
    await callback.message.answer("Желаете еще получить информацию?", reply_markup=keyboard)
    await callback.answer()

###########################################################################################################

# Обработчик кнопки "Да, хочу"
@dp.callback_query(lambda callback: callback.data == "yes_more")
async def handle_yes_more(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
    await send_welcome(callback.message)
    await callback.answer()
    
###########################################################################################################

# Обработчик кнопки "Нет, не хочу"
@dp.callback_query(lambda callback: callback.data == "no_more")
async def handle_no_more(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
       #     [InlineKeyboardButton(text="✍ Оставить отзыв", callback_data="leave_feedback")],
            [InlineKeyboardButton(text="✍ Оставить отзыв", callback_data="end_bot")],
            [InlineKeyboardButton(text="🚪 Завершить работу", callback_data="end_bot")]
        ]
    )
    await callback.message.answer("Вы хотите оставить отзыв о боте?", reply_markup=keyboard)
    await callback.answer()

###########################################################################################################

# Обработчик кнопки "Оставить отзыв"
@dp.callback_query(lambda callback: callback.data == "leave_feedback")
async def handle_feedback_request(callback: CallbackQuery):
    await callback.message.answer("Пожалуйста, напишите ваш отзыв и отправьте его в чат.")
    await callback.answer()

###########################################################################################################

# Обработчик текстового отзыва        
@dp.message()
async def receive_feedback(message: types.Message):
    if message.text:  # Проверяем, что это текст
        feedback = f"📩 Новый отзыв от @{message.from_user.username or message.from_user.id}:\n{message.text}"
        await bot.send_message(admin_id, feedback)  # Отправка админу
        await message.answer(Message_end)  # Отправляем сообщение пользователю

###########################################################################################################

# Обработчик кнопки "Завершить работу"
@dp.callback_query(F.data == "end_bot")
async def handle_end_bot(callback: CallbackQuery):
    await callback.message.edit_text(Message_end)
    await callback.answer()

###########################################################################################################

# Запуск бота
async def main():
    try:
        init_db()
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except BlockedUserException as e:
        print("❌ Заблокированный доступ:", e)

    except KeyboardInterrupt:
        print("Бот остановлен вручную.")

    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
    
###########################################################################################################


# удаление кнопок после нажатия
# await callback_query.message.edit_reply_markup(reply_markup=None)
