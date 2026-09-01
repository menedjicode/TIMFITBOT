import telebot
from telebot import types
import sqlite3
import config
from datetime import datetime, timedelta
from db_helper import update_slots_status
from db_helper import clear_past_bookings  # 👈 ИМПОРТ


ITEMS_PER_PAGE = 3  # Сколько тренеров на странице

bot = telebot.TeleBot(config.BOT_TOKEN)
user_data = {}

def get_all_trainers():
    conn = sqlite3.connect('timfitbot.sql')
    cur = conn.cursor()
    cur.execute('SELECT id, name, about FROM coaches WHERE is_active = 1 ORDER BY id ASC')
    trainers = cur.fetchall()
    conn.close()
    return trainers

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_data[user_id] = {}


    conn = sqlite3.connect('timfitbot.sql')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,name VARCHAR(50),time INTEGER,coach VARCHAR(50),date VARCHAR(20),telegram_id INTEGER, UNIQUE(telegram_id, date, time))')
    cur.execute('''
           CREATE TABLE IF NOT EXISTS coaches (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               telegram_id INTEGER UNIQUE,
               name VARCHAR(100),
               about TEXT,
               is_active INTEGER DEFAULT 1
           )
       ''')

    conn.commit()

    cur.close()
    conn.close()

    cleared = clear_past_bookings()
    if cleared > 0:
        print(f"🗑️ Удалено {cleared} прошедших записей")

    markup = types.InlineKeyboardMarkup(row_width=2)

    appoint = types.InlineKeyboardButton('📝 Записаться', callback_data='appoint')
    coaches = types.InlineKeyboardButton('👨‍🏫 Тренеры', callback_data='coaches')

    markup.row(appoint, coaches)
    markup.row(types.InlineKeyboardButton('📋 Мои записи', callback_data='list'))
    markup.row(types.InlineKeyboardButton('📊 Мои тренировки', callback_data='history'))

    bot.send_message(message.chat.id, '👋 Здравствуйте!\n\nВы можете записаться к тренеру или посмотреть информацию о тренерах.', reply_markup=markup)


def show_coaches_list(call, page=0):
    """Показывает список тренеров с пагинацией"""
    user_id = call.message.chat.id

    trainers = get_all_trainers()

    if not trainers:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))
        bot.edit_message_text(
            '😕 Пока нет тренеров.',
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return

    total_pages = (len(trainers) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, len(trainers))
    page_trainers = trainers[start:end]

    text = f'🏋️ *Выберите тренера:*\n\n'

    markup = types.InlineKeyboardMarkup(row_width=1)
    for trainer in page_trainers:
        markup.add(
            types.InlineKeyboardButton(
                f'👤 {trainer[1]}',
                callback_data=f'coach_info_{trainer[0]}'
            )
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'booking_page_{page - 1}'))

    nav_buttons.append(types.InlineKeyboardButton(f'📄 {page + 1}/{total_pages}', callback_data='none'))

    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton('Вперед ➡️', callback_data=f'booking_page_{page + 1}'))

    markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton('🔙 В меню', callback_data='back'))

    bot.edit_message_text(
        text,
        user_id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)
