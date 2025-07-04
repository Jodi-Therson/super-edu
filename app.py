# app.py
import os
import mysql.connector
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from rag_engine import RAGQueryEngine

# Muat environment variables
load_dotenv()

# Inisialisasi Aplikasi Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super-secret-key-for-dev')

UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

rag_engine = RAGQueryEngine() 

# Konfigurasi Database
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'autocommit': True
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# Konfigurasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model untuk Flask-Login
class User(UserMixin):
    def __init__(self, id, username, nama_lengkap, nis_nim, no_telepon):
        self.id = id
        self.username = username
        self.nama_lengkap = nama_lengkap
        self.nis_nim = nis_nim
        self.no_telepon = no_telepon

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, nama_lengkap, nis_nim, no_telepon FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_data:
        return User(**user_data)
    return None

# Muat RAG Engine
print("Loading RAG Engine...")
rag_engine = RAGQueryEngine()
print("RAG Engine Loaded.")

# --- Fungsi Bantuan Achievements ---
def check_achievements(user_id):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor(dictionary=True)

    # 1. Cek Login Streak
    cursor.execute("SELECT last_login, login_streak FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM achievements WHERE type = 'streak'")
    streak_achievements = cursor.fetchall()
    
    for ach in streak_achievements:
        if user['login_streak'] >= ach['threshold']:
            cursor.execute("INSERT IGNORE INTO user_achievements (user_id, achievement_id) VALUES (%s, %s)", (user_id, ach['id']))
            if cursor.rowcount > 0:
                flash(f"Pencapaian Terbuka: {ach['name']}!", "success")

    # 2. Cek Unique Topics
    cursor.execute("SELECT COUNT(DISTINCT question) as unique_count FROM chat_history WHERE user_id = %s", (user_id,))
    topic_count = cursor.fetchone()['unique_count']
    cursor.execute("SELECT * FROM achievements WHERE type = 'unique_topics'")
    topic_achievements = cursor.fetchall()

    for ach in topic_achievements:
        if topic_count >= ach['threshold']:
            cursor.execute("INSERT IGNORE INTO user_achievements (user_id, achievement_id) VALUES (%s, %s)", (user_id, ach['id']))
            if cursor.rowcount > 0:
                flash(f"Pencapaian Terbuka: {ach['name']}!", "success")
    
    cursor.close()
    conn.close()

# --- Rute Aplikasi ---
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))



@app.route("/index")
def nama_kelompok():

    # List of dictionaries untuk anggota kelompok
    group_members = [
        {'nama': 'Alfin Maulana', 'nim': '2401010433'},
        {'nama': 'I Komang Desta', 'nim': '2401010390'},
        {'nama': 'I Made Arimbawa Suputra', 'nim': '2401010415'},
        {'nama': 'Jodi Therson', 'nim': '2401010393'},
        {'nama': 'Tommy Rama Wijaya', 'nim': '2401010422'}
    ]
    return render_template(
        "index.html", 
        members=group_members, 
        title="Informasi Kelompok",
        active_page="info"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db_connection()
        if not conn:
            flash("Gagal terhubung ke server. Coba lagi nanti.", "danger")
            return render_template("login.html")
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'], nama_lengkap=user_data['nama_lengkap'], nis_nim=user_data['nis_nim'], no_telepon=user_data['no_telepon'])
            login_user(user)

            # Update login streak
            today = date.today()
            last_login = user_data.get('last_login')
            if last_login == today:
                # Sudah login hari ini, tidak ada perubahan
                pass
            elif last_login == today - timedelta(days=1):
                # Login berurutan
                cursor.execute("UPDATE users SET last_login = %s, login_streak = login_streak + 1 WHERE id = %s", (today, user.id))
            else:
                # Reset streak
                cursor.execute("UPDATE users SET last_login = %s, login_streak = 1 WHERE id = %s", (today, user.id))
            
            conn.commit()
            cursor.close()
            conn.close()

            flash("Login berhasil!", "success")
            check_achievements(user.id)
            return redirect(url_for('chat'))
        else:
            flash("Username atau password salah.", "danger")
            cursor.close()
            conn.close()

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for('login'))

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")

