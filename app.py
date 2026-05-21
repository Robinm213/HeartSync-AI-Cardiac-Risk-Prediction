"""
HeartSync — AI-Powered Early Cardiac Risk Prediction
Flask Application v3.0
  - Private predictions (user never sees risk level)
  - Emergency contact alerts (email for High/Medium risk)
  - Universal smartwatch support (Noise, Fire-Boltt, boAt, Samsung, etc.)
  - Food photo recognition with local AI fallback
"""

import os, json, pickle, sqlite3, base64, io, csv
import numpy as np
import matplotlib; matplotlib.use('Agg')
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from food_database import FOOD_DATABASE
from smartwatch import (
    get_simulator, save_wearable_reading, get_latest_wearable,
    get_wearable_history, evaluate_alerts, impute_missing,
    parse_noisefit_csv, init_wearable_tables,
    WATCH_BRANDS, get_brands_grouped, get_connection_guide,
)
from google_fit import (
    is_google_fit_configured, get_google_auth_url, exchange_google_code,
    save_google_tokens, get_valid_token, fetch_google_fit_data,
    get_config_status, disconnect_google_fit
)
from weekly_report import generate_weekly_report, get_past_reports
from emergency_alerts import (
    init_emergency_tables, add_emergency_contact, get_emergency_contacts,
    delete_emergency_contact, update_emergency_contact,
    dispatch_alerts, get_alert_history, is_email_configured,
)

app = Flask(__name__)
app.secret_key = 'heartsync_v3_secret_2025'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'users.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
MODEL_DIR = os.path.join(BASE_DIR, 'models')

# ─── Load Models ─────────────────────────────────────────────────────────────
def load_models():
    def load_pkl(f):
        with open(os.path.join(MODEL_DIR, f), 'rb') as fh: return pickle.load(fh)
    gb = load_pkl('gb_model.pkl'); rf = load_pkl('rf_model.pkl')
    sc = load_pkl('scaler.pkl'); lg = load_pkl('le_gender.pkl'); la = load_pkl('le_activity.pkl')
    lr = load_pkl('lr_model.pkl') if os.path.exists(os.path.join(MODEL_DIR,'lr_model.pkl')) else None
    svm = load_pkl('svm_model.pkl') if os.path.exists(os.path.join(MODEL_DIR,'svm_model.pkl')) else None
    lstm = None
    lp = os.path.join(MODEL_DIR,'lstm_model.keras')
    if os.path.exists(lp):
        try:
            from tensorflow.keras.models import load_model; lstm = load_model(lp)
        except: pass
    with open(os.path.join(MODEL_DIR,'metadata.json')) as f: meta = json.load(f)
    return gb,rf,lr,svm,lstm,sc,lg,la,meta

gb_model,rf_model,lr_model,svm_model,lstm_model,scaler,le_gender,le_activity,metadata = load_models()
FEATURES = metadata['features']

# ─── Database ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
            age INTEGER, gender TEXT, height_cm REAL, weight_kg REAL,
            watch_model TEXT DEFAULT '', watch_brand TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            model_used TEXT DEFAULT 'Gradient Boosting', risk_score REAL,
            risk_label INTEGER, risk_level TEXT, probability REAL,
            data_source TEXT DEFAULT 'manual', alert_status TEXT DEFAULT 'none',
            age INTEGER, sleep_hours REAL, stress_level INTEGER,
            systolic_bp INTEGER, diastolic_bp INTEGER, heart_rate INTEGER,
            bmi REAL, activity_minutes INTEGER, daily_calories INTEGER,
            cholesterol INTEGER, blood_glucose INTEGER, spo2 REAL,
            steps INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            food_name TEXT, calories INTEGER, protein REAL, carbs REAL, fat REAL,
            source TEXT, barcode TEXT, image_path TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    conn.commit(); conn.close()

