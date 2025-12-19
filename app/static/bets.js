/**
 * Today's Bets Page JavaScript
 * Fetches and displays today's betting recommendations
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
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function getTierClass(tier) {
    const tierMap = {
        'GOLDEN': 'tier-golden',
        'HIGH_VOLATILITY': 'tier-high-volatility',
        'PROB_SWEET_SPOT': 'tier-prob-sweet-spot',
        'STD_SWEET_SPOT': 'tier-std-sweet-spot'
    };
    return tierMap[tier] || 'tier-golden';
}

function formatTierName(tier) {
    const nameMap = {
        'GOLDEN': 'Golden',
        'HIGH_VOLATILITY': 'High Vol',
        'PROB_SWEET_SPOT': 'Prob SS',
        'STD_SWEET_SPOT': 'Std SS'
    };
    return nameMap[tier] || tier;
}

function groupBetsByTier(bets) {
    const groups = {};

    bets.forEach(bet => {
        const tier = bet.tier || 'OTHER';
        if (!groups[tier]) {
            groups[tier] = [];
        }
        groups[tier].push(bet);
    });

    // Sort by tier priority
    const tierOrder = ['GOLDEN', 'HIGH_VOLATILITY', 'PROB_SWEET_SPOT', 'STD_SWEET_SPOT', 'OTHER'];
    const sortedGroups = {};

    tierOrder.forEach(tier => {
        if (groups[tier]) {
            sortedGroups[tier] = groups[tier];
        }
    });

    return sortedGroups;
}

function renderBetRow(bet) {
    const directionClass = bet.direction === 'OVER' ? 'direction-over' : 'direction-under';
    const tierClass = getTierClass(bet.tier);

    let resultBadge = '';
    if (bet.result === 'WON') {
        resultBadge = '<span class="result-badge won">WON</span>';
    } else if (bet.result === 'LOST') {
        resultBadge = '<span class="result-badge lost">LOST</span>';
    } else if (bet.result === 'VOIDED') {
        resultBadge = '<span class="result-badge voided">VOIDED</span>';
    }

    return `
        <div class="bet-row">
            <div class="player-info" data-line="${bet.direction} ${bet.betting_line}">
                <span class="player-name">${bet.player_name}</span>
                ${bet.probability ? `<span class="probability">${bet.probability}% prob</span>` : ''}
            </div>
            <div class="bet-line">
                <div class="line-value">${bet.betting_line}</div>
                <div class="line-label">PRA Line</div>
            </div>
            <div class="bet-direction ${directionClass}">
                ${bet.direction}
            </div>
            <div class="bet-tier">
                <span class="tier-badge ${tierClass}">${formatTierName(bet.tier)}</span>
                <span class="units">${bet.tier_units}u</span>
                ${resultBadge}
            </div>
        </div>
    `;
}

function renderTierGroup(tier, bets) {
    const tierClass = getTierClass(tier);
    const tierName = formatTierName(tier);
    const totalUnits = bets.reduce((sum, b) => sum + b.tier_units, 0);

    return `
        <div class="game-card">
            <div class="game-header">
                <div class="matchup">
                    <span class="tier-badge ${tierClass}">${tierName}</span>
                    <span class="team-home">${bets.length} bets</span>
                </div>
                <div class="game-time">${totalUnits} units</div>
            </div>
            <div class="bets-list">
                ${bets.map(bet => renderBetRow(bet)).join('')}
            </div>
        </div>
    `;
}

function renderNoBets() {
    return `
        <div class="no-bets">
            <div class="no-bets-icon">📋</div>
            <h3>No Bets Today</h3>
            <p>Check back when new betting recommendations are generated.</p>
        </div>
    `;
}

async function initBetsPage() {
    const data = await fetchTodaysBets();

    if (!data) {
        document.getElementById('gamesContainer').innerHTML = `
            <div class="no-bets">
                <div class="no-bets-icon">⚠️</div>
                <h3>Error Loading Bets</h3>
                <p>Please try refreshing the page.</p>
            </div>
        `;
        return;
    }

    // Update header
    document.getElementById('betsDate').textContent = formatDate(data.date);
    document.getElementById('totalBets').textContent = data.summary.total_bets;
    document.getElementById('totalUnits').textContent = data.summary.total_units;

    // Count unique games (for now, count unique tiers as proxy)
    const bets = data.bets || [];
    const uniqueTiers = new Set(bets.map(b => b.tier)).size;
    document.getElementById('gamesCount').textContent = uniqueTiers;

    // Render bets
    const container = document.getElementById('gamesContainer');

    if (bets.length === 0) {
        container.innerHTML = renderNoBets();
        return;
    }

    // Group by tier and render
    const groupedBets = groupBetsByTier(bets);
    let html = '';

    for (const [tier, tierBets] of Object.entries(groupedBets)) {
        html += renderTierGroup(tier, tierBets);
    }

    container.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initBetsPage);
