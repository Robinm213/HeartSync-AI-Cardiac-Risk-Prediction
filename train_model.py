"""
HeartSync — Model Training
Trains: Gradient Boosting, Random Forest, Logistic Regression, SVM, LSTM
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(BASE_DIR, 'data', 'cardiac_lifestyle_dataset.csv')
MODEL_DIR  = os.path.join(BASE_DIR, 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 60)
print("  HeartSync — AI Model Training Pipeline")
print("=" * 60)

df = pd.read_csv(DATA_PATH)
print(f"\n  Dataset: {df.shape[0]} rows, {df.shape[1]} columns")

le_gender   = LabelEncoder()
le_activity = LabelEncoder()
df['gender_enc']   = le_gender.fit_transform(df['gender'])
df['activity_enc'] = le_activity.fit_transform(df['activity_type'])

FEATURES = [
    'age', 'gender_enc', 'smoking', 'alcohol',
    'sleep_hours', 'sleep_quality',
    'activity_minutes_per_day', 'activity_enc',
    'stress_level',
    'systolic_bp', 'diastolic_bp', 'heart_rate',
    'bmi', 'cholesterol_mg_dl', 'blood_glucose_mg_dl', 'spo2_percent',
    'daily_calories', 'saturated_fat_g', 'sodium_mg',
    'fiber_g', 'sugar_g', 'fruits_veg_servings',
    'family_history', 'diabetes'
]

X = df[FEATURES]
y = df['cardiac_risk']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler    = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)


def calc_metrics(y_true, y_pred, y_prob):
    return {
        'accuracy':  round(accuracy_score(y_true, y_pred), 4),
        'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
        'recall':    round(recall_score(y_true, y_pred, zero_division=0), 4),
        'f1':        round(f1_score(y_true, y_pred, zero_division=0), 4),
        'auc_roc':   round(roc_auc_score(y_true, y_prob), 4)
    }


# 1. Gradient Boosting
print("\n  Training Gradient Boosting...")
gb = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=4,
                                subsample=0.8, random_state=42)
gb.fit(X_train_s, y_train)
gb_m = calc_metrics(y_test, gb.predict(X_test_s), gb.predict_proba(X_test_s)[:, 1])
print(f"    Accuracy: {gb_m['accuracy']*100:.2f}%")

# 2. Random Forest
print("  Training Random Forest...")
rf = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
rf.fit(X_train_s, y_train)
rf_m = calc_metrics(y_test, rf.predict(X_test_s), rf.predict_proba(X_test_s)[:, 1])
print(f"    Accuracy: {rf_m['accuracy']*100:.2f}%")

# 3. Logistic Regression
print("  Training Logistic Regression...")
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train_s, y_train)
lr_m = calc_metrics(y_test, lr.predict(X_test_s), lr.predict_proba(X_test_s)[:, 1])
print(f"    Accuracy: {lr_m['accuracy']*100:.2f}%")

# 4. SVM
print("  Training SVM...")
svm = SVC(kernel='rbf', C=1.0, probability=True, random_state=42)
svm.fit(X_train_s, y_train)
svm_m = calc_metrics(y_test, svm.predict(X_test_s), svm.predict_proba(X_test_s)[:, 1])
print(f"    Accuracy: {svm_m['accuracy']*100:.2f}%")

# 5. LSTM (optional — requires tensorflow)
lstm_m = None
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping

    print("  Training LSTM...")
    X_train_l = X_train_s.reshape((X_train_s.shape[0], 1, X_train_s.shape[1]))
    X_test_l  = X_test_s.reshape((X_test_s.shape[0], 1, X_test_s.shape[1]))

    lstm = Sequential([
        LSTM(64, input_shape=(1, X_train_s.shape[1]), return_sequences=True),
        Dropout(0.3),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    lstm.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    lstm.fit(X_train_l, y_train, epochs=50, batch_size=32,
             validation_split=0.1,
             callbacks=[EarlyStopping(monitor='val_loss', patience=5,
                                      restore_best_weights=True)],
             verbose=0)
    lstm_prob = lstm.predict(X_test_l, verbose=0).flatten()
    lstm_pred = (lstm_prob >= 0.5).astype(int)
    lstm_m = calc_metrics(y_test, lstm_pred, lstm_prob)
    print(f"    Accuracy: {lstm_m['accuracy']*100:.2f}%")
    lstm.save(os.path.join(MODEL_DIR, 'lstm_model.keras'))
except ImportError:
    print("  [SKIP] TensorFlow not installed — LSTM skipped")
except Exception as e:
    print(f"  [SKIP] LSTM failed: {e}")

# Cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(gb, scaler.transform(X), y, cv=cv, scoring='accuracy')
print(f"\n  5-Fold CV (GB): {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")

# Feature importances
importances = pd.Series(gb.feature_importances_, index=FEATURES).sort_values(ascending=False)

# Save models
for fname, obj in [('gb_model.pkl', gb), ('rf_model.pkl', rf),
                   ('lr_model.pkl', lr), ('svm_model.pkl', svm),
                   ('scaler.pkl', scaler), ('le_gender.pkl', le_gender),
                   ('le_activity.pkl', le_activity)]:
    with open(os.path.join(MODEL_DIR, fname), 'wb') as f:
        pickle.dump(obj, f)

# Save metadata
metadata = {
    'features':     FEATURES,
    'gb_metrics':   gb_m,
    'rf_metrics':   rf_m,
    'lr_metrics':   lr_m,
    'svm_metrics':  svm_m,
    'lstm_metrics': lstm_m,
    'cv_mean':      round(cv_scores.mean(), 4),
    'cv_std':       round(cv_scores.std(), 4),
    'cv_scores':    cv_scores.tolist(),
    'feature_importances': importances.to_dict(),
    'top_features': list(importances.index[:8]),
    'train_size':   len(X_train),
    'test_size':    len(X_test),
    'dataset_size': len(df)
}
with open(os.path.join(MODEL_DIR, 'metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2)

print("\n" + "=" * 60)
print("  Training Complete! Models saved to ./models/")
print("=" * 60)
