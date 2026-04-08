import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# 1. Configuration
MODEL_PATH = "student_success_model.pkl"
SAMPLE_SIZE = 1000

# 2. Generate Synthetic Data
# Features:
# - avg_quiz_score (0-100)
# - active_days (0-30)
# - posts_count (0-20)
# - lessons_completed (0-50)

def generate_synthetic_data(n=1000):
    np.random.seed(42)
    
    avg_score = np.random.normal(loc=70, scale=15, size=n)
    avg_score = np.clip(avg_score, 0, 100)
    
    active_days = np.random.randint(0, 31, size=n)
    posts_count = np.random.poisson(lam=2, size=n)
    lessons_completed = np.random.randint(0, 50, size=n)
    
    # Label Generation Logic (Success Metric)
    # Success Score = (Score * 0.5) + (ActiveDays * 1.5) + (Posts * 2) + (Lessons * 1)
    # This is a hidden heuristic to create ground truth labels
    success_metric = (avg_score * 0.5) + (active_days * 1.5) + (posts_count * 2) + (lessons_completed * 1)
    
    # Define Classes based on Success Metric percentile
    # Low (At Risk) < 33rd percentile
    # Medium (Stable) 33rd-66th percentile
    # High (Safe) > 66th percentile
    
    p33 = np.percentile(success_metric, 33)
    p66 = np.percentile(success_metric, 66)
    
    labels = []
    for s in success_metric:
        if s < p33:
            labels.append(0) # At Risk
        elif s < p66:
            labels.append(1) # Stable
        else:
            labels.append(2) # Safe
            
    df = pd.DataFrame({
        'avg_quiz_score': avg_score,
        'active_days': active_days,
        'posts_count': posts_count,
        'lessons_completed': lessons_completed,
        'risk_level': labels
    })
    
    return df

# 3. Train Model
def train():
    print("Generating synthetic data...")
    df = generate_synthetic_data(SAMPLE_SIZE)
    
    X = df.drop('risk_level', axis=1)
    y = df['risk_level']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Model Accuracy: {acc:.2f}")
    
    # Save Model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(clf, f)
    print(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
