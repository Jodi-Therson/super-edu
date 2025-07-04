# add_user.py
import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import getpass

# Muat variabel lingkungan dari file .env
load_dotenv()

def add_new_user():
    """
    Skrip interaktif untuk menambahkan pengguna baru ke database.
    """
    print("--- Formulir Penambahan Pengguna Baru ---")
    
    # Kumpulkan data dari input pengguna
    username = input("Masukkan username baru: ").strip()
    password = getpass.getpass("Masukkan password baru: ")
    nama_lengkap = input("Masukkan nama lengkap: ").strip()
    nis_nim = input("Masukkan NIS/NIM: ").strip()
    no_telepon = input("Masukkan nomor telepon: ").strip()

    # Pastikan semua field diisi
    if not all([username, password, nama_lengkap, nis_nim, no_telepon]):
        print("\n❌ Gagal: Semua field harus diisi. Silakan coba lagi.")
        return

    # Buat hash dari password
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Konfigurasi dan koneksi database
    conn = None
    try:
        db_config = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS'),
            'database': os.getenv('DB_NAME'),
        }
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Perintah SQL untuk memasukkan data
        sql_query = """
        INSERT INTO users (username, password, nama_lengkap, nis_nim, no_telepon)
        VALUES (%s, %s, %s, %s, %s)
        """
        user_data = (username, hashed_password, nama_lengkap, nis_nim, no_telepon)

        # Eksekusi perintah
        cursor.execute(sql_query, user_data)
        conn.commit()

        print(f"\n✅ Pengguna '{username}' berhasil ditambahkan ke database!")

    except mysql.connector.Error as err:
        # Tangani error, misalnya jika username sudah ada
        if err.errno == 1062: # Error code for duplicate entry
            print(f"\n❌ Gagal: Username '{username}' sudah ada. Silakan gunakan username lain.")
        else:
            print(f"\n❌ Terjadi kesalahan database: {err}")
    finally:
        # Tutup koneksi
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    add_new_user()