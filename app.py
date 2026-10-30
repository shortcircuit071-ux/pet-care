from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyrebase
from google import genai

app = Flask(__name__)
app.secret_key = "super_secret_session_key_change_this"

# 1. Firebase Configuration
firebase_config = {
    "apiKey": "YOUR_FIREBASE_API_KEY",
    "authDomain": "YOUR_://firebaseapp.com",
    "databaseURL": "https://YOUR_://firebaseio.com",
    "projectId": "YOUR_PROJECT_ID",
    "storageBucket": "YOUR_://appspot.com",
    "messagingSenderId": "YOUR_SENDER_ID",
    "appId": "YOUR_APP_ID"
}
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database() # Using Firebase Realtime Database for quick setups

# 2. AI Configuration (Using Google Gemini)
# Make sure to set your environment variable or paste directly for a prototype
ai_client = genai.Client(api_key="YOUR_GEMINI_API_KEY")

# --- Authentication Middleware Helper ---
def get_current_user():
    return session.get('user_id'), session.get('email')

# --- Routes ---

@app.route('/')
def index():
    user_id, email = get_current_user()
    if not user_id:
        return redirect(url_for('login'))
    
    # Fetch only this user's pets from Firebase
    user_pets = db.child("pets").child(user_id).get().val() or {}
    return render_template('index.html', pets=user_pets, email=email)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            auth.create_user_with_email_and_password(email, password)
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Registration failed: Invalid email or password too short.", "error")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user_id'] = user['localId']
            session['email'] = email
            session['id_token'] = user['idToken']
            return redirect(url_for('index'))
        except Exception:
            flash("Invalid credentials. Try again.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id, email = get_current_user()
    if not user_id: return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete_account':
            try:
                # Remove user records from db first
                db.child("pets").child(user_id).remove()
                auth.delete_user(session['id_token'])
                session.clear()
                flash("Your account has been deleted permanently.", "success")
                return redirect(url_for('register'))
            except Exception:
                flash("Please re-login and try deleting again for security reasons.", "error")
    return render_template('profile.html', email=email)

# --- Pet CRUD + AI Features ---

@app.route('/pet/add', methods=['POST'])
def add_pet():
    user_id, _ = get_current_user()
    if not user_id: return redirect(url_for('login'))

    name = request.form.get('name')
    species = request.form.get('species')
    age = request.form.get('age')
    diet = request.form.get('diet')

    # Trigger Gemini AI to generate customized tips based on pet info
    try:
        ai_prompt = f"Provide 3 short, punchy bullet points of care or health tips for a {age} year old {species} pet named {name} who eats {diet}."
        ai_response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=ai_prompt)
        ai_tips = ai_response.text
    except Exception:
        ai_tips = "Could not generate AI insights at this time."

    pet_data = {
        "name": name,
        "species": species,
        "age": age,
        "diet": diet,
        "ai_tips": ai_tips
    }
    
    db.child("pets").child(user_id).push(pet_data)
    flash("Pet registered with AI insights!", "success")
    return redirect(url_for('index'))

@app.route('/pet/edit/<pet_id>', methods=['POST'])
def edit_pet(pet_id):
    user_id, _ = get_current_user()
    if not user_id: return redirect(url_for('login'))

    updated_data = {
        "name": request.form.get('name'),
        "species": request.form.get('species'),
        "age": request.form.get('age'),
        "diet": request.form.get('diet')
    }
    
    db.child("pets").child(user_id).child(pet_id).update(updated_data)
    flash("Pet details updated!", "success")
    return redirect(url_for('index'))

@app.route('/pet/delete/<pet_id>')
def delete_pet(pet_id):
    user_id, _ = get_current_user()
    if not user_id: return redirect(url_for('login'))

    db.child("pets").child(user_id).child(pet_id).remove()
    flash("Pet removed.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
