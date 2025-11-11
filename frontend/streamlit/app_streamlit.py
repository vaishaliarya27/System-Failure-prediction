import streamlit as st
import requests
import json
import pandas as pd
import time

# --- CONFIGURATION ---
API_URL = "http://localhost:8080/predict" 
FAILURE_THRESHOLD = 0.7

st.set_page_config(
    page_title="Predictive Maintenance Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_probability(prob):
    """Formats the probability as a percentage string."""
    prob = max(0.0, min(1.0, prob))
    return f"{prob * 100:.1f}%"

def extract_probability(result):
    """Extracts probability from API response, handling different response formats."""
    if isinstance(result, dict):
        # Handle dictionary response
        return result.get("failure_probability", 
                         result.get("probability", 
                                   result.get("prediction", 0)))
    elif isinstance(result, list):
        # Handle list response - take first element if it's a dict
        if result and isinstance(result[0], dict):
            return result[0].get("failure_probability", 0)
        # If it's a list of numbers, take the first one (assuming it's the probability)
        elif result and isinstance(result[0], (int, float)):
            return float(result[0])
        else:
            return 0
    elif isinstance(result, (int, float)):
        # Handle direct numeric response
        return float(result)
    else:
        return 0

def call_api(data):
    """Sends the machine parameters to the FastAPI service."""
    try:
        response = requests.post(API_URL, json=data, timeout=5)
        response.raise_for_status()
        time.sleep(0.5)
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Connection Error: Could not reach the ML service at {API_URL}. Please ensure your Docker container is running on port 8080 and accessible.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ API Error: Received HTTP status {e.response.status_code}. Response: {e.response.text}")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Timeout Error: The ML service did not respond within the time limit.")
        return None
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")
        return None

# --- UI LAYOUT ---

st.title("🏭 Predictive Maintenance Dashboard")
st.markdown("Monitor and predict critical machine failures using your deployed ML service.")

col_input, col_output = st.columns([2, 1])

with col_input:
    st.subheader("Machine Operating Parameters")
    st.markdown("Adjust the values and click 'Check Risk' to get an instant prediction.")

    col1, col2 = st.columns(2)

    with col1:
        current_temp = st.slider("Current Temperature (°C)", 280.0, 350.0, 320.0, 0.1)
        voltage = st.slider("Voltage (V)", 15.0, 20.0, 17.0, 0.1)
        rot_speed = st.slider("Rotational Speed (RPM)", 1300, 2000, 1500, 10)
        sensor_A = st.slider("Sensor A Reading", 0.0, 100.0, 50.0, 0.1)

    with col2:
        torque = st.slider("Torque (Nm)", 30.0, 60.0, 45.0, 0.1)
        tool_wear = st.slider("Tool Wear (Min)", 0, 250, 150, 1)
        error_count = st.slider("Error Count (last 24h)", 0, 10, 0, 1)
        sensor_A_mean_4h = st.slider("Sensor A Mean (4h)", 0.0, 100.0, 50.0, 0.1)
        sensor_A_max_4h = st.slider("Sensor A Max (4h)", 0.0, 100.0, 60.0, 0.1)

        status_map = {"Active": 1, "Down": 0}
        status_selection = st.selectbox("Machine Status", list(status_map.keys()))
        status = status_map[status_selection]

        error_map = {"No Error": 0, "Type 1 (Heat/Temp)": 1, "Type 2 (Power/Voltage)": 2, "Type 3 (Tool/Torque)": 3}
        error_selection = st.selectbox("Observed Error Type", list(error_map.keys()))
        error_type = error_map[error_selection]

    st.markdown("---")

    if st.button("🚨 CHECK FAILURE RISK NOW", use_container_width=True, type="primary"):
        input_data = {
            "status": status,
            "current_temp": current_temp,
            "voltage": voltage,
            "rot_speed": rot_speed,
            "torque": torque,
            "tool_wear": tool_wear,
            "error_type": error_type,
            "sensor_A": sensor_A,
            "error_count": error_count,
            "sensor_A_mean_4h": sensor_A_mean_4h,
            "sensor_A_max_4h": sensor_A_max_4h
        }

        with st.spinner('Calculating risk...'):
            prediction_result = call_api(input_data)

        if prediction_result is not None:
            st.session_state['prediction'] = prediction_result
            st.session_state['input_data'] = input_data

# --- OUTPUT DISPLAY ---

with col_output:
    st.subheader("Prediction Result")

    if 'prediction' in st.session_state:
        result = st.session_state['prediction']
        
        # Use the new extraction function
        probability = extract_probability(result)

        # Debug information (can be removed later)
        with st.expander("Debug Info"):
            st.write(f"Response type: {type(result)}")
            st.write(f"Full response: {result}")
            st.write(f"Extracted probability: {probability}")

        # Determine visual style based on threshold
        if probability > FAILURE_THRESHOLD:
            st.markdown(f"""
                <div style='background-color: #ef4444; color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style='margin: 0; font-size: 1.5rem;'>⚠️ CRITICAL RISK ⚠️</h3>
                    <p style='font-size: 4rem; font-weight: bold; margin: 10px 0;'>{format_probability(probability)}</p>
                    <p style='margin: 0;'>IMMEDIATE ATTENTION REQUIRED</p>
                </div>
            """, unsafe_allow_html=True)
            st.error(f"**Action Required:** High predicted risk of failure: {format_probability(probability)}! Investigate component status.")

        elif probability > 0.4:
            st.markdown(f"""
                <div style='background-color: #f59e0b; color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style='margin: 0; font-size: 1.5rem;'>📈 MEDIUM RISK</h3>
                    <p style='font-size: 4rem; font-weight: bold; margin: 10px 0;'>{format_probability(probability)}</p>
                    <p style='margin: 0;'>MONITOR CLOSELY</p>
                </div>
            """, unsafe_allow_html=True)
            st.warning("Risk is elevated. Continue monitoring parameters.")
        else:
            st.markdown(f"""
                <div style='background-color: #10b981; color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style='margin: 0; font-size: 1.5rem;'>✅ NORMAL OPERATION</h3>
                    <p style='font-size: 4rem; font-weight: bold; margin: 10px 0;'>{format_probability(probability)}</p>
                    <p style='margin: 0;'>RISK IS LOW</p>
                </div>
            """, unsafe_allow_html=True)
            st.success("System running within acceptable limits.")

        st.markdown("---")
        st.caption("Raw API Response:")
        st.json(result)
    else:
        st.info("Waiting for first prediction run... Adjust inputs and click the button!")

# Footer/Instructions
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1.  **Activate venv:** Ensure your virtual environment is active.
2.  **Run Docker:** The container must be running on **port 8080**.
3.  **Launch Streamlit:** Run `streamlit run app_streamlit.py`.
4.  **Test:** Adjust parameters and click **CHECK FAILURE RISK NOW** to see real-time predictions.
""")