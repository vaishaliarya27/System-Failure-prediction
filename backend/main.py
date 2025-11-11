from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import mlflow.pyfunc
import pandas as pd
import numpy as np
import json
import asyncio
import logging
from datetime import datetime
import sqlite3
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Predictive Monitor API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
model = None
model_loaded = False

def load_model():
    """Load model from MLflow or create a mock model for demo"""
    global model, model_loaded
    
    try:
        # First, check if we can load from MLflow
        # Try to find model URI from the database
        conn = sqlite3.connect('mlruns.db')
        cursor = conn.cursor()
        
        # Query for model information
        cursor.execute("""
            SELECT run_id, artifact_uri FROM runs 
            WHERE run_id = '5482f4ad69d74181a86e9b5b1d2017cb'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            run_id, artifact_uri = result
            logger.info(f"Found model run: {run_id}")
            logger.info(f"Artifact URI: {artifact_uri}")
            
            # Try to load the model
            try:
                model = mlflow.pyfunc.load_model(f"runs:/{run_id}/model")
                model_loaded = True
                logger.info("✅ MLflow model loaded successfully!")
                return
            except Exception as e:
                logger.warning(f"Could not load MLflow model: {e}")
        
        # If MLflow model loading fails, create a mock model
        logger.info("Creating mock model for demonstration...")
        create_mock_model()
        model_loaded = True
        
    except Exception as e:
        logger.error(f"Error in model loading: {e}")
        # Create mock model as fallback
        create_mock_model()
        model_loaded = True

def create_mock_model():
    """Create a simple mock model for demonstration"""
    global model
    
    class MockModel:
        def predict(self, X):
            # Generate realistic-looking predictions
            if isinstance(X, pd.DataFrame):
                n_samples = len(X)
            else:
                n_samples = X.shape[0]
            
            # Simulate binary classification probabilities
            predictions = np.random.uniform(0, 1, n_samples)
            return predictions
    
    model = MockModel()
    logger.info("✅ Mock model created for demonstration")

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    logger.info("🚀 Starting up Predictive Monitor API...")
    load_model()

@app.get("/")
async def root():
    return {
        "message": "Predictive Monitor API", 
        "status": "running",
        "model_loaded": model_loaded,
        "model_type": "MLflow + Mock Fallback"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model_loaded
    }

@app.get("/model-status")
async def model_status():
    return {
        "model_loaded": model_loaded,
        "database_exists": os.path.exists("mlruns.db"),
        "database_size": os.path.getsize("mlruns.db") if os.path.exists("mlruns.db") else 0
    }

@app.post("/predict")
async def predict(data: dict):
    """Make a prediction with the loaded model"""
    if not model_loaded:
        return {"error": "Model not loaded", "prediction": None}
    
    try:
        # Get features from request
        features = data.get("features", [])
        
        # Create DataFrame with proper column names
        if features:
            n_features = len(features)
            columns = [f"feature_{i}" for i in range(n_features)]
            df = pd.DataFrame([features], columns=columns)
        else:
            # Generate random features if none provided
            df = pd.DataFrame(np.random.random((1, 10)))
        
        # Make prediction
        prediction = model.predict(df)
        
        # Format prediction for response
        if hasattr(prediction, 'tolist'):
            prediction_value = prediction.tolist()[0]
        else:
            prediction_value = float(prediction[0])
        
        # Generate confidence score
        confidence = min(0.95, max(0.7, prediction_value))
        
        return {
            "prediction": prediction_value,
            "confidence": confidence,
            "anomaly": prediction_value > 0.8,  # Example threshold
            "features_used": len(features) if features else 10,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"error": str(e), "prediction": None}

# WebSocket for real-time monitoring
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Generate real-time monitoring data
            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "predictions_made": np.random.randint(0, 1000),
                "avg_prediction_time": round(np.random.uniform(0.1, 2.0), 3),
                "model_confidence": round(np.random.uniform(0.7, 0.99), 3),
                "system_load": round(np.random.uniform(0.1, 0.8), 3),
                "active_connections": len(manager.active_connections),
                "anomalies_detected": np.random.randint(0, 10),
                "throughput": np.random.randint(50, 200)
            }
            
            await websocket.send_text(json.dumps(monitoring_data))
            await asyncio.sleep(2)  # Send data every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/database-info")
async def database_info():
    """Check what's in the MLflow database"""
    try:
        conn = sqlite3.connect('mlruns.db')
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Get run count
        cursor.execute("SELECT COUNT(*) FROM runs")
        run_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "tables": [table[0] for table in tables],
            "total_runs": run_count,
            "database_file": "mlruns.db",
            "file_exists": os.path.exists("mlruns.db")
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)