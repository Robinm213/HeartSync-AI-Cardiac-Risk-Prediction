"""
HeartSync — Food Image Recognition
=====================================
Identifies food from photos and returns full nutritional details
(calories + protein + carbs + fat + fiber + category).

Methods (in order of preference):
  1. Anthropic Claude Vision API (requires ANTHROPIC_API_KEY) — best accuracy.
  2. Database name match — when AI returns a name we already have full data for,
     use the verified DB nutrition rather than the model's estimate.
  3. Filename keyword fallback — if no API key, try to guess from filename.
  4. Generic estimate — last resort, marked low confidence so the user edits.

Flow: User snaps a photo → Upload → AI identifies food → Match to DB →
      Auto-fill full nutrition panel (incl. fiber + category) → Log
"""

import os
import re
import json
import base64
from typing import Dict, Any, Optional


# ─── Local nutrition fallback table ─────────────────────────────────────────
# Used when AI is unavailable or to enrich AI results that lack fiber/category.
COMMON_FOODS_NUTRITION = {
    'rice':          {'name': 'Rice (1 plate)',        'calories': 240, 'protein': 5,   'carbs': 53, 'fat': 0.5, 'fiber': 0.6, 'category': 'Grain'},
    'roti':          {'name': 'Roti / Chapati (2)',    'calories': 208, 'protein': 6,   'carbs': 36, 'fat': 7,   'fiber': 4.0, 'category': 'Grain'},
    'chapati':       {'name': 'Chapati (2)',           'calories': 208, 'protein': 6,   'carbs': 36, 'fat': 7,   'fiber': 4.0, 'category': 'Grain'},
    'naan':          {'name': 'Naan (1 pc)',           'calories': 262, 'protein': 9,   'carbs': 45, 'fat': 5,   'fiber': 2.0, 'category': 'Grain'},
    'paratha':       {'name': 'Paratha (1 pc)',        'calories': 260, 'protein': 5,   'carbs': 36, 'fat': 11,  'fiber': 2.0, 'category': 'Grain'},
    'puri':          {'name': 'Puri (2 pcs)',          'calories': 198, 'protein': 4,   'carbs': 24, 'fat': 10,  'fiber': 1.0, 'category': 'Grain'},
    'dal':           {'name': 'Dal (1 bowl)',          'calories': 198, 'protein': 14,  'carbs': 34, 'fat': 1,   'fiber': 7.5, 'category': 'Protein'},
    'paneer':        {'name': 'Paneer Curry',          'calories': 320, 'protein': 18,  'carbs': 8,  'fat': 24,  'fiber': 2.0, 'category': 'Curry'},
    'chicken':       {'name': 'Chicken Curry',         'calories': 285, 'protein': 28,  'carbs': 10, 'fat': 15,  'fiber': 1.5, 'category': 'Curry'},
    'mutton':        {'name': 'Mutton Curry',          'calories': 340, 'protein': 25,  'carbs': 8,  'fat': 22,  'fiber': 1.0, 'category': 'Curry'},
    'fish':          {'name': 'Fish Curry',            'calories': 230, 'protein': 22,  'carbs': 8,  'fat': 12,  'fiber': 1.0, 'category': 'Curry'},
    'biryani':       {'name': 'Biryani (1 plate)',     'calories': 490, 'protein': 18,  'carbs': 62, 'fat': 18,  'fiber': 2.0, 'category': 'Mixed'},
    'pulao':         {'name': 'Veg Pulao (1 plate)',   'calories': 380, 'protein': 8,   'carbs': 65, 'fat': 9,   'fiber': 3.5, 'category': 'Mixed'},
    'dosa':          {'name': 'Dosa (1 pc)',           'calories': 168, 'protein': 4,   'carbs': 27, 'fat': 5,   'fiber': 0.9, 'category': 'Grain'},
    'idli':          {'name': 'Idli (2 pcs)',          'calories': 130, 'protein': 4,   'carbs': 26, 'fat': 0.4, 'fiber': 1.2, 'category': 'Grain'},
    'samosa':        {'name': 'Samosa (1 pc)',         'calories': 262, 'protein': 4,   'carbs': 24, 'fat': 17,  'fiber': 1.8, 'category': 'Snack'},
    'pizza':         {'name': 'Pizza (1 slice)',       'calories': 285, 'protein': 12,  'carbs': 36, 'fat': 11,  'fiber': 2.5, 'category': 'Mixed'},
    'burger':        {'name': 'Burger',                'calories': 354, 'protein': 17,  'carbs': 29, 'fat': 19,  'fiber': 3.0, 'category': 'Mixed'},
    'sandwich':      {'name': 'Sandwich',              'calories': 252, 'protein': 9,   'carbs': 28, 'fat': 12,  'fiber': 2.5, 'category': 'Mixed'},
    'pasta':         {'name': 'Pasta (1 plate)',       'calories': 370, 'protein': 12,  'carbs': 55, 'fat': 11,  'fiber': 3.0, 'category': 'Grain'},
    'noodles':       {'name': 'Noodles (1 plate)',     'calories': 340, 'protein': 8,   'carbs': 50, 'fat': 12,  'fiber': 2.5, 'category': 'Grain'},
    'salad':         {'name': 'Green Salad',           'calories': 95,  'protein': 3,   'carbs': 12, 'fat': 4,   'fiber': 4.0, 'category': 'Vegetable'},
    'fruit':         {'name': 'Mixed Fruits',          'calories': 110, 'protein': 1,   'carbs': 28, 'fat': 0.5, 'fiber': 3.0, 'category': 'Fruit'},
    'apple':         {'name': 'Apple',                 'calories': 95,  'protein': 0.5, 'carbs': 25, 'fat': 0.3, 'fiber': 4.4, 'category': 'Fruit'},
    'banana':        {'name': 'Banana',                'calories': 105, 'protein': 1,   'carbs': 27, 'fat': 0.4, 'fiber': 3.1, 'category': 'Fruit'},
    'mango':         {'name': 'Mango (1 cup)',         'calories': 99,  'protein': 1.4, 'carbs': 25, 'fat': 0.6, 'fiber': 2.6, 'category': 'Fruit'},
    'orange':        {'name': 'Orange',                'calories': 62,  'protein': 1.2, 'carbs': 15, 'fat': 0.2, 'fiber': 3.1, 'category': 'Fruit'},
    'grapes':        {'name': 'Grapes (1 cup)',        'calories': 104, 'protein': 1.1, 'carbs': 27, 'fat': 0.2, 'fiber': 1.4, 'category': 'Fruit'},
    'egg':           {'name': 'Egg (2 boiled)',        'calories': 156, 'protein': 13,  'carbs': 1,  'fat': 11,  'fiber': 0,   'category': 'Protein'},
    'omelette':      {'name': 'Omelette (2 egg)',      'calories': 188, 'protein': 14,  'carbs': 2,  'fat': 14,  'fiber': 0,   'category': 'Protein'},
    'poha':          {'name': 'Poha (1 plate)',        'calories': 244, 'protein': 5,   'carbs': 42, 'fat': 7,   'fiber': 2.0, 'category': 'Grain'},
    'upma':          {'name': 'Upma (1 bowl)',         'calories': 210, 'protein': 5,   'carbs': 32, 'fat': 7,   'fiber': 3.0, 'category': 'Grain'},
    'vada':          {'name': 'Vada (2 pcs)',          'calories': 280, 'protein': 6,   'carbs': 30, 'fat': 16,  'fiber': 2.0, 'category': 'Snack'},
    'curd':          {'name': 'Curd / Yogurt (1 cup)', 'calories': 98,  'protein': 11,  'carbs': 4,  'fat': 4,   'fiber': 0,   'category': 'Dairy'},
    'yogurt':        {'name': 'Yogurt (1 cup)',        'calories': 98,  'protein': 11,  'carbs': 4,  'fat': 4,   'fiber': 0,   'category': 'Dairy'},
    'milk':          {'name': 'Milk (1 glass)',        'calories': 120, 'protein': 8,   'carbs': 12, 'fat': 5,   'fiber': 0,   'category': 'Dairy'},
    'tea':           {'name': 'Chai / Tea',            'calories': 72,  'protein': 2,   'carbs': 12, 'fat': 2,   'fiber': 0,   'category': 'Beverage'},
    'coffee':        {'name': 'Coffee',                'calories': 60,  'protein': 1,   'carbs': 10, 'fat': 2,   'fiber': 0,   'category': 'Beverage'},
    'juice':         {'name': 'Fresh Juice',           'calories': 130, 'protein': 1,   'carbs': 32, 'fat': 0,   'fiber': 0.5, 'category': 'Beverage'},
    'lassi':         {'name': 'Lassi (1 glass)',       'calories': 220, 'protein': 6,   'carbs': 35, 'fat': 6,   'fiber': 0,   'category': 'Beverage'},
    'ice cream':     {'name': 'Ice Cream (1 scoop)',   'calories': 207, 'protein': 4,   'carbs': 24, 'fat': 11,  'fiber': 0.5, 'category': 'Snack'},
    'cake':          {'name': 'Cake (1 slice)',        'calories': 352, 'protein': 5,   'carbs': 50, 'fat': 16,  'fiber': 1.0, 'category': 'Snack'},
    'chocolate':     {'name': 'Chocolate Bar',         'calories': 235, 'protein': 3,   'carbs': 26, 'fat': 14,  'fiber': 1.5, 'category': 'Snack'},
    'chips':         {'name': 'Chips / Crisps',        'calories': 274, 'protein': 3,   'carbs': 28, 'fat': 18,  'fiber': 1.5, 'category': 'Snack'},
    'pav bhaji':     {'name': 'Pav Bhaji',             'calories': 380, 'protein': 10,  'carbs': 52, 'fat': 15,  'fiber': 6.0, 'category': 'Mixed'},
    'chole':         {'name': 'Chole Bhature',         'calories': 450, 'protein': 14,  'carbs': 55, 'fat': 20,  'fiber': 7.0, 'category': 'Mixed'},
    'rajma':         {'name': 'Rajma Chawal',          'calories': 350, 'protein': 16,  'carbs': 55, 'fat': 6,   'fiber': 9.0, 'category': 'Mixed'},
    'pakora':        {'name': 'Pakora (5 pcs)',        'calories': 240, 'protein': 5,   'carbs': 22, 'fat': 14,  'fiber': 3.0, 'category': 'Snack'},
    'dhokla':        {'name': 'Dhokla (2 pcs)',        'calories': 160, 'protein': 6,   'carbs': 25, 'fat': 4,   'fiber': 2.0, 'category': 'Snack'},
}


