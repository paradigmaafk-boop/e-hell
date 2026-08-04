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
    
    # Таблица для хранения связей старых и новых никнеймов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nickname_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating_type TEXT NOT NULL,
            current_nickname TEXT NOT NULL,
            old_nickname TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(rating_type, old_nickname)
        )
    """)
    
    # Таблица для гайдов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Таблицы для разных рейтингов
    rating_types = ['duel', 'reservoir', 'oil']
    
    for rt in rating_types:
        # Таблица игроков (текущие данные)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS players_{rt} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL,
                points INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                UNIQUE(nickname)
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

# ===== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ НИКНЕЙМАМИ =====

def add_nickname_alias(rating_type, current_nickname, old_nickname):
    """Добавляет связь между старым и новым никнеймом"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute("""
            SELECT id FROM nickname_aliases 
            WHERE rating_type = ? AND old_nickname = ?
        """, (rating_type, old_nickname))
        
        if cursor.fetchone():
            cursor.execute("""
                UPDATE nickname_aliases 
                SET current_nickname = ?, created_at = ?
                WHERE rating_type = ? AND old_nickname = ?
            """, (current_nickname, created_at, rating_type, old_nickname))
        else:
            cursor.execute("""
                INSERT INTO nickname_aliases (rating_type, current_nickname, old_nickname, created_at)
                VALUES (?, ?, ?, ?)
            """, (rating_type, current_nickname, old_nickname, created_at))
        
        cursor.execute(f"""
            UPDATE history_{rating_type}
            SET nickname = ?
            WHERE nickname = ?
        """, (current_nickname, old_nickname))
        
        cursor.execute(f"""
            UPDATE players_{rating_type}
            SET nickname = ?
            WHERE nickname = ?
        """, (current_nickname, old_nickname))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding alias: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_nickname_aliases(rating_type):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT current_nickname, old_nickname, created_at
        FROM nickname_aliases
        WHERE rating_type = ?
        ORDER BY created_at DESC
    """, (rating_type,))
    data = cursor.fetchall()
    conn.close()
    return data

def delete_nickname_alias(rating_type, old_nickname):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM nickname_aliases
        WHERE rating_type = ? AND old_nickname = ?
    """, (rating_type, old_nickname))
    conn.commit()
    conn.close()

def resolve_nickname(rating_type, nickname):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT current_nickname
        FROM nickname_aliases
        WHERE rating_type = ? AND old_nickname = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (rating_type, nickname))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else nickname

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С РЕЙТИНГОМ (С СУММИРОВАНИЕМ) =====

def save_rating(rating_type, data_list):
    """Сохраняет рейтинг с СУММИРОВАНИЕМ очков"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for nickname, points in data_list:
        # Пытаемся разрешить никнейм через алиасы
        resolved_nickname = resolve_nickname(rating_type, nickname)
        
        # Проверяем, существует ли игрок
        cursor.execute(f"SELECT id, points FROM players_{rating_type} WHERE nickname = ?", (resolved_nickname,))
        existing = cursor.fetchone()
        
        if existing:
            # СУММИРУЕМ очки: старые + новые
            new_total = existing[1] + points
            cursor.execute(f"""
                UPDATE players_{rating_type} 
                SET points = ?, last_updated = ? 
                WHERE nickname = ?
            """, (new_total, today, resolved_nickname))
        else:
            # Новый игрок - просто сохраняем очки
            cursor.execute(f"""
                INSERT INTO players_{rating_type} (nickname, points, last_updated) 
                VALUES (?, ?, ?)
            """, (resolved_nickname, points, today))
        
        # В историю записываем новую порцию очков (НЕ суммируем!)
        cursor.execute(f"""
            INSERT INTO history_{rating_type} (nickname, points, date) 
            VALUES (?, ?, ?)
        """, (resolved_nickname, points, today))
    
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
    """Получает историю средних значений по всем игрокам за каждую неделю"""
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

def get_total_weeks_for_player(rating_type, nickname):
    """Получает количество недель, в которых участвовал игрок"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT COUNT(DISTINCT date) 
        FROM history_{rating_type} 
        WHERE nickname = ?
    """, (nickname,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count or 0

def get_player_average_points(rating_type, nickname):
    """Получает среднее значение очков игрока за все недели"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT AVG(points) 
        FROM history_{rating_type} 
        WHERE nickname = ?
    """, (nickname,))
    
    avg = cursor.fetchone()[0]
    conn.close()
    return round(avg, 1) if avg else 0

def reset_rating(rating_type):
    """Сброс рейтинга (очищает все данные для конкретного типа)"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"DELETE FROM players_{rating_type}")
        cursor.execute(f"DELETE FROM history_{rating_type}")
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resetting rating: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_player(rating_type, nickname):
    """Полностью удаляет игрока и всю его историю из рейтинга"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        # Удаляем из таблицы игроков
        cursor.execute(f"DELETE FROM players_{rating_type} WHERE nickname = ?", (nickname,))
        
        # Удаляем всю историю игрока
        cursor.execute(f"DELETE FROM history_{rating_type} WHERE nickname = ?", (nickname,))
        
        # Удаляем все связи псевдонимов, связанные с этим игроком
        cursor.execute("""
            DELETE FROM nickname_aliases 
            WHERE rating_type = ? AND (current_nickname = ? OR old_nickname = ?)
        """, (rating_type, nickname, nickname))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting player: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ГАЙДАМИ =====

def create_guide(title, content):
    """Создает новый гайд"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute("""
            INSERT INTO guides (title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (title, content, now, now))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error creating guide: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_all_guides():
    """Получает все гайды"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, content, created_at, updated_at
        FROM guides
        ORDER BY created_at DESC
    """)
    
    data = cursor.fetchall()
    conn.close()
    return data

def get_guide_by_id(guide_id):
    """Получает гайд по ID"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, content, created_at, updated_at
        FROM guides
        WHERE id = ?
    """, (guide_id,))
    
    data = cursor.fetchone()
    conn.close()
    return data

def update_guide(guide_id, title, content):
    """Обновляет гайд"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute("""
            UPDATE guides
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ?
        """, (title, content, now, guide_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating guide: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_guide(guide_id):
    """Удаляет гайд"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM guides WHERE id = ?", (guide_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting guide: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_rating_types():
    return [
        {'id': 'duel', 'name': 'Дуэль', 'icon': '⚔️', 'color': '#ff5500'},
        {'id': 'reservoir', 'name': 'Резервуар', 'icon': '💧', 'color': '#2196F3'},
        {'id': 'oil', 'name': 'Нефть', 'icon': '🛢️', 'color': '#2c1810'}
    ]

def get_rating_display_name(rating_type):
    names = {
        'duel': 'Дуэль',
        'reservoir': 'Резервуар',
        'oil': 'Нефть'
    }
    return names.get(rating_type, rating_type)
