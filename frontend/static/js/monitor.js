const logContainer = document.getElementById('log-container');
const statusBadge = document.getElementById('status');
const totalCountEl = document.getElementById('total-count');
const errorCountEl = document.getElementById('error-count');
const clearBtn = document.getElementById('clear-btn');

let totalLogs = 0;
let errorLogs = 0;

function updateStatus(connected) {
    if (connected) {
        statusBadge.textContent = 'Connected';
        statusBadge.className = 'px-4 py-2 rounded-full bg-green-900/50 text-green-400 text-sm font-medium border border-green-800';
    } else {
        statusBadge.textContent = 'Disconnected';
        statusBadge.className = 'px-4 py-2 rounded-full bg-red-900/50 text-red-400 text-sm font-medium border border-red-800';
    }
}

function addLogEntry(log) {
    if (totalLogs === 0) logContainer.innerHTML = '';
    
    totalLogs++;
    if (log.level.toUpperCase() === 'ERROR') errorLogs++;
    
    totalCountEl.textContent = totalLogs;
    errorCountEl.textContent = errorLogs;

    const entry = document.createElement('div');
    entry.className = 'log-entry p-2 rounded bg-gray-900/50 border-l-4 border-gray-700 hover:bg-gray-700/30';
    
    const levelClass = `level-${log.level.toLowerCase()}`;
    const timestamp = new Date(log.timestamp).toLocaleTimeString();

    entry.innerHTML = `
        <span class="text-gray-500">[${timestamp}]</span>
        <span class="font-bold ${levelClass} ml-2">${log.level.toUpperCase()}</span>
        <span class="text-blue-400 ml-2">@${log.source}</span>
        <span class="ml-2 text-gray-200">${log.message}</span>
    `;

    if (log.level.toUpperCase() === 'ERROR') {
        entry.style.borderColor = '#ef4444';
    } else if (log.level.toUpperCase() === 'WARNING') {
        entry.style.borderColor = '#f59e0b';
    } else {
        entry.style.borderColor = '#3b82f6';
    }

    logContainer.prepend(entry);
    
    // Visual flash effect for new logs
    entry.classList.add('bg-blue-900/20');
    setTimeout(() => entry.classList.remove('bg-blue-900/20'), 1000);

    // Keep only last 100 logs in view
    if (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Since everything is now on the same port, we just use the current host
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('Connected to log stream');
        updateStatus(true);
    };

    socket.onmessage = (event) => {
        const log = JSON.parse(event.data);
        addLogEntry(log);
    };

    socket.onclose = () => {
        console.log('Disconnected from log stream');
        updateStatus(false);
        setTimeout(connect, 3000); // Reconnect after 3 seconds
    };

    socket.onerror = (err) => {
        console.error('WebSocket error:', err);
        socket.close();
    };
}

clearBtn.onclick = () => {
    logContainer.innerHTML = '<div class="text-gray-500 italic">Waiting for logs...</div>';
    totalLogs = 0;
    errorLogs = 0;
    totalCountEl.textContent = '0';
    errorCountEl.textContent = '0';
};

// Fetch history on load
async function fetchHistory() {
    try {
        // Use relative path since we are on the same port
        const response = await fetch('/history');
        const logs = await response.json();
        logs.reverse().forEach(addLogEntry);
    } catch (err) {
        console.error('Failed to fetch history:', err);
    }
}

connect();
fetchHistory();
