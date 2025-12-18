// Goldilocks V2 Live Tracker

const STATUS_EMOJI = {
    'hit': '&#x2705;',      // checkmark
    'on_track': '&#x1F525;', // fire
    'safe': '&#x2705;',      // checkmark
    'needs_more': '&#x26A0;&#xFE0F;', // warning
    'close': '&#x26A0;&#xFE0F;',      // warning
    'unlikely': '&#x274C;',  // X
    'busted': '&#x274C;',    // X
    'danger': '&#x1F525;',   // fire
    'miss': '&#x274C;',      // X
    'not_started': '&#x23F0;', // clock
};

async function loadLiveBets() {
    try {
        const response = await fetch('/api/live-bets');
        const data = await response.json();

        // Update summary
        document.getElementById('totalBets').textContent = data.summary.total;
        document.getElementById('liveCount').textContent = data.summary.live;
        document.getElementById('hitsCount').textContent = data.summary.hits;
        document.getElementById('pendingCount').textContent = data.summary.pending;

        // Update games bar
        renderGamesBar(data.games);

        // Update bets
        renderBets(data.bets);

        // Update timestamp
        document.getElementById('lastUpdate').textContent =
            `Last updated: ${new Date().toLocaleTimeString()}`;

    } catch (error) {
        console.error('Error loading live bets:', error);
    }
}

function renderGamesBar(games) {
    const container = document.getElementById('gamesBar');

    if (!games || games.length === 0) {
        container.innerHTML = '<div class="no-games">No games today</div>';
        return;
    }

    container.innerHTML = games.map(game => {
        const statusClass = game.status === 'Live' ? 'game-live' :
                           game.status === 'Finished' ? 'game-final' : 'game-upcoming';
        return `
            <div class="game-chip ${statusClass}">
                <span class="game-matchup">${game.game}</span>
                <span class="game-score">${game.score}</span>
                <span class="game-status">${game.status === 'Live' ? 'Q' + game.period : game.status}</span>
            </div>
        `;
    }).join('');
}

function renderBets(bets) {
    const container = document.getElementById('liveBets');

    if (!bets || bets.length === 0) {
        container.innerHTML = '<div class="no-bets">No bets for today</div>';
        return;
    }

    // Sort: live games first, then by status
    const statusOrder = ['on_track', 'safe', 'needs_more', 'close', 'danger', 'hit', 'unlikely', 'busted', 'miss', 'not_started'];
    bets.sort((a, b) => {
        // Live first
        if (a.game_status === 'Live' && b.game_status !== 'Live') return -1;
        if (b.game_status === 'Live' && a.game_status !== 'Live') return 1;
        // Then by status
        return statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status);
    });

    container.innerHTML = bets.map(bet => renderBetCard(bet)).join('');
}

function renderBetCard(bet) {
    const emoji = STATUS_EMOJI[bet.status] || '&#x2753;';
    const colorClass = bet.status_color;

    // Calculate progress percentage
    let progress = 0;
    if (bet.current_pra !== null && bet.betting_line > 0) {
        progress = Math.min(100, (bet.current_pra / bet.betting_line) * 100);
    }

    // For UNDER bets, invert the visual (full = safe)
    const isUnder = bet.direction === 'UNDER';
    const progressColor = isUnder ?
        (progress > 100 ? 'var(--accent-red)' : 'var(--accent-green)') :
        (progress >= 100 ? 'var(--accent-green)' : 'var(--accent-blue)');

    const tierClass = bet.tier === 'GOLDEN' ? 'tier-golden' : 'tier-volatile';

    return `
        <div class="live-bet-card ${bet.game_status === 'Live' ? 'is-live' : ''} ${bet.game_status === 'Finished' ? 'is-finished' : ''}">
            <div class="bet-header">
                <div class="bet-player-info">
                    <span class="bet-player-name">${bet.player_name}</span>
                    <span class="bet-tier ${tierClass}">${bet.tier}</span>
                </div>
                <div class="bet-status ${colorClass}">
                    <span class="status-emoji">${emoji}</span>
                    <span class="status-text">${bet.status_text}</span>
                </div>
            </div>

            <div class="bet-line-info">
                <span class="bet-direction ${bet.direction.toLowerCase()}">${bet.direction}</span>
                <span class="bet-line">${bet.betting_line}</span>
                <span class="bet-prediction">Pred: ${bet.prediction || '-'}</span>
            </div>

            <div class="bet-progress-section">
                <div class="progress-numbers">
                    <span class="current-pra">${bet.current_pra !== null ? bet.current_pra : '-'}</span>
                    <span class="progress-separator">/</span>
                    <span class="target-line">${bet.betting_line}</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progress}%; background: ${progressColor}"></div>
                    ${bet.direction === 'OVER' ? `<div class="progress-target" style="left: 100%"></div>` : ''}
                </div>
                <div class="progress-details">
                    ${bet.distance !== null ?
                        (bet.direction === 'OVER' ?
                            `<span>Need: ${bet.distance > 0 ? bet.distance : 0}</span>` :
                            `<span>Margin: ${bet.distance}</span>`)
                        : ''}
                    ${bet.projected_pra ? `<span>Proj: ${bet.projected_pra}</span>` : ''}
                </div>
            </div>

            <div class="bet-game-info">
                <span class="game-matchup">${bet.game}</span>
                <span class="game-time">${bet.game_status === 'Live' ? `${bet.period} ${bet.game_time}` : bet.game_status}</span>
                <span class="minutes-played">${bet.minutes_played} min</span>
            </div>
        </div>
    `;
}

// Initial load
loadLiveBets();

// Refresh every 5 seconds
setInterval(loadLiveBets, 5000);
