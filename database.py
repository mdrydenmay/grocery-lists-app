import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "data" / "grocery.db"

def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema and seed data."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Recipes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            source TEXT,
            image_url TEXT,
            ingredients TEXT NOT NULL,  -- JSON array
            instructions TEXT,
            rating INTEGER DEFAULT 0,
            notes TEXT,
            tags TEXT,  -- JSON array
            date_added TEXT NOT NULL,
            last_made TEXT
        )
    ''')

    # Pantry staples table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pantry_staples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient_name TEXT NOT NULL UNIQUE,
            category TEXT,
            is_low INTEGER DEFAULT 0
        )
    ''')

    # Ingredient categories (for auto-categorization)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            store_preference TEXT
        )
    ''')

    # Meal plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            recipe_id INTEGER NOT NULL,
            day_of_week INTEGER,  -- 0=Sunday, 1=Monday, etc.
            FOREIGN KEY (recipe_id) REFERENCES recipes(id),
            UNIQUE(week_start, recipe_id)
        )
    ''')

    # Grocery lists table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grocery_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL UNIQUE,
            items TEXT NOT NULL,  -- JSON array of items
            created_at TEXT NOT NULL
        )
    ''')

    # Ingredient store overrides (manual store assignments)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_store_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient_pattern TEXT NOT NULL UNIQUE,
            store TEXT NOT NULL
        )
    ''')

    # Ingredient name overrides (manual name corrections)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_name_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL UNIQUE,
            corrected_name TEXT NOT NULL,
            corrected_qty REAL,
            corrected_unit TEXT
        )
    ''')

    conn.commit()

    # Meal pairings table (for tracking main+side combos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_pairings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_recipe_id INTEGER NOT NULL,
            side_recipe_id INTEGER NOT NULL,
            times_paired INTEGER DEFAULT 1,
            last_paired TEXT NOT NULL,
            avg_combined_rating REAL DEFAULT 0,
            FOREIGN KEY (main_recipe_id) REFERENCES recipes(id),
            FOREIGN KEY (side_recipe_id) REFERENCES recipes(id),
            UNIQUE(main_recipe_id, side_recipe_id)
        )
    ''')
    conn.commit()

    # Migrate: add quantity tracking columns if they don't exist
    cursor.execute("PRAGMA table_info(pantry_staples)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'track_quantity' not in columns:
        cursor.execute("ALTER TABLE pantry_staples ADD COLUMN track_quantity INTEGER DEFAULT 0")
    if 'quantity' not in columns:
        cursor.execute("ALTER TABLE pantry_staples ADD COLUMN quantity INTEGER DEFAULT 0")

    # Migrate: add is_favorite column to recipes if it doesn't exist
    cursor.execute("PRAGMA table_info(recipes)")
    recipe_columns = [col[1] for col in cursor.fetchall()]
    if 'is_favorite' not in recipe_columns:
        cursor.execute("ALTER TABLE recipes ADD COLUMN is_favorite INTEGER DEFAULT 0")
    conn.commit()

    # Migrate: add missing ingredient category patterns
    _add_missing_categories(conn)

    # Seed with initial data if tables are empty
    _seed_staples(conn)
    _seed_ingredient_categories(conn)

    conn.close()

def _add_missing_categories(conn):
    """Add ingredient category patterns that may be missing from older databases."""
    cursor = conn.cursor()
    extra_patterns = [
        # Produce items commonly missing
        ("fennel", "Produce", "Trader Joe's"),
        ("shallot", "Produce", "Trader Joe's"),
        ("arugula", "Produce", "Trader Joe's"),
        ("endive", "Produce", "Trader Joe's"),
        ("brussels sprout", "Produce", "Trader Joe's"),
        ("cabbage", "Produce", "Trader Joe's"),
        ("squash", "Produce", "Trader Joe's"),
        ("pumpkin", "Produce", "Trader Joe's"),
        ("persimmon", "Produce", "Trader Joe's"),
        ("pear", "Produce", "Trader Joe's"),
        ("peach", "Produce", "Trader Joe's"),
        ("plum", "Produce", "Trader Joe's"),
        ("grape", "Produce", "Trader Joe's"),
        ("mango", "Produce", "Trader Joe's"),
        ("pineapple", "Produce", "Trader Joe's"),
        ("asparagus", "Produce", "Trader Joe's"),
        ("corn", "Produce", "Trader Joe's"),
        ("pea", "Produce", "Trader Joe's"),
        ("snap pea", "Produce", "Trader Joe's"),
        ("snow pea", "Produce", "Trader Joe's"),
        ("green bean", "Produce", "Trader Joe's"),
        ("radish", "Produce", "Trader Joe's"),
        ("beet", "Produce", "Trader Joe's"),
        ("turnip", "Produce", "Trader Joe's"),
        ("sweet potato", "Produce", "Trader Joe's"),
        ("eggplant", "Produce", "Trader Joe's"),
        ("artichoke", "Produce", "Trader Joe's"),
        ("leek", "Produce", "Trader Joe's"),
        ("chili", "Produce", "Trader Joe's"),
        ("jalapeno", "Produce", "Trader Joe's"),
        ("serrano", "Produce", "Trader Joe's"),
        ("turmeric", "Seasonings", "Trader Joe's"),
        ("dill", "Produce", "Trader Joe's"),
        ("rosemary", "Produce", "Trader Joe's"),
        ("sage", "Produce", "Trader Joe's"),
        ("thyme", "Produce", "Trader Joe's"),
        # Dried fruit / pantry produce
        ("apricot", "Produce", "Trader Joe's"),
        ("olive", "Produce", "Trader Joe's"),
        # Nuts & snacks
        ("walnut", "Dry Goods", "Trader Joe's"),
        ("almond", "Dry Goods", "Trader Joe's"),
        ("pecan", "Dry Goods", "Trader Joe's"),
        ("cashew", "Dry Goods", "Trader Joe's"),
        ("pistachio", "Dry Goods", "Trader Joe's"),
        ("pine nut", "Dry Goods", "Trader Joe's"),
        ("breadcrumb", "Dry Goods", "Trader Joe's"),
        ("lasagna", "Dry Goods", "Trader Joe's"),
        ("noodle", "Dry Goods", "Trader Joe's"),
        ("yeast", "Baking", "Trader Joe's"),
        # Seafood
        ("anchovy", "Meat & Seafood", "Whole Foods"),
        ("mackerel", "Meat & Seafood", "Whole Foods"),
        ("trout", "Meat & Seafood", "Whole Foods"),
        # Asian produce
        ("makrut", "Produce", "HMart"),
        ("bird's eye", "Produce", "HMart"),
        # Dairy additions
        ("labneh", "Dairy", "Whole Foods"),
        ("pecorino", "Dairy", "Trader Joe's"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO ingredient_categories (pattern, category, store_preference) VALUES (?, ?, ?)",
        extra_patterns
    )
    conn.commit()

def _seed_staples(conn):
    """Seed pantry staples if table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pantry_staples")
    if cursor.fetchone()[0] > 0:
        return

    staples = [
        # Basics
        ("salt", "Seasonings"),
        ("pepper", "Seasonings"),
        ("black pepper", "Seasonings"),
        ("olive oil", "Oils & Vinegars"),
        ("vegetable oil", "Oils & Vinegars"),
        ("butter", "Dairy"),
        # Baking
        ("flour", "Baking"),
        ("all-purpose flour", "Baking"),
        ("sugar", "Baking"),
        ("granulated sugar", "Baking"),
        ("brown sugar", "Baking"),
        ("baking powder", "Baking"),
        ("baking soda", "Baking"),
        # Asian staples
        ("soy sauce", "Condiments"),
        ("fish sauce", "Condiments"),
        ("rice vinegar", "Oils & Vinegars"),
        ("sesame oil", "Oils & Vinegars"),
        # Vinegars
        ("balsamic vinegar", "Oils & Vinegars"),
        ("white vinegar", "Oils & Vinegars"),
        ("red wine vinegar", "Oils & Vinegars"),
        # Spices
        ("garlic powder", "Seasonings"),
        ("onion powder", "Seasonings"),
        ("paprika", "Seasonings"),
        ("cumin", "Seasonings"),
        ("oregano", "Seasonings"),
        ("thyme", "Seasonings"),
        ("bay leaves", "Seasonings"),
        ("cinnamon", "Seasonings"),
        ("nutmeg", "Seasonings"),
        ("red pepper flakes", "Seasonings"),
        ("cayenne", "Seasonings"),
        # Grains
        ("rice", "Dry Goods"),
        ("white rice", "Dry Goods"),
        ("pasta", "Dry Goods"),
        ("dried beans", "Dry Goods"),
        ("lentils", "Dry Goods"),
        # Stock
        ("chicken stock", "Canned & Jarred"),
        ("chicken broth", "Canned & Jarred"),
        ("vegetable stock", "Canned & Jarred"),
        ("vegetable broth", "Canned & Jarred"),
        ("beef stock", "Canned & Jarred"),
        ("beef broth", "Canned & Jarred"),
        # Other common staples
        ("honey", "Condiments"),
        ("maple syrup", "Condiments"),
        ("mustard", "Condiments"),
        ("dijon mustard", "Condiments"),
        ("mayonnaise", "Condiments"),
        ("ketchup", "Condiments"),
        ("hot sauce", "Condiments"),
        ("worcestershire sauce", "Condiments"),
        ("tomato paste", "Canned & Jarred"),
        ("canned tomatoes", "Canned & Jarred"),
        ("coconut milk", "Canned & Jarred"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO pantry_staples (ingredient_name, category) VALUES (?, ?)",
        staples
    )
    conn.commit()

def _seed_ingredient_categories(conn):
    """Seed ingredient category patterns if table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ingredient_categories")
    if cursor.fetchone()[0] > 0:
        return

    categories = [
        # Produce
        ("tomato", "Produce", "Trader Joe's"),
        ("onion", "Produce", "Trader Joe's"),
        ("garlic", "Produce", "Trader Joe's"),
        ("potato", "Produce", "Trader Joe's"),
        ("carrot", "Produce", "Trader Joe's"),
        ("celery", "Produce", "Trader Joe's"),
        ("lettuce", "Produce", "Trader Joe's"),
        ("spinach", "Produce", "Trader Joe's"),
        ("kale", "Produce", "Trader Joe's"),
        ("broccoli", "Produce", "Trader Joe's"),
        ("cauliflower", "Produce", "Trader Joe's"),
        ("zucchini", "Produce", "Trader Joe's"),
        ("pepper", "Produce", "Trader Joe's"),
        ("bell pepper", "Produce", "Trader Joe's"),
        ("cucumber", "Produce", "Trader Joe's"),
        ("mushroom", "Produce", "Trader Joe's"),
        ("avocado", "Produce", "Trader Joe's"),
        ("lemon", "Produce", "Trader Joe's"),
        ("lime", "Produce", "Trader Joe's"),
        ("orange", "Produce", "Trader Joe's"),
        ("apple", "Produce", "Trader Joe's"),
        ("banana", "Produce", "Trader Joe's"),
        ("berry", "Produce", "Trader Joe's"),
        ("strawberry", "Produce", "Trader Joe's"),
        ("blueberry", "Produce", "Trader Joe's"),
        ("ginger", "Produce", "Trader Joe's"),
        ("cilantro", "Produce", "Trader Joe's"),
        ("parsley", "Produce", "Trader Joe's"),
        ("basil", "Produce", "Trader Joe's"),
        ("mint", "Produce", "Trader Joe's"),
        ("scallion", "Produce", "Trader Joe's"),
        ("green onion", "Produce", "Trader Joe's"),
        # Asian produce - HMart
        ("bok choy", "Produce", "HMart"),
        ("napa cabbage", "Produce", "HMart"),
        ("daikon", "Produce", "HMart"),
        ("bean sprout", "Produce", "HMart"),
        ("enoki", "Produce", "HMart"),
        ("shiitake", "Produce", "HMart"),
        ("lemongrass", "Produce", "HMart"),
        ("galangal", "Produce", "HMart"),
        ("thai basil", "Produce", "HMart"),
        ("shiso", "Produce", "HMart"),
        # Meat
        ("chicken", "Meat & Seafood", "Trader Joe's"),
        ("beef", "Meat & Seafood", "Whole Foods"),
        ("pork", "Meat & Seafood", "Trader Joe's"),
        ("ground beef", "Meat & Seafood", "Trader Joe's"),
        ("ground turkey", "Meat & Seafood", "Trader Joe's"),
        ("bacon", "Meat & Seafood", "Trader Joe's"),
        ("sausage", "Meat & Seafood", "Trader Joe's"),
        ("lamb", "Meat & Seafood", "Whole Foods"),
        ("steak", "Meat & Seafood", "Whole Foods"),
        # Seafood
        ("salmon", "Meat & Seafood", "Whole Foods"),
        ("shrimp", "Meat & Seafood", "Whole Foods"),
        ("fish", "Meat & Seafood", "Whole Foods"),
        ("tuna", "Meat & Seafood", "Whole Foods"),
        ("cod", "Meat & Seafood", "Whole Foods"),
        ("scallop", "Meat & Seafood", "Whole Foods"),
        ("crab", "Meat & Seafood", "HMart"),
        ("lobster", "Meat & Seafood", "Whole Foods"),
        # Dairy
        ("milk", "Dairy", "Trader Joe's"),
        ("cream", "Dairy", "Trader Joe's"),
        ("heavy cream", "Dairy", "Trader Joe's"),
        ("half and half", "Dairy", "Trader Joe's"),
        ("cheese", "Dairy", "Trader Joe's"),
        ("parmesan", "Dairy", "Trader Joe's"),
        ("mozzarella", "Dairy", "Trader Joe's"),
        ("cheddar", "Dairy", "Trader Joe's"),
        ("feta", "Dairy", "Trader Joe's"),
        ("yogurt", "Dairy", "Trader Joe's"),
        ("sour cream", "Dairy", "Trader Joe's"),
        ("egg", "Dairy", "Trader Joe's"),
        # Asian ingredients - HMart
        ("tofu", "Proteins", "HMart"),
        ("gochujang", "Asian", "HMart"),
        ("gochugaru", "Asian", "HMart"),
        ("miso", "Asian", "HMart"),
        ("mirin", "Asian", "HMart"),
        ("sake", "Asian", "HMart"),
        ("dashi", "Asian", "HMart"),
        ("nori", "Asian", "HMart"),
        ("rice noodle", "Asian", "HMart"),
        ("udon", "Asian", "HMart"),
        ("soba", "Asian", "HMart"),
        ("rice paper", "Asian", "HMart"),
        ("kimchi", "Asian", "HMart"),
        ("sambal", "Asian", "HMart"),
        ("sriracha", "Asian", "HMart"),
        ("hoisin", "Asian", "HMart"),
        ("oyster sauce", "Asian", "HMart"),
        ("tamarind", "Asian", "HMart"),
        ("curry paste", "Asian", "HMart"),
        ("coconut cream", "Asian", "HMart"),
        # Bread & Bakery
        ("bread", "Bread & Bakery", "Trader Joe's"),
        ("tortilla", "Bread & Bakery", "Trader Joe's"),
        ("pita", "Bread & Bakery", "Trader Joe's"),
        ("naan", "Bread & Bakery", "Trader Joe's"),
        # Frozen
        ("frozen", "Frozen", "Trader Joe's"),
        # Canned
        ("canned", "Canned & Jarred", "Trader Joe's"),
        ("beans", "Canned & Jarred", "Trader Joe's"),
        ("chickpea", "Canned & Jarred", "Trader Joe's"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO ingredient_categories (pattern, category, store_preference) VALUES (?, ?, ?)",
        categories
    )
    conn.commit()

# Recipe CRUD operations

def get_recipe_by_url(url):
    """Check if a recipe with this URL already exists. Returns the recipe or None."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE url = ?", (url,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _row_to_recipe(row)
    return None

def add_recipe(title, ingredients, instructions="", url=None, source=None,
               image_url=None, tags=None):
    """Add a new recipe to the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recipes (title, url, source, image_url, ingredients,
                           instructions, tags, date_added)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        title, url, source, image_url,
        json.dumps(ingredients),
        instructions,
        json.dumps(tags or []),
        datetime.now().isoformat()
    ))
    recipe_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recipe_id

def get_recipe(recipe_id):
    """Get a single recipe by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _row_to_recipe(row)
    return None

def get_all_recipes(search=None, tag=None, favorites_only=False):
    """Get all recipes, optionally filtered by search term, tag, or favorites."""
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM recipes WHERE 1=1"
    params = []

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    if favorites_only:
        query += " AND is_favorite = 1"

    query += " ORDER BY date_added DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    recipes = [_row_to_recipe(row) for row in rows]

    if tag:
        recipes = [r for r in recipes if tag in r.get('tags', [])]

    return recipes

def update_recipe(recipe_id, **kwargs):
    """Update a recipe's fields."""
    conn = get_db()
    cursor = conn.cursor()

    allowed_fields = ['title', 'url', 'source', 'image_url', 'ingredients',
                      'instructions', 'rating', 'notes', 'tags', 'last_made',
                      'is_favorite']

    updates = []
    params = []
    for field, value in kwargs.items():
        if field in allowed_fields:
            if field in ['ingredients', 'tags']:
                value = json.dumps(value)
            updates.append(f"{field} = ?")
            params.append(value)

    if updates:
        params.append(recipe_id)
        query = f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()

    conn.close()

def delete_recipe(recipe_id):
    """Delete a recipe."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    cursor.execute("DELETE FROM meal_plans WHERE recipe_id = ?", (recipe_id,))
    cursor.execute("DELETE FROM meal_pairings WHERE main_recipe_id = ? OR side_recipe_id = ?",
                   (recipe_id, recipe_id))
    conn.commit()
    conn.close()

def _row_to_recipe(row):
    """Convert a database row to a recipe dictionary."""
    return {
        'id': row['id'],
        'title': row['title'],
        'url': row['url'],
        'source': row['source'],
        'image_url': row['image_url'],
        'ingredients': json.loads(row['ingredients']),
        'instructions': row['instructions'],
        'rating': row['rating'],
        'notes': row['notes'],
        'tags': json.loads(row['tags']) if row['tags'] else [],
        'date_added': row['date_added'],
        'last_made': row['last_made'],
        'is_favorite': bool(row['is_favorite']) if row['is_favorite'] else False
    }

def toggle_favorite(recipe_id):
    """Toggle the is_favorite status of a recipe."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recipes SET is_favorite = NOT is_favorite WHERE id = ?",
        (recipe_id,)
    )
    conn.commit()
    conn.close()

