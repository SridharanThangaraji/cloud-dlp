const API_BASE = "http://127.0.0.1:8000";

async function uploadFile() {
    const input = document.getElementById("fileInput");
    const result = document.getElementById("result");

    if (input.files.length === 0) {
        alert("Please select a file to upload");
        return;
    }

    const formData = new FormData();
    formData.append("file", input.files[0]);

    result.innerText = "Uploading...";
    result.className = "result";

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.status === "BLOCKED") {
            result.innerText = `BLOCKED – Sensitive data detected (${data.reason.join(", ")})`;
            result.classList.add("blocked");
        } else {
            result.innerText = "ALLOWED – File uploaded successfully";
            result.classList.add("allowed");
        }

        loadLogs();
    } catch (error) {
        result.innerText = "Error connecting to server";
        result.classList.add("blocked");
    }
}

async function loadLogs() {
    const tbody = document.getElementById("logs");

    try {
        const response = await fetch(`${API_BASE}/logs`);
        const logs = await response.json();

        tbody.innerHTML = "";

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4">No logs available</td></tr>`;
            return;
        }

        logs.forEach(log => {
            const row = `
                <tr>
                    <td>${log.filename}</td>
                    <td>${log.status}</td>
                    <td>${log.reason}</td>
                    <td>${log.timestamp}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });

    } catch {
        tbody.innerHTML = `<tr><td colspan="4">Failed to load logs</td></tr>`;
    }
}

loadLogs();

