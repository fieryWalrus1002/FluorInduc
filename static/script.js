
let lastStatus = "";

async function startTask() {
    const actinic = parseInt(document.getElementById("actinic_led_intensity").value || 50);
    const measurement = parseInt(document.getElementById("measurement_led_intensity").value || 50);
    const recordingHz = parseInt(document.getElementById("recording_hz").value || 1000);
    const aredDuration = parseFloat(document.getElementById("ared_duration_s").value || 3.0);
    const waitAfterAred = parseFloat(document.getElementById("wait_after_ared_s").value || 0.002);
    const agreenDelay = parseFloat(document.getElementById("agreen_delay_s").value || 0.002);
    const agreenDuration = parseFloat(document.getElementById("agreen_duration_s").value || 2.0);
    const channelRange = parseInt(document.getElementById("channel_range").value || 50);
    const filename = document.getElementById("filename").value || "record.csv";

    const payload = {
        actinic_led_intensity: actinic,
        measurement_led_intensity: measurement,
        recording_hz: recordingHz,
        ared_duration_s: aredDuration,
        wait_after_ared_s: waitAfterAred,
        agreen_delay_s: agreenDelay,
        agreen_duration_s: agreenDuration,
        channel_range: channelRange,
        filename: filename
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

async function resetDevice() {
    const response = await fetch('/reset_device', { method: 'POST' });
    const data = await response.json();
    alert(data.status);
    updateStatus();
}

async function updateStatus() {
    try {
        const response = await fetch('/device_status');
        const data = await response.json();
        const currentStatus = data.status;

        document.getElementById('status').innerText = "Status: " + currentStatus;

        if (data.last_result && currentStatus === "Idle") {
            document.getElementById('status').innerText += " — " + data.last_result;
        }

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

    // Plot signal
    const yMax = Math.max(...data.signal);
    const yRange = [0, yMax * 1.1];

    Plotly.newPlot('plot', [{
        x: data.time,
        y: data.signal,
        type: 'scatter',
        mode: 'lines',
        name: 'Signal'
    }], {
        title: filename,
        xaxis: { title: 'Time (s)' },
        yaxis: {
            title: 'Signal (V)',
            range: yRange
        }
    });

    document.getElementById('download_link').href = `/download_csv/${filename}`;

    // Load and display metadata
    await loadMetadata(filename);
}


async function loadMetadata(filename) {
    const response = await fetch(`/load_metadata/${filename}`);
    const result = await response.json();
    const metaElem = document.getElementById("metadata_pretty");
    console.log("Metadata response:", result);
    
    if (!response.ok) {
        // Server returned 404 or 500
        metaElem.textContent = `Error loading metadata: ${result.error || 'Unknown error'}`;
        return;
    }

    if (result.metadata) {
        const metadataText = result.metadata
            //.replace(/,/g, ',\n')  // Add newlines after commas for better readability

        metaElem.textContent = metadataText;
    } else {
        // response.ok but no metadata field (possible logic error or empty file)
        metaElem.textContent = result.error || 'No metadata found for this file.';
    }
}


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

// Initialize tooltips for Bootstrap
document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl)
    })
});

setInterval(updateStatus, 2000); // update status every 2 seconds

window.onload = function () {
    updateStatus();
    populateFileList();
    drawBlankPlot();  // Draw a blank plot on initial load
};

