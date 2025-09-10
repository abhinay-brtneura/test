from flask import Flask, request, jsonify
from google.cloud import firestore
import os, datetime, bcrypt, jwt

app = Flask(__name__)

# Use secret key for JWT (store in Cloud Run ENV)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")

# Firestore client (pointing to your custom DB)
DB_NAME = os.getenv("FIRESTORE_DB", "test")
client = firestore.Client(database=DB_NAME)


# -----------------------
# Signup Route
# -----------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    # Check if user exists
    user_ref = client.collection("users").where("email", "==", email).get()
    if user_ref:
        return jsonify({"error": "User already exists"}), 400

    # Hash password
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Save user
    client.collection("users").add({
        "email": email,
        "password": hashed,
        "created_at": datetime.datetime.utcnow()
    })

    return jsonify({"message": "User created successfully"}), 201


# -----------------------
# Signin Route
# -----------------------
@app.route("/signin", methods=["POST"])
def signin():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    # Lookup user
    users = client.collection("users").where("email", "==", email).get()
    if not users:
        return jsonify({"error": "User not found"}), 404

    user = users[0].to_dict()
    hashed_pw = user["password"]

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8")):
        return jsonify({"error": "Invalid password"}), 401

    # Create JWT token
    token = jwt.encode({
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"token": token})


# -----------------------
# Protected Route
# -----------------------
@app.route("/profile", methods=["GET"])
def profile():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Token missing"}), 401

    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return jsonify({"message": f"Welcome {decoded['email']}!"})
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401


# -----------------------
# Health Check
# -----------------------
@app.route("/")
def home():
    return jsonify({"status": "running", "db": DB_NAME})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
