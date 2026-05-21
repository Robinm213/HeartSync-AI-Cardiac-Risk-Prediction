"""
HeartSync — Emergency Alert & Notification System
===================================================
Sends email alerts to registered emergency contacts when
cardiac risk is detected. Supports SMTP email.

Privacy: The user NEVER sees their risk level directly.
Only emergency contacts receive the actual risk assessment.
"""

import os
import json
import sqlite3
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'users.db')

# Email config — set via environment variables
SMTP_CONFIG = {
    'host':     os.getenv('SMTP_HOST', 'smtp.gmail.com'),
    'port':     int(os.getenv('SMTP_PORT', '587')),
    'email':    os.getenv('SMTP_EMAIL', 'robinmandal105@gmail.com'),
    'password': os.getenv('SMTP_PASSWORD', 'dkhbtqzboeasfwjl'),
    'use_tls':  True,
}

logger = logging.getLogger('heartsync.alerts')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Database ────────────────────────────────────────────────────────────────

def init_emergency_tables():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            name        TEXT NOT NULL,
            relationship TEXT DEFAULT 'Family',
            email       TEXT,
            phone       TEXT,
            is_doctor   INTEGER DEFAULT 0,
            notify_high INTEGER DEFAULT 1,
            notify_medium INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS alert_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            contact_id  INTEGER NOT NULL,
            prediction_id INTEGER,
            risk_level  TEXT,
            alert_type  TEXT DEFAULT 'email',
            status      TEXT DEFAULT 'pending',
            message     TEXT,
            sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (contact_id) REFERENCES emergency_contacts(id)
        );
    """)
    conn.commit()
    conn.close()


# ─── Emergency Contact CRUD ──────────────────────────────────────────────────

def add_emergency_contact(user_id: int, name: str, email: str,
                          phone: str = '', relationship: str = 'Family',
                          is_doctor: int = 0,
                          notify_high: int = 1, notify_medium: int = 0) -> int:
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO emergency_contacts
        (user_id, name, relationship, email, phone, is_doctor, notify_high, notify_medium)
        VALUES (?,?,?,?,?,?,?,?)
    """, (user_id, name, relationship, email, phone, is_doctor, notify_high, notify_medium))
    contact_id = cur.lastrowid
    conn.commit()
    conn.close()
    return contact_id


def get_emergency_contacts(user_id: int) -> List[Dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM emergency_contacts WHERE user_id=? ORDER BY is_doctor DESC, created_at",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_emergency_contact(contact_id: int, user_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM emergency_contacts WHERE id=? AND user_id=?", (contact_id, user_id))
    conn.commit()
    conn.close()
    return True


def update_emergency_contact(contact_id: int, user_id: int, data: Dict) -> bool:
    conn = get_db()
    conn.execute("""
        UPDATE emergency_contacts SET
            name=?, relationship=?, email=?, phone=?,
            is_doctor=?, notify_high=?, notify_medium=?
        WHERE id=? AND user_id=?
    """, (
        data.get('name'), data.get('relationship', 'Family'),
        data.get('email'), data.get('phone', ''),
        data.get('is_doctor', 0),
        data.get('notify_high', 1), data.get('notify_medium', 0),
        contact_id, user_id
    ))
    conn.commit()
    conn.close()
    return True


def get_alert_history(user_id: int, limit: int = 20) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT al.*, ec.name as contact_name, ec.email as contact_email
        FROM alert_logs al
        JOIN emergency_contacts ec ON al.contact_id = ec.id
        WHERE al.user_id=?
        ORDER BY al.sent_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Email Sending ───────────────────────────────────────────────────────────

