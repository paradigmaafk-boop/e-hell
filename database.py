import os
import psycopg2
import psycopg2.extras
import hashlib
from datetime import datetime, timedelta

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


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # === ЕДИНАЯ ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            linked_nickname TEXT,
            role TEXT NOT NULL DEFAULT 'player',
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='linked_nickname') THEN
                ALTER TABLE users ADD COLUMN linked_nickname TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='role') THEN
                ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'player';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='created_at') THEN
                ALTER TABLE users ADD COLUMN created_at TEXT;
            END IF;
        END $$;
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_linked_nickname
        ON users (linked_nickname)
        WHERE linked_nickname IS NOT NULL
    """)

    # === АЛИАСЫ НИКНЕЙМОВ ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nickname_aliases (
            id SERIAL PRIMARY KEY,
            current_nickname TEXT NOT NULL,
            old_nickname TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(old_nickname)
        )
    """)

    # === РЕЙТИНГИ ===
    for rt in ['duel', 'arcadia']:
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
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='carousel_slides' AND column_name='poster_url') THEN
                ALTER TABLE carousel_slides ADD COLUMN poster_url TEXT;
            END IF;
        END $$;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_map (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # === ЯБЛОКИ (иммунитет) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apples (
            id SERIAL PRIMARY KEY,
            from_user_id INTEGER NOT NULL,
            to_nickname TEXT NOT NULL,
            week_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_apples_from_week
        ON apples (from_user_id, week_key)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_apples_to_nickname
        ON apples (to_nickname)
    """)

    # === НАСТРОЙКИ САЙТА (для тултипа и т.п.) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # === СУПЕР-АДМИН по умолчанию ===
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hashed = _hash('admin123')
    cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE users SET role = 'super_admin' WHERE username = 'admin'")
    else:
        cursor.execute("""
            INSERT INTO users (username, password, linked_nickname, role, created_at)
            VALUES (%s, %s, NULL, 'super_admin', %s)
        """, ('admin', hashed, now))

    # Дефолтный текст тултипа
    cursor.execute("SELECT id FROM site_settings WHERE key = 'rating_tooltip_text'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO site_settings (key, value, updated_at)
            VALUES ('rating_tooltip_text', %s, %s)
        """, ('Это рейтинг союза. Каждую неделю игроки могут дарить яблоки 🍎 тем, кто находится ниже топ-50, чтобы помочь им избежать исключения. Победитель по яблокам в конце сезона получает иммунитет.', now))

    conn.commit()
    conn.close()


# ============================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================

def check_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, username, role FROM users
                      WHERE username = %s AND password = %s""",
                   (username, _hash(password)))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, username, password, linked_nickname, role, created_at
                      FROM users WHERE id = %s""", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, username, password, linked_nickname, role, created_at
                      FROM users WHERE username = %s""", (username,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, username, linked_nickname, role, created_at
                      FROM users ORDER BY
                      CASE role
                          WHEN 'super_admin' THEN 0
                          WHEN 'admin' THEN 1
                          ELSE 2
                      END,
                      created_at DESC""")
    data = cursor.fetchall()
    conn.close()
    return data


