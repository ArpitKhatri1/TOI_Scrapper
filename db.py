from config import MONGODB_PASSWORD,MONGODB_USER
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
uri = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASSWORD}@cluster0.3la4lvh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(uri,server_api=ServerApi('1'))

db = client.vibenews_db
articles_collection:Collection = db["vibenews_articles"]
new_articles_collection:Collection = db["articles_tags"]

try:
    client.admin.command('ping')
    print("✅ Ping successful: Connected to MongoDB!")
except ConnectionFailure as e:
    print(f"❌ Ping failed: {e}")