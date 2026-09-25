import os
import psycopg2
import psycopg2.extras
import hashlib
from datetime import datetime

DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nickname_aliases (
            id SERIAL PRIMARY KEY,
            rating_type TEXT NOT NULL,
            current_nickname TEXT NOT NULL,
            old_nickname TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(rating_type, old_nickname)
        )
    """)
    
    rating_types = ['duel']
    for rt in rating_types:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS players_{rt} (
                id SERIAL PRIMARY KEY,
                nickname TEXT NOT NULL,
                points INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                UNIQUE(nickname)
            )
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS history_{rt} (
                id SERIAL PRIMARY KEY,
                nickname TEXT NOT NULL,
                points INTEGER NOT NULL,
                date TEXT NOT NULL
            )
        """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacation_log (
            id SERIAL PRIMARY KEY,
            player_name TEXT NOT NULL,
            comment TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            value INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carousel_slides (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content TEXT NOT NULL,
            media_type TEXT DEFAULT 'image',
            media_url TEXT,
            position INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_map (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    hashed = hashlib.sha256('admin123'.encode()).hexdigest()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING",
            ('admin', hashed)
        )
    except:
        pass
    
    conn.commit()
    conn.close()

def check_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s",
                   (username, hashlib.sha256(password.encode()).hexdigest()))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def add_nickname_alias(rating_type, current_nickname, old_nickname):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("SELECT id FROM nickname_aliases WHERE rating_type = %s AND old_nickname = %s",
                       (rating_type, old_nickname))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""UPDATE nickname_aliases SET current_nickname = %s, created_at = %s
                              WHERE rating_type = %s AND old_nickname = %s""",
                           (current_nickname, created_at, rating_type, old_nickname))
        else:
            cursor.execute("""INSERT INTO nickname_aliases (rating_type, current_nickname, old_nickname, created_at)
                              VALUES (%s, %s, %s, %s)""",
                           (rating_type, current_nickname, old_nickname, created_at))
        cursor.execute(f"UPDATE history_{rating_type} SET nickname = %s WHERE nickname = %s",
                       (current_nickname, old_nickname))
        cursor.execute(f"UPDATE players_{rating_type} SET nickname = %s WHERE nickname = %s",
                       (current_nickname, old_nickname))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding alias: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_nickname_aliases(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT current_nickname, old_nickname, created_at FROM nickname_aliases
                      WHERE rating_type = %s ORDER BY created_at DESC""", (rating_type,))
    data = cursor.fetchall()
    conn.close()
    return data

def delete_nickname_alias(rating_type, old_nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nickname_aliases WHERE rating_type = %s AND old_nickname = %s",
                   (rating_type, old_nickname))
    conn.commit()
    conn.close()

def resolve_nickname(rating_type, nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT current_nickname FROM nickname_aliases
                      WHERE rating_type = %s AND old_nickname = %s
                      ORDER BY created_at DESC LIMIT 1""", (rating_type, nickname))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else nickname

def save_rating(rating_type, data_list):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for nickname, points in data_list:
        resolved_nickname = resolve_nickname(rating_type, nickname)
        cursor.execute(f"SELECT id, points FROM players_{rating_type} WHERE nickname = %s", (resolved_nickname,))
        existing = cursor.fetchone()
        if existing:
            new_total = existing[1] + points
            cursor.execute(f"""UPDATE players_{rating_type} SET points = %s, last_updated = %s
                               WHERE nickname = %s""", (new_total, today, resolved_nickname))
        else:
            cursor.execute(f"""INSERT INTO players_{rating_type} (nickname, points, last_updated)
                               VALUES (%s, %s, %s)""", (resolved_nickname, points, today))
        cursor.execute(f"""INSERT INTO history_{rating_type} (nickname, points, date)
                           VALUES (%s, %s, %s)""", (resolved_nickname, points, today))
    conn.commit()
    conn.close()

def get_latest_rating(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT nickname, points FROM players_{rating_type} ORDER BY points DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def get_player_history(rating_type, nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT date, points FROM history_{rating_type} WHERE nickname = %s ORDER BY date ASC",
                   (nickname,))
    data = cursor.fetchall()
    conn.close()
    return data

def get_all_players(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT nickname FROM players_{rating_type} ORDER BY nickname")
    data = cursor.fetchall()
    conn.close()
    return [row[0] for row in data]

def get_average_history(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""SELECT date, AVG(points) as avg_points FROM history_{rating_type}
                       GROUP BY date ORDER BY date ASC""")
    data = cursor.fetchall()
    conn.close()
    return data

