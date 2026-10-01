import os
import base64
from datetime import datetime
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
    # === аккаунты игроков ===
    register_player_account, get_player_account_by_username,
    get_player_account_by_id, get_all_player_accounts,
    check_player_credentials, get_linked_nicknames,
    get_total_rating_for_registration, link_player_nickname,
    unlink_player_nickname, delete_player_account,
    update_player_account_username, update_player_account_password,
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

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    """Возвращает (place, css_class, tier_label, icon) для ника из общего рейтинга."""
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

@app.route('/')
def index():
    count_once('visits', 'counted_visit')
    slides = get_all_slides(only_active=True)
    rating_types = get_all_rating_types()

    for slide in slides:
        if slide[4] and slide[4].startswith('/static/carousel/'):
            rel_path = slide[4].replace('/static/', 'static/', 1)
            if not os.path.exists(rel_path):
                print(f"[WARN] Файл слайда #{slide[0]} не найден: {rel_path}")

    return render_template('index.html',
                           slides=slides,
                           rating_types=rating_types)

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

    return render_template('rating.html',
                           rating=rating_data,
                           rating_type=rating_type,
                           display_name=display_name,
                           rating_types=rating_types)

@app.route('/reservoir-map')
def reservoir_map():
    count_once('visits', 'counted_visit')
    map_values = get_all_map_values()
    return render_template('reservoir_map.html', map_values=map_values)

@app.route('/api/reservoir-map/save', methods=['POST'])
def save_reservoir_map():
    if 'logged_in' not in session or session['username'] != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещён'}), 403
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
def reset_reservoir_map():
    if 'logged_in' not in session or session['username'] != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещён'}), 403
    if reset_map_values():
        increment_counter('admin_actions')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Ошибка сброса'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        if not login or not password:
            flash('Заполните все поля!')
            return redirect(url_for('login'))
        if check_user(login, password):
            session.clear()
            session['logged_in'] = True
            session['username'] = login
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
# АККАУНТЫ ИГРОКОВ — РЕГИСТРАЦИЯ И КАБИНЕТ
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('player_id'):
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
            flash('Логин должен быть не короче 2 символов!')
            return redirect(url_for('register'))
        if len(password) < 4:
            flash('Пароль должен быть не короче 4 символов!')
            return redirect(url_for('register'))

        new_id = register_player_account(username, password)
        if not new_id:
            flash('Такой логин уже занят! Попробуйте другой.')
            return redirect(url_for('register'))

        session['player_id'] = new_id
        session['player_username'] = username
        flash('Аккаунт создан! Теперь выберите себя в списке рейтинга.')
        return redirect(url_for('register_link'))
    return render_template('register.html')

@app.route('/register/link', methods=['GET', 'POST'])
def register_link():
    if not session.get('player_id'):
        return redirect(url_for('register'))

    player_id = session['player_id']
    player = get_player_account_by_id(player_id)
    if not player:
        session.pop('player_id', None)
        return redirect(url_for('register'))

    # Если уже есть привязка — в кабинет
    if player[3]:
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

        if link_player_nickname(player_id, nickname):
            flash(f'Отлично! Вы привязаны к нику «{nickname}».')
            return redirect(url_for('cabinet'))
        else:
            flash('Ошибка при привязке. Попробуйте ещё раз.')
            return redirect(url_for('register_link'))

    all_nicks = get_total_rating_for_registration()
    linked = get_linked_nicknames()
    available = [n for n in all_nicks if n not in linked]

    return render_template('register_link.html',
                           username=player[1],
                           available=available)

@app.route('/cabinet')
def cabinet():
    if not session.get('player_id'):
        return redirect(url_for('register'))

    player = get_player_account_by_id(session['player_id'])
    if not player:
        session.pop('player_id', None)
        return redirect(url_for('register'))

    linked_nickname = player[3]
    rank_data = get_player_rank_data(linked_nickname) if linked_nickname else None

    # Публичное имя для отображения = linked_nickname, если оно есть, иначе username
    display_name = linked_nickname if linked_nickname else player[1]

    return render_template('cabinet.html',
                           player={
                               'id': player[0],
                               'username': player[1],
                               'linked_nickname': player[3],
                               'created_at': player[4],
                           },
                           display_name=display_name,
                           rank_data=rank_data)

@app.route('/cabinet/logout')
def cabinet_logout():
    session.pop('player_id', None)
    session.pop('player_username', None)
    flash('Вы вышли из личного кабинета.')
    return redirect(url_for('index'))

# ============================================================
# АДМИН — УПРАВЛЕНИЕ ИГРОКАМИ
# ============================================================

@app.route('/admin/players')
def admin_players():
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

    accounts = get_all_player_accounts()
    linked = get_linked_nicknames()

    players_view = []
    for acc in accounts:
        rank_data = get_player_rank_data(acc[2]) if acc[2] else None
        players_view.append({
            'id': acc[0],
            'username': acc[1],
            'linked_nickname': acc[2],
            'created_at': acc[3],
            'rank_data': rank_data,
        })

    all_nicks = get_total_rating_for_registration()

    return render_template('admin_players.html',
                           players=players_view,
                           linked=linked,
                           all_nicks=all_nicks)

@app.route('/admin/players/unlink/<int:player_id>', methods=['POST'])
def admin_players_unlink(player_id):
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    if unlink_player_nickname(player_id):
        increment_counter('admin_actions')
        flash('Связь с ником удалена.')
    else:
        flash('Ошибка при отвязке.')
    return redirect(url_for('admin_players'))

