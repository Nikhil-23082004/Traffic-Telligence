import pandas as pd
import numpy as np
import pickle

# Load model
with open(r"C:\Users\nikhi\OneDrive\Desktop\Internship APSCHE\auth\templates\model.pkl", "rb") as f:
    model = pickle.load(f)

# Load encoder and scaler
with open(r"C:\Users\nikhi\OneDrive\Desktop\Internship APSCHE\auth\templates\encoder.pkl", "rb") as f:
    encoders = pickle.load(f)

weather_encoder = encoders['weather_encoder']
scaler = encoders['scaler']

# New input values
new_data = {
    'holiday': [1],
    'temp': [308.25],
    'rain': [0],
    'snow': [0],
    'weather': [weather_encoder.transform(['Clear'])[0]],
    'day': [16],
    'month': [6],
    'year': [2024],
    'hours': [17],
    'minutes': [30],
    'seconds': [0]
}
new_instance = pd.DataFrame(new_data)
new_instance_scaled = scaler.transform(new_instance)

# Predict
predicted_volume = model.predict(new_instance_scaled)[0]

print("\n=== Predicted Traffic Volume ===")
print(f"Predicted Volume: {predicted_volume:.2f} vehicles")
