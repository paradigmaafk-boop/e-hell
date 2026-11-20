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
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='squad_1') THEN
                ALTER TABLE users ADD COLUMN squad_1 TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='squad_2') THEN
                ALTER TABLE users ADD COLUMN squad_2 TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='squad_3') THEN
                ALTER TABLE users ADD COLUMN squad_3 TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='squad_4') THEN
                ALTER TABLE users ADD COLUMN squad_4 TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='users' AND column_name='squad_5') THEN
                ALTER TABLE users ADD COLUMN squad_5 TEXT;
            END IF;
        END $$;
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_linked_nickname
        ON users (linked_nickname)
        WHERE linked_nickname IS NOT NULL
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nickname_aliases (
            id SERIAL PRIMARY KEY,
            current_nickname TEXT NOT NULL,
            old_nickname TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(old_nickname)
        )
    """)
    cursor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'nickname_aliases'
                  AND column_name = 'rating_type'
                  AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE nickname_aliases ALTER COLUMN rating_type DROP NOT NULL;
            END IF;
        END $$;
    """)

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
        CREATE TABLE IF NOT EXISTS merge_log (
            id SERIAL PRIMARY KEY,
            target_nickname TEXT NOT NULL,
            merged_nickname TEXT NOT NULL,
            rating_type TEXT NOT NULL,
            points NUMERIC NOT NULL DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS media_assets (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            title TEXT,
            mime_type TEXT NOT NULL,
            data BYTEA NOT NULL,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            uploaded_by TEXT,
            preview_data BYTEA,
            preview_mime TEXT,
            preview_size INTEGER
        )
    """)
    cursor.execute("""
        ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS title TEXT
    """)
    cursor.execute("""
        UPDATE media_assets SET title = 'Фото ' || id WHERE title IS NULL OR title = ''
    """)
    cursor.execute("""
        ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS preview_data BYTEA
    """)
    cursor.execute("""
        ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS preview_mime TEXT
    """)
    cursor.execute("""
        ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS preview_size INTEGER
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_media_assets_name_size
        ON media_assets (filename, size)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_map (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # ============================================================
    # КАРТА ШТАТА
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_legend (
            id SERIAL PRIMARY KEY,
            color TEXT NOT NULL,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_cells (
            id SERIAL PRIMARY KEY,
            cell_index INTEGER NOT NULL UNIQUE,
            color TEXT,
            label TEXT,
            updated_at TEXT NOT NULL
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_bolts (
            id SERIAL PRIMARY KEY,
            from_user_id INTEGER NOT NULL,
            to_nickname TEXT NOT NULL,
            duel_average NUMERIC(12, 2) NOT NULL DEFAULT 0,
            bonus_points INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_gold_bolts_to_nickname
        ON gold_bolts (to_nickname)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_gold_bolts_from_user
        ON gold_bolts (from_user_id)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_weeks (
            week_key TEXT PRIMARY KEY,
            session_time TEXT NOT NULL,
            session_time_overridden BOOLEAN DEFAULT FALSE,
            roster_published BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_registrations (
            id SERIAL PRIMARY KEY,
            week_key TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            preferred_session TEXT NOT NULL DEFAULT 'any',
            created_at TEXT NOT NULL,
            UNIQUE(week_key, user_id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reservoir_reg_week
        ON reservoir_registrations (week_key)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_roster (
            id SERIAL PRIMARY KEY,
            week_key TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'rotation',
            attended INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(week_key, user_id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reservoir_roster_week
        ON reservoir_roster (week_key)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservoir_blacklist (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            week_key TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, week_key)
        )
    """)

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

    cursor.execute("SELECT id FROM site_settings WHERE key = 'rating_tooltip_text'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO site_settings (key, value, updated_at)
            VALUES ('rating_tooltip_text', %s, %s)
        """, ('Это рейтинг союза. Каждую неделю игроки могут дарить яблоки другим участникам союза. Яблоки копятся весь сезон, а топ-10 игроков по сбору яблок получают иммунитет от ротации.', now))

    conn.commit()
    conn.close()


def _has_column(cursor, table_name, column_name):
    cursor.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        LIMIT 1
    """, (table_name, column_name))
    return cursor.fetchone() is not None


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
    cursor.execute("""SELECT id, username, password, linked_nickname, role, created_at,
                             squad_1, squad_2, squad_3, squad_4, squad_5
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
                          WHEN 'state_admin' THEN 2
                          WHEN 'reservoir' THEN 3
                          ELSE 4
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
    if new_role not in ('player', 'reservoir', 'state_admin', 'admin', 'super_admin'):
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
# БОЕВАЯ МОЩЬ ОТРЯДОВ
# ============================================================

def update_user_squads(user_id, squads_list):
    while len(squads_list) < 5:
        squads_list.append(None)
    squads_list = squads_list[:5]

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET squad_1 = %s, squad_2 = %s, squad_3 = %s,
                             squad_4 = %s, squad_5 = %s
            WHERE id = %s
        """, (squads_list[0], squads_list[1], squads_list[2],
              squads_list[3], squads_list[4], user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"update_user_squads error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_squads(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT squad_1, squad_2, squad_3, squad_4, squad_5
                      FROM users WHERE id = %s""", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return [None] * 5
    return list(row)


def get_squads_by_nickname_map():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT linked_nickname, squad_1 FROM users
                      WHERE linked_nickname IS NOT NULL
                        AND squad_1 IS NOT NULL
                        AND squad_1 <> ''""")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in data}


# ============================================================
# АЛИАСЫ НИКНЕЙМОВ
# ============================================================

def _insert_alias(cursor, current_nickname, old_nickname, created_at, rating_type=None):
    has_rating_type = _has_column(cursor, 'nickname_aliases', 'rating_type')
    if has_rating_type:
        rt_value = rating_type or 'any'
        cursor.execute("""INSERT INTO nickname_aliases
                          (current_nickname, old_nickname, created_at, rating_type)
                          VALUES (%s, %s, %s, %s)""",
                       (current_nickname, old_nickname, created_at, rt_value))
    else:
        cursor.execute("""INSERT INTO nickname_aliases
                          (current_nickname, old_nickname, created_at)
                          VALUES (%s, %s, %s)""",
                       (current_nickname, old_nickname, created_at))


def _update_alias(cursor, current_nickname, old_nickname, created_at, rating_type=None):
    has_rating_type = _has_column(cursor, 'nickname_aliases', 'rating_type')
    if has_rating_type:
        rt_value = rating_type or 'any'
        cursor.execute("""UPDATE nickname_aliases
                          SET current_nickname = %s, created_at = %s, rating_type = %s
                          WHERE old_nickname = %s""",
                       (current_nickname, created_at, rt_value, old_nickname))
    else:
        cursor.execute("""UPDATE nickname_aliases
                          SET current_nickname = %s, created_at = %s
                          WHERE old_nickname = %s""",
                       (current_nickname, created_at, old_nickname))


def add_nickname_alias(current_nickname, old_nickname):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("SELECT id FROM nickname_aliases WHERE old_nickname = %s", (old_nickname,))
        existing = cursor.fetchone()
        if existing:
            _update_alias(cursor, current_nickname, old_nickname, created_at)
        else:
            _insert_alias(cursor, current_nickname, old_nickname, created_at)

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
        cursor.execute("""UPDATE gold_bolts SET to_nickname = %s
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


def get_alias_resolutions(nicknames):
    """Пары (старый ник → новый ник) для ников из загружаемой таблицы."""
    nicknames = [n for n in set(nicknames or []) if n]
    if not nicknames:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT old_nickname, current_nickname FROM nickname_aliases
                      WHERE old_nickname = ANY(%s)""", (nicknames,))
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
    try:
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
        return True
    except Exception as e:
        print(f"save_rating error: {e}")
        conn.rollback()
        return False
    finally:
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
            UNION
            SELECT to_nickname FROM gold_bolts
        ),
        duel AS (SELECT nickname, points FROM players_duel),
        arcadia AS (SELECT nickname, points FROM players_arcadia),
        bolts AS (
            SELECT to_nickname AS nickname,
                   COUNT(*) AS bolt_count,
                   COALESCE(SUM(bonus_points), 0) AS bolt_bonus
            FROM gold_bolts
            GROUP BY to_nickname
        )
        SELECT
            p.nickname,
            COALESCE(d.points, 0) AS duel_points,
            COALESCE(a.points, 0) AS arcadia_points,
            COALESCE(d.points, 0) + COALESCE(a.points, 0)
                + COALESCE(b.bolt_bonus, 0) AS total_points,
            COALESCE(b.bolt_bonus, 0) AS bolt_bonus,
            COALESCE(b.bolt_count, 0) AS bolt_count
        FROM players p
        LEFT JOIN duel d ON d.nickname = p.nickname
        LEFT JOIN arcadia a ON a.nickname = p.nickname
        LEFT JOIN bolts b ON b.nickname = p.nickname
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


def get_total_player_history(nickname):
    """История игрока по датам: Дуэль + Аркадия.

    Группируем по календарному дню: загрузки Дуэли и Аркадии могут
    прийти в разное время, но относиться к одному замеру.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MIN(date) AS date, SUM(points) AS points
        FROM (
            SELECT date, points FROM history_duel WHERE nickname = %s
            UNION ALL
            SELECT date, points FROM history_arcadia WHERE nickname = %s
        ) AS combined
        GROUP BY SUBSTR(date, 1, 10)
        ORDER BY MIN(date) ASC
    """, (nickname, nickname))
    data = cursor.fetchall()
    conn.close()
    return data


def get_total_average_history():
    """Среднее по союзу за день: сумма Дуэли и Аркадии на игрока."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        WITH combined AS (
            SELECT date, SUBSTR(date, 1, 10) AS day, nickname, points
            FROM history_duel
            UNION ALL
            SELECT date, SUBSTR(date, 1, 10) AS day, nickname, points
            FROM history_arcadia
        ),
        per_player AS (
            SELECT day, nickname, SUM(points) AS points, MIN(date) AS sample_date
            FROM combined
            GROUP BY day, nickname
        )
        SELECT MIN(sample_date) AS date, AVG(points) AS avg_points
        FROM per_player
        GROUP BY day
        ORDER BY MIN(sample_date) ASC
    """)
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


def get_nicknames_with_history(rating_type):
    """Ники, у которых реально есть точки на графике."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT nickname FROM history_{rating_type}")
    data = cursor.fetchall()
    conn.close()
    return {row[0] for row in data}


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
        cursor.execute(f"DELETE FROM history_{rating_type}")
        cursor.execute(f"UPDATE players_{rating_type} SET points = 0")
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_rating error: {e}")
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

        # Если игрок удалён из обоих рейтингов, убираем и связи,
        # которые вели на этот ник. Иначе при следующей загрузке
        # старый ник снова «оживит» удалённую строку.
        other_type = 'arcadia' if rating_type == 'duel' else 'duel'
        cursor.execute(f"SELECT 1 FROM players_{other_type} WHERE nickname = %s LIMIT 1", (nickname,))
        if not cursor.fetchone():
            cursor.execute("DELETE FROM nickname_aliases WHERE current_nickname = %s", (nickname,))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting player: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_player_from_all_ratings(nickname):
    """Полностью убирает строку из общего рейтинга: Дуэль + Аркадия."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for rating_type in ('duel', 'arcadia'):
            cursor.execute(f"DELETE FROM players_{rating_type} WHERE nickname = %s", (nickname,))
            cursor.execute(f"DELETE FROM history_{rating_type} WHERE nickname = %s", (nickname,))
        cursor.execute("DELETE FROM gold_bolts WHERE to_nickname = %s", (nickname,))
        # Иначе будущая загрузка старого ника через алиас вернёт удалённого игрока.
        cursor.execute("DELETE FROM nickname_aliases WHERE current_nickname = %s", (nickname,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting player from all ratings: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_rating_types():
    return [
        {'id': 'total',   'name': 'Рейтинг',         'icon': '🏆', 'color': '#ffb800'},
        {'id': 'duel',    'name': 'Рейтинг Дуэли',   'icon': '⚔️', 'color': '#ff8a1f'},
        {'id': 'arcadia', 'name': 'Рейтинг Аркадии', 'icon': '🌿', 'color': '#4caf50'},
        {'id': 'events',  'name': 'Ивенты',          'icon': '🔩', 'color': '#ffd166'},
    ]


def get_rating_display_name(rating_type):
    names = {
        'duel': 'Рейтинг Дуэли',
        'arcadia': 'Рейтинг Аркадии',
        'total': 'Общий рейтинг',
        'events': 'Ивенты',
    }
    return names.get(rating_type, rating_type)


def get_last_update_date(rating_type):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT MAX(date) FROM history_{rating_type}")
        row = cursor.fetchone()
        if not row or not row[0]:
            return None
        date_str = str(row[0])[:10]
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return date_str
    except Exception as e:
        print(f"get_last_update_date error: {e}")
        return None
    finally:
        conn.close()


# ============================================================
# ОБЪЕДИНЕНИЕ СТРОК РЕЙТИНГА
# ============================================================

def get_all_duel_players_with_points():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, points FROM players_duel ORDER BY points DESC, nickname ASC")
    data = cursor.fetchall()
    conn.close()
    return data


def get_all_arcadia_players_with_points():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nickname, points FROM players_arcadia ORDER BY points DESC, nickname ASC")
    data = cursor.fetchall()
    conn.close()
    return data


def associate_players(target_nickname, duel_nicks, arcadia_nicks, created_by=''):
    """Объединение строк рейтинга.

    Очки и история выбранных строк переносятся в целевую строку.
    Связи никнеймов (nickname_aliases) НЕ создаются: объединение
    не является переименованием игрока.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        duel_nicks = [n.strip() for n in (duel_nicks or []) if n and n.strip()]
        arcadia_nicks = [n.strip() for n in (arcadia_nicks or []) if n and n.strip()]

        # Убираем целевой ник и дубли.
        duel_nicks = list(dict.fromkeys(n for n in duel_nicks if n != target_nickname))
        arcadia_nicks = list(dict.fromkeys(n for n in arcadia_nicks if n != target_nickname))

        if not duel_nicks and not arcadia_nicks:
            return False, 'Ничего не выбрано для объединения.'

        def merge_group(rating_type, nicks):
            added = 0
            merged = 0
            for nick in nicks:
                cursor.execute(f"SELECT points FROM players_{rating_type} WHERE nickname = %s", (nick,))
                row = cursor.fetchone()
                if not row:
                    continue
                points = row[0] or 0
                added += points
                merged += 1

                cursor.execute(f"UPDATE history_{rating_type} SET nickname = %s WHERE nickname = %s",
                               (target_nickname, nick))
                cursor.execute(f"DELETE FROM players_{rating_type} WHERE nickname = %s", (nick,))

                cursor.execute("""INSERT INTO merge_log
                                  (target_nickname, merged_nickname, rating_type, points, created_at, created_by)
                                  VALUES (%s, %s, %s, %s, %s, %s)""",
                               (target_nickname, nick, rating_type, points, now, created_by or ''))

                # Объединение — это только перенос очков и истории.
                # Аккаунты и подарки не перепривязываем: это не переименование.
            return added, merged

        duel_added, duel_merged = merge_group('duel', duel_nicks)
        arcadia_added, arcadia_merged = merge_group('arcadia', arcadia_nicks)

        # Болтики — часть рейтинга игрока, поэтому при объединении строк
        # переносим и их на целевой ник.
        for nick in dict.fromkeys(duel_nicks + arcadia_nicks):
            cursor.execute("UPDATE gold_bolts SET to_nickname = %s WHERE to_nickname = %s",
                           (target_nickname, nick))

        if duel_merged:
            cursor.execute("SELECT points FROM players_duel WHERE nickname = %s", (target_nickname,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE players_duel SET points = points + %s, last_updated = %s WHERE nickname = %s",
                    (duel_added, now, target_nickname)
                )
            else:
                cursor.execute(
                    """INSERT INTO players_duel (nickname, points, last_updated)
                       VALUES (%s, %s, %s)""",
                    (target_nickname, duel_added, now)
                )

        if arcadia_merged:
            cursor.execute("SELECT points FROM players_arcadia WHERE nickname = %s", (target_nickname,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE players_arcadia SET points = points + %s, last_updated = %s WHERE nickname = %s",
                    (arcadia_added, now, target_nickname)
                )
            else:
                cursor.execute(
                    """INSERT INTO players_arcadia (nickname, points, last_updated)
                       VALUES (%s, %s, %s)""",
                    (target_nickname, arcadia_added, now)
                )

        conn.commit()

        merged_total = duel_merged + arcadia_merged
        if not merged_total:
            return False, 'Выбранные строки не найдены.'

        msg = f'Объединено строк: {merged_total}.'
        if duel_merged:
            msg += f' Перенесено в Дуэль: {duel_added}.'
        if arcadia_merged:
            msg += f' Перенесено в Аркадию: {arcadia_added}.'
        return True, msg

    except Exception as e:
        print(f"associate_players error: {e}")
        conn.rollback()
        return False, f'Ошибка при объединении: {e}'
    finally:
        conn.close()


def get_all_merge_records(limit=200):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, target_nickname, merged_nickname, rating_type,
                             points, created_at, created_by
                      FROM merge_log
                      ORDER BY created_at DESC, id DESC
                      LIMIT %s""", (limit,))
    data = cursor.fetchall()
    conn.close()
    return data


# ============================================================
# ЯБЛОКИ
# ============================================================

def get_week_key(dt=None):
    dt = dt or datetime.now()
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def get_apples_given_this_week(user_id):
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
    week = get_week_key()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT linked_nickname FROM users WHERE id = %s", (from_user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Пользователь не найден.", 0
        from_nickname = row[0]
        if from_nickname and from_nickname == to_nickname:
            return False, "Нельзя дарить яблоко самому себе.", 0

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


def get_apple_givers_for(nickname):
    """Кто и сколько яблок подарил конкретному нику.

    Возвращает строки: (from_user_id, username, linked_nickname, count, last_at).
    LEFT JOIN — чтобы подарки от уже удалённых аккаунтов не исчезали.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.from_user_id,
               u.username,
               u.linked_nickname,
               COUNT(a.id) AS apples_count,
               MAX(a.created_at) AS last_at
        FROM apples a
        LEFT JOIN users u ON u.id = a.from_user_id
        WHERE a.to_nickname = %s
        GROUP BY a.from_user_id, u.username, u.linked_nickname
        ORDER BY last_at DESC, u.username ASC
    """, (nickname,))
    data = cursor.fetchall()
    conn.close()
    return data


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


def reset_apples_given_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM apples WHERE from_user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_apples_given_by_user error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ============================================================
# ЗОЛОТЫЕ БОЛТИКИ (ИВЕНТЫ)
# ============================================================

def get_duel_union_average():
    """Средний рейтинг Дуэли по союзу за последнее обновление.

    Важно: players_duel хранит накопленную сумму, а не последний замер.
    Поэтому берём среднее из history_duel за самую свежую дату —
    именно его видно на графике как «среднее по союзу».
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(points) FROM history_duel
        WHERE date = (SELECT MAX(date) FROM history_duel)
    """)
    row = cursor.fetchone()
    avg = row[0] if row else None
    conn.close()
    return float(avg or 0)


def get_gold_bolt_value():
    """Сколько очков даёт один болт при текущем среднем по союзу."""
    avg = get_duel_union_average()
    return avg, int(avg * 0.5 + 0.5)


def recalculate_gold_bolt_bonuses():
    """Уравнивает стоимость всех болтов по последнему обновлению Дуэли."""
    avg, bonus = get_gold_bolt_value()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE gold_bolts
                          SET duel_average = %s, bonus_points = %s""",
                       (avg, bonus))
        updated = cursor.rowcount or 0
        conn.commit()
        return avg, bonus, updated
    except Exception as e:
        print(f"recalculate_gold_bolt_bonuses error: {e}")
        conn.rollback()
        return avg, bonus, 0
    finally:
        conn.close()


def give_gold_bolt(from_user_id, to_nickname):
    """Дарит один болт. Бонус фиксируется по среднему Дуэли сейчас."""
    nickname = (to_nickname or '').strip()
    if not nickname:
        return False, 'Не указан игрок.', 0, 0, 0
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 1 FROM players_duel WHERE nickname = %s
            UNION
            SELECT 1 FROM players_arcadia WHERE nickname = %s
            UNION
            SELECT 1 FROM gold_bolts WHERE to_nickname = %s
            LIMIT 1
        """, (nickname, nickname, nickname))
        if not cursor.fetchone():
            conn.rollback()
            return False, 'Игрок не найден в рейтингах.', 0, 0, 0

        avg, bonus = get_gold_bolt_value()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Держим одинаковую стоимость у всех болтов.
        cursor.execute("""UPDATE gold_bolts
                          SET duel_average = %s, bonus_points = %s""",
                       (avg, bonus))
        cursor.execute("""
            INSERT INTO gold_bolts (from_user_id, to_nickname, duel_average, bonus_points, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (from_user_id, nickname, avg, bonus, now))
        cursor.execute("SELECT COUNT(*) FROM gold_bolts WHERE to_nickname = %s", (nickname,))
        count = cursor.fetchone()[0] or 0
        conn.commit()
        message = f'Золотой болт вручён игроку {nickname}.'
        if bonus:
            message += f' +{bonus} к общему рейтингу (50% от среднего по союзу {avg:.1f}).'
        else:
            message += ' Средний рейтинг Дуэли по союзу пока 0, поэтому бонусных очков нет.'
        return True, message, count, bonus, avg
    except Exception as e:
        print(f"give_gold_bolt error: {e}")
        conn.rollback()
        return False, 'Ошибка при вручении болта.', 0, 0, 0
    finally:
        conn.close()


def get_gold_bolts_received_map():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT to_nickname, COUNT(*) FROM gold_bolts
                      GROUP BY to_nickname""")
    data = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return data


def get_gold_bolts_bonus_map():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT to_nickname, COALESCE(SUM(bonus_points), 0)
                      FROM gold_bolts GROUP BY to_nickname""")
    data = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}
    conn.close()
    return data


def get_gold_bolts_summary(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT COUNT(*), COALESCE(SUM(bonus_points), 0)
                      FROM gold_bolts WHERE to_nickname = %s""", (nickname,))
    row = cursor.fetchone()
    conn.close()
    return (row[0] or 0, int(row[1] or 0)) if row else (0, 0)


def get_gold_bolt_givers_for(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(u.username, '—') AS giver,
               COUNT(g.id) AS bolts_count,
               COALESCE(SUM(g.bonus_points), 0) AS bonus_total,
               MAX(g.created_at) AS last_at
        FROM gold_bolts g
        LEFT JOIN users u ON u.id = g.from_user_id
        WHERE g.to_nickname = %s
        GROUP BY g.from_user_id, u.username
        ORDER BY last_at DESC, giver ASC
    """, (nickname,))
    data = cursor.fetchall()
    conn.close()
    return data


def get_all_gold_bolts(limit=200):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.to_nickname, g.duel_average, g.bonus_points, g.created_at,
               COALESCE(u.username, '—') AS giver
        FROM gold_bolts g
        LEFT JOIN users u ON u.id = g.from_user_id
        ORDER BY g.created_at DESC, g.id DESC
        LIMIT %s
    """, (limit,))
    data = cursor.fetchall()
    conn.close()
    return data


def get_events_rating():
    """Рейтинг посещаемости: количество болтов и их вклад в общий рейтинг."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT to_nickname,
               COUNT(*) AS bolts_count,
               COALESCE(SUM(bonus_points), 0) AS bonus_total
        FROM gold_bolts
        GROUP BY to_nickname
        ORDER BY bolts_count DESC, bonus_total DESC, to_nickname ASC
    """)
    data = cursor.fetchall()
    conn.close()
    return data


def get_events_player_history(nickname):
    """Накопленные болты по дням — для графика."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUBSTR(created_at, 1, 10) AS day, COUNT(*)
        FROM gold_bolts
        WHERE to_nickname = %s
        GROUP BY SUBSTR(created_at, 1, 10)
        ORDER BY day ASC
    """, (nickname,))
    rows = cursor.fetchall()
    conn.close()
    total = 0
    result = []
    for day, count in rows:
        total += count
        result.append((day, total))
    return result


def get_bolt_bonus_history(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT created_at, bonus_points FROM gold_bolts
                      WHERE to_nickname = %s ORDER BY created_at ASC, id ASC""",
                   (nickname,))
    data = cursor.fetchall()
    conn.close()
    return data


def reset_gold_bolts():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM gold_bolts")
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_gold_bolts error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def reset_gold_bolts_given_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM gold_bolts WHERE from_user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_gold_bolts_given_by_user error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def reset_gold_bolts_for_player(nickname):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM gold_bolts WHERE to_nickname = %s", (nickname,))
        conn.commit()
        return True
    except Exception as e:
        print(f"reset_gold_bolts_for_player error: {e}")
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
# МЕДИА-АЛЬБОМ (хранится в БД, переживает передеплой)
# ============================================================

def create_media_asset(filename, mime_type, data, uploaded_by='', preview_data=None, preview_mime=None, title=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    display_title = (title or filename).strip() or filename
    try:
        cursor.execute("""
            INSERT INTO media_assets
                (filename, title, mime_type, data, size, created_at, uploaded_by,
                 preview_data, preview_mime, preview_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (filename, size) DO NOTHING
            RETURNING id
        """, (
            filename, display_title, mime_type, psycopg2.Binary(data), len(data), now, uploaded_by or '',
            psycopg2.Binary(preview_data) if preview_data else None,
            preview_mime,
            len(preview_data) if preview_data else None,
        ))
        row = cursor.fetchone()
        if row:
            asset_id = row[0]
        else:
            cursor.execute(
                "SELECT id, preview_data FROM media_assets WHERE filename = %s AND size = %s LIMIT 1",
                (filename, len(data))
            )
            existing = cursor.fetchone()
            if not existing:
                conn.rollback()
                return None
            asset_id = existing[0]
            # Старые записи (до появления превью) дозаполняем.
            if preview_data and existing[1] is None:
                cursor.execute("""UPDATE media_assets
                                  SET preview_data = %s, preview_mime = %s, preview_size = %s
                                  WHERE id = %s""",
                               (psycopg2.Binary(preview_data), preview_mime,
                                len(preview_data), asset_id))
        conn.commit()
        return asset_id
    except Exception as e:
        print(f"create_media_asset error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_media_assets():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, filename, mime_type, size, created_at, uploaded_by, preview_size,
                             COALESCE(title, filename) AS title
                      FROM media_assets
                      ORDER BY created_at DESC, id DESC""")
    data = cursor.fetchall()
    conn.close()
    return data


def update_media_asset_title(asset_id, title):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE media_assets SET title = %s WHERE id = %s", (title, asset_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"update_media_asset_title error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_media_asset(asset_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, filename, mime_type, data, size, created_at, uploaded_by
                      FROM media_assets WHERE id = %s""", (asset_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return (row[0], row[1], row[2], bytes(row[3]), row[4], row[5], row[6])
    return None


def get_media_asset_preview(asset_id):
    """Лёгкая версия для показа; None, если превью ещё нет."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT filename, preview_data, preview_mime, preview_size
                      FROM media_assets WHERE id = %s""", (asset_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[1] is not None:
        return (row[0], bytes(row[1]), row[2], row[3])
    return None


def get_media_assets_without_previews():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, mime_type, data
                      FROM media_assets
                      WHERE preview_data IS NULL AND mime_type LIKE 'image/%'""")
    data = cursor.fetchall()
    conn.close()
    return data


def set_media_preview(asset_id, data, mime_type):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE media_assets
                          SET preview_data = %s, preview_mime = %s, preview_size = %s
                          WHERE id = %s""",
                       (psycopg2.Binary(data), mime_type, len(data), asset_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"set_media_preview error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_media_asset(asset_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM media_assets WHERE id = %s", (asset_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"delete_media_asset error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def count_media_asset_usage(asset_id):
    url = f'/media/{asset_id}'
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT COUNT(*) FROM carousel_slides
                      WHERE media_url = %s OR poster_url = %s""", (url, url))
    count = cursor.fetchone()[0]
    conn.close()
    return count or 0


def clear_slide_media(slide_id):
    """Убирает битую ссылку на статический файл, которого уже нет."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE carousel_slides SET media_url = NULL WHERE id = %s", (slide_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"clear_slide_media error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate_static_media_urls(mapping):
    """Заменяет старые /static/carousel/... на /media/<id>."""
    if not mapping:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    updated = 0
    try:
        for old_url, new_url in mapping.items():
            cursor.execute("UPDATE carousel_slides SET media_url = %s WHERE media_url = %s",
                           (new_url, old_url))
            updated += cursor.rowcount or 0
            cursor.execute("UPDATE carousel_slides SET poster_url = %s WHERE poster_url = %s",
                           (new_url, old_url))
            updated += cursor.rowcount or 0
        conn.commit()
        return updated
    except Exception as e:
        print(f"migrate_static_media_urls error: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


# ============================================================
# КАРТА БОЯ (РЕЗЕРВУАР)
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


# ============================================================
# РЕЗЕРВУАР: НЕДЕЛИ
# ============================================================

def _iso_week_key(dt=None):
    dt = dt or datetime.now()
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def _default_session_for_week(week_key):
    try:
        week_num = int(week_key.split('-W')[1])
    except Exception:
        return '22'
    return '22' if week_num % 2 == 0 else '14'


def get_or_create_reservoir_week(week_key=None):
    week_key = week_key or _iso_week_key()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT week_key, session_time, session_time_overridden,
                             roster_published, created_at, updated_at
                      FROM reservoir_weeks WHERE week_key = %s""", (week_key,))
    row = cursor.fetchone()

    if row:
        conn.close()
        return {
            'week_key': row[0],
            'session_time': row[1],
            'session_time_overridden': row[2],
            'roster_published': row[3],
            'created_at': row[4],
            'updated_at': row[5],
        }

    default_session = _default_session_for_week(week_key)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO reservoir_weeks
                          (week_key, session_time, session_time_overridden, roster_published, created_at, updated_at)
                          VALUES (%s, %s, FALSE, FALSE, %s, %s)""",
                       (week_key, default_session, now, now))
        conn.commit()
    except Exception as e:
        print(f"get_or_create_reservoir_week error: {e}")
        conn.rollback()

    conn.close()
    return {
        'week_key': week_key,
        'session_time': default_session,
        'session_time_overridden': False,
        'roster_published': False,
        'created_at': now,
        'updated_at': now,
    }


def set_reservoir_session_time(week_key, session_time):
    if session_time not in ('14', '22'):
        return False
    get_or_create_reservoir_week(week_key)

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""UPDATE reservoir_weeks
                          SET session_time = %s, session_time_overridden = TRUE, updated_at = %s
                          WHERE week_key = %s""",
                       (session_time, now, week_key))
        conn.commit()
        return True
    except Exception as e:
        print(f"set_reservoir_session_time error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def set_reservoir_published(week_key, published):
    get_or_create_reservoir_week(week_key)

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""UPDATE reservoir_weeks
                          SET roster_published = %s, updated_at = %s
                          WHERE week_key = %s""",
                       (bool(published), now, week_key))
        conn.commit()
        return True
    except Exception as e:
        print(f"set_reservoir_published error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_reservoir_week_history(limit=30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT week_key, session_time, roster_published, created_at
                      FROM reservoir_weeks
                      ORDER BY week_key DESC LIMIT %s""", (limit,))
    data = cursor.fetchall()
    conn.close()
    return data


# ============================================================
# РЕЗЕРВУАР: ЗАЯВКИ
# ============================================================

def get_reservoir_registrations(week_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.user_id, r.preferred_session, r.created_at,
               u.username, u.linked_nickname, u.squad_1
        FROM reservoir_registrations r
        JOIN users u ON u.id = r.user_id
        WHERE r.week_key = %s
        ORDER BY u.squad_1 DESC NULLS LAST, r.created_at ASC
    """, (week_key,))
    data = cursor.fetchall()
    conn.close()
    return data


def get_reservoir_registration_for_user(week_key, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, preferred_session, created_at
                      FROM reservoir_registrations
                      WHERE week_key = %s AND user_id = %s""",
                   (week_key, user_id))
    row = cursor.fetchone()
    conn.close()
    return row


def add_reservoir_registration(week_key, user_id, preferred_session):
    if preferred_session not in ('14', '22', 'any'):
        preferred_session = 'any'

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO reservoir_registrations
                          (week_key, user_id, preferred_session, created_at)
                          VALUES (%s, %s, %s, %s)""",
                       (week_key, user_id, preferred_session, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"add_reservoir_registration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def cancel_reservoir_registration(week_key, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""DELETE FROM reservoir_registrations
                          WHERE week_key = %s AND user_id = %s""",
                       (week_key, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"cancel_reservoir_registration error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ============================================================
# РЕЗЕРВУАР: СОСТАВ
# ============================================================

def get_reservoir_roster(week_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.user_id, r.role, r.attended,
               u.username, u.linked_nickname, u.squad_1
        FROM reservoir_roster r
        JOIN users u ON u.id = r.user_id
        WHERE r.week_key = %s
        ORDER BY
            CASE r.role WHEN 'core' THEN 0 ELSE 1 END,
            u.squad_1 DESC NULLS LAST
    """, (week_key,))
    data = cursor.fetchall()
    conn.close()
    return data


def save_reservoir_roster(week_key, roster_items):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""SELECT user_id, attended FROM reservoir_roster WHERE week_key = %s""",
                       (week_key,))
        old_attended = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("DELETE FROM reservoir_roster WHERE week_key = %s", (week_key,))

        for item in roster_items:
            uid = int(item.get('user_id'))
            role = item.get('role', 'rotation')
            if role not in ('core', 'rotation'):
                role = 'rotation'
            attended = old_attended.get(uid, None)
            cursor.execute("""INSERT INTO reservoir_roster
                              (week_key, user_id, role, attended, created_at)
                              VALUES (%s, %s, %s, %s, %s)""",
                           (week_key, uid, role, attended, now))

        conn.commit()
        return True
    except Exception as e:
        print(f"save_reservoir_roster error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def set_reservoir_attendance(week_key, user_id, attended):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""UPDATE reservoir_roster
                          SET attended = %s
                          WHERE week_key = %s AND user_id = %s""",
                       (attended, week_key, user_id))
        conn.commit()

        if attended == 0:
            next_week = _next_week_key(week_key)
            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""INSERT INTO reservoir_blacklist
                                  (user_id, week_key, reason, created_at)
                                  VALUES (%s, %s, %s, %s)
                                  ON CONFLICT (user_id, week_key) DO NOTHING""",
                               (user_id, next_week,
                                f'Не пришёл на игре недели {week_key}',
                                now))
                conn.commit()
            except Exception as e:
                print(f"blacklist auto-add error: {e}")
                conn.rollback()

        return True
    except Exception as e:
        print(f"set_reservoir_attendance error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def _next_week_key(week_key):
    try:
        year_part, week_part = week_key.split('-W')
        year = int(year_part)
        week = int(week_part)
    except Exception:
        return week_key

    week += 1
    if week > 52:
        week = 1
        year += 1
    return f"{year}-W{week:02d}"


# ============================================================
# РЕЗЕРВУАР: ЧЁРНЫЕ МЕТКИ
# ============================================================

def get_blacklist_for_week(week_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.id, b.user_id, b.reason, b.created_at,
               u.username, u.linked_nickname, u.squad_1
        FROM reservoir_blacklist b
        JOIN users u ON u.id = b.user_id
        WHERE b.week_key = %s
        ORDER BY b.created_at ASC
    """, (week_key,))
    data = cursor.fetchall()
    conn.close()
    return data


def is_user_blacklisted(week_key, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, reason FROM reservoir_blacklist
                      WHERE week_key = %s AND user_id = %s""",
                   (week_key, user_id))
    row = cursor.fetchone()
    conn.close()
    return row


def remove_from_blacklist(week_key, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""DELETE FROM reservoir_blacklist
                          WHERE week_key = %s AND user_id = %s""",
                       (week_key, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"remove_from_blacklist error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_reservoir_history(user_id, limit=30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT week_key, role, attended
        FROM reservoir_roster
        WHERE user_id = %s
        ORDER BY week_key DESC LIMIT %s
    """, (user_id, limit))
    data = cursor.fetchall()
    conn.close()
    return data


# ============================================================
# КАРТА ШТАТА
# ============================================================

def get_state_legend():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, color, label FROM state_legend ORDER BY id ASC")
    data = cursor.fetchall()
    conn.close()
    return data


def add_state_legend(color, label):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute(
            "INSERT INTO state_legend (color, label, created_at) VALUES (%s, %s, %s) RETURNING id",
            (color, label, now)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    except Exception as e:
        print(f"add_state_legend error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def delete_state_legend(legend_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM state_legend WHERE id = %s", (legend_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"delete_state_legend error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_state_cells():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cell_index, color, label FROM state_cells ORDER BY cell_index ASC")
    data = cursor.fetchall()
    conn.close()
    return data


def save_state_cells(cells_list):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("DELETE FROM state_cells")
        for cell in cells_list:
            idx = int(cell.get('index', 0))
            color = cell.get('color')
            label = cell.get('label')
            cursor.execute("""
                INSERT INTO state_cells (cell_index, color, label, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (idx, color, label, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"save_state_cells error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
