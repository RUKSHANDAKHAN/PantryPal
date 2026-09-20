# PantryPal 🍲

**Your AI Cooking Assistant**: turn whatever is in your kitchen into delicious meals, track expiry dates, and plan your whole week.
## 📸 Screenshots

## 📸 Screenshots

| Home | Recipe Collection |
|------|-------------------|
| ![Home](screenshots/Home%20page.png) | ![Recipe Collection](screenshots/Recipe%20Collection.png) |

| Meal Planner | Meal Plan Result |
|--------------|------------------|
| ![Meal Planner](screenshots/Meal%20planner.png) | ![Meal Plan Result](screenshots/Meal%20planner%20output.png) |

| Expiry Tracker | My Gallery |
|----------------|------------|
| ![Expiry Tracker](screenshots/Expiry%20tracker.png) | ![My Gallery](screenshots/My%20gallery.png) |

| Chef Bot |
|----------|
| ![Chef Bot](screenshots/Ai%20chatbot.png) |

🌐 **Live demo:** https://pantrypal-58tf.onrender.com

> The app is hosted on a free plan, so the first load after a period of inactivity can take up to a minute.

---

## 🚀 Features

- 🔐 **User accounts**: register and log in securely (passwords are hashed)
- 🧺 **My Pantry**: enter the ingredients you have, pick a cuisine and meal type, and get 3 AI-generated recipes with steps and a food-waste tip
- 🔄 **Smart Ingredient Substitutions**: missing an ingredient? Get 3 substitutes with exact quantities and taste/texture notes
- 📅 **Meal Planner**: generate a 7-day meal plan for any number of people, with a full shopping list you can download
- ⏰ **Expiry Tracker**: add items with expiry dates, see what is urgent, expiring soon, fine, or expired, and get AI recipes to use up items before they go bad
- 📖 **Recipes**: browse, search, and filter by cuisine; add or delete your own recipes
- 🥗 **Nutrition Estimates**: AI-estimated calories, protein, carbs, fat, and fiber for a recipe
- ❤️ **Favourites**: save the recipes you love
- 📸 **My Gallery**: upload photos of the dishes you cooked, with notes and optional links to recipes
- 🤖 **Chef Bot**: a friendly AI assistant for any cooking question

## 🛠 Tech Stack

- **Backend:** Python, Flask
- **Database:** MongoDB (Atlas)
- **AI:** Groq API (`openai/gpt-oss-120b`)
- **Frontend:** HTML, CSS, JavaScript
- **Hosting:** Render

## ▶️ Run Locally

1. Clone the repository:
```
   git clone https://github.com/RUKSHANDAKHAN/PantryPal.git
   cd PantryPal
```
2. Install dependencies:
```
   pip install -r requirements.txt
```
3. Create a `.env` file in the project folder:
```
   MONGO_URI=your_mongodb_connection_string
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=openai/gpt-oss-120b
```
   `GROQ_MODEL` is optional; the app uses `openai/gpt-oss-120b` by default.
4. Start the app:
```
   python app.py
```
5. Open http://127.0.0.1:10000 in your browser.

## 📁 Project Structure

```
PantryPal/
├── app.py              # Flask app and all routes
├── templates/          # HTML pages
├── static/uploads/     # Gallery photo uploads
├── requirements.txt
└── Procfile            # Render deployment
```

## 🔒 Note

Never upload your `.env` file or API keys to GitHub. Keep them in environment variables (locally in `.env`, on Render under **Environment**).

## 👩‍💻 Author

Rukshanda Khan

