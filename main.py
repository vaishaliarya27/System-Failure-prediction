from fastapi import FastAPI
from pydantic import BaseModel
import mlflow
import mlflow.xgboost 
import pandas as pd
import uvicorn
import os

# --- Configuration (Must match your training setup) ---
MLFLOW_TRACKING_URI = 'sqlite:///mlruns.db'
MODEL_NAME = "FailurePredictor"
MODEL_VERSION = 1 # Use the latest version in MLflow

# --- Pydantic Schema: Defines the structure of incoming data ---
# The names MUST match the features the model was trained on!
class PredictionRequest(BaseModel):
    # These are the feature names created in feature_engine.py
    sensor_A: float
    error_count: int
    sensor_A_mean_4h: float
    sensor_A_max_4h: float

# --- FastAPI Setup ---
app = FastAPI(
    title="Real-Time Failure Predictor API",
    version="1.0"
)

# Variable to hold the loaded ML model
model = None

@app.on_event("startup")
def load_model():
    """
    Loads the XGBoost model from MLflow Model Registry when the API starts.
    """
    global model
    # Ensure the database path exists relative to the current directory
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    try:
        # Load the model using the MLflow model URI
        model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
        
        # === THE FIX: Use mlflow.xgboost.load_model to restore native methods ===
        model = mlflow.xgboost.load_model(model_uri)
        
        print(f"Successfully loaded model: {model_uri}")
    except Exception as e:
        print(f"Error loading model from MLflow: {e}")
        # In a production setting, you would raise an exception and fail startup

@app.post("/predict")
async def predict(request: PredictionRequest):
    """
    Accepts new system telemetry data and returns the probability of failure 
    within the next 24 hours.
    """
    if model is None:
        return {"error": "Model not loaded. API is not ready."}, 500
    
    # Convert incoming data (Pydantic model) to a DataFrame row
    data_df = pd.DataFrame([request.dict()])
    
    # Ensure columns are in the correct order as trained (best practice)
    expected_columns = ['sensor_A', 'error_count', 'sensor_A_mean_4h', 'sensor_A_max_4h']
    
    # Reindex to ensure order and presence (and drop the index column if it snuck in)
    data_df = data_df.reindex(columns=expected_columns, fill_value=0)
    
    # Make prediction: [:, 1] gets the probability for the positive class (1)
    prediction_proba = model.predict_proba(data_df)[:, 1][0]
    
    # Define a simple threshold for alerting
    alert_threshold = 0.5 
    
    return {
        "status": "success",
        "failure_probability": float(prediction_proba),
        "alert": "True" if prediction_proba >= alert_threshold else "False"
    }

# Entry point for running the API server (only used if running this file directly)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
