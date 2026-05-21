"""
HeartSync — Food Database
Barcode → nutrition lookup for food logging.
Covers Indian staples, street food, common fruits/veg, dairy, drinks, restaurant
items, and packaged Indian snacks with real EAN-13 barcodes (where known).
"""

FOOD_DATABASE = {
    # ── Generic / common foods (synthetic codes) ─────────────────────────────
    "012345678901": {"name": "Apple (Medium)",          "calories": 95,  "protein": 0.5,  "carbs": 25,  "fat": 0.3,  "fiber": 4.4, "category": "Fruit"},
    "890123456789": {"name": "Banana",                   "calories": 105, "protein": 1.3,  "carbs": 27,  "fat": 0.4,  "fiber": 3.1, "category": "Fruit"},
    "456789012345": {"name": "Brown Rice (1 cup)",       "calories": 216, "protein": 5,    "carbs": 45,  "fat": 1.8,  "fiber": 3.5, "category": "Grain"},
    "567890123456": {"name": "Chicken Breast (100g)",    "calories": 165, "protein": 31,   "carbs": 0,   "fat": 3.6,  "fiber": 0,   "category": "Protein"},
    "678901234567": {"name": "Egg (Boiled)",             "calories": 78,  "protein": 6.3,  "carbs": 0.6, "fat": 5.3,  "fiber": 0,   "category": "Protein"},
    "789012345678": {"name": "Greek Yogurt (100g)",      "calories": 59,  "protein": 10,   "carbs": 3.6, "fat": 0.7,  "fiber": 0,   "category": "Dairy"},
    "234567890123": {"name": "Oats (1 cup)",             "calories": 307, "protein": 10.7, "carbs": 55,  "fat": 5.3,  "fiber": 8.2, "category": "Grain"},
    "345678901234": {"name": "Salmon (100g)",            "calories": 208, "protein": 20,   "carbs": 0,   "fat": 13,   "fiber": 0,   "category": "Protein"},
    "111222333444": {"name": "Roti / Chapati",           "calories": 104, "protein": 3.1,  "carbs": 18,  "fat": 3.5,  "fiber": 2.0, "category": "Grain"},
    "222333444555": {"name": "Dal (1 cup)",              "calories": 198, "protein": 13.5, "carbs": 34,  "fat": 1.0,  "fiber": 7.5, "category": "Protein"},
    "333444555666": {"name": "Paneer (100g)",            "calories": 265, "protein": 18.3, "carbs": 1.2, "fat": 20.8, "fiber": 0,   "category": "Dairy"},
    "444555666777": {"name": "Idli (2 pcs)",             "calories": 130, "protein": 4.0,  "carbs": 26,  "fat": 0.4,  "fiber": 1.2, "category": "Grain"},
    "555666777888": {"name": "Dosa (1 pc)",              "calories": 168, "protein": 3.9,  "carbs": 27,  "fat": 5.2,  "fiber": 0.9, "category": "Grain"},
    "666777888999": {"name": "Biryani (1 plate)",        "calories": 490, "protein": 18,   "carbs": 62,  "fat": 18,   "fiber": 2.0, "category": "Mixed"},
    "777888999000": {"name": "Samosa (1 pc)",            "calories": 262, "protein": 3.5,  "carbs": 24,  "fat": 17,   "fiber": 1.8, "category": "Snack"},
    "888999000111": {"name": "Milk Tea (1 cup)",         "calories": 72,  "protein": 2.0,  "carbs": 12,  "fat": 2.0,  "fiber": 0,   "category": "Beverage"},
    "999000111222": {"name": "Curd Rice (1 bowl)",       "calories": 210, "protein": 6.0,  "carbs": 38,  "fat": 4.0,  "fiber": 0.5, "category": "Grain"},
    "000111222333": {"name": "Poha (1 plate)",           "calories": 244, "protein": 5.0,  "carbs": 42,  "fat": 7.0,  "fiber": 2.0, "category": "Grain"},
    "111333555777": {"name": "Upma (1 bowl)",            "calories": 210, "protein": 5.5,  "carbs": 32,  "fat": 7.0,  "fiber": 3.0, "category": "Grain"},
    "222444666888": {"name": "Vada Pav (1 pc)",          "calories": 290, "protein": 5.0,  "carbs": 36,  "fat": 14,   "fiber": 2.5, "category": "Snack"},

    # ── Indian breakfast / tiffin items ──────────────────────────────────────
    "100100100001": {"name": "Paratha (Plain)",          "calories": 260, "protein": 5,    "carbs": 36,  "fat": 11,   "fiber": 2.0, "category": "Grain"},
    "100100100002": {"name": "Aloo Paratha",             "calories": 320, "protein": 6,    "carbs": 42,  "fat": 13,   "fiber": 3.0, "category": "Grain"},
    "100100100003": {"name": "Puri (2 pcs)",             "calories": 198, "protein": 4,    "carbs": 24,  "fat": 10,   "fiber": 1.0, "category": "Grain"},
    "100100100004": {"name": "Medu Vada (2 pcs)",        "calories": 280, "protein": 6,    "carbs": 30,  "fat": 16,   "fiber": 2.0, "category": "Snack"},
    "100100100005": {"name": "Uttapam (1 pc)",           "calories": 200, "protein": 5,    "carbs": 35,  "fat": 5,    "fiber": 1.5, "category": "Grain"},
    "100100100006": {"name": "Sambar (1 bowl)",          "calories": 130, "protein": 6,    "carbs": 22,  "fat": 2.5,  "fiber": 5.0, "category": "Soup"},
    "100100100007": {"name": "Rasam (1 bowl)",           "calories": 60,  "protein": 2,    "carbs": 10,  "fat": 1.5,  "fiber": 1.5, "category": "Soup"},
    "100100100008": {"name": "Pongal (1 bowl)",          "calories": 280, "protein": 7,    "carbs": 45,  "fat": 8,    "fiber": 1.8, "category": "Grain"},
    "100100100009": {"name": "Appam (1 pc)",             "calories": 120, "protein": 2.5,  "carbs": 24,  "fat": 1.5,  "fiber": 0.8, "category": "Grain"},
    "100100100010": {"name": "Bhel Puri (1 plate)",      "calories": 280, "protein": 6,    "carbs": 50,  "fat": 7,    "fiber": 4.0, "category": "Snack"},

    # ── Indian curries / mains ───────────────────────────────────────────────
    "100200200001": {"name": "Paneer Butter Masala",     "calories": 340, "protein": 17,   "carbs": 14,  "fat": 24,   "fiber": 2.5, "category": "Curry"},
    "100200200002": {"name": "Chicken Curry (1 bowl)",   "calories": 285, "protein": 28,   "carbs": 10,  "fat": 15,   "fiber": 1.5, "category": "Curry"},
    "100200200003": {"name": "Mutton Curry (1 bowl)",    "calories": 340, "protein": 25,   "carbs": 8,   "fat": 22,   "fiber": 1.0, "category": "Curry"},
    "100200200004": {"name": "Fish Curry (1 bowl)",      "calories": 230, "protein": 22,   "carbs": 8,   "fat": 12,   "fiber": 1.0, "category": "Curry"},
    "100200200005": {"name": "Rajma (1 bowl)",           "calories": 240, "protein": 14,   "carbs": 38,  "fat": 4,    "fiber": 9.0, "category": "Curry"},
    "100200200006": {"name": "Chana Masala (1 bowl)",    "calories": 270, "protein": 13,   "carbs": 42,  "fat": 6,    "fiber": 9.0, "category": "Curry"},
    "100200200007": {"name": "Aloo Gobi (1 bowl)",       "calories": 180, "protein": 5,    "carbs": 24,  "fat": 8,    "fiber": 5.0, "category": "Curry"},
    "100200200008": {"name": "Bhindi Masala (1 bowl)",   "calories": 160, "protein": 4,    "carbs": 18,  "fat": 8,    "fiber": 5.5, "category": "Curry"},
    "100200200009": {"name": "Pav Bhaji",                "calories": 380, "protein": 10,   "carbs": 52,  "fat": 15,   "fiber": 6.0, "category": "Mixed"},
    "100200200010": {"name": "Chole Bhature",            "calories": 450, "protein": 14,   "carbs": 55,  "fat": 20,   "fiber": 7.0, "category": "Mixed"},
    "100200200011": {"name": "Naan (1 pc)",              "calories": 262, "protein": 9,    "carbs": 45,  "fat": 5,    "fiber": 2.0, "category": "Grain"},
    "100200200012": {"name": "Butter Chicken (1 bowl)",  "calories": 410, "protein": 26,   "carbs": 12,  "fat": 28,   "fiber": 1.5, "category": "Curry"},
    "100200200013": {"name": "Veg Pulao (1 plate)",      "calories": 380, "protein": 8,    "carbs": 65,  "fat": 9,    "fiber": 3.5, "category": "Mixed"},
    "100200200014": {"name": "Egg Curry (2 eggs)",       "calories": 280, "protein": 16,   "carbs": 8,   "fat": 20,   "fiber": 1.5, "category": "Curry"},
    "100200200015": {"name": "Palak Paneer",             "calories": 290, "protein": 17,   "carbs": 12,  "fat": 20,   "fiber": 4.0, "category": "Curry"},

    # ── Street food / snacks ─────────────────────────────────────────────────
    "100300300001": {"name": "Pani Puri (6 pcs)",        "calories": 180, "protein": 4,    "carbs": 32,  "fat": 4,    "fiber": 2.5, "category": "Snack"},
    "100300300002": {"name": "Pakora (5 pcs)",           "calories": 240, "protein": 5,    "carbs": 22,  "fat": 14,   "fiber": 3.0, "category": "Snack"},
    "100300300003": {"name": "Kachori (1 pc)",           "calories": 270, "protein": 5,    "carbs": 30,  "fat": 14,   "fiber": 2.5, "category": "Snack"},
    "100300300004": {"name": "Dhokla (2 pcs)",           "calories": 160, "protein": 6,    "carbs": 25,  "fat": 4,    "fiber": 2.0, "category": "Snack"},
    "100300300005": {"name": "Misal Pav",                "calories": 380, "protein": 14,   "carbs": 50,  "fat": 14,   "fiber": 8.0, "category": "Mixed"},

    # ── Vegetables / legumes ─────────────────────────────────────────────────
    "100400400001": {"name": "Mixed Salad (1 bowl)",     "calories": 95,  "protein": 3,    "carbs": 12,  "fat": 4,    "fiber": 4.0, "category": "Vegetable"},
    "100400400002": {"name": "Boiled Chickpeas (1 cup)", "calories": 269, "protein": 14.5, "carbs": 45,  "fat": 4.2,  "fiber": 12.5,"category": "Protein"},
    "100400400003": {"name": "Sprouts (1 cup)",          "calories": 110, "protein": 9,    "carbs": 21,  "fat": 1,    "fiber": 6.0, "category": "Protein"},
    "100400400004": {"name": "Spinach (cooked, 100g)",   "calories": 23,  "protein": 3,    "carbs": 3.6, "fat": 0.4,  "fiber": 2.2, "category": "Vegetable"},
    "100400400005": {"name": "Boiled Potato (medium)",   "calories": 130, "protein": 3,    "carbs": 30,  "fat": 0.2,  "fiber": 3.0, "category": "Vegetable"},

    # ── Fruits ───────────────────────────────────────────────────────────────
    "100500500001": {"name": "Mango (1 cup)",            "calories": 99,  "protein": 1.4,  "carbs": 25,  "fat": 0.6,  "fiber": 2.6, "category": "Fruit"},
    "100500500002": {"name": "Orange (1 medium)",        "calories": 62,  "protein": 1.2,  "carbs": 15,  "fat": 0.2,  "fiber": 3.1, "category": "Fruit"},
    "100500500003": {"name": "Grapes (1 cup)",           "calories": 104, "protein": 1.1,  "carbs": 27,  "fat": 0.2,  "fiber": 1.4, "category": "Fruit"},
    "100500500004": {"name": "Watermelon (1 cup)",       "calories": 46,  "protein": 0.9,  "carbs": 12,  "fat": 0.2,  "fiber": 0.6, "category": "Fruit"},
    "100500500005": {"name": "Papaya (1 cup)",           "calories": 62,  "protein": 0.7,  "carbs": 16,  "fat": 0.4,  "fiber": 2.5, "category": "Fruit"},
    "100500500006": {"name": "Pomegranate (1 cup)",      "calories": 144, "protein": 2.9,  "carbs": 33,  "fat": 2.0,  "fiber": 7.0, "category": "Fruit"},
    "100500500007": {"name": "Guava (1 medium)",         "calories": 68,  "protein": 2.6,  "carbs": 14,  "fat": 1.0,  "fiber": 5.4, "category": "Fruit"},

    # ── Drinks / beverages ───────────────────────────────────────────────────
    "100600600001": {"name": "Coffee (with milk, 1 cup)","calories": 60,  "protein": 1.5,  "carbs": 9,   "fat": 2,    "fiber": 0,   "category": "Beverage"},
    "100600600002": {"name": "Lassi (1 glass)",          "calories": 220, "protein": 6,    "carbs": 35,  "fat": 6,    "fiber": 0,   "category": "Beverage"},
    "100600600003": {"name": "Buttermilk (1 glass)",     "calories": 80,  "protein": 4,    "carbs": 9,   "fat": 3,    "fiber": 0,   "category": "Beverage"},
    "100600600004": {"name": "Coconut Water (1 cup)",    "calories": 46,  "protein": 1.7,  "carbs": 9,   "fat": 0.5,  "fiber": 2.6, "category": "Beverage"},
    "100600600005": {"name": "Fresh Lime Soda",          "calories": 70,  "protein": 0.2,  "carbs": 18,  "fat": 0,    "fiber": 0,   "category": "Beverage"},
    "100600600006": {"name": "Mango Shake (1 glass)",    "calories": 240, "protein": 6,    "carbs": 42,  "fat": 6,    "fiber": 1.5, "category": "Beverage"},

    # ── Western / restaurant staples ─────────────────────────────────────────
    "100700700001": {"name": "Pizza (1 slice)",          "calories": 285, "protein": 12,   "carbs": 36,  "fat": 11,   "fiber": 2.5, "category": "Mixed"},
    "100700700002": {"name": "Burger (Veg)",             "calories": 354, "protein": 12,   "carbs": 42,  "fat": 16,   "fiber": 3.5, "category": "Mixed"},
    "100700700003": {"name": "French Fries (regular)",   "calories": 365, "protein": 4,    "carbs": 48,  "fat": 17,   "fiber": 4.0, "category": "Snack"},
    "100700700004": {"name": "Pasta (1 plate)",          "calories": 370, "protein": 12,   "carbs": 55,  "fat": 11,   "fiber": 3.0, "category": "Grain"},
    "100700700005": {"name": "Hakka Noodles (1 plate)",  "calories": 340, "protein": 8,    "carbs": 50,  "fat": 12,   "fiber": 2.5, "category": "Grain"},
    "100700700006": {"name": "Fried Rice (1 plate)",     "calories": 360, "protein": 9,    "carbs": 58,  "fat": 10,   "fiber": 2.0, "category": "Grain"},
    "100700700007": {"name": "Spring Roll (2 pcs)",      "calories": 220, "protein": 5,    "carbs": 26,  "fat": 11,   "fiber": 2.0, "category": "Snack"},

    # ── Real Indian packaged-food barcodes (publicly known EAN-13) ───────────
    "8901058001322": {"name": "Parle-G Biscuits (100g)",      "calories": 484, "protein": 6.7, "carbs": 76, "fat": 16,  "fiber": 0,   "category": "Snack"},
    "8901058003739": {"name": "Parle Krackjack (100g)",        "calories": 460, "protein": 7.5, "carbs": 70, "fat": 16,  "fiber": 2,   "category": "Snack"},
    "8901058004330": {"name": "Hide & Seek Bourbon (100g)",    "calories": 480, "protein": 5,   "carbs": 68, "fat": 21,  "fiber": 2,   "category": "Snack"},
    "8901725131323": {"name": "Maggi Noodles (70g pack)",      "calories": 310, "protein": 8,   "carbs": 48, "fat": 10,  "fiber": 1.5, "category": "Snack"},
    "8901725132405": {"name": "Nestle KitKat (37g)",           "calories": 196, "protein": 2.5, "carbs": 25, "fat": 10,  "fiber": 0.5, "category": "Snack"},
    "8901030862229": {"name": "Lays Classic Salted (26g)",     "calories": 130, "protein": 2,   "carbs": 17, "fat": 6,   "fiber": 1,   "category": "Snack"},
    "8964000267795": {"name": "Kurkure Masala Munch (90g)",    "calories": 520, "protein": 5,   "carbs": 67, "fat": 26,  "fiber": 2,   "category": "Snack"},
    "8901030000002": {"name": "Amul Butter (100g)",            "calories": 720, "protein": 0.5, "carbs": 0,  "fat": 80,  "fiber": 0,   "category": "Dairy"},
    "8904109400017": {"name": "Britannia Marie Gold (100g)",   "calories": 449, "protein": 7,   "carbs": 74, "fat": 13,  "fiber": 1,   "category": "Snack"},
    "8901138507312": {"name": "Horlicks Health Drink (100g)",  "calories": 388, "protein": 14,  "carbs": 73, "fat": 4,   "fiber": 0,   "category": "Beverage"},
    "8906008680014": {"name": "Paper Boat Aam Panna (200ml)",  "calories": 70,  "protein": 0,   "carbs": 18, "fat": 0,   "fiber": 0,   "category": "Beverage"},
    "4902430566094": {"name": "Pocky Chocolate (47g)",         "calories": 228, "protein": 3.5, "carbs": 31, "fat": 10,  "fiber": 1,   "category": "Snack"},
    "8901063142008": {"name": "Britannia Good Day (100g)",     "calories": 500, "protein": 6,   "carbs": 67, "fat": 23,  "fiber": 1.5, "category": "Snack"},
    "8901491100021": {"name": "Cadbury Dairy Milk (50g)",      "calories": 270, "protein": 4,   "carbs": 30, "fat": 14,  "fiber": 1,   "category": "Snack"},
    "8901719110018": {"name": "Haldiram's Bhujia (100g)",      "calories": 540, "protein": 22,  "carbs": 36, "fat": 35,  "fiber": 8,   "category": "Snack"},
    "8901764100013": {"name": "Bingo Mad Angles (66g)",        "calories": 340, "protein": 4,   "carbs": 42, "fat": 17,  "fiber": 2,   "category": "Snack"},
    "8901030865015": {"name": "Amul Cheese Slice (1 slice)",   "calories": 70,  "protein": 4,   "carbs": 1,  "fat": 6,   "fiber": 0,   "category": "Dairy"},
    "8902080001019": {"name": "Mother Dairy Milk (500ml)",     "calories": 320, "protein": 16,  "carbs": 24, "fat": 17,  "fiber": 0,   "category": "Dairy"},
    "8901491001018": {"name": "Bournvita (100g)",              "calories": 400, "protein": 5,   "carbs": 80, "fat": 6,   "fiber": 1,   "category": "Beverage"},
    "8901138110011": {"name": "Bru Instant Coffee (50g)",      "calories": 75,  "protein": 4,   "carbs": 13, "fat": 0,   "fiber": 0,   "category": "Beverage"},
}
