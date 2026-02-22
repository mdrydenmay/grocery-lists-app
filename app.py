#!/usr/bin/env python3
"""
Grocery Lists App - Meal planning and grocery list management.
Run with: python app.py
Then open http://localhost:5000 in your browser.
"""

import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from database import (
    init_db, add_recipe, get_recipe, get_recipe_by_url, get_all_recipes,
    update_recipe, delete_recipe, toggle_favorite,
    get_staples, is_staple, add_staple, toggle_staple_low, delete_staple,
    enable_quantity_tracking, disable_quantity_tracking, set_staple_quantity,
    has_grocery_list_been_generated, mark_grocery_list_generated,
    record_pairings_from_meal_plan, suggest_meals,
    get_ingredient_category, get_meal_plan, add_to_meal_plan,
    remove_from_meal_plan, clear_meal_plan, get_week_start,
    set_store_override, get_store_overrides, delete_store_override,
    set_name_override, get_name_overrides, delete_name_override
)
from recipe_parser import parse_recipe_url, parse_ingredient_parts
from grocery_generator import generate_grocery_list

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')

UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_IMAGE_WIDTH = 800

def _save_upload(file):
    """Save an uploaded image, resize if too large, and return its URL path."""
    if file and file.filename:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext in ALLOWED_EXTENSIONS:
            from PIL import Image
            img = Image.open(file)
            # Convert RGBA to RGB for JPEG
            if img.mode in ('RGBA', 'P') and ext in ('jpg', 'jpeg'):
                img = img.convert('RGB')
            # Resize if wider than MAX_IMAGE_WIDTH
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                new_size = (MAX_IMAGE_WIDTH, int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            filename = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            img.save(save_path, quality=80, optimize=True)
            return url_for('static', filename=f'uploads/{filename}')
    return None

# Initialize database on startup
init_db()

# ============== Home ==============

@app.route('/')
def index():
    """Home page with quick access to main features."""
    recipes = get_all_recipes()[:6]  # Show recent recipes
    meal_plan = get_meal_plan()
    return render_template('index.html', recipes=recipes, meal_plan=meal_plan)

# ============== Recipes ==============

@app.route('/recipes')
def recipes():
    """Browse all recipes."""
    search = request.args.get('search', '')
    tag = request.args.get('tag', '')
    favorites_only = request.args.get('favorites') == '1'
    all_recipes = get_all_recipes(search=search, tag=tag if tag else None,
                                  favorites_only=favorites_only)

    # Get unique tags for filter
    all_tags = set()
    for recipe in get_all_recipes():
        all_tags.update(recipe.get('tags', []))

    return render_template('recipes.html', recipes=all_recipes,
                         search=search, current_tag=tag, all_tags=sorted(all_tags),
                         favorites_only=favorites_only)

@app.route('/recipes/<int:recipe_id>')
def recipe_detail(recipe_id):
    """View a single recipe."""
    recipe = get_recipe(recipe_id)
    if not recipe:
        flash('Recipe not found')
        return redirect(url_for('recipes'))
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/recipes/add', methods=['GET', 'POST'])
def add_recipe_page():
    """Add a new recipe (manual or from URL)."""
    if request.method == 'POST':
        url = request.form.get('url', '').strip()

        if url:
            # Check for duplicate URL
            existing = get_recipe_by_url(url)
            if existing:
                flash(f'This recipe has already been added: "{existing["title"]}"')
                return redirect(url_for('recipe_detail', recipe_id=existing['id']))

            # Import from URL
            try:
                recipe_data = parse_recipe_url(url)
                recipe_id = add_recipe(
                    title=recipe_data['title'],
                    ingredients=recipe_data['ingredients'],
                    instructions=recipe_data['instructions'],
                    url=url,
                    source=recipe_data.get('source'),
                    image_url=recipe_data.get('image_url'),
                    tags=[]
                )
                flash(f'Recipe "{recipe_data["title"]}" imported successfully!')
                return redirect(url_for('recipe_detail', recipe_id=recipe_id))
            except Exception as e:
                flash(f'Error importing recipe: {str(e)}')
                return redirect(url_for('add_recipe_page'))
        else:
            # Manual entry
            title = request.form.get('title', '').strip()
            ingredients_text = request.form.get('ingredients', '').strip()
            instructions = request.form.get('instructions', '').strip()
            tags_text = request.form.get('tags', '').strip()

            if not title or not ingredients_text:
                flash('Title and ingredients are required')
                return redirect(url_for('add_recipe_page'))

            # Parse ingredients (one per line)
            ingredients = []
            for line in ingredients_text.split('\n'):
                line = line.strip()
                if line:
                    parts = parse_ingredient_parts(line)
                    ingredients.append({
                        'raw': line,
                        'name': parts['name'],
                        'qty': parts['qty'],
                        'unit': parts['unit']
                    })

            # Parse tags (comma separated)
            tags = [t.strip() for t in tags_text.split(',') if t.strip()]

            image_url = _save_upload(request.files.get('image'))

            recipe_id = add_recipe(
                title=title,
                ingredients=ingredients,
                instructions=instructions,
                image_url=image_url,
                tags=tags
            )
            flash(f'Recipe "{title}" added successfully!')
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))

    return render_template('add_recipe.html')

