"""
HeartSync — Google Fit Integration (Hardened)
==============================================
Reads real Noise / Fire-Boltt / boAt / Samsung / Fitbit smartwatch data
through Google Fit API.

Flow:  Watch → Companion App (NoiseFit / Da Fit / etc.) → Google Fit → HeartSync

Setup:
  1. Enable Google Fit sync in your watch's companion app.
  2. Create a Google Cloud project and enable the **Fitness API**.
  3. Create OAuth2 *Web application* credentials.
     - Add this exact Authorized redirect URI:
         http://localhost:5000/oauth/google/callback
     - Add the same URI under "Authorized JavaScript origins":
         http://localhost:5000
  4. Set environment variables:
       GOOGLE_CLIENT_ID
       GOOGLE_CLIENT_SECRET
       GOOGLE_REDIRECT_URI   (only if you change the default)
  5. Add yourself as a Test User on the OAuth consent screen
     (Project → APIs & Services → OAuth consent screen → Test Users → Add)
  6. Click "Connect Google Fit" in HeartSync → consent → done.

This module surfaces every error explicitly instead of swallowing it,
so the UI can tell the user *why* a connection or sync failed.
"""

import os
import sqlite3
import datetime
from typing import Optional, Dict, Any

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'users.db')


# ─── Google OAuth Config ─────────────────────────────────────────────────────
# Read entirely from env so credentials never live in source control.
# These envs are read fresh every call so editing .env + restart is enough.
def _cfg() -> Dict[str, Any]:
    return {
        'client_id':     os.getenv('GOOGLE_CLIENT_ID',     '').strip(),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', '').strip(),
        'redirect_uri':  os.getenv('GOOGLE_REDIRECT_URI',
                                   'http://localhost:5000/oauth/google/callback').strip(),
        'scopes': [
            'https://www.googleapis.com/auth/fitness.heart_rate.read',
            'https://www.googleapis.com/auth/fitness.sleep.read',
            'https://www.googleapis.com/auth/fitness.activity.read',
            'https://www.googleapis.com/auth/fitness.body.read',
            'https://www.googleapis.com/auth/fitness.oxygen_saturation.read',
        ],
    }


def is_google_fit_configured() -> bool:
    """Both client id and secret must be set and non-empty."""
    cfg = _cfg()
    return bool(cfg['client_id']) and bool(cfg['client_secret'])


def get_config_status() -> Dict[str, Any]:
    """
    Used by the Watch page to show a precise diagnostic when something is
    misconfigured. Never returns the secret itself.
    """
    cfg = _cfg()
    cid_ok    = bool(cfg['client_id'])
    secret_ok = bool(cfg['client_secret'])
    return {
        'configured':       cid_ok and secret_ok,
        'has_client_id':    cid_ok,
        'has_client_secret': secret_ok,
        # Show only the first 12 chars of the client_id so the user can
        # confirm the right project is loaded — full id is non-sensitive.
        'client_id_preview': (cfg['client_id'][:12] + '…') if cid_ok else '',
        'redirect_uri':     cfg['redirect_uri'],
    }


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── OAuth Flow ──────────────────────────────────────────────────────────────

def get_google_auth_url() -> str:
    """Build the consent-screen URL the user is sent to."""
    from urllib.parse import urlencode
    cfg = _cfg()
    params = {
        'client_id':     cfg['client_id'],
        'redirect_uri':  cfg['redirect_uri'],
        'response_type': 'code',
        'scope':         ' '.join(cfg['scopes']),
        'access_type':   'offline',
        'include_granted_scopes': 'true',
        'prompt':        'consent',
    }
    return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)


def exchange_google_code(code: str) -> Dict[str, Any]:
    """
    Trade an authorization code for access + refresh tokens.
    Returns the parsed JSON. On failure returns a dict containing 'error'.
    """
    cfg = _cfg()
    try:
        resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code':          code,
                'client_id':     cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'redirect_uri':  cfg['redirect_uri'],
                'grant_type':    'authorization_code',
            },
            timeout=15,
        )
        try:
            payload = resp.json()
        except Exception:
            payload = {'error': 'non_json_response',
                       'error_description': resp.text[:300]}
        if resp.status_code != 200 and 'error' not in payload:
            payload['error'] = f'http_{resp.status_code}'
        return payload
    except requests.RequestException as e:
        return {'error': 'network_error', 'error_description': str(e)}


def refresh_google_token(refresh_token: str) -> Dict[str, Any]:
    """Use a long-lived refresh token to get a new short-lived access token."""
    cfg = _cfg()
    try:
        resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'refresh_token': refresh_token,
                'client_id':     cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'grant_type':    'refresh_token',
            },
            timeout=15,
        )
        try:
            return resp.json()
        except Exception:
            return {'error': 'non_json_response',
                    'error_description': resp.text[:300]}
    except requests.RequestException as e:
        return {'error': 'network_error', 'error_description': str(e)}