@app.route("/get_chat_history")
@login_required
def get_chat_history():
    """Endpoint untuk menyediakan riwayat chat sebagai JSON."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT question, answer, source FROM chat_history WHERE user_id = %s ORDER BY timestamp ASC",
        (current_user.id,)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(history)

# Ganti fungsi ask_question di app.py dengan ini

@app.route('/ask', methods=['POST'])
@login_required # Pastikan decorator ini aktif untuk mendapatkan current_user.id
def ask_question():
    text_query = request.form.get('message', '')
    file = request.files.get('file')

    if not text_query and not file:
        return jsonify({"error": "No input provided"}), 400

    image_data = None
    audio_path = None

    if file:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        if file.mimetype.startswith('image/'):
            with open(temp_path, 'rb') as f:
                image_data = f.read()
            os.remove(temp_path)
        elif file.mimetype.startswith('audio/'):
            audio_path = temp_path
    
    # Panggil RAG engine untuk mendapatkan jawaban
    response = rag_engine.ask(
        query=text_query, 
        image_data=image_data, 
        audio_file_path=audio_path
    )

    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)

    if response and response.get('source') != 'error':
        conn = None # Inisialisasi conn
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                
                # Menentukan teks pertanyaan untuk disimpan
                question_to_save = text_query if text_query else f"[File Terlampir: {file.filename}]"
                
                # Query SQL untuk memasukkan data ke tabel chat_history
                sql = "INSERT INTO chat_history (user_id, question, answer, source) VALUES (%s, %s, %s, %s)"
                val = (current_user.id, question_to_save, response['answer'], response['source'])
                
                cursor.execute(sql, val)
                # conn.commit() # Tidak perlu jika autocommit=True, tapi lebih aman jika ada
                print(f"✅ Riwayat chat untuk user {current_user.id} berhasil disimpan.")
                
                # Setelah menyimpan, cek apakah ada achievement baru yang terbuka
                check_achievements(current_user.id)

                cursor.close()
        except mysql.connector.Error as err:
            print(f"❌ Gagal menyimpan riwayat chat: {err}")
        finally:
            if conn and conn.is_connected():
                conn.close()

    return jsonify(response)

@app.route("/history")
@login_required
def history():
    conn = get_db_connection()
    if not conn:
        flash("Tidak bisa mengambil riwayat chat.", "danger")
        return render_template("history.html", history=[])
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT question, answer, source, timestamp FROM chat_history WHERE user_id = %s ORDER BY timestamp DESC", (current_user.id,))
    user_history = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("history.html", history=user_history)

@app.route("/achievements")
@login_required
def achievements():
    conn = get_db_connection()
    if not conn:
        flash("Tidak bisa mengambil data achievements.", "danger")
        return render_template("achievements.html", achievements=[])
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.name, a.description, ua.unlocked_at 
        FROM achievements a 
        JOIN user_achievements ua ON a.id = ua.achievement_id 
        WHERE ua.user_id = %s 
        ORDER BY ua.unlocked_at DESC
    """, (current_user.id,))
    user_achievements = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("achievements.html", achievements=user_achievements)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    conn = get_db_connection()
    if not conn:
        flash("Tidak bisa memuat pengaturan.", "danger")
        return redirect(url_for('chat'))

    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        if 'update_profile' in request.form:
            nama = request.form.get("nama_lengkap")
            nis_nim = request.form.get("nis_nim")
            no_telp = request.form.get("no_telepon")
            cursor.execute("UPDATE users SET nama_lengkap = %s, nis_nim = %s, no_telepon = %s WHERE id = %s",
                           (nama, nis_nim, no_telp, current_user.id))
            flash("Profil berhasil diperbarui.", "success")
        
        elif 'change_password' in request.form:
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            
            cursor.execute("SELECT password FROM users WHERE id = %s", (current_user.id,))
            user_pass = cursor.fetchone()
            
            if check_password_hash(user_pass['password'], current_password):
                hashed_new_password = generate_password_hash(new_password, method='pbkdf2:sha256')
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_new_password, current_user.id))
                flash("Password berhasil diubah.", "success")
            else:
                flash("Password saat ini salah.", "danger")
        
        conn.commit()

    cursor.execute("SELECT nama_lengkap, nis_nim, no_telepon, username FROM users WHERE id = %s", (current_user.id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("settings.html", user=user_data)


if __name__ == "__main__":
    app.run(debug=True, port=5001)