def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO users (username, password, linked_nickname, role, created_at)
                          VALUES (%s, %s, NULL, 'player', %s) RETURNING id""",
                       (username, _hash(password), now))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    except Exception as e:
        print(f"register_user error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_user_username(user_id, new_username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"update_user_username error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_user_password(user_id, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (_hash(new_password), user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"update_user_password error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_user_role(user_id, new_role):
    if new_role not in ('player', 'admin', 'super_admin'):
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"update_user_role error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def link_user_nickname(user_id, nickname):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET linked_nickname = %s WHERE id = %s", (nickname, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"link_user_nickname error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def unlink_user_nickname(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET linked_nickname = NULL WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"unlink_user_nickname error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"delete_user error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_linked_nicknames():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT linked_nickname FROM users WHERE linked_nickname IS NOT NULL")
    data = cursor.fetchall()
    conn.close()
    return {row[0] for row in data}


def count_super_admins():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
    n = cursor.fetchone()[0]
    conn.close()
    return n


# ============================================================
# АЛИАСЫ НИКНЕЙМОВ
# ============================================================

def add_nickname_alias(current_nickname, old_nickname):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("SELECT id FROM nickname_aliases WHERE old_nickname = %s", (old_nickname,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""UPDATE nickname_aliases SET current_nickname = %s, created_at = %s
                              WHERE old_nickname = %s""",
                           (current_nickname, created_at, old_nickname))
        else:
            cursor.execute("""INSERT INTO nickname_aliases (current_nickname, old_nickname, created_at)
                              VALUES (%s, %s, %s)""",
                           (current_nickname, old_nickname, created_at))

        for rt in ['duel', 'arcadia']:
            cursor.execute(f"UPDATE history_{rt} SET nickname = %s WHERE nickname = %s",
                           (current_nickname, old_nickname))
            cursor.execute(f"UPDATE players_{rt} SET nickname = %s WHERE nickname = %s",
                           (current_nickname, old_nickname))

        cursor.execute("""UPDATE users SET linked_nickname = %s
                          WHERE linked_nickname = %s""",
                       (current_nickname, old_nickname))
        cursor.execute("""UPDATE apples SET to_nickname = %s
                          WHERE to_nickname = %s""",
                       (current_nickname, old_nickname))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding alias: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_nickname_aliases():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT current_nickname, old_nickname, created_at FROM nickname_aliases
                      ORDER BY created_at DESC""")
    data = cursor.fetchall()
    conn.close()
    return data


def delete_nickname_alias(old_nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nickname_aliases WHERE old_nickname = %s", (old_nickname,))
    conn.commit()
    conn.close()


def resolve_nickname(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT current_nickname FROM nickname_aliases
                      WHERE old_nickname = %s ORDER BY created_at DESC LIMIT 1""", (nickname,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else nickname


# ============================================================
# РЕЙТИНГ
# ============================================================

def save_rating(rating_type, data_list):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for nickname, points in data_list:
        resolved_nickname = resolve_nickname(nickname)
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


def get_total_rating():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        WITH players AS (
            SELECT nickname FROM players_duel
            UNION
            SELECT nickname FROM players_arcadia
        ),
        duel AS (SELECT nickname, points FROM players_duel),
        arcadia AS (SELECT nickname, points FROM players_arcadia)
        SELECT
            p.nickname,
            COALESCE(d.points, 0) AS duel_points,
            COALESCE(a.points, 0) AS arcadia_points,
            COALESCE(d.points, 0) + COALESCE(a.points, 0) AS total_points
        FROM players p
        LEFT JOIN duel d ON d.nickname = p.nickname
        LEFT JOIN arcadia a ON a.nickname = p.nickname
        ORDER BY total_points DESC, p.nickname ASC
    """)
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


def get_all_time_leaders(rating_type, limit=3):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""SELECT nickname, SUM(points) as total_points FROM history_{rating_type}
                       GROUP BY nickname ORDER BY total_points DESC LIMIT %s""", (limit,))
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
        cursor.execute("DELETE FROM nickname_aliases WHERE current_nickname = %s OR old_nickname = %s",
                       (nickname, nickname))
        cursor.execute("UPDATE users SET linked_nickname = NULL WHERE linked_nickname = %s", (nickname,))
        cursor.execute("DELETE FROM apples WHERE to_nickname = %s", (nickname,))
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
        {'id': 'total',   'name': 'Рейтинг',         'icon': '🏆', 'color': '#ffb800'},
        {'id': 'duel',    'name': 'Рейтинг Дуэли',   'icon': '⚔️', 'color': '#ff8a1f'},
        {'id': 'arcadia', 'name': 'Рейтинг Аркадии', 'icon': '🌿', 'color': '#4caf50'},
    ]


def get_rating_display_name(rating_type):
    names = {
        'duel': 'Рейтинг Дуэли',
        'arcadia': 'Рейтинг Аркадии',
        'total': 'Рейтинг',
    }
    return names.get(rating_type, rating_type)