def _normalise(food: Dict, source: str, confidence: str) -> Dict:
    """Ensure every returned record has the full nutrition schema."""
    return {
        'name':       food.get('name', 'Unknown Food'),
        'calories':   int(food.get('calories', 0) or 0),
        'protein':    float(food.get('protein', 0) or 0),
        'carbs':      float(food.get('carbs', 0) or 0),
        'fat':        float(food.get('fat', 0) or 0),
        'fiber':      float(food.get('fiber', 0) or 0),
        'category':   food.get('category', 'Food'),
        'source':     source,
        'confidence': confidence,
    }


def _match_to_db(food_name: str) -> Optional[Dict]:
    """Match a recognised food name against the local FOOD_DATABASE for verified values."""
    try:
        from food_database import FOOD_DATABASE
    except Exception:
        return None
    if not food_name:
        return None
    food_name_lower = food_name.lower()
    # 1) full substring match against DB names
    for barcode, food in FOOD_DATABASE.items():
        if food_name_lower in food['name'].lower() or food['name'].lower() in food_name_lower:
            return {**food, 'barcode': barcode}
    # 2) word-by-word match (only meaningful words)
    words = [w for w in re.split(r'[^a-z]+', food_name_lower) if len(w) > 3]
    for barcode, food in FOOD_DATABASE.items():
        name_lower = food['name'].lower()
        if any(w in name_lower for w in words):
            return {**food, 'barcode': barcode}
    return None