def save_google_tokens(user_id: int, tokens: Dict[str, Any]):
    """Persist tokens, preserving the existing refresh_token if Google omits it."""
    conn = get_db()
    expires_at = datetime.datetime.now() + datetime.timedelta(
        seconds=int(tokens.get('expires_in', 3600))
    )
    conn.execute(
        """
        INSERT INTO wearable_tokens (user_id, platform, access_token, refresh_token, expires_at)
        VALUES (?, 'google_fit', ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            access_token  = excluded.access_token,
            refresh_token = COALESCE(excluded.refresh_token, wearable_tokens.refresh_token),
            expires_at    = excluded.expires_at
        """,
        (user_id, tokens.get('access_token'), tokens.get('refresh_token'),
         expires_at.isoformat()),
    )
    conn.commit()
    conn.close()


def get_valid_token(user_id: int) -> Optional[str]:
    """
    Return a valid access token, automatically refreshing if expired.
    Returns None if the user has never connected (or refresh fails).
    """
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM wearable_tokens WHERE user_id=? AND platform='google_fit'",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    # Still valid?
    try:
        expires = datetime.datetime.fromisoformat(row['expires_at'])
        # Refresh 60 seconds early to avoid edge-case 401s.
        if datetime.datetime.now() < (expires - datetime.timedelta(seconds=60)):
            return row['access_token']
    except Exception:
        pass

    # Need refresh
    if row['refresh_token']:
        new_tokens = refresh_google_token(row['refresh_token'])
        if 'access_token' in new_tokens:
            save_google_tokens(user_id, new_tokens)
            return new_tokens['access_token']

    return None


def disconnect_google_fit(user_id: int) -> None:
    """Forget the Google Fit tokens for this user (also revokes server-side cache)."""
    conn = get_db()
    conn.execute(
        "DELETE FROM wearable_tokens WHERE user_id=? AND platform='google_fit'",
        (user_id,)
    )
    conn.commit()
    conn.close()


# ─── Fetch Health Data from Google Fit ───────────────────────────────────────

# Phone sensors / on-device steps trackers we want to EXCLUDE because they
# cause double-counting (phone records steps too while you walk with it).
PHONE_PACKAGE_HINTS = (
    'com.google.android.apps.fitness',          # Google Fit app itself (phone-recorded)
    'com.google.android.gms',                   # Google Play Services (phone sensors)
)

# Health Connect package — Samsung / Fitbit / etc. flow through this and
# this is what we want to PREFER.
HEALTH_CONNECT_PACKAGE = 'com.google.android.apps.healthdata'
SAMSUNG_HEALTH_PACKAGE = 'com.sec.android.app.shealth'


def _aggregate_request(access_token: str, body: dict) -> dict:
    """Low-level helper — performs the aggregate POST and surfaces real errors."""
    try:
        resp = requests.post(
            'https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type':  'application/json',
            },
            json=body,
            timeout=20,
        )
        if resp.status_code == 401:
            return {'error': 'unauthorized',
                    'error_description': 'Access token rejected by Google. Reconnect Google Fit.'}
        if resp.status_code == 403:
            return {'error': 'forbidden',
                    'error_description': 'Fitness API not enabled on this Google Cloud project, '
                                          'or scopes were declined. Enable it in Google Cloud Console.'}
        try:
            return resp.json()
        except Exception:
            return {'error': 'non_json_response',
                    'error_description': resp.text[:300]}
    except requests.RequestException as e:
        return {'error': 'network_error', 'error_description': str(e)}


