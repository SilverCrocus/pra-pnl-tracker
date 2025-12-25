// Goldilocks V2 Dashboard - Premium Theme
// Chart.js configuration and data management

// Chart.js theme configuration
Chart.defaults.color = '#71717a';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, sans-serif";

let bankrollChart = null;
let pnlChart = null;

// Store raw data for filtering
let rawSummaryData = null;
let rawBankrollHistory = [];
let rawDailyPnl = [];
let currentPeriod = 'all';

// Starting bankroll constant
const STARTING_BANKROLL = 100;

// Get date range for period filter
function getDateRange(period) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    switch (period) {
        case 'week':
            const weekStart = new Date(today);
            weekStart.setDate(today.getDate() - today.getDay()); // Start of week (Sunday)
            return { start: weekStart, end: now };
        case 'month':
            const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
            return { start: monthStart, end: now };
        case 'all':
        default:
            return { start: new Date(0), end: now };
    }
}

// Filter data by date range
function filterByPeriod(data, period, dateKey = 'date') {
    if (period === 'all') return data;

    const { start, end } = getDateRange(period);
    return data.filter(item => {
        if (!item[dateKey]) return period === 'all'; // Include start point for 'all'
        const itemDate = new Date(item[dateKey]);
        return itemDate >= start && itemDate <= end;
    });
}

// Calculate stats for a filtered period
function calculatePeriodStats(dailyPnl, period) {
    const filtered = filterByPeriod(dailyPnl, period);

    let wins = 0;
    let losses = 0;
    let totalPnl = 0;

    filtered.forEach(day => {
        wins += day.wins || 0;
        losses += day.losses || 0;
        totalPnl += day.pnl || 0;
    });

    const total = wins + losses;
    const winRate = total > 0 ? (wins / total * 100) : 0;

    return { wins, losses, total, winRate, totalPnl };
}

