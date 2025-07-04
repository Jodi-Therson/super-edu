# database_setup.py
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Muat variabel dari .env
load_dotenv()

# Konfigurasi database
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
}

try:
    # Koneksi ke database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    print("✅ Koneksi database berhasil.")

    # 1. Membuat tabel 'users'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(80) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        nama_lengkap VARCHAR(100),
        nis_nim VARCHAR(50),
        no_telepon VARCHAR(20),
        last_login DATE,
        login_streak INT DEFAULT 0
    )
    """)
    print("Tabel 'users' dibuat atau sudah ada.")

    # 2. Membuat tabel 'chat_history'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source ENUM('konteks', 'umum') NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("Tabel 'chat_history' dibuat atau sudah ada.")
    
    # 3. Membuat tabel 'achievements'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        type VARCHAR(50) NOT NULL,
        threshold INT NOT NULL
    )
    """)
    print("Tabel 'achievements' dibuat atau sudah ada.")

    # 4. Membuat tabel 'user_achievements'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        achievement_id INT NOT NULL,
        unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (achievement_id) REFERENCES achievements(id),
        UNIQUE(user_id, achievement_id)
    )
    """)
    print("Tabel 'user_achievements' dibuat atau sudah ada.")

    # Menambahkan data awal ke 'achievements'
    achievements_to_add = [
        ('Login Streak 3 Hari', 'Login selama 3 hari berturut-turut.', 'streak', 3),
        ('Login Streak 7 Hari', 'Login selama 7 hari berturut-turut.', 'streak', 7),
        ('Tutor Penasaran', 'Bertanya 5 materi yang berbeda.', 'unique_topics', 5),
        ('Tutor Ahli', 'Bertanya 10 materi yang berbeda.', 'unique_topics', 10)
    ]
    cursor.executemany("INSERT IGNORE INTO achievements (name, description, type, threshold) VALUES (%s, %s, %s, %s)", achievements_to_add)
    print(f"{cursor.rowcount} achievements ditambahkan.")


    # Menambahkan pengguna awal secara manual
    # Cek apakah 'admin' sudah ada
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
        cursor.execute("""
        INSERT INTO users (username, password, nama_lengkap, nis_nim, no_telepon)
        VALUES (%s, %s, %s, %s, %s)
        """, ('admin', hashed_password, 'Admin User', '123456789', '081234567890'))
        print("Pengguna 'admin' berhasil ditambahkan. Password: admin")
    else:
        print("Pengguna 'admin' sudah ada.")

    # Commit perubahan dan tutup koneksi
    conn.commit()

except mysql.connector.Error as err:
    print(f"❌ Terjadi kesalahan: {err}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("Koneksi database ditutup.")