from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import os
import sqlite3
from database import (
    init_db, check_user, save_rating, get_latest_rating, 
    get_player_history, get_all_players, get_average_history, 
    get_underperforming, get_consistently_underperforming, 
    get_total_weeks, get_all_time_leaders, get_all_rating_types, 
    get_rating_display_name, add_nickname_alias, get_nickname_aliases,
    delete_nickname_alias, reset_rating, get_total_weeks_for_player,
    get_player_average_points, delete_player,
    create_guide, get_all_guides, get_guide_by_id, update_guide, delete_guide
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_it_to_something_secret'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('rating_view', rating_type='duel'))

@app.route('/rating/<rating_type>')
def rating_view(rating_type):
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('rating_view', rating_type='duel'))
    
    rating_data = get_latest_rating(rating_type)
    leaders = get_all_time_leaders(rating_type)
    display_name = get_rating_display_name(rating_type)
    
    return render_template('index.html', 
                           rating=rating_data, 
                           leaders=leaders,
                           rating_type=rating_type,
                           display_name=display_name,
                           rating_types=rating_types)

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
            df_clean = df[[1, 3]].dropna()
            
            rating_list = []
            for index, row in df_clean.iterrows():
                nickname = str(row[1]).strip()
                try:
                    points = int(float(row[3]))
                except:
                    points = 0
                if nickname and points > 0:
                    rating_list.append((nickname, points))
            
            if not rating_list:
                flash('Не удалось найти данные в колонках B и D.')
                return redirect(url_for('rating_view', rating_type=rating_type))
                
            save_rating(rating_type, rating_list)
            all_players = get_all_players(rating_type)
            flash(f'✅ Рейтинг обновлен! Добавлено {len(rating_list)} записей. Всего в рейтинге: {len(all_players)} игроков. Очки СУММИРУЮТСЯ!')
            
        except Exception as e:
            flash(f'❌ Ошибка: {e}')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
                
        return redirect(url_for('rating_view', rating_type=rating_type))
    else:
        flash('Разрешены только .xlsx или .xls')
        return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/manage-nicknames/<rating_type>', methods=['GET', 'POST'])
def manage_nicknames(rating_type):
    """Страница управления псевдонимами никнеймов"""
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
                    flash(f'✅ Связь добавлена: "{old_nickname}" → "{current_nickname}"')
                else:
                    flash('❌ Ошибка при добавлении связи')
            else:
                flash('❌ Заполните оба поля!')
        
        elif action == 'delete':
            old_nickname = request.form.get('old_nickname')
            if old_nickname:
                delete_nickname_alias(rating_type, old_nickname)
                flash(f'✅ Связь для "{old_nickname}" удалена')
        
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
    """Сброс рейтинга (только для админа)"""
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    
    if reset_rating(rating_type):
        flash('✅ Рейтинг полностью сброшен!')
    else:
        flash('❌ Ошибка при сбросе рейтинга')
    
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/delete-player/<rating_type>/<nickname>', methods=['POST'])
def delete_player_route(rating_type, nickname):
    """Удаляет игрока и всю его историю (только для админа)"""
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        flash('Неверный тип рейтинга!')
        return redirect(url_for('index'))
    
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('rating_view', rating_type=rating_type))
    
    if delete_player(rating_type, nickname):
        flash(f'✅ Игрок "{nickname}" и вся его история удалены!')
    else:
        flash(f'❌ Ошибка при удалении игрока "{nickname}"')
    
    return redirect(url_for('rating_view', rating_type=rating_type))

@app.route('/rating-stats/<rating_type>')
def rating_stats(rating_type):
    """Страница со статистикой рейтинга"""
    rating_types = get_all_rating_types()
    rt_ids = [rt['id'] for rt in rating_types]
    if rating_type not in rt_ids:
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Получаем всех игроков с их очками
    cursor.execute(f"""
        SELECT nickname, points 
        FROM players_{rating_type} 
        ORDER BY points DESC
    """)
    players = cursor.fetchall()
    
    # Считаем общую статистику
    total_players = len(players)
    total_points = sum([p[1] for p in players]) if players else 0
    avg_points = round(total_points / total_players, 1) if total_players > 0 else 0
    
    # Получаем количество недель
    cursor.execute(f"SELECT COUNT(DISTINCT date) FROM history_{rating_type}")
    total_weeks = cursor.fetchone()[0] or 0
    
    # Собираем статистику по каждому игроку
    players_stats = []
    for nickname, points in players:
        cursor.execute(f"""
            SELECT COUNT(DISTINCT date), AVG(points) 
            FROM history_{rating_type} 
            WHERE nickname = ?
        """, (nickname,))
        weeks, avg = cursor.fetchone()
        players_stats.append((nickname, points, weeks or 0, round(avg or 0, 1)))
    
    conn.close()
    
    display_name = get_rating_display_name(rating_type)
    
    return render_template('rating_stats.html',
                         rating_type=rating_type,
                         display_name=display_name,
                         players_stats=players_stats,
                         total_players=total_players,
                         total_points=total_points,
                         avg_points=avg_points,
                         total_weeks=total_weeks,
                         rating_types=rating_types)

@app.route('/player/<rating_type>/<nickname>')
def player_profile(rating_type, nickname):
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
                           dates=dates, 
                           points=points,
                           avg_dates=avg_dates,
                           avg_points=avg_points)

@app.route('/underperforming/<rating_type>')
def underperforming(rating_type):
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
    """Калькулятор Турбочерепашки"""
    return render_template('turtle_calculator.html')

# ===== МАРШРУТЫ ДЛЯ ГАЙДОВ =====

@app.route('/guides')
def guides_list():
    """Страница со списком гайдов"""
    guides = get_all_guides()
    return render_template('guides.html', guides=guides)

@app.route('/admin/guides', methods=['GET', 'POST'])
def admin_guides():
    """Админ-панель для управления гайдами"""
    if 'logged_in' not in session or session['username'] != 'admin':
        flash('Доступ только для администратора!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            
            if title and content:
                if create_guide(title, content):
                    flash(f'✅ Гайд "{title}" создан!')
                else:
                    flash('❌ Ошибка при создании гайда')
            else:
                flash('❌ Заполните все поля!')
        
        elif action == 'update':
            guide_id = request.form.get('guide_id')
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            
            if guide_id and title and content:
                if update_guide(int(guide_id), title, content):
                    flash(f'✅ Гайд "{title}" обновлен!')
                else:
                    flash('❌ Ошибка при обновлении гайда')
            else:
                flash('❌ Заполните все поля!')
        
        elif action == 'delete':
            guide_id = request.form.get('guide_id')
            if guide_id:
                guide = get_guide_by_id(int(guide_id))
                if delete_guide(int(guide_id)):
                    flash(f'✅ Гайд "{guide[1]}" удален!')
                else:
                    flash('❌ Ошибка при удалении гайда')
        
        return redirect(url_for('admin_guides'))
    
    guides = get_all_guides()
    return render_template('admin_guides.html', guides=guides)

if __name__ == '__main__':
    app.run()
else:
    application = app