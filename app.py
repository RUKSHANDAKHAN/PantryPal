from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from flask_login import current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, date
from groq import Groq
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import io
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv



app = Flask(__name__)
app.secret_key = "pantrypal_secret_key_2024"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# New MongoDB collection for gallery

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── MongoDB ──────────────────────────────────────────────

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MongoDB URI is missing. Please set MONGO_URI in environment variables.")

client_db = MongoClient(MONGO_URI)
db = client_db["cookbook_db"]  # same database name
recipes = db["recipes"]
expiry_items = db["expiry_items"]
users = db["users"]
favorites = db["favorites"]
gallery_col = db["gallery"]
chat_messages = db["chat_messages"]

# ── Groq AI ──────────────────────────────────────────────
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY is missing")

groq_client = Groq(api_key=api_key)

def ask_claude(prompt):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096
    )
    return response.choices[0].message.content

# ── LOGIN REQUIRED DECORATOR ─────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ── AUTH ROUTES ───────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            error = "All fields are required!"
        elif users.find_one({"email": email}):
            error = "Email already registered! Please login."
        else:
            hashed_pw = generate_password_hash(password)
            user = {
                "name": name,
                "email": email,
                "password": hashed_pw,
                "created_at": datetime.now().strftime('%Y-%m-%d')
            }
            result = users.insert_one(user)
            session['user_id'] = str(result.inserted_id)
            session['user_name'] = name
            return redirect(url_for('home'))

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = users.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password!"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── HOME ─────────────────────────────────────────────────
@app.route('/')
@login_required
def home():
    total_recipes = recipes.count_documents({})
    expiring_count = 0
    all_items = list(expiry_items.find())
    for item in all_items:
        try:
            exp_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_left = (exp_date - date.today()).days
            if 0 <= days_left <= 3:
                expiring_count += 1
        except:
            pass
    return render_template('index.html',
                           total_recipes=total_recipes,
                           expiring_count=expiring_count,
                           user_name=session.get('user_name', ''))

# ── PANTRY: AI RECIPE SUGGESTIONS ────────────────────────
@app.route('/pantry', methods=['GET', 'POST'])
@login_required
def pantry():
    suggestions = None
    ingredients_input = ""
    if request.method == 'POST':
        ingredients_input = request.form.get('ingredients', '')
        cuisine_pref = request.form.get('cuisine_pref', 'Any')
        meal_type = request.form.get('meal_type', 'Any')

        prompt = f"""Ingredients: {ingredients_input}
Cuisine: {cuisine_pref} | Meal: {meal_type}

Give 3 recipes. For each use this format:

🍽️ [RECIPE NAME]
⏱️ Time: X mins
🥘 Use: [ingredients from list]
➕ Extra: [1-2 extras or "None!"]
📝 Steps:
1. [detailed step one]
2. [detailed step two]
3. [detailed step three]
4. [detailed step four]
♻️ Tip: [1 waste reduction tip]
---"""

        try:
            suggestions = ask_claude(prompt)
        except Exception as e:
            suggestions = f"Error: {str(e)}"

    return render_template('pantry.html', suggestions=suggestions, ingredients_input=ingredients_input)

# ── MEAL PLANNER ─────────────────────────────────────────
@app.route('/planner', methods=['GET'])
@login_required
def planner():
    return render_template('planner.html')

@app.route('/planner/generate', methods=['POST'])
@login_required
def planner_generate():
    people_count = request.form.get('people', '2')
    cuisine_mix = request.form.get('cuisine_mix', 'Mixed')
    preferences = request.form.get('preferences', '')

    prompt = f"""Generate a detailed 7-day meal plan.
People: {people_count}
Cuisine: {cuisine_mix}
Preferences: {preferences if preferences else 'None'}

Format each day exactly like this:
Day 1:
  Breakfast: [meal name]
  Lunch: [meal name]
  Dinner: [meal name]

Day 2:
  Breakfast: [meal name]
  Lunch: [meal name]
  Dinner: [meal name]

(repeat for all 7 days)

Then end with:
Shopping List:
- item 1
- item 2
- item 3
(list every ingredient needed for the full week)"""

    try:
        result = ask_claude(prompt)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"meal_plan": result})