# ============================================================
# ЯБЛОКИ (иммунитет)
# ============================================================

def get_week_key(dt=None):
    """ISO-неделя, например 2026-W14."""
    dt = dt or datetime.now()
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def get_apples_given_this_week(user_id):
    """Сколько яблок пользователь подарил на текущей ISO-неделе."""
    conn = get_connection()
    cursor = conn.cursor()
    week = get_week_key()
    cursor.execute("""SELECT COUNT(*) FROM apples
                      WHERE from_user_id = %s AND week_key = %s""",
                   (user_id, week))
    n = cursor.fetchone()[0]
    conn.close()
    return n or 0


def give_apple(from_user_id, to_nickname):
    """Пытается подарить яблоко. Возвращает (ok, message, remaining)."""
    week = get_week_key()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # проверка: не себе
        cursor.execute("SELECT linked_nickname FROM users WHERE id = %s", (from_user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Пользователь не найден.", 0
        from_nickname = row[0]
        if from_nickname and from_nickname == to_nickname:
            return False, "Нельзя дарить яблоко самому себе.", 0

        # проверка лимита
        cursor.execute("""SELECT COUNT(*) FROM apples
                          WHERE from_user_id = %s AND week_key = %s""",
                       (from_user_id, week))
        given = cursor.fetchone()[0] or 0
        if given >= 5:
            return False, "Вы уже подарили 5 яблок на этой неделе.", 0

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""INSERT INTO apples (from_user_id, to_nickname, week_key, created_at)
                          VALUES (%s, %s, %s, %s)""",
                       (from_user_id, to_nickname, week, now))
        conn.commit()
        remaining = 5 - (given + 1)
        return True, f"Вы подарили яблоко игроку «{to_nickname}».", remaining
    except Exception as e:
        print(f"give_apple error: {e}")
        conn.rollback()
        return False, "Ошибка при дарении.", 0
    finally:
        conn.close()


def get_apples_received_map():
    """dict: nickname -> количество полученных яблок (за весь сезон)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT to_nickname, COUNT(*) FROM apples
                      GROUP BY to_nickname""")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in data}


def get_apples_received_for(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM apples WHERE to_nickname = %s", (nickname,))
    n = cursor.fetchone()[0]
    conn.close()
    return n or 0


def reset_apples():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM apples")
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_apples error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ============================================================
# НАСТРОЙКИ САЙТА
# ============================================================

def get_setting(key, default=''):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM site_settings WHERE key = %s", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""
            INSERT INTO site_settings (key, value, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = %s
        """, (key, value, now, value, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"set_setting error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ============================================================
# ЖУРНАЛ ОТПУСКОВ
# ============================================================

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


# ============================================================
# КАРУСЕЛЬ
# ============================================================

def create_slide(title, content, media_type, media_url, position, poster_url=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO carousel_slides (title, content, media_type, media_url, position, is_active, created_at, updated_at, poster_url)
                          VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s, %s) RETURNING id""",
                       (title, content, media_type, media_url, position, now, now, poster_url))
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
        cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at, poster_url
                          FROM carousel_slides WHERE is_active = TRUE
                          ORDER BY position ASC, id ASC""")
    else:
        cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at, poster_url
                          FROM carousel_slides ORDER BY position ASC, id ASC""")
    data = cursor.fetchall()
    conn.close()
    return data


def get_slide_by_id(slide_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, title, content, media_type, media_url, position, is_active, created_at, updated_at, poster_url
                      FROM carousel_slides WHERE id = %s""", (slide_id,))
    data = cursor.fetchone()
    conn.close()
    return data


def update_slide(slide_id, title, content, media_type, media_url, position, is_active, poster_url=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""UPDATE carousel_slides SET title = %s, content = %s, media_type = %s,
                          media_url = %s, position = %s, is_active = %s, updated_at = %s, poster_url = %s WHERE id = %s""",
                       (title, content, media_type, media_url, position, is_active, now, poster_url, slide_id))
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


# ============================================================
# КАРТА БОЯ
# ============================================================

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
