async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
}

function setHealthBadge(status) {
    const badge = document.getElementById('healthBadge');
    badge.textContent = status;
    badge.className = 'badge';

    if (status === 'WARNING') {
        badge.classList.add('warning');
    } else if (status === 'CRITICAL') {
        badge.classList.add('critical');
    }
}

function setIoPill(id, isHealthy, healthyLabel, unhealthyLabel) {
    const pill = document.getElementById(id);
    pill.textContent = isHealthy ? healthyLabel : unhealthyLabel;
    pill.className = 'io-pill';
    pill.classList.add(isHealthy ? 'good' : 'bad');
}

function renderSnapshot(snapshot) {
    document.getElementById('lastUpdate').textContent = snapshot.timestamp;
    document.getElementById('motorStatus').textContent = snapshot.motor_status;
    document.getElementById('throughputRate').textContent = `${snapshot.throughput_rate} u/min`;
    document.getElementById('speedValue').textContent = `${snapshot.conveyor_speed} m/min`;
    document.getElementById('plcMode').textContent = snapshot.plc_mode;
    document.getElementById('currentValue').textContent = `${snapshot.current_draw} A`;
    document.getElementById('temperatureValue').textContent = `${snapshot.temperature} °C`;
    document.getElementById('loadValue').textContent = `${snapshot.load_pct}%`;
    document.getElementById('unitsValue').textContent = snapshot.total_units;
    document.getElementById('faultValue').textContent = snapshot.active_fault || 'None';
    document.getElementById('recommendation').textContent = snapshot.recommendation;
    document.getElementById('uptimeValue').textContent = `${snapshot.uptime_seconds}s`;
    document.getElementById('lineState').textContent = snapshot.line_state;
    document.getElementById('alarmCode').textContent = snapshot.alarm_code;
    document.getElementById('alarmStatus').textContent = snapshot.alarm_status;

    document.getElementById('jamCount').textContent = snapshot.fault_counts.JAM;
    document.getElementById('slowdownCount').textContent = snapshot.fault_counts.SLOWDOWN;
    document.getElementById('overloadCount').textContent = snapshot.fault_counts.OVERLOAD;
    document.getElementById('stopCount').textContent = snapshot.fault_counts.STOP;
    document.getElementById('loadBar').style.width = `${Math.min(snapshot.load_pct, 100)}%`;

    const sensors = snapshot.sensors || {};
    setIoPill('startPermissive', Boolean(sensors.start_permissive), 'READY', 'LOCKED');
    setIoPill('photoeyeState', Boolean(sensors.photoeye_clear), 'CLEAR', 'BLOCKED');
    setIoPill('driveReady', Boolean(sensors.drive_ready), 'READY', 'FAULTED');
    setIoPill('safetyCircuit', Boolean(sensors.safety_circuit), 'CLOSED', 'OPEN');

    setHealthBadge(snapshot.health_status);

    const alertsList = document.getElementById('alertsList');
    alertsList.innerHTML = '';
    snapshot.alerts.forEach((alertText) => {
        const li = document.createElement('li');
        li.textContent = alertText;
        alertsList.appendChild(li);
    });
}

function renderReport(report) {
    document.getElementById('samplesValue').textContent = report.samples;
    document.getElementById('availabilityValue').textContent = `${report.availability_pct}%`;
    document.getElementById('avgThroughputValue').textContent = `${report.avg_throughput} u/min`;
    document.getElementById('criticalEventsValue').textContent = report.critical_events;
    document.getElementById('peakTempValue').textContent = `${report.peak_temperature} °C`;
    document.getElementById('dominantFaultValue').textContent = report.dominant_fault;
}

function renderEvents(events) {
    const tbody = document.getElementById('eventsBody');
    tbody.innerHTML = '';

    if (!events.length) {
        tbody.innerHTML = '<tr><td colspan="4">No events logged.</td></tr>';
        return;
    }

    events.slice(0, 10).forEach((event) => {
        const row = document.createElement('tr');
        row.className = `severity-${String(event.severity || '').toLowerCase()}`;
        row.innerHTML = `
            <td>${event.timestamp}</td>
            <td>${event.event_type}</td>
            <td>${event.severity}</td>
            <td>${event.message}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderMetrics(metrics) {
    const tbody = document.getElementById('metricsBody');
    tbody.innerHTML = '';

    if (!metrics.length) {
        tbody.innerHTML = '<tr><td colspan="4">No metric history available.</td></tr>';
        return;
    }

    metrics.slice(-8).reverse().forEach((metric) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${metric.timestamp}</td>
            <td>${metric.throughput_rate}</td>
            <td>${metric.conveyor_speed}</td>
            <td>${metric.health_status}</td>
        `;
        tbody.appendChild(row);
    });
}

function drawTrend(metrics) {
    const canvas = document.getElementById('trendCanvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#08111f';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i += 1) {
        const y = (height / 5) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    if (!metrics.length) {
        return;
    }

    const values = metrics.map((item) => item.throughput_rate);
    const maxValue = Math.max(...values, 10);
    const padding = 28;

    ctx.strokeStyle = '#4cc9f0';
    ctx.lineWidth = 3;
    ctx.beginPath();

    values.forEach((value, index) => {
        const x = padding + (index * (width - padding * 2)) / Math.max(values.length - 1, 1);
        const y = height - padding - (value / maxValue) * (height - padding * 2);
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.stroke();

    ctx.fillStyle = '#9db1d1';
    ctx.font = '14px Segoe UI';
    ctx.fillText(`Peak: ${maxValue.toFixed(1)} u/min`, 16, 20);
}

async function refreshDashboard() {
    try {
        const [snapshot, history, report] = await Promise.all([
            fetchJson('/api/status'),
            fetchJson('/api/history'),
            fetchJson('/api/report')
        ]);

        renderSnapshot(snapshot);
        renderReport(report);
        renderEvents(history.events || []);
        renderMetrics(history.metrics || []);
        drawTrend(history.metrics || []);
    } catch (error) {
        console.error(error);
    }
}

async function sendControl(action) {
    try {
        await fetchJson('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        await refreshDashboard();
    } catch (error) {
        alert(`Control action failed: ${error.message}`);
    }
}

function downloadReport() {
    window.location.href = '/api/report.csv';
}

window.sendControl = sendControl;
window.downloadReport = downloadReport;
refreshDashboard();
setInterval(refreshDashboard, 1000);
