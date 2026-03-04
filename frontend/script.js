const API_BASE = (typeof window !== "undefined" && window.location && window.location.origin && String(window.location.origin).startsWith("http")) ? "" : "http://127.0.0.1:8000";

const PAGE_META = {
    dashboard: { title: "Dashboard", desc: "Overview of uploads and stored assets" },
    upload: { title: "Upload", desc: "Scan for sensitive data, then encrypt and store" },
    assets: { title: "Assets", desc: "Stored encrypted files and integrity hashes" },
    logs: { title: "Audit Logs", desc: "History of all upload attempts" },
    about: { title: "About", desc: "Project overview, modules, and tech stack" },
    architecture: { title: "Architecture", desc: "System design and data flow" },
    policies: { title: "Policies", desc: "Active DLP detection rules" },
    settings: { title: "Settings", desc: "Server configuration (read-only)" },
};

// --- Toast ---
function toast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const el = document.createElement("div");
    el.className = "toast " + (type === "error" ? "error" : "success");
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
        el.remove();
    }, 3000);
}

// --- Navigation ---
function showPage(page) {
    const links = document.querySelectorAll(".nav-link[data-page]");
    const pages = document.querySelectorAll(".page[data-page]");
    const pageTitle = document.getElementById("pageTitle");
    const pageDesc = document.getElementById("pageDesc");
    const meta = PAGE_META[page] || {};
    pageTitle.textContent = meta.title || page;
    pageDesc.textContent = meta.desc || "";
    links.forEach((l) => l.classList.toggle("active", l.getAttribute("data-page") === page));
    pages.forEach((p) => {
        p.classList.toggle("active", p.getAttribute("data-page") === page);
    });
    if (page === "dashboard") loadStats();
    if (page === "assets") loadAssets();
    if (page === "logs") loadLogs();
    if (page === "policies") loadPolicies();
    if (page === "settings") loadSettings();
}

function initNav() {
    document.querySelectorAll(".nav-link[data-page]").forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            showPage(link.getAttribute("data-page"));
        });
    });
    document.querySelectorAll("[data-goto]").forEach((btn) => {
        btn.addEventListener("click", () => showPage(btn.getAttribute("data-goto")));
    });
}

// --- Health ---
async function checkHealth() {
    const dot = document.getElementById("healthDot");
    const label = document.getElementById("healthLabel");
    try {
        const r = await fetch(`${API_BASE}/health`, { method: "GET" });
        if (r.ok) {
            dot.className = "health-dot online";
            label.textContent = "Connected";
        } else {
            dot.className = "health-dot offline";
            label.textContent = "Error";
        }
    } catch {
        dot.className = "health-dot offline";
        label.textContent = "Offline";
    }
}

// --- Dashboard stats ---
const CHART_MAX_HEIGHT = 120;

async function loadStats() {
    const els = {
        total: document.getElementById("statTotal"),
        allowed: document.getElementById("statAllowed"),
        blocked: document.getElementById("statBlocked"),
        errors: document.getElementById("statErrors"),
        assets: document.getElementById("statAssets"),
    };
    try {
        const r = await fetch(`${API_BASE}/stats`);
        if (!r.ok) throw new Error();
        const s = await r.json();
        els.total.textContent = s.total_uploads ?? "—";
        els.allowed.textContent = s.allowed ?? "—";
        els.blocked.textContent = s.blocked ?? "—";
        els.errors.textContent = s.errors ?? "—";
        els.assets.textContent = s.stored_assets ?? "—";
        updateChart(s);
    } catch {
        Object.values(els).forEach((el) => { if (el) el.textContent = "—"; });
        updateChart(null);
    }
}

function updateChart(stats) {
    const barAllowed = document.getElementById("barAllowed");
    const barBlocked = document.getElementById("barBlocked");
    const barErrors = document.getElementById("barErrors");
    if (!barAllowed || !barBlocked || !barErrors) return;
    const total = stats && stats.total_uploads > 0 ? stats.total_uploads : 0;
    if (total === 0) {
        barAllowed.style.height = barBlocked.style.height = barErrors.style.height = "8px";
        return;
    }
    const pct = (v) => Math.max(8, Math.round((v / total) * CHART_MAX_HEIGHT));
    barAllowed.style.height = pct(stats.allowed) + "px";
    barBlocked.style.height = pct(stats.blocked) + "px";
    barErrors.style.height = pct(stats.errors) + "px";
}

