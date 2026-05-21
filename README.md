# HeartSync — AI-Powered Early Cardiac Risk Prediction Using Lifestyle & Smartwatch Data

> **Major Project** — Health & Human Field  
> **Topic:** HeartSync: AI-Powered Early Cardiac Risk Prediction using Lifestyle Data  
> **Smartwatch:** Noise (Model IND0926 — Halo Plus) supported

---

## What is HeartSync?

HeartSync is a full-stack web application that connects to your **Noise smartwatch** and uses **5 AI/ML models** to predict cardiac (heart) risk in real-time. Instead of manually entering health data, the system automatically pulls heart rate, SpO₂, sleep, stress, steps, and HRV from your smartwatch — then runs predictions using trained models.

### Key Features

| Feature | Description |
|---------|-------------|
| **Smartwatch Sync** | Auto-sync data from Noise watch via BLE simulator / CSV export / Google Fit |
| **5 AI Models** | Gradient Boosting, Random Forest, Logistic Regression, SVM, LSTM |
| **Live Dashboard** | Real-time health metrics with trend charts (like NoiseFit app) |
| **Health Alerts** | Instant warnings when heart rate, SpO₂, or stress go out of safe range |
| **Food Tracker** | Log meals with barcode scanning, calorie tracking |
| **Risk Analysis** | Historical trends, BP charts, risk distribution |
| **Model Performance** | Compare all 5 models — accuracy, precision, recall, F1, AUC-ROC |

---

## Project Structure

```
heartsync/
├── app.py                    # Main Flask application
├── smartwatch.py             # Smartwatch integration (BLE simulator + CSV import)
├── food_database.py          # Food nutrition database
├── generate_dataset.py       # Generates synthetic training data (3000 records)
├── train_model.py            # Trains all 5 ML models
├── requirements.txt          # Python dependencies
├── data/
│   ├── cardiac_lifestyle_dataset.csv   # Training dataset
│   └── users.db                        # SQLite database (auto-created)
├── models/
│   ├── gb_model.pkl          # Gradient Boosting model
│   ├── rf_model.pkl          # Random Forest model
│   ├── lr_model.pkl          # Logistic Regression model (after retraining)
│   ├── svm_model.pkl         # SVM model (after retraining)
│   ├── lstm_model.keras      # LSTM model (requires TensorFlow)
│   ├── scaler.pkl            # Feature scaler
│   ├── le_gender.pkl         # Gender label encoder
│   ├── le_activity.pkl       # Activity type label encoder
│   └── metadata.json         # Model metrics & feature info
├── templates/
│   ├── base.html             # Base template (dark theme, Noise Fit-inspired)
│   ├── home.html             # Landing page
│   ├── login.html            # Sign in
│   ├── register.html         # Sign up (with watch model selection)
│   ├── dashboard.html        # Main health dashboard
│   ├── watch.html            # Smartwatch connection & live monitoring
│   ├── predict.html          # Cardiac risk prediction form
│   ├── analysis.html         # Health analysis with charts
│   ├── performance.html      # Model comparison & metrics
│   └── food_log.html         # Food & nutrition tracker
├── static/                   # Static assets
└── uploads/                  # Uploaded CSV files
```

---

## How to Run (Step-by-Step)

### Prerequisites
- **Python 3.9+** installed
- **pip** (comes with Python)
- Windows / macOS / Linux — any OS works

### Step 1: Extract the ZIP

```bash
unzip heartsync.zip
cd heartsync
```

### Step 2: Create Virtual Environment (recommended)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Generate Dataset (optional — dataset already included)

```bash
python generate_dataset.py
```
This creates `data/cardiac_lifestyle_dataset.csv` with 3,000 synthetic health records.

### Step 5: Train Models (optional — pre-trained models included)

```bash
python train_model.py
```
This trains all 5 models and saves them to the `models/` folder. Takes 1-2 minutes.

> **Note:** To train the LSTM model, install TensorFlow first:
> ```bash
> pip install tensorflow
> ```

### Step 6: Run the Application

