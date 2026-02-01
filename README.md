# Grocery Lists App

A meal planning and grocery list management app built with Flask and SQLite. Add recipes (manually or by importing from 40+ recipe websites), plan weekly meals, and generate organized shopping lists grouped by store or category.

## Setup

### Requirements

- Python 3

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python app.py
```

The app starts at **http://localhost:5001**. The SQLite database (`data/grocery.db`) is created automatically on first run with pre-seeded pantry staples and ingredient categories.

## Features

- **Recipes** — Add manually or import from URLs (AllRecipes, Bon Appetit, NYT Cooking, etc.). Rate, tag, and organize.
- **Meal Plan** — Assign recipes to days of the week. Navigate between weeks.
- **Grocery List** — Auto-generated from your meal plan. Items are deduplicated, categorized, and grouped by category or preferred store (Trader Joe's, Whole Foods, HMart). Copy to clipboard for Google Keep.
- **Pantry** — Track staples you keep on hand. Mark items as "low" so they appear on your grocery list.

## Project Structure

```
grocery_lists_app/
├── app.py                 # Flask routes and server entry point
├── database.py            # SQLite schema, CRUD operations, seeding
├── recipe_parser.py       # Recipe URL scraper (uses recipe-scrapers)
├── grocery_generator.py   # Grocery list generation and merging logic
├── requirements.txt
├── data/
│   └── grocery.db         # SQLite database (auto-created)
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── recipes.html
│   ├── recipe_detail.html
│   ├── add_recipe.html
│   ├── edit_recipe.html
│   ├── meal_plan.html
│   ├── grocery_list.html
│   └── pantry.html
└── static/
    ├── style.css
    └── app.js
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/recipes` | All recipes as JSON |
| `GET /api/grocery-list` | Current grocery list as JSON |

## Notes

- The Flask secret key in `app.py` is a placeholder — change it before exposing the app to the internet.
- The database file lives at `data/grocery.db`. Back this file up to preserve your recipes and meal plans.
