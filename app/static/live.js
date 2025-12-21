// Goldilocks V2 Live Tracker - Game Cards Edition

// Cache for recent results (so we don't lose them on live updates)
let cachedRecentResults = null;

async function loadLiveBets() {
    try {
        const response = await fetch('/api/live-bets');
        const data = await response.json();

        // Update summary stats
        document.getElementById('totalBets').textContent = data.summary.total;
        document.getElementById('liveCount').textContent = data.summary.live;
        document.getElementById('hitsCount').textContent = data.summary.hits;
        document.getElementById('pendingCount').textContent = data.summary.pending;
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

        // Handle different tracking states
        const container = document.getElementById('gameCards');

        if (data.summary.total === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🏀</div>
                    <span class="empty-title">No bets for today</span>
                    <span class="empty-sub">Check back when new bets are generated</span>
                </div>
            `;
            appendCachedRecentResults();
            return;
        }

        if (data.tracking_state === 'complete') {
            // All games finished - show results table
            renderResultsTable(container, data.bets, data.date);
            appendCachedRecentResults();
            return;
        }

        if (data.tracking_state === 'upcoming') {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⏳</div>
                    <span class="empty-title">Games Starting Soon</span>
                    <span class="empty-sub">${data.summary.pending} bets ready to track</span>
                </div>
            `;
            appendCachedRecentResults();
            return;
        }

        // Group bets by game
        const betsByGame = groupBetsByGame(data.bets, data.games);

        // Render game cards
        renderGameCards(betsByGame, data.games);

        // Re-append cached recent results if we have them
        appendCachedRecentResults();

    } catch (error) {
        console.error('Error loading live bets:', error);
        document.getElementById('gameCards').innerHTML = `
            <div class="error-state">
                <span>Failed to load data. Retrying...</span>
            </div>
        `;
        // Still show recent results even on error
        appendCachedRecentResults();
    }
}

