"""
HeartSync — Universal Smartwatch Integration
==============================================
Supports ALL major smartwatch brands via multiple connection methods:

  Brand         | App              | Bridge to HeartSync
  --------------|------------------|--------------------------
  Noise         | NoiseFit         | Google Fit / CSV export
  Fire-Boltt    | Da Fit / FitCloudPro | Google Fit / CSV
  boAt          | boAt Progear     | Google Fit / CSV
  Amazfit       | Zepp             | Google Fit / Zepp API
  Samsung       | Samsung Health   | Google Fit / Samsung Health
  Fitbit        | Fitbit           | Google Fit / Fitbit API
  Apple Watch   | Apple Health     | HealthKit CSV export
  Xiaomi/Redmi  | Mi Fitness       | Google Fit / CSV
  Realme        | Realme Link      | Google Fit / CSV
  OnePlus       | N Health         | Google Fit / CSV
  Generic       | Any              | Google Fit / Manual CSV

Architecture:
  Since most Indian smartwatch brands (Noise, Fire-Boltt, boAt, Realme)
  do NOT have public APIs, we use Google Fit as a universal bridge.
  All these companion apps can sync data to Google Fit.

  Watch → Companion App → Google Fit → HeartSync
"""

import os
import json
import sqlite3
import datetime
import random
from typing import Optional, Dict, Any, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'users.db')


# ─── Supported Watch Brands ─────────────────────────────────────────────────

