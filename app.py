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

    def run():
        result = controller.run_task()
        print(f"Task finished with result: {result}")

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

@app.route('/task_status', methods=['GET'])
def task_status():
    global task_thread
    if task_thread and task_thread.is_alive():
        return jsonify({"status": "Running"})
    return jsonify({"status": "Idle"})



if __name__ == '__main__':
    app.run(debug=False)
