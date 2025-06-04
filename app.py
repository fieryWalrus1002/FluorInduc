from flask import Flask, render_template, jsonify, request
import os
import threading
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.web_api import WebApiController
from src.experiment_config import ExperimentConfig
from flask import send_from_directory
import csv


app = Flask(__name__)
controller = WebApiController()  # Initialize the WebApiController
task_thread = None
last_result = None
app.config["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "data")


@app.route("/list_csv_files")
def list_csv_files():
    try:
        data_dir = app.config["DATA_DIR"]
        files = [
            f
            for f in os.listdir(data_dir)
            if f.endswith(".csv") and os.path.isfile(os.path.join(data_dir, f))
        ]

        # Sort files by modification time (newest first)
        files.sort(
            key=lambda f: os.path.getmtime(os.path.join(data_dir, f)), reverse=True
        )

        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_csv/<filename>", methods=["DELETE"])
def delete_csv(filename):
    try:
        file_path = os.path.join(app.config["DATA_DIR"], filename)

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404

        os.remove(file_path)
        return jsonify({"status": f"Deleted {filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/load_csv/<filename>")
def load_csv(filename):
    # f.write("time,signal\n")
    filepath = os.path.join(app.config["DATA_DIR"], filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    time_data = []
    signal_data = []
    try:
        with open(filepath, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                time_data.append(float(row.get("time", 0)))
                signal_data.append(float(row.get("signal", 0)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"time": time_data, "signal": signal_data})


@app.route("/download_csv/<filename>")
def download_csv(filename):
    return send_from_directory(app.config["DATA_DIR"], filename, as_attachment=True)

@app.route('/')
def index():
    return render_template('index.html')


@app.route("/start_task", methods=["POST"])
def start_task():
    global task_thread
    if task_thread and task_thread.is_alive():
        return jsonify({"status": "Task already running."})

    # Parse JSON and fill config object
    data = request.get_json()
    config = ExperimentConfig.from_dict(data)

    # Resolve full path for filename
    config.filename = os.path.join(app.config["DATA_DIR"], config.filename)

    def run():
        global last_result
        try:
            result = controller.run_task(config)
            last_result = result  # Store the result for later use
            if isinstance(result, str):
                print(f"Task finished with message: {result}")
        except Exception as e:
            last_result = f"Error: {str(e)}"
            print(f"Error running task: {e}")

    task_thread = threading.Thread(target=run)
    task_thread.start()
    return jsonify({"status": "Task started."})

@app.route('/cancel_task', methods=['POST'])
def cancel_task():
    global task_thread
    global last_result
    """Cancel the currently running task."""
    if not task_thread or not task_thread.is_alive():
        return jsonify({"status": "No running task to cancel."})

    controller.cancel_task()
    task_thread.join()  # Wait for the thread to actually terminate
    last_result = "Task canceled."
    return jsonify({"status": "Task canceled.", "last_result": last_result})

@app.route("/device_status", methods=["GET"])
def device_status():
    global task_thread
    global last_result
    """Check the status of the device and the current task."""
    status = "Running" if task_thread and task_thread.is_alive() else "Idle"
    return jsonify({"status": status, "last_result": last_result})

@app.route("/reset_device", methods=["POST"])
def reset_device():
    """Clean up the device without restarting the Flask server."""
    global last_result
    try:
        controller.cancel_task()
        controller.cleanup()
        last_result = "Device reset."
        return jsonify({"status": "Task canceled", "last_result": last_result})
    except Exception as e:
        print(f"Error during reset: {e}")
        last_result = f"Error during reset: {str(e)}"
        return jsonify({"status": "Error", "last_result": last_result}), 500

if __name__ == '__main__':
    app.run(debug=False)
