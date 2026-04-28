import os

class Config:
    # Güvenlik: SECRET_KEY çevre değişkeninden okunur, yoksa varsayılan kullanılır
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pastai-super-gizli-anahtar-2024'
    
    # Veritabanı: instance klasöründe SQLite
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/pastai.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Dosya yükleme ayarları
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    GENERATED_FOLDER = os.path.join('static', 'generated')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}