import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import psycopg2
from database import (
    init_db, check_user, save_rating, get_latest_rating,
    get_player_history, get_all_players, get_average_history,
    get_underperforming, get_consistently_underperforming,
    get_total_weeks, get_all_time_leaders, get_all_rating_types,
    get_rating_display_name, add_nickname_alias, get_nickname_aliases,
    delete_nickname_alias, reset_rating, delete_player,
    add_vacation_record, get_all_vacation_records, delete_vacation_record,
    create_slide, get_all_slides, get_slide_by_id, update_slide, delete_slide,
    get_all_map_values, save_map_values, reset_map_values,
    get_connection
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

@app.route('/')
def index():
    increment_counter('visits')
    slides = get_all_slides(only_active=True)
    rating_types = get_all_rating_types()
    return render_template('index.html',
                           slides=slides,
                           rating_types=rating_types)

@app.route('/rating/<rating_type>')
def rating_view(rating_type):
    increment_counter('visits')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('rating_view', rating_type='duel'))

    rating_data = get_latest_rating(rating_type)
    leaders = get_all_time_leaders(rating_type)
    display_name = get_rating_display_name(rating_type)

    return render_template('rating.html',
                           rating=rating_data,
                           leaders=leaders,
                           rating_type=rating_type,
                           display_name=display_name,
                           rating_types=rating_types)

@app.route('/reservoir-map')
def reservoir_map():
    increment_counter('visits')
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
            session['logged_in'] = True
            session['username'] = login
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/upload/<rating_type>', methods=['POST'])
def upload_file(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
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

@app.route('/manage-nicknames/<rating_type>', methods=['GET', 'POST'])
def manage_nicknames(rating_type):
    increment_counter('admin_actions')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('index'))

    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            current_nickname = request.form.get('current_nickname', '').strip()
            old_nickname = request.form.get('old_nickname', '').strip()
            if current_nickname and old_nickname:
                if add_nickname_alias(rating_type, current_nickname, old_nickname):
                    flash(f'Связь добавлена: "{old_nickname}" → "{current_nickname}"')
                else:
                    flash('Ошибка при добавлении связи')
            else:
                flash('Заполните оба поля!')
        elif action == 'delete':
            old_nickname = request.form.get('old_nickname')
            if old_nickname:
                delete_nickname_alias(rating_type, old_nickname)
                flash(f'Связь для "{old_nickname}" удалена')
        return redirect(url_for('manage_nicknames', rating_type=rating_type))

    aliases = get_nickname_aliases(rating_type)
    players = get_all_players(rating_type)
    display_name = get_rating_display_name(rating_type)

    return render_template('manage_nicknames.html',
                           rating_type=rating_type,
                           display_name=display_name,
                           aliases=aliases,
                           players=players,
                           rating_types=rating_types)

@app.route('/reset-rating/<rating_type>', methods=['POST'])
def reset_rating_route(rating_type):
    increment_counter('admin_actions')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    if reset_rating(rating_type):
        flash('Рейтинг полностью сброшен!')
    else:
        flash('Ошибка при сбросе рейтинга')
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/delete-player/<rating_type>/<nickname>', methods=['POST'])
def delete_player_route(rating_type, nickname):
    increment_counter('admin_actions')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    if delete_player(rating_type, nickname):
        flash(f'Игрок "{nickname}" удалён!')
    else:
        flash(f'Ошибка при удалении игрока "{nickname}"')
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/rating-stats/<rating_type>')
def rating_stats(rating_type):
    increment_counter('visits')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('index'))

    visit_count = get_counter_value('visits')
    turtle_count = get_counter_value('turtle_calculator')
    hero_count = get_counter_value('hero_calculator')
    chart_count = get_counter_value('chart_views')
    admin_count = get_counter_value('admin_actions')

    display_name = get_rating_display_name(rating_type)

    return render_template('rating_stats.html',
                           rating_type=rating_type,
                           display_name=display_name,
                           visit_count=visit_count,
                           turtle_count=turtle_count,
                           hero_count=hero_count,
                           chart_count=chart_count,
                           admin_count=admin_count,
                           rating_types=rating_types)

@app.route('/player/<rating_type>/<nickname>')
def player_profile(rating_type, nickname):
    increment_counter('chart_views')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('index'))

    history = get_player_history(rating_type, nickname)
    if not history:
        flash('Игрок не найден')
        return redirect(url_for('rating_view', rating_type=rating_type))

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
    increment_counter('admin_actions')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
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
    increment_counter('admin_actions')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
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
    increment_counter('chart_views')
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return jsonify({'error': 'Invalid rating type'}), 400
    history = get_player_history(rating_type, nickname)
    avg_data = get_average_history(rating_type)
    return jsonify({
        'dates': [row[0] for row in history],
        'points': [row[1] for row in history],
        'avg_dates': [row[0] for row in avg_data],
        'avg_points': [row[1] for row in avg_data]
    })

@app.route('/turtle-calculator')
def turtle_calculator():
    increment_counter('turtle_calculator')
    return render_template('turtle_calculator.html')

@app.route('/hero-calculator')
def hero_calculator():
    increment_counter('hero_calculator')
    return render_template('hero_calculator.html')

@app.route('/admin/vacations', methods=['GET', 'POST'])
def admin_vacations():
    increment_counter('admin_actions')
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
                    flash(f'Запись для "{player_name}" добавлена!')
                else:
                    flash('Ошибка при добавлении записи')
            else:
                flash('Заполните обязательные поля!')
        elif action == 'delete':
            record_id = request.form.get('record_id')
            if record_id:
                if delete_vacation_record(int(record_id)):
                    flash('Запись удалена!')
                else:
                    flash('Ошибка при удалении записи')
        return redirect(url_for('admin_vacations'))

    records = get_all_vacation_records()
    return render_template('admin_vacations.html', records=records)

@app.route('/admin/carousel', methods=['GET', 'POST'])
def admin_carousel():
    increment_counter('admin_actions')
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
            position = int(request.form.get('position', 0) or 0)
            if 'media_file' in request.files:
                file = request.files['media_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    filepath = os.path.join(CAROUSEL_FOLDER, unique_name)
                    file.save(filepath)
                    media_url = f"/static/carousel/{unique_name}"
            if content:
                if create_slide(title, content, media_type, media_url, position):
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
            if 'media_file' in request.files:
                file = request.files['media_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    filepath = os.path.join(CAROUSEL_FOLDER, unique_name)
                    file.save(filepath)
                    media_url = f"/static/carousel/{unique_name}"
            if slide_id and content:
                if update_slide(int(slide_id), title, content, media_type, media_url, position, is_active):
                    flash('Слайд обновлен!')
                else:
                    flash('Ошибка при обновлении')
            else:
                flash('Заполните текст слайда!')
        elif action == 'delete':
            slide_id = request.form.get('slide_id')
            if slide_id:
                if delete_slide(int(slide_id)):
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
