"""
Recipe URL parser using the recipe-scrapers library.
Supports 40+ recipe websites including Bon Appetit, NYT Cooking, etc.
"""

from urllib.parse import urlparse

try:
    from recipe_scrapers import scrape_html
    import urllib.request
    SCRAPERS_AVAILABLE = True
except ImportError:
    SCRAPERS_AVAILABLE = False


def parse_recipe_url(url):
    """
    Parse a recipe URL and extract recipe data.

    Returns:
        dict with keys: title, ingredients, instructions, source, image_url
    """
    if not SCRAPERS_AVAILABLE:
        raise ImportError(
            "recipe-scrapers is not installed. "
            "Run: pip install recipe-scrapers"
        )

    # Fetch the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        raise ValueError(f"Could not fetch URL: {e}")

    # Parse with recipe-scrapers
    try:
        scraper = scrape_html(html, org_url=url)
    except Exception as e:
        raise ValueError(f"Could not parse recipe from this URL: {e}")

    # Extract data
    title = scraper.title() or "Untitled Recipe"

    # Get ingredients as list of dicts with parsed parts
    raw_ingredients = scraper.ingredients() or []
    ingredients = []
    for ing in raw_ingredients:
        parts = parse_ingredient_parts(ing)
        ingredients.append({
            'raw': ing,
            'name': parts['name'],
            'qty': parts['qty'],
            'unit': parts['unit']
        })

    # Get instructions
    try:
        instructions = scraper.instructions() or ""
    except:
        instructions = ""

    # Get image
    try:
        image_url = scraper.image()
    except:
        image_url = None

    # Determine source from URL
    domain = urlparse(url).netloc.replace('www.', '')
    source_map = {
        'bonappetit.com': 'Bon Appetit',
        'cooking.nytimes.com': 'NYT Cooking',
        'nytimes.com': 'NYT Cooking',
        'seriouseats.com': 'Serious Eats',
        'food52.com': 'Food52',
        'allrecipes.com': 'AllRecipes',
        'epicurious.com': 'Epicurious',
        'foodnetwork.com': 'Food Network',
        'delish.com': 'Delish',
        'tasty.co': 'Tasty',
        'simplyrecipes.com': 'Simply Recipes',
        'budgetbytes.com': 'Budget Bytes',
        'thekitchn.com': 'The Kitchn',
        'smittenkitchen.com': 'Smitten Kitchen',
        'minimalistbaker.com': 'Minimalist Baker',
        'halfbakedharvest.com': 'Half Baked Harvest',
    }
    source = source_map.get(domain, domain)

    return {
        'title': title,
        'ingredients': ingredients,
        'instructions': instructions,
        'source': source,
        'image_url': image_url,
        'url': url
    }


def parse_ingredient_parts(raw_ingredient):
    """
    Parse a raw ingredient string into structured parts.

    Returns dict with: name, qty (float), unit (str), raw (original string)

    Examples:
        "3 cloves garlic, minced" -> {name: "garlic", qty: 3.0, unit: "cloves", raw: ...}
        "1 large onion, chopped"  -> {name: "onion", qty: 1.0, unit: "", raw: ...}
        "2 cups all-purpose flour" -> {name: "all-purpose flour", qty: 2.0, unit: "cups", raw: ...}
        "1½ cups chicken broth"   -> {name: "chicken broth", qty: 1.5, unit: "cups", raw: ...}
    """
    import re

    text = raw_ingredient.strip()
    raw = text
    text_lower = text.lower()

    # --- Parse quantity ---
    qty = 0.0
    # Match leading numbers, fractions, unicode fractions
    # e.g. "2", "1/2", "1 1/2", "1½", "½"
    unicode_fracs = {'½': 0.5, '⅓': 1/3, '⅔': 2/3, '¼': 0.25, '¾': 0.75,
                     '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875}

    qty_match = re.match(r'^(\d+)\s*([½⅓⅔¼¾⅛⅜⅝⅞])', text_lower)
    if qty_match:
        qty = float(qty_match.group(1)) + unicode_fracs.get(qty_match.group(2), 0)
        text_lower = text_lower[qty_match.end():].strip()
    else:
        qty_match = re.match(r'^([½⅓⅔¼¾⅛⅜⅝⅞])', text_lower)
        if qty_match:
            qty = unicode_fracs.get(qty_match.group(1), 0)
            text_lower = text_lower[qty_match.end():].strip()
        else:
            qty_match = re.match(r'^(\d+)\s+(\d+)\s*/\s*(\d+)', text_lower)
            if qty_match:
                qty = float(qty_match.group(1)) + float(qty_match.group(2)) / float(qty_match.group(3))
                text_lower = text_lower[qty_match.end():].strip()
            else:
                qty_match = re.match(r'^(\d+)\s*/\s*(\d+)', text_lower)
                if qty_match:
                    qty = float(qty_match.group(1)) / float(qty_match.group(2))
                    text_lower = text_lower[qty_match.end():].strip()
                else:
                    qty_match = re.match(r'^(\d+\.?\d*)', text_lower)
                    if qty_match:
                        qty = float(qty_match.group(1))
                        text_lower = text_lower[qty_match.end():].strip()

    # --- Parse unit ---
    unit = ''
    unit_words = [
        'cups', 'cup', 'tablespoons', 'tablespoon', 'tbsp', 'teaspoons', 'teaspoon', 'tsp',
        'pounds', 'pound', 'lbs', 'lb', 'ounces', 'ounce', 'oz',
        'cloves', 'clove', 'sprigs', 'sprig', 'bunches', 'bunch',
        'cans', 'can', 'packages', 'package', 'heads', 'head',
        'pieces', 'piece', 'stalks', 'stalk', 'slices', 'slice',
        'pints', 'pint', 'quarts', 'quart', 'gallons', 'gallon',
        'liters', 'liter', 'ml', 'g', 'kg',
    ]
    for uw in unit_words:
        pattern = r'^(' + re.escape(uw) + r')\b\.?\s*'
        m = re.match(pattern, text_lower, re.IGNORECASE)
        if m:
            unit = m.group(1).lower().rstrip('.')
            text_lower = text_lower[m.end():].strip()
            break

    # --- Strip "of" after unit ---
    text_lower = re.sub(r'^of\b\s*', '', text_lower)

    # --- Remove everything after comma ---
    text_lower = re.sub(r',.*$', '', text_lower)

    # --- Remove parenthetical content ---
    text_lower = re.sub(r'\([^)]*\)', '', text_lower)

    # --- Remove prep/size words ---
    prep_words = [
        r'\b(chopped|minced|peeled|diced|sliced|crushed|grated|shredded|cubed)\b',
        r'\b(finely|roughly|thinly|thickly|coarsely)\b',
        r'\b(to taste|for serving|optional|or more|as needed)\b',
        r'\b(about|approximately|around)\b',
        r'\b(large|medium|small|whole|fresh|dried|ground|boneless|skinless)\b',
    ]
    for p in prep_words:
        text_lower = re.sub(p, ' ', text_lower)

    # --- Strip trailing unit/count words from name ---
    # Handles "garlic clove" -> "garlic", "garlic cloves" -> "garlic"
    trailing_unit_words = [
        'cloves', 'clove', 'sprigs', 'sprig', 'bunches', 'bunch',
        'heads', 'head', 'stalks', 'stalk', 'pieces', 'piece',
        'slices', 'slice', 'leaves', 'leaf',
    ]
    for tw in trailing_unit_words:
        text_lower = re.sub(r'\b' + re.escape(tw) + r'\b', ' ', text_lower)

    # Clean up
    name = ' '.join(text_lower.split()).strip()
    if not name:
        name = raw_ingredient.lower()

    # --- Normalize simple plurals for better merging ---
    # "lemons" -> "lemon", "onions" -> "onion", "anchovies" -> "anchovy"
    no_deplural = {'hummus', 'couscous', 'asparagus', 'citrus', 'hibiscus',
                   'tahini', 'quinoa', 'molasses', 'meringues'}
    words = name.split()
    if words and words[-1] not in no_deplural:
        last = words[-1]
        if last.endswith('ies') and len(last) > 4:
            words[-1] = last[:-3] + 'y'
        elif last.endswith('es') and len(last) > 3 and last[-3] in 'shxz':
            words[-1] = last[:-2]
        elif (last.endswith('s') and not last.endswith('ss')
              and not last.endswith('us') and len(last) > 3):
            words[-1] = last[:-1]
        name = ' '.join(words)

    return {'name': name, 'qty': qty, 'unit': unit, 'raw': raw}


def _extract_ingredient_name(raw_ingredient):
    """
    Extract just the ingredient name from a full ingredient string.
    e.g., "2 cups all-purpose flour" -> "flour"

    Uses parse_ingredient_parts internally.
    """
    parts = parse_ingredient_parts(raw_ingredient)
    return parts['name']


def get_supported_sites():
    """Return a list of commonly supported recipe sites."""
    return [
        "Bon Appetit (bonappetit.com)",
        "NYT Cooking (cooking.nytimes.com)",
        "Serious Eats (seriouseats.com)",
        "Food52 (food52.com)",
        "AllRecipes (allrecipes.com)",
        "Epicurious (epicurious.com)",
        "Food Network (foodnetwork.com)",
        "Simply Recipes (simplyrecipes.com)",
        "Budget Bytes (budgetbytes.com)",
        "The Kitchn (thekitchn.com)",
        "Smitten Kitchen (smittenkitchen.com)",
        "Minimalist Baker (minimalistbaker.com)",
        "Half Baked Harvest (halfbakedharvest.com)",
        "And 30+ more sites..."
    ]