def migrate_db():
    """Safe ALTER TABLE migrations for existing databases."""
    conn = get_db()
    try:
        conn.execute("ALTER TABLE predictions ADD COLUMN steps INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # column already exists
    conn.close()

init_db(); migrate_db(); init_wearable_tables(); init_emergency_tables()


# ─── Google Fit cache (avoid hitting API on every page load) ────────────────
# Cache full sync result per user for 60 seconds. Manual "Sync Now" bypasses it.
_GFIT_CACHE = {}      # uid -> (timestamp, result_dict)
_GFIT_TTL_SECONDS = 60

def cached_google_sync(uid: int, force: bool = False):
    """
    Return latest Google Fit data for this user.
    Reuses a cached result if it's < 60s old to keep page loads fast.
    Returns dict with 'ok' bool, 'data' (if ok), 'message' (if not ok), or None
    if user hasn't connected Google Fit at all.
    """
    import time
    if not force:
        cached = _GFIT_CACHE.get(uid)
        if cached:
            ts, val = cached
            if time.time() - ts < _GFIT_TTL_SECONDS:
                return val

    token = get_valid_token(uid)
    if not token:
        # Don't cache misses — user might connect mid-session
        return None

    data = fetch_google_fit_data(token)
    if 'error' not in data:
        save_wearable_reading(uid, 'google_fit', impute_missing(data))
        out = {'ok': True, 'data': data}
    else:
        out = {'ok': False,
               'message': data.get('error_description', data.get('error'))}
    _GFIT_CACHE[uid] = (time.time(), out)
    return out

def login_required(f):
    @wraps(f)
    def decorated(*a,**kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return decorated

# ─── Prediction Engine ───────────────────────────────────────────────────────
def build_features(d):
    try: ge = le_gender.transform([d.get('gender','Male')])[0]
    except: ge = 0
    try: ae = le_activity.transform([d.get('activity_type','Walking')])[0]
    except: ae = 0
    return [float(d.get('age',40)),ge,int(d.get('smoking',0)),int(d.get('alcohol',0)),
        float(d.get('sleep_hours',7)),int(d.get('sleep_quality',5)),
        float(d.get('activity_minutes',30)),ae,int(d.get('stress_level',5)),
        int(d.get('systolic_bp',120)),int(d.get('diastolic_bp',80)),
        int(d.get('heart_rate',75)),float(d.get('bmi',25)),
        int(d.get('cholesterol',180)),int(d.get('blood_glucose',95)),
        float(d.get('spo2',98)),int(d.get('daily_calories',2000)),
        float(d.get('saturated_fat',15)),int(d.get('sodium',2000)),
        float(d.get('fiber',20)),float(d.get('sugar',40)),
        float(d.get('fruits_veg',3)),int(d.get('family_history',0)),int(d.get('diabetes',0))]

def predict_risk(data):
    import pandas as pd
    feat = build_features(data)
    feat_df = pd.DataFrame([feat], columns=FEATURES)
    feat_s = scaler.transform(feat_df)
    mn = data.get('model_choice','Gradient Boosting')

    if mn == 'Gradient Boosting':
        # Weighted ensemble: GB (50%) + RF (30%) + LR (10%) + SVM (10%)
        gb_prob = gb_model.predict_proba(feat_s)[0][1]
        rf_prob = rf_model.predict_proba(feat_s)[0][1]
        probs   = [gb_prob, rf_prob]
        weights = [0.5, 0.3]
        if lr_model is not None:
            try:
                probs.append(lr_model.predict_proba(feat_s)[0][1]); weights.append(0.1)
            except Exception: pass
        if svm_model is not None:
            try:
                probs.append(svm_model.predict_proba(feat_s)[0][1]); weights.append(0.1)
            except Exception: pass
        total_w = sum(weights) or 1.0
        prob = float(sum(p * (w / total_w) for p, w in zip(probs, weights)))
        label = int(prob >= 0.5)
        mn = 'Gradient Boosting (Ensemble)'
    elif mn == 'LSTM' and lstm_model:
        fl = feat_s.reshape((1,1,feat_s.shape[1]))
        prob = float(lstm_model.predict(fl,verbose=0)[0][0]); label = int(prob>=0.5)
    else:
        models = {'Random Forest':rf_model,'Logistic Regression':lr_model,'SVM':svm_model}
        chosen = models.get(mn)
        if not chosen:
            mn = 'Gradient Boosting'
            chosen = gb_model
        prob = float(chosen.predict_proba(feat_s)[0][1])
        label = int(chosen.predict(feat_s)[0])

    risk_level = 'High' if prob>=0.66 else 'Medium' if prob>=0.33 else 'Low'
    return {'probability':round(prob*100,2),'label':label,'risk_level':risk_level,
            'model_used':mn,'features':dict(zip(FEATURES,feat))}

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def home(): return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name=request.form['name']; email=request.form['email']; pw=request.form['password']
        age=request.form.get('age',30); gender=request.form.get('gender','Male')
        hc=request.form.get('height_cm',170); wk=request.form.get('weight_kg',70)
        wm=request.form.get('watch_model',''); wb=request.form.get('watch_brand','')
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (name,email,password,age,gender,height_cm,weight_kg,watch_model,watch_brand) VALUES (?,?,?,?,?,?,?,?,?)',
                (name,email,generate_password_hash(pw),age,gender,hc,wk,wm,wb))
            conn.commit(); flash('Registration successful! Please sign in.','success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError: flash('Email already registered.','danger')
        finally: conn.close()
    return render_template('register.html', watch_brands=get_brands_grouped())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email=request.form['email']; pw=request.form['password']
        conn=get_db(); user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); conn.close()
        if user and check_password_hash(user['password'],pw):
            session['user_id']=user['id']; session['user_name']=user['name']
            flash(f'Welcome back, {user["name"]}!','success'); return redirect(url_for('dashboard'))
        flash('Invalid email or password.','danger')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid=session['user_id']
    # Pull latest Google Fit data once (60s cache) so dashboard tiles are fresh
    google_sync_status = cached_google_sync(uid)
    conn=get_db()
    user=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    preds=conn.execute('SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT 15',(uid,)).fetchall()
    food_logs=conn.execute('SELECT * FROM food_logs WHERE user_id=? ORDER BY logged_at DESC LIMIT 10',(uid,)).fetchall()
    today_cals=conn.execute("SELECT COALESCE(SUM(calories),0) as total FROM food_logs WHERE user_id=? AND DATE(logged_at)=DATE('now')",(uid,)).fetchone()['total']
    conn.close()
    wearable=get_latest_wearable(uid); wearable_history=get_wearable_history(uid,24)
    alerts=evaluate_alerts(wearable) if wearable else []
    contacts=get_emergency_contacts(uid)
    tl,tp=[],[]
    for p in reversed(list(preds)):
        try:
            dt=datetime.fromisoformat(p['created_at'])
            if dt.tzinfo is None:
                dt=dt.replace(tzinfo=timezone.utc)
            tl.append(dt.astimezone(IST).strftime('%d %b %I:%M %p'))
        except: tl.append(p['created_at'][:16])
        tp.append(p['probability'])
    hl,hv=[],[]
    for r in reversed(wearable_history[:12]):
        try:
            dt=datetime.fromisoformat(r['recorded_at'])
            if dt.tzinfo is None:
                dt=dt.replace(tzinfo=timezone.utc)
            hl.append(dt.astimezone(IST).strftime('%I:%M %p'))
        except: hl.append('')
        hv.append(r.get('heart_rate',72))
    return render_template('dashboard.html',
        user=user,predictions=preds,food_logs=food_logs,today_calories=today_cals,
        wearable=wearable,wearable_history=wearable_history,alerts=alerts,
        contacts=contacts,
        trend_labels=json.dumps(tl),trend_probs=json.dumps(tp),
        hr_labels=json.dumps(hl),hr_values=json.dumps(hv),
        latest_pred=preds[0] if preds else None)

# ─── PREDICT (Private — no risk shown to user) ──────────────────────────────
@app.route('/predict', methods=['GET','POST'])
@login_required
def predict():
    prediction_done = False
    alert_result = None
    uid = session['user_id']
    available_models = ['Gradient Boosting','Random Forest']
    if lr_model: available_models.append('Logistic Regression')
    if svm_model: available_models.append('SVM')
    if lstm_model: available_models.append('LSTM')

    # Auto-refresh from Google Fit on every GET so the "From Watch" toggle
    # always shows the latest live numbers — no stale defaults.
    google_sync_status = None
    if request.method == 'GET':
        google_sync_status = cached_google_sync(uid)

    wearable = get_latest_wearable(uid)
    conn=get_db(); user=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    contacts=conn.execute('SELECT COUNT(*) as cnt FROM emergency_contacts WHERE user_id=?',(uid,)).fetchone()['cnt']
    conn.close()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        data_source = form_data.get('data_source','manual')
        if data_source == 'smartwatch' and wearable:
            for k in ['heart_rate','spo2','sleep_hours','sleep_quality','stress_level','activity_minutes','steps']:
                if wearable.get(k): form_data[k] = wearable[k]

        result = predict_risk(form_data)
        prediction_done = True

        # Save to DB
        conn=get_db()
        cur=conn.execute('''INSERT INTO predictions
            (user_id,model_used,risk_label,risk_level,probability,data_source,
             age,sleep_hours,stress_level,systolic_bp,diastolic_bp,heart_rate,
             bmi,activity_minutes,daily_calories,cholesterol,blood_glucose,spo2,steps)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (uid,result['model_used'],result['label'],result['risk_level'],
             result['probability'],data_source,
             form_data.get('age'),form_data.get('sleep_hours'),
             form_data.get('stress_level'),form_data.get('systolic_bp'),
             form_data.get('diastolic_bp'),form_data.get('heart_rate'),
             form_data.get('bmi'),form_data.get('activity_minutes'),
             form_data.get('daily_calories'),form_data.get('cholesterol'),
             form_data.get('blood_glucose'),form_data.get('spo2'),
             form_data.get('steps', 0)))
        pred_id = cur.lastrowid
        conn.commit(); conn.close()

        # Dispatch emergency alerts (user never sees risk level)
        alert_result = dispatch_alerts(uid, result, form_data, pred_id)

        # Update prediction with alert status
        conn=get_db()
        astatus = 'sent' if alert_result['alerts_sent']>0 else 'none'
        conn.execute('UPDATE predictions SET alert_status=? WHERE id=?',(astatus,pred_id))
        conn.commit(); conn.close()

    activity_types = ['None','Walking','Running','Gym','Yoga','Cycling']
    return render_template('predict.html',
        prediction_done=prediction_done, alert_result=alert_result,
        activity_types=activity_types, available_models=available_models,
        wearable=wearable, user=user, has_contacts=contacts>0,
        google_sync_status=google_sync_status)

# ─── Emergency Contacts ─────────────────────────────────────────────────────
@app.route('/contacts', methods=['GET','POST'])
@login_required
def emergency_contacts_page():
    uid=session['user_id']
    if request.method == 'POST':
        add_emergency_contact(uid,
            name=request.form['name'], email=request.form['email'],
            phone=request.form.get('phone',''),
            relationship=request.form.get('relationship','Family'),
            is_doctor=int(request.form.get('is_doctor', 0)),
            notify_high=int('notify_high' in request.form),
            notify_medium=int('notify_medium' in request.form))
        flash('Emergency contact added!','success')
        return redirect(url_for('emergency_contacts_page'))
    contacts=get_emergency_contacts(uid)
    alert_history=get_alert_history(uid)
    return render_template('contacts.html', contacts=contacts,
        alert_history=alert_history, email_configured=is_email_configured())

@app.route('/contacts/delete/<int:cid>', methods=['POST'])
@login_required
def delete_contact(cid):
    delete_emergency_contact(cid, session['user_id'])
    flash('Contact removed.','success'); return redirect(url_for('emergency_contacts_page'))

# ─── Analysis, Watch, Performance, Report, Food (unchanged logic) ────────────
@app.route('/analysis')
@login_required
def analysis():
    uid=session['user_id']; conn=get_db()
    preds=conn.execute('SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC',(uid,)).fetchall()
    food_logs=conn.execute('SELECT * FROM food_logs WHERE user_id=? ORDER BY logged_at DESC LIMIT 30',(uid,)).fetchall()
    conn.close(); wh=get_wearable_history(uid,30)
    return render_template('analysis.html',predictions=preds,food_logs=food_logs,wearable_history=wh)

@app.route('/watch')
@login_required
def watch_dashboard():
    uid=session['user_id']
    google_sync_status = cached_google_sync(uid)
    google_token = get_valid_token(uid)
    wearable=get_latest_wearable(uid)
    history=get_wearable_history(uid,48); alerts=evaluate_alerts(wearable) if wearable else []
    conn=get_db(); user=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close()
    brand = user['watch_brand'] if user and user['watch_brand'] else 'Other'
    guide = get_connection_guide(brand)
    return render_template('watch.html', wearable=wearable, history=history, alerts=alerts,
        user=user, watch_brands=get_brands_grouped(), connection_guide=guide,
        google_fit_configured=is_google_fit_configured(),
        google_fit_status=get_config_status(),
        google_fit_connected=bool(google_token),
        google_sync_status=google_sync_status)

@app.route('/performance')
def performance(): return render_template('performance.html', metadata=metadata)

@app.route('/report')
@login_required
def weekly_report_page():
    uid=session['user_id']; report=generate_weekly_report(uid)
    return render_template('report.html', report=report, past_reports=get_past_reports(uid))

@app.route('/food_log')
@login_required
def food_log():
    uid=session['user_id']; conn=get_db()
    logs=conn.execute('SELECT * FROM food_logs WHERE user_id=? ORDER BY logged_at DESC LIMIT 20',(uid,)).fetchall()
    today=conn.execute("SELECT COALESCE(SUM(calories),0) as total FROM food_logs WHERE user_id=? AND DATE(logged_at)=DATE('now')",(uid,)).fetchone()['total']
    conn.close()
    return render_template('food_log.html', logs=logs, today_calories=today, food_list=list(FOOD_DATABASE.values()))

# ─── Watch API ───────────────────────────────────────────────────────────────
@app.route('/api/watch/connect', methods=['POST'])
@login_required
def api_watch_connect():
    wk = request.json.get('watch_key','noise_halo_plus')
    sim=get_simulator(wk); info=sim.connect(); return jsonify(info)

@app.route('/api/watch/sync', methods=['POST'])
@login_required
def api_watch_sync():
    uid=session['user_id']; wk=request.json.get('watch_key','noise_halo_plus')
    sim=get_simulator(wk)
    if not sim.connected: sim.connect()
    reading=sim.read_realtime(); reading['_use_defaults']=True; reading=impute_missing(reading)
    save_wearable_reading(uid,f'{sim.brand.lower()}_ble',reading)
    return jsonify({'success':True,'reading':reading,'alerts':evaluate_alerts(reading)})

@app.route('/api/watch/disconnect', methods=['POST'])
@login_required
def api_watch_disconnect():
    sim=get_simulator(); sim.disconnect()
    conn=get_db(); conn.execute("UPDATE wearable_latest SET is_connected=0 WHERE user_id=?",(session['user_id'],))
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/watch/upload_csv', methods=['POST'])
@login_required
def api_watch_upload_csv():
    if 'file' not in request.files: return jsonify({'success':False,'message':'No file'})
    f=request.files['file']
    if not f.filename.endswith('.csv'): return jsonify({'success':False,'message':'CSV only'})
    fp=os.path.join(UPLOAD_FOLDER,secure_filename(f.filename)); f.save(fp)
    readings=parse_noisefit_csv(fp); uid=session['user_id']
    for r in readings: save_wearable_reading(uid,'csv_import',impute_missing(r))
    return jsonify({'success':True,'imported':len(readings)})

@app.route('/api/watch/status')
@login_required
def api_watch_status():
    w=get_latest_wearable(session['user_id']); s=get_simulator()
    return jsonify({'connected':s.connected,'latest':w,'model':s.model if s else None})

# ─── Food API ────────────────────────────────────────────────────────────────
@app.route('/api/food/search')
@login_required
def search_food():
    q=request.args.get('q','').lower()
    results=[{**f,'barcode':bc} for bc,f in FOOD_DATABASE.items() if q in f['name'].lower()]
    return jsonify({'results':results[:10]})

@app.route('/api/food/today_summary')
@login_required
def food_today_summary():
    """Return today's aggregated nutrition totals for the dashboard + auto-fill."""
    uid = session['user_id']
    conn = get_db()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(calories), 0) AS total_calories,
            COALESCE(SUM(protein),  0) AS total_protein,
            COALESCE(SUM(carbs),    0) AS total_carbs,
            COALESCE(SUM(fat),      0) AS total_fat,
            COUNT(*)                   AS item_count
        FROM food_logs
        WHERE user_id = ?
          AND DATE(logged_at) = DATE('now')
    """, (uid,)).fetchone()
    conn.close()
    return jsonify({
        'calories':   round(row['total_calories'] or 0),
        'protein':    round(row['total_protein']  or 0, 1),
        'carbs':      round(row['total_carbs']    or 0, 1),
        'fat':        round(row['total_fat']      or 0, 1),
        'item_count': row['item_count'] or 0,
    })

@app.route('/api/food/log', methods=['POST'])
@login_required
def log_food():
    d=request.json; uid=session['user_id']; conn=get_db()
    conn.execute('INSERT INTO food_logs (user_id,food_name,calories,protein,carbs,fat,source,barcode) VALUES (?,?,?,?,?,?,?,?)',
        (uid,d['food_name'],d['calories'],d.get('protein',0),d.get('carbs',0),d.get('fat',0),d.get('source','manual'),d.get('barcode','')))
    conn.commit(); conn.close()
    return jsonify({'success':True,'message':f"{d['food_name']} logged!"})

@app.route('/api/food/barcode', methods=['POST'])
@login_required
def lookup_barcode():
    barcode = request.json.get('barcode','').strip()
    # Check local database first
    if barcode in FOOD_DATABASE:
        return jsonify({'found':True,'food':FOOD_DATABASE[barcode],'barcode':barcode})
    # Try Open Food Facts API (free, no key, works for ANY barcode globally)
    try:
        import requests as req
        resp = req.get(f'https://world.openfoodfacts.org/api/v0/product/{barcode}.json', timeout=8)
        data = resp.json()
        if data.get('status') == 1:
            p = data.get('product', {})
            nut = p.get('nutriments', {})
            food = {
                'name': p.get('product_name', p.get('generic_name', 'Unknown Product')),
                'calories': int(nut.get('energy-kcal_100g', nut.get('energy-kcal', 0))),
                'protein': round(float(nut.get('proteins_100g', 0)), 1),
                'carbs': round(float(nut.get('carbohydrates_100g', 0)), 1),
                'fat': round(float(nut.get('fat_100g', 0)), 1),
                'category': p.get('categories', 'Food'),
                'brand': p.get('brands', ''),
                'image': p.get('image_front_small_url', ''),
            }
            return jsonify({'found':True,'food':food,'barcode':barcode,'source':'openfoodfacts'})
    except:
        pass
    return jsonify({'found':False,'message':'Barcode not found in local DB or Open Food Facts'})

@app.route('/api/food/recognize', methods=['POST'])
@login_required
def recognize_food_image():
    from food_recognition import process_food_image
    if 'image' not in request.files:
        return jsonify({'success':False,'message':'No image uploaded'})
    f=request.files['image']
    if not f.filename: return jsonify({'success':False,'message':'No file selected'})
    # Save image for records
    fname = secure_filename(f.filename)
    fpath = os.path.join(UPLOAD_FOLDER, f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{fname}")
    image_data = f.read()
    with open(fpath, 'wb') as fp: fp.write(image_data)
    result = process_food_image(image_data, fname)
    result['image_path'] = fpath
    return jsonify({'success':True,'food':result})

# ─── Google Fit OAuth ────────────────────────────────────────────────────────
@app.route('/oauth/google')
@login_required
def google_fit_connect():
    if not is_google_fit_configured():
        flash('Google Fit is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET '
              'environment variables, then restart the server.', 'warning')
        return redirect(url_for('watch_dashboard'))
    return redirect(get_google_auth_url())

@app.route('/oauth/google/callback')
@login_required
def google_fit_callback():
    # Google redirected back with either ?code=... or ?error=...
    err = request.args.get('error')
    if err:
        flash(f'Google declined the connection: {err}. '
              'Check that you added yourself as a Test User on the OAuth consent screen.',
              'danger')
        return redirect(url_for('watch_dashboard'))

    code = request.args.get('code')
    if not code:
        flash('No authorization code received from Google.', 'danger')
        return redirect(url_for('watch_dashboard'))

    tokens = exchange_google_code(code)
    if 'access_token' not in tokens:
        # Show the real reason — almost always a redirect-URI mismatch
        # or a wrong client secret.
        reason = tokens.get('error_description') or tokens.get('error') or 'Unknown error'
        flash(f'Token exchange failed: {reason}. '
              'Most common cause: the redirect URI in Google Cloud Console must EXACTLY match '
              'the GOOGLE_REDIRECT_URI value (default: http://localhost:5000/oauth/google/callback).',
              'danger')
        return redirect(url_for('watch_dashboard'))

    save_google_tokens(session['user_id'], tokens)

    data = fetch_google_fit_data(tokens['access_token'])
    if 'error' not in data:
        save_wearable_reading(session['user_id'], 'google_fit', impute_missing(data))
        flash(f'Google Fit connected! Synced HR={data.get("heart_rate","-")} bpm, '
              f'Steps={data.get("steps","-")}, SpO₂={data.get("spo2","-")}.', 'success')
    else:
        flash(f'Connected to Google Fit, but: {data.get("error_description", data.get("error"))}',
              'warning')
    return redirect(url_for('watch_dashboard'))

@app.route('/api/watch/google_sync', methods=['POST'])
@login_required
def api_google_sync():
    uid = session['user_id']
    token = get_valid_token(uid)
    if not token:
        return jsonify({'success': False, 'message':
            'Google Fit not connected for this user. Click "Connect Google Fit" first.'})
    data = fetch_google_fit_data(token)
    if 'error' in data:
        # Invalidate cache so next page doesn't show stale ok status
        _GFIT_CACHE.pop(uid, None)
        return jsonify({'success': False,
                        'error': data.get('error'),
                        'message': data.get('error_description', data.get('error', 'Unknown error'))})
    data = impute_missing(data)
    save_wearable_reading(uid, 'google_fit', data)
    # Refresh cache with this new sync result so subsequent page loads use it
    import time
    _GFIT_CACHE[uid] = (time.time(), {'ok': True, 'data': data})
    return jsonify({'success': True, 'reading': data, 'alerts': evaluate_alerts(data)})

@app.route('/api/watch/google_disconnect', methods=['POST'])
@login_required
def api_google_disconnect():
    disconnect_google_fit(session['user_id'])
    _GFIT_CACHE.pop(session['user_id'], None)
    return jsonify({'success': True, 'message': 'Google Fit disconnected.'})

@app.route('/api/watch/google_status')
@login_required
def api_google_status():
    """Diagnostic endpoint — used by the Watch page to show config issues."""
    uid = session['user_id']
    status = get_config_status()
    status['connected'] = bool(get_valid_token(uid))
    return jsonify(status)


@app.route('/api/watch/google_debug')
@login_required
def api_google_debug():
    """
    Inspect what Google Fit actually has for this user.
    Lists data sources so the user can see whether Health Connect / Samsung
    Health is actually pushing data through. Use this when sync says 'ok'
    but values look like defaults.
    """
    uid = session['user_id']
    token = get_valid_token(uid)
    if not token:
        return jsonify({'connected': False,
                        'message': 'Connect Google Fit first.'})

    from google_fit import _list_data_sources, fetch_google_fit_data
    sources = _list_data_sources(token)
    fresh   = fetch_google_fit_data(token, hours_back=24)

    # Trim noisy fields for display
    summarised = []
    for s in sources:
        summarised.append({
            'dataType':    s.get('dataType', {}).get('name', ''),
            'name':        s.get('name', '')[:80],
            'application': s.get('application', {}).get('name', '') or s.get('application', {}).get('packageName', ''),
            'device':      s.get('device', {}).get('model', ''),
        })

    return jsonify({
        'connected': True,
        'live_fetch': fresh,
        'sources_count': len(sources),
        'sources': summarised,
    })

# ─── Report API ──────────────────────────────────────────────────────────────
@app.route('/api/report/generate', methods=['POST'])
@login_required
def api_generate_report():
    return jsonify(generate_weekly_report(session['user_id']))

@app.route('/api/auto_sync', methods=['POST'])
@login_required
def api_auto_sync():
    uid=session['user_id']; token=get_valid_token(uid)
    if token:
        data=fetch_google_fit_data(token)
        if 'error' not in data:
            data=impute_missing(data); save_wearable_reading(uid,'google_fit',data)
            return jsonify({'success':True,'source':'google_fit','reading':data})
    sim=get_simulator()
    if not sim.connected: sim.connect()
    r=sim.read_realtime(); r['_use_defaults']=True; r=impute_missing(r)
    save_wearable_reading(uid,f'{sim.brand.lower()}_ble',r)
    return jsonify({'success':True,'source':'simulator','reading':r})

# ─── Template Helpers ────────────────────────────────────────────────────────
import builtins
app.jinja_env.globals['enumerate'] = builtins.enumerate
app.jinja_env.globals['min'] = builtins.min
app.jinja_env.globals['max'] = builtins.max
# IST timezone helper (Asia/Kolkata, UTC+05:30)
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    """Return the current time in IST (Asia/Kolkata, UTC+05:30)."""
    return datetime.now(IST)

app.jinja_env.globals['now'] = now_ist

@app.template_filter('ist')
def to_ist(value):
    """Convert UTC datetime (str or datetime) to a friendly IST string."""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            v = value.strip().replace('Z', '+00:00').replace(' ', 'T', 1)
            dt = datetime.fromisoformat(v)
        else:
            dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime('%d %b %Y, %I:%M %p IST')
    except Exception:
        try:
            return str(value)[:16]
        except Exception:
            return ''

@app.template_filter('ist_short')
def to_ist_short(value):
    """Short IST string: '06 May, 04:30 PM' — fits inside compact tables."""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            v = value.strip().replace('Z', '+00:00').replace(' ', 'T', 1)
            dt = datetime.fromisoformat(v)
        else:
            dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime('%d %b, %I:%M %p')
    except Exception:
        try:
            return str(value)[:16]
        except Exception:
            return ''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
