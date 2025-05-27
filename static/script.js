
let lastStatus = "";

async function startTask() {
    const payload = {
        actinic_led_intensity: parseInt(document.getElementById("actinic_led_intensity").value || 50),
        measurement_led_intensity: parseInt(document.getElementById("measurement_led_intensity").value || 0),
        recording_length: parseInt(document.getElementById("recording_length").value || 10),
        shutter_state: document.getElementById("shutter_state").checked,
        filename: document.getElementById("filename").value || "record.csv",
        recording_hz: parseInt(document.getElementById("recording_hz").value || 1000)
    };

    const response = await fetch('/start_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    alert(data.status);
    updateStatus();
}

async function cancelTask() {
    const response = await fetch('/cancel_task', { method: 'POST' });
    const data = await response.json();
    alert(data.status);
    updateStatus();
}

// async function updateStatus() {
//     const response = await fetch('/device_status');
//     const data = await response.json();
//     document.getElementById('status').innerText = "Status: " + data.status;
// }

async function updateStatus() {
    try {
        const response = await fetch('/device_status');
        const data = await response.json();
        const currentStatus = data.status;

        document.getElementById('status').innerText = "Status: " + currentStatus;

        if (lastStatus === "Running" && currentStatus === "Idle") {
            console.log("Task finished, refreshing file list...");
            await populateFileList();
        }

        lastStatus = currentStatus;
    } catch (err) {
        console.error("Failed to fetch device status:", err);
    }
}

async function populateFileList() {
    const response = await fetch('/list_csv_files');
    const files = await response.json();
    const select = document.getElementById('file_select');
    select.innerHTML = files.map(f => `<option value="${f}">${f}</option>`).join('');
}

async function loadPlot() {
    const filename = document.getElementById("file_select").value;
    if (!filename) return;

    const response = await fetch(`/load_csv/${filename}`);
    const data = await response.json();

    Plotly.newPlot('plot', [{
        x: data.time,
        y: data.signal,
        type: 'scatter',
        mode: 'lines',
        name: 'Signal'
    }], {
        title: filename,
        xaxis: { title: 'time' },
        yaxis: { title: 'signal' }
    });

    document.getElementById('download_link').href = `/download_csv/${filename}`;
}

setInterval(updateStatus, 2000);
window.onload = function () {
    updateStatus();
    populateFileList();
};


function drawBlankPlot() {
    Plotly.newPlot('plot', [{
        x: [],
        y: [],
        type: 'scatter'
    }], {
        title: 'No Data',
        xaxis: { title: 'time' },
        yaxis: { title: 'signal' }
    });
}

window.onload = function () {
    updateStatus();
    populateFileList();
    drawBlankPlot();  // Draw a blank plot on initial load
};

async function deleteSelectedFile() {
    const filename = document.getElementById("file_select").value;
    if (!filename) {
        alert("Please select a file to delete.");
        return;
    }

    const confirmed = confirm(`Are you sure you want to delete "${filename}"?`);
    if (!confirmed) return;

    const response = await fetch(`/delete_csv/${filename}`, {
        method: "DELETE"
    });

    const result = await response.json();

    if (response.ok) {
        alert(result.status);
        populateFileList();  // refresh the dropdown
        Plotly.purge('plot');  // clear the plot
        document.getElementById('download_link').href = '#';  // reset download
        drawBlankPlot();  // draw a blank plot
    } else {
        alert(`Error: ${result.error}`);
    }
}

