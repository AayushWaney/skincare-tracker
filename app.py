from flask import Flask, jsonify, render_template, request
import json
import os
import threading

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.json')

db_lock = threading.Lock()

# In-Memory Cache
db_cache = None


def load_db():
    global db_cache

    # If already loaded it into memory, return it instantly for speed boost
    if db_cache is not None:
        return db_cache

    if not os.path.exists(DB_PATH):
        db_cache = {"templates": {}, "progress": {}}
        return db_cache

    with open(DB_PATH, 'r') as f:
        db = json.load(f)

    # DB structure (Ensures it never breaks if the file is empty)
    if "templates" not in db:
        db["templates"] = {}
    if "progress" not in db:
        db["progress"] = {}

    db_cache = db
    return db_cache


def save_db(data):
    global db_cache
    db_cache = data  # Update the memory cache instantly
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/routine/all', methods=['GET'])
def get_all_routines():
    db = load_db()
    return jsonify(db)


@app.route('/api/routine/templates', methods=['POST'])
def save_templates():
    new_templates = request.json

    # Validate incoming data
    if not isinstance(new_templates, dict):
        return jsonify({"error": "Invalid data format"}), 400

    with db_lock:
        try:
            db = load_db()
            db["templates"] = new_templates
            save_db(db)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/api/progress/<date_str>', methods=['GET'])
def get_progress(date_str):
    db = load_db()
    progress = db.get("progress", {}).get(date_str, {})
    return jsonify(progress)


@app.route('/api/progress/<date_str>', methods=['POST'])
def save_progress(date_str):
    new_progress = request.json

    # Validate incoming data
    if not isinstance(new_progress, dict):
        return jsonify({"error": "Invalid data format"}), 400

    with db_lock:
        try:
            db = load_db()
            db["progress"][date_str] = new_progress
            save_db(db)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)