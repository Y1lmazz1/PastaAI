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
from datetime import datetime

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
    seed = int(time.time()) 
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&model=flux&seed={seed}"
    
    response = requests.get(url, timeout=90)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"AI Servis Hatası: {response.status_code}")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Veritabanını otomatik oluştur
with app.app_context():
    db.create_all()

# --- 3. KULLANICI İŞLEMLERİ ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
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
            # Admin girişi yapıldıysa direkt admin paneline yönlendirilebilir (isteğe bağlı)
            return redirect(url_for('order'))

        flash("Hatalı kullanıcı adı veya şifre!", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- 4. PASTA TASARIM VE AI İŞLEMLERİ ---

@app.route('/generate-preview', methods=['POST'])
@login_required
def generate_preview():
    prompt = request.form.get('prompt')
    tier = request.form.get('tier', '1')
    ai_prompt = (
        f"A real, professional 8k food photography of a {tier}-tiered cake. "
        f"Design details: {prompt}. The cake must have exactly {tier} tiers. "
        "Culinary masterpiece, hyper-realistic, centered on elegant cake stand, studio lighting."
    )
    try:
        image_bytes = generate_image(ai_prompt)
        image = Image.open(io.BytesIO(image_bytes))
        filename = f"cake_{current_user.id}_{int(time.time())}.png"
        save_path = os.path.join('static', 'generated')
        os.makedirs(save_path, exist_ok=True)
        image.save(os.path.join(save_path, filename))
        return jsonify({"image_url": url_for('static', filename=f'generated/{filename}')})
    except Exception as e:
        return jsonify({"error": "Görsel oluşturulamadı."}), 500

@app.route('/generate-revision', methods=['POST'])
@login_required
def generate_revision():
    original_prompt = request.form.get('original_prompt')
    revision_instruction = request.form.get('revision_instruction')
    tier = request.form.get('tier', '1')
    refined_prompt = (
        f"A professional food photography of a {tier}-tiered cake. "
        f"Original Style: {original_prompt}. USER REQUESTED CHANGE: {revision_instruction}. "
        "Maintain the overall structure but apply the change accurately."
    )
    try:
        image_bytes = generate_image(refined_prompt)
        image = Image.open(io.BytesIO(image_bytes))
        filename = f"revised_{current_user.id}_{int(time.time())}.png"
        save_path = os.path.join('static', 'generated')
        os.makedirs(save_path, exist_ok=True)
        image.save(os.path.join(save_path, filename))
        return jsonify({"image_url": url_for('static', filename=f'generated/{filename}')})
    except Exception as e:
        return jsonify({"error": "Değişiklik uygulanamadı."}), 500

# --- C: Sipariş Verme (TESLİMAT BİLGİLERİ EKLENDİ) ---
@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    if request.method == 'POST':
        # HTML'deki 'name' öznitelikleriyle birebir aynı olmalı
        tier = request.form.get('selected_tier', '1')
        base_prompt = request.form.get('prompt')
        rev_prompt = request.form.get('revision_prompt')
        generated_image_url = request.form.get('generated_image_url')
        
        # Senin HTML input isimlerin bunlar:
        d_date = request.form.get('teslimat_tarih') # f_tarih id'li inputun name'i
        d_time = request.form.get('teslimat_saat')  # f_saat id'li inputun name'i
        d_type = request.form.get('teslimat')       # f_teslimat id'li inputun name'i

        # Açıklamayı zenginleştir (Boyut, Kaplama vb. diğer gizli inputları da ekleyebilirsin)
        final_description = base_prompt if base_prompt else ""
        if rev_prompt:
            final_description += f" | Revizyon: {rev_prompt}"
        
        # Opsiyonel: Boyut ve kaplama bilgilerini de prompta ekle
        boyut = request.form.get('boyut')
        kaplama = request.form.get('kaplama')
        if boyut or kaplama:
            final_description += f" (Boyut: {boyut}, Kaplama: {kaplama})"

        new_order = Order(
            user_id=current_user.id,
            tier_count=int(tier[0]) if tier and tier[0].isdigit() else 1,
            prompt=final_description,
            image_source=generated_image_url if generated_image_url else "default_cake.png",
            status="Bekliyor",
            # Veritabanı sütun isimlerin modellerinde neyse ona göre eşle:
            delivery_date=f"{d_date} ({d_type})" if d_date and d_type else d_date,
            delivery_time=d_time
        )
        
        try:
            db.session.add(new_order)
            db.session.commit()
            flash("Siparişiniz başarıyla alındı!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Sipariş kaydedilirken hata oluştu: {e}", "danger")
            
        return redirect(url_for('my_orders'))

    return render_template('order.html')

# --- 5. YÖNETİCİ PANELİ (İSTATİSTİKLER EKLENDİ) ---

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash("Bu sayfaya erişim yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    
    orders = Order.query.order_by(Order.id.desc()).all()
    
    # Widgetlar için İstatistikleri hesapla
    stats = {
        'total': len(orders),
        'pending': Order.query.filter_by(status='Bekliyor').count(),
        'preparing': Order.query.filter_by(status='Hazırlanıyor').count(),
        'completed': Order.query.filter_by(status='Teslim Edildi').count()
    }
    
    return render_template('admin.html', orders=orders, stats=stats)

@app.route('/admin/update-status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    if current_user.role != 'admin':
        return jsonify({"error": "Yetkisiz erişim"}), 403

    order_to_update = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    order_to_update.status = new_status
    db.session.commit()
    
    flash(f"Sipariş #{order_id} güncellendi.", "success")
    return redirect(url_for('admin'))

@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('my_orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)