// Update display with period-specific data
function updateDisplayForPeriod(period) {
    currentPeriod = period;

    // Calculate period-specific stats
    const periodStats = calculatePeriodStats(rawDailyPnl, period);

    // Determine bankroll display based on period
    let displayBankroll, profitAmount, profitPercent;

    if (period === 'all') {
        displayBankroll = rawSummaryData?.bankroll || STARTING_BANKROLL;
        profitAmount = displayBankroll - STARTING_BANKROLL;
        profitPercent = ((displayBankroll - STARTING_BANKROLL) / STARTING_BANKROLL * 100);
    } else {
        // For week/month, show period P&L
        displayBankroll = rawSummaryData?.bankroll || STARTING_BANKROLL;
        profitAmount = periodStats.totalPnl;
        profitPercent = periodStats.total > 0
            ? (periodStats.totalPnl / (periodStats.total * 1) * 100) // Approximate ROI
            : 0;
    }

    // Update bankroll display
    const bankrollEl = document.getElementById('bankroll');
    bankrollEl.textContent = `$${displayBankroll.toFixed(2)}`;
    bankrollEl.className = `bankroll-value ${displayBankroll >= STARTING_BANKROLL ? 'positive' : 'negative'}`;

    // Update change indicator
    const changeEl = document.getElementById('bankrollChange');
    const isPositive = profitAmount >= 0;
    changeEl.className = `bankroll-change ${isPositive ? '' : 'negative'}`;
    changeEl.querySelector('.change-arrow').textContent = isPositive ? '↑' : '↓';
    changeEl.querySelector('.change-amount').textContent = `${isPositive ? '+' : ''}$${profitAmount.toFixed(2)}`;
    changeEl.querySelector('.change-percent').textContent = `(${isPositive ? '+' : ''}${profitPercent.toFixed(1)}%)`;

    // Update win rate
    const winRateEl = document.getElementById('winRate');
    winRateEl.textContent = `${periodStats.winRate.toFixed(1)}%`;
    winRateEl.className = `stat-pill-value ${periodStats.winRate >= 52.4 ? 'positive' : periodStats.winRate >= 50 ? '' : 'negative'}`;
    document.getElementById('winLossCount').textContent = `${periodStats.wins}W - ${periodStats.losses}L`;

    // Update ROI
    const roiEl = document.getElementById('roi');
    const roi = periodStats.total > 0 ? (periodStats.totalPnl / periodStats.total * 100) : 0;
    roiEl.textContent = `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`;
    roiEl.className = `stat-pill-value ${roi >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('totalBets').textContent = `${periodStats.total} bets`;

    // Update charts with filtered data
    updateBankrollChart(period);
    updatePnlChart(period);
}

// Fetch and store summary data
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        rawSummaryData = await response.json();

        // Initial display with all-time stats
        updateDisplayForPeriod('all');

        // Update last updated timestamp
        document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

// Load today's record
async function loadTodayStats() {
    try {
        const response = await fetch('/api/by-date?limit=1');
        const data = await response.json();

        const todayRecordEl = document.getElementById('todayRecord');
        const todayPnlEl = document.getElementById('todayPnl');

        if (data && data.length > 0) {
            const today = data[0];
            const todayDate = new Date().toISOString().split('T')[0];

            // Check if the most recent date is actually today
            if (today.date === todayDate) {
                todayRecordEl.textContent = `${today.wins}-${today.total - today.wins}`;

                // Calculate today's P&L from daily-pnl endpoint
                const pnlResponse = await fetch('/api/daily-pnl');
                const pnlData = await pnlResponse.json();
                const todayPnl = pnlData.find(d => d.date === todayDate);

                if (todayPnl) {
                    const pnl = todayPnl.pnl;
                    todayPnlEl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
                    todayPnlEl.style.color = pnl >= 0 ? '#10b981' : '#ef4444';
                } else {
                    todayPnlEl.textContent = '$0.00';
                }
            } else {
                todayRecordEl.textContent = '0-0';
                todayPnlEl.textContent = 'No bets';
            }
        } else {
            todayRecordEl.textContent = '0-0';
            todayPnlEl.textContent = 'No bets';
        }
    } catch (error) {
        console.error('Error loading today stats:', error);
        document.getElementById('todayRecord').textContent = '--';
        document.getElementById('todayPnl').textContent = '--';
    }
}

// Fetch and store bankroll history
async function loadBankrollHistory() {
    try {
        const response = await fetch('/api/bankroll-history');
        rawBankrollHistory = await response.json();
        updateBankrollChart('all');
    } catch (error) {
        console.error('Error loading bankroll history:', error);
    }
}

// Update bankroll chart with filtered data
function updateBankrollChart(period) {
    const filtered = period === 'all'
        ? rawBankrollHistory
        : filterByPeriod(rawBankrollHistory, period);

    // If filtering and we have data, prepend the starting point
    let chartData = filtered;
    if (period !== 'all' && filtered.length > 0 && filtered[0].date) {
        // Find the bankroll value just before the period start
        const { start } = getDateRange(period);
        let startingValue = STARTING_BANKROLL;

        for (const item of rawBankrollHistory) {
            if (!item.date) continue;
            const itemDate = new Date(item.date);
            if (itemDate < start) {
                startingValue = item.bankroll;
            } else {
                break;
            }
        }

        chartData = [{ date: null, bankroll: startingValue }, ...filtered];
    }

    const labels = chartData.map(d => {
        if (!d.date) return 'Start';
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const values = chartData.map(d => d.bankroll);

    const ctx = document.getElementById('bankrollChart').getContext('2d');

    if (bankrollChart) {
        bankrollChart.destroy();
    }

    // Determine if profit or loss for gradient color
    const lastValue = values[values.length - 1] || STARTING_BANKROLL;
    const isProfit = lastValue >= STARTING_BANKROLL;

    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    if (isProfit) {
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');
    } else {
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
    }

    bankrollChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Bankroll',
                data: values,
                borderColor: isProfit ? '#10b981' : '#ef4444',
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: isProfit ? '#10b981' : '#ef4444',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(12, 12, 20, 0.9)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    titleFont: {
                        size: 12,
                        weight: '600',
                    },
                    bodyFont: {
                        size: 14,
                        weight: '700',
                    },
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
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 8,
                        font: {
                            size: 11,
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.04)',
                    },
                    ticks: {
                        callback: (value) => `$${value}`,
                        font: {
                            size: 11,
                        }
                    }
                }
            }
        }
    });
}

// Fetch and store daily P&L
async function loadDailyPnl() {
    try {
        const response = await fetch('/api/daily-pnl');
        rawDailyPnl = await response.json();
        updatePnlChart('all');
    } catch (error) {
        console.error('Error loading daily P&L:', error);
    }
}

// Update P&L chart with filtered data
function updatePnlChart(period) {
    const filtered = filterByPeriod(rawDailyPnl, period);

    const labels = filtered.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const values = filtered.map(d => d.pnl);
    const colors = values.map(v => v >= 0 ? '#10b981' : '#ef4444');
    const borderColors = values.map(v => v >= 0 ? '#059669' : '#dc2626');

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
                borderColor: borderColors,
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(12, 12, 20, 0.9)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    titleFont: {
                        size: 12,
                        weight: '600',
                    },
                    bodyFont: {
                        size: 14,
                        weight: '700',
                    },
                    callbacks: {
                        label: (context) => {
                            const d = filtered[context.dataIndex];
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
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 8,
                        font: {
                            size: 11,
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.04)',
                    },
                    ticks: {
                        callback: (value) => `${value >= 0 ? '+' : ''}$${value}`,
                        font: {
                            size: 11,
                        }
                    }
                }
            }
        }
    });
}

// Setup period toggle buttons
function setupPeriodToggles() {
    const buttons = document.querySelectorAll('.period-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update display
            const period = btn.dataset.period;
            updateDisplayForPeriod(period);
        });
    });
}

// Load all dashboard data
async function loadDashboard() {
    await Promise.all([
        loadBankrollHistory(),
        loadDailyPnl(),
    ]);

    // Load summary after history so we have data for period calculations
    await loadSummary();
    await loadTodayStats();
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    setupPeriodToggles();
    loadDashboard();
});

// Refresh every 5 minutes
setInterval(loadDashboard, 5 * 60 * 1000);