function appendCachedRecentResults() {
    if (!cachedRecentResults) return;

    const container = document.getElementById('gameCards');
    const existingRecent = container.querySelector('.recent-results-section');
    if (existingRecent) {
        existingRecent.remove();
    }

    const recentHtml = renderRecentResultsSection(cachedRecentResults);
    if (recentHtml) {
        container.insertAdjacentHTML('beforeend', recentHtml);
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

function groupBetsByGame(bets, games) {
    const grouped = {};

    // Initialize with all games that have bets
    games.forEach(game => {
        const gameKey = game.game;
        grouped[gameKey] = {
            game: game,
            bets: []
        };
    });

    // Add "Unmatched" for bets without game info
    grouped['Unmatched'] = {
        game: null,
        bets: []
    };

    // Group bets into their games
    bets.forEach(bet => {
        const gameKey = bet.game && bet.game !== '-' ? bet.game : 'Unmatched';
        if (grouped[gameKey]) {
            grouped[gameKey].bets.push(bet);
        } else {
            grouped['Unmatched'].bets.push(bet);
        }
    });

    return grouped;
}

function renderGameCards(betsByGame, games) {
    const container = document.getElementById('gameCards');

    // Filter to only games with bets, sort by status (live first)
    const gamesWithBets = Object.entries(betsByGame)
        .filter(([key, data]) => data.bets.length > 0)
        .sort((a, b) => {
            const aLive = a[1].game?.status === 'Live' ? 0 : 1;
            const bLive = b[1].game?.status === 'Live' ? 0 : 1;
            return aLive - bLive;
        });

    if (gamesWithBets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🏀</div>
                <span class="empty-title">No bets tracking today</span>
                <span class="empty-sub">Check back at gametime</span>
            </div>
        `;
        return;
    }

    container.innerHTML = gamesWithBets.map(([gameKey, data]) =>
        renderGameCard(gameKey, data.game, data.bets)
    ).join('');
}

function renderGameCard(gameKey, game, bets) {
    const isLive = game?.status === 'Live';
    const isFinished = game?.status === 'Finished';

    // Sort bets: hits first, then by current PRA
    bets.sort((a, b) => {
        if (a.status === 'hit' && b.status !== 'hit') return -1;
        if (b.status === 'hit' && a.status !== 'hit') return 1;
        return (b.current_pra || 0) - (a.current_pra || 0);
    });

    const clockDisplay = game ? formatClock(game) : 'Not Started';
    const awayTeam = game ? game.game.split(' @ ')[0] : '???';
    const homeTeam = game ? game.game.split(' @ ')[1] : '???';
    const awayScore = game ? game.score.split(' - ')[0] : '0';
    const homeScore = game ? game.score.split(' - ')[1] : '0';

    return `
        <div class="game-card ${isLive ? 'is-live' : ''} ${isFinished ? 'is-finished' : ''}">
            <!-- Card Header -->
            <div class="card-header">
                <div class="status-badge ${isLive ? 'live' : isFinished ? 'final' : 'upcoming'}">
                    ${isLive ? '<span class="pulse-dot"></span>LIVE' : isFinished ? 'FINAL' : 'UPCOMING'}
                </div>
                <span class="clock">${clockDisplay}</span>
            </div>

            <!-- Scoreboard -->
            <div class="scoreboard">
                <div class="team away">
                    <span class="team-name">${awayTeam}</span>
                    <span class="team-score">${awayScore}</span>
                </div>
                <span class="vs">@</span>
                <div class="team home">
                    <span class="team-name">${homeTeam}</span>
                    <span class="team-score">${homeScore}</span>
                </div>
            </div>

            <!-- Tracked Players -->
            <div class="tracked-players">
                <div class="section-label">TRACKED PLAYERS</div>
                ${bets.map(bet => renderPlayerRow(bet)).join('')}
            </div>
        </div>
    `;
}

function renderPlayerRow(bet) {
    const current = bet.current_pra !== null ? bet.current_pra : 0;
    const line = bet.betting_line;
    const direction = bet.direction;
    const isGoldilocks = bet.tier === 'GOLDEN';

    // Calculate progress
    const progress = Math.min((current / line) * 100, 150);

    // Determine status and colors
    const statusInfo = getStatusInfo(bet);
    const barColor = getBarColor(bet);

    return `
        <div class="player-row">
            <div class="player-info">
                <div class="player-name-row">
                    <span class="player-name">${bet.player_name}</span>
                    ${isGoldilocks ? '<span class="goldilocks-badge">GOLDILOCKS</span>' : ''}
                    <span class="status-chip ${statusInfo.class}">${statusInfo.text}</span>
                </div>
                <div class="bet-details">
                    <span class="direction ${direction.toLowerCase()}">${direction}</span>
                    <span class="line">${line} PRA</span>
                    ${bet.minutes_played ? `<span class="minutes">${bet.minutes_played} min</span>` : ''}
                </div>
            </div>
            <div class="player-progress">
                <div class="progress-value">
                    <span class="current ${statusInfo.valueClass}">${current}</span>
                    <span class="separator">/</span>
                    <span class="target">${line}</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill ${barColor}" style="width: ${Math.min(progress, 100)}%"></div>
                    ${direction === 'OVER' ? '<div class="progress-target-line"></div>' : ''}
                </div>
            </div>
        </div>
    `;
}

function formatClock(game) {
    if (!game) return '-';
    const status = game.status;
    if (status === 'Finished') return 'Final';
    if (status === 'Not Started') return 'Upcoming';

    const period = game.period;
    if (period === 0) return '-';
    if (period <= 4) return `Q${period}`;
    if (period === 5) return 'OT';
    return `${period - 4}OT`;
}

function getStatusInfo(bet) {
    const status = bet.status;
    const statusMap = {
        'hit': { text: 'HIT', class: 'hit', valueClass: 'text-hit' },
        'on_track': { text: 'ON TRACK', class: 'on-track', valueClass: 'text-on-track' },
        'safe': { text: 'SAFE', class: 'safe', valueClass: 'text-safe' },
        'needs_more': { text: 'NEEDS MORE', class: 'warning', valueClass: 'text-warning' },
        'close': { text: 'CLOSE', class: 'warning', valueClass: 'text-warning' },
        'unlikely': { text: 'UNLIKELY', class: 'danger', valueClass: 'text-danger' },
        'busted': { text: 'BUSTED', class: 'danger', valueClass: 'text-danger' },
        'danger': { text: 'DANGER', class: 'danger', valueClass: 'text-danger' },
        'miss': { text: 'MISS', class: 'danger', valueClass: 'text-danger' },
        'not_started': { text: 'PENDING', class: 'pending', valueClass: '' },
    };
    return statusMap[status] || { text: status?.toUpperCase() || 'UNKNOWN', class: 'pending', valueClass: '' };
}

function getBarColor(bet) {
    const status = bet.status;
    if (status === 'hit' || status === 'safe') return 'bar-hit';
    if (status === 'on_track') return 'bar-on-track';
    if (status === 'needs_more' || status === 'close') return 'bar-warning';
    if (status === 'unlikely' || status === 'busted' || status === 'danger' || status === 'miss') return 'bar-danger';
    return 'bar-neutral';
}

function renderResultsTable(container, bets, dateStr) {
    // Group bets by outcome
    const hits = bets.filter(b => b.status === 'hit');
    const misses = bets.filter(b => b.status === 'miss');
    const voided = bets.filter(b => b.status === 'not_started' || b.game_status === 'Not Started')
        .concat(bets.filter(b => !['hit', 'miss'].includes(b.status) && b.current_pra === null));

    // Calculate win rate (excluding voided)
    const settled = hits.length + misses.length;
    const winRate = settled > 0 ? ((hits.length / settled) * 100).toFixed(1) : '0.0';

    container.innerHTML = `
        <div class="results-container">
            <div class="results-header">
                <div class="results-title">
                    <span class="results-date">${formatDate(dateStr)}</span>
                    <span class="results-record">${hits.length}/${settled} Hits (${winRate}%)</span>
                </div>
            </div>

            ${hits.length > 0 ? `
                <div class="results-section hits-section">
                    <div class="section-header">
                        <span class="section-icon">✅</span>
                        <span class="section-title">HITS (${hits.length})</span>
                    </div>
                    <div class="results-list">
                        ${hits.map(bet => renderResultRow(bet, 'hit')).join('')}
                    </div>
                </div>
            ` : ''}

            ${misses.length > 0 ? `
                <div class="results-section misses-section">
                    <div class="section-header">
                        <span class="section-icon">❌</span>
                        <span class="section-title">MISSES (${misses.length})</span>
                    </div>
                    <div class="results-list">
                        ${misses.map(bet => renderResultRow(bet, 'miss')).join('')}
                    </div>
                </div>
            ` : ''}

            ${voided.length > 0 ? `
                <div class="results-section voided-section">
                    <div class="section-header">
                        <span class="section-icon">🚫</span>
                        <span class="section-title">VOIDED (${voided.length})</span>
                    </div>
                    <div class="results-list">
                        ${voided.map(bet => renderResultRow(bet, 'voided')).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function renderResultRow(bet, outcome) {
    const actualPra = bet.current_pra !== null ? bet.current_pra : 'DNP';
    const isGoldilocks = bet.tier === 'GOLDEN';

    return `
        <div class="result-row ${outcome}">
            <div class="result-player">
                <span class="player-name">${bet.player_name}</span>
                ${isGoldilocks ? '<span class="goldilocks-badge">GOLDILOCKS</span>' : ''}
            </div>
            <div class="result-bet">
                <span class="direction ${bet.direction.toLowerCase()}">${bet.direction}</span>
                <span class="line">${bet.betting_line}</span>
            </div>
            <div class="result-actual">
                <span class="arrow">→</span>
                <span class="actual-value ${outcome}">${actualPra}</span>
                <span class="pra-label">PRA</span>
            </div>
        </div>
    `;
}

async function loadRecentResults() {
    try {
        const response = await fetch('/api/recent-results?days=3');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading recent results:', error);
        return { days: [], total_days: 0 };
    }
}

function renderRecentResultsSection(recentData) {
    if (!recentData.days || recentData.days.length === 0) {
        return '';
    }

    return `
        <div class="recent-results-section">
            <div class="section-header-bar">
                <h2>Recent Results</h2>
            </div>
            ${recentData.days.map(day => renderDayResults(day)).join('')}
        </div>
    `;
}

function renderDayResults(day) {
    const dateObj = new Date(day.date + 'T00:00:00');
    const dateDisplay = dateObj.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });

    const hits = day.bets.filter(b => b.result === 'WON');
    const misses = day.bets.filter(b => b.result === 'LOST');
    const voided = day.bets.filter(b => b.result === 'VOIDED');

    return `
        <div class="day-results-card">
            <div class="day-header">
                <span class="day-date">${dateDisplay}</span>
                <span class="day-record">${day.wins}/${day.wins + day.losses} (${day.win_rate}%)</span>
            </div>
            <div class="day-bets-grid">
                ${hits.map(bet => `
                    <div class="result-chip hit">
                        <span class="chip-name">${bet.player_name.split(' ').pop()}</span>
                        <span class="chip-result">${bet.actual_pra}/${bet.betting_line}</span>
                    </div>
                `).join('')}
                ${misses.map(bet => `
                    <div class="result-chip miss">
                        <span class="chip-name">${bet.player_name.split(' ').pop()}</span>
                        <span class="chip-result">${bet.actual_pra}/${bet.betting_line}</span>
                    </div>
                `).join('')}
                ${voided.map(bet => `
                    <div class="result-chip voided">
                        <span class="chip-name">${bet.player_name.split(' ').pop()}</span>
                        <span class="chip-result">DNP</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

async function loadAll() {
    // Load and cache recent results first
    const recentData = await loadRecentResults();
    cachedRecentResults = recentData;

    // Load live bets (this will also append cached recent results)
    await loadLiveBets();
}

// Initial load
loadAll();

// Refresh live data every 5 seconds, recent results less frequently
setInterval(loadLiveBets, 5000);
setInterval(loadAll, 60000); // Full refresh every minute