WATCH_BRANDS = {
    # Noise
    'noise_halo_plus':    {'brand': 'Noise',     'model': 'NoiseFit Halo Plus',    'code': 'IND0926', 'app': 'NoiseFit',       'google_fit': True},
    'noise_ind0925':      {'brand': 'Noise',     'model': 'NoiseFit Pulse 4 (IND0925)', 'code': 'IND0925', 'app': 'NoiseFit',  'google_fit': True},
    'noise_evolve_3':     {'brand': 'Noise',     'model': 'NoiseFit Evolve 3',     'code': 'IND0800', 'app': 'NoiseFit',       'google_fit': True},
    'noise_force_plus':   {'brand': 'Noise',     'model': 'NoiseFit Force Plus',   'code': 'IND0750', 'app': 'NoiseFit',       'google_fit': True},
    'noise_colorfit_pro4':{'brand': 'Noise',     'model': 'ColorFit Pro 4',        'code': 'IND0600', 'app': 'NoiseFit',       'google_fit': True},
    'noise_colorfit_u2':  {'brand': 'Noise',     'model': 'ColorFit Ultra 2',      'code': 'IND0500', 'app': 'NoiseFit',       'google_fit': True},
    # Fire-Boltt
    'fireboltt_invincible': {'brand': 'Fire-Boltt', 'model': 'Invincible Plus',    'code': 'FB-INV',  'app': 'Da Fit / FitCloudPro', 'google_fit': True},
    'fireboltt_ninja':      {'brand': 'Fire-Boltt', 'model': 'Ninja Call Pro Max', 'code': 'FB-NJC',  'app': 'Da Fit / FitCloudPro', 'google_fit': True},
    'fireboltt_phoenix':    {'brand': 'Fire-Boltt', 'model': 'Phoenix Ultra',      'code': 'FB-PHX',  'app': 'Da Fit / FitCloudPro', 'google_fit': True},
    'fireboltt_gladiator':  {'brand': 'Fire-Boltt', 'model': 'Gladiator',          'code': 'FB-GLD',  'app': 'Da Fit / FitCloudPro', 'google_fit': True},
    'fireboltt_ring3':      {'brand': 'Fire-Boltt', 'model': 'Ring 3',             'code': 'FB-R3',   'app': 'Da Fit / FitCloudPro', 'google_fit': True},
    # boAt
    'boat_lunar_pro':  {'brand': 'boAt',     'model': 'Lunar Pro LTE',     'code': 'BT-LPL', 'app': 'boAt Progear',    'google_fit': True},
    'boat_wave_call2': {'brand': 'boAt',     'model': 'Wave Call 2',       'code': 'BT-WC2', 'app': 'boAt Progear',    'google_fit': True},
    'boat_storm':      {'brand': 'boAt',     'model': 'Storm Call 3',      'code': 'BT-SC3', 'app': 'boAt Progear',    'google_fit': True},
    # Amazfit
    'amazfit_gtr4':    {'brand': 'Amazfit',  'model': 'GTR 4',             'code': 'AF-G4',  'app': 'Zepp',            'google_fit': True},
    'amazfit_bip5':    {'brand': 'Amazfit',  'model': 'Bip 5',             'code': 'AF-B5',  'app': 'Zepp',            'google_fit': True},
    # Samsung
    'samsung_fit3':    {'brand': 'Samsung',  'model': 'Galaxy Fit 3',      'code': 'SM-R390','app': 'Samsung Health',  'google_fit': True},
    'samsung_gw6':     {'brand': 'Samsung',  'model': 'Galaxy Watch 6',    'code': 'SM-GW6', 'app': 'Samsung Health',  'google_fit': True},
    'samsung_gw5':     {'brand': 'Samsung',  'model': 'Galaxy Watch 5',    'code': 'SM-GW5', 'app': 'Samsung Health',  'google_fit': True},
    # Xiaomi / Redmi
    'xiaomi_band8':    {'brand': 'Xiaomi',   'model': 'Smart Band 8',      'code': 'XI-B8',  'app': 'Mi Fitness',      'google_fit': True},
    'redmi_watch4':    {'brand': 'Redmi',    'model': 'Watch 4',           'code': 'RD-W4',  'app': 'Mi Fitness',      'google_fit': True},
    # Realme
    'realme_watch3':   {'brand': 'Realme',   'model': 'Watch 3 Pro',       'code': 'RL-W3P', 'app': 'Realme Link',     'google_fit': True},
    # Apple
    'apple_watch_se':  {'brand': 'Apple',    'model': 'Apple Watch SE',    'code': 'AP-SE',  'app': 'Apple Health',    'google_fit': False},
    'apple_watch_s9':  {'brand': 'Apple',    'model': 'Apple Watch S9',    'code': 'AP-S9',  'app': 'Apple Health',    'google_fit': False},
    # Fitbit
    'fitbit_versa4':   {'brand': 'Fitbit',   'model': 'Versa 4',           'code': 'FT-V4',  'app': 'Fitbit',          'google_fit': True},
    'fitbit_charge6':  {'brand': 'Fitbit',   'model': 'Charge 6',          'code': 'FT-C6',  'app': 'Fitbit',          'google_fit': True},
    # Generic
    'other':           {'brand': 'Other',    'model': 'Generic Smartwatch', 'code': 'GEN',    'app': 'Google Fit / CSV', 'google_fit': True},
}

def get_brands_grouped() -> Dict[str, List]:
    """Return watches grouped by brand for UI dropdowns."""
    groups = {}
    for key, info in WATCH_BRANDS.items():
        brand = info['brand']
        if brand not in groups:
            groups[brand] = []
        groups[brand].append({'key': key, **info})
    return groups


