import random
import json
import psycopg2
from flask import Flask, render_template, jsonify, request

from ai_response import extract_ai_insight

app = Flask(__name__)

# Global state to track our machine simulation
machine_state = 'normal'
current_pressure = 280.0
current_temp = 42.0
current_vib = 1.8

def get_db_connection():
    """Connects to our local, air-gapped AlloyDB Omni instance."""
    try:
        return psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="omni", # The password you set in the docker run command
            host="127.0.0.1",
            port="5432"
        )
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

@app.route('/')
def index():
    # Serves the beautiful UI
    return render_template('dashboard.html')

@app.route('/api/control', methods=['POST'])
def control():
    """Endpoint for the UI to trigger anomalies."""
    global machine_state
    data = request.json
    machine_state = data.get('mode', 'normal')
    return jsonify({"status": "success", "mode": machine_state})

@app.route('/api/stream')
def stream():
    global current_pressure, current_temp, current_vib, machine_state
    
    # 1. Simulate the physics of the machine based on current mode
    if machine_state == 'normal':
        # Revert to baseline smoothly
        current_pressure = current_pressure * 0.9 + 280.0 * 0.1 + random.uniform(-2, 2)
        current_temp = current_temp * 0.9 + 42.0 * 0.1 + random.uniform(-0.5, 0.5)
        current_vib = current_vib * 0.9 + 1.8 * 0.1 + random.uniform(-0.1, 0.1)
    else: 
        # Simulate a catastrophic hydraulic seal rupture
        current_pressure -= random.uniform(2, 6)
        current_temp += random.uniform(1, 3)
        current_vib += random.uniform(0.5, 1.8)
    
    # Clamp values so they don't go into negative infinity
    current_pressure = max(0, current_pressure)
    current_vib = max(0, current_vib)
    
    insight = None
    insight_status = "idle"

    # 2. Threshold Detection -> Trigger AlloyDB AI!
    if current_pressure < 255 or current_vib > 4.5:
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                # We dynamically inject the live sensor readings into the prompt.
                prompt = f"Analyze this sensor data from a 1500T forging press: Pressure={current_pressure:.1f} bar, Vibration={current_vib:.1f} mm/s. Normal pressure is ~280 bar and normal vibration is ~2.0 mm/s. Does this indicate a hydraulic failure? Answer in one short sentence."

                # Execute the SQL that utilizes our internal ML-Agent.
                query = """
                SELECT google_ml.predict_row(
                    model_id => 'gemma4:e2b',
                    request_body => json_build_object(
                        'model', 'gemma4:e2b',
                        'prompt', %s,
                        'stream', false
                    )
                );
                """
                cur.execute(query, (prompt,))
                res = cur.fetchone()
                raw_prediction = res[0] if res else None
                insight = extract_ai_insight(raw_prediction)

                if insight:
                    insight_status = "ok"
                else:
                    # A successful SQL round trip is not proof that Gemma returned text.
                    insight = "Gemma returned an empty response. Sensor telemetry is still running."
                    insight_status = "unavailable"
            except Exception:
                # Keep detailed exceptions in server logs, not in the browser UI.
                app.logger.exception("Failed to obtain a Gemma insight from AlloyDB Omni")
                insight = "AI analysis failed. Sensor telemetry is still running; check the server logs."
                insight_status = "error"
            finally:
                conn.close()
        else:
            insight = "AlloyDB is unavailable. Sensor telemetry is still running without AI analysis."
            insight_status = "unavailable"

    # 3. Return telemetry independently of whether AI analysis succeeded.
    return jsonify({
        "pressure": current_pressure,
        "temperature": current_temp,
        "vibration": current_vib,
        "state": machine_state,
        "insight": insight,
        "insight_status": insight_status
    })

if __name__ == '__main__':
    print("🛡️ Starting Air-Gapped AI Dashboard on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
