FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies first (for faster caching)
# This installs all the required libraries (fastapi, uvicorn, mlflow, pandas, xgboost)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MLflow uses a local database (mlruns.db) for model metadata.
# We MUST copy it so the model loading function in main.py works.
COPY mlruns.db .

# Copy the application code
COPY main.py .

# Expose the port the API runs on
EXPOSE 8000

# Command to run the Uvicorn server when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