```bash
python app.py
```

### Step 7: Open in Browser

```
http://localhost:5000
```

### Step 8: Create Account & Start Using

1. Click **"Get Started"** → fill registration form
2. Select your Noise watch model (IND0926) during registration
3. Go to **Dashboard** → see health overview
4. Go to **Watch** → click **"Connect via BLE"** → click **"Sync Now"**
5. Go to **Predict** → switch to **"From Watch"** → auto-fills sensor data → predict!

---

## How to Connect Your Noise Smartwatch (IND0926)

Your Noise watch (model IND0926 — Halo Plus) does **not** have a public API. Here are the 3 ways to get data into HeartSync:

### Method 1: BLE Simulator (Demo Mode — Works Immediately)

This is the **default mode**. When you click "Connect via BLE" in the Watch page, it uses a built-in simulator that generates realistic smartwatch-like data. This lets you demo the entire system without actual hardware.

**How it works:**
1. Go to **Watch** page
2. Click **"Connect via BLE"**
3. Click **"Sync Now"** — data appears instantly
4. Auto-syncs every 30 seconds

### Method 2: NoiseFit App CSV Export (Real Watch Data)

1. Open **NoiseFit app** on your phone
2. Go to **Profile → Settings → Export Data → CSV**
3. Transfer the CSV file to your computer
4. In HeartSync, go to **Watch** page
5. Under "NoiseFit App Export", upload the CSV file
6. Data is imported and stored for predictions

**Expected CSV format:**
```csv
Heart Rate,Steps,Sleep,SpO2,Calories,Stress,Active Minutes
72,8500,7.2,97,1850,4,45
```

### Method 3: Google Fit Bridge (Advanced)

If your NoiseFit app syncs data to Google Fit:

1. Set up a **Google Cloud Console** project
2. Enable the **Fitness API**
3. Create OAuth2 credentials
4. Set environment variables:
   ```bash
   export GOOGLE_CLIENT_ID=your_id
   export GOOGLE_CLIENT_SECRET=your_secret
   ```
5. HeartSync can then pull data from Google Fit automatically

> This requires additional setup — see Google Fit API documentation.

### For Production (Real BLE Connection)

To connect to the actual Noise watch hardware via Bluetooth:

1. Install the `bleak` library:
   ```bash
   pip install bleak
   ```
2. The Noise watch exposes standard BLE GATT services:
   - **Heart Rate Service:** UUID `0x180D`
   - **SpO₂ (Pulse Oximeter):** UUID `0x1822`
   - **Battery Service:** UUID `0x180F`
3. Replace the `NoiseWatchSimulator` class in `smartwatch.py` with actual BLE reads using `bleak`
4. Example scan code:
   ```python
   import asyncio
   from bleak import BleakScanner, BleakClient
   
   async def scan():
       devices = await BleakScanner.discover()
       for d in devices:
           if 'Noise' in (d.name or ''):
               print(f"Found: {d.name} [{d.address}]")
   
   asyncio.run(scan())
   ```

---

## Dataset Details

The training dataset has **3,000 records** with **24 features**:

| Feature | Type | Source | Description |
|---------|------|--------|-------------|
| age | Integer | Manual | Patient age (18-80) |
| gender | Categorical | Manual | Male / Female |
| smoking | Binary | Manual | 0=No, 1=Yes |
| alcohol | Binary | Manual | 0=No, 1=Yes |
| sleep_hours | Float | **Watch** | Hours of sleep (tracked by watch) |
| sleep_quality | Integer | **Watch** | 1-10 sleep quality score |
| activity_minutes_per_day | Integer | **Watch** | Active minutes per day |
| activity_type | Categorical | **Watch** | None/Walking/Running/Gym/Yoga/Cycling |
| stress_level | Integer | **Watch** | 1-10 stress score |
| systolic_bp | Integer | Manual/Watch | Systolic blood pressure |
| diastolic_bp | Integer | Manual | Diastolic blood pressure |
| heart_rate | Integer | **Watch** | Resting heart rate (bpm) |
| bmi | Float | Calculated | Body mass index |
| cholesterol_mg_dl | Integer | Manual | Total cholesterol |
| blood_glucose_mg_dl | Integer | Manual | Fasting blood glucose |
| spo2_percent | Float | **Watch** | Blood oxygen saturation |
| daily_calories | Integer | Food Log | Daily calorie intake |
| saturated_fat_g | Float | Manual | Saturated fat intake |
| sodium_mg | Integer | Manual | Sodium intake |
| fiber_g | Float | Manual | Fiber intake |
| sugar_g | Float | Manual | Sugar intake |
| fruits_veg_servings | Float | Manual | Fruits & vegetables servings |
| family_history | Binary | Manual | Family cardiac history |
| diabetes | Binary | Manual | Diabetes diagnosis |