def show_coach_info(call, trainer_id):
    user_id = call.message.chat.id
    conn = sqlite3.connect('timfitbot.sql')
    cur = conn.cursor()
    cur.execute('SELECT name, about FROM coaches WHERE id = ?', (trainer_id,))
    trainer = cur.fetchone()
    conn.close()

    if not trainer:
        bot.answer_callback_query(call.id, '❌ Тренер не найден')
        return

    text = f'👤 *{trainer[0]}*\n\n'
    if trainer[1]:
        text += f'📝 *О себе:*\n{trainer[1]}\n'
    else:
        text += '📝 Тренер пока не добавил информацию о себе.'

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('🔙 Назад к списку', callback_data='back_to_coaches'))
    markup.add(types.InlineKeyboardButton('📝 Записаться', callback_data=f'appoint_trainer_{trainer_id}'))

    bot.edit_message_text(
        text,
        user_id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def show_trainers_for_booking(call, page=0):
    """Показывает список тренеров для записи с пагинацией"""
    user_id = call.message.chat.id

    trainers = get_all_trainers()

    if not trainers:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))
        bot.edit_message_text(
            '😕 Пока нет доступных тренеров.',
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        return

    total_pages = (len(trainers) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, len(trainers))
    page_trainers = trainers[start:end]

    text = f'🏋️ *Выберите тренера:* (страница {page + 1}/{total_pages})\n\n'
    for trainer in page_trainers:
        text += f'👤 {trainer[1]}\n'

    markup = types.InlineKeyboardMarkup(row_width=1)
    for trainer in page_trainers:
        markup.add(
            types.InlineKeyboardButton(
                f'👤 {trainer[1]}',
                callback_data=f'book_trainer_{trainer[0]}'
            )
        )

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'booking_page_{page - 1}'))

    nav_buttons.append(types.InlineKeyboardButton(f'📄 {page + 1}/{total_pages}', callback_data='none'))

    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton('Вперед ➡️', callback_data=f'booking_page_{page + 1}'))

    markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton('🔙 В меню', callback_data='back'))

    bot.edit_message_text(
        text,
        user_id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


def show_slots_for_booking(call, trainer_id):
    """Показывает свободные слоты для записи"""
    user_id = call.message.chat.id

    conn = sqlite3.connect('annika.sql')
    cur = conn.cursor()
    cur.execute('SELECT name FROM coaches WHERE id = ?', (trainer_id,))
    trainer = cur.fetchone()
    conn.close()

    if not trainer:
        bot.answer_callback_query(call.id, '❌ Тренер не найден')
        return

    conn = sqlite3.connect('coaches.sql')
    cur = conn.cursor()
    cur.execute('''
        SELECT date, time FROM schedule 
        WHERE coach_id = (SELECT id FROM coaches WHERE name = ?)
        AND is_booked = 0
        AND date >= date('now')
        ORDER BY date, time
        LIMIT 10
    ''', (trainer[0],))

    slots = cur.fetchall()
    conn.close()

    if not slots:
        bot.send_message(
            user_id,
            f'😔 У тренера *{trainer[0]}* нет свободного времени.',
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return

    user_data[user_id]['coach_name'] = trainer[0]
    user_data[user_id]['trainer_id'] = trainer_id

    markup = types.InlineKeyboardMarkup(row_width=2)
    for slot in slots:
        markup.add(
            types.InlineKeyboardButton(
                f'📅 {slot[0]} 🕐 {slot[1]}:00',
                callback_data=f'slot_{trainer_id}_{slot[0]}_{slot[1]}'
            )
        )
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data=f'back_to_booking'))

    bot.edit_message_text(
        f'📅 *Свободное время для записи к {trainer[0]}:*\n\nВыберите время:',
        user_id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    elif call.data == 'none':
        bot.answer_callback_query(call.id)
        return
    elif call.data == 'appoint':
        show_trainers_for_booking(call, 0)
    elif call.data == 'coaches':
        show_coaches_list(call, 0)
    elif call.data == 'back':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('📝 Записаться', callback_data='appoint'),
            types.InlineKeyboardButton('👨‍🏫 Тренеры', callback_data='coaches'),
            types.InlineKeyboardButton('📋 Мои записи', callback_data='list'),
            types.InlineKeyboardButton('📊 Мои тренировки', callback_data='history')
        )
        bot.edit_message_text(
            '👋 Здравствуйте!\n\nВыберите действие:',
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    elif call.data == 'back_to_coaches':
        show_coaches_list(call, 0)
    elif call.data == 'back_to_booking':
        show_trainers_for_booking(call, 0)
    elif call.data.startswith('coaches_page_'):
        page = int(call.data.split('_')[2])
        show_coaches_list(call, page)
    elif call.data.startswith('booking_page_'):
        page = int(call.data.split('_')[2])
        show_trainers_for_booking(call, page)

    elif call.data.startswith('coach_info_'):
        trainer_id = int(call.data.split('_')[2])
        show_coach_info(call, trainer_id)

    elif call.data.startswith('book_trainer_'):
        trainer_id = int(call.data.split('_')[2])
        show_slots_for_booking(call, trainer_id)

    elif call.data.startswith('appoint_trainer_'):
        trainer_id = int(call.data.split('_')[2])
        show_slots_for_booking(call, trainer_id)



    elif call.data == 'list':
        conn = sqlite3.connect('annika.sql')
        cur = conn.cursor()

        cur.execute('SELECT id, name, coach, date, time FROM users WHERE telegram_id = ? ORDER BY date DESC', (user_id,))

        bookings = cur.fetchall()
        conn.close()

        if not bookings:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))
            bot.edit_message_text(
                '📋 У вас пока нет записей.\n\nХотите записаться? Введите "/start"',
                user_id,
                call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
        else:
            text = '📋 *Все записи:*\n\n'
            for booking in bookings:
                text += f'🔹 #{booking[0]}\n'
                text += f'   👤 {booking[1]}\n'
                text += f'   🏋️ {booking[2]}\n'
                text += f'   📅 {booking[3]}\n'
                text += f'   🕐 {booking[4]}:00\n\n'
            markup = types.InlineKeyboardMarkup(row_width=1)
            for booking in bookings:
                markup.add(
                    types.InlineKeyboardButton(
                        f'❌ Отменить запись #{booking[0]}',
                        callback_data=f'cancel_booking_{booking[0]}'
                    )
                )
            markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))

            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id)

    elif call.data.startswith('cancel_booking_'):
        booking_id = int(call.data.split('_')[2])

        conn = sqlite3.connect('annika.sql')
        cur = conn.cursor()

        cur.execute('SELECT id, name, coach, date, time, telegram_id FROM users WHERE id = ?', (booking_id,))
        booking = cur.fetchone()

        if not booking:
            bot.answer_callback_query(call.id, '❌ Запись не найдена')
            return

        # Удаляем запись
        cur.execute('DELETE FROM users WHERE id = ?', (booking_id,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, f'✅ Запись #{booking_id} отменена!')

        # Возвращаемся в главное меню
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('📝 Записаться', callback_data='appoint'),
            types.InlineKeyboardButton('👨‍🏫 Тренеры', callback_data='coaches'),
            types.InlineKeyboardButton('📋 Мои записи', callback_data='list'),
            types.InlineKeyboardButton('📊 Мои тренировки', callback_data='history')
        )

        bot.edit_message_text(
            f'✅ Запись #{booking_id} успешно отменена!\n\n'
            f'👤 {booking[1]}\n'
            f'🏋️ {booking[2]}\n'
            f'📅 {booking[3]}\n'
            f'🕐 {booking[4]}:00\n\n'
            f'Что хотите сделать дальше?',
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
    elif call.data.startswith('slot_'):
        _, trainer_id, date, time = call.data.split('_')
        trainer_id = int(trainer_id)
        time = int(time)

        conn = sqlite3.connect('annika.sql')
        cur = conn.cursor()
        cur.execute('SELECT name FROM coaches WHERE id = ?', (trainer_id,))
        trainer = cur.fetchone()

        if not trainer:
            bot.answer_callback_query(call.id, '❌ Тренер не найден')
            conn.close()
            return

        try:
            cur.execute('''
                    INSERT INTO users (name, time, coach, date, telegram_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (call.message.chat.first_name, time, trainer[0], date, user_id))
            conn.commit()
            update_slots_status()
        except sqlite3.IntegrityError:
            bot.send_message(user_id, '⚠️ Это время уже занято!')
            conn.close()
            bot.answer_callback_query(call.id)
            return

        conn.close()

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('📋 Мои записи', callback_data='list'))
        markup.add(types.InlineKeyboardButton('🔙 В меню', callback_data='back'))

        bot.edit_message_text(
            f'✅ *Вы записались!*\n\n'
            f'👤 Тренер: {trainer[0]}\n'
            f'📅 Дата: {date}\n'
            f'🕐 Время: {time}:00',
            user_id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'history':
        user_id = call.message.chat.id
        page = 0  # Можно передавать как параметр

        ITEMS_PER_PAGE = 10

        conn = sqlite3.connect('annika.sql')
        cur = conn.cursor()

        today = datetime.now().strftime('%d.%m.%Y')

        # Сначала считаем общее количество
        cur.execute('SELECT COUNT(*) FROM users WHERE telegram_id = ?', (user_id,))
        total = cur.fetchone()[0]

        # Потом берём страницу
        offset = page * ITEMS_PER_PAGE
        cur.execute('''
                SELECT coach, date, time FROM users 
                WHERE telegram_id = ?
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            ''', (user_id, ITEMS_PER_PAGE, offset))

        bookings = cur.fetchall()

        # Считаем статистику
        total = len(bookings)
        completed = 0
        upcoming = 0

        for booking in bookings:
            if booking[1] < today:  # booking[1] = date
                completed += 1
            else:
                upcoming += 1

        conn.close()
        markup = types.InlineKeyboardMarkup(row_width=2)

        if not bookings:
            markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))
            bot.edit_message_text('📊 У вас пока нет записей.', user_id, call.message.message_id, reply_markup=markup)
            bot.answer_callback_query(call.id)
            return

        text = f'📊 *Мои тренировки ({total})*\n\n'
        text += f'Всего: {total} | ✅ {completed} | ⏳ {upcoming}\n\n'

        for booking in bookings:
            coach_name, date, time = booking
            status = '✅' if date < today else '⏳'
            text += f'{status} {date} | {time}:00 | {coach_name}\n'



        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton('⬅️', callback_data=f'history_page_{page - 1}'))
        nav_buttons.append(
            types.InlineKeyboardButton(f'{page + 1}/{(total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE}',
                                       callback_data='none'))
        if (page + 1) * ITEMS_PER_PAGE < total:
            nav_buttons.append(types.InlineKeyboardButton('➡️', callback_data=f'history_page_{page + 1}'))

        if nav_buttons:
            markup.row(*nav_buttons)

        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))

        bot.edit_message_text(
            text,
            user_id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)

    elif call.data == 'cancel':
        user_data[user_id] = {}
        markup = types.InlineKeyboardMarkup(row_width=2)
        appoint = types.InlineKeyboardButton('📝 Записаться', callback_data='appoint')
        coaches = types.InlineKeyboardButton('👨‍🏫 Тренеры', callback_data='coaches')
        markup.row(appoint, coaches)
        markup.row(types.InlineKeyboardButton('📋 Мои записи', callback_data='list'))
        markup.row(types.InlineKeyboardButton('📊 Мои тренировки', callback_data='history'))

        bot.edit_message_text(
            '❌ Запись отменена\n\nЧто хотите сделать?',
            user_id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)



def process_name(message):
    user_id = message.chat.id

    if user_id not in user_data or not user_data[user_id]:
        bot.send_message(user_id, '❌ Что-то пошло не так. Нажмите /start')
        return

    user_data[user_id]['name'] = message.text

    try:
        conn = sqlite3.connect('annika.sql')
        cur = conn.cursor()

        coach_map = {
            '1': 'Леонардо ДиКаприо',
            '2': 'Брэд Питт',
            '3': 'Джонни Депп'
        }
        #сюда импортирую бд

        coach_name = coach_map.get(user_data[user_id]['coach'], 'Неизвестный тренер')
        date_str = user_data[user_id]['date']
        time_int = user_data[user_id]['time']
        name = user_data[user_id]['name']
        telegram_id = user_data[user_id]['telegram_id']
        try:
            cur.execute(
                'INSERT INTO users (name, time, coach, date, telegram_id) VALUES (?, ?, ?, ?, ?)',
                (name, time_int, coach_name, date_str, telegram_id)
            )
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id,'Время занято, либо вы уже записаны на это время')
            return
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton('🔄 Новая запись', callback_data='appoint'))
        markup.row(types.InlineKeyboardButton('Меню', callback_data='back'))
        bot.send_message(
            user_id,
            f'✅ *Запись успешно создана!*\n\n'
            f'👤 Тренер: {coach_name}\n'
            f'📅 Дата: {date_str}\n'
            f'🕐 Время: {time_int}:00\n'
            f'✍️ Имя: {name}\n\n'
            f'Спасибо! Мы свяжемся с вами!',
            reply_markup=markup,
            parse_mode='Markdown'
        )

        user_data[user_id] = {}

    except Exception as e:
        bot.send_message(user_id, f'❌ Ошибка: {str(e)}')



bot.polling(none_stop=True)
