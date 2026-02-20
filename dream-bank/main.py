"""
بنك الأحلام - نسخة Zeabur النهائية
"""

import sqlite3
import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "dreambank_super_secret_key_2025_final"

# ==================== قاعدة البيانات ====================
def init_db():
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT,
                  join_date TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dreams
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  dream_text TEXT NOT NULL,
                  dream_date TEXT NOT NULL,
                  is_public INTEGER DEFAULT 1,
                  likes INTEGER DEFAULT 0,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()

init_db()

# ==================== دوال مساعدة ====================
def get_stats():
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dreams")
    total_dreams = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    c.execute("SELECT SUM(likes) FROM dreams")
    total_likes = c.fetchone()[0] or 0
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM dreams WHERE dream_date LIKE ?", (f"{today}%",))
    today_dreams = c.fetchone()[0] or 0
    conn.close()
    return {
        'total_dreams': total_dreams,
        'total_users': total_users,
        'total_likes': total_likes,
        'today_dreams': today_dreams
    }

def get_recent_dreams(limit=5):
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute("""
        SELECT dreams.*, users.username 
        FROM dreams 
        JOIN users ON dreams.user_id = users.id 
        WHERE is_public = 1 
        ORDER BY dreams.id DESC 
        LIMIT ?
    """, (limit,))
    dreams = c.fetchall()
    conn.close()
    return dreams

# ==================== الصفحات الرئيسية ====================
@app.route('/')
def index():
    stats = get_stats()
    recent_dreams = get_recent_dreams(5)
    return render_template('index.html', **stats, recent_dreams=recent_dreams)

@app.route('/submit', methods=['GET', 'POST'])
def submit_dream():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('يجب تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        dream_text = request.form.get('dream_text', '').strip()
        if not dream_text:
            flash('يرجى كتابة الحلم', 'error')
            return redirect(url_for('submit_dream'))
        is_public = 1 if request.form.get('is_public') else 0
        conn = sqlite3.connect('dreams.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO dreams (user_id, dream_text, dream_date, is_public) 
            VALUES (?, ?, ?, ?)
        """, (session['user_id'], dream_text, 
              datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), is_public))
        conn.commit()
        conn.close()
        flash('✅ تم تسجيل حلمك بنجاح!', 'success')
        return redirect(url_for('index'))
    return render_template('submit.html')

@app.route('/explore')
def explore():
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute("""
        SELECT dreams.*, users.username 
        FROM dreams 
        JOIN users ON dreams.user_id = users.id 
        WHERE is_public = 1 
        ORDER BY dreams.id DESC
    """)
    all_dreams = c.fetchall()
    conn.close()
    return render_template('explore.html', dreams=all_dreams)

@app.route('/dream/<int:dream_id>')
def view_dream(dream_id):
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute("""
        SELECT dreams.*, users.username 
        FROM dreams 
        JOIN users ON dreams.user_id = users.id 
        WHERE dreams.id = ?
    """, (dream_id,))
    dream = c.fetchone()
    conn.close()
    if dream:
        return render_template('dream.html', dream=dream)
    else:
        flash('الحلم غير موجود!', 'error')
        return redirect(url_for('explore'))

@app.route('/like/<int:dream_id>')
def like_dream(dream_id):
    conn = sqlite3.connect('dreams.db')
    c = conn.cursor()
    c.execute("UPDATE dreams SET likes = likes + 1 WHERE id = ?", (dream_id,))
    conn.commit()
    conn.close()
    flash('❤️ تم تسجيل إعجابك!', 'success')
    return redirect(request.referrer or url_for('explore'))

# ==================== نظام المستخدمين ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        if not username or not password:
            flash('اسم المستخدم وكلمة السر مطلوبان', 'error')
            return redirect(url_for('register'))
        conn = sqlite3.connect('dreams.db')
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO users (username, password, email, join_date) 
                VALUES (?, ?, ?, ?)
            """, (username, password, email, 
                  datetime.datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            flash('✅ تم التسجيل بنجاح! سجل دخولك الآن', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('❌ اسم المستخدم موجود بالفعل!', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = sqlite3.connect('dreams.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                 (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash(f'👋 مرحباً {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('❌ اسم المستخدم أو كلمة السر خطأ!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 تم تسجيل الخروج', 'success')
    return redirect(url_for('index'))

# ==================== تشغيل التطبيق ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