def _local_keyword_match(text: str) -> Optional[Dict]:
    """Match arbitrary text against the COMMON_FOODS_NUTRITION fallback table."""
    if not text:
        return None
    t = text.lower()
    for keyword, nutrition in COMMON_FOODS_NUTRITION.items():
        if keyword in t:
            return dict(nutrition)
    return None


# ─── Claude Vision API ───────────────────────────────────────────────────────

def identify_food_with_api(image_base64: str, api_key: str, mime: str = 'image/jpeg') -> Optional[Dict]:
    """Use Anthropic Claude Vision to identify food from image."""
    import requests

    prompt = (
        "Identify the food item(s) in this image. Reply ONLY with a JSON object "
        "(no markdown, no commentary) using this exact schema:\n"
        '{"food_name": "...", "calories_per_serving": 0, "protein_g": 0, '
        '"carbs_g": 0, "fat_g": 0, "fiber_g": 0, "serving_size": "...", '
        '"category": "Grain|Protein|Curry|Vegetable|Fruit|Dairy|Beverage|Snack|Mixed", '
        '"confidence": "high|medium|low"}\n'
        "If multiple items are visible, return the totals for the whole plate. "
        "Be realistic with Indian-cuisine portions if the dish looks Indian."
    )

    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 400,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': image_base64}},
                        {'type': 'text', 'text': prompt},
                    ],
                }],
            },
            timeout=30,
        )
        data = resp.json()
        text = data.get('content', [{}])[0].get('text', '').strip()
        text = re.sub(r'^```(?:json)?|```$', '', text, flags=re.MULTILINE).strip()
        parsed = json.loads(text)
        return {
            'name':       parsed.get('food_name', 'Unknown Food'),
            'calories':   parsed.get('calories_per_serving', 0),
            'protein':    parsed.get('protein_g', 0),
            'carbs':      parsed.get('carbs_g', 0),
            'fat':        parsed.get('fat_g', 0),
            'fiber':      parsed.get('fiber_g', 0),
            'category':   parsed.get('category', 'Food'),
            'serving_size': parsed.get('serving_size', '1 serving'),
            'confidence': parsed.get('confidence', 'medium'),
        }
    except Exception as e:
        print(f"AI food recognition error: {e}")
        return None


