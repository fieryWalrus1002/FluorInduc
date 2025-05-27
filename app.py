from flask import Flask, render_template, jsonify, request
import os
import threading
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.io_controller import IOController
from src.experiment_config import ExperimentConfig
from flask import send_from_directory
import csv


app = Flask(__name__)
controller = IOController()
task_thread = None
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
        try:
            result = controller.run_task(config)
            print(
                f"Task finished with result: {result}, data saved to {config.filename}"
            )
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


# from flask import Flask, jsonify, request, send_from_directory
# import os
# import csv

# app = Flask(__name__)
# DATA_DIR = "./data"


# @app.route("/list_csv_files")
# def list_csv_files():
#     files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
#     return jsonify(files)


# @app.route("/load_csv/<filename>")
# def load_csv(filename):
#     filepath = os.path.join(DATA_DIR, filename)
#     time_data = []
#     signal_data = []
#     with open(filepath, newline="") as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             time_data.append(float(row["time"]))
#             signal_data.append(float(row["signal"]))
#     return jsonify({"time": time_data, "signal": signal_data})


# @app.route("/download_csv/<filename>")
# def download_csv(filename):
#     return send_from_directory(DATA_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=False)
