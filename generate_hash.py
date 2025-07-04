# generate_hash.py
from werkzeug.security import generate_password_hash
import getpass

password = getpass.getpass("Masukkan password baru untuk pengguna: ")
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
print("\nPassword Hash Anda (salin teks di bawah ini):")
print(hashed_password)