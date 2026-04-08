import pickle
import numpy as np
import os
import pandas as pd

# Load Model Once
MODEL_PATH = "ml_engine/student_success_model.pkl"
# If running not from root, try absolute path or adjust
if not os.path.exists(MODEL_PATH) and os.path.exists("student_success_model.pkl"):
    MODEL_PATH = "student_success_model.pkl"

model = None

try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    print("ML Model Loaded Successfully.")
except Exception as e:
    print(f"Error loading model: {e}")

def predict_student_risk(features):
    """
    Features dict:
    {
        'avg_quiz_score': float,
        'active_days': int,
        'posts_count': int,
        'lessons_completed': int
    }
    """
    if not model:
        return {"label": "Error", "color": "gray", "msg": "Model not loaded"}
        
    # Prepare DataFrame for scikit-learn
    df = pd.DataFrame([features])
    
    # Predict
    prediction = model.predict(df)[0]
    
    # Map Prediction to User Friendly Output
    if prediction == 0:
        return {"label": "At Risk", "color": "red", "msg": "Consider reaching out to offer support."}
    elif prediction == 1:
        return {"label": "Stable", "color": "#FFC107", "msg": "Student is progressing normally."} # Yellow/Amber
    else:
        return {"label": "Safe", "color": "green", "msg": "High performing student!"}
