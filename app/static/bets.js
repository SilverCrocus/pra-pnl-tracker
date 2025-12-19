/**
 * Today's Bets Page JavaScript
 * Fetches and displays today's betting recommendations grouped by team
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

function renderPlayerRow(bet) {
    const directionClass = bet.direction === 'OVER' ? 'direction-over' : 'direction-under';
    const tierClass = getTierClass(bet.tier);
    const predText = bet.prediction ? `pred: ${bet.prediction}` : '';

    return `
        <div class="player-row">
            <div class="player-info">
                <span class="player-name">${bet.player_name}</span>
                <div class="player-meta">
                    <span>${predText}</span>
                </div>
            </div>
            <div class="bet-line">
                <div class="line-value">${bet.betting_line}</div>
                <div class="line-label">Line</div>
            </div>
            <div class="bet-direction ${directionClass}">
                ${bet.direction}
            </div>
            <div class="bet-tier">
                <span class="tier-badge ${tierClass}">${formatTierName(bet.tier)}</span>
                <span class="units">${bet.tier_units}u</span>
            </div>
        </div>
    `;
}

function renderTeamCard(teamData) {
    const team = teamData.team;
    const betCount = teamData.bets.length;
    const totalUnits = teamData.bets.reduce((sum, b) => sum + b.tier_units, 0);

    const isUnknown = team === 'UNK';
    const cardClass = isUnknown ? 'team-card unknown-card' : 'team-card';

    return `
        <div class="${cardClass}">
            <div class="team-header">
                <div class="team-name-display">
                    <span class="team-icon">📍</span>
                    <span class="team-abbrev">${isUnknown ? 'Unknown' : team}</span>
                </div>
                <span class="bet-count">${betCount} bet${betCount !== 1 ? 's' : ''} · ${totalUnits}u</span>
            </div>
            <div class="players-list">
                ${teamData.bets.map(bet => renderPlayerRow(bet)).join('')}
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
        document.getElementById('teamsContainer').innerHTML = `
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
    document.getElementById('teamsCount').textContent = data.summary.teams_count || data.teams.length;

    // Render teams
    const container = document.getElementById('teamsContainer');
    const teams = data.teams || [];

    if (teams.length === 0) {
        container.innerHTML = renderNoBets();
        return;
    }

    // Render team cards
    let html = '';
    for (const team of teams) {
        html += renderTeamCard(team);
    }

    container.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initBetsPage);
