"""
HeartSync — Dataset Generator
Generates synthetic cardiac lifestyle + wearable sensor data
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)
N = 3000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Demographics
ages = np.random.randint(18, 80, N)
genders = np.random.choice(['Male', 'Female'], N)

# Lifestyle
smoke = np.random.choice([0, 1], N, p=[0.72, 0.28])
alcohol = np.random.choice([0, 1], N, p=[0.65, 0.35])

# Sleep (smartwatch-tracked)
sleep_hours = np.clip(np.random.normal(6.8, 1.6, N), 2.5, 11)
sleep_quality = np.random.randint(1, 11, N)

# Activity (smartwatch-tracked)
activity_minutes = np.clip(np.random.normal(38, 28, N), 0, 180).astype(int)
activity_type = np.random.choice(['None', 'Walking', 'Running', 'Gym', 'Yoga', 'Cycling'], N,
                                  p=[0.15, 0.30, 0.15, 0.15, 0.10, 0.15])

# Stress (smartwatch-derived)
stress_level = np.random.randint(1, 11, N)

# Vitals (smartwatch-tracked)
systolic_bp = np.clip(np.random.normal(122, 20, N), 80, 200).astype(int)
diastolic_bp = np.clip(np.random.normal(80, 12, N), 50, 130).astype(int)
heart_rate = np.clip(np.random.normal(74, 14, N), 42, 140).astype(int)
bmi = np.clip(np.random.normal(25.5, 5.2, N), 14, 48).round(1)
cholesterol = np.clip(np.random.normal(195, 42, N), 100, 340).astype(int)
blood_glucose = np.clip(np.random.normal(100, 28, N), 55, 280).astype(int)
spo2 = np.clip(np.random.normal(97.2, 1.4, N), 88, 100).round(1)

# Steps (smartwatch-tracked)
daily_steps = np.clip(np.random.normal(7200, 3500, N), 500, 25000).astype(int)

# Nutrition
daily_calories = np.clip(np.random.normal(2000, 450, N), 700, 4500).astype(int)
saturated_fat_g = np.clip(np.random.normal(20, 9, N), 0, 65).round(1)
sodium_mg = np.clip(np.random.normal(2300, 650, N), 200, 5500).astype(int)
fiber_g = np.clip(np.random.normal(18, 8, N), 1, 55).round(1)
sugar_g = np.clip(np.random.normal(48, 22, N), 3, 160).round(1)
fruits_veg_servings = np.clip(np.random.normal(3.2, 1.8, N), 0, 10).round(1)

# Medical history
family_history = np.random.choice([0, 1], N, p=[0.58, 0.42])
diabetes = np.random.choice([0, 1], N, p=[0.84, 0.16])

# HRV (smartwatch-tracked) — Heart Rate Variability in ms
hrv_ms = np.clip(np.random.normal(55, 22, N), 10, 120).round(1)

# --- Risk Score Computation ---
risk_score = np.zeros(N)
risk_score += (ages > 50).astype(float) * 2.0
risk_score += (ages > 65).astype(float) * 1.5
risk_score += (genders == 'Male').astype(float) * 0.5
risk_score += smoke * 2.2
risk_score += alcohol * 1.0
risk_score += (sleep_hours < 5.5).astype(float) * 1.8
risk_score += (sleep_quality < 4).astype(float) * 1.0
risk_score += (activity_minutes < 15).astype(float) * 1.8
risk_score += (daily_steps < 4000).astype(float) * 1.2
risk_score += (stress_level > 7).astype(float) * 2.0
risk_score += (systolic_bp > 140).astype(float) * 2.5
risk_score += (diastolic_bp > 90).astype(float) * 1.5
risk_score += (heart_rate > 100).astype(float) * 1.2
risk_score += (bmi > 30).astype(float) * 2.0
risk_score += (cholesterol > 240).astype(float) * 2.0
risk_score += (blood_glucose > 126).astype(float) * 2.0
risk_score += (spo2 < 94).astype(float) * 2.5
risk_score += (daily_calories > 3000).astype(float) * 1.0
risk_score += (saturated_fat_g > 30).astype(float) * 1.5
risk_score += (sodium_mg > 3500).astype(float) * 1.0
risk_score += (hrv_ms < 25).astype(float) * 1.5
risk_score += family_history * 2.0
risk_score += diabetes * 2.0
risk_score += np.random.normal(0, 0.6, N)

threshold = np.percentile(risk_score, 58)
cardiac_risk = (risk_score > threshold).astype(int)

risk_level = pd.cut(risk_score,
                    bins=[-np.inf, np.percentile(risk_score, 33),
                          np.percentile(risk_score, 66), np.inf],
                    labels=['Low', 'Medium', 'High'])

df = pd.DataFrame({
    'age': ages,
    'gender': genders,
    'smoking': smoke,
    'alcohol': alcohol,
    'sleep_hours': sleep_hours.round(1),
    'sleep_quality': sleep_quality,
    'activity_minutes_per_day': activity_minutes,
    'activity_type': activity_type,
    'stress_level': stress_level,
    'systolic_bp': systolic_bp,
    'diastolic_bp': diastolic_bp,
    'heart_rate': heart_rate,
    'bmi': bmi,
    'cholesterol_mg_dl': cholesterol,
    'blood_glucose_mg_dl': blood_glucose,
    'spo2_percent': spo2,
    'daily_calories': daily_calories,
    'saturated_fat_g': saturated_fat_g,
    'sodium_mg': sodium_mg,
    'fiber_g': fiber_g,
    'sugar_g': sugar_g,
    'fruits_veg_servings': fruits_veg_servings,
    'family_history': family_history,
    'diabetes': diabetes,
    'daily_steps': daily_steps,
    'hrv_ms': hrv_ms,
    'risk_score': risk_score.round(2),
    'risk_level': risk_level,
    'cardiac_risk': cardiac_risk
})

out_path = os.path.join(DATA_DIR, 'cardiac_lifestyle_dataset.csv')
df.to_csv(out_path, index=False)
print(f"Dataset saved: {len(df)} rows → {out_path}")
print(f"Risk distribution:\n{df['cardiac_risk'].value_counts()}")
print(f"Risk levels:\n{df['risk_level'].value_counts()}")