# ─── Public entry point ──────────────────────────────────────────────────────

def process_food_image(image_data: bytes, filename: str = '') -> Dict:
    """
    Identify food from image and return full nutritional details.

    Pipeline:
      1) Try Claude Vision (if ANTHROPIC_API_KEY set)
      2) Match the AI's food name against the local DB for verified nutrition
         — fall back to AI's estimates if no match.
      3) If no AI: try filename keyword match against the COMMON foods table.
      4) Otherwise return a generic editable estimate (low confidence).
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '')

    # Determine MIME from filename (default jpeg)
    ext = (filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg').lower()
    mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'webp': 'image/webp'}.get(ext, 'image/jpeg')
    image_b64 = base64.b64encode(image_data).decode('utf-8')

    # Stage 1 — AI Vision
    if api_key:
        ai = identify_food_with_api(image_b64, api_key, mime)
        if ai:
            # Stage 2 — try to upgrade with verified DB values
            matched = _match_to_db(ai['name'])
            if matched:
                merged = {
                    'name':     matched['name'],
                    'calories': matched['calories'],
                    'protein':  matched['protein'],
                    'carbs':    matched['carbs'],
                    'fat':      matched['fat'],
                    'fiber':    matched.get('fiber', ai.get('fiber', 0)),
                    'category': matched.get('category', ai.get('category', 'Food')),
                }
                merged['detected_name'] = ai['name']
                return _normalise(merged, source='ai_vision+db', confidence='high')
            return _normalise(ai, source='ai_vision', confidence=ai.get('confidence', 'medium'))

    # Stage 3 — filename keyword match
    if filename:
        local = _local_keyword_match(filename)
        if local:
            return _normalise(local, source='filename_match', confidence='medium')
        db_match = _match_to_db(filename)
        if db_match:
            return _normalise(db_match, source='filename_db_match', confidence='medium')

    # Stage 4 — generic editable fallback
    return _normalise({
        'name':     'Meal (edit name below)',
        'calories': 350,
        'protein':  15,
        'carbs':    45,
        'fat':      12,
        'fiber':    3,
        'category': 'Mixed',
    }, source='photo_estimate', confidence='low') | {
        'note': 'Photo saved! Edit the food name and calories above, then tap Log. '
                'For automatic detection set ANTHROPIC_API_KEY.'
    }