def is_email_configured() -> bool:
    return bool(SMTP_CONFIG['email'] and SMTP_CONFIG['password'])


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send email via SMTP. Returns True if sent successfully."""
    if not is_email_configured():
        logger.warning("SMTP not configured — email not sent")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"HeartSync Alerts <{SMTP_CONFIG['email']}>"
        msg['To']      = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
            if SMTP_CONFIG['use_tls']:
                server.starttls()
            server.login(SMTP_CONFIG['email'], SMTP_CONFIG['password'])
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Email failed to {to_email}: {e}")
        return False


# ─── Alert Email Templates ───────────────────────────────────────────────────

def build_high_risk_email(patient_name: str, contact_name: str,
                          prediction: Dict, vitals: Dict) -> tuple:
    """Build HIGH RISK urgent email. Returns (subject, html_body)."""
    subject = f"⚠️ URGENT: High Cardiac Risk Alert for {patient_name}"

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif; max-width:600px; margin:0 auto; background:#0a0a0f; color:#f0f0f5; border-radius:12px; overflow:hidden;">
        <div style="background:linear-gradient(135deg,#ff4757,#ff6b81); padding:24px 30px;">
            <h1 style="margin:0; font-size:20px; color:#fff;">⚠️ HIGH RISK — Immediate Attention Required</h1>
            <p style="margin:6px 0 0; color:rgba(255,255,255,0.85); font-size:14px;">HeartSync Cardiac Risk Alert System</p>
        </div>
        <div style="padding:30px;">
            <p style="font-size:15px; color:#f0f0f5;">Dear <strong>{contact_name}</strong>,</p>
            <p style="font-size:14px; color:#9d9daf; line-height:1.7;">
                This is an <strong style="color:#ff4757;">urgent automated alert</strong> from HeartSync.
                The AI cardiac risk prediction system has detected a <strong style="color:#ff4757;">HIGH cardiac risk level</strong>
                for <strong>{patient_name}</strong>.
            </p>

            <div style="background:#1a1a26; border:1px solid rgba(255,71,87,0.3); border-radius:10px; padding:20px; margin:20px 0;">
                <h3 style="margin:0 0 12px; font-size:13px; color:#ff4757; text-transform:uppercase; letter-spacing:1px;">Risk Assessment</h3>
                <table style="width:100%; font-size:14px; color:#9d9daf;">
                    <tr><td style="padding:6px 0;">Risk Level</td><td style="text-align:right; color:#ff4757; font-weight:700;">{prediction.get('risk_level', 'High')}</td></tr>
                    <tr><td style="padding:6px 0;">AI Model Used</td><td style="text-align:right;">{prediction.get('model_used', 'Gradient Boosting')}</td></tr>
                    <tr><td style="padding:6px 0;">Assessment Time</td><td style="text-align:right;">{datetime.now().strftime('%d %b %Y, %I:%M %p')}</td></tr>
                </table>
            </div>

            <div style="background:#1a1a26; border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:20px; margin:20px 0;">
                <h3 style="margin:0 0 12px; font-size:13px; color:#00d4aa; text-transform:uppercase; letter-spacing:1px;">Patient Vitals Summary</h3>
                <table style="width:100%; font-size:14px; color:#9d9daf;">
                    <tr><td style="padding:6px 0;">Heart Rate</td><td style="text-align:right; font-weight:600;">{vitals.get('heart_rate', 'N/A')} bpm</td></tr>
                    <tr><td style="padding:6px 0;">Blood Pressure</td><td style="text-align:right; font-weight:600;">{vitals.get('systolic_bp', 'N/A')}/{vitals.get('diastolic_bp', 'N/A')} mmHg</td></tr>
                    <tr><td style="padding:6px 0;">SpO₂</td><td style="text-align:right; font-weight:600;">{vitals.get('spo2', 'N/A')}%</td></tr>
                    <tr><td style="padding:6px 0;">BMI</td><td style="text-align:right; font-weight:600;">{vitals.get('bmi', 'N/A')}</td></tr>
                    <tr><td style="padding:6px 0;">Stress Level</td><td style="text-align:right; font-weight:600;">{vitals.get('stress_level', 'N/A')}/10</td></tr>
                </table>
            </div>

            <div style="background:rgba(255,71,87,0.1); border:1px solid rgba(255,71,87,0.2); border-radius:8px; padding:16px; margin:20px 0;">
                <p style="margin:0; font-size:14px; color:#ff6b81;">
                    <strong>⚠️ Recommended Action:</strong> Please contact {patient_name} immediately and
                    consider scheduling an urgent cardiac consultation.
                </p>
            </div>

            <p style="font-size:12px; color:#5e5e72; margin-top:30px; line-height:1.6;">
                This is an automated alert from HeartSync AI Cardiac Risk Prediction System.
                This is NOT a medical diagnosis. Please consult a qualified healthcare professional
                for proper evaluation and treatment.
            </p>
        </div>
        <div style="background:#12121a; padding:16px 30px; font-size:11px; color:#5e5e72; text-align:center;">
            HeartSync — AI-Powered Cardiac Risk Prediction &bull; For research & educational purposes
        </div>
    </div>
    """
    return subject, html


