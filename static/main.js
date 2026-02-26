/**
 * AntiGravity Dashboard Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const powerBtn = document.getElementById('power-btn');
    const powerText = document.getElementById('power-text');
    const powerIcon = document.getElementById('power-icon');
    const statusBadge = document.getElementById('status-badge');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    const terminalOutput = document.getElementById('terminal-output');
    const cycleCount = document.getElementById('cycle-count');
    const thresholdVal = document.getElementById('threshold-val');
    const activeCoinsDiv = document.getElementById('active-coins');
    const tradesContainer = document.getElementById('trades-container');

    let isRunning = false;
    let pollInterval = null;
    let lastLogCount = 0;

    // Conectar eventos
    powerBtn.addEventListener('click', toggleBot);

    // Initial check
    fetchStatus();

    async function toggleBot() {
        // Optimistic UI update
        powerBtn.disabled = true;

        const endpoint = isRunning ? '/api/bot/stop' : '/api/bot/start';

        try {
            const res = await fetch(endpoint, { method: 'POST' });
            const data = await res.json();

            if (res.ok) {
                // Fetch will catch the state change in the next tick
                setTimeout(fetchStatus, 500);
            } else {
                addLogLine(`[WEB API] Error: ${data.message}`, 'error');
            }
        } catch (error) {
            addLogLine(`[WEB API] Fallo al conectar con backend: ${error}`, 'error');
        } finally {
            powerBtn.disabled = false;
        }
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/api/bot/status');
            const data = await res.json();

            updateState(data);

            // Si está corriendo y no estamos polling, empezamos a hacerlo
            if (data.status === 'running' && !pollInterval) {
                pollInterval = setInterval(fetchStatus, 1500); // 1.5s refresh rate
            }
            // Si está detenido y estábamos polling, paramos
            else if (data.status === 'stopped' && pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }

        } catch (error) {
            console.error("Error fetching status:", error);
            // Si el backend muere, asumimos detenido y paramos polling
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
            updateState({ status: 'stopped' });
        }
    }

    function updateState(data) {
        // 1. Update Power Button & Status
        isRunning = (data.status === 'running');

        if (isRunning) {
            powerText.innerText = "STOP ENGINE";
            powerIcon.innerHTML = '<i class="fa-solid fa-stop"></i>';
            powerBtn.className = "group relative px-6 py-2 bg-cyber-panel border-2 border-cyber-red text-cyber-red font-bold tracking-widest rounded transition-all duration-300 hover:bg-cyber-red hover:text-white hover:shadow-[0_0_15px_rgba(255,0,85,0.5)]";

            statusBadge.classList.add('status-live');
            statusDot.className = "w-2 h-2 rounded-full bg-cyber-green";
            statusText.innerText = "STATUS: SCANNING";
            statusText.classList.replace('text-gray-500', 'text-cyber-green');
        } else {
            powerText.innerText = "START ENGINE";
            powerIcon.innerHTML = '<i class="fa-solid fa-power-off"></i>';
            powerBtn.className = "group relative px-6 py-2 bg-cyber-panel border-2 border-cyber-accent text-cyber-accent font-bold tracking-widest rounded transition-all duration-300 hover:bg-cyber-accent hover:text-black hover:shadow-[0_0_15px_rgba(0,240,255,0.5)]";

            statusBadge.classList.remove('status-live');
            statusDot.className = "w-2 h-2 rounded-full bg-gray-500";
            statusText.innerText = "STATUS: OFFLINE";
            statusText.classList.replace('text-cyber-green', 'text-gray-500');
        }

        if (!data.config) return;

        // 2. Update Telemetry
        cycleCount.innerText = String(data.cycle).padStart(3, '0');
        thresholdVal.innerText = `${data.config.threshold}%`;

        if (activeCoinsDiv.children.length !== data.config.coins.length) {
            activeCoinsDiv.innerHTML = data.config.coins.map(
                c => `<span class="px-2 py-1 bg-cyber-border text-[10px] font-bold tracking-widest uppercase rounded text-[#8abcff]">${c}</span>`
            ).join('');
        }

        // 3. Render Trades (Ledger)
        if (data.recent_trades && data.recent_trades.length > 0) {
            renderTrades(data.recent_trades);
        }

        // 4. Update Terminal Logs
        if (data.logs && data.logs.length > 0) {
            // Un poco rústico, pero si el array creció o es diferente, re-renderizamos
            if (data.logs.length !== lastLogCount || JSON.stringify(data.logs).length > 100) {
                renderLogs(data.logs);
                lastLogCount = data.logs.length;
            }
        }
    }

    function renderTrades(trades) {
        let html = '';
        trades.forEach(t => {
            const isWin = t.net_profit_usd > 0;
            const fgcolor = isWin ? 'text-cyber-green' : 'text-cyber-red';
            const bgcolor = isWin ? 'bg-cyber-green/10 border-cyber-green/30' : 'bg-cyber-red/10 border-cyber-red/30';
            const sign = isWin ? '+' : '';

            html += `
                <div class="p-3 border rounded ${bgcolor} flex flex-col gap-2">
                    <div class="flex justify-between items-center">
                        <span class="font-bold text-white uppercase">${t.coin}</span>
                        <span class="${fgcolor} font-bold text-sm">${sign}$${t.net_profit_usd.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between text-gray-400 text-[10px]">
                        <span>Buy: ${t.buy_exchange} @ $${t.buy_price.toFixed(2)}</span>
                        <span>Sell: ${t.sell_exchange} @ $${t.sell_price.toFixed(2)}</span>
                    </div>
                    <div class="text-right text-gray-500 text-[9px]">${t.timestamp}</div>
                </div>
            `;
        });
        tradesContainer.innerHTML = html;
    }

    function renderLogs(lines) {
        let html = '';
        lines.forEach(line => {
            // Saltar lineas decorativas o vacías
            if (!line.trim() || line.includes('─────────────────────')) return;

            let colorCls = 'log-info';
            if (line.includes('ERROR')) colorCls = 'log-error';
            else if (line.includes('WARNING') || line.includes('⚠️')) colorCls = 'log-warn';
            else if (line.includes('OPORTUNIDAD DETECTADA') || line.includes('VIABLE')) colorCls = 'log-opportunity';
            else if (line.includes('CICLO #')) colorCls = 'log-cycle';

            // Extraer solo del texto hacia adelante si tiene timestamp
            let text = line;
            html += `<div class="log-line ${colorCls}">${text}</div>`;
        });

        terminalOutput.innerHTML = html;
        // Scroll to bottom
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function addLogLine(text, type = 'info') {
        const div = document.createElement('div');
        div.className = `log-line log-${type}`;
        div.innerText = text;
        terminalOutput.appendChild(div);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
});
