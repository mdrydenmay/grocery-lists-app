"""
Grocery list generator - creates organized shopping lists from meal plans.
"""

from database import (
    is_staple, get_ingredient_category, get_staples,
    get_quantity_staple_by_name, decrement_staple_quantity,
    apply_name_override
)
from recipe_parser import parse_ingredient_parts


def generate_grocery_list(meal_plan_recipes, apply_decrements=True):
    """
    Generate a grocery list from a list of recipes in the meal plan.

    Args:
        meal_plan_recipes: list of recipe dicts from the meal plan
        apply_decrements: if True, decrement quantity-tracked staples in the DB

    Returns:
        dict with:
            - items: list of all items
            - by_category: items grouped by category
            - by_store: items grouped by store
            - staples_to_check: staples used in recipes (reminder to check pantry)
            - depleted_staples: quantity-tracked staples that ran out
    """
    all_ingredients = []
    staples_to_check = []
    quantity_decrements = {}

    # Collect all ingredients from all recipes
    for recipe in meal_plan_recipes:
        for ingredient in recipe.get('ingredients', []):
            raw = ingredient.get('raw', ingredient.get('name', ''))

            # Always re-parse from raw text to ensure consistent
            # name/qty/unit even for old recipes without parsed fields
            parts = parse_ingredient_parts(raw)

            # Apply name override if one exists
            override = apply_name_override(parts['name'])
            if override:
                parts['name'] = override['corrected_name']
                if override.get('corrected_qty') is not None:
                    parts['qty'] = override['corrected_qty']
                if override.get('corrected_unit') is not None:
                    parts['unit'] = override['corrected_unit']

            item = {
                'raw': raw,
                'name': parts['name'],
                'qty': parts['qty'],
                'unit': parts['unit'],
                'recipe': recipe['title'],
                'recipe_id': recipe['id'],
                'has_name_override': override is not None
            }

            # Check if it's a staple using parsed name
            name = parts['name']
            if is_staple(name):
                # Check if this staple uses quantity tracking
                qty_staple = get_quantity_staple_by_name(name)
                if qty_staple:
                    qty_key = qty_staple['id']
                    if qty_key not in quantity_decrements:
                        quantity_decrements[qty_key] = {
                            'staple': qty_staple,
                            'count': 0,
                            'items': []
                        }
                    quantity_decrements[qty_key]['count'] += 1
                    quantity_decrements[qty_key]['items'].append(item)
                else:
                    # Standard OK/LOW staple
                    staples_to_check.append(item)
            else:
                # Get category and store info
                cat_info = get_ingredient_category(name)
                item['category'] = cat_info['category']
                item['store'] = cat_info['store']
                all_ingredients.append(item)

    # Process quantity-tracked staples
    depleted_staples = []
    for staple_id, info in quantity_decrements.items():
        staple = info['staple']
        decrement_count = info['count']
        current_qty = staple['quantity']
        new_qty = max(0, current_qty - decrement_count)

        if apply_decrements:
            decrement_staple_quantity(staple_id, decrement_count)

        if new_qty <= 0:
            # Quantity depleted -- add to shopping list
            for item in info['items']:
                cat_info = get_ingredient_category(item['name'])
                item['category'] = cat_info['category']
                item['store'] = cat_info['store']
                all_ingredients.append(item)
            depleted_staples.append({
                'ingredient_name': staple['ingredient_name'],
                'was_quantity': current_qty,
                'needed': decrement_count
            })
        else:
            # Still have some -- just remind to check
            for item in info['items']:
                staples_to_check.append(item)

    # Merge duplicate ingredients
    merged = _merge_ingredients(all_ingredients)

    # Group by category
    by_category = {}
    for item in merged:
        cat = item['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    # Sort categories in a logical order
    category_order = [
        'Produce', 'Meat & Seafood', 'Dairy', 'Bread & Bakery',
        'Asian', 'Dry Goods', 'Canned & Jarred', 'Frozen',
        'Condiments', 'Oils & Vinegars', 'Seasonings', 'Baking',
        'Proteins', 'Other'
    ]

    sorted_by_category = {}
    for cat in category_order:
        if cat in by_category:
            sorted_by_category[cat] = sorted(by_category[cat], key=lambda x: x['name'])
    for cat in by_category:
        if cat not in sorted_by_category:
            sorted_by_category[cat] = sorted(by_category[cat], key=lambda x: x['name'])

    # Group by store
    by_store = {}
    for item in merged:
        store = item['store']
        if store not in by_store:
            by_store[store] = []
        by_store[store].append(item)

    # Sort stores
    store_order = ["Trader Joe's", "Whole Foods", "HMart", "Other"]
    sorted_by_store = {}
    for store in store_order:
        if store in by_store:
            sorted_by_store[store] = sorted(by_store[store], key=lambda x: x['category'])
    for store in by_store:
        if store not in sorted_by_store:
            sorted_by_store[store] = sorted(by_store[store], key=lambda x: x['category'])

    # Check which staples are marked as low
    low_staples = _get_low_staples()

    return {
        'items': merged,
        'by_category': sorted_by_category,
        'by_store': sorted_by_store,
        'staples_to_check': staples_to_check,
        'low_staples': low_staples,
        'depleted_staples': depleted_staples
    }


def _merge_ingredients(ingredients):
    """
    Merge duplicate ingredients with quantity-aware combining.
    Groups by normalized name, sums quantities when units match,
    and builds a display string for each merged item.
    """
    merged = {}

    for item in ingredients:
        key = item['name'].lower().strip()

        if key in merged:
            existing = merged[key]
            if item['recipe'] not in existing['recipes']:
                existing['recipes'].append(item['recipe'])
                existing['raw_variants'].append(item['raw'])
            # Accumulate quantities
            existing['qty_entries'].append({
                'qty': item.get('qty', 0) or 0,
                'unit': (item.get('unit', '') or '').lower().strip()
            })
            if item.get('has_name_override'):
                existing['has_name_override'] = True
        else:
            merged[key] = {
                'name': item['name'],
                'raw': item['raw'],
                'raw_variants': [item['raw']],
                'recipes': [item['recipe']],
                'category': item['category'],
                'store': item['store'],
                'has_name_override': item.get('has_name_override', False),
                'qty_entries': [{
                    'qty': item.get('qty', 0) or 0,
                    'unit': (item.get('unit', '') or '').lower().strip()
                }]
            }

    # Build display text for each merged item
    result = []
    for item in merged.values():
        item['display'] = _build_display(item['name'], item['qty_entries'])
        del item['qty_entries']
        result.append(item)

    return result


def _build_display(name, qty_entries):
    """Build a human-readable display string from merged quantity entries."""
    # Group quantities by unit
    by_unit = {}
    for entry in qty_entries:
        u = entry['unit']
        if u not in by_unit:
            by_unit[u] = 0.0
        by_unit[u] += entry['qty']

    # Remove zero-quantity no-unit entries if we have real quantities
    if '' in by_unit and by_unit[''] == 0.0 and len(by_unit) > 1:
        del by_unit['']

    # If all quantities are zero (no parsed qty info), just show the name
    if all(q == 0.0 for q in by_unit.values()):
        if len(qty_entries) > 1:
            return f"{name} (x{len(qty_entries)})"
        return name

    parts = []
    for unit, total in by_unit.items():
        # Format the number nicely (no trailing .0)
        if total == int(total):
            qty_str = str(int(total))
        else:
            qty_str = f"{total:.1f}".rstrip('0').rstrip('.')
        if unit:
            parts.append(f"{qty_str} {unit}")
        else:
            parts.append(qty_str)

    if len(parts) == 1:
        return f"{parts[0]} {name}"
    else:
        return f"{name} ({' + '.join(parts)})"


def _get_low_staples():
    """Get staples that are marked as running low."""
    staples = get_staples()
    return [s for s in staples if s.get('is_low')]


def format_for_clipboard(grocery_data, group_by='category'):
    """
    Format the grocery list for clipboard (to paste into Google Keep).

    Args:
        grocery_data: output from generate_grocery_list
        group_by: 'category' or 'store'
    """
    lines = []

    if group_by == 'store':
        groups = grocery_data['by_store']
    else:
        groups = grocery_data['by_category']

    for group_name, items in groups.items():
        lines.append(f"\n{group_name.upper()}")
        lines.append("-" * len(group_name))
        for item in items:
            display_text = item.get('display', item['name'])
            lines.append(f"[ ] {display_text}")

    # Add staples reminder
    if grocery_data.get('staples_to_check'):
        lines.append("\n\nCHECK PANTRY (staples)")
        lines.append("-" * 20)
        seen = set()
        for item in grocery_data['staples_to_check']:
            if item['name'].lower() not in seen:
                seen.add(item['name'].lower())
                lines.append(f"[ ] {item['raw']}")

    # Add low staples reminder
    if grocery_data.get('low_staples'):
        lines.append("\n\nRUNNING LOW (restock)")
        lines.append("-" * 20)
        for item in grocery_data['low_staples']:
            lines.append(f"[ ] {item['ingredient_name']}")

    return '\n'.join(lines)
