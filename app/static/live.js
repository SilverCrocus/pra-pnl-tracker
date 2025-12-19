// Goldilocks V2 Live Tracker - Game Cards Edition

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
            return;
        }

        if (data.tracking_state === 'complete') {
            // All games finished - show summary instead of live tracking
            const wins = data.bets.filter(b => b.status === 'hit').length;
            const losses = data.bets.filter(b => b.status === 'miss').length;
            container.innerHTML = `
                <div class="complete-state">
                    <div class="complete-icon">✅</div>
                    <span class="complete-title">Tracking Complete</span>
                    <span class="complete-date">${formatDate(data.date)}</span>
                    <div class="complete-summary">
                        <div class="complete-stat">
                            <span class="stat-value text-hit">${wins}</span>
                            <span class="stat-label">Hits</span>
                        </div>
                        <div class="complete-stat">
                            <span class="stat-value text-danger">${losses}</span>
                            <span class="stat-label">Misses</span>
                        </div>
                        <div class="complete-stat">
                            <span class="stat-value">${data.summary.total}</span>
                            <span class="stat-label">Total</span>
                        </div>
                    </div>
                    <span class="complete-sub">All games have finished. Results synced to Performance page.</span>
                </div>
            `;
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
            return;
        }

        // Group bets by game
        const betsByGame = groupBetsByGame(data.bets, data.games);

        // Render game cards
        renderGameCards(betsByGame, data.games);

    } catch (error) {
        console.error('Error loading live bets:', error);
        document.getElementById('gameCards').innerHTML = `
            <div class="error-state">
                <span>Failed to load data. Retrying...</span>
            </div>
        `;
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

// Initial load
loadLiveBets();

// Refresh every 5 seconds
setInterval(loadLiveBets, 5000);
