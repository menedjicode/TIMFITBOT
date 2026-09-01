import sqlite3
from datetime import datetime


def clear_past_bookings():
    """Удаляет прошедшие записи и освобожждает слоты"""

    today = datetime.now().strftime('%d.%m.%Y')

    # 1. Находим прошедшие записи в annika.sql
    conn_clients = sqlite3.connect('annika.sql')
    cur_clients = conn_clients.cursor()

    cur_clients.execute('''
        SELECT id, coach, date, time 
        FROM users 
        WHERE date < ?
    ''', (today,))

    past_bookings = cur_clients.fetchall()

    if not past_bookings:
        conn_clients.close()
        return 0

    # 2. Освобождаем слоты в coaches.sql
    conn_coaches = sqlite3.connect('coaches.sql')
    cur_coaches = conn_coaches.cursor()

    for booking in past_bookings:
        booking_id, coach_name, date, time = booking
        cur_coaches.execute('''
            UPDATE schedule 
            SET is_booked = 0 
            WHERE coach_id = (SELECT id FROM coaches WHERE name = ?)
            AND date = ? AND time = ?
        ''', (coach_name, date, time))

    # 3. Удаляем прошедшие записи
    cur_clients.execute('DELETE FROM users WHERE date < ?', (today,))

    conn_clients.commit()
    conn_coaches.commit()
    conn_clients.close()
    conn_coaches.close()

    return len(past_bookings)

def update_slots_status():
    # 1. Подключаемся к coaches.sql (БД тренеров)
    conn_coaches = sqlite3.connect('coaches.sql')
    cur_coaches = conn_coaches.cursor()

    # 2. Подключаемся к annika.sql (БД клиентов)
    conn_clients = sqlite3.connect('annika.sql')
    cur_clients = conn_clients.cursor()

    # 3. Сбрасываем все слоты в 0 (свободны)
    cur_coaches.execute('UPDATE schedule SET is_booked = 0')

    # 4. Получаем все записи клиентов
    cur_clients.execute('SELECT coach, date, time FROM users')
    bookings = cur_clients.fetchall()

    # 5. Для каждой записи помечаем соответствующий слот как занятый
    for booking in bookings:
        coach_name = booking[0]
        date = booking[1]
        time = booking[2]

        cur_coaches.execute('''
            UPDATE schedule 
            SET is_booked = 1 
            WHERE coach_id = (SELECT id FROM coaches WHERE name = ?)
            AND date = ? AND time = ?
        ''', (coach_name, date, time))

    conn_coaches.commit()
    conn_coaches.close()
    conn_clients.close()

    print("✅ Статусы слотов обновлены")