def build_medium_risk_email(patient_name: str, contact_name: str,
                            prediction: Dict, vitals: Dict) -> tuple:
    """Build MEDIUM RISK advisory email."""
    subject = f"📋 Health Advisory: Moderate Cardiac Risk for {patient_name}"

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif; max-width:600px; margin:0 auto; background:#0a0a0f; color:#f0f0f5; border-radius:12px; overflow:hidden;">
        <div style="background:linear-gradient(135deg,#ffa502,#ffc048); padding:24px 30px;">
            <h1 style="margin:0; font-size:20px; color:#0a0a0f;">📋 Moderate Risk — Health Advisory</h1>
            <p style="margin:6px 0 0; color:rgba(0,0,0,0.6); font-size:14px;">HeartSync Cardiac Risk Alert System</p>
        </div>
        <div style="padding:30px;">
            <p style="font-size:15px;">Dear <strong>{contact_name}</strong>,</p>
            <p style="font-size:14px; color:#9d9daf; line-height:1.7;">
                This is an advisory notification from HeartSync. The AI system has detected a
                <strong style="color:#ffa502;">moderate cardiac risk level</strong> for <strong>{patient_name}</strong>.
                This is not an emergency but warrants attention.
            </p>

            <div style="background:#1a1a26; border:1px solid rgba(255,165,2,0.2); border-radius:10px; padding:20px; margin:20px 0;">
                <h3 style="margin:0 0 12px; font-size:13px; color:#ffa502; text-transform:uppercase; letter-spacing:1px;">Assessment Summary</h3>
                <table style="width:100%; font-size:14px; color:#9d9daf;">
                    <tr><td style="padding:6px 0;">Risk Level</td><td style="text-align:right; color:#ffa502; font-weight:700;">Moderate</td></tr>
                    <tr><td style="padding:6px 0;">Heart Rate</td><td style="text-align:right;">{vitals.get('heart_rate', 'N/A')} bpm</td></tr>
                    <tr><td style="padding:6px 0;">Blood Pressure</td><td style="text-align:right;">{vitals.get('systolic_bp', 'N/A')}/{vitals.get('diastolic_bp', 'N/A')} mmHg</td></tr>
                    <tr><td style="padding:6px 0;">Assessment Time</td><td style="text-align:right;">{datetime.now().strftime('%d %b %Y, %I:%M %p')}</td></tr>
                </table>
            </div>

            <p style="font-size:14px; color:#9d9daf;">
                <strong>Suggestion:</strong> Consider scheduling a routine health checkup for {patient_name}
                within the next few weeks.
            </p>
            <p style="font-size:12px; color:#5e5e72; margin-top:30px; line-height:1.6;">
                Automated alert from HeartSync. Not a medical diagnosis.
            </p>
        </div>
    </div>
    """
    return subject, html


# ─── Main Alert Dispatcher ──────────────────────────────────────────────────

def dispatch_alerts(user_id: int, prediction: Dict, form_data: Dict,
                    prediction_id: int = None) -> Dict:
    """
    Send email alerts based on risk level and per-contact preferences.
      • High risk   → contacts with notify_high=1   are emailed (urgent template).
      • Medium risk → contacts with notify_medium=1 are emailed (advisory template).
      • Low risk    → no alert ever.
    """
    risk_level = prediction.get('risk_level', 'Low')

    result = {
        'risk_level': risk_level,
        'alerts_sent': 0,
        'contacts_notified': [],
        'alert_details': [],
    }

    # Low risk: completely silent.
    if risk_level == 'Low':
        result['message'] = 'No alert sent (Low risk).'
        return result

    contacts = get_emergency_contacts(user_id)

    conn = get_db()
    user = conn.execute("SELECT name FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    patient_name = user['name'] if user else 'Patient'

    vitals = {
        'heart_rate':   form_data.get('heart_rate',   'N/A'),
        'systolic_bp':  form_data.get('systolic_bp',  'N/A'),
        'diastolic_bp': form_data.get('diastolic_bp', 'N/A'),
        'spo2':         form_data.get('spo2',         'N/A'),
        'bmi':          form_data.get('bmi',          'N/A'),
        'stress_level': form_data.get('stress_level', 'N/A'),
    }

    for contact in contacts:
        if not contact.get('email'):
            continue

        # Per-contact toggle check
        should_alert = False
        if risk_level == 'High'   and contact.get('notify_high',   1):
            should_alert = True
        elif risk_level == 'Medium' and contact.get('notify_medium', 0):
            should_alert = True

        if not should_alert:
            continue

        # Build the appropriate email template
        if risk_level == 'High':
            subject, html = build_high_risk_email(
                patient_name, contact['name'], prediction, vitals
            )
        else:  # Medium
            subject, html = build_medium_risk_email(
                patient_name, contact['name'], prediction, vitals
            )

        sent = send_email(contact['email'], subject, html)
        status = 'sent' if sent else 'failed'
        if not is_email_configured():
            status = 'simulated'

        # Log alert
        conn = get_db()
        conn.execute("""
            INSERT INTO alert_logs (user_id, contact_id, prediction_id, risk_level, alert_type, status, message)
            VALUES (?,?,?,?,?,?,?)
        """, (user_id, contact['id'], prediction_id, risk_level, 'email', status, subject))
        conn.commit()
        conn.close()

        result['alerts_sent'] += 1
        result['contacts_notified'].append(contact['name'])
        result['alert_details'].append({
            'contact':    contact['name'],
            'email':      contact['email'],
            'status':     status,
            'risk_level': risk_level,
        })

    return result


# Initialize tables
init_emergency_tables()
