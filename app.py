import os
import random
import json
import psycopg2
from flask import Flask, render_template, jsonify, request

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
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "omni"), # The password you set in the docker run command
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=os.environ.get("DB_PORT", "5432")
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Expected a JSON object"}), 400
    mode = data.get('mode', 'normal')
    if mode not in ('normal', 'anomaly'):
        return jsonify({"status": "error", "message": "Invalid mode"}), 400
    machine_state = mode
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
    
    # 2. Threshold Detection -> Trigger AlloyDB AI!
    if current_pressure < 255 or current_vib > 4.5:
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                # We dynamically inject the live sensor readings into the prompt
                prompt = f"Analyze this sensor data from a 1500T forging press: Pressure={current_pressure:.1f} bar, Vibration={current_vib:.1f} mm/s. Normal pressure is ~280 bar and normal vibration is ~2.0 mm/s. Does this indicate a hydraulic failure? Answer in one short sentence."
                
                # Execute the exact SQL that utilizes our internal ML-Agent
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
                
                # Parse the response from Ollama (returned through AlloyDB)
                if res and res[0]:
                    try:
                        # The prediction returns a JSON blob, we extract the "response" text
                        parsed = res[0]
                        if isinstance(parsed, str):
                            parsed = json.loads(parsed)
                        insight = parsed.get('response', str(parsed))
                    except:
                        insight = str(res[0])
            except Exception as e:
                insight = f"Database AI Error: {e}"
            finally:
                conn.close()
        else:
            insight = "CRITICAL ANOMALY: (AlloyDB offline, cannot fetch Gemma insight)"

    # 3. Return the payload to the UI
    return jsonify({
        "pressure": current_pressure,
        "temperature": current_temp,
        "vibration": current_vib,
        "state": machine_state,
        "insight": insight
    })

if __name__ == '__main__':
    print("🛡️ Starting Air-Gapped AI Dashboard on port 5000")
    app.run(host=os.environ.get("FLASK_HOST", "127.0.0.1"), port=5000,
            debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
