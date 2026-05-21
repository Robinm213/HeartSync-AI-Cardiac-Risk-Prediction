# Google Fit Setup — Connect your Smartwatch to HeartSync

This guide walks you through connecting your **Noise / Fire-Boltt / boAt / Samsung / Fitbit / Mi / Realme** smartwatch to HeartSync, end-to-end. Following each step exactly will avoid the common errors.

---

## How the bridge works

Indian smartwatches (Noise, Fire-Boltt, boAt, Realme) don't have public APIs. So we use Google Fit as a universal bridge:

```
[Your Watch]  →  [Companion App: NoiseFit / Da Fit / etc.]  →  [Google Fit]  →  [HeartSync]
```

You will need:
- Your watch's companion phone app (NoiseFit, Da Fit, boAt Progear, Zepp, Mi Fitness, etc.)
- A Google account
- 5 minutes for one-time Google Cloud setup

---

## Part 1 — Set up your Google Cloud project (one-time, ~5 minutes)

### 1.1 Create the project

1. Open https://console.cloud.google.com/
2. Click the project dropdown in the top-left → **NEW PROJECT**.
3. Name it `HeartSync` → **CREATE** → wait ~10 seconds → switch to it.

### 1.2 Enable the Fitness API

1. Open https://console.cloud.google.com/apis/library/fitness.googleapis.com
2. Make sure your `HeartSync` project is selected at the top.
3. Click the big blue **ENABLE** button. Wait until it says "API enabled".

> If you skip this, every sync will fail with `Fitness API has not been used in project ... or it is disabled`.

### 1.3 Configure the OAuth consent screen

1. Open https://console.cloud.google.com/apis/credentials/consent
2. Choose **External** → **CREATE**.
3. Fill in only the required fields:
   - **App name:** `HeartSync`
   - **User support email:** your email
   - **Developer contact email:** your email
4. Click **SAVE AND CONTINUE** through Scopes (leave empty) and continue.
5. On the **Test users** step, click **+ ADD USERS** → enter the Gmail address you'll use on the watch → **SAVE**.

> If you skip the Test User step, you will get **Error 403: access_denied** when trying to log in. While the app is in "Testing" status, only Test Users can sign in.

### 1.4 Create the OAuth Web client

1. Open https://console.cloud.google.com/apis/credentials
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**.
3. Application type: **Web application**.
4. Name: `HeartSync Local`.
5. Under **Authorized redirect URIs** click **+ ADD URI** and paste **exactly**:
   ```
   http://localhost:5000/oauth/google/callback
   ```
6. Click **CREATE**.
7. A modal pops up with the **Client ID** and **Client secret**. Copy both values now — you'll paste them into HeartSync next.

> The most common cause of failure is a **redirect URI mismatch**. The URI must be character-for-character identical, including the protocol (`http://`, not `https://`) and the trailing path. No trailing slash. No `www`.

---

## Part 2 — Tell HeartSync your credentials

You have three options. Pick the easiest one for your OS.

### Option A — Set environment variables (recommended)

**Windows (Command Prompt):**
```cmd
set GOOGLE_CLIENT_ID=784440828388-xxxxx.apps.googleusercontent.com
set GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxx
python app.py
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CLIENT_ID = "784440828388-xxxxx.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "GOCSPX-xxxxxxxxxxxxxxxxxx"
python app.py
```

**macOS / Linux:**
```bash
export GOOGLE_CLIENT_ID="784440828388-xxxxx.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="GOCSPX-xxxxxxxxxxxxxxxxxx"
python app.py
```

### Option B — `.env` file