@app.route('/recipes/<int:recipe_id>/edit', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    """Edit an existing recipe."""
    recipe = get_recipe(recipe_id)
    if not recipe:
        flash('Recipe not found')
        return redirect(url_for('recipes'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        ingredients_text = request.form.get('ingredients', '').strip()
        instructions = request.form.get('instructions', '').strip()
        tags_text = request.form.get('tags', '').strip()
        rating = int(request.form.get('rating', 0))
        notes = request.form.get('notes', '').strip()

        # Parse ingredients
        ingredients = []
        for line in ingredients_text.split('\n'):
            line = line.strip()
            if line:
                parts = parse_ingredient_parts(line)
                ingredients.append({
                    'raw': line,
                    'name': parts['name'],
                    'qty': parts['qty'],
                    'unit': parts['unit']
                })

        # Parse tags
        tags = [t.strip() for t in tags_text.split(',') if t.strip()]

        image_url = _save_upload(request.files.get('image'))

        update_kwargs = dict(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            tags=tags,
            rating=rating,
            notes=notes
        )
        if image_url:
            update_kwargs['image_url'] = image_url

        update_recipe(recipe_id, **update_kwargs)
        flash('Recipe updated!')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))

    # Format ingredients for textarea
    ingredients_text = '\n'.join(
        ing.get('raw', ing.get('name', ''))
        for ing in recipe['ingredients']
    )
    tags_text = ', '.join(recipe.get('tags', []))

    return render_template('edit_recipe.html', recipe=recipe,
                         ingredients_text=ingredients_text, tags_text=tags_text)

@app.route('/recipes/<int:recipe_id>/toggle-favorite', methods=['POST'])
def toggle_favorite_route(recipe_id):
    """Toggle favorite status of a recipe."""
    toggle_favorite(recipe_id)
    return redirect(request.referrer or url_for('recipes'))

@app.route('/recipes/<int:recipe_id>/delete', methods=['POST'])
def delete_recipe_route(recipe_id):
    """Delete a recipe."""
    recipe = get_recipe(recipe_id)
    if recipe:
        delete_recipe(recipe_id)
        flash(f'Recipe "{recipe["title"]}" deleted')
    return redirect(url_for('recipes'))

# ============== Meal Planning ==============

@app.route('/meal-plan')
def meal_plan():
    """View and manage weekly meal plan."""
    week_start = request.args.get('week', get_week_start())
    plan = get_meal_plan(week_start)
    all_recipes = get_all_recipes()
    return render_template('meal_plan.html',
                         plan=plan, recipes=all_recipes, week_start=week_start)

@app.route('/meal-plan/add', methods=['POST'])
def add_to_plan():
    """Add a recipe to the meal plan."""
    recipe_id = request.form.get('recipe_id', type=int)
    week_start = request.form.get('week_start', get_week_start())
    if recipe_id:
        add_to_meal_plan(recipe_id, week_start)
    return redirect(url_for('meal_plan', week=week_start))

@app.route('/meal-plan/remove', methods=['POST'])
def remove_from_plan():
    """Remove a recipe from the meal plan."""
    recipe_id = request.form.get('recipe_id', type=int)
    week_start = request.form.get('week_start', get_week_start())
    if recipe_id:
        remove_from_meal_plan(recipe_id, week_start)
    return redirect(url_for('meal_plan', week=week_start))

@app.route('/meal-plan/clear', methods=['POST'])
def clear_plan():
    """Clear the meal plan for a week."""
    week_start = request.form.get('week_start', get_week_start())
    clear_meal_plan(week_start)
    return redirect(url_for('meal_plan', week=week_start))

# ============== Grocery List ==============

@app.route('/grocery-list')
def grocery_list():
    """Generate and view grocery list from meal plan."""
    week_start = request.args.get('week', get_week_start())
    plan = get_meal_plan(week_start)

    if not plan:
        return render_template('grocery_list.html',
                             grocery_list=None, week_start=week_start, plan=[])

    already_generated = has_grocery_list_been_generated(week_start)
    grocery_data = generate_grocery_list(plan, apply_decrements=not already_generated)
    if not already_generated:
        mark_grocery_list_generated(week_start)
        record_pairings_from_meal_plan(week_start)

    return render_template('grocery_list.html',
                         grocery_list=grocery_data, week_start=week_start, plan=plan)

@app.route('/grocery/set-store', methods=['POST'])
def set_grocery_store():
    """Set a manual store override for an ingredient."""
    ingredient_name = request.form.get('ingredient_name', '').strip()
    store = request.form.get('store', '').strip()
    week_start = request.form.get('week_start', get_week_start())
    if ingredient_name and store:
        set_store_override(ingredient_name, store)
    return redirect(url_for('grocery_list', week=week_start))

@app.route('/grocery/set-name', methods=['POST'])
def set_grocery_name():
    """Set a name correction override for an ingredient."""
    original_name = request.form.get('original_name', '').strip()
    corrected_name = request.form.get('corrected_name', '').strip()
    corrected_qty = request.form.get('corrected_qty', '').strip()
    corrected_unit = request.form.get('corrected_unit', '').strip()
    week_start = request.form.get('week_start', get_week_start())
    if original_name and corrected_name:
        qty = float(corrected_qty) if corrected_qty else None
        unit = corrected_unit if corrected_unit else None
        set_name_override(original_name, corrected_name, qty, unit)
    return redirect(url_for('grocery_list', week=week_start))

# ============== Store Settings ==============

@app.route('/settings/stores')
def store_settings():
    """View and manage store assignment and name correction overrides."""
    overrides = get_store_overrides()
    name_overrides = get_name_overrides()
    return render_template('store_settings.html', overrides=overrides,
                         name_overrides=name_overrides)

@app.route('/settings/stores/delete/<int:override_id>', methods=['POST'])
def delete_store_override_route(override_id):
    """Delete a store override."""
    delete_store_override(override_id)
    flash('Store override removed')
    return redirect(url_for('store_settings'))

@app.route('/settings/names/delete/<int:override_id>', methods=['POST'])
def delete_name_override_route(override_id):
    """Delete a name correction override."""
    delete_name_override(override_id)
    flash('Name correction removed')
    return redirect(url_for('store_settings'))

# ============== Pantry ==============

@app.route('/pantry')
def pantry():
    """View and manage pantry staples."""
    staples = get_staples()
    # Group by category
    grouped = {}
    for staple in staples:
        cat = staple['category'] or 'Other'
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(staple)
    return render_template('pantry.html', grouped_staples=grouped)

@app.route('/pantry/add', methods=['POST'])
def add_pantry_staple():
    """Add a new pantry staple."""
    ingredient = request.form.get('ingredient', '').strip()
    category = request.form.get('category', 'Other').strip()
    if ingredient:
        add_staple(ingredient, category)
        flash(f'Added "{ingredient}" to pantry staples')
    return redirect(url_for('pantry'))

@app.route('/pantry/toggle-low/<int:staple_id>', methods=['POST'])
def toggle_low(staple_id):
    """Toggle the low status of a staple."""
    toggle_staple_low(staple_id)
    return redirect(url_for('pantry'))

@app.route('/pantry/delete/<int:staple_id>', methods=['POST'])
def delete_pantry_staple(staple_id):
    """Delete a pantry staple."""
    delete_staple(staple_id)
    return redirect(url_for('pantry'))

@app.route('/pantry/enable-quantity/<int:staple_id>', methods=['POST'])
def enable_quantity(staple_id):
    """Enable quantity tracking for a staple."""
    initial = request.form.get('initial_quantity', 0, type=int)
    enable_quantity_tracking(staple_id, initial)
    return redirect(url_for('pantry'))

@app.route('/pantry/disable-quantity/<int:staple_id>', methods=['POST'])
def disable_quantity(staple_id):
    """Disable quantity tracking for a staple."""
    disable_quantity_tracking(staple_id)
    return redirect(url_for('pantry'))

@app.route('/pantry/set-quantity/<int:staple_id>', methods=['POST'])
def update_quantity(staple_id):
    """Update the quantity of a staple."""
    quantity = request.form.get('quantity', 0, type=int)
    set_staple_quantity(staple_id, quantity)
    return redirect(url_for('pantry'))

# ============== Meal Suggestions ==============

@app.route('/suggest', methods=['GET', 'POST'])
def suggest_meals_page():
    """Meal suggestion page."""
    suggestions = None
    num_meals = 5
    constraints = {}

    all_recipes = get_all_recipes()
    mains = [r for r in all_recipes if 'main' in r.get('tags', [])]
    sides = [r for r in all_recipes if 'side' in r.get('tags', [])]

    # Gather constraint tags from mains (exclude "main"/"side")
    constraint_tags = set()
    for m in mains:
        for t in m.get('tags', []):
            if t not in ('main', 'side'):
                constraint_tags.add(t)

    if request.method == 'POST':
        num_meals = int(request.form.get('num_meals', 5))
        for tag in constraint_tags:
            count = int(request.form.get(f'tag_{tag}', 0))
            if count > 0:
                constraints[tag] = count

        suggestions = suggest_meals(num_meals=num_meals, constraints=constraints)

    return render_template('suggest.html',
                         suggestions=suggestions,
                         num_meals=num_meals,
                         constraints=constraints,
                         constraint_tags=sorted(constraint_tags),
                         main_count=len(mains),
                         side_count=len(sides),
                         week_start=get_week_start())

@app.route('/suggest/add-all', methods=['POST'])
def add_suggestions_to_plan():
    """Add all suggested recipes to the current meal plan."""
    week_start = request.form.get('week_start', get_week_start())
    recipe_ids = request.form.getlist('recipe_ids', type=int)
    for rid in recipe_ids:
        add_to_meal_plan(rid, week_start)
    flash(f'Added {len(recipe_ids)} recipes to meal plan!')
    return redirect(url_for('meal_plan', week=week_start))

# ============== API Endpoints ==============

@app.route('/api/recipes')
def api_recipes():
    """JSON API for recipes."""
    recipes = get_all_recipes()
    return jsonify(recipes)

@app.route('/api/grocery-list')
def api_grocery_list():
    """JSON API for grocery list."""
    week_start = request.args.get('week', get_week_start())
    plan = get_meal_plan(week_start)
    if not plan:
        return jsonify({'items': [], 'by_category': {}, 'by_store': {}})
    grocery_data = generate_grocery_list(plan)
    return jsonify(grocery_data)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  Grocery Lists App")
    print("  Open http://localhost:5001 in your browser")
    print("="*50 + "\n")
    app.run(debug=True, port=5001)
