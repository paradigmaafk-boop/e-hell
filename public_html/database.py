import sqlite3
import hashlib
from datetime import datetime

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Таблица пользователей (для входа)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL
        )
    """)
    
    # Таблицы для разных рейтингов
    rating_types = ['duel', 'reservoir', 'oil', 'power']
    
    for rt in rating_types:
        # Таблица игроков (текущие данные)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS players_{rt} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                points INTEGER NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Таблица истории
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS history_{rt} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                points INTEGER NOT NULL,
                date TEXT NOT NULL
            )
        """)
    
    # Создаем админа
    hashed = hashlib.sha256('admin123'.encode()).hexdigest()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed))
    except:
        pass
    
    conn.commit()
    conn.close()

def check_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                   (username, hashlib.sha256(password.encode()).hexdigest()))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def save_rating(rating_type, data_list):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for nickname, points in data_list:
        cursor.execute(f"SELECT id FROM players_{rating_type} WHERE nickname = ?", (nickname,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute(f"""
                UPDATE players_{rating_type} 
                SET points = ?, last_updated = ? 
                WHERE nickname = ?
            """, (points, today, nickname))
        else:
            cursor.execute(f"""
                INSERT INTO players_{rating_type} (nickname, points, last_updated) 
                VALUES (?, ?, ?)
            """, (nickname, points, today))
        
        cursor.execute(f"""
            INSERT INTO history_{rating_type} (nickname, points, date) 
            VALUES (?, ?, ?)
        """, (nickname, points, today))
    
    conn.commit()
    conn.close()

def get_latest_rating(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT nickname, points 
        FROM players_{rating_type} 
        ORDER BY points DESC
    """)
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_player_history(rating_type, nickname):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT date, points 
        FROM history_{rating_type} 
        WHERE nickname = ? 
        ORDER BY date ASC
    """, (nickname,))
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_all_players(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT nickname FROM players_{rating_type} ORDER BY nickname")
    data = cursor.fetchall()
    conn.close()
    return [row[0] for row in data]

def get_average_history(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT date, AVG(points) as avg_points
        FROM history_{rating_type}
        GROUP BY date
        ORDER BY date ASC
    """)
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_underperforming(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT MAX(date) FROM history_{rating_type}")
    last_date = cursor.fetchone()[0]
    
    if not last_date:
        conn.close()
        return [], None
    
    cursor.execute(f"""
        SELECT AVG(points) 
        FROM history_{rating_type} 
        WHERE date = ?
    """, (last_date,))
    
    avg_points = cursor.fetchone()[0]
    
    if avg_points is None:
        conn.close()
        return [], None
    
    cursor.execute(f"""
        SELECT nickname, points 
        FROM history_{rating_type} 
        WHERE date = ? AND points < ?
        ORDER BY points ASC
    """, (last_date, avg_points))
    
    underperformers = cursor.fetchall()
    conn.close()
    
    return underperformers, round(avg_points, 1)

def get_consistently_underperforming(rating_type, limit=10):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        WITH daily_avg AS (
            SELECT date, AVG(points) as avg_points
            FROM history_{rating_type}
            GROUP BY date
        ),
        underperformers AS (
            SELECT h.nickname, h.date
            FROM history_{rating_type} h
            JOIN daily_avg da ON h.date = da.date
            WHERE h.points < da.avg_points
        )
        SELECT nickname, COUNT(*) as count
        FROM underperformers
        GROUP BY nickname
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_total_weeks(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(DISTINCT date) FROM history_{rating_type}")
    total = cursor.fetchone()[0]
    
    conn.close()
    return total or 0

def get_all_time_leaders(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT nickname, SUM(points) as total_points
        FROM history_{rating_type}
        GROUP BY nickname
        ORDER BY total_points DESC
        LIMIT 3
    """)
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_all_rating_types():
    return [
        {'id': 'duel', 'name': 'Дуэль', 'icon': '⚔️', 'color': '#ff5500'},
        {'id': 'reservoir', 'name': 'Резервуар', 'icon': '💧', 'color': '#2196F3'},
        {'id': 'oil', 'name': 'Нефть', 'icon': '🛢️', 'color': '#2c1810'},
        {'id': 'power', 'name': 'Личная мощь', 'icon': '💪', 'color': '#4CAF50'}
    ]

def get_rating_display_name(rating_type):
    names = {
        'duel': 'Дуэль',
        'reservoir': 'Резервуар',
        'oil': 'Нефть',
        'power': 'Личная мощь'
    }
    return names.get(rating_type, rating_type)