# ─── Database ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_wearable_tables():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wearable_readings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            source          TEXT NOT NULL,
            heart_rate      REAL,
            steps           INTEGER,
            sleep_hours     REAL,
            sleep_quality   INTEGER,
            spo2            REAL,
            stress_level    INTEGER,
            activity_minutes INTEGER,
            calories_burned INTEGER,
            hrv_ms          REAL,
            skin_temp       REAL,
            recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS wearable_tokens (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL UNIQUE,
            platform      TEXT NOT NULL,
            access_token  TEXT,
            refresh_token TEXT,
            expires_at    TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS wearable_latest (
            user_id          INTEGER PRIMARY KEY,
            heart_rate       REAL,
            steps            INTEGER,
            sleep_hours      REAL,
            sleep_quality    INTEGER,
            spo2             REAL,
            stress_level     INTEGER,
            activity_minutes INTEGER,
            hrv_ms           REAL,
            calories_burned  INTEGER,
            battery_percent  INTEGER DEFAULT 100,
            is_connected     INTEGER DEFAULT 0,
            watch_model      TEXT DEFAULT 'Unknown',
            watch_brand      TEXT DEFAULT 'Unknown',
            last_sync        TIMESTAMP,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


# ─── Universal Watch Simulator ──────────────────────────────────────────────

class UniversalWatchSimulator:
    """
    Simulates data from ANY smartwatch brand.
    Used for demo/testing without actual hardware.
    """
    def __init__(self, watch_key: str = 'noise_halo_plus'):
        info = WATCH_BRANDS.get(watch_key, WATCH_BRANDS['other'])
        self.watch_key = watch_key
        self.brand     = info['brand']
        self.model     = info['model']
        self.code      = info['code']
        self.app       = info['app']
        self.connected = False
        self.battery   = random.randint(40, 100)

    def connect(self) -> Dict[str, Any]:
        self.connected = True
        return {
            'status': 'connected',
            'brand': self.brand,
            'device_name': self.model,
            'model_code': self.code,
            'companion_app': self.app,
            'firmware': f'{random.randint(2,5)}.{random.randint(0,9)}.{random.randint(0,9)}',
            'battery': self.battery,
        }

    def read_realtime(self) -> Dict[str, Any]:
        if not self.connected:
            return {'error': 'Not connected'}

        hour = datetime.datetime.now().hour
        if 0 <= hour < 6:
            hr_base, stress = 58, random.randint(1, 3)
        elif 6 <= hour < 9:
            hr_base, stress = 72, random.randint(3, 5)
        elif 9 <= hour < 17:
            hr_base, stress = 78, random.randint(4, 7)
        elif 17 <= hour < 21:
            hr_base, stress = 74, random.randint(3, 6)
        else:
            hr_base, stress = 65, random.randint(2, 4)

        return {
            'heart_rate':       hr_base + random.randint(-8, 12),
            'spo2':             round(96.5 + random.uniform(0, 2.5), 1),
            'steps':            random.randint(200, 15000),
            'calories_burned':  random.randint(80, 600),
            'stress_level':     stress,
            'hrv_ms':           round(40 + random.uniform(-15, 30), 1),
            'skin_temp':        round(36.2 + random.uniform(-0.5, 0.8), 1),
            'activity_minutes': random.randint(0, 90),
            'sleep_hours':      round(random.uniform(5, 9), 1),
            'sleep_quality':    random.randint(4, 9),
            'battery':          self.battery,
            'timestamp':        datetime.datetime.now().isoformat(),
            'source':           f'{self.brand.lower()}_ble',
            'device':           self.model,
            'brand':            self.brand,
        }

    def read_daily_summary(self) -> Dict[str, Any]:
        return {
            'heart_rate':       random.randint(65, 85),
            'steps':            random.randint(3000, 18000),
            'calories_burned':  random.randint(1200, 2800),
            'sleep_hours':      round(random.uniform(5, 9), 1),
            'sleep_quality':    random.randint(4, 9),
            'spo2':             round(96 + random.uniform(0, 3), 1),
            'stress_level':     random.randint(3, 7),
            'hrv_ms':           round(40 + random.uniform(-10, 30), 1),
            'activity_minutes': random.randint(15, 120),
            'battery':          self.battery,
            'source':           f'{self.brand.lower()}_daily',
            'device':           self.model,
            'brand':            self.brand,
            'date':             datetime.date.today().isoformat(),
        }

    def disconnect(self):
        self.connected = False


# Global simulator
_simulator = None

def get_simulator(watch_key: str = 'noise_halo_plus') -> UniversalWatchSimulator:
    global _simulator
    if _simulator is None or _simulator.watch_key != watch_key:
        _simulator = UniversalWatchSimulator(watch_key)
    return _simulator


# ─── Data Helpers ────────────────────────────────────────────────────────────

WEARABLE_DEFAULTS = {
    'heart_rate': 72, 'steps': 6000, 'sleep_hours': 7.0,
    'sleep_quality': 6, 'spo2': 97.5, 'stress_level': 5,
    'activity_minutes': 30, 'calories_burned': 1800, 'hrv_ms': 50,
}

def impute_missing(reading: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conservative imputation:
      - For values explicitly present in the reading, keep them.
      - For 'real' sources (google_fit, csv, ble), DO NOT fill defaults —
        leave fields None so the UI can distinguish real-from-watch vs.
        nothing-known. Only the simulator uses defaults.
      - The legacy behaviour (fill all defaults) only applies when the caller
        sets reading['_use_defaults'] = True.
    """
    if reading.get('_use_defaults'):
        result = {**WEARABLE_DEFAULTS, **{k: v for k, v in reading.items() if v is not None}}
    else:
        result = {k: v for k, v in reading.items() if v is not None}

    # Stress-level inference is reasonable (it's derived, not defaulted)
    if 'stress_level' not in result and 'heart_rate' in result:
        hr = result['heart_rate']
        if hr < 65:   result['stress_level'] = 2
        elif hr < 80: result['stress_level'] = 5
        elif hr < 95: result['stress_level'] = 7
        else:         result['stress_level'] = 9
    return result


def save_wearable_reading(user_id: int, source: str, reading: Dict[str, Any]):
    conn = get_db()
    conn.execute("""
        INSERT INTO wearable_readings
        (user_id, source, heart_rate, steps, sleep_hours, sleep_quality,
         spo2, stress_level, activity_minutes, calories_burned, hrv_ms, skin_temp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        user_id, source, reading.get('heart_rate'), reading.get('steps'),
        reading.get('sleep_hours'), reading.get('sleep_quality'),
        reading.get('spo2'), reading.get('stress_level'),
        reading.get('activity_minutes'), reading.get('calories_burned'),
        reading.get('hrv_ms'), reading.get('skin_temp'),
    ))
    conn.execute("""
        INSERT INTO wearable_latest
        (user_id, heart_rate, steps, sleep_hours, sleep_quality, spo2,
         stress_level, activity_minutes, hrv_ms, calories_burned,
         battery_percent, is_connected, watch_model, watch_brand, last_sync, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            heart_rate=excluded.heart_rate, steps=excluded.steps,
            sleep_hours=excluded.sleep_hours, sleep_quality=excluded.sleep_quality,
            spo2=excluded.spo2, stress_level=excluded.stress_level,
            activity_minutes=excluded.activity_minutes, hrv_ms=excluded.hrv_ms,
            calories_burned=excluded.calories_burned,
            battery_percent=excluded.battery_percent,
            is_connected=1, watch_model=excluded.watch_model,
            watch_brand=excluded.watch_brand,
            last_sync=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
    """, (
        user_id, reading.get('heart_rate'), reading.get('steps'),
        reading.get('sleep_hours'), reading.get('sleep_quality'),
        reading.get('spo2'), reading.get('stress_level'),
        reading.get('activity_minutes'), reading.get('hrv_ms'),
        reading.get('calories_burned'),
        reading.get('battery', 100),
        reading.get('device', 'Watch'),
        reading.get('brand', 'Unknown'),
    ))
    conn.commit()
    conn.close()


def get_latest_wearable(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM wearable_latest WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_wearable_history(user_id: int, limit: int = 50) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM wearable_readings WHERE user_id=?
        ORDER BY recorded_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Health Alerts ───────────────────────────────────────────────────────────

def evaluate_alerts(reading: Dict[str, Any]) -> List[Dict]:
    alerts = []
    hr = reading.get('heart_rate')
    if hr:
        if hr > 100:
            alerts.append({'level': 'danger', 'icon': 'fa-heart-pulse',
                           'message': f'Elevated heart rate: {hr} bpm (normal < 100)'})
        elif hr < 50:
            alerts.append({'level': 'warning', 'icon': 'fa-heart-pulse',
                           'message': f'Low heart rate: {hr} bpm (normal > 50)'})

    spo2 = reading.get('spo2')
    if spo2 and spo2 < 94:
        alerts.append({'level': 'danger', 'icon': 'fa-lungs',
                       'message': f'Low SpO₂: {spo2}% (normal >= 95%)'})

    sleep = reading.get('sleep_hours')
    if sleep and sleep < 5:
        alerts.append({'level': 'warning', 'icon': 'fa-moon',
                       'message': f'Poor sleep: {sleep:.1f}h (recommended >= 7h)'})

    stress = reading.get('stress_level')
    if stress and stress >= 8:
        alerts.append({'level': 'warning', 'icon': 'fa-brain',
                       'message': f'High stress detected: {stress}/10'})

    hrv = reading.get('hrv_ms')
    if hrv and hrv < 20:
        alerts.append({'level': 'danger', 'icon': 'fa-wave-square',
                       'message': f'Very low HRV: {hrv}ms (normal > 30ms)'})
    return alerts


# ─── CSV Import ──────────────────────────────────────────────────────────────

def parse_noisefit_csv(filepath: str) -> List[Dict]:
    import csv
    readings = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                readings.append({
                    'heart_rate':       float(row.get('Heart Rate', row.get('heart_rate', 72))),
                    'steps':            int(row.get('Steps', row.get('steps', 0))),
                    'sleep_hours':      float(row.get('Sleep', row.get('sleep_hours', 7))),
                    'spo2':             float(row.get('SpO2', row.get('spo2', 97))),
                    'calories_burned':  int(row.get('Calories', row.get('calories_burned', 0))),
                    'stress_level':     int(row.get('Stress', row.get('stress_level', 5))),
                    'activity_minutes': int(row.get('Active Minutes', row.get('activity_minutes', 30))),
                    'source': 'csv_import',
                })
    except Exception as e:
        print(f"CSV parse error: {e}")
    return readings


# ─── Connection Instructions per Brand ───────────────────────────────────────

CONNECTION_GUIDES = {
    'Noise': {
        'app': 'NoiseFit',
        'steps': [
            "1. Install the NoiseFit app on your Android phone from Google Play Store.",
            "2. Open NoiseFit -> tap the '+' icon -> select your watch model (IND0925 / Pulse 4 / Halo Plus).",
            "3. Enable Bluetooth on your phone and keep the watch nearby during pairing.",
            "4. Once paired, go to NoiseFit -> Profile -> Connected Apps -> enable Google Fit sync.",
            "5. Install Google Fit app on your phone and sign in with your Google account.",
            "6. In Google Fit -> Settings -> Connected apps -> confirm NoiseFit is listed and syncing.",
            "7. In HeartSync -> Watch page -> tap 'Connect via Google Fit' and authorise.",
            "8. Your heart rate, SpO2, steps, sleep, and stress data will now sync automatically.",
        ],
        'alternative': 'No Google Fit? Export your NoiseFit health data as CSV (NoiseFit -> Profile -> Export Data) and upload it on the HeartSync Watch page.',
        'metrics_available': ['heart_rate', 'spo2', 'steps', 'sleep_hours', 'stress_level', 'calories_burned'],
    },
    'Fire-Boltt': {
        'app': 'Da Fit or FitCloudPro',
        'steps': [
            'Open Da Fit (or FitCloudPro) app on your phone',
            'Go to Settings → Third-party Integration → Google Fit',
            'Enable Google Fit sync and sign in with Google',
            'In HeartSync, go to Watch page and click "Connect Google Fit"',
            'Authorize HeartSync to read your Google Fit data',
            'Your Fire-Boltt watch data will flow: Watch → Da Fit → Google Fit → HeartSync',
        ],
        'alternative': 'Export health data from Da Fit app as CSV and upload in HeartSync Watch page.',
    },
    'boAt': {
        'app': 'boAt Progear',
        'steps': [
            'Open boAt Progear app on your phone',
            'Go to Profile → Settings → Sync to Google Fit',
            'Enable Google Fit and sign in with Google',
            'In HeartSync, click "Connect Google Fit"',
            'Data flow: Watch → boAt Progear → Google Fit → HeartSync',
        ],
        'alternative': 'Export from boAt Progear app and upload CSV.',
    },
    'Amazfit': {
        'app': 'Zepp',
        'steps': [
            'Open Zepp app on your phone',
            'Go to Profile → Add Accounts → Google Fit',
            'Enable sync and authorize',
            'In HeartSync, click "Connect Google Fit"',
        ],
        'alternative': 'Zepp also has its own API — advanced users can set up direct integration.',
    },
    'Samsung': {
        'app': 'Samsung Health',
        'steps': [
            "1. Install the Samsung Health app on your phone (Play Store) and pair your Galaxy Fit 3 / Galaxy Watch via Bluetooth.",
            "2. Install Health Connect from Play Store. (On most newer Samsung phones it's preinstalled — check Settings → Apps.)",
            "3. Open Samsung Health → tap Profile (top-right) → Settings → Health Connect → tap 'Connect to Health Connect' → allow ALL permissions (heart rate, steps, sleep, oxygen).",
            "4. Install the Google Fit app from Play Store and sign in with your Google account.",
            "5. Open Google Fit → Profile → Settings → Manage connected apps → enable Health Connect → grant ALL data access.",
            "6. Now: Galaxy Fit 3 → Samsung Health → Health Connect → Google Fit. Wear the watch for ~5 minutes so heart rate is measured at least once.",
            "7. In HeartSync → Watch page → tap 'Connect Google Fit' and sign in with the SAME Google account.",
            "8. HeartSync now reads your Galaxy Fit 3 data automatically.",
        ],
        'alternative': "No Health Connect? Samsung Health → Profile → Settings → Download personal data → choose date range → CSV → upload it on the HeartSync Watch page.",
        'metrics_available': ['heart_rate', 'spo2', 'steps', 'sleep_hours', 'stress_level', 'calories_burned'],
    },
    'Xiaomi': {
        'app': 'Mi Fitness',
        'steps': [
            'Open Mi Fitness app',
            'Go to Profile → Settings → Accounts → Google Fit',
            'Enable sync and sign in',
            'In HeartSync, click "Connect Google Fit"',
        ],
        'alternative': 'Export from Mi Fitness as CSV.',
    },
    'Fitbit': {
        'app': 'Fitbit',
        'steps': [
            'Fitbit automatically syncs with Google Fit (Google owns Fitbit)',
            'In HeartSync, click "Connect Google Fit"',
            'Alternatively, HeartSync supports direct Fitbit API (set FITBIT_CLIENT_ID)',
        ],
        'alternative': 'Visit fitbit.com/settings → Data Export to download CSV.',
    },
    'Apple': {
        'app': 'Apple Health',
        'steps': [
            'Apple Watch does not support Google Fit directly',
            'Install "Health Auto Export" app from App Store',
            'Export your health data as CSV',
            'Upload the CSV file in HeartSync Watch page',
        ],
        'alternative': 'Use Health Auto Export or QS Access app to get CSV from HealthKit.',
    },
    'Other': {
        'app': 'Google Fit / CSV',
        'steps': [
            'Check if your watch companion app supports Google Fit sync',
            'If yes, enable Google Fit sync in the app settings',
            'In HeartSync, click "Connect Google Fit"',
            'If not, export health data as CSV and upload manually',
        ],
        'alternative': 'Any app that can produce a CSV with Heart Rate, Steps, Sleep, SpO2 columns will work.',
    },
}

def get_connection_guide(brand: str) -> Dict:
    return CONNECTION_GUIDES.get(brand, CONNECTION_GUIDES['Other'])


# Initialize tables
init_wearable_tables()
