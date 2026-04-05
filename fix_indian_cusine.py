from pymongo import MongoClient
 
client = MongoClient("mongodb://localhost:27017/")
db = client["cookbook_db"]
recipes = db["recipes"]
 
# Add cuisine: Indian to all recipes that don't have a cuisine field yet
result = recipes.update_many(
    {"cuisine": {"$exists": False}},
    {"$set": {"cuisine": "Indian"}}
)
 
print(f"Updated {result.modified_count} Indian recipes with cuisine field!")