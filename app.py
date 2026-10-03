import os
import base64
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import psycopg2
from database import (
    init_db, check_user, save_rating, get_latest_rating, get_total_rating,
    get_player_history, get_all_players, get_average_history,
    get_underperforming, get_consistently_underperforming,
    get_total_weeks, get_all_time_leaders, get_all_rating_types,
    get_rating_display_name, add_nickname_alias, get_nickname_aliases,
    delete_nickname_alias, reset_rating, delete_player,
    add_vacation_record, get_all_vacation_records, delete_vacation_record,
    create_slide, get_all_slides, get_slide_by_id, update_slide, delete_slide,
    get_all_map_values, save_map_values, reset_map_values,
    get_connection,
    get_user_by_id, get_user_by_username, get_all_users,
    register_user, update_user_username, update_user_password,
    update_user_role, link_user_nickname, unlink_user_nickname,
    delete_user, get_linked_nicknames, count_super_admins,
    give_apple, get_apples_given_this_week, get_apples_received_map,
    get_apples_received_for, reset_apples, get_week_key,
    reset_apples_given_by_user,
    get_setting, set_setting,
    update_user_squads, get_user_squads, get_squads_by_nickname_map,
    _iso_week_key, get_or_create_reservoir_week,
    set_reservoir_session_time, set_reservoir_published,
    get_reservoir_week_history,
    get_reservoir_registrations, get_reservoir_registration_for_user,
    add_reservoir_registration, cancel_reservoir_registration,
    get_reservoir_roster, save_reservoir_roster, set_reservoir_attendance,
    get_blacklist_for_week, is_user_blacklisted, remove_from_blacklist,
    get_user_reservoir_history,
    get_last_update_date,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = 'your_secret_key_here_change_it_to_something_secret'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CAROUSEL_FOLDER = os.path.join('static', 'carousel')
if not os.path.exists(CAROUSEL_FOLDER):
    os.makedirs(CAROUSEL_FOLDER)

APPLES_PER_WEEK = 5

init_db()


# ============================================================
# ДЕКОРАТОРЫ
# ============================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def linked_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        if not user[3]:
            flash('Сначала привяжите себя к нику в рейтинге.')
            return redirect(url_for('register_link'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        if session.get('role') not in ('admin', 'super_admin'):
            flash('Доступ только для администратора!')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def super_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        if session.get('role') != 'super_admin':
            flash('Доступ только для супер-администратора!')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def reservoir_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        if session.get('role') not in ('admin', 'super_admin', 'reservoir'):
            flash('Доступ только для администратора резервуара!')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def is_admin():
    return session.get('role') in ('admin', 'super_admin')


def is_super_admin():
    return session.get('role') == 'super_admin'


def can_edit_reservoir():
    return session.get('role') in ('admin', 'super_admin', 'reservoir')


# ============================================================
# УТИЛИТЫ
# ============================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_squad(raw):
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw == '':
        return None

    normalized = raw.replace(',', '.')
    if not re.match(r'^\d*\.?\d*$', normalized):
        return 'err'
    if normalized == '.' or normalized == '':
        return 'err'

    if '.' in normalized:
        int_part, frac_part = normalized.split('.', 1)
        if frac_part == '':
            frac_part = None
        if int_part == '':
            int_part = '0'
    else:
        int_part = normalized
        frac_part = None

    if frac_part is not None:
        frac_part = frac_part[:4]
        if frac_part == '':
            frac_part = None

    if frac_part is None:
        return int_part
    return f"{int_part},{frac_part}"


def save_base64_image(data_url, prefix='poster'):
    if not data_url or ',' not in data_url:
        return None
    try:
        header, encoded = data_url.split(',', 1)
        if 'image' not in header:
            return None
        img_bytes = base64.b64decode(encoded)
        ext = 'jpg'
        if 'png' in header:
            ext = 'png'
        elif 'webp' in header:
            ext = 'webp'
        unique_name = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        filepath = os.path.join(CAROUSEL_FOLDER, unique_name)
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        return f"/static/carousel/{unique_name}"
    except Exception as e:
        print(f"Error saving base64 image: {e}")
        return None


def increment_counter(counter_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO counters (name, value) VALUES (%s, 1)
            ON CONFLICT (name) DO UPDATE SET value = counters.value + 1
        """, (counter_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error incrementing counter: {e}")


def get_counter_value(counter_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM counters WHERE name = %s", (counter_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except:
        return 0


def count_once(counter_name, session_key):
    if session_key not in session:
        session[session_key] = True
        increment_counter(counter_name)


def get_player_rank_data(linked_nickname):
    if not linked_nickname:
        return None
    total = get_total_rating()
    for idx, row in enumerate(total, start=1):
        if row[0] == linked_nickname:
            place = idx
            if place == 1:
                css = 'p1'; tier = 'Алмаз'; icon = '💎'
            elif place <= 3:
                css = 'p2'; tier = 'Золото'; icon = '🥇'
            elif place <= 6:
                css = 'p3'; tier = 'Серебро'; icon = '🥈'
            elif place <= 10:
                css = 'p4'; tier = 'Бронза'; icon = '🥉'
            elif place <= 50:
                css = 'p5'; tier = 'Сталь'; icon = '⚙️'
            else:
                css = 'stone'; tier = 'Камень'; icon = '🪨'
            return {
                'place': place,
                'css_class': css,
                'tier_label': tier,
                'icon': icon,
                'duel_points': row[1],
                'arcadia_points': row[2],
                'total_points': row[3],
            }
    return None


def _registration_status(now=None):
    """
    Возвращает dict:
      {
        'is_open': bool,
        'status': 'soon'|'open'|'closed',
        'message': str,
        'time_left': str | None
      }
    Регистрация открыта с Пн 00:00 до Чт 15:00 текущей ISO-недели.
    """
    now = now or datetime.now()
    weekday = now.weekday()

    is_open = False
    status = 'closed'
    message = ''
    time_left = None

    if weekday == 0:
        is_open = True
        status = 'open'
        end_dt = now.replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=3)
        delta = end_dt - now
        time_left = _human_delta(delta)
        message = f'Регистрация открыта. Осталось: {time_left}'
    elif weekday in (1, 2):
        is_open = True
        status = 'open'
        days_to_thu = 3 - weekday
        end_dt = now.replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=days_to_thu)
        delta = end_dt - now
        time_left = _human_delta(delta)
        message = f'Регистрация открыта. Осталось: {time_left}'
    elif weekday == 3:
        if now.hour < 15:
            is_open = True
            status = 'open'
            end_dt = now.replace(hour=15, minute=0, second=0, microsecond=0)
            delta = end_dt - now
            time_left = _human_delta(delta)
            message = f'Регистрация открыта. Осталось: {time_left}'
        else:
            is_open = False
            status = 'closed'
            message = 'Регистрация закрыта (четверг 15:00)'
    else:
        is_open = False
        status = 'closed'
        days_to_mon = (7 - weekday) % 7
        if days_to_mon == 0:
            days_to_mon = 7
        next_mon = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_to_mon)
        delta = next_mon - now
        time_left = _human_delta(delta)
        message = f'Регистрация закрыта. Откроется через: {time_left}'

    return {
        'is_open': is_open,
        'status': status,
        'message': message,
        'time_left': time_left,
    }


def _human_delta(delta):
    if delta.total_seconds() < 0:
        return '0 мин'
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f'{days} д')
    if hours:
        parts.append(f'{hours} ч')
    if minutes and not days:
        parts.append(f'{minutes} мин')
    return ' '.join(parts) if parts else 'меньше минуты'


def _next_monday_00(now=None):
    now = now or datetime.now()
    wd = now.weekday()
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if wd == 0:
        return base + timedelta(days=7)
    days = 7 - wd
    return base + timedelta(days=days)


# ============================================================
# ГЛАВНАЯ
# ============================================================

@app.route('/')
def index():
    count_once('visits', 'counted_visit')
    slides = get_all_slides(only_active=True)
    rating_types = get_all_rating_types()
    return render_template('index.html', slides=slides, rating_types=rating_types)


# ============================================================
# РЕЙТИНГИ
# ============================================================

@app.route('/rating/<rating_type>')
def rating_view(rating_type):
    count_once('visits', 'counted_visit')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('rating_view', rating_type='total'))

    display_name = get_rating_display_name(rating_type)

    if rating_type == 'total':
        rating_data = get_total_rating()
    else:
        rating_data = get_latest_rating(rating_type)

    apples_map = {}
    squads_map = {}
    my_apples_left = 0
    is_logged_player = False
    my_linked_nickname = None

    if rating_type == 'total':
        apples_map = get_apples_received_map()
        squads_map = get_squads_by_nickname_map()

        if session.get('user_id'):
            user = get_user_by_id(session['user_id'])
            if user and user[3]:
                is_logged_player = True
                my_linked_nickname = user[3]
                given = get_apples_given_this_week(session['user_id'])
                my_apples_left = max(0, APPLES_PER_WEEK - given)

    tooltip_text = get_setting('rating_tooltip_text', '')

    last_update_date = None
    if rating_type in ('duel', 'arcadia'):
        last_update_date = get_last_update_date(rating_type)

    return render_template('rating.html',
                           rating=rating_data,
                           rating_type=rating_type,
                           display_name=display_name,
                           rating_types=rating_types,
                           apples_map=apples_map,
                           squads_map=squads_map,
                           my_apples_left=my_apples_left,
                           is_logged_player=is_logged_player,
                           my_linked_nickname=my_linked_nickname,
                           tooltip_text=tooltip_text,
                           apples_per_week=APPLES_PER_WEEK,
                           last_update_date=last_update_date)


@app.route('/give-apple', methods=['POST'])
def give_apple_route():
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': 'Войдите, чтобы дарить яблоки.'}), 401

    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': 'Пользователь не найден.'}), 401
    if not user[3]:
        return jsonify({'success': False, 'error': 'Сначала привяжите себя к нику.'}), 403

    to_nickname = (request.json or {}).get('nickname', '').strip()
    if not to_nickname:
        return jsonify({'success': False, 'error': 'Не указан ник.'}), 400

    ok, message, remaining = give_apple(session['user_id'], to_nickname)
    if ok:
        total_received = get_apples_received_for(to_nickname)
        return jsonify({
            'success': True,
            'message': message,
            'remaining': remaining,
            'received': total_received
        })
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/player/<rating_type>/<nickname>')
def player_profile(rating_type, nickname):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return redirect(url_for('index'))

    history = get_player_history(rating_type, nickname)
    if not history:
        flash('Игрок не найден')
        return redirect(url_for('rating_view', rating_type=rating_type))

    count_once('chart_views', f'chart_viewed_{rating_type}_{nickname}')

    dates = [row[0] for row in history]
    points = [row[1] for row in history]
    avg_data = get_average_history(rating_type)
    avg_dates = [row[0] for row in avg_data]
    avg_points = [round(row[1], 1) for row in avg_data]

    display_name = get_rating_display_name(rating_type)

    return render_template('player.html',
                           nickname=nickname,
                           rating_type=rating_type,
                           display_name=display_name,
                           dates=dates, points=points,
                           avg_dates=avg_dates, avg_points=avg_points)


# ============================================================
# ВХОД / ВЫХОД
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_ = request.form['login']
        password = request.form['password']
        if not login_ or not password:
            flash('Заполните все поля!')
            return redirect(url_for('login'))
        row = check_user(login_, password)
        if row:
            session['user_id'] = row[0]
            session['username'] = row[1]
            session['role'] = row[2]
            user = get_user_by_id(row[0])
            if user and not user[3] and row[2] != 'super_admin':
                flash('Сначала привяжите себя к нику в рейтинге.')
                return redirect(url_for('register_link'))
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('cabinet'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()

        if not username or not password:
            flash('Заполните все поля!')
            return redirect(url_for('register'))
        if password != password2:
            flash('Пароли не совпадают!')
            return redirect(url_for('register'))
        if len(username) < 2:
            flash('Логин не короче 2 символов!')
            return redirect(url_for('register'))
        if len(password) < 4:
            flash('Пароль не короче 4 символов!')
            return redirect(url_for('register'))

        new_id = register_user(username, password)
        if not new_id:
            flash('Такой логин уже занят!')
            return redirect(url_for('register'))

        session['user_id'] = new_id
        session['username'] = username
        session['role'] = 'player'
        flash('Аккаунт создан! Теперь обязательно выберите себя в списке рейтинга.')
        return redirect(url_for('register_link'))

    return render_template('register.html')


@app.route('/register/link', methods=['GET', 'POST'])
def register_link():
    if not session.get('user_id'):
        return redirect(url_for('register'))

    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('register'))

    if user[3]:
        return redirect(url_for('cabinet'))

    if request.method == 'POST':
        if request.form.get('action') == 'cancel':
            delete_user(session['user_id'])
            session.clear()
            flash('Регистрация отменена. Вы можете зарегистрироваться заново.')
            return redirect(url_for('register'))

        nickname = request.form.get('nickname', '').strip()
        if not nickname:
            flash('Выберите себя в списке!')
            return redirect(url_for('register_link'))

        linked = get_linked_nicknames()
        if nickname in linked:
            flash('Этот ник уже привязан к другому аккаунту.')
            return redirect(url_for('register_link'))

        if link_user_nickname(session['user_id'], nickname):
            flash(f'Отлично! Вы привязаны к нику «{nickname}».')
            return redirect(url_for('cabinet'))
        else:
            flash('Ошибка при привязке. Попробуйте ещё раз.')
            return redirect(url_for('register_link'))

    all_nicks = [row[0] for row in get_total_rating()]
    linked = get_linked_nicknames()
    available = [n for n in all_nicks if n not in linked]

    return render_template('register_link.html',
                           username=user[1],
                           available=available)


# ============================================================
# ЛИЧНЫЙ КАБИНЕТ
# ============================================================

@app.route('/cabinet')
@linked_required
def cabinet():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    user_id, username, _pwd, linked_nickname, role, created_at = user[0:6]
    squads = list(user[6:11]) if len(user) >= 11 else [None]*5

    preview = request.args.get('preview', '').strip()
    rank_data = get_player_rank_data(linked_nickname) if linked_nickname else None

    preview_options = [
        {'key': 'current', 'label': 'Текущий рейтинг'},
        {'key': 'stone',   'label': 'Камень'},
        {'key': 'p5',      'label': 'Сталь'},
        {'key': 'p4',      'label': 'Бронза'},
        {'key': 'p3',      'label': 'Серебро'},
        {'key': 'p2',      'label': 'Золото'},
        {'key': 'p1',      'label': 'Алмаз'},
    ]
    preview_labels = {
        'current': ('Текущий рейтинг', None),
        'stone':   ('Камень',   '🪨'),
        'p5':      ('Сталь',    '⚙️'),
        'p4':      ('Бронза',   '🥉'),
        'p3':      ('Серебро',  '🥈'),
        'p2':      ('Золото',   '🥇'),
        'p1':      ('Алмаз',    '💎'),
    }

    if is_super_admin() and preview and preview in preview_labels:
        lbl, ic = preview_labels[preview]
        if preview == 'current':
            preview_active = 'current'
        else:
            preview_active = preview
            if rank_data:
                rank_data = dict(rank_data)
                rank_data['css_class'] = preview
                rank_data['tier_label'] = lbl
                rank_data['icon'] = ic
            else:
                rank_data = {
                    'place': '—',
                    'css_class': preview,
                    'tier_label': lbl,
                    'icon': ic,
                    'duel_points': 0,
                    'arcadia_points': 0,
                    'total_points': 0,
                }
    else:
        preview_active = 'current'

    display_name = linked_nickname if linked_nickname else username

    given_this_week = get_apples_given_this_week(user_id)
    apples_left = max(0, APPLES_PER_WEEK - given_this_week)
    apples_received = get_apples_received_for(linked_nickname) if linked_nickname else 0

    return render_template('cabinet.html',
                           player={
                               'id': user_id,
                               'username': username,
                               'linked_nickname': linked_nickname,
                               'role': role,
                               'created_at': created_at,
                           },
                           squads=squads,
                           display_name=display_name,
                           rank_data=rank_data,
                           is_admin=is_admin(),
                           is_super_admin=is_super_admin(),
                           preview_options=preview_options,
                           preview_active=preview_active,
                           apples_left=apples_left,
                           apples_received=apples_received,
                           apples_per_week=APPLES_PER_WEEK)


@app.route('/cabinet/save-squads', methods=['POST'])
@linked_required
def cabinet_save_squads():
    user_id = session['user_id']

    raw_values = []
    for i in range(1, 6):
        raw_values.append(request.form.get(f'squad_{i}', ''))

    parsed = []
    error = False
    for raw in raw_values:
        p = _parse_squad(raw)
        if p == 'err':
            error = True
            break
        parsed.append(p)

    if error:
        flash('Введите цифры в формате 100,00 (например, 103,5 или 103.5)')
        return redirect(url_for('cabinet'))

    if update_user_squads(user_id, parsed):
        flash('Боевая мощь отрядов сохранена!')
    else:
        flash('Ошибка при сохранении.')
    return redirect(url_for('cabinet'))


# ============================================================
# РЕЗЕРВУАР — ОСНОВНАЯ СТРАНИЦА
# ============================================================

@app.route('/reservoir')
def reservoir_index():
    count_once('visits', 'counted_visit')

    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    reg_status = _registration_status()

    registrations = get_reservoir_registrations(week_key)
    roster = get_reservoir_roster(week_key)
    blacklist = get_blacklist_for_week(week_key)

    roster_ids = [r[1] for r in roster]

    my_registration = None
    my_blacklist = None
    my_can_register = False
    my_cannot_reason = ''
    my_squad1 = None

    if session.get('user_id'):
        my_registration = get_reservoir_registration_for_user(week_key, session['user_id'])
        my_blacklist = is_user_blacklisted(week_key, session['user_id'])

        user = get_user_by_id(session['user_id'])
        if user:
            my_squad1 = user[6] if len(user) >= 7 else None
            if not user[3]:
                my_cannot_reason = 'Сначала привяжите ник к аккаунту'
            elif not my_squad1:
                my_cannot_reason = 'Сначала заполните мощь 1-го отряда в кабинете'
            elif my_blacklist:
                my_cannot_reason = f'⛔ Чёрная метка — пропуск этой недели ({my_blacklist[1] or "неявка"})'
            elif not reg_status['is_open']:
                my_cannot_reason = reg_status['message']
            elif my_registration:
                my_cannot_reason = 'Вы уже подали заявку'
            else:
                my_can_register = True

    history_weeks = get_reservoir_week_history(limit=30)

    history_data = []
    for hw in history_weeks:
        hw_key = hw[0]
        hw_roster = get_reservoir_roster(hw_key)
        hw_regs = get_reservoir_registrations(hw_key)
        history_data.append({
            'week_key': hw_key,
            'session_time': hw[1],
            'roster_published': hw[2],
            'created_at': hw[3],
            'roster': hw_roster,
            'registrations': hw_regs,
        })

    now = datetime.now()
    iso_weekday = now.isoweekday()
    days_until_sunday = 7 - iso_weekday
    game_date = (now + timedelta(days=days_until_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    MONTHS_RU = [
        '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    game_date_full = f"{game_date.day} {MONTHS_RU[game_date.month]}"

    next_monday = _next_monday_00(now)
    registration_opens_str = next_monday.strftime('%d.%m.%Y в %H:%M')

    return render_template('reservoir.html',
                           week=week,
                           reg_status=reg_status,
                           registrations=registrations,
                           roster=roster,
                           roster_ids=roster_ids,
                           blacklist=blacklist,
                           my_registration=my_registration,
                           my_blacklist=my_blacklist,
                           my_can_register=my_can_register,
                           my_cannot_reason=my_cannot_reason,
                           my_squad1=my_squad1,
                           history_data=history_data,
                           can_edit=can_edit_reservoir(),
                           game_date_full=game_date_full,
                           registration_opens_str=registration_opens_str)


@app.route('/reservoir/map')
def reservoir_map():
    count_once('visits', 'counted_visit')
    map_values = get_all_map_values()
    can_edit = can_edit_reservoir()
    return render_template('reservoir_map.html',
                           map_values=map_values,
                           can_edit_reservoir=can_edit)


# ============================================================
# РЕЗЕРВУАР — ДЕЙСТВИЯ ИГРОКА
# ============================================================

@app.route('/reservoir/register', methods=['POST'])
@linked_required
def reservoir_register():
    user_id = session['user_id']
    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    reg_status = _registration_status()
    if not reg_status['is_open']:
        flash(reg_status['message'])
        return redirect(url_for('reservoir_index'))

    user = get_user_by_id(user_id)
    if not user or not user[3]:
        flash('Сначала привяжите ник к аккаунту.')
        return redirect(url_for('reservoir_index'))

    squad1 = user[6] if len(user) >= 7 else None
    if not squad1:
        flash('Сначала заполните мощь 1-го отряда в личном кабинете.')
        return redirect(url_for('reservoir_index'))

    blacklisted = is_user_blacklisted(week_key, user_id)
    if blacklisted:
        flash(f'⛔ У вас чёрная метка на эту неделю: {blacklisted[1] or "неявка"}')
        return redirect(url_for('reservoir_index'))

    existing = get_reservoir_registration_for_user(week_key, user_id)
    if existing:
        flash('Вы уже подали заявку на эту неделю.')
        return redirect(url_for('reservoir_index'))

    preferred = request.form.get('preferred_session', 'any').strip()
    if preferred not in ('14', '22', 'any'):
        preferred = 'any'

    if add_reservoir_registration(week_key, user_id, preferred):
        flash('✅ Заявка принята!')
    else:
        flash('Ошибка при подаче заявки.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/unregister', methods=['POST'])
@linked_required
def reservoir_unregister():
    user_id = session['user_id']
    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    reg_status = _registration_status()
    if not reg_status['is_open']:
        flash('Регистрация закрыта — отменить заявку уже нельзя.')
        return redirect(url_for('reservoir_index'))

    if cancel_reservoir_registration(week_key, user_id):
        flash('Заявка отменена.')
    else:
        flash('Ошибка при отмене заявки.')
    return redirect(url_for('reservoir_index'))


# ============================================================
# РЕЗЕРВУАР — ДЕЙСТВИЯ УПРАВЛЯЮЩЕГО
# ============================================================

@app.route('/reservoir/admin/set-session', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_set_session():
    session_time = request.form.get('session_time', '').strip()
    if session_time not in ('14', '22'):
        flash('Неверное время сессии.')
        return redirect(url_for('reservoir_index'))

    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    if set_reservoir_session_time(week_key, session_time):
        flash(f'Время сессии изменено на {session_time}:00')
    else:
        flash('Ошибка при смене времени.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/save-roster', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_save_roster():
    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    core_ids = request.form.getlist('core_ids')
    rotation_ids = request.form.getlist('rotation_ids')

    roster_items = []
    try:
        for uid in core_ids:
            roster_items.append({'user_id': int(uid), 'role': 'core'})
        for uid in rotation_ids:
            roster_items.append({'user_id': int(uid), 'role': 'rotation'})
    except Exception as e:
        flash(f'Ошибка в данных формы: {e}')
        return redirect(url_for('reservoir_index'))

    if len(roster_items) > 30:
        flash(f'Слишком много игроков: {len(roster_items)} из 30 максимум.')
        return redirect(url_for('reservoir_index'))

    if save_reservoir_roster(week_key, roster_items):
        flash(f'Состав сохранён ({len(roster_items)} чел.).')
    else:
        flash('Ошибка при сохранении состава.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/publish', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_publish():
    week = get_or_create_reservoir_week()
    week_key = week['week_key']
    if set_reservoir_published(week_key, True):
        flash('Состав опубликован!')
    else:
        flash('Ошибка при публикации.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/unpublish', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_unpublish():
    week = get_or_create_reservoir_week()
    week_key = week['week_key']
    if set_reservoir_published(week_key, False):
        flash('Состав снят с публикации.')
    else:
        flash('Ошибка.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/attendance', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_attendance():
    week_key = request.form.get('week_key', '').strip()
    if not week_key:
        week = get_or_create_reservoir_week()
        week_key = week['week_key']

    user_id = request.form.get('user_id', type=int)
    if not user_id:
        flash('Не указан игрок.')
        return redirect(url_for('reservoir_index'))

    attended_raw = request.form.get('attended', '').strip()
    if attended_raw == '1':
        attended = 1
    elif attended_raw == '0':
        attended = 0
    else:
        attended = None

    if set_reservoir_attendance(week_key, user_id, attended):
        if attended == 0:
            flash('❌ Отмечено: не пришёл. Чёрная метка на следующую неделю.')
        elif attended == 1:
            flash('✅ Отмечено: пришёл.')
        else:
            flash('Отметка снята.')
    else:
        flash('Ошибка при сохранении отметки.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/cancel-registration', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_cancel_registration():
    user_id = request.form.get('user_id', type=int)
    if not user_id:
        flash('Не указан игрок.')
        return redirect(url_for('reservoir_index'))

    week = get_or_create_reservoir_week()
    week_key = week['week_key']

    if cancel_reservoir_registration(week_key, user_id):
        flash('Заявка отменена управляющим.')
    else:
        flash('Ошибка при отмене заявки.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/blacklist-remove', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_blacklist_remove():
    user_id = request.form.get('user_id', type=int)
    week_key = request.form.get('week_key', '').strip()
    if not user_id or not week_key:
        flash('Не указаны данные.')
        return redirect(url_for('reservoir_index'))

    if remove_from_blacklist(week_key, user_id):
        flash('Чёрная метка снята.')
    else:
        flash('Ошибка при снятии метки.')
    return redirect(url_for('reservoir_index'))


@app.route('/reservoir/admin/blacklist-add', methods=['POST'])
@reservoir_or_admin_required
def reservoir_admin_blacklist_add():
    user_id = request.form.get('user_id', type=int)
    week_key = request.form.get('week_key', '').strip()
    reason = request.form.get('reason', '').strip()

    if not user_id:
        flash('Не указан игрок.')
        return redirect(url_for('reservoir_index'))

    if not week_key:
        week = get_or_create_reservoir_week()
        week_key = week['week_key']

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor.execute("""INSERT INTO reservoir_blacklist
                          (user_id, week_key, reason, created_at)
                          VALUES (%s, %s, %s, %s)
                          ON CONFLICT (user_id, week_key) DO UPDATE
                          SET reason = %s""",
                       (user_id, week_key, reason or 'Вручную', now, reason or 'Вручную'))
        conn.commit()
        flash('Чёрная метка поставлена.')
    except Exception as e:
        print(f"blacklist-add error: {e}")
        conn.rollback()
        flash('Ошибка при постановке метки.')
    finally:
        conn.close()

    return redirect(url_for('reservoir_index'))


# ============================================================
# СУПЕР-АДМИН: СМЕНА РОЛЕЙ
# ============================================================

@app.route('/admin/roles/update', methods=['POST'])
@super_admin_required
def admin_roles_update():
    user_id = request.form.get('user_id', type=int)
    new_role = request.form.get('new_role', '').strip()
    if not user_id or new_role not in ('player', 'reservoir', 'admin', 'super_admin'):
        flash('Неверные данные.')
        return redirect(url_for('admin_panel'))

    if user_id == session['user_id'] and new_role != 'super_admin':
        flash('Нельзя понизить самого себя.')
        return redirect(url_for('admin_panel'))

    target = get_user_by_id(user_id)
    if not target:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_panel'))

    if target[4] == 'super_admin' and new_role != 'super_admin' and count_super_admins() <= 1:
        flash('Нельзя понизить последнего супер-администратора.')
        return redirect(url_for('admin_panel'))

    if update_user_role(user_id, new_role):
        increment_counter('admin_actions')
        flash(f'Роль пользователя «{target[1]}» изменена на «{new_role}».')
    else:
        flash('Ошибка при смене роли.')
    return redirect(url_for('admin_panel'))


# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================

@app.route('/admin')
@admin_required
def admin_panel():
    rating_types = get_all_rating_types()
    admin_players = None
    if is_super_admin():
        admin_players = get_all_users()
    return render_template('admin.html',
                           rating_types=rating_types,
                           admin_players=admin_players,
                           is_super_admin=is_super_admin(),
                           current_user_id=session['user_id'])


@app.route('/admin/rating-tooltip', methods=['GET', 'POST'])
@super_admin_required
def admin_rating_tooltip():
    if request.method == 'POST':
        text = request.form.get('tooltip_text', '').strip()
        if set_setting('rating_tooltip_text', text):
            increment_counter('admin_actions')
            flash('Текст тултипа сохранён!')
        else:
            flash('Ошибка при сохранении.')
        return redirect(url_for('admin_rating_tooltip'))

    current = get_setting('rating_tooltip_text', '')
    return render_template('admin_tooltip.html', tooltip_text=current)


@app.route('/admin/reset-apples', methods=['POST'])
@super_admin_required
def admin_reset_apples():
    if reset_apples():
        increment_counter('admin_actions')
        flash('Все яблоки сброшены!')
    else:
        flash('Ошибка при сбросе яблок.')
    return redirect(url_for('admin_panel'))


@app.route('/admin/reset-my-apples', methods=['POST'])
@super_admin_required
def admin_reset_my_apples():
    user_id = session['user_id']
    if reset_apples_given_by_user(user_id):
        increment_counter('admin_actions')
        flash('Ваши отданные яблоки обнулены — можно снова подарить 5 штук!')
    else:
        flash('Ошибка при обнулении.')
    return redirect(url_for('admin_panel'))


@app.route('/admin/players')
@admin_required
def admin_players():
    accounts = get_all_users()
    linked = get_linked_nicknames()
    all_nicks = [row[0] for row in get_total_rating()]

    players_view = []
    for acc in accounts:
        rank_data = get_player_rank_data(acc[2]) if acc[2] else None
        players_view.append({
            'id': acc[0],
            'username': acc[1],
            'linked_nickname': acc[2],
            'role': acc[3],
            'created_at': acc[4],
            'rank_data': rank_data,
        })

    return render_template('admin_players.html',
                           players=players_view,
                           linked=linked,
                           all_nicks=all_nicks,
                           is_super_admin=is_super_admin(),
                           current_user_id=session['user_id'])


@app.route('/admin/players/unlink/<int:user_id>', methods=['POST'])
@admin_required
def admin_players_unlink(user_id):
    if unlink_user_nickname(user_id):
        increment_counter('admin_actions')
        flash('Связь с ником удалена.')
    else:
        flash('Ошибка при отвязке.')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/link/<int:user_id>', methods=['POST'])
@admin_required
def admin_players_link(user_id):
    nickname = request.form.get('nickname', '').strip()
    if not nickname:
        flash('Выберите ник!')
        return redirect(url_for('admin_players'))
    linked = get_linked_nicknames()
    if nickname in linked:
        flash('Этот ник уже привязан к другому аккаунту.')
        return redirect(url_for('admin_players'))
    if link_user_nickname(user_id, nickname):
        increment_counter('admin_actions')
        flash(f'Привязано: {nickname}')
    else:
        flash('Ошибка при привязке.')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_players_delete(user_id):
    target = get_user_by_id(user_id)
    if not target:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_players'))
    if user_id == session['user_id']:
        flash('Нельзя удалить самого себя.')
        return redirect(url_for('admin_players'))
    if target[4] == 'super_admin':
        flash('Нельзя удалить супер-администратора.')
        return redirect(url_for('admin_players'))
    if target[4] == 'admin' and not is_super_admin():
        flash('Только супер-администратор может удалять администраторов.')
        return redirect(url_for('admin_players'))
    if target[4] == 'reservoir' and not is_super_admin():
        flash('Только супер-администратор может удалять роль «Резервуар».')
        return redirect(url_for('admin_players'))
    if delete_user(user_id):
        increment_counter('admin_actions')
        flash('Аккаунт удалён.')
    else:
        flash('Ошибка при удалении.')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/change-username/<int:user_id>', methods=['POST'])
@admin_required
def admin_players_change_username(user_id):
    target = get_user_by_id(user_id)
    if not target:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_players'))
    if target[4] == 'super_admin' and not is_super_admin():
        flash('Только супер-администратор может менять супер-администратора.')
        return redirect(url_for('admin_players'))
    if target[4] in ('admin', 'reservoir') and not is_super_admin() and user_id != session['user_id']:
        flash('Только супер-администратор может менять других администраторов.')
        return redirect(url_for('admin_players'))
    new_username = request.form.get('new_username', '').strip()
    if not new_username or len(new_username) < 2:
        flash('Новый логин слишком короткий!')
        return redirect(url_for('admin_players'))
    if update_user_username(user_id, new_username):
        increment_counter('admin_actions')
        if user_id == session['user_id']:
            session['username'] = new_username
        flash(f'Логин изменён на «{new_username}».')
    else:
        flash('Ошибка: возможно, такой логин уже занят.')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/change-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_players_change_password(user_id):
    target = get_user_by_id(user_id)
    if not target:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_players'))
    if target[4] == 'super_admin' and not is_super_admin():
        flash('Только супер-администратор может менять пароль супер-администратора.')
        return redirect(url_for('admin_players'))
    if target[4] in ('admin', 'reservoir') and not is_super_admin() and user_id != session['user_id']:
        flash('Только супер-администратор может менять пароли других администраторов.')
        return redirect(url_for('admin_players'))
    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 4:
        flash('Пароль слишком короткий!')
        return redirect(url_for('admin_players'))
    if update_user_password(user_id, new_password):
        increment_counter('admin_actions')
        flash('Пароль изменён.')
    else:
        flash('Ошибка при смене пароля.')
    return redirect(url_for('admin_players'))


@app.route('/admin/players/change-role/<int:user_id>', methods=['POST'])
@super_admin_required
def admin_players_change_role(user_id):
    target = get_user_by_id(user_id)
    if not target:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_players'))
    new_role = request.form.get('new_role', '').strip()
    if new_role not in ('player', 'reservoir', 'admin'):
        flash('Неверная роль.')
        return redirect(url_for('admin_players'))
    if user_id == session['user_id']:
        flash('Нельзя менять роль самому себе.')
        return redirect(url_for('admin_players'))
    if update_user_role(user_id, new_role):
        increment_counter('admin_actions')
        flash(f'Роль пользователя «{target[1]}» изменена на «{new_role}».')
    else:
        flash('Ошибка при смене роли.')
    return redirect(url_for('admin_players'))


# ============================================================
# ЗАГРУЗКА РЕЙТИНГА
# ============================================================

@app.route('/upload/<rating_type>', methods=['POST'])
@admin_required
def upload_file(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))

    if 'file' not in request.files:
        flash('Файл не выбран')
        return redirect(url_for('rating_view', rating_type=rating_type))

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран')
        return redirect(url_for('rating_view', rating_type=rating_type))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath, header=None)
            df_clean = df[[0, 3]].dropna()

            rating_list = []
            for index, row in df_clean.iterrows():
                nickname = str(row[0]).strip()
                try:
                    points = float(row[3])
                    points = int(points) if points == int(points) else points
                except:
                    points = 0
                if nickname and points > 0:
                    rating_list.append((nickname, points))

            if not rating_list:
                flash('Не удалось найти данные в колонках A и D.')
                return redirect(url_for('rating_view', rating_type=rating_type))

            save_rating(rating_type, rating_list)
            all_players = get_all_players(rating_type)
            increment_counter('admin_actions')
            flash(f'Рейтинг обновлен! Добавлено {len(rating_list)} записей. Всего: {len(all_players)} игроков.')
        except Exception as e:
            flash(f'Ошибка: {e}')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        return redirect(url_for('rating_view', rating_type=rating_type))
    else:
        flash('Разрешены только .xlsx или .xls')
        return redirect(url_for('rating_view', rating_type=rating_type))


# ============================================================
# УПРАВЛЕНИЕ НИКНЕЙМАМИ
# ============================================================

@app.route('/manage-nicknames', methods=['GET', 'POST'])
@admin_required
def manage_nicknames():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            current_nickname = request.form.get('current_nickname', '').strip()
            old_nickname = request.form.get('old_nickname', '').strip()
            if current_nickname and old_nickname:
                if add_nickname_alias(current_nickname, old_nickname):
                    increment_counter('admin_actions')
                    flash(f'Связь добавлена: "{old_nickname}" → "{current_nickname}"')
                else:
                    flash('Ошибка при добавлении связи')
            else:
                flash('Заполните оба поля!')
        elif action == 'delete':
            old_nickname = request.form.get('old_nickname')
            if old_nickname:
                delete_nickname_alias(old_nickname)
                increment_counter('admin_actions')
                flash(f'Связь для "{old_nickname}" удалена')
        return redirect(url_for('manage_nicknames'))

    aliases = get_nickname_aliases()
    players_duel = get_all_players('duel')
    players_arcadia = get_all_players('arcadia')
    players = sorted(set(players_duel + players_arcadia))

    return render_template('manage_nicknames.html',
                           aliases=aliases,
                           players=players,
                           rating_types=get_all_rating_types())


@app.route('/reset-rating/<rating_type>', methods=['POST'])
@admin_required
def reset_rating_route(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))

    if reset_rating(rating_type):
        increment_counter('admin_actions')
        if rating_type == 'duel':
            flash('Рейтинг Дуэли сброшен. Яблоки и игроки сохранены.')
        elif rating_type == 'arcadia':
            flash('Рейтинг Аркадии сброшен. Яблоки и игроки сохранены.')
        else:
            flash('Рейтинг сброшен.')
    else:
        flash('Ошибка при сбросе рейтинга')

    return redirect(url_for('rating_view', rating_type=rating_type))


@app.route('/delete-player/<rating_type>/<nickname>', methods=['POST'])
@admin_required
def delete_player_route(rating_type, nickname):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    if delete_player(rating_type, nickname):
        increment_counter('admin_actions')
        flash(f'Игрок "{nickname}" удалён!')
    else:
        flash(f'Ошибка при удалении игрока "{nickname}"')
    return redirect(url_for('rating_view', rating_type=rating_type))


# ============================================================
# СТАТИСТИКА
# ============================================================

@app.route('/rating-stats')
@admin_required
def rating_stats():
    count_once('visits', 'counted_visit')
    visit_count = get_counter_value('visits')
    home_count = get_counter_value('home')
    reservoir_count = get_counter_value('reservoir')
    turtle_count = get_counter_value('turtle_calculator')
    hero_count = get_counter_value('hero_calculator')
    chart_count = get_counter_value('chart_views')
    admin_count = get_counter_value('admin_actions')

    return render_template('rating_stats.html',
                           visit_count=visit_count,
                           home_count=home_count,
                           reservoir_count=reservoir_count,
                           turtle_count=turtle_count,
                           hero_count=hero_count,
                           chart_count=chart_count,
                           admin_count=admin_count,
                           rating_types=get_all_rating_types())


# ============================================================
# ОТСТАЮЩИЕ
# ============================================================

@app.route('/underperforming/<rating_type>')
@admin_required
def underperforming(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return redirect(url_for('index'))

    underperformers, avg = get_underperforming(rating_type)
    display_name = get_rating_display_name(rating_type)
    return render_template('underperforming.html',
                           underperformers=underperformers,
                           avg=avg,
                           rating_type=rating_type,
                           display_name=display_name)


@app.route('/consistently-underperforming/<rating_type>')
@admin_required
def consistently_underperforming(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return redirect(url_for('index'))

    players = get_consistently_underperforming(rating_type, 10)
    total_weeks = get_total_weeks(rating_type)
    display_name = get_rating_display_name(rating_type)
    return render_template('consistently.html',
                           players=players,
                           total_weeks=total_weeks,
                           rating_type=rating_type,
                           display_name=display_name)


# ============================================================
# КАРТА РЕЗЕРВУАРА — API
# ============================================================

@app.route('/api/reservoir-map/save', methods=['POST'])
@reservoir_or_admin_required
def save_reservoir_map():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'success': False, 'error': 'Неверные данные'}), 400
        if save_map_values(data):
            increment_counter('admin_actions')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    except Exception as e:
        print(f"Error saving map: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reservoir-map/reset', methods=['POST'])
@reservoir_or_admin_required
def reset_reservoir_map():
    if reset_map_values():
        increment_counter('admin_actions')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Ошибка сброса'}), 500


# ============================================================
# КАЛЬКУЛЯТОР
# ============================================================

@app.route('/calculator')
def calculator():
    count_once('calculator', 'used_calculator')
    return render_template('calculator.html')


# ============================================================
# ЖУРНАЛ ОТПУСКОВ
# ============================================================

@app.route('/admin/vacations', methods=['GET', 'POST'])
@admin_required
def admin_vacations():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            player_name = request.form.get('player_name', '').strip()
            comment = request.form.get('comment', '').strip()
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            if player_name and start_date and end_date:
                if add_vacation_record(player_name, comment, start_date, end_date, session['username']):
                    increment_counter('admin_actions')
                    flash(f'Запись для "{player_name}" добавлена!')
                else:
                    flash('Ошибка при добавлении записи')
            else:
                flash('Заполните обязательные поля!')
        elif action == 'delete':
            record_id = request.form.get('record_id')
            if record_id:
                if delete_vacation_record(int(record_id)):
                    increment_counter('admin_actions')
                    flash('Запись удалена!')
                else:
                    flash('Ошибка при удалении записи')
        return redirect(url_for('admin_vacations'))

    records = get_all_vacation_records()
    return render_template('admin_vacations.html', records=records)


# ============================================================
# КАРУСЕЛЬ
# ============================================================

@app.route('/admin/carousel', methods=['GET', 'POST'])
@admin_required
def admin_carousel():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            media_type = request.form.get('media_type', 'image')
            media_url = request.form.get('media_url', '').strip()
            poster_url = None
            position = int(request.form.get('position', 0) or 0)

            if 'media_file' in request.files:
                file = request.files['media_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    filepath = os.path.join(CAROUSEL_FOLDER, unique_name)
                    file.save(filepath)
                    media_url = f"/static/carousel/{unique_name}"

            poster_data = request.form.get('poster_data', '').strip()
            if poster_data:
                poster_url = save_base64_image(poster_data, prefix='poster')

            if content:
                if create_slide(title, content, media_type, media_url, position, poster_url):
                    increment_counter('admin_actions')
                    flash('Слайд добавлен!')
                else:
                    flash('Ошибка при добавлении слайда')
            else:
                flash('Заполните текст слайда!')
        elif action == 'update':
            slide_id = request.form.get('slide_id')
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            media_type = request.form.get('media_type', 'image')
            media_url = request.form.get('media_url', '').strip()
            position = int(request.form.get('position', 0) or 0)
            is_active = request.form.get('is_active') == 'on'

            existing = get_slide_by_id(int(slide_id)) if slide_id else None
            poster_url = existing[9] if existing and len(existing) > 9 else None

            if 'media_file' in request.files:
                file = request.files['media_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    filepath = os.path.join(CAROUSEL_FOLDER, unique_name)
                    file.save(filepath)
                    media_url = f"/static/carousel/{unique_name}"

            poster_data = request.form.get('poster_data', '').strip()
            if poster_data:
                new_poster = save_base64_image(poster_data, prefix='poster')
                if new_poster:
                    poster_url = new_poster

            if request.form.get('remove_poster') == '1':
                poster_url = None

            if slide_id and content:
                if update_slide(int(slide_id), title, content, media_type, media_url, position, is_active, poster_url):
                    increment_counter('admin_actions')
                    flash('Слайд обновлен!')
                else:
                    flash('Ошибка при обновлении')
            else:
                flash('Заполните текст слайда!')
        elif action == 'delete':
            slide_id = request.form.get('slide_id')
            if slide_id:
                if delete_slide(int(slide_id)):
                    increment_counter('admin_actions')
                    flash('Слайд удален!')
                else:
                    flash('Ошибка при удалении')
        return redirect(url_for('admin_carousel'))

    slides = get_all_slides()
    return render_template('admin_carousel.html', slides=slides)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
else:
    application = app
