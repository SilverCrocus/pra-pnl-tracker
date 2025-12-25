/**
 * Today's Bets Page JavaScript - Redesigned
 * Fetches and displays today's betting recommendations grouped by game matchup
 */

async function fetchTodaysBets() {
    try {
        const response = await fetch('/api/todays-bets');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching bets:', error);
        return null;
    }
}

function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}

function formatTierBadge(tier) {
    if (tier === 'GOLDEN' || tier === 'GOLD') {
        return '<span class="tier-badge golden">GOLDEN</span>';
    } else if (tier === 'BRONZE') {
        return '<span class="tier-badge bronze">BRONZE</span>';
    }
    // For any other tiers, format nicely
    const nameMap = {
        'HIGH_VOLATILITY': 'HIGH VOL',
        'PROB_SWEET_SPOT': 'PROB SS',
        'STD_SWEET_SPOT': 'STD SS'
    };
    const displayName = nameMap[tier] || tier;
    return `<span class="tier-badge bronze">${displayName}</span>`;
}

function renderBetPlayerRow(bet) {
    const direction = bet.direction;
    const directionClass = direction === 'OVER' ? 'over' : 'under';
    const prediction = bet.prediction ? `Pred: ${bet.prediction}` : '';

    return `
        <div class="bet-player-row">
            <div class="bet-player-main">
                <span class="bet-player-name">${bet.player_name}</span>
                <div class="bet-line-row">
                    <span class="direction ${directionClass}">${direction}</span>
                    <span class="bet-line-value">${bet.betting_line} PRA</span>
                    ${prediction ? `<span class="bet-prediction">${prediction}</span>` : ''}
                </div>
            </div>
            <div class="bet-tier-col">
                ${formatTierBadge(bet.tier)}
                <span class="bet-units-display">${bet.tier_units}u</span>
            </div>
        </div>
    `;
}

function renderGameCard(gameData) {
    const matchup = gameData.matchup;
    const betCount = gameData.bets.length;

    return `
        <div class="bets-game-card">
            <div class="bets-game-header">
                <div class="game-matchup">
                    <span class="game-icon">🏀</span>
                    <span class="game-teams">${matchup}</span>
                </div>
                <div class="game-meta">
                    <span class="picks-count">${betCount} pick${betCount !== 1 ? 's' : ''}</span>
                </div>
            </div>
            <div class="bets-game-players">
                ${gameData.bets.map(bet => renderBetPlayerRow(bet)).join('')}
            </div>
        </div>
    `;
}

function renderNoBets() {
    return `
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <span class="empty-title">No Bets Today</span>
            <span class="empty-sub">Check back when new betting recommendations are generated.</span>
        </div>
    `;
}

function renderError() {
    return `
        <div class="empty-state">
            <div class="empty-icon">⚠️</div>
            <span class="empty-title">Error Loading Bets</span>
            <span class="empty-sub">Please try refreshing the page.</span>
        </div>
    `;
}

async function initBetsPage() {
    const data = await fetchTodaysBets();
    const container = document.getElementById('gamesContainer');

    if (!data) {
        container.innerHTML = renderError();
        return;
    }

    // Update hero summary
    const dateEl = document.getElementById('betsDate');
    if (data.date) {
        dateEl.textContent = formatDate(data.date);
    }

    document.getElementById('totalBets').textContent = data.summary.total_bets || 0;
    document.getElementById('totalUnits').textContent = `${data.summary.total_units || 0}u`;
    document.getElementById('gamesCount').textContent = data.summary.games_count || 0;

    // Render game cards (API returns games array now)
    const games = data.games || [];

    if (games.length === 0) {
        container.innerHTML = renderNoBets();
        return;
    }

    // Render game cards - already sorted by API (most bets first, then alphabetically)
    container.innerHTML = games.map(game => renderGameCard(game)).join('');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initBetsPage);

// Refresh every 5 minutes
setInterval(initBetsPage, 5 * 60 * 1000);