**Target:** `cardiac_risk` (0 = No Risk, 1 = At Risk)

### Where to Get Real Datasets

For your project panel, you can also use real-world datasets:

1. **Kaggle — Heart Disease Dataset**
   - https://www.kaggle.com/datasets/johnsmith88/heart-disease-dataset
   - 303 records, clinical features

2. **UCI Heart Disease Dataset**
   - https://archive.ics.uci.edu/ml/datasets/heart+disease
   - 920 records from 4 hospitals

3. **Kaggle — Cardiovascular Disease**
   - https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset
   - 70,000 records with lifestyle features

4. **MIMIC-III / PhysioNet**
   - https://physionet.org/content/mimiciii/
   - Real ICU patient data (requires credentials)

> **Tip:** You can combine real datasets with our synthetic data for a larger, more robust training set.

---

## AI Models Used

| # | Model | Type | Best For |
|---|-------|------|----------|
| 1 | **Gradient Boosting** | Ensemble | Highest accuracy, handles non-linear relationships |
| 2 | **Random Forest** | Ensemble | Robust, handles missing data well |
| 3 | **Logistic Regression** | Linear | Fast, interpretable, good baseline |
| 4 | **SVM** | Kernel | Good with high-dimensional data |
| 5 | **LSTM** | Deep Learning | Sequential/time-series health data |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.9+, Flask 3.0 |
| ML/AI | scikit-learn, TensorFlow/Keras |
| Database | SQLite |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Design | Custom dark theme (Noise Fit inspired) |
| Smartwatch | BLE (bleak), CSV import, Google Fit API |
| Data | pandas, numpy, matplotlib |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/watch/connect` | Connect to smartwatch (BLE) |
| POST | `/api/watch/sync` | Sync latest readings |
| POST | `/api/watch/daily` | Get daily summary |
| POST | `/api/watch/disconnect` | Disconnect watch |
| GET  | `/api/watch/status` | Check connection status |
| POST | `/api/watch/upload_csv` | Upload NoiseFit CSV export |
| GET  | `/api/food/search?q=` | Search food database |
| POST | `/api/food/log` | Log a food item |
| POST | `/api/food/barcode` | Lookup food by barcode |

---

## Screenshots / Pages

1. **Home** — Landing page with animated watch visual
2. **Dashboard** — Health overview with metric tiles, risk trend, HR chart
3. **Watch** — Connect, sync, live readings, CSV upload, sync history
4. **Predict** — Manual entry OR auto-fill from watch, model selection
5. **Analysis** — Risk trend, BP chart, risk distribution, watch HR data
6. **Food Log** — Search food, manual add, barcode lookup, calorie tracking
7. **Models** — Performance comparison of all 5 AI models

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Models not loading | Run `python train_model.py` to retrain |
| Port 5000 in use | Change port: `python app.py` → edit `port=5001` in app.py |
| LSTM not working | Install tensorflow: `pip install tensorflow` |
| Watch not connecting | Use the built-in BLE simulator (default mode) |
| Database errors | Delete `data/users.db` and restart — it auto-recreates |

---

## License

For educational and research purposes only. Not for clinical/medical use.

---

**Built with** ❤️ **for cardiac health awareness**
