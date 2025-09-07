from flask import Flask, request, render_template, jsonify, redirect, url_for
import random
import smtplib
from email.mime.text import MIMEText
import os
import pickle
from pymongo import MongoClient
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from xgboost import XGBRegressor

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI")
PASSWORD = os.getenv("PASSWORD")
# ---------------- Database Connection ----------------
try:
    client = MongoClient(MONGO_URI)
    db = client['APSCHE']
    users_collection = db['userdata']
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# ---------------- OTP and Email Config ----------------
otp_store = {}
EMAIL_SENDER = "clginternshipacc@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", PASSWORD)  # ⚠️ use Render env var


def send_email(email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP code is {otp}. Use it to log in."

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# ---------------- Routes ----------------
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('setPwd')
        confirm_password = request.form.get('confirmPwd')

        if not all([fname, lname, email, password, confirm_password]):
            return "All fields are required.", 400

        if password != confirm_password:
            return "Passwords do not match.", 400

        if users_collection.find_one({"email": email}):
            return "User already registered.", 400

        users_collection.insert_one({
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "password": password
        })

        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = users_collection.find_one({"email": email, "password": password})
    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    otp = random.randint(100000, 999999)
    otp_store[email] = otp

    if send_email(email, otp):
        return jsonify({"message": f"OTP sent to {email}"}), 200
    else:
        return jsonify({"message": "Failed to send OTP"}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp_entered = int(data.get('otp', 0))

    if not email or email not in otp_store:
        return jsonify({"message": "Invalid email"}), 400

    if otp_store.get(email) == otp_entered:
        del otp_store[email]
        return jsonify({"message": "Login successful", "redirect": url_for('interface')}), 200

    return jsonify({"message": "Incorrect OTP. Try again"}), 400

@app.route('/interface')
def interface():
    return render_template('interface.html')


# ---------------- Load Model and Encoders ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

with open(os.path.join(MODELS_DIR, "encoder.pkl"), "rb") as f:
    encoders = pickle.load(f)

weather_encoder = encoders['weather_encoder']
scaler = encoders['scaler']

with open(os.path.join(MODELS_DIR, "model.pkl"), "rb") as f:
    model = pickle.load(f)


# ---------------- Prediction Route ----------------
@app.route('/process', methods=['POST'])
def process():
    try:
        holiday = request.form.get('holiday', "").strip()
        temp = request.form.get('temp', "").strip()
        rain = request.form.get('rain', "").strip()
        snow = request.form.get('snow', "").strip()
        weather = request.form.get('weather', "").strip()
        day = request.form.get('day', "").strip()
        month = request.form.get('month', "").strip()
        year = request.form.get('year', "").strip()
        hours = request.form.get('hours', "").strip()
        minutes = request.form.get('minutes', "").strip()
        seconds = request.form.get('seconds', "").strip()

        fields = [holiday, temp, rain, snow, weather, day, month, year, hours, minutes, seconds]
        if not all(fields):
            return jsonify({"error": "All fields must be provided."}), 400

        input_data = pd.DataFrame([[
            int(holiday),
            float(temp),
            float(rain),
            float(snow),
            weather_encoder.transform([weather])[0],
            int(day),
            int(month),
            int(year),
            int(hours),
            int(minutes),
            int(seconds)
        ]], columns=[
            'holiday', 'temp', 'rain', 'snow', 'weather',
            'day', 'month', 'year', 'hours', 'minutes', 'seconds'
        ])

        input_scaled = scaler.transform(input_data)
        predicted_volume = model.predict(input_scaled)[0]

        return render_template(
            'result.html',
            predicted_volume=round(predicted_volume, 2),
            inputs={
                'Holiday': holiday,
                'Temp (K)': temp,
                'Rain (mm)': rain,
                'Snow (mm)': snow,
                'Weather': weather,
                'Date': f"{day}/{month}/{year}",
                'Time': f"{hours}:{minutes}:{seconds}"
            }
        )

    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500


# ---------------- Run Server ----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)


