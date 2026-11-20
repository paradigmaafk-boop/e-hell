import os
import base64
import json
import mimetypes
import re
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, Response)
import pandas as pd
from database import (
    init_db, check_user, save_rating, get_latest_rating, get_total_rating,
    get_player_history, get_all_players, get_average_history,
    get_nicknames_with_history, get_total_player_history, get_total_average_history,
    get_underperforming, get_consistently_underperforming,
    get_total_weeks, get_all_rating_types,
    get_rating_display_name, add_nickname_alias, get_nickname_aliases,
    get_alias_resolutions,
    delete_nickname_alias, reset_rating, delete_player, delete_player_from_all_ratings,
    add_vacation_record, get_all_vacation_records, delete_vacation_record,
    create_slide, get_all_slides, get_slide_by_id, update_slide, delete_slide,
    create_media_asset, get_media_assets, get_media_asset,
    delete_media_asset, count_media_asset_usage, migrate_static_media_urls,
    clear_slide_media,
    get_connection,
    get_user_by_id, get_all_users,
    register_user, update_user_username, update_user_password,
    update_user_role, link_user_nickname, unlink_user_nickname,
    delete_user, get_linked_nicknames, count_super_admins,
    give_apple, get_apples_given_this_week, get_apples_received_map,
    get_apples_received_for, get_apple_givers_for, reset_apples,
    reset_apples_given_by_user,
    get_setting, set_setting,
    update_user_squads, get_squads_by_nickname_map,
    get_last_update_date,
    associate_players, get_all_merge_records,
    get_all_duel_players_with_points,
    get_all_arcadia_players_with_points,
    # Карта штата:
    get_state_legend, add_state_legend, delete_state_legend,
    get_state_cells, save_state_cells,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here_change_it_to_something_secret')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

# Медиа для карусели храним в БД: файловая система контейнера
# очищается при каждом передеплое.
ALLOWED_MEDIA_EXTENSIONS = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'gif': 'image/gif',
    'avif': 'image/avif',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'ogg': 'video/ogg',
}

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
        session['linked_nickname'] = user[3]
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Полный админ: admin + super_admin. НЕ пропускает state_admin."""
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


def state_access_required(f):
    """Раздел «Штат» доступен только авторизованным пользователям
    с привязанным к аккаунту ником."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы открыть раздел «Штат».')
            return redirect(url_for('login'))
        user = get_user_by_id(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        if not user[3]:
            flash('Раздел «Штат» доступен только участникам с привязанным ником.')
            return redirect(url_for('register_link'))
        session['linked_nickname'] = user[3]
        return f(*args, **kwargs)
    return wrapper


def state_editor_required(f):
    """Доступ к редактированию карты штата: admin, super_admin, state_admin."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Войдите, чтобы продолжить.')
            return redirect(url_for('login'))
        if session.get('role') not in ('admin', 'super_admin', 'state_admin'):
            flash('Доступ только для администратора штата!')
            return redirect(url_for('index'))
        user = get_user_by_id(session['user_id'])
        if not user or not user[3]:
            flash('Редактировать карту штата могут только пользователи с привязанным ником.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def is_admin():
    return session.get('role') in ('admin', 'super_admin')


def is_super_admin():
    return session.get('role') == 'super_admin'


def is_state_admin():
    return session.get('role') == 'state_admin'


def can_edit_state():
    return session.get('role') in ('admin', 'super_admin', 'state_admin')


def _state_legend_to_json():
    """Возвращает легенду в виде списка словарей {id, color, label}."""
    rows = get_state_legend()
    return [
        {'id': row[0], 'color': row[1], 'label': row[2]}
        for row in rows
    ]


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


def _media_mime(filename):
    ext = (filename.rsplit('.', 1)[1].lower() if '.' in filename else '')
    return ALLOWED_MEDIA_EXTENSIONS.get(ext)


def _safe_media_name(filename):
    filename = filename or ''
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'bin'
    safe = secure_filename(filename)
    # secure_filename может выбросить кириллическое имя целиком.
    if not safe or '.' not in safe or safe.rsplit('.', 1)[1].lower() != ext:
        safe = f"media_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
    return safe


def save_media_bytes(filename, data, mime_type, uploaded_by=''):
    asset_id = create_media_asset(filename, mime_type, data, uploaded_by)
    return f"/media/{asset_id}" if asset_id else None


def save_uploaded_media(file, uploaded_by=''):
    """Сохраняет загруженный файл в БД. Возвращает (url, error)."""
    if not file or not file.filename:
        return None, 'Файл не выбран.'
    filename = _safe_media_name(file.filename)
    mime_type = _media_mime(filename)
    if not mime_type:
        return None, 'Разрешены только изображения и видео (png, jpg, webp, gif, mp4, webm, ogg).'
    data = file.read()
    if not data:
        return None, 'Пустой файл.'
    url = save_media_bytes(filename, data, mime_type, uploaded_by)
    if not url:
        return None, 'Не удалось сохранить файл в альбом.'
    return url, None


def save_base64_media(data_url, prefix='poster'):
    if not data_url or ',' not in data_url:
        return None
    try:
        header, encoded = data_url.split(',', 1)
        if 'image' not in header:
            return None
        img_bytes = base64.b64decode(encoded)
        ext = 'jpg'
        mime_type = 'image/jpeg'
        if 'png' in header:
            ext, mime_type = 'png', 'image/png'
        elif 'webp' in header:
            ext, mime_type = 'webp', 'image/webp'
        unique_name = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
        return save_media_bytes(unique_name, img_bytes, mime_type, 'carousel')
    except Exception as e:
        print(f"Error saving base64 media: {e}")
        return None


def import_carousel_seed():
    """Импортирует файлы из static/carousel в БД и переводит слайды на /media/<id>.

    Нужно один раз после перехода на медиа-альбом: так уже загруженные
    фотографии не пропадут при следующем передеплое.
    """
    if not os.path.isdir(CAROUSEL_FOLDER):
        return 0

    try:
        if get_setting('carousel_seed_imported', '') == '1':
            return 0
    except Exception as e:
        print(f"seed media setting check skipped: {e}")

    # Если все слайды уже переведены на /media/, повторно 27 МБ не читаем.
    try:
        slides = get_all_slides()
        has_static = any(
            (s[4] or '').startswith('/static/carousel/')
            or (len(s) > 9 and (s[9] or '').startswith('/static/carousel/'))
            for s in slides
        )
        if not has_static:
            set_setting('carousel_seed_imported', '1')
            return 0
    except Exception as e:
        print(f"seed media check skipped: {e}")

    mapping = {}
    failed = 0
    for name in os.listdir(CAROUSEL_FOLDER):
        path = os.path.join(CAROUSEL_FOLDER, name)
        if not os.path.isfile(path):
            continue
        mime_type = _media_mime(name)
        if not mime_type:
            continue
        try:
            with open(path, 'rb') as f:
                data = f.read()
            asset_id = create_media_asset(name, mime_type, data, 'seed')
            if asset_id:
                mapping[f'/static/carousel/{name}'] = f'/media/{asset_id}'
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"seed media import skipped for {name}: {e}")
    updated = migrate_static_media_urls(mapping)
    if mapping and not failed:
        try:
            set_setting('carousel_seed_imported', '1')
        except Exception as e:
            print(f"seed media setting save skipped: {e}")
    return updated


def cleanup_missing_static_slides():
    """Убирает ссылки на статические файлы, которых уже нет на диске.

    Иначе в карусели остаётся битая картинка. Текст слайда сохраняется.
    """
    try:
        slides = get_all_slides()
    except Exception as e:
        print(f"cleanup static slides skipped: {e}")
        return 0
    cleared = 0
    for slide in slides:
        url = slide[4] or ''
        if not url.startswith('/static/carousel/'):
            continue
        name = os.path.basename(url.split('?', 1)[0])
        if not name or os.path.exists(os.path.join(CAROUSEL_FOLDER, name)):
            continue
        if clear_slide_media(slide[0]):
            cleared += 1
    return cleared


# Импортируем уже загруженные фото в БД при старте приложения.
try:
    import_carousel_seed()
    cleanup_missing_static_slides()
except Exception as _media_seed_error:
    print(f"carousel seed import failed: {_media_seed_error}")


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


@app.context_processor
def inject_navigation_state():
    """Даёт шаблонам единый признак доступа к разделу «Штат».

    Ссылка на раздел показывается только авторизованным пользователям,
    у которых аккаунт привязан к нику в рейтинге.
    """
    user_id = session.get('user_id')
    linked = session.get('linked_nickname')
    if user_id and linked is None:
        user = get_user_by_id(user_id)
        linked = user[3] if user else None
        session['linked_nickname'] = linked or ''
    return {
        'state_available': bool(user_id and linked),
        'current_linked_nickname': linked or '',
    }


# ============================================================
# ГЛАВНАЯ
# ============================================================

@app.route('/favicon.ico')
def favicon_ico():
    # Старые страницы/браузеры всё ещё спрашивают /favicon.ico.
    return app.send_static_file('favicon.svg')


@app.route('/media/<int:asset_id>')
def media_file(asset_id):
    asset = get_media_asset(asset_id)
    if not asset:
        return 'Файл не найден', 404
    _, filename, mime_type, data, _size, _created, _uploaded_by = asset
    response = Response(data, mimetype=mime_type)
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@app.errorhandler(413)
def file_too_large(_error):
    flash('Суммарный размер файлов больше 64 МБ. Загрузите файлы меньшими частями.')
    return redirect(url_for('admin_media'))


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

    # Для общего рейтинга подсказываем, в каком разделе у игрока есть история:
    # иначе ссылка на график вела в «пустой» раздел и выдавала «Игрок не найден».
    chart_types = {}
    if rating_type == 'total':
        duel_nicks = get_nicknames_with_history('duel')
        arcadia_nicks = get_nicknames_with_history('arcadia')
        for row in rating_data:
            nick = row[0]
            if nick in duel_nicks:
                chart_types[nick] = 'duel'
            elif nick in arcadia_nicks:
                chart_types[nick] = 'arcadia'

    apples_map = {}
    squads_map = {}
    my_apples_left = 0
    is_logged_player = False
    my_linked_nickname = None
    all_duel_players = []
    all_arcadia_players = []

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

        if session.get('role') in ('admin', 'super_admin'):
            all_duel_players = get_all_duel_players_with_points()
            all_arcadia_players = get_all_arcadia_players_with_points()

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
                           last_update_date=last_update_date,
                           chart_types=chart_types,
                           all_duel_players=all_duel_players,
                           all_arcadia_players=all_arcadia_players)


@app.route('/merge-player', methods=['POST'])
@app.route('/associate-player', methods=['POST'])  # старый адрес для совместимости
@admin_required
def merge_player_route():
    data = request.get_json() or {}
    target = (data.get('target') or '').strip()
    duel_nicks = data.get('duel_nicks') or []
    arcadia_nicks = data.get('arcadia_nicks') or []

    if not target:
        return jsonify({'success': False, 'error': 'Не указан игрок.'}), 400

    ok, msg = associate_players(target, duel_nicks, arcadia_nicks, session.get('username', ''))
    if ok:
        increment_counter('admin_actions')
        return jsonify({'success': True, 'message': msg})
    else:
        return jsonify({'success': False, 'error': msg}), 400


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
    if rating_type not in rt_ids:
        return redirect(url_for('index'))

    if rating_type == 'total':
        history = get_total_player_history(nickname)
        avg_data = get_total_average_history()
        series_label = f'{nickname} — сумма Дуэли и Аркадии'
    else:
        history = get_player_history(rating_type, nickname)
        avg_data = get_average_history(rating_type)
        series_label = nickname

    if not history:
        flash('У этого игрока пока нет истории замеров.')
        return redirect(url_for('rating_view', rating_type=rating_type))

    count_once('chart_views', f'chart_viewed_{rating_type}_{nickname}')

    dates = [row[0] for row in history]
    points = [row[1] for row in history]
    avg_by_date = {str(row[0]): round(row[1], 1) for row in avg_data}
    # Выравниваем среднее по датам игрока, иначе линии на графике
    # рисовались по разным неделям и не совпадали.
    avg_points = [avg_by_date.get(str(d)) for d in dates]

    display_name = get_rating_display_name(rating_type)

    return render_template('player.html',
                           nickname=nickname,
                           rating_type=rating_type,
                           display_name=display_name,
                           series_label=series_label,
                           dates=dates, points=points,
                           avg_dates=[row[0] for row in avg_data],
                           avg_points=avg_points)


# ============================================================
# ВХОД / ВЫХОД
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_ = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        if not login_ or not password:
            flash('Заполните все поля!')
            return redirect(url_for('login'))
        row = check_user(login_, password)
        if row:
            session['user_id'] = row[0]
            session['username'] = row[1]
            session['role'] = row[2]
            user = get_user_by_id(row[0])
            session['linked_nickname'] = (user[3] if user and user[3] else '')
            if user and not user[3] and row[2] not in ('super_admin', 'state_admin'):
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
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

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
        session['linked_nickname'] = ''
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
        nickname = request.form.get('nickname', '').strip()
        if not nickname:
            flash('Выберите себя в списке!')
            return redirect(url_for('register_link'))

        linked = get_linked_nicknames()
        if nickname in linked:
            flash('Этот ник уже привязан к другому аккаунту.')
            return redirect(url_for('register_link'))

        if link_user_nickname(session['user_id'], nickname):
            session['linked_nickname'] = nickname
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
    session['linked_nickname'] = linked_nickname or ''

    # Ссылки на графики показываем только там, где у игрока есть история,
    # иначе переход выдавал «Игрок не найден».
    has_duel_history = bool(linked_nickname and get_player_history('duel', linked_nickname))
    has_arcadia_history = bool(linked_nickname and get_player_history('arcadia', linked_nickname))

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
    apple_givers = get_apple_givers_for(linked_nickname) if linked_nickname else []

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
                           has_duel_history=has_duel_history,
                           has_arcadia_history=has_arcadia_history,
                           is_admin=is_admin(),
                           is_super_admin=is_super_admin(),
                           preview_options=preview_options,
                           preview_active=preview_active,
                           apples_left=apples_left,
                           apples_received=apples_received,
                           apple_givers=apple_givers,
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
# РЕЗЕРВУАР — РАЗДЕЛ УДАЛЁН
# ============================================================
# Страница убрана с сайта. Данные резервуара (таблицы reservoir_*),
# заявки, состав и чёрные метки остаются в базе без изменений.
# Старые ссылки и закладки мягко возвращают на главную.

@app.route('/reservoir')
@app.route('/reservoir/<path:subpath>')
def reservoir_removed(subpath=None):
    return redirect(url_for('index'), code=301)


# ============================================================
# СУПЕР-АДМИН: СМЕНА РОЛЕЙ
# ============================================================

@app.route('/admin/roles/update', methods=['POST'])
@super_admin_required
def admin_roles_update():
    user_id = request.form.get('user_id', type=int)
    new_role = request.form.get('new_role', '').strip()
    if not user_id or new_role not in ('player', 'reservoir', 'state_admin', 'admin', 'super_admin'):
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


@app.route('/admin/reset-state-tables', methods=['POST'])
@super_admin_required
def admin_reset_state_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS state_cells")
        cursor.execute("DROP TABLE IF EXISTS state_legend")

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
        conn.commit()

        increment_counter('admin_actions')
        flash('✅ Таблицы карты штата пересозданы. Данные очищены.')
    except Exception as e:
        print(f"reset_state_tables error: {e}")
        conn.rollback()
        flash(f'❌ Ошибка: {e}')
    finally:
        conn.close()

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
        if user_id == session.get('user_id'):
            session['linked_nickname'] = ''
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
        if user_id == session.get('user_id'):
            session['linked_nickname'] = nickname
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
    if target[4] in ('reservoir', 'state_admin') and not is_super_admin():
        flash('Только супер-администратор может удалять эту роль.')
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
    if target[4] in ('admin', 'reservoir', 'state_admin') and not is_super_admin() and user_id != session['user_id']:
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
    if target[4] in ('admin', 'reservoir', 'state_admin') and not is_super_admin() and user_id != session['user_id']:
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
    if new_role not in ('player', 'reservoir', 'state_admin', 'admin'):
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
            hidden_rows = set()
            try:
                if filepath.lower().endswith('.xlsx'):
                    from openpyxl import load_workbook
                    wb = load_workbook(filepath, data_only=True, read_only=False)
                    ws = wb.active
                    # Скрытые строки Excel не должны попадать в рейтинг:
                    # пользователь их не видит, а pandas их читает.
                    hidden_rows = {
                        idx for idx, dim in ws.row_dimensions.items() if dim.hidden
                    }
                    wb.close()
            except Exception as e:
                print(f"hidden rows check skipped: {e}")

            df = pd.read_excel(filepath, header=None)
            df_clean = df[[0, 3]].dropna()

            rating_list = []
            skipped_hidden = 0
            for index, row in df_clean.iterrows():
                excel_row = index + 1
                if excel_row in hidden_rows:
                    skipped_hidden += 1
                    continue
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

            uploaded_names = {nickname for nickname, _ in rating_list}
            alias_pairs = get_alias_resolutions(uploaded_names)
            missing_targets = sorted({new for _, new in alias_pairs if new not in uploaded_names})

            if not save_rating(rating_type, rating_list):
                flash('Не удалось сохранить рейтинг. Изменения отменены.')
                return redirect(url_for('rating_view', rating_type=rating_type))

            all_players = get_all_players(rating_type)
            increment_counter('admin_actions')
            flash(f'Рейтинг обновлен! Добавлено {len(rating_list)} записей. Всего: {len(all_players)} игроков.')

            if skipped_hidden:
                flash(f'Пропущено скрытых строк Excel: {skipped_hidden}.')

            if alias_pairs:
                shown = ', '.join(f'{old} → {new}' for old, new in alias_pairs[:6])
                if len(alias_pairs) > 6:
                    shown += f' и ещё {len(alias_pairs) - 6}'
                flash(f'Применены связи ников: {shown}.')

            if missing_targets:
                shown = ', '.join(missing_targets[:6])
                if len(missing_targets) > 6:
                    shown += f' и ещё {len(missing_targets) - 6}'
                flash(
                    f'Внимание: в таблице нет ников «{shown}», но очки по связям ушли на них. '
                    'Если это ошибка, удалите лишнюю связь в «Управлении никнеймами» '
                    'или удалите эту строку из рейтинга — связь удалится вместе с ней.'
                )
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


@app.route('/delete-total-player/<nickname>', methods=['POST'])
@admin_required
def delete_total_player_route(nickname):
    """Удаляет строку из общего рейтинга: результаты и история обеих дисциплин."""
    if delete_player_from_all_ratings(nickname):
        increment_counter('admin_actions')
        flash(f'Игрок "{nickname}" удалён из общего рейтинга (Дуэль и Аркадия).')
    else:
        flash(f'Ошибка при удалении игрока "{nickname}"')
    return redirect(url_for('rating_view', rating_type='total'))


# ============================================================
# СТАТИСТИКА
# ============================================================

@app.route('/rating-stats')
@admin_required
def rating_stats():
    count_once('visits', 'counted_visit')
    visit_count = get_counter_value('visits')
    home_count = get_counter_value('home')
    turtle_count = get_counter_value('turtle_calculator')
    hero_count = get_counter_value('hero_calculator')
    chart_count = get_counter_value('chart_views')
    admin_count = get_counter_value('admin_actions')

    return render_template('rating_stats.html',
                           visit_count=visit_count,
                           home_count=home_count,
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
# КАРТА ШТАТА
# ============================================================

@app.route('/state')
@state_access_required
def state_view():
    count_once('visits', 'counted_visit')
    legend = get_state_legend()
    cells = get_state_cells()
    can_edit = can_edit_state()
    return render_template('state.html',
                           legend=legend,
                           cells=cells,
                           can_edit_state=can_edit)


@app.route('/state/export')
@state_editor_required
def state_export():
    """Резервная копия карты штата (легенда + ячейки) без изменения данных."""
    backup = {
        'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'legend': _state_legend_to_json(),
        'cells': [
            {'index': row[0], 'color': row[1], 'label': row[2]}
            for row in get_state_cells()
        ],
    }
    return Response(
        json.dumps(backup, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': 'attachment; filename=state-map-backup.json'
        },
    )


@app.route('/state/legend/add', methods=['POST'])
@state_editor_required
def state_legend_add():
    data = request.get_json() or {}
    color = (data.get('color') or '').strip()
    label = (data.get('label') or '').strip()
    if not color or not label:
        return jsonify({'success': False, 'error': 'Цвет и название обязательны'}), 400
    new_id = add_state_legend(color, label)
    if new_id:
        increment_counter('admin_actions')
        return jsonify({'success': True, 'legend': _state_legend_to_json()})
    return jsonify({'success': False, 'error': 'Ошибка добавления'}), 500


@app.route('/state/legend/delete/<int:legend_id>', methods=['POST'])
@state_editor_required
def state_legend_delete(legend_id):
    if delete_state_legend(legend_id):
        increment_counter('admin_actions')
        return jsonify({'success': True, 'legend': _state_legend_to_json()})
    return jsonify({'success': False, 'error': 'Ошибка удаления'}), 500


@app.route('/state/save', methods=['POST'])
@state_editor_required
def state_save():
    data = request.get_json() or {}
    cells = data.get('cells') or []
    if save_state_cells(cells):
        increment_counter('admin_actions')
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500


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

@app.route('/admin/merges')
@admin_required
def admin_merges():
    return render_template('admin_merges.html', records=get_all_merge_records())


@app.route('/admin/media', methods=['GET', 'POST'])
@admin_required
def admin_media():
    if request.method == 'POST':
        action = request.form.get('action', 'upload')
        if action == 'delete':
            asset_id = request.form.get('asset_id', type=int)
            if not asset_id:
                flash('Файл не указан.')
            elif count_media_asset_usage(asset_id):
                flash('Этот файл используется в слайде карусели. Сначала замените его в слайде.')
            elif delete_media_asset(asset_id):
                increment_counter('admin_actions')
                flash('Файл удалён из альбома.')
            else:
                flash('Ошибка при удалении файла.')
            return redirect(url_for('admin_media'))

        files = request.files.getlist('files')
        if not files or all(not f.filename for f in files):
            flash('Выберите файлы для загрузки.')
            return redirect(url_for('admin_media'))

        saved = 0
        errors = []
        for file in files:
            if not file or not file.filename:
                continue
            _url, error = save_uploaded_media(file, session.get('username', ''))
            if error:
                errors.append(f'{file.filename}: {error}')
            else:
                saved += 1
        if saved:
            increment_counter('admin_actions')
            flash(f'Загружено в альбом: {saved}.')
        for error in errors[:5]:
            flash(error)
        return redirect(url_for('admin_media'))

    return render_template('admin_media.html', assets=get_media_assets())


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
                    uploaded_url, upload_error = save_uploaded_media(file, session.get('username', ''))
                    if uploaded_url:
                        media_url = uploaded_url
                    else:
                        flash(upload_error or 'Не удалось загрузить файл.')

            poster_data = request.form.get('poster_data', '').strip()
            if poster_data:
                poster_url = save_base64_media(poster_data, prefix='poster')

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
                    uploaded_url, upload_error = save_uploaded_media(file, session.get('username', ''))
                    if uploaded_url:
                        media_url = uploaded_url
                    else:
                        flash(upload_error or 'Не удалось загрузить файл.')

            poster_data = request.form.get('poster_data', '').strip()
            if poster_data:
                new_poster = save_base64_media(poster_data, prefix='poster')
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
    return render_template('admin_carousel.html', slides=slides, media_assets=get_media_assets())


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
else:
    application = app
