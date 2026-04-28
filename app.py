import os
import time
import io
import requests
import urllib.parse
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Order
from config import Config

# --- 1. UYGULAMA YAPILANDIRMASI ---
app = Flask(__name__)
app.config.from_object(Config)

# --- 2. EKLENTİLERİN BAŞLATILMASI ---
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- POLLINATIONS AI GÖRSEL ÜRETME FONKSİYONU ---
def generate_image(prompt):
    encoded = urllib.parse.quote(prompt)
    # seed eklemek, her seferinde benzersiz ve taze bir sonuç üretmesini sağlar
    seed = int(time.time()) 
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&model=flux&seed={seed}"
    
    response = requests.get(url, timeout=90)
    return response.content

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Veritabanını otomatik oluştur
with app.app_context():
    db.create_all()

# --- 3. ANA SAYFA VE KULLANICI İŞLEMLERİ ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        if User.query.filter_by(username=username).first():
            flash("Bu kullanıcı adı zaten alınmış!", "danger")
            return redirect(url_for('register'))

        new_user = User(username=username, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('order'))

        flash("Hatalı kullanıcı adı veya şifre!", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- 4. PASTA TASARIM VE SİPARİŞ İŞLEMLERİ ---

@app.route('/generate-preview', methods=['POST'])
@login_required
def generate_preview():
    prompt = request.form.get('prompt')
    tier = request.form.get('tier')
    # Referans görselin varlığını kontrol et (isteğe bağlı metin olarak da gelebilir)
    has_ref_image = 'ref_image' in request.files 

    # AI'yı tüm seçeneklere uyması için zorlayan katı yapı
    # 'Following the visual style of the reference' ifadesi AI'yı yönlendirir
    reference_instruction = "Follow the exact visual style, color palette, and aesthetic of the provided reference image. " if has_ref_image else ""

    ai_prompt = (
        f"{reference_instruction}"
        f"A real, professional 8k food photography of a {tier}-tiered cake. "
        f"Core Design: {prompt}. "
        f"The cake must strictly have exactly {tier} tiers. "
        "Style: culinary masterpiece, hyper-realistic, centered, elegant cake stand, sharp focus, studio lighting. "
        "Excluding: NO people, NO hands, NO messy background, NO blurry parts."
    )

    try:
        # Görsel üretimi
        image_bytes = generate_image(ai_prompt)
        image = Image.open(io.BytesIO(image_bytes))

        filename = f"cake_{current_user.id}_{int(time.time())}.png"
        save_path = os.path.join('static', 'generated')
        os.makedirs(save_path, exist_ok=True)
        image.save(os.path.join(save_path, filename))

        return jsonify({"image_url": url_for('static', filename=f'generated/{filename}')})
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({"image_url": url_for('static', filename=f'templates_png/{tier}-kat.png')})

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    if request.method == 'POST':
        tier = request.form.get('selected_tier')
        prompt = request.form.get('prompt')
        generated_image_url = request.form.get('generated_image_url')

        # Sipariş kaydı
        new_order = Order(
            user_id=current_user.id,
            tier_count=int(tier),
            prompt=prompt,
            image_source=generated_image_url if generated_image_url else f"templates_png/{tier}-kat.png",
            is_ai=True
        )
        db.session.add(new_order)
        db.session.commit()

        flash("Siparişiniz başarıyla alındı! Pasta ustalarımız hazırlığa başlıyor.", "success")
        return redirect(url_for('index'))

    return render_template('order.html')

# --- 5. YÖNETİCİ PANELİ ---

@app.route('/admin')
@login_required
def admin():
    # Sadece admin rolündekiler girebilir
    if current_user.role != 'admin':
        flash("Bu sayfaya erişim yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    
    # Tüm siparişleri getir
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template('admin.html', orders=orders)

@app.route('/admin/update-status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    if current_user.role != 'admin':
        return jsonify({"error": "Yetkisiz erisim"}), 403

    order_to_update = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order_to_update.status = new_status
    db.session.commit()
    
    flash(f"Sipariş #{order_id} durumu güncellendi.", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)