// --- Upload ---
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileNameDisplay");
const dropZone = document.getElementById("dropZone");
const uploadResult = document.getElementById("uploadResult");
const btnUpload = document.getElementById("btnUpload");

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        fileNameDisplay.textContent = e.target.files[0].name;
        fileNameDisplay.style.color = "var(--primary)";
    }
});

["dragenter", "dragover", "dragleave", "drop"].forEach((ev) => {
    dropZone.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); });
});
["dragenter", "dragover"].forEach((ev) => {
    dropZone.addEventListener(ev, () => dropZone.classList.add("dragover"));
});
["dragleave", "drop"].forEach((ev) => {
    dropZone.addEventListener(ev, () => dropZone.classList.remove("dragover"));
});
dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    fileInput.files = files;
    if (files.length > 0) {
        fileNameDisplay.textContent = files[0].name;
        fileNameDisplay.style.color = "var(--primary)";
    }
});

async function uploadFile() {
    if (fileInput.files.length === 0) {
        toast("Please select a file", "error");
        return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    btnUpload.disabled = true;
    uploadResult.textContent = "Scanning…";
    uploadResult.className = "result visible";
    uploadResult.style.color = "var(--text-dim)";

    try {
        const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        uploadResult.classList.remove("allowed", "blocked", "error");

        if (!response.ok) {
            const msg = getErrorMsg(data, response);
            uploadResult.textContent = "Error – " + msg;
            uploadResult.className = "result visible error";
            loadLogs();
            loadStats();
            return;
        }

        if (data.status === "BLOCKED") {
            const reason = arrayOrString(data.reason);
            uploadResult.innerHTML = "Blocked – sensitive data: " + escapeHtml(reason);
            uploadResult.className = "result visible blocked";
        } else if (data.status === "ERROR") {
            uploadResult.textContent = "Error – " + arrayOrString(data.reason);
            uploadResult.className = "result visible error";
        } else {
            uploadResult.innerHTML =
                "Encrypted and stored." +
                (data.file_hash
                    ? '<div class="hash-display">Hash: ' + escapeHtml(data.file_hash) + "</div>"
                    : "");
            uploadResult.className = "result visible allowed";
            toast("File stored successfully");
            fileInput.value = "";
            fileNameDisplay.textContent = "Click or drag file to scan";
            fileNameDisplay.style.color = "";
            loadAssets();
            loadStats();
        }
        loadLogs();
    } catch {
        uploadResult.textContent = "Connection error. Is the backend running?";
        uploadResult.className = "result visible error";
        toast("Connection failed", "error");
    } finally {
        btnUpload.disabled = false;
    }
}

btnUpload.addEventListener("click", uploadFile);

// --- Demo uploads ---
const DEMO_SAFE = "This is a safe document with no sensitive information.\nIt can be stored after scanning.";
const DEMO_SENSITIVE = "Contact: john@example.com\nPhone: 9876543210\nPassword: mySecret123";

function uploadDemo(content, filename) {
    const file = new File([content], filename, { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", file);
    fileNameDisplay.textContent = filename;
    fileNameDisplay.style.color = "var(--primary)";
    btnUpload.disabled = true;
    uploadResult.textContent = "Scanning…";
    uploadResult.className = "result visible";
    uploadResult.style.color = "var(--text-dim)";
    fetch(`${API_BASE}/upload`, { method: "POST", body: formData })
        .then((r) => r.json().catch(() => ({})))
        .then((data) => {
            uploadResult.classList.remove("allowed", "blocked", "error");
            if (data.status === "BLOCKED") {
                uploadResult.innerHTML = "Blocked – sensitive data: " + escapeHtml(arrayOrString(data.reason));
                uploadResult.className = "result visible blocked";
            } else if (data.status === "ERROR") {
                uploadResult.textContent = "Error – " + arrayOrString(data.reason);
                uploadResult.className = "result visible error";
            } else {
                uploadResult.innerHTML = "Encrypted and stored." + (data.file_hash ? '<div class="hash-display">Hash: ' + escapeHtml(data.file_hash) + "</div>" : "");
                uploadResult.className = "result visible allowed";
                toast("File stored successfully");
                loadAssets();
            }
            loadStats();
            loadLogs();
        })
        .catch(() => {
            uploadResult.textContent = "Connection error.";
            uploadResult.className = "result visible error";
        })
        .finally(() => { btnUpload.disabled = false; });
}

document.getElementById("demoSafe").addEventListener("click", () => uploadDemo(DEMO_SAFE, "demo_safe.txt"));
document.getElementById("demoSensitive").addEventListener("click", () => uploadDemo(DEMO_SENSITIVE, "demo_sensitive.txt"));

// --- Policies ---
async function loadPolicies() {
    const el = document.getElementById("policiesList");
    if (!el) return;
    try {
        const r = await fetch(`${API_BASE}/policies`);
        if (!r.ok) throw new Error();
        const policies = await r.json();
        const names = Object.keys(policies);
        if (names.length === 0) {
            el.innerHTML = "<p class=\"muted\">No policies configured.</p>";
            return;
        }
        el.innerHTML = names.map((name) =>
            "<div class=\"policy-item\"><div class=\"policy-name\">" + escapeHtml(name) + "</div><div class=\"policy-pattern\">" + escapeHtml(policies[name]) + "</div></div>"
        ).join("");
    } catch {
        el.innerHTML = "<p class=\"muted\">Failed to load policies. Is the backend running?</p>";
    }
}
document.getElementById("refreshPolicies").addEventListener("click", () => loadPolicies());

// --- Settings ---
async function loadSettings() {
    const el = document.getElementById("settingsContent");
    if (!el) return;
    try {
        const r = await fetch(`${API_BASE}/config`);
        if (!r.ok) throw new Error();
        const c = await r.json();
        el.innerHTML =
            "<div class=\"settings-row\"><label>Max file size</label><span>" + (c.max_file_size_mb ?? "—") + " MB</span></div>" +
            "<div class=\"settings-row\"><label>Allowed MIME types</label><span>" + escapeHtml((c.allowed_mime_types || []).join(", ")) + "</span></div>" +
            "<div class=\"settings-row\"><label>API version</label><span>" + escapeHtml(c.version || "—") + "</span></div>";
    } catch {
        el.innerHTML = "<p class=\"muted\">Failed to load config.</p>";
    }
}

// --- Footer version ---
async function setFooterVersion() {
    const el = document.getElementById("footerVersion");
    if (!el) return;
    try {
        const r = await fetch(`${API_BASE}/config`);
        if (r.ok) {
            const c = await r.json();
            el.textContent = "v" + (c.version || "—");
        }
    } catch {
        el.textContent = "—";
    }
}

function getErrorMsg(data, response) {
    if (data.detail == null) return response.statusText;
    if (Array.isArray(data.detail.reason)) return data.detail.reason.join(", ");
    if (typeof data.detail.reason === "string") return data.detail.reason;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail.map((e) => e.msg).join("; ");
    if (typeof data.detail === "string") return data.detail;
    return response.statusText;
}

function arrayOrString(v) {
    return Array.isArray(v) ? v.join(", ") : String(v ?? "");
}

function escapeHtml(str) {
    if (str == null) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

// --- Assets ---
let allAssets = [];

async function loadAssets() {
    const tbody = document.getElementById("assetsBody");
    const emptyEl = document.getElementById("assetsEmpty");
    const tableWrap = tbody && tbody.closest(".table-container");
    try {
        const response = await fetch(`${API_BASE}/assets`);
        const assets = await response.json().catch(() => []);
        const list = Array.isArray(assets) ? assets : [];
        allAssets = list;

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="4" class="muted">Failed to load (' + response.status + ")</td></tr>";
            if (emptyEl) emptyEl.style.display = "none";
            if (tableWrap) tableWrap.style.display = "block";
            return;
        }

        renderAssetsFiltered();
    } catch {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">Failed to load assets</td></tr>';
        if (emptyEl) emptyEl.style.display = "none";
    }
}

async function verifyAsset(id) {
    const el = document.getElementById("verify-" + id);
    if (!el) return;
    el.textContent = "…";
    el.className = "verify-result";
    try {
        const response = await fetch(`${API_BASE}/assets/${id}/verify`);
        const data = await response.json().catch(() => ({}));
        if (data.verified) {
            el.textContent = "✓ OK";
            el.className = "verify-result verify-ok";
        } else {
            el.textContent = data.reason || "Mismatch";
            el.className = "verify-result verify-fail";
        }
    } catch {
        el.textContent = "Error";
        el.className = "verify-result verify-fail";
    }
}

async function deleteAsset(id, filename) {
    if (!confirm('Delete stored asset "' + filename + '"? This cannot be undone.')) return;
    try {
        const r = await fetch(`${API_BASE}/assets/${id}`, { method: "DELETE" });
        if (r.ok) {
            toast("Asset deleted");
            loadAssets();
            loadStats();
        } else {
            const d = await r.json().catch(() => ({}));
            toast(d.detail || "Delete failed", "error");
        }
    } catch {
        toast("Delete failed", "error");
    }
}

document.getElementById("refreshAssets").addEventListener("click", () => loadAssets());

function renderAssetsFiltered() {
    const tbody = document.getElementById("assetsBody");
    const emptyEl = document.getElementById("assetsEmpty");
    const tableWrap = tbody && tbody.closest(".table-container");
    const searchInput = document.getElementById("assetSearch");
    const term = searchInput ? searchInput.value.trim().toLowerCase() : "";

    const list = term
        ? allAssets.filter((a) => {
              const name = (a.filename || "").toLowerCase();
              const hash = (a.file_hash || "").toLowerCase();
              return name.includes(term) || hash.includes(term);
          })
        : allAssets.slice();

    if (!list.length) {
        tbody.innerHTML = "";
        if (tableWrap) tableWrap.style.display = allAssets.length ? "block" : "none";
        if (emptyEl) emptyEl.style.display = "block";
        if (allAssets.length && term) {
            tbody.innerHTML = '<tr><td colspan="4" class="muted">No assets match the search</td></tr>';
            if (tableWrap) tableWrap.style.display = "block";
        }
        return;
    }

    if (emptyEl) emptyEl.style.display = "none";
    if (tableWrap) tableWrap.style.display = "block";

    const fragment = document.createDocumentFragment();
    tbody.innerHTML = "";
    list.forEach((a) => {
        const tr = document.createElement("tr");
        const dateStr = a.created_at ? new Date(a.created_at).toLocaleString() : "—";
        const hashShort = (a.file_hash || "").slice(0, 12) + "…";
        tr.innerHTML =
            "<td>" + escapeHtml(a.filename) + "</td>" +
            '<td class="hash-cell"><code class="hash-code" data-hash="' + escapeHtml(a.file_hash || "") + '" title="' + escapeHtml(a.file_hash || "") + '">' + escapeHtml(hashShort) + "</code> <button type=\"button\" class=\"btn-sm btn-copy\" title=\"Copy hash\">Copy</button></td>" +
            "<td>" + escapeHtml(dateStr) + "</td>" +
            "<td class=\"actions-cell\">" +
            "<button type=\"button\" class=\"btn-sm\" data-verify-id=\"" + a.id + "\">Verify</button> " +
            "<span class=\"verify-result\" id=\"verify-" + a.id + "\"></span> " +
            "<button type=\"button\" class=\"btn-sm btn-danger\" data-delete-id=\"" + a.id + "\" data-filename=\"" + escapeHtml(a.filename) + "\">Delete</button>" +
            "</td>";
        tr.querySelector("[data-verify-id]").addEventListener("click", () => verifyAsset(a.id));
        tr.querySelector("[data-delete-id]").addEventListener("click", () => deleteAsset(a.id, a.filename));
        const copyBtn = tr.querySelector(".btn-copy");
        const hashCode = tr.querySelector(".hash-code");
        if (copyBtn && hashCode) {
            copyBtn.addEventListener("click", () => {
                const h = hashCode.getAttribute("data-hash");
                if (h && navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(h).then(() => toast("Hash copied"));
                }
            });
        }
        fragment.appendChild(tr);
    });
    tbody.appendChild(fragment);
}

// --- Logs ---
let allLogs = [];

async function loadLogs() {
    const tbody = document.getElementById("logsBody");
    const emptyEl = document.getElementById("logsEmpty");
    const tableWrap = tbody && tbody.closest(".table-container");
    const filter = document.getElementById("logFilter");
    try {
        const response = await fetch(`${API_BASE}/logs`);
        const data = await response.json().catch(() => []);
        allLogs = Array.isArray(data) ? data : [];

        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="4" class="muted">Failed to load (' + response.status + ")</td></tr>";
            if (emptyEl) emptyEl.style.display = "none";
            if (tableWrap) tableWrap.style.display = "block";
            return;
        }

        const statusFilter = filter ? filter.value : "";
        const list = statusFilter
            ? allLogs.filter((l) => (l.status || "").toUpperCase() === statusFilter)
            : allLogs.slice();

        if (list.length === 0) {
            tbody.innerHTML = "";
            if (tableWrap) tableWrap.style.display = allLogs.length === 0 ? "none" : "block";
            if (emptyEl) emptyEl.style.display = "block";
            if (allLogs.length > 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="muted">No logs match the filter</td></tr>';
                if (tableWrap) tableWrap.style.display = "block";
            }
            return;
        }

        if (emptyEl) emptyEl.style.display = "none";
        if (tableWrap) tableWrap.style.display = "block";

        const fragment = document.createDocumentFragment();
        list.slice().reverse().forEach((log) => {
            const status = log.status ?? "";
            const statusClass = "status-" + String(status).toLowerCase();
            const ts = log.timestamp != null ? new Date(log.timestamp) : new Date(NaN);
            const timeStr = Number.isNaN(ts.getTime()) ? "—" : ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const tr = document.createElement("tr");
            tr.innerHTML =
                "<td>" + escapeHtml(log.filename) + "</td>" +
                '<td><span class="status-badge ' + escapeHtml(statusClass) + '">' + escapeHtml(status) + "</span></td>" +
                "<td>" + escapeHtml(log.reason) + "</td>" +
                "<td>" + escapeHtml(timeStr) + "</td>";
            fragment.appendChild(tr);
        });
        tbody.innerHTML = "";
        tbody.appendChild(fragment);
    } catch {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">Failed to load logs</td></tr>';
        if (emptyEl) emptyEl.style.display = "none";
    }
}

document.getElementById("refreshLogs").addEventListener("click", () => loadLogs());
document.getElementById("exportLogsCsv").addEventListener("click", exportLogsCsv);
document.getElementById("logFilter").addEventListener("change", () => renderLogsFiltered());
const logSearchInput = document.getElementById("logSearch");
if (logSearchInput) {
    logSearchInput.addEventListener("input", () => renderLogsFiltered());
}

const assetSearchInput = document.getElementById("assetSearch");
if (assetSearchInput) {
    assetSearchInput.addEventListener("input", () => renderAssetsFiltered());
}

function exportLogsCsv() {
    if (!allLogs.length) {
        toast("No logs to export", "error");
        return;
    }
    const headers = ["filename", "status", "reason", "timestamp"];
    const rows = allLogs.map((l) => headers.map((h) => (l[h] != null ? String(l[h]) : "").replace(/"/g, '""')).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "cloud_dlp_audit_logs_" + new Date().toISOString().slice(0, 10) + ".csv";
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Logs exported as CSV");
}

function renderLogsFiltered() {
    if (!allLogs.length) return;
    const filter = document.getElementById("logFilter");
    const searchInput = document.getElementById("logSearch");
    const term = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const tbody = document.getElementById("logsBody");
    const statusFilter = filter ? filter.value : "";
    let list = statusFilter
        ? allLogs.filter((l) => (l.status || "").toUpperCase() === statusFilter)
        : allLogs.slice();

    if (term) {
        list = list.filter((log) => {
            const name = (log.filename || "").toLowerCase();
            const reason = (log.reason || "").toLowerCase();
            return name.includes(term) || reason.includes(term);
        });
    }
    tbody.innerHTML = "";
    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">No logs match the filter</td></tr>';
        return;
    }
    const fragment = document.createDocumentFragment();
    list.slice().reverse().forEach((log) => {
        const status = log.status ?? "";
        const statusClass = "status-" + String(status).toLowerCase();
        const ts = log.timestamp != null ? new Date(log.timestamp) : new Date(NaN);
        const timeStr = Number.isNaN(ts.getTime()) ? "—" : ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const tr = document.createElement("tr");
        tr.innerHTML =
            "<td>" + escapeHtml(log.filename) + "</td>" +
            '<td><span class="status-badge ' + escapeHtml(statusClass) + '">' + escapeHtml(status) + "</span></td>" +
            "<td>" + escapeHtml(log.reason) + "</td>" +
            "<td>" + escapeHtml(timeStr) + "</td>";
        fragment.appendChild(tr);
    });
    tbody.appendChild(fragment);
}

// --- Init ---
initNav();
checkHealth();
setInterval(checkHealth, 15000);
loadStats();
loadLogs();
setFooterVersion();

// PWA service worker registration (requires HTTPS in browsers on real devices)
if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(() => {
            // Ignore registration errors; app still works without offline support.
        });
    });
}

setInterval(() => {
    const logsPage = document.getElementById("page-logs");
    if (logsPage && logsPage.classList.contains("active")) loadLogs();
}, 10000);