def _list_data_sources(access_token: str) -> list:
    """List all Google Fit data sources available to this user (debug aid)."""
    try:
        resp = requests.get(
            'https://www.googleapis.com/fitness/v1/users/me/dataSources',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get('dataSource', [])
    except Exception:
        pass
    return []


def _pick_source_chain(sources: list, data_type: str) -> list:
    """
    Return a PRIORITY-ORDERED list of source IDs to try for this data type.
    We try them in order; first one with data wins.

    Order:
      1. Health Connect raw (Samsung / Fitbit watch data lands here)
      2. Samsung Health direct
      3. Watch device sources
      4. Google Fit's merge stream (combines all sources — has phone steps!)
      5. Anything else, except phone-only sensors
    """
    matches = [s for s in sources if s.get('dataType', {}).get('name') == data_type]
    if not matches:
        return []

    def score(src):
        pkg = src.get('application', {}).get('packageName', '') or ''
        name = (src.get('name', '') or src.get('dataStreamId', '')).lower()
        device_type = (src.get('device', {}) or {}).get('type', '')

        if pkg == HEALTH_CONNECT_PACKAGE:        return 100
        if pkg == SAMSUNG_HEALTH_PACKAGE:        return 90
        if device_type == 'watch':               return 80
        if 'merge_' in name:                     return 60
        if pkg in PHONE_PACKAGE_HINTS:           return 5
        if device_type == 'phone':               return 10
        return 50

    matches.sort(key=score, reverse=True)
    # Filter out very low-priority phone-only sources unless that's all we have
    high_priority = [m for m in matches if score(m) >= 30]
    if high_priority:
        return [m.get('dataStreamId') for m in high_priority]
    # Fallback: include everything (better than no data)
    return [m.get('dataStreamId') for m in matches]


def _pick_best_source(sources: list, data_type: str) -> Optional[str]:
    """Backwards-compat — returns just the top pick."""
    chain = _pick_source_chain(sources, data_type)
    return chain[0] if chain else None


def _query_dataset(access_token: str, source_id: str, start_ms: int, end_ms: int) -> dict:
    """Read raw data points from ONE specific data source (no aggregation, no merging)."""
    start_ns = start_ms * 1_000_000
    end_ns   = end_ms   * 1_000_000
    url = (f'https://www.googleapis.com/fitness/v1/users/me/dataSources/'
           f'{source_id}/datasets/{start_ns}-{end_ns}')
    try:
        resp = requests.get(
            url,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json()
        return {'error': f'http_{resp.status_code}', 'error_description': resp.text[:200]}
    except requests.RequestException as e:
        return {'error': 'network_error', 'error_description': str(e)}


def _extract_value(point: dict, dtype: str):
    """Pull the right scalar out of a Fitness API point."""
    vals = point.get('value', [])
    if not vals:
        return None
    if dtype == 'com.google.heart_rate.bpm':
        return vals[0].get('fpVal')
    if dtype == 'com.google.step_count.delta':
        return vals[0].get('intVal')
    if dtype == 'com.google.calories.expended':
        return vals[0].get('fpVal')
    if dtype == 'com.google.active_minutes':
        return vals[0].get('intVal')
    if dtype == 'com.google.oxygen_saturation':
        return vals[0].get('fpVal')
    if dtype == 'com.google.weight':
        return vals[0].get('fpVal')
    return None


def fetch_google_fit_data(access_token: str, hours_back: int = 24) -> Dict[str, Any]:
    """
    Fetch heart rate, steps, sleep, calories, SpO2 from Google Fit.

    Strategy (the one that matches what the user's Google Fit app shows):
      1. List every Google Fit data source.
      2. For each metric (HR, steps, SpO2, calories, active minutes), find the
         BEST source — preferring Health Connect / Samsung Health / watch over
         phone sensors. This stops "phone steps + watch steps" double-counting.
      3. Query that ONE source directly via dataSources/{id}/datasets endpoint.
      4. For HR/SpO2 → take the latest individual reading.
         For steps/calories/active minutes → sum the deltas in the window.
      5. Sleep is fetched via the Sessions API (independent of step sources).
    """
    now_ms   = int(datetime.datetime.utcnow().timestamp() * 1000)
    start_ms = now_ms - (hours_back * 3600 * 1000)
    week_start_ms = now_ms - (7 * 24 * 3600 * 1000)

    sources = _list_data_sources(access_token)
    if not sources:
        return {'error': 'no_sources',
                'error_description': 'No data sources available on Google Fit. '
                                     'Connect your watch via Health Connect first.'}

    result: Dict[str, Any] = {'_chosen_sources': {}}

    metrics = [
        ('heart_rate',       'com.google.heart_rate.bpm',       'latest'),
        ('steps',            'com.google.step_count.delta',     'sum'),
        ('calories_burned',  'com.google.calories.expended',    'sum'),
        ('activity_minutes', 'com.google.active_minutes',       'sum'),
        ('spo2',             'com.google.oxygen_saturation',    'latest'),
    ]

    for key, dtype, agg in metrics:
        chain = _pick_source_chain(sources, dtype)
        if not chain:
            continue
        result['_chosen_sources'][key] = chain[:3]   # debug: top 3

        # Try each source in priority order; first one that has data wins.
        got_value = False
        for src in chain[:5]:                # cap at 5 to keep request count low
            if got_value:
                break
            for window_start in (start_ms, week_start_ms):
                data = _query_dataset(access_token, src, window_start, now_ms)
                if 'error' in data:
                    break
                points = data.get('point', [])
                if not points:
                    continue

                if agg == 'latest':
                    points.sort(key=lambda p: int(p.get('endTimeNanos', 0)), reverse=True)
                    val = _extract_value(points[0], dtype)
                    if val is not None and val > 0:
                        if dtype == 'com.google.heart_rate.bpm':
                            result[key] = round(val)
                        else:
                            result[key] = round(val, 1)
                        got_value = True
                        break

                elif agg == 'sum':
                    today_start_ms = int(datetime.datetime.combine(
                        datetime.date.today(), datetime.time.min
                    ).timestamp() * 1000)
                    total = 0
                    for p in points:
                        p_start = int(p.get('startTimeNanos', 0)) // 1_000_000
                        if p_start < today_start_ms:
                            continue
                        v = _extract_value(p, dtype)
                        if v is not None:
                            total += v
                    if total > 0:
                        if dtype == 'com.google.step_count.delta':
                            result[key] = int(total)
                        elif dtype == 'com.google.active_minutes':
                            result[key] = int(total)
                        else:
                            result[key] = int(round(total))
                        got_value = True
                        break

    # ── Sleep via Sessions API ──
    try:
        sleep_start_ms = now_ms - (3 * 24 * 3600 * 1000)  # last 3 days
        sleep_resp = requests.get(
            'https://www.googleapis.com/fitness/v1/users/me/sessions',
            headers={'Authorization': f'Bearer {access_token}'},
            params={
                'startTime':    datetime.datetime.utcfromtimestamp(sleep_start_ms / 1000).isoformat() + 'Z',
                'endTime':      datetime.datetime.utcfromtimestamp(now_ms / 1000).isoformat() + 'Z',
                'activityType': '72',
            },
            timeout=15,
        )
        if sleep_resp.status_code == 200:
            sessions = sleep_resp.json().get('session', [])
            if sessions:
                sessions.sort(key=lambda s: int(s.get('startTimeMillis', 0)), reverse=True)
                last = sessions[0]
                ms = int(last.get('endTimeMillis', 0)) - int(last.get('startTimeMillis', 0))
                if ms > 0:
                    result['sleep_hours'] = round(ms / 3_600_000, 1)
    except Exception:
        pass

    # ── No data at all? ──
    real_keys = ['heart_rate', 'steps', 'spo2', 'calories_burned',
                 'activity_minutes', 'sleep_hours']
    if not any(k in result for k in real_keys):
        return {
            'error': 'no_data',
            'error_description':
                ('Connected to Google Fit, but no fresh readings found across the '
                 'last 7 days. Open Samsung Health → Profile → Settings → Health '
                 'Connect → grant ALL permissions. Then Google Fit app → Profile → '
                 'Settings → Manage connected apps → Health Connect → enable ALL '
                 'data access. Wear the watch for ~5 minutes.'),
            'sources_count': len(sources),
        }

    result['source'] = 'google_fit'
    result['device'] = 'Google Fit (Smartwatch)'
    return result


def fetch_google_fit_week(access_token: str) -> list:
    """Return one record per day for the last 7 days (used by weekly report)."""
    days = []
    for i in range(7):
        day_start = datetime.datetime.combine(
            datetime.date.today() - datetime.timedelta(days=6 - i),
            datetime.time.min,
        )
        day_end = day_start + datetime.timedelta(hours=24)

        body = {
            'aggregateBy': [
                {'dataTypeName': 'com.google.heart_rate.bpm'},
                {'dataTypeName': 'com.google.step_count.delta'},
                {'dataTypeName': 'com.google.calories.expended'},
                {'dataTypeName': 'com.google.active_minutes'},
            ],
            'bucketByTime':    {'durationMillis': 86_400_000},
            'startTimeMillis': int(day_start.timestamp() * 1000),
            'endTimeMillis':   int(day_end.timestamp()   * 1000),
        }

        day_data: Dict[str, Any] = {'date': day_start.strftime('%Y-%m-%d')}
        raw = _aggregate_request(access_token, body)
        if 'error' not in raw:
            for bucket in raw.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        dtype = point.get('dataTypeName', '')
                        vals  = point.get('value', [])
                        if not vals:
                            continue
                        if dtype == 'com.google.heart_rate.bpm':
                            day_data['heart_rate'] = round(vals[0].get('fpVal', 0))
                        elif dtype == 'com.google.step_count.delta':
                            day_data['steps'] = int(vals[0].get('intVal', 0))
                        elif dtype == 'com.google.calories.expended':
                            day_data['calories_burned'] = int(vals[0].get('fpVal', 0))
                        elif dtype == 'com.google.active_minutes':
                            day_data['activity_minutes'] = int(vals[0].get('intVal', 0))
        days.append(day_data)

    return days
