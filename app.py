from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import json
import os
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_dev_key')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Try to get the Cloud Database URL from Render. If it's missing, fall back to local SQLite.
db_url = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'users.db'))


if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirects here if not logged in
login_manager.login_message = None


# DATABASE MODELS
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    # Acts exactly like old database.json, but safely stored per-user
    routine_data = db.Column(db.Text, default=json.dumps({"templates": {}, "progress": {}}))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# HELPER FUNCTIONS
def get_user_db():
    if current_user.routine_data:
        return json.loads(current_user.routine_data)
    return {"templates": {}, "progress": {}}


def save_user_db(data):
    current_user.routine_data = json.dumps(data)
    db.session.commit()


# AUTHENTICATION ROUTES
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=request.form.get('username'), password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# API ROUTES (Protected by @login_required)
@app.route('/api/routine/all', methods=['GET'])
@login_required
def get_all_routines():
    return jsonify(get_user_db())


@app.route('/api/routine/templates', methods=['POST'])
@login_required
def save_templates():
    new_templates = request.json
    if not isinstance(new_templates, dict):
        return jsonify({"error": "Invalid data format"}), 400

    try:
        db_data = get_user_db()
        db_data["templates"] = new_templates
        save_user_db(db_data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/progress/<date_str>', methods=['GET'])
@login_required
def get_progress(date_str):
    db_data = get_user_db()
    progress = db_data.get("progress", {}).get(date_str, {})
    return jsonify(progress)


@app.route('/api/progress/<date_str>', methods=['POST'])
@login_required
def save_progress(date_str):
    new_progress = request.json
    if not isinstance(new_progress, dict):
        return jsonify({"error": "Invalid data format"}), 400

    try:
        db_data = get_user_db()
        if "progress" not in db_data:
            db_data["progress"] = {}
        db_data["progress"][date_str] = new_progress
        save_user_db(db_data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)