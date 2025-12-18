// Goldilocks V2 Dashboard Charts and Data

// Chart.js default config for dark theme
Chart.defaults.color = '#a1a1aa';
Chart.defaults.borderColor = '#27273a';

let bankrollChart = null;
let pnlChart = null;

// Fetch and display summary stats
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();

        // Bankroll
        const bankrollEl = document.getElementById('bankroll');
        bankrollEl.textContent = `$${data.bankroll.toFixed(2)}`;
        bankrollEl.className = `card-value ${data.bankroll >= 100 ? 'positive' : 'negative'}`;

        // Win Rate
        const winRateEl = document.getElementById('winRate');
        winRateEl.textContent = `${data.win_rate}%`;
        winRateEl.className = `card-value ${data.win_rate >= 52.4 ? 'positive' : data.win_rate >= 50 ? 'neutral' : 'negative'}`;

        document.getElementById('winLossCount').textContent = `${data.wins}W - ${data.losses}L`;

        // ROI
        const roiEl = document.getElementById('roi');
        roiEl.textContent = `${data.roi >= 0 ? '+' : ''}${data.roi}%`;
        roiEl.className = `card-value ${data.roi >= 0 ? 'positive' : 'negative'}`;

        document.getElementById('totalBets').textContent = `${data.total_bets} settled bets`;

        // Pending
        document.getElementById('pending').textContent = data.pending_bets;

        // Last updated
        document.getElementById('lastUpdated').textContent = `Updated: ${new Date().toLocaleString()}`;

    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

// Fetch and render bankroll chart
async function loadBankrollChart() {
    try {
        const response = await fetch('/api/bankroll-history');
        const data = await response.json();

        const labels = data.map(d => d.date || 'Start');
        const values = data.map(d => d.bankroll);

        const ctx = document.getElementById('bankrollChart').getContext('2d');

        if (bankrollChart) {
            bankrollChart.destroy();
        }

        bankrollChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Bankroll ($)',
                    data: values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1a1a2e',
                        borderColor: '#27273a',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => `$${context.raw.toFixed(2)}`
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        grid: {
                            color: '#27273a'
                        },
                        ticks: {
                            callback: (value) => `$${value}`
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading bankroll chart:', error);
    }
}

// Fetch and render daily P&L chart
async function loadPnlChart() {
    try {
        const response = await fetch('/api/daily-pnl');
        const data = await response.json();

        const labels = data.map(d => d.date);
        const values = data.map(d => d.pnl);
        const colors = values.map(v => v >= 0 ? '#22c55e' : '#ef4444');

        const ctx = document.getElementById('pnlChart').getContext('2d');

        if (pnlChart) {
            pnlChart.destroy();
        }

        pnlChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily P&L',
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#1a1a2e',
                        borderColor: '#27273a',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                const d = data[context.dataIndex];
                                return [
                                    `P&L: ${context.raw >= 0 ? '+' : ''}$${context.raw.toFixed(2)}`,
                                    `Record: ${d.wins}W - ${d.losses}L`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        grid: {
                            color: '#27273a'
                        },
                        ticks: {
                            callback: (value) => `${value >= 0 ? '+' : ''}$${value}`
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading P&L chart:', error);
    }
}

// Load tier breakdown table
async function loadTierTable() {
    try {
        const response = await fetch('/api/by-tier');
        const data = await response.json();

        const tbody = document.querySelector('#tierTable tbody');
        tbody.innerHTML = data.map(tier => {
            const winRateClass = tier.win_rate >= 55 ? 'high' : tier.win_rate >= 50 ? 'neutral' : 'low';
            return `
                <tr>
                    <td>${tier.tier}</td>
                    <td>${tier.wins}/${tier.total}</td>
                    <td class="win-rate ${winRateClass}">${tier.win_rate}%</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading tier table:', error);
    }
}

// Load date breakdown table
async function loadDateTable() {
    try {
        const response = await fetch('/api/by-date');
        const data = await response.json();

        const tbody = document.querySelector('#dateTable tbody');
        tbody.innerHTML = data.map(day => {
            const winRateClass = day.win_rate >= 55 ? 'high' : day.win_rate >= 50 ? 'neutral' : 'low';
            const dateStr = new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            return `
                <tr>
                    <td>${dateStr}</td>
                    <td>${day.wins}/${day.total}</td>
                    <td class="win-rate ${winRateClass}">${day.win_rate}%</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading date table:', error);
    }
}

// Load recent bets
async function loadRecentBets() {
    try {
        const response = await fetch('/api/recent-bets');
        const data = await response.json();

        const container = document.getElementById('recentBets');

        if (data.length === 0) {
            container.innerHTML = '<div class="loading">No bets yet</div>';
            return;
        }

        container.innerHTML = data.map(bet => {
            let icon = '⏳';
            if (bet.result === 'WON') icon = '✅';
            else if (bet.result === 'LOST') icon = '❌';
            else if (bet.result === 'VOIDED') icon = '🚫';

            const tierClass = bet.tier === 'GOLDEN' ? 'golden' : 'high-volatility';
            const resultClass = bet.result.toLowerCase();
            let actualStr = 'Pending';
            if (bet.result === 'VOIDED') actualStr = 'DNP/Voided';
            else if (bet.actual_pra !== null) actualStr = `Actual: ${bet.actual_pra}`;

            return `
                <div class="bet-row">
                    <div class="bet-icon">${icon}</div>
                    <div class="bet-info">
                        <div class="bet-player">${bet.player_name}</div>
                        <div class="bet-details">${bet.direction} ${bet.betting_line} | ${actualStr}</div>
                    </div>
                    <span class="bet-tier ${tierClass}">${bet.tier}</span>
                    <div class="bet-result ${resultClass}">${bet.result}</div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading recent bets:', error);
    }
}

// Load all data
async function loadDashboard() {
    await Promise.all([
        loadSummary(),
        loadBankrollChart(),
        loadPnlChart(),
        loadTierTable(),
        loadDateTable(),
        loadRecentBets()
    ]);
}

// Initial load
document.addEventListener('DOMContentLoaded', loadDashboard);

// Refresh every 5 minutes
setInterval(loadDashboard, 5 * 60 * 1000);
