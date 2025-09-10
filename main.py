from flask import Flask, request, jsonify
from google.cloud import firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os, datetime, bcrypt, jwt

app = Flask(__name__)

# -----------------------
# Config
# -----------------------
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
DB_NAME = os.getenv("FIRESTORE_DB", "test")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")  # Set this in Cloud Run env

client = firestore.Client(database=DB_NAME)

# -----------------------
# Initialize DB / Collections
# -----------------------
def initialize_db():
    """Ensure necessary collections exist and create initial documents."""
    # --- Users collection ---
    users_ref = client.collection("users").limit(1).get()
    if not users_ref:
        print("No users found. Creating default admin user...")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        hashed_pw = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        client.collection("users").add({
            "email": admin_email,
            "password": hashed_pw,
            "created_at": datetime.datetime.utcnow(),
            "role": "admin"
        })
        print(f"Admin user created: {admin_email}")

    # --- Example Posts collection ---
    posts_ref = client.collection("posts").limit(1).get()
    if not posts_ref:
        print("Creating sample posts...")
        client.collection("posts").add({
            "title": "Welcome Post",
            "content": "This is a sample post.",
            "created_at": datetime.datetime.utcnow(),
            "author": "system"
        })
        print("Sample post created.")

    # --- Auto-create indexes ---
    create_indexes()

# -----------------------
# Firestore Index Creation
# -----------------------
def create_indexes():
    """
    Auto-create composite indexes for common queries:
    e.g., posts ordered by created_at and filtered by author.
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        service = build('firestore', 'v1', credentials=credentials)
        parent = f'projects/{PROJECT_ID}/databases/(default)/collectionGroups/posts/indexes'

        indexes_to_create = [
            {
                "fields": [
                    {"fieldPath": "author", "order": "ASCENDING"},
                    {"fieldPath": "created_at", "order": "DESCENDING"}
                ],
                "queryScope": "COLLECTION"
            }
        ]

        for index in indexes_to_create:
            # Firestore Admin API requires POST to create index
            request = service.projects().databases().collectionGroups().indexes().create(
                parent=f'projects/{PROJECT_ID}/databases/(default)/collectionGroups/posts',
                body=index
            )
            response = request.execute()
            print(f"Index creation requested: {response.get('name')}")

    except Exception as e:
        print(f"Index creation skipped or failed: {e}")

initialize_db()