# Meal pairings

def record_pairings_from_meal_plan(week_start=None):
    """Record all main+side pairings from a week's meal plan."""
    plan = get_meal_plan(week_start)
    if not plan:
        return

    mains = [r for r in plan if 'main' in r.get('tags', [])]
    sides = [r for r in plan if 'side' in r.get('tags', [])]

    if not mains or not sides:
        return

    conn = get_db()
    cursor = conn.cursor()
    today = date.today().isoformat()

    for main in mains:
        for side in sides:
            avg_rating = ((main.get('rating', 0) or 0) + (side.get('rating', 0) or 0)) / 2.0
            cursor.execute('''
                INSERT INTO meal_pairings (main_recipe_id, side_recipe_id, times_paired, last_paired, avg_combined_rating)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(main_recipe_id, side_recipe_id)
                DO UPDATE SET
                    times_paired = times_paired + 1,
                    last_paired = ?,
                    avg_combined_rating = (avg_combined_rating * (times_paired - 1) + ?) / times_paired
            ''', (main['id'], side['id'], today, avg_rating, today, avg_rating))

    conn.commit()
    conn.close()

def get_past_pairings(main_id=None, side_id=None, min_times=1):
    """Get pairing history, optionally filtered by a specific main or side."""
    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT mp.*
        FROM meal_pairings mp
        WHERE mp.times_paired >= ?
    '''
    params = [min_times]

    if main_id:
        query += " AND mp.main_recipe_id = ?"
        params.append(main_id)
    if side_id:
        query += " AND mp.side_recipe_id = ?"
        params.append(side_id)

    query += " ORDER BY mp.times_paired DESC, mp.avg_combined_rating DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def suggest_meals(num_meals=5, constraints=None, exclude_ids=None):
    """
    Suggest main+side pairings based on ratings, favorites, and past pairings.

    constraints: dict like {"vegetarian": 2, "chicken": 1}
    exclude_ids: set of recipe IDs to exclude
    """
    import random

    all_recipes = get_all_recipes()
    mains = [r for r in all_recipes if 'main' in r.get('tags', [])]
    sides = [r for r in all_recipes if 'side' in r.get('tags', [])]

    if not mains or not sides:
        return []

    exclude_ids = exclude_ids or set()
    constraints = constraints or {}
    pairings = get_past_pairings()

    # Build pairing lookup
    pairing_lookup = {}
    for p in pairings:
        pairing_lookup[(p['main_recipe_id'], p['side_recipe_id'])] = p

    def score_recipe(recipe):
        s = (recipe.get('rating', 0) or 0) * 2
        if recipe.get('is_favorite'):
            s += 5
        return s

    def score_pair(main, side):
        s = score_recipe(main) + score_recipe(side)
        pair_data = pairing_lookup.get((main['id'], side['id']))
        if pair_data:
            s += pair_data['times_paired'] * 2
            s += pair_data['avg_combined_rating'] * 1.5
        return s

    suggestions = []
    used_main_ids = set(exclude_ids)
    used_side_ids = set(exclude_ids)

    def find_best_pair(candidate_mains, candidate_sides):
        best_pair = None
        best_score = -1
        for m in candidate_mains:
            for s in candidate_sides:
                sc = score_pair(m, s) + random.uniform(0, 3)
                if sc > best_score:
                    best_score = sc
                    best_pair = (m, s)
        return best_pair, best_score

    # First pass: fill constrained slots
    for tag, count in constraints.items():
        tagged_mains = [m for m in mains
                        if tag in m.get('tags', []) and m['id'] not in used_main_ids]
        for _ in range(count):
            if not tagged_mains:
                break
            available_sides = [s for s in sides if s['id'] not in used_side_ids]
            if not available_sides:
                available_sides = sides

            best_pair, best_score = find_best_pair(tagged_mains, available_sides)
            if best_pair:
                pair_data = pairing_lookup.get((best_pair[0]['id'], best_pair[1]['id']))
                suggestions.append({
                    'main': best_pair[0],
                    'side': best_pair[1],
                    'score': best_score,
                    'past_pairing': pair_data is not None,
                    'times_paired': pair_data['times_paired'] if pair_data else 0
                })
                used_main_ids.add(best_pair[0]['id'])
                used_side_ids.add(best_pair[1]['id'])
                tagged_mains = [m for m in tagged_mains if m['id'] not in used_main_ids]

    # Second pass: fill remaining unconstrained slots
    remaining = num_meals - len(suggestions)
    for _ in range(remaining):
        available_mains = [m for m in mains if m['id'] not in used_main_ids]
        if not available_mains:
            available_mains = [m for m in mains if m['id'] not in exclude_ids]
        available_sides = [s for s in sides if s['id'] not in used_side_ids]
        if not available_sides:
            available_sides = sides

        best_pair, best_score = find_best_pair(available_mains, available_sides)
        if best_pair:
            pair_data = pairing_lookup.get((best_pair[0]['id'], best_pair[1]['id']))
            suggestions.append({
                'main': best_pair[0],
                'side': best_pair[1],
                'score': best_score,
                'past_pairing': pair_data is not None,
                'times_paired': pair_data['times_paired'] if pair_data else 0
            })
            used_main_ids.add(best_pair[0]['id'])
            used_side_ids.add(best_pair[1]['id'])

    return suggestions

# Pantry operations

def get_staples():
    """Get all pantry staples."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pantry_staples ORDER BY category, ingredient_name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def is_staple(ingredient_name):
    """Check if an ingredient is a pantry staple using word-boundary matching."""
    import re
    conn = get_db()
    cursor = conn.cursor()
    normalized = ingredient_name.lower().strip()

    # Exact match first
    cursor.execute(
        "SELECT 1 FROM pantry_staples WHERE LOWER(ingredient_name) = ?",
        (normalized,)
    )
    if cursor.fetchone():
        conn.close()
        return True

    # Word-boundary match: check if any staple name appears as whole words
    cursor.execute("SELECT ingredient_name FROM pantry_staples")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        staple = row['ingredient_name'].lower()
        # Use word boundaries so "butter" doesn't match "butternut"
        if re.search(r'\b' + re.escape(staple) + r'\b', normalized):
            return True
    return False

def add_staple(ingredient_name, category="Other"):
    """Add a new pantry staple."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO pantry_staples (ingredient_name, category) VALUES (?, ?)",
        (ingredient_name.lower(), category)
    )
    conn.commit()
    conn.close()

def toggle_staple_low(staple_id):
    """Toggle the is_low status of a staple."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pantry_staples SET is_low = NOT is_low WHERE id = ?",
        (staple_id,)
    )
    conn.commit()
    conn.close()

def delete_staple(staple_id):
    """Delete a pantry staple."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pantry_staples WHERE id = ?", (staple_id,))
    conn.commit()
    conn.close()

def enable_quantity_tracking(staple_id, initial_quantity=0):
    """Enable quantity tracking for a staple, replacing OK/LOW mode."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pantry_staples SET track_quantity = 1, quantity = ?, is_low = 0 WHERE id = ?",
        (max(0, initial_quantity), staple_id)
    )
    conn.commit()
    conn.close()

def disable_quantity_tracking(staple_id):
    """Disable quantity tracking, reverting to OK/LOW mode."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pantry_staples SET track_quantity = 0, quantity = 0 WHERE id = ?",
        (staple_id,)
    )
    conn.commit()
    conn.close()

def set_staple_quantity(staple_id, quantity):
    """Set the quantity for a quantity-tracked staple."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pantry_staples SET quantity = ? WHERE id = ? AND track_quantity = 1",
        (max(0, quantity), staple_id)
    )
    conn.commit()
    conn.close()

def get_quantity_staple_by_name(ingredient_name):
    """If ingredient matches a quantity-tracked staple, return it. Otherwise None."""
    import re
    conn = get_db()
    cursor = conn.cursor()
    normalized = ingredient_name.lower().strip()

    # Exact match first
    cursor.execute(
        "SELECT * FROM pantry_staples WHERE track_quantity = 1 AND LOWER(ingredient_name) = ?",
        (normalized,)
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)

    # Word-boundary match
    cursor.execute("SELECT * FROM pantry_staples WHERE track_quantity = 1")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        staple = row['ingredient_name'].lower()
        if re.search(r'\b' + re.escape(staple) + r'\b', normalized):
            return dict(row)
    return None

def decrement_staple_quantity(staple_id, amount=1):
    """Decrement a staple's quantity, flooring at 0."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pantry_staples SET quantity = MAX(0, quantity - ?) WHERE id = ? AND track_quantity = 1",
        (amount, staple_id)
    )
    conn.commit()
    conn.close()

def has_grocery_list_been_generated(week_start):
    """Check if a grocery list has already been generated for this week."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM grocery_lists WHERE week_start = ?", (week_start,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def mark_grocery_list_generated(week_start):
    """Record that a grocery list was generated for this week."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO grocery_lists (week_start, items, created_at) VALUES (?, ?, ?)",
        (week_start, '[]', datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# Store overrides

def set_store_override(ingredient_name, store):
    """Upsert a manual store override for an ingredient pattern."""
    conn = get_db()
    cursor = conn.cursor()
    pattern = ingredient_name.lower().strip()
    cursor.execute(
        """INSERT INTO ingredient_store_overrides (ingredient_pattern, store)
           VALUES (?, ?)
           ON CONFLICT(ingredient_pattern)
           DO UPDATE SET store = ?""",
        (pattern, store, store)
    )
    conn.commit()
    conn.close()

def get_store_overrides():
    """Return all manual store overrides."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredient_store_overrides ORDER BY ingredient_pattern")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_store_override(override_id):
    """Remove a store override by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ingredient_store_overrides WHERE id = ?", (override_id,))
    conn.commit()
    conn.close()

# Name overrides

def set_name_override(original_name, corrected_name, corrected_qty=None, corrected_unit=None):
    """Upsert a name correction override for an ingredient."""
    conn = get_db()
    cursor = conn.cursor()
    key = original_name.lower().strip()
    cursor.execute(
        """INSERT INTO ingredient_name_overrides (original_name, corrected_name, corrected_qty, corrected_unit)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(original_name)
           DO UPDATE SET corrected_name = ?, corrected_qty = ?, corrected_unit = ?""",
        (key, corrected_name.strip(), corrected_qty, corrected_unit or None,
         corrected_name.strip(), corrected_qty, corrected_unit or None)
    )
    conn.commit()
    conn.close()

def get_name_overrides():
    """Return all ingredient name overrides."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredient_name_overrides ORDER BY original_name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_name_override(override_id):
    """Remove a name override by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ingredient_name_overrides WHERE id = ?", (override_id,))
    conn.commit()
    conn.close()

def apply_name_override(parsed_name):
    """Look up a name override. Returns dict with corrected fields, or None."""
    conn = get_db()
    cursor = conn.cursor()
    normalized = parsed_name.lower().strip()
    cursor.execute(
        "SELECT corrected_name, corrected_qty, corrected_unit FROM ingredient_name_overrides WHERE original_name = ?",
        (normalized,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'corrected_name': row['corrected_name'],
            'corrected_qty': row['corrected_qty'],
            'corrected_unit': row['corrected_unit']
        }
    return None

# Ingredient categorization

def get_ingredient_category(ingredient_name):
    """Get the category and store preference for an ingredient.
    Checks manual store overrides first, then falls back to auto-detection."""
    conn = get_db()
    cursor = conn.cursor()
    normalized = ingredient_name.lower()

    # Check manual overrides first
    cursor.execute(
        "SELECT store FROM ingredient_store_overrides WHERE ? LIKE '%' || ingredient_pattern || '%' ORDER BY LENGTH(ingredient_pattern) DESC LIMIT 1",
        (normalized,)
    )
    override_row = cursor.fetchone()

    # Get category from ingredient_categories (always needed)
    cursor.execute(
        "SELECT category, store_preference FROM ingredient_categories WHERE ? LIKE '%' || pattern || '%' ORDER BY LENGTH(pattern) DESC LIMIT 1",
        (normalized,)
    )
    cat_row = cursor.fetchone()
    conn.close()

    category = cat_row['category'] if cat_row else 'Other'
    if override_row:
        return {'category': category, 'store': override_row['store']}
    if cat_row:
        return {'category': category, 'store': cat_row['store_preference']}
    return {'category': 'Other', 'store': "Trader Joe's"}

# Meal plan operations

def get_week_start(for_date=None):
    """Get the Sunday that starts the week containing the given date."""
    if for_date is None:
        for_date = date.today()
    days_since_sunday = for_date.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    from datetime import timedelta
    sunday = for_date - timedelta(days=days_since_sunday)
    return sunday.isoformat()

def add_to_meal_plan(recipe_id, week_start=None, day_of_week=None):
    """Add a recipe to the meal plan."""
    if week_start is None:
        week_start = get_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO meal_plans (week_start, recipe_id, day_of_week) VALUES (?, ?, ?)",
        (week_start, recipe_id, day_of_week)
    )
    conn.commit()
    conn.close()

def remove_from_meal_plan(recipe_id, week_start=None):
    """Remove a recipe from the meal plan."""
    if week_start is None:
        week_start = get_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM meal_plans WHERE week_start = ? AND recipe_id = ?",
        (week_start, recipe_id)
    )
    conn.commit()
    conn.close()

def get_meal_plan(week_start=None):
    """Get the meal plan for a week."""
    if week_start is None:
        week_start = get_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, mp.day_of_week
        FROM meal_plans mp
        JOIN recipes r ON mp.recipe_id = r.id
        WHERE mp.week_start = ?
        ORDER BY mp.day_of_week
    ''', (week_start,))
    rows = cursor.fetchall()
    conn.close()

    recipes = []
    for row in rows:
        recipe = _row_to_recipe(row)
        recipe['day_of_week'] = row['day_of_week']
        recipes.append(recipe)
    return recipes

def clear_meal_plan(week_start=None):
    """Clear all recipes from a week's meal plan."""
    if week_start is None:
        week_start = get_week_start()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meal_plans WHERE week_start = ?", (week_start,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