1. In the project folder, copy `.env.example` to `.env`.
2. Fill in `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
3. Install python-dotenv: `pip install python-dotenv` and add `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py` (already done if you used the latest version).
4. Run `python app.py`.

### Option C — Verify it worked

After you start the server, open http://localhost:5000/watch (after logging in). The Google Fit Bridge card now shows the project ID preview, e.g. `784440828388…`, and the redirect URI HeartSync is using. If you see **"Configuration Incomplete"** instead, the env vars didn't load — check your shell and restart.

---

## Part 3 — Make sure your watch is sending data to Google Fit

This is the step most people skip. Without it, HeartSync will connect successfully but report **"Google Fit returned 0 data points"**.

### For Noise watches

1. Open the **NoiseFit** app on your phone.
2. **Profile** (bottom right) → **Connected Apps** (or **3rd-party Apps**) → toggle **Google Fit** ON.
3. Sign in with the **same** Gmail you added as a Test User.
4. Wear the watch for 2–3 minutes — heart rate must be measured at least once.
5. Open the **Google Fit** app on your phone, swipe down to refresh — you should see today's heart rate, steps, etc.

### For Fire-Boltt / boAt / Realme / Mi / Samsung watches

The flow is identical — open the companion app (Da Fit / boAt Progear / Realme Link / Mi Fitness / Samsung Health) → settings → connect Google Fit → sign in with the same Gmail.

**If your phone doesn't have the Google Fit app** (newer Android versions sometimes hide it): install it from Play Store. It's officially being deprecated by Google, but the API HeartSync uses still works in 2026.

---

## Part 4 — Connect HeartSync to Google Fit

1. Open http://localhost:5000/watch
2. Find the **Google Fit Bridge** card.
3. Click **Connect Google Fit**.
4. You'll be redirected to Google's consent screen. Sign in with the **same** Gmail you added as a Test User in Part 1.3.
5. Approve the requested scopes (heart rate, sleep, activity, body, oxygen saturation).
6. You'll be redirected back to HeartSync. The flash message should say something like:
   > "Google Fit connected! Synced HR=72 bpm, Steps=4521, SpO₂=98."
7. After this, the page shows a green **"Google Fit Connected"** banner with **Sync Now** and **Disconnect** buttons.

---

## Part 5 — Use it

### On the Predict page
- Click **From Watch** at the top of the form.
- The Heart Rate, SpO₂, Sleep, Stress, Activity Minutes, and Steps fields auto-fill from your latest Google Fit reading (highlighted in green).
- Fill the remaining fields (BP, BMI, cholesterol, etc.) manually.
- Click **Analyze Health Data**.

### On the Watch page
- Click **Sync Now** any time to pull the latest reading.
- The page also auto-syncs every 30 seconds while open.

---

## Troubleshooting cheat sheet

| Symptom | Cause | Fix |
|---|---|---|
| **"Configuration Incomplete"** on Watch page | Env vars not set when `python app.py` started | Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, then restart |
| **redirect_uri_mismatch** during sign-in | Mismatch between Google Cloud and HeartSync | In Cloud Console, the URI must be exactly `http://localhost:5000/oauth/google/callback` |
| **Error 403: access_denied** | You're not a Test User on the consent screen | Add your Gmail to OAuth consent screen → Test Users → Add |
| **invalid_client** when redirecting back | Client ID or secret typo | Re-copy both from Cloud Console, restart |
| **Token exchange failed: invalid_grant** | Auth code re-used or expired | Click Connect Google Fit again — start fresh |
| **"Fitness API has not been used"** | Fitness API not enabled in your project | Enable it: https://console.cloud.google.com/apis/library/fitness.googleapis.com |
| Connected, but **"0 data points"** | Watch hasn't synced to Google Fit yet | Companion app → Connected Apps → enable Google Fit → wear watch 5 min → Sync Now |
| **"Access token rejected"** when syncing | Token expired and refresh failed | Click Disconnect Google Fit → then Connect Google Fit again |

---

## What if you don't want to use Google Fit?

You don't have to. HeartSync also supports:

- **CSV export** — most companion apps let you export historical health data as CSV. Use the CSV upload card on the Watch page. No Google account needed.
- **Manual entry** — just type vitals directly on the Predict page (default mode).

Both are full-fidelity alternatives — your project demo works fine without Google Fit if needed.
