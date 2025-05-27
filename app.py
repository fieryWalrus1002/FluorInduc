from flask import Flask, render_template, jsonify, request
import os
import threading
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.io_controller import IOController

app = Flask(__name__)
controller = IOController()
task_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_task', methods=['POST'])
def start_task():
    global task_thread
    if task_thread and task_thread.is_alive():
        return jsonify({"status": "Task already running."})

    # Extract user-provided parameters (defaults if not provided)
    data = request.get_json()
    measurement_led_intensity = data.get("measurement_led_intensity", 50)
    actinic_led_intensity = data.get("actinic_led_intensity", 50)
    recording_length = data.get("recording_length", 10)
    shutter_state = data.get("shutter_state", False)

    def run():
        try:
            result = controller.run_task(
                actinic_led_intensity=actinic_led_intensity,
                measurement_led_intensity=measurement_led_intensity,
                recording_length=recording_length,
                shutter_state=shutter_state
            )
            print(f"Task finished with result: {result}")
        except Exception as e:
            print(f"Error running task: {e}")

    task_thread = threading.Thread(target=run)
    task_thread.start()
    return jsonify({"status": "Task started."})

@app.route('/cancel_task', methods=['POST'])
def cancel_task():
    global task_thread
    if not task_thread or not task_thread.is_alive():
        return jsonify({"status": "No running task to cancel."})

    controller.cancel_task()
    task_thread.join()  # Wait for the thread to actually terminate
    return jsonify({"status": "Task canceled."})

@app.route("/device_status", methods=["GET"])
def device_status():
    global task_thread
    status = "Running" if task_thread and task_thread.is_alive() else "Idle"
    return jsonify({"status": status})

@app.route("/shutdown", methods=["POST"])
def shutdown():
    """Clean up the device and stop the Flask server."""
    try:
        controller.cancel_task()
        controller.cleanup()
        print("Device cleaned up.")
    
        return jsonify({"status": "Task canceled, device cleaned up."})
    except Exception as e:
        print(f"Error during shutdown: {e}")
        return jsonify({"status": "Error during shutdown."}), 500

if __name__ == '__main__':
    app.run(debug=False)