def get_underperforming(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT MAX(date) FROM history_{rating_type}")
    last_date = cursor.fetchone()
    last_date = last_date[0] if last_date else None
    if not last_date:
        conn.close()
        return [], None
    cursor.execute(f"SELECT AVG(points) FROM history_{rating_type} WHERE date = %s", (last_date,))
    avg_points = cursor.fetchone()
    avg_points = avg_points[0] if avg_points else None
    if avg_points is None:
        conn.close()
        return [], None
    cursor.execute(f"""SELECT nickname, points FROM history_{rating_type}
                       WHERE date = %s AND points < %s ORDER BY points ASC""", (last_date, avg_points))
    underperformers = cursor.fetchall()
    conn.close()
    return underperformers, round(avg_points, 1)

def get_consistently_underperforming(rating_type, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        WITH daily_avg AS (
            SELECT date, AVG(points) as avg_points FROM history_{rating_type} GROUP BY date
        ),
        underperformers AS (
            SELECT h.nickname, h.date FROM history_{rating_type} h
            JOIN daily_avg da ON h.date = da.date
            WHERE h.points < da.avg_points
        )
        SELECT nickname, COUNT(*) as count FROM underperformers
        GROUP BY nickname ORDER BY count DESC LIMIT %s
    """, (limit,))
    data = cursor.fetchall()
    conn.close()
    return data

def get_total_weeks(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(DISTINCT date) FROM history_{rating_type}")
    total = cursor.fetchone()
    total = total[0] if total else 0
    conn.close()
    return total or 0

def get_all_time_leaders(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""SELECT nickname, SUM(points) as total_points FROM history_{rating_type}
                       GROUP BY nickname ORDER BY total_points DESC LIMIT 3""")
    data = cursor.fetchall()
    conn.close()
    return data

def reset_rating(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM players_{rating_type}")
        cursor.execute(f"DELETE FROM history_{rating_type}")
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_player(rating_type, nickname):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM players_{rating_type} WHERE nickname = %s", (nickname,))
        cursor.execute(f"DELETE FROM history_{rating_type} WHERE nickname = %s", (nickname,))
        cursor.execute("DELETE FROM nickname_aliases WHERE rating_type = %s AND (current_nickname = %s OR old_nickname = %s)",
                       (rating_type, nickname, nickname))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting player: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_rating_types():
    return [
        {'id': 'duel', 'name': 'Дуэль', 'icon': '⚔️', 'color': '#ff8a1f'}
    ]

def get_rating_display_name(rating_type):
    names = {'duel': 'Дуэль'}
    return names.get(rating_type, rating_type)

def add_vacation_record(player_name, comment, start_date, end_date, created_by):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO vacation_log (player_name, comment, start_date, end_date, created_at, created_by)
                          VALUES (%s, %s, %s, %s, %s, %s)""",
                       (player_name, comment, start_date, end_date, created_at, created_by))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding vacation record: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_vacation_records():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, player_name, comment, start_date, end_date, created_at, created_by
                      FROM vacation_log ORDER BY created_at DESC""")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_vacation_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM vacation_log WHERE id = %s", (record_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting vacation record: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ===== КАРУСЕЛЬ =====

def create_slide(title, content, media_type, media_url, position):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO carousel_slides (title, content, media_type, media_url, position, is_active, created_at, updated_at)
                          VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s) RETURNING id""",
                       (title, content, media_type, media_url, position, now, now))
        slide_id = cursor.fetchone()[0]
        conn.commit()
        return slide_id
    except Exception as e:
        print(f"Error creating slide: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_all_slides(only_active=False):
    conn = get_connection()
    cursor = conn.cursor()
    if only_active:
        cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at
                          FROM carousel_slides WHERE is_active = TRUE
                          ORDER BY position ASC, id ASC""")
    else:
        cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at
                          FROM carousel_slides ORDER BY position ASC, id ASC""")
    data = cursor.fetchall()
    conn.close()
    return data

def get_slide_by_id(slide_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at
                      FROM carousel_slides WHERE id = %s""", (slide_id,))
    data = cursor.fetchone()
    conn.close()
    return data

def update_slide(slide_id, title, content, media_type, media_url, position, is_active):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""UPDATE carousel_slides SET title = %s, content = %s, media_type = %s,
                          media_url = %s, position = %s, is_active = %s, updated_at = %s WHERE id = %s""",
                       (title, content, media_type, media_url, position, is_active, now, slide_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating slide: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_slide(slide_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM carousel_slides WHERE id = %s", (slide_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting slide: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ===== КАРТА БОЯ (РЕЗЕРВУАР) =====

def get_all_map_values():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM reservoir_map")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in data}

def save_map_values(data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        for key, value in data_dict.items():
            cursor.execute("""
                INSERT INTO reservoir_map (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
            """, (key, value, now, value, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving map values: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def reset_map_values():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reservoir_map")
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resetting map: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