@app.route('/admin/players/link/<int:player_id>', methods=['POST'])
def admin_players_link(player_id):
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    nickname = request.form.get('nickname', '').strip()
    if not nickname:
        flash('Выберите ник!')
        return redirect(url_for('admin_players'))
    linked = get_linked_nicknames()
    if nickname in linked:
        flash('Этот ник уже привязан к другому аккаунту.')
        return redirect(url_for('admin_players'))
    if link_player_nickname(player_id, nickname):
        increment_counter('admin_actions')
        flash(f'Привязано: {nickname}')
    else:
        flash('Ошибка при привязке.')
    return redirect(url_for('admin_players'))

@app.route('/admin/players/delete/<int:player_id>', methods=['POST'])
def admin_players_delete(player_id):
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    if delete_player_account(player_id):
        increment_counter('admin_actions')
        flash('Аккаунт игрока удалён.')
    else:
        flash('Ошибка при удалении.')
    return redirect(url_for('admin_players'))

@app.route('/admin/players/change-username/<int:player_id>', methods=['POST'])
def admin_players_change_username(player_id):
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    new_username = request.form.get('new_username', '').strip()
    if not new_username or len(new_username) < 2:
        flash('Новый логин слишком короткий!')
        return redirect(url_for('admin_players'))
    if update_player_account_username(player_id, new_username):
        increment_counter('admin_actions')
        flash(f'Логин изменён на «{new_username}».')
    else:
        flash('Ошибка: возможно, такой логин уже занят.')
    return redirect(url_for('admin_players'))

@app.route('/admin/players/change-password/<int:player_id>', methods=['POST'])
def admin_players_change_password(player_id):
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ запрещён!')
        return redirect(url_for('index'))
    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 4:
        flash('Пароль слишком короткий!')
        return redirect(url_for('admin_players'))
    if update_player_account_password(player_id, new_password):
        increment_counter('admin_actions')
        flash('Пароль изменён.')
    else:
        flash('Ошибка при смене пароля.')
    return redirect(url_for('admin_players'))

# ============================================================
# ДАЛЬШЕ — СУЩЕСТВУЮЩИЕ РОУТЫ (БЕЗ ИЗМЕНЕНИЙ)
# ============================================================

@app.route('/upload/<rating_type>', methods=['POST'])
def upload_file(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))

    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))

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

@app.route('/manage-nicknames', methods=['GET', 'POST'])
def manage_nicknames():
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

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
def reset_rating_route(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    if reset_rating(rating_type):
        increment_counter('admin_actions')
        flash('Рейтинг полностью сброшен!')
    else:
        flash('Ошибка при сбросе рейтинга')
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/delete-player/<rating_type>/<nickname>', methods=['POST'])
def delete_player_route(rating_type, nickname):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    if delete_player(rating_type, nickname):
        increment_counter('admin_actions')
        flash(f'Игрок "{nickname}" удалён!')
    else:
        flash(f'Ошибка при удалении игрока "{nickname}"')
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/rating-stats')
def rating_stats():
    count_once('visits', 'counted_visit')
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

    visit_count = get_counter_value('visits')
    turtle_count = get_counter_value('turtle_calculator')
    hero_count = get_counter_value('hero_calculator')
    chart_count = get_counter_value('chart_views')
    admin_count = get_counter_value('admin_actions')

    return render_template('rating_stats.html',
                           visit_count=visit_count,
                           turtle_count=turtle_count,
                           hero_count=hero_count,
                           chart_count=chart_count,
                           admin_count=admin_count,
                           rating_types=get_all_rating_types())

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

@app.route('/underperforming/<rating_type>')
def underperforming(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))

    underperformers, avg = get_underperforming(rating_type)
    display_name = get_rating_display_name(rating_type)
    return render_template('underperforming.html',
                           underperformers=underperformers,
                           avg=avg,
                           rating_type=rating_type,
                           display_name=display_name)

@app.route('/consistently-underperforming/<rating_type>')
def consistently_underperforming(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))

    players = get_consistently_underperforming(rating_type, 10)
    total_weeks = get_total_weeks(rating_type)
    display_name = get_rating_display_name(rating_type)
    return render_template('consistently.html',
                           players=players,
                           total_weeks=total_weeks,
                           rating_type=rating_type,
                           display_name=display_name)

@app.route('/api/player/<rating_type>/<nickname>')
def api_player_data(rating_type, nickname):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids or rating_type == 'total':
        return jsonify({'error': 'Invalid rating type'}), 400
    history = get_player_history(rating_type, nickname)
    avg_data = get_average_history(rating_type)
    return jsonify({
        'dates': [row[0] for row in history],
        'points': [row[1] for row in history],
        'avg_dates': [row[0] for row in avg_data],
        'avg_points': [row[1] for row in avg_data]
    })

@app.route('/calculator')
def calculator():
    count_once('calculator', 'used_calculator')
    return render_template('calculator.html')

@app.route('/admin/vacations', methods=['GET', 'POST'])
def admin_vacations():
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

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

@app.route('/admin/carousel', methods=['GET', 'POST'])
def admin_carousel():
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

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

@app.route('/admin')
def admin_panel():
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))

    rating_types = get_all_rating_types()
    return render_template('admin.html', rating_types=rating_types)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
else:
    application = app
