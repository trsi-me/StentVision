/**
 * StentVision - البرنامج الرئيسي للواجهة
 * Vanilla JavaScript فقط
 */

const STATUS_LABELS = {
    normal: 'طبيعي',
    warning: 'تحذير',
    critical: 'حرج'
};

function updateTopCards(readings) {
    if (!readings || readings.length === 0) return;
    const latest = readings[readings.length - 1];
    document.getElementById('flow-rate').textContent = latest.flow_rate ?? '--';
    document.getElementById('p1').textContent = latest.p1 ?? '--';
    document.getElementById('p2').textContent = latest.p2 ?? '--';
    document.getElementById('delta-p').textContent = latest.delta_p ?? '--';
}

function updateRiskGauge(risk) {
    const gaugeFill = document.getElementById('gauge-fill');
    const gaugeValue = document.getElementById('gauge-value');
    const riskStatus = document.getElementById('risk-status');
    const riskDesc = document.getElementById('risk-description');

    if (!gaugeFill || !risk) return;

    const score = risk.risk_score || 0;
    gaugeFill.style.height = Math.min(score, 100) + '%';
    gaugeFill.classList.remove('warning', 'critical');
    if (risk.status === 'warning') gaugeFill.classList.add('warning');
    else if (risk.status === 'critical') gaugeFill.classList.add('critical');

    if (gaugeValue) gaugeValue.textContent = score.toFixed(1) + '%';
    if (riskStatus) {
        riskStatus.textContent = STATUS_LABELS[risk.status] || risk.status;
        riskStatus.className = 'risk-status ' + (risk.status || 'normal');
    }
    if (riskDesc) riskDesc.textContent = risk.description || '';
}

function drawSimpleChart(canvasId, data, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length === 0) return;

    const parent = canvas.parentElement;
    const w = parent ? parent.clientWidth : 0;
    if (w <= 0) return;

    const ctx = canvas.getContext('2d');
    canvas.width = w;
    const h = canvas.height = 150;
    const padding = 20;
    const chartW = w - padding * 2;
    const chartH = h - padding * 2;

    const values = data.map(d => parseFloat(d.value));
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = max - min || 1;
    const step = values.length > 1 ? (values.length - 1) : 1;

    ctx.clearRect(0, 0, w, h);
    ctx.beginPath();
    ctx.strokeStyle = color || '#3182ce';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';

    if (values.length === 1) {
        const x = padding + chartW / 2;
        const y = h - padding - ((values[0] - min) / range) * chartH;
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = color || '#3182ce';
        ctx.fill();
    } else {
        values.forEach((v, i) => {
            const x = padding + (i / step) * chartW;
            const y = h - padding - ((v - min) / range) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }
}

function loadDashboard() {
    fetch('/api/readings/latest')
        .then(r => r.json())
        .then(updateTopCards);

    fetch('/api/risk/current')
        .then(r => r.json())
        .then(updateRiskGauge);

    fetch('/api/chart/flow')
        .then(r => r.json())
        .then(data => drawSimpleChart('flow-chart', data, '#3182ce'));

    fetch('/api/chart/pressure')
        .then(r => r.json())
        .then(data => drawSimpleChart('pressure-chart', data, '#2b6cb0'));

    fetch('/api/chart/risk')
        .then(r => r.json())
        .then(data => drawSimpleChart('risk-chart', data, '#e53e3e'));

    fetch('/api/alerts')
        .then(r => r.json())
        .then(alerts => {
            const tbody = document.getElementById('alerts-body');
            if (!tbody) return;
            tbody.innerHTML = '';
            alerts.slice(0, 10).forEach(a => {
                const tr = document.createElement('tr');
                const sev = a.severity === 'high' ? 'عالي' : a.severity === 'medium' ? 'متوسط' : 'منخفض';
                tr.innerHTML = `
                    <td>${a.created_at || '--'}</td>
                    <td class="severity-${a.severity}">${sev}</td>
                    <td>${a.description || '--'}</td>
                    <td>${a.action || '--'}</td>
                `;
                tbody.appendChild(tr);
            });
            if (alerts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">لا توجد تنبيهات</td></tr>';
            }
        });
}

function simulateReading() {
    const flow = 70 + Math.random() * 35;
    const p1 = 115 + Math.random() * 20;
    const delta = 15 + Math.random() * 40;
    const p2 = p1 - delta;

    fetch('/api/reading/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            flow_rate: Math.round(flow * 10) / 10,
            p1: Math.round(p1 * 10) / 10,
            p2: Math.round(p2 * 10) / 10,
            delta_p: Math.round(delta * 10) / 10
        })
    })
        .then(r => r.json())
        .then(result => {
            updateRiskGauge(result);
            loadDashboard();
        });
}

document.addEventListener('DOMContentLoaded', function() {
    const simulateBtn = document.getElementById('simulate-btn');
    if (simulateBtn) {
        simulateBtn.addEventListener('click', simulateReading);
    }

    if (document.getElementById('alerts-body') !== null) {
        requestAnimationFrame(function() {
            loadDashboard();
            setInterval(loadDashboard, 5000);
        });
    }
});
