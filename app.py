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
    
    total_players = len(players)
    total_points = sum([p[1] for p in players]) if players else 0
    avg_points = round(total_points / total_players, 1) if total_players > 0 else 0
    
    # Получаем количество недель
    cursor.execute(f"SELECT COUNT(DISTINCT date) FROM history_{rating_type}")
    total_weeks = cursor.fetchone()[0] or 0
    
    # ===== ОТСТАЮЩИЕ ОТ СРЕДНЕГО (текущая неделя) =====
    cursor.execute(f"SELECT MAX(date) FROM history_{rating_type}")
    last_date = cursor.fetchone()[0]
    underperformers = []
    if last_date:
        cursor.execute(f"""
            SELECT nickname, points 
            FROM history_{rating_type} 
            WHERE date = ? AND points < ?
            ORDER BY points ASC
        """, (last_date, avg_points))
        underperformers = cursor.fetchall()
    
    # ===== СТАБИЛЬНО ОТСТАЮЩИЕ =====
    cursor.execute(f"""
        WITH daily_avg AS (
            SELECT date, AVG(points) as avg_points
            FROM history_{rating_type}
            GROUP BY date
        ),
        underperformers AS (
            SELECT h.nickname, COUNT(*) as count
            FROM history_{rating_type} h
            JOIN daily_avg da ON h.date = da.date
            WHERE h.points < da.avg_points
            GROUP BY h.nickname
        )
        SELECT nickname, count
        FROM underperformers
        ORDER BY count DESC
        LIMIT 20
    """)
    consistently_under = cursor.fetchall()
    
    # ===== СТАБИЛЬНО ЛИДИРУЮЩИЕ =====
    cursor.execute(f"""
        WITH daily_avg AS (
            SELECT date, AVG(points) as avg_points
            FROM history_{rating_type}
            GROUP BY date
        ),
        overperformers AS (
            SELECT h.nickname, COUNT(*) as count
            FROM history_{rating_type} h
            JOIN daily_avg da ON h.date = da.date
            WHERE h.points > da.avg_points
            GROUP BY h.nickname
        )
        SELECT nickname, count
        FROM overperformers
        ORDER BY count DESC
        LIMIT 20
    """)
    consistently_over = cursor.fetchall()
    
    # ===== ТОП-15 ИГРОКОВ =====
    top_15 = players[:15]
    
    # ===== ТОП-10 РЕЗЕРВУАР =====
    cursor.execute("""
        SELECT nickname, points 
        FROM players_reservoir 
        ORDER BY points DESC 
        LIMIT 10
    """)
    reservoir_top_10 = cursor.fetchall()
    
    conn.close()
    
    display_name = get_rating_display_name(rating_type)
    
    return render_template('rating_stats.html',
                         rating_type=rating_type,
                         display_name=display_name,
                         players=players,
                         total_players=total_players,
                         total_points=total_points,
                         avg_points=avg_points,
                         total_weeks=total_weeks,
                         underperformers=underperformers,
                         consistently_under=consistently_under,
                         consistently_over=consistently_over,
                         top_15=top_15,
                         reservoir_top_10=reservoir_top_10,
                         rating_types=rating_types)