# ── SHOPPING LIST PDF EXPORT ──────────────────────────────
@app.route('/shopping-list/export', methods=['POST'])
@login_required
def export_shopping_list():
    items_text = request.form.get('items', '')
    user_name = session.get('user_name', 'User')

    # Build plain text PDF content
    lines = []
    lines.append("PANTRY PAL - SHOPPING LIST")
    lines.append(f"Generated for: {user_name}")
    lines.append(f"Date: {date.today().strftime('%d %B %Y')}")
    lines.append("-" * 40)
    lines.append("")

    if items_text:
        for item in items_text.split('\n'):
            if item.strip():
                lines.append(f"[ ]  {item.strip()}")
    else:
        lines.append("No items in shopping list.")

    lines.append("")
    lines.append("-" * 40)
    lines.append("Generated by Pantry Pal - AI Cooking Assistant")

    content = '\n'.join(lines)

    # Send as downloadable text file
    buffer = io.BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'shopping_list_{date.today()}.txt',
        mimetype='text/plain'
    )

# ── FAVORITES ─────────────────────────────────────────────
@app.route('/favorites')
@login_required
def favorites_page():
    user_id = session.get('user_id')
    fav_docs = list(favorites.find({"user_id": user_id}))
    fav_recipe_ids = [f['recipe_id'] for f in fav_docs]
    fav_recipes = []
    for rid in fav_recipe_ids:
        try:
            r = recipes.find_one({"_id": ObjectId(rid)})
            if r:
                fav_recipes.append(r)
        except:
            pass
    return render_template('favorites.html', recipes=fav_recipes)


@app.route('/favorites/add/<recipe_id>')
@login_required
def add_favorite(recipe_id):
    user_id = session.get('user_id')
    existing = favorites.find_one({"user_id": user_id, "recipe_id": recipe_id})
    if not existing:
        favorites.insert_one({
            "user_id": user_id,
            "recipe_id": recipe_id,
            "added_on": date.today().strftime('%Y-%m-%d')
        })
    return redirect(url_for('recipe_detail', id=recipe_id))

@app.route('/favorites/remove/<recipe_id>')
@login_required
def remove_favorite(recipe_id):
    user_id = session.get('user_id')
    favorites.delete_one({"user_id": user_id, "recipe_id": recipe_id})
    return redirect(url_for('favorites_page'))

# ── EXPIRY TRACKER ────────────────────────────────────────
@app.route('/expiry')
@login_required
def expiry():
    all_items = list(expiry_items.find())
    categorized = {"urgent": [], "warning": [], "good": [], "expired": []}

    for item in all_items:
        try:
            exp_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            days_left = (exp_date - date.today()).days
            item['days_left'] = days_left
            item['exp_formatted'] = exp_date.strftime('%d %b %Y')
            if days_left < 0:
                categorized['expired'].append(item)
            elif days_left <= 3:
                categorized['urgent'].append(item)
            elif days_left <= 7:
                categorized['warning'].append(item)
            else:
                categorized['good'].append(item)
        except:
            item['days_left'] = 99
            item['exp_formatted'] = item.get('expiry_date', 'Unknown')
            categorized['good'].append(item)

    return render_template('expiry.html', categorized=categorized)

@app.route('/expiry/add', methods=['POST'])
@login_required
def add_expiry():
    item = {
        "name": request.form['name'],
        "quantity": request.form['quantity'],
        "expiry_date": request.form['expiry_date'],
        "added_on": date.today().strftime('%Y-%m-%d')
    }
    expiry_items.insert_one(item)
    return redirect(url_for('expiry'))

@app.route('/expiry/delete/<id>')
@login_required
def delete_expiry(id):
    expiry_items.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('expiry'))

@app.route('/expiry/suggest', methods=['POST'])
@login_required
def suggest_from_expiry():
    urgent_items = request.form.get('items', '')
    prompt = f"""Expiring today/tomorrow: {urgent_items}
Give 2 quick recipes using these. Format:
🚨 [Recipe Name] | ⏱️ X mins
📝 3 quick steps
♻️ How it uses expiring items
---"""
    try:
        result = ask_claude(prompt)
    except Exception as e:
        result = f"Error: {str(e)}"
    return jsonify({"suggestions": result})

# ── RECIPES BROWSER ───────────────────────────────────────
@app.route('/recipes')
@login_required
def recipes_page():
    query = request.args.get('q')
    cuisine = request.args.get('cuisine')
    filters = {}
    if query:
        filters["title"] = {"$regex": query, "$options": "i"}
    if cuisine and cuisine != "All":
        filters["cuisine"] = cuisine
    data = list(recipes.find(filters))

    # Get user favorites
    user_id = session.get('user_id')
    fav_docs = list(favorites.find({"user_id": user_id}))
    fav_ids = [f['recipe_id'] for f in fav_docs]

    return render_template('recipes.html', recipes=data,
                           selected_cuisine=cuisine or "All",
                           query=query or "",
                           fav_ids=fav_ids)

