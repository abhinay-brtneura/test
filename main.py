from flask import Flask, jsonify
from google.auth import default
from google.cloud import firestore

app = Flask(__name__)

@app.route("/check-auth")
def check_auth():
    try:
        # Check what credentials Cloud Run is using
        creds, project = default()
        client = firestore.Client(database="skill-assessment")
        docs = client.collection("test").limit(1).get()

        return jsonify({
            "auth_type": str(type(creds)),
            "project_id": project,
            "firestore_access": "success",
            "sample_doc": [doc.to_dict() for doc in docs]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
