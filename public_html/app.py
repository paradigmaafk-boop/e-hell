from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import os
from database import init_db, check_user, save_rating, get_latest_rating, get_player_history, get_all_players, get_average_history, get_underperforming, get_consistently_underperforming, get_total_weeks, get_all_time_leaders, get_all_rating_types, get_rating_display_name
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_it_to_something_secret'

# --- НАСТРОЙКИ ДЛЯ TIMEWEB (CGI) ---
# Папка для загрузки файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку, если её нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Инициализируем базу данных (если её нет, создастся)
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
            flash(f'✅ Рейтинг обновлен! Обновлено {len(rating_list)} игроков. Всего в рейтинге: {len(all_players)} игроков.')
            
        except Exception as e:
            flash(f'❌ Ошибка: {e}')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
                
        return redirect(url_for('rating_view', rating_type=rating_type))
    else:
        flash('Разрешены только .xlsx или .xls')
        return redirect(url_for('rating_view', rating_type=rating_type))

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

# Это условие нужно для запуска на Timeweb через CGI
# Если файл запускается как приложение, а не как скрипт напрямую
if __name__ == '__main__':
    app.run()
else:
    # Это для CGI: определяем переменную application
    application = app