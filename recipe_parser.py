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

    # Get ingredients as list of dicts
    raw_ingredients = scraper.ingredients() or []
    ingredients = []
    for ing in raw_ingredients:
        ingredients.append({
            'raw': ing,
            'name': _extract_ingredient_name(ing)
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


def _extract_ingredient_name(raw_ingredient):
    """
    Extract just the ingredient name from a full ingredient string.
    e.g., "2 cups all-purpose flour" -> "flour"

    This is a simple heuristic - it removes common quantity words and
    returns the main ingredient.
    """
    import re

    text = raw_ingredient.lower()

    # Remove parenthetical content
    text = re.sub(r'\([^)]*\)', '', text)

    # Remove common quantity words and measurements
    remove_patterns = [
        r'^\d+[\d\s/.-]*',  # Numbers at start (including fractions)
        r'\b(cup|cups|tablespoon|tablespoons|tbsp|teaspoon|teaspoons|tsp)\b',
        r'\b(pound|pounds|lb|lbs|ounce|ounces|oz)\b',
        r'\b(large|medium|small|whole|fresh|dried|ground|minced|chopped)\b',
        r'\b(finely|roughly|thinly|thickly|coarsely)\b',
        r'\b(sliced|diced|crushed|grated|shredded|cubed)\b',
        r'\b(to taste|for serving|optional|or more|as needed)\b',
        r'\b(about|approximately|around)\b',
        r'\b(can|cans|package|packages|bunch|bunches|head|heads)\b',
        r'\b(piece|pieces|clove|cloves|sprig|sprigs)\b',
        r',.*$',  # Remove everything after comma
    ]

    for pattern in remove_patterns:
        text = re.sub(pattern, ' ', text)

    # Clean up whitespace
    text = ' '.join(text.split())

    return text.strip() if text.strip() else raw_ingredient


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
