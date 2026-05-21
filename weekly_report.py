"""
HeartSync — Weekly Health Report Generator
============================================
Generates a comprehensive weekly health report based on:
  - 7 days of wearable data (HR, steps, sleep, stress, SpO2)
  - Prediction history
  - Food log data
  - AI-powered risk analysis

Provides:
  - Weekly summary with averages
  - Trend analysis (improving / worsening / stable)
  - Personalized DO's and DON'Ts
  - Risk prediction using latest watch data
  - Score out of 100 for overall cardiac health
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'users.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Data Collection ─────────────────────────────────────────────────────────

def get_week_wearable_data(user_id: int) -> List[Dict]:
    """Get last 7 days of wearable readings."""
    conn = get_db()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    rows = conn.execute("""
        SELECT * FROM wearable_readings
        WHERE user_id=? AND recorded_at >= ?
        ORDER BY recorded_at ASC
    """, (user_id, week_ago)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_week_predictions(user_id: int) -> List[Dict]:
    """Get last 7 days of predictions."""
    conn = get_db()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    rows = conn.execute("""
        SELECT * FROM predictions
        WHERE user_id=? AND created_at >= ?
        ORDER BY created_at ASC
    """, (user_id, week_ago)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_week_food_data(user_id: int) -> List[Dict]:
    """Get last 7 days of food logs."""
    conn = get_db()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    rows = conn.execute("""
        SELECT * FROM food_logs
        WHERE user_id=? AND logged_at >= ?
        ORDER BY logged_at ASC
    """, (user_id, week_ago)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_info(user_id: int) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Statistics Calculation ──────────────────────────────────────────────────

def safe_avg(values: list) -> float:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else 0


def safe_min(values: list) -> float:
    clean = [v for v in values if v is not None]
    return min(clean) if clean else 0


def safe_max(values: list) -> float:
    clean = [v for v in values if v is not None]
    return max(clean) if clean else 0


def calculate_trend(values: list) -> str:
    """Determine if values are improving, worsening, or stable."""
    clean = [v for v in values if v is not None]
    if len(clean) < 3:
        return 'insufficient_data'
    mid = len(clean) // 2
    first_half = sum(clean[:mid]) / mid
    second_half = sum(clean[mid:]) / (len(clean) - mid)
    diff_pct = ((second_half - first_half) / first_half * 100) if first_half != 0 else 0
    if abs(diff_pct) < 3:
        return 'stable'
    elif diff_pct > 0:
        return 'increasing'
    else:
        return 'decreasing'


# ─── Health Score Calculation ────────────────────────────────────────────────

def calculate_health_score(stats: Dict) -> int:
    """
    Calculate overall cardiac health score out of 100.
    Based on: HR, SpO2, sleep, steps, stress, risk predictions.
    """
    score = 100

    # Heart Rate scoring (resting: 60-80 ideal)
    hr = stats.get('hr_avg', 72)
    if hr < 50 or hr > 100:
        score -= 20
    elif hr < 60 or hr > 90:
        score -= 8
    elif hr > 80:
        score -= 3

    # SpO2 scoring (>95% ideal)
    spo2 = stats.get('spo2_avg', 97)
    if spo2 < 90:
        score -= 25
    elif spo2 < 94:
        score -= 15
    elif spo2 < 96:
        score -= 5

    # Sleep scoring (7-9 hours ideal)
    sleep = stats.get('sleep_avg', 7)
    if sleep < 4:
        score -= 20
    elif sleep < 5.5:
        score -= 12
    elif sleep < 6.5:
        score -= 6
    elif sleep > 10:
        score -= 5

    # Steps scoring (>7000 ideal)
    steps = stats.get('steps_avg', 6000)
    if steps < 2000:
        score -= 15
    elif steps < 4000:
        score -= 10
    elif steps < 6000:
        score -= 5
    elif steps > 10000:
        score += 3  # bonus

    # Stress scoring (1-4 ideal)
    stress = stats.get('stress_avg', 5)
    if stress >= 8:
        score -= 15
    elif stress >= 6:
        score -= 8
    elif stress >= 5:
        score -= 3

    # Activity scoring (>30 min ideal)
    activity = stats.get('activity_avg', 30)
    if activity < 10:
        score -= 10
    elif activity < 20:
        score -= 5
    elif activity > 60:
        score += 3  # bonus

    # Risk prediction scoring
    risk_avg = stats.get('risk_avg', 50)
    if risk_avg > 70:
        score -= 15
    elif risk_avg > 50:
        score -= 8
    elif risk_avg < 25:
        score += 5  # bonus

    return max(0, min(100, score))


# ─── Recommendation Engine ──────────────────────────────────────────────────

def generate_recommendations(stats: Dict, user: Dict) -> Dict:
    """
    Generate personalized DO's, DON'Ts, and warnings based on weekly data.
    """
    dos = []
    donts = []
    warnings = []
    highlights = []

    age = user.get('age', 30)

    # ── Heart Rate Analysis ──
    hr = stats.get('hr_avg', 72)
    hr_trend = stats.get('hr_trend', 'stable')
    if hr > 90:
        warnings.append({
            'icon': 'fa-heart-pulse', 'color': '#ff4757',
            'title': 'High Resting Heart Rate',
            'text': f'Your average HR this week was {hr} bpm which is elevated. Normal resting HR is 60-80 bpm.'
        })
        dos.append('Practice deep breathing exercises (4-7-8 technique) for 5 minutes daily')
        dos.append('Reduce caffeine intake — limit to 1 cup of coffee/tea per day')
        donts.append('Avoid intense workouts without proper warm-up')
        donts.append('Don\'t consume energy drinks or excessive caffeine')
    elif hr < 55:
        warnings.append({
            'icon': 'fa-heart-pulse', 'color': '#ffa502',
            'title': 'Low Resting Heart Rate',
            'text': f'Average HR was {hr} bpm. While low HR can indicate fitness, consult a doctor if you feel dizzy or fatigued.'
        })
    else:
        highlights.append(f'Heart rate is healthy at {hr} bpm avg')

    if hr_trend == 'increasing':
        dos.append('Your heart rate is trending upward — increase relaxation activities')

    # ── SpO2 Analysis ──
    spo2 = stats.get('spo2_avg', 97)
    if spo2 < 94:
        warnings.append({
            'icon': 'fa-lungs', 'color': '#ff4757',
            'title': 'Low Blood Oxygen',
            'text': f'Average SpO₂ was {spo2}% — below the safe threshold of 95%. Please consult a doctor.'
        })
        dos.append('Practice deep breathing exercises daily')
        dos.append('Spend time outdoors in fresh air for at least 30 minutes')
        donts.append('Avoid smoking or second-hand smoke exposure')
        donts.append('Don\'t sleep in poorly ventilated rooms')
    elif spo2 < 96:
        dos.append('Monitor your SpO₂ levels more frequently')
    else:
        highlights.append(f'Blood oxygen is excellent at {spo2}%')

    # ── Sleep Analysis ──
    sleep = stats.get('sleep_avg', 7)
    if sleep < 5.5:
        warnings.append({
            'icon': 'fa-moon', 'color': '#8b5cf6',
            'title': 'Insufficient Sleep',
            'text': f'You averaged only {sleep} hours of sleep. Poor sleep increases cardiac risk by 20-40%.'
        })
        dos.append('Set a fixed bedtime and wake-up time — consistency is key')
        dos.append('Avoid screens (phone, laptop) 1 hour before bed')
        dos.append('Keep bedroom temperature between 18-22°C')
        donts.append('Don\'t consume caffeine after 2 PM')
        donts.append('Avoid heavy meals within 3 hours of bedtime')
        donts.append('Don\'t use your bed for work or scrolling — bed is only for sleep')
    elif sleep < 6.5:
        dos.append('Try to add 30-60 minutes more sleep — your body needs 7+ hours')
    else:
        highlights.append(f'Good sleep pattern at {sleep} hrs/night avg')

    # ── Steps & Activity Analysis ──
    steps = stats.get('steps_avg', 6000)
    activity = stats.get('activity_avg', 30)
    if steps < 4000:
        warnings.append({
            'icon': 'fa-person-walking', 'color': '#ffa502',
            'title': 'Very Low Physical Activity',
            'text': f'You averaged only {int(steps)} steps/day. WHO recommends at least 7,000-10,000 steps for heart health.'
        })
        dos.append('Start with a 15-minute walk after dinner — build up gradually')
        dos.append('Take stairs instead of elevator')
        dos.append('Set hourly reminders to stand up and move for 2 minutes')
        donts.append('Don\'t sit continuously for more than 2 hours')
    elif steps < 7000:
        dos.append(f'Increase daily steps from {int(steps)} to 8,000+ for better heart health')
    else:
        highlights.append(f'Great activity level with {int(steps)} avg daily steps')

    if activity < 20:
        dos.append('Aim for 30+ minutes of moderate exercise daily (brisk walking, yoga, cycling)')
        donts.append('Don\'t skip exercise for more than 2 consecutive days')

    # ── Stress Analysis ──
    stress = stats.get('stress_avg', 5)
    if stress >= 7:
        warnings.append({
            'icon': 'fa-brain', 'color': '#ffa502',
            'title': 'Chronic High Stress',
            'text': f'Your stress averaged {stress}/10 this week. Chronic stress significantly increases cardiac risk.'
        })
        dos.append('Practice meditation for 10 minutes daily (try Headspace or Calm app)')
        dos.append('Schedule "worry time" — 15 min to process stress, then let go')
        dos.append('Spend time with family/friends — social connection reduces stress')
        donts.append('Don\'t skip meals when stressed — it worsens cortisol levels')
        donts.append('Avoid doom-scrolling social media before bed')
    elif stress >= 5:
        dos.append('Consider adding a short meditation or breathing session to your routine')

    # ── Risk Predictions ──
    risk_avg = stats.get('risk_avg', 50)
    if risk_avg > 65:
        warnings.append({
            'icon': 'fa-triangle-exclamation', 'color': '#ff4757',
            'title': 'Elevated Cardiac Risk',
            'text': f'Your average predicted risk was {risk_avg}% this week. Schedule a cardiac health checkup.'
        })
        dos.append('Schedule an appointment with a cardiologist within the next 2 weeks')
        dos.append('Get blood work done: lipid panel, HbA1c, CRP levels')
        donts.append('Don\'t ignore chest discomfort, breathlessness, or unusual fatigue')
    elif risk_avg > 40:
        dos.append('Continue monitoring and focus on lifestyle improvements')

    # ── Age-specific advice ──
    if age > 45:
        dos.append('Get a cardiac checkup (ECG, stress test) at least once a year')
    if age > 55:
        dos.append('Monitor blood pressure at home at least twice a week')

    # ── Calories ──
    cal_avg = stats.get('calories_avg', 0)
    if cal_avg > 2500:
        donts.append(f'Reduce daily calorie intake — you\'re averaging {int(cal_avg)} kcal (target: ~2000)')
        dos.append('Replace fried snacks with fruits, nuts, or salads')

    # Add general positive advice if few issues
    if len(warnings) == 0:
        highlights.append('No health warnings this week — keep it up!')
        dos.append('Maintain your current healthy routine')
        dos.append('Stay hydrated — drink 8+ glasses of water daily')

    return {
        'dos': dos,
        'donts': donts,
        'warnings': warnings,
        'highlights': highlights,
    }


# ─── Main Report Generator ──────────────────────────────────────────────────

def generate_weekly_report(user_id: int) -> Dict[str, Any]:
    """
    Generate complete weekly health report.
    Returns a dict with all report data.
    """
    user = get_user_info(user_id)
    if not user:
        return {'error': 'User not found'}

    wearable_data = get_week_wearable_data(user_id)
    predictions   = get_week_predictions(user_id)
    food_data     = get_week_food_data(user_id)

    # ── Calculate statistics ──
    hr_values      = [r['heart_rate'] for r in wearable_data if r.get('heart_rate')]
    spo2_values    = [r['spo2'] for r in wearable_data if r.get('spo2')]
    sleep_values   = [r['sleep_hours'] for r in wearable_data if r.get('sleep_hours')]
    steps_values   = [r['steps'] for r in wearable_data if r.get('steps')]
    stress_values  = [r['stress_level'] for r in wearable_data if r.get('stress_level')]
    activity_values = [r['activity_minutes'] for r in wearable_data if r.get('activity_minutes')]
    risk_values    = [p['probability'] for p in predictions if p.get('probability')]
    cal_values     = [f['calories'] for f in food_data if f.get('calories')]

    stats = {
        'hr_avg':       safe_avg(hr_values),
        'hr_min':       safe_min(hr_values),
        'hr_max':       safe_max(hr_values),
        'hr_trend':     calculate_trend(hr_values),
        'spo2_avg':     safe_avg(spo2_values),
        'spo2_min':     safe_min(spo2_values),
        'sleep_avg':    safe_avg(sleep_values),
        'sleep_min':    safe_min(sleep_values),
        'sleep_max':    safe_max(sleep_values),
        'sleep_trend':  calculate_trend(sleep_values),
        'steps_avg':    safe_avg(steps_values),
        'steps_total':  sum(v for v in steps_values if v) if steps_values else 0,
        'stress_avg':   safe_avg(stress_values),
        'stress_trend': calculate_trend(stress_values),
        'activity_avg': safe_avg(activity_values),
        'risk_avg':     safe_avg(risk_values),
        'risk_trend':   calculate_trend(risk_values),
        'calories_avg': safe_avg(cal_values),
        'total_readings': len(wearable_data),
        'total_predictions': len(predictions),
        'total_food_logs':   len(food_data),
    }

    # ── Health Score ──
    health_score = calculate_health_score(stats)

    # ── Score Grade ──
    if health_score >= 85:
        grade = 'Excellent'
        grade_color = '#2ed573'
    elif health_score >= 70:
        grade = 'Good'
        grade_color = '#00d4aa'
    elif health_score >= 55:
        grade = 'Fair'
        grade_color = '#ffa502'
    elif health_score >= 40:
        grade = 'Needs Attention'
        grade_color = '#ff6b81'
    else:
        grade = 'Critical'
        grade_color = '#ff4757'

    # ── Recommendations ──
    recs = generate_recommendations(stats, user)

    # ── Compile Report ──
    report = {
        'user_name':    user['name'],
        'user_age':     user.get('age', 30),
        'user_gender':  user.get('gender', 'Unknown'),
        'generated_at': datetime.now().isoformat(),
        'week_start':   (datetime.now() - timedelta(days=7)).strftime('%d %b %Y'),
        'week_end':     datetime.now().strftime('%d %b %Y'),
        'stats':        stats,
        'health_score': health_score,
        'grade':        grade,
        'grade_color':  grade_color,
        'recommendations': recs,
        'has_data':     len(wearable_data) > 0 or len(predictions) > 0,

        # Daily breakdown for charts
        'daily_hr':     hr_values[-7:] if hr_values else [],
        'daily_steps':  steps_values[-7:] if steps_values else [],
        'daily_sleep':  sleep_values[-7:] if sleep_values else [],
        'daily_stress': stress_values[-7:] if stress_values else [],
    }

    # ── Save report to DB ──
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            health_score INTEGER,
            grade TEXT,
            report_json TEXT,
            week_start TEXT,
            week_end TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        INSERT INTO weekly_reports (user_id, health_score, grade, report_json, week_start, week_end)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, health_score, grade, json.dumps(report), report['week_start'], report['week_end']))
    conn.commit()
    conn.close()

    return report


def get_past_reports(user_id: int, limit: int = 12) -> List[Dict]:
    """Get historical weekly reports."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, health_score, grade, week_start, week_end, created_at
            FROM weekly_reports WHERE user_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        conn.close()
        return []