@app.route('/recipe/<id>')
@login_required
def recipe_detail(id):
    recipe = recipes.find_one({"_id": ObjectId(id)})
    user_id = session.get('user_id')
    is_favorite = favorites.find_one({"user_id": user_id, "recipe_id": id}) is not None
    return render_template('recipe_detail.html', recipe=recipe, is_favorite=is_favorite)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_recipe():
    if request.method == 'POST':
        new_recipe = {
            "title": request.form['title'],
            "ingredients": [i.strip() for i in request.form['ingredients'].split(',')],
            "steps": request.form['steps'],
            "cuisine": request.form['cuisine']
        }
        recipes.insert_one(new_recipe)
        return redirect(url_for('recipes_page'))
    return render_template('add_recipe.html')

@app.route('/delete/<id>')
@login_required
def delete_recipe(id):
    recipes.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('recipes_page'))

@app.route('/recipe/<id>/nutrition')
def recipe_nutrition(id):
    recipe = recipes.find_one({"_id": ObjectId(id)})
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    ingredients = recipe.get('ingredients', [])
    if isinstance(ingredients, list):
        ing_text = ', '.join(ingredients)
    else:
        ing_text = ingredients

    prompt = f"""Estimate nutrition for one serving of "{recipe['title']}".
Ingredients: {ing_text}

Reply ONLY in this exact JSON format, no extra text:
{{
  "calories": 350,
  "protein": 25,
  "carbs": 30,
  "fat": 12,
  "fiber": 4,
  "serving": "1 plate (approx 300g)"
}}"""

    try:
        result = ask_claude(prompt)
        # clean any markdown fences
        result = result.strip().replace('```json','').replace('```','').strip()
        import json
        data = json.loads(result)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── GALLERY ──────────────────────────────────────────────
@app.route('/gallery')
def gallery_page():
    photos = list(gallery_col.find().sort("_id", -1))
    all_recipes = list(recipes.find({}, {"title": 1}))
    return render_template('gallery.html', photos=photos, recipes=all_recipes)

@app.route('/gallery/upload', methods=['POST'])
def gallery_upload():
    if 'photo' not in request.files:
        return redirect(url_for('gallery_page'))
    
    file = request.files['photo']
    title = request.form.get('title', 'My Dish')
    note = request.form.get('note', '')
    linked_recipe = request.form.get('linked_recipe', '')

    if file and allowed_file(file.filename):
        filename = secure_filename(f"gallery_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        gallery_col.insert_one({
            "filename": filename,
            "title": title,
            "note": note,
            "linked_recipe": linked_recipe,
            "date": date.today().strftime('%d %b %Y')
        })

    return redirect(url_for('gallery_page'))

@app.route('/gallery/delete/<id>')
def gallery_delete(id):
    photo = gallery_col.find_one({"_id": ObjectId(id)})
    if photo:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        gallery_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('gallery_page'))
# ── SMART SUBSTITUTIONS ──────────────────────────────────
@app.route('/substitute', methods=['POST'])
def substitute():
    ingredient = request.form.get('ingredient', '')
    dish = request.form.get('dish', '')

    prompt = f"""I don't have "{ingredient}" for my cooking.
{"I'm making: " + dish if dish else ""}

Suggest 3 smart substitutes. For each use exactly this format:

✅ [Substitute Name]
📏 Use: [exact quantity to replace e.g. "use 3/4 cup yogurt instead of 1 cup cream"]
🍽️ Works best for: [what dishes/uses it works for]
⚠️ Note: [any important difference in taste or texture]
---"""

    try:
        result = ask_claude(prompt)
    except Exception as e:
        result = f"Error: {str(e)}"

    return jsonify({"result": result})

@app.route('/assistant')
def assistant():
    return render_template('assistant.html')

@app.route('/assistant/chat', methods=['POST'])
def assistant_chat():
    message = request.form.get('message', '')
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    prompt = f"""You are Chef Bot, a friendly AI cooking assistant for Pantry Pal.
User asked: {message}
Give helpful, friendly cooking advice with emojis. Keep it practical and clear."""

    try:
        result = ask_claude(prompt)
        return jsonify({'response': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)