# train_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import recall_score, precision_score
import mlflow
import numpy as np

# --- Configuration ---
FINAL_DATA_PATH = 'prepared_data.csv' 
TARGET_COLUMN = 'will_fail'
MLFLOW_TRACKING_URI = 'sqlite:///mlruns.db'

# Set up MLflow
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("System_Failure_Prediction")

# --- 1. Load Data and Split ---
print("Loading data and splitting...")
df = pd.read_csv(FINAL_DATA_PATH).set_index('timestamp')
X = df.drop(columns=[TARGET_COLUMN])
y = df[TARGET_COLUMN]

print(f"Dataset shape: {X.shape}")
print(f"Target distribution:\n{y.value_counts()}")
print(f"Positive class ratio: {y.mean():.4f}")

# --- 2. Handle the case where there are no positive samples in training ---
# Use stratified split to ensure positive samples in both train and test
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=True, stratify=y, random_state=42
    )
except ValueError:
    # If stratification fails (not enough positive samples), use regular split
    print("Stratified split failed, using regular split...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=True, random_state=42
    )

print(f"Training set - Positive ratio: {y_train.mean():.4f}")
print(f"Test set - Positive ratio: {y_test.mean():.4f}")

# --- 3. Start MLflow Run and Train Model ---
with mlflow.start_run() as run:
    
    # Calculate base_score - ensure it's in valid range (0,1)
    positive_ratio = y_train.mean()
    if positive_ratio == 0:
        # If no positive samples in training, use a small non-zero value
        base_score_value = 0.01
        print(f"No positive samples in training. Using base_score: {base_score_value}")
    elif positive_ratio == 1:
        # If all samples are positive, use a value less than 1
        base_score_value = 0.99
        print(f"All samples positive in training. Using base_score: {base_score_value}")
    else:
        base_score_value = max(0.01, min(0.99, positive_ratio))
        print(f"Using calculated base_score: {base_score_value:.4f}")
    
    # Define Hyperparameters
    params = {
        "objective": "binary:logistic",
        "n_estimators": 100,
        "learning_rate": 0.1,
        "max_depth": 5,
        "random_state": 42,
        "use_label_encoder": False,
        "base_score": base_score_value,
        "eval_metric": "logloss",
        "scale_pos_weight": 1.0  # Handle class imbalance
    }
    
    # If we have imbalanced data, adjust scale_pos_weight
    if positive_ratio > 0 and positive_ratio < 1:
        params["scale_pos_weight"] = (1 - positive_ratio) / positive_ratio
    
    # Log parameters
    mlflow.log_params(params)

    # Initialize and Train the Model
    model = XGBClassifier(**params)
    model.fit(X_train, y_train)

    # --- 4. Evaluate and Log Metrics ---
    y_pred = model.predict(X_test)
    
    recall = recall_score(y_test, y_pred, zero_division=0) 
    precision = precision_score(y_test, y_pred, zero_division=0)
    
    print(f"Test Recall Score: {recall:.4f}")
    print(f"Test Precision Score: {precision:.4f}")
    print(f"Test set size: {len(y_test)}")
    print(f"Positive samples in test: {y_test.sum()}")

    # Log metrics
    mlflow.log_metric("test_recall", recall)
    mlflow.log_metric("test_precision", precision)

    # --- 5. Register the Model ---
    mlflow.xgboost.log_model(
        xgb_model=model, 
        artifact_path="model", 
        registered_model_name="FailurePredictor"
    )

    print(f"Model logged to MLflow. Run ID: {run.info.run_id}")