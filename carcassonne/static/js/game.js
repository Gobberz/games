import { drawTile, drawHandTile, TILE_SIZE, COLORS } from './renderer.js';

const MEEPLE_COLORS = { 0: '#e74c3c', 1: '#3498db', 2: '#2ecc71', 3: '#f39c12' };
const SIDE_OFFSETS = {
    N: { x: 0.5, y: 0.15 }, E: { x: 0.85, y: 0.5 },
    S: { x: 0.5, y: 0.85 }, W: { x: 0.15, y: 0.5 }, CENTER: { x: 0.5, y: 0.5 },
};

class GameClient {
    constructor() {
        this.gameId = null;
        this.playerId = null;
        this.playerIndex = 0;
        this.stage = null;
        this.boardLayer = null;
        this.meepleLayer = null;
        this.overlayLayer = null;
        this.heatmapLayer = null;
        this.gameState = null;
        this.selectedTileIdx = null;
        this.selectedRotation = 0;
        this.validMoves = [];
        this.currentHand = [];
        this.pollTimer = null;
        this.lastStateKey = '';
        this.hasBotOpponent = false;
        this.analyticsData = null;
        this.showHeatmap = false;
        this.engineerMode = false;
        this.engineerTargets = [];
    }

    init() {
        document.getElementById('btn-create').addEventListener('click', () => this.createGame());
        document.getElementById('btn-join').addEventListener('click', () => this.joinGame());
        document.getElementById('heatmap-toggle')?.addEventListener('change', e => {
            this.showHeatmap = e.target.checked;
            this.renderHeatmap();
        });
        this.setupKeyboard();
    }

    // ── Lobby ──

    async createGame() {
        const opponentType = document.getElementById('opponent-type').value;
        const botOpponent = opponentType !== 'human' ? opponentType : null;
        this.hasBotOpponent = !!botOpponent;

        const rules = {
            engineer: document.getElementById('rule-engineer').checked,
            objectives: document.getElementById('rule-objectives').checked,
        };

        const resp = await fetch('/api/games', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ num_players: 2, bot_opponent: botOpponent, rules }),
        });
        const data = await resp.json();
        document.getElementById('game-id-input').value = data.game_id;

        if (botOpponent) {
            this.joinGame();
        } else {
            document.getElementById('game-id-display').textContent = `Share: ${data.game_id}`;
        }
    }

    async joinGame() {
        const gameId = document.getElementById('game-id-input').value.trim();
        const name = document.getElementById('player-name').value.trim() || 'Player';
        if (!gameId) return;

        const resp = await fetch(`/api/games/${gameId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        if (!resp.ok) { alert((await resp.json()).error || 'Failed'); return; }

        const data = await resp.json();
        this.gameId = gameId;
        this.playerId = data.player_id;
        document.getElementById('lobby').style.display = 'none';
        this.setupBoard();
        this.startPolling();
    }

    // ── Board Setup ──

    setupBoard() {
        const c = document.getElementById('board-container');
        this.stage = new Konva.Stage({ container: 'board-container', width: c.offsetWidth, height: c.offsetHeight, draggable: true });
        this.boardLayer = new Konva.Layer({ listening: false });
        this.heatmapLayer = new Konva.Layer({ listening: false, opacity: 0.5 });
        this.meepleLayer = new Konva.Layer({ listening: false });
        this.overlayLayer = new Konva.Layer();
        this.stage.add(this.boardLayer, this.heatmapLayer, this.meepleLayer, this.overlayLayer);
        this.stage.position({ x: c.offsetWidth / 2, y: c.offsetHeight / 2 });

        this.stage.on('wheel', e => {
            e.evt.preventDefault();
            const s = this.stage.scaleX();
            const p = this.stage.getPointerPosition();
            const d = e.evt.deltaY > 0 ? -1 : 1;
            const ns = Math.max(0.3, Math.min(3, s + d * 0.1));
            const mp = { x: (p.x - this.stage.x()) / s, y: (p.y - this.stage.y()) / s };
            this.stage.scale({ x: ns, y: ns });
            this.stage.position({ x: p.x - mp.x * ns, y: p.y - mp.y * ns });
        });
        window.addEventListener('resize', () => { this.stage.width(c.offsetWidth); this.stage.height(c.offsetHeight); });
    }

    setupKeyboard() {
        document.addEventListener('keydown', e => {
            if (e.key === 'r' || e.key === 'R') {
                this.selectedRotation = (this.selectedRotation + 90) % 360;
                this.renderSlots();
            }
            if (e.key === 'h' || e.key === 'H') {
                this.showHeatmap = !this.showHeatmap;
                const cb = document.getElementById('heatmap-toggle');
                if (cb) cb.checked = this.showHeatmap;
                this.renderHeatmap();
            }
            if (e.key === 'Escape') {
                if (this.engineerMode) this.cancelEngineerMode();
            }
        });
    }

    // ── Polling ──

    startPolling() { this.poll(); this.pollTimer = setInterval(() => this.poll(), 1200); }

    async poll() {
        if (!this.gameId || !this.playerId) return;
        try {
            const resp = await fetch(`/api/games/${this.gameId}?player_id=${this.playerId}`);
            if (!resp.ok) return;
            const state = await resp.json();
            this.gameState = state;

            const key = `${state.turn}-${state.turn_phase}-${state.phase}`;
            if (key === this.lastStateKey) return;
            this.lastStateKey = key;

            this.resolvePlayerIndex();
            this.renderBoard();
            this.renderMeeples();
            this.updateInfo();
            this.updateHand();
            this.updateEngineerPanel();
            this.updateObjectives();

            const isMyTurn = state.current_player === this.playerId;
            if (isMyTurn && state.phase === 'playing') {
                if (state.turn_phase === 'place_meeple') {
                    this.fetchMeepleOptions();
                } else {
                    this.fetchValidMoves();
                }
            } else {
                this.validMoves = [];
                this.renderSlots();
                if (state.phase === 'playing') this.triggerBotTurn();
            }

            if (state.turn > 0 && state.turn % 3 === 0) this.fetchAnalytics();
            if (state.phase === 'finished') this.fetchAnalytics();
        } catch (e) { console.error('Poll:', e); }
    }

    async triggerBotTurn() {
        if (!this.gameState) return;
        const cp = this.gameState.players[this.gameState.current_player];
        if (!cp?.is_bot) return;
        await new Promise(r => setTimeout(r, 500));
        const resp = await fetch(`/api/games/${this.gameId}/bot_turn`, { method: 'POST' });
        if (resp.ok) { this.lastStateKey = ''; this.poll(); }
    }

    resolvePlayerIndex() {
        if (this.gameState) this.playerIndex = Object.keys(this.gameState.players).indexOf(this.playerId);
    }

    // ── Data Fetching ──

    async fetchValidMoves() {
        const resp = await fetch(`/api/games/${this.gameId}/moves?player_id=${this.playerId}`);
        if (resp.ok) { this.validMoves = (await resp.json()).moves; this.renderSlots(); }
    }

    async fetchMeepleOptions() {
        const resp = await fetch(`/api/games/${this.gameId}/meeple_options?player_id=${this.playerId}`);
        if (resp.ok) this.renderMeepleOptions((await resp.json()).options);
    }

    async fetchAnalytics() {
        try {
            const resp = await fetch(`/api/games/${this.gameId}/analytics`);
            if (resp.ok) { this.analyticsData = await resp.json(); this.renderAnalytics(); if (this.showHeatmap) this.renderHeatmap(); }
        } catch (e) {}
    }

    async fetchEngineerTargets() {
        const resp = await fetch(`/api/games/${this.gameId}/engineer_targets?player_id=${this.playerId}`);
        if (resp.ok) this.engineerTargets = (await resp.json()).targets;
    }

    // ── Rendering ──

    renderBoard() {
        if (!this.gameState || !this.boardLayer) return;
        this.boardLayer.destroyChildren();
        const tiles = this.gameState.board.tiles;
        for (const key in tiles) {
            const t = tiles[key];
            drawTile(this.boardLayer, t, t.x * TILE_SIZE, t.y * TILE_SIZE, TILE_SIZE);
        }
        this.boardLayer.draw();
    }

    renderMeeples() {
        if (!this.meepleLayer || !this.gameState) return;
        this.meepleLayer.destroyChildren();
        const pids = Object.keys(this.gameState.players);
        (this.gameState.meeples?.placed || []).forEach(m => {
            const idx = pids.indexOf(m.player_id);
            const color = MEEPLE_COLORS[idx] || '#fff';
            const off = SIDE_OFFSETS[m.position] || SIDE_OFFSETS.CENTER;
            const px = m.x * TILE_SIZE + off.x * TILE_SIZE;
            const py = m.y * TILE_SIZE + off.y * TILE_SIZE;
            // body
            this.meepleLayer.add(new Konva.Circle({ x: px, y: py - 2, radius: 6, fill: color, stroke: '#000', strokeWidth: 1.5 }));
            // head
            this.meepleLayer.add(new Konva.Circle({ x: px, y: py - 10, radius: 3.5, fill: color, stroke: '#000', strokeWidth: 1 }));
        });
        this.meepleLayer.draw();
    }

    renderHeatmap() {
        if (!this.heatmapLayer) return;
        this.heatmapLayer.destroyChildren();
        if (!this.showHeatmap || !this.analyticsData?.heatmap?.cells) { this.heatmapLayer.draw(); return; }
        const cells = this.analyticsData.heatmap.cells;
        const max = this.analyticsData.heatmap.max_prob || 1;
        for (const key in cells) {
            const [x, y] = key.split(',').map(Number);
            const p = cells[key];
            const i = p / max;
            this.heatmapLayer.add(new Konva.Rect({
                x: x * TILE_SIZE, y: y * TILE_SIZE, width: TILE_SIZE, height: TILE_SIZE,
                fill: `rgba(${Math.round(255*i)},${Math.round(100*(1-i))},50,${0.15+i*0.4})`, cornerRadius: 2,
            }));
            if (p > 0.1) this.heatmapLayer.add(new Konva.Text({
                x: x*TILE_SIZE+2, y: y*TILE_SIZE+TILE_SIZE-14,
                text: `${Math.round(p*100)}%`, fontSize: 10, fill: '#fff', fontStyle: 'bold',
            }));
        }
        this.heatmapLayer.draw();
    }

    renderSlots() {
        if (!this.overlayLayer) return;
        this.overlayLayer.destroyChildren();
        this.showPanel('meeple-panel', false);

        if (this.engineerMode) { this.renderEngineerTargets(); return; }
        if (this.selectedTileIdx === null || !this.gameState) { this.overlayLayer.draw(); return; }

        const valid = this.validMoves.filter(m => m.tile_idx === this.selectedTileIdx);
        const slotMap = new Map();
        valid.forEach(m => { const k = `${m.x},${m.y}`; if (!slotMap.has(k)) slotMap.set(k, []); slotMap.get(k).push(m); });

        slotMap.forEach((moves, key) => {
            const [x, y] = key.split(',').map(Number);
            const px = x * TILE_SIZE, py = y * TILE_SIZE;
            const hasRot = moves.some(m => m.rotation === this.selectedRotation);
            const baseFill = hasRot ? 'rgba(46,204,113,0.2)' : 'rgba(241,196,15,0.1)';
            const hoverFill = hasRot ? 'rgba(46,204,113,0.4)' : 'rgba(241,196,15,0.25)';
            const rect = new Konva.Rect({
                x: px, y: py, width: TILE_SIZE, height: TILE_SIZE,
                fill: baseFill,
                stroke: hasRot ? '#2ecc71' : '#f1c40f', strokeWidth: 2, cornerRadius: 3,
            });
            rect.on('click tap', () => {
                if (hasRot) this.placeTile(x, y);
                else { this.selectedRotation = moves[0].rotation; this.renderSlots(); }
            });
            rect.on('mouseenter', () => { rect.fill(hoverFill); document.body.style.cursor = 'pointer'; this.overlayLayer.draw(); });
            rect.on('mouseleave', () => { rect.fill(baseFill); document.body.style.cursor = 'default'; this.overlayLayer.draw(); });
            this.overlayLayer.add(rect);
            if (hasRot && this.currentHand[this.selectedTileIdx]) {
                const tile = this.currentHand[this.selectedTileIdx];
                const re = this.rotEdges(tile.edges, this.selectedRotation);
                drawTile(this.overlayLayer, { ...tile, edges: re, center: 0 }, px, py, TILE_SIZE, { opacity: 0.45, listening: false });
            }
        });

        // empty slots
        (this.gameState.board.open_slots || []).forEach(([x,y]) => {
            if (!slotMap.has(`${x},${y}`))
                this.overlayLayer.add(new Konva.Rect({
                    x: x*TILE_SIZE, y: y*TILE_SIZE, width: TILE_SIZE, height: TILE_SIZE,
                    fill: 'rgba(255,255,255,0.02)', stroke: '#222', strokeWidth: 1, dash: [4,4],
                }));
        });
        this.overlayLayer.draw();
    }

    renderMeepleOptions(options) {
        if (!this.overlayLayer || !this.gameState) return;
        this.overlayLayer.destroyChildren();
        const lp = this.gameState.last_placed;
        if (!lp) return;
        const [tx, ty] = lp;
        this.setStatus('Place a meeple or skip');
        this.showPanel('meeple-panel', true);

        this.overlayLayer.add(new Konva.Rect({
            x: tx*TILE_SIZE, y: ty*TILE_SIZE, width: TILE_SIZE, height: TILE_SIZE,
            fill: 'rgba(233,69,96,0.08)', stroke: '#e94560', strokeWidth: 2, dash: [6,3],
        }));

        const types = { 0: 'F', 1: 'R', 2: 'C', '-1': 'M' };
        options.forEach(opt => {
            const off = SIDE_OFFSETS[opt.position] || SIDE_OFFSETS.CENTER;
            const px = tx*TILE_SIZE + off.x*TILE_SIZE, py = ty*TILE_SIZE + off.y*TILE_SIZE;
            const c = new Konva.Circle({
                x: px, y: py, radius: 11,
                fill: 'rgba(233,69,96,0.5)', stroke: '#e94560', strokeWidth: 2,
            });
            c.on('click tap', () => this.placeMeeple(opt.position));
            c.on('mouseenter', () => { c.fill('rgba(233,69,96,0.85)'); document.body.style.cursor = 'pointer'; this.overlayLayer.draw(); });
            c.on('mouseleave', () => { c.fill('rgba(233,69,96,0.5)'); document.body.style.cursor = 'default'; this.overlayLayer.draw(); });
            this.overlayLayer.add(c);
            this.overlayLayer.add(new Konva.Text({
                x: px-4, y: py-5, text: types[opt.feature_type]||'?', fontSize: 10, fill: '#fff', fontStyle: 'bold',
            }));
        });
        this.overlayLayer.draw();
    }

    // ── Engineer ──

    async startEngineerMode() {
        this.engineerMode = true;
        await this.fetchEngineerTargets();
        this.renderEngineerTargets();
        document.getElementById('btn-engineer').style.display = 'none';
        document.getElementById('btn-cancel-engineer').style.display = 'inline-block';
        this.setStatus('Click a highlighted tile to rotate it 90°');
    }

    cancelEngineerMode() {
        this.engineerMode = false;
        this.engineerTargets = [];
        document.getElementById('btn-engineer').style.display = 'inline-block';
        document.getElementById('btn-cancel-engineer').style.display = 'none';
        this.renderSlots();
    }

    renderEngineerTargets() {
        if (!this.overlayLayer) return;
        this.overlayLayer.destroyChildren();
        this.engineerTargets.forEach(t => {
            const rect = new Konva.Rect({
                x: t.x*TILE_SIZE, y: t.y*TILE_SIZE, width: TILE_SIZE, height: TILE_SIZE,
                fill: 'rgba(52,152,219,0.2)', stroke: '#3498db', strokeWidth: 2,
            });
            rect.on('click tap', () => this.useEngineer(t.x, t.y));
            rect.on('mouseenter', () => { rect.fill('rgba(52,152,219,0.4)'); this.overlayLayer.draw(); });
            rect.on('mouseleave', () => { rect.fill('rgba(52,152,219,0.2)'); this.overlayLayer.draw(); });
            this.overlayLayer.add(rect);
            this.overlayLayer.add(new Konva.Text({
                x: t.x*TILE_SIZE+TILE_SIZE/2-5, y: t.y*TILE_SIZE+TILE_SIZE/2-6,
                text: '🔧', fontSize: 14,
            }));
        });
        if (this.engineerTargets.length === 0)
            this.setStatus('No valid engineer targets available');
        this.overlayLayer.draw();
    }

    async useEngineer(x, y) {
        const resp = await fetch(`/api/games/${this.gameId}/engineer`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: this.playerId, x, y }),
        });
        const r = await resp.json();
        if (r.error) { this.setStatus('Error: ' + r.error); return; }
        this.cancelEngineerMode();
        this.lastStateKey = '';
        this.poll();
    }

    updateEngineerPanel() {
        if (!this.gameState) return;
        const me = this.gameState.players[this.playerId];
        const panel = document.getElementById('engineer-panel');
        if (!panel) return;
        const hasEngineer = me?.has_engineer;
        const isMyTurn = this.gameState.current_player === this.playerId;
        const inTilePhase = this.gameState.turn_phase === 'place_tile';
        panel.style.display = (hasEngineer && isMyTurn && inTilePhase && this.gameState.rules?.engineer) ? 'block' : 'none';
    }

    // ── Objectives ──

    updateObjectives() {
        if (!this.gameState?.objectives) { this.showPanel('objectives-panel', false); return; }
        const myObj = this.gameState.objectives[this.playerId];
        if (!myObj?.objectives) { this.showPanel('objectives-panel', false); return; }

        this.showPanel('objectives-panel', true);
        const el = document.getElementById('objectives-content');
        el.innerHTML = myObj.objectives.map(o => `
            <div class="objective">
                <div class="obj-header ${o.completed ? 'obj-done' : ''}">${o.icon} ${o.name} ${o.completed ? '✓' : ''}</div>
                <div class="obj-desc">${o.description}</div>
                <div class="obj-bonus">+${o.bonus_points} pts</div>
            </div>
        `).join('');
    }

    // ── Actions ──

    async placeTile(x, y) {
        if (this.selectedTileIdx === null) return;
        const resp = await fetch(`/api/games/${this.gameId}/place`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: this.playerId, tile_idx: this.selectedTileIdx, x, y, rotation: this.selectedRotation }),
        });
        const r = await resp.json();
        if (r.error) { this.setStatus('Error: ' + r.error); return; }
        this.selectedTileIdx = null; this.selectedRotation = 0;
        this.lastStateKey = ''; this.poll();
    }

    async placeMeeple(pos) {
        const resp = await fetch(`/api/games/${this.gameId}/meeple`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: this.playerId, position: pos }),
        });
        const r = await resp.json();
        if (r.error) { this.setStatus('Error: ' + r.error); return; }
        if (r.score_events?.length) this.setStatus(`+${r.score_events.reduce((s,e)=>s+e.points,0)} pts!`);
        this.showPanel('meeple-panel', false);
        this.lastStateKey = ''; this.poll();
    }

    async skipMeeple() {
        await fetch(`/api/games/${this.gameId}/skip_meeple`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: this.playerId }),
        });
        this.showPanel('meeple-panel', false);
        this.lastStateKey = ''; this.poll();
    }

    // ── Hand ──

    updateHand() {
        if (!this.gameState) return;
        const me = this.gameState.players[this.playerId];
        if (!me?.hand) return;
        this.currentHand = me.hand;
        this.renderHand(me.hand);
    }

    renderHand(hand) {
        const c = document.getElementById('hand-panel');
        c.innerHTML = '';
        hand.forEach((tile, idx) => {
            drawHandTile(c, tile, idx, idx === this.selectedTileIdx, i => {
                this.selectedTileIdx = i; this.selectedRotation = 0;
                this.renderHand(hand); this.fetchValidMoves();
            });
        });
    }

    // ── Info Panel ──

    updateInfo() {
        if (!this.gameState) return;
        const gs = this.gameState;
        const pids = Object.keys(gs.players);
        const el = document.getElementById('game-info');

        let html = `<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text2);margin-bottom:8px">
            <span>Turn ${gs.turn}</span><span>Deck: ${gs.deck_remaining}</span></div>`;

        pids.forEach((pid, idx) => {
            const p = gs.players[pid];
            const me = pid === this.playerId ? ' (you)' : '';
            const bot = p.is_bot ? ' 🤖' : '';
            const active = pid === gs.current_player;
            const color = MEEPLE_COLORS[idx] || '#fff';
            html += `<div class="player-row">
                <div class="active-indicator" style="background:${active ? color : 'transparent'}"></div>
                <span class="name" style="color:${color}">${p.name}${me}${bot}</span>
                <span class="score">${p.score}</span>
                <span class="meta">${p.meeples_available}m${p.has_engineer?' 🔧':''}</span>
            </div>`;
        });

        if (gs.recent_scores?.length) {
            html += '<div style="margin-top:6px;border-top:1px solid var(--border);padding-top:4px">';
            gs.recent_scores.slice(-4).forEach(e => {
                const n = gs.players[e.player_id]?.name || '?';
                html += `<div class="score-event"><span class="pts">+${e.points}</span> ${n} — ${e.reason}</div>`;
            });
            html += '</div>';
        }
        el.innerHTML = html;

        // Status
        if (gs.phase === 'finished') {
            const w = pids.reduce((a,b) => gs.players[a].score >= gs.players[b].score ? a : b);
            this.setStatus(`🏆 ${gs.players[w].name} wins! ${gs.players[w].score} pts`);
        } else if (gs.phase === 'waiting') {
            this.setStatus('Waiting for opponent...');
        } else if (gs.current_player === this.playerId) {
            this.setStatus(gs.turn_phase === 'place_meeple' ? 'Place meeple or skip' : 'Your turn — select tile, R to rotate, click slot');
        } else {
            const cp = gs.players[gs.current_player];
            this.setStatus(cp?.is_bot ? '🤖 Bot thinking...' : 'Opponent\'s turn...');
        }
    }

    // ── Analytics ──

    renderAnalytics() {
        const el = document.getElementById('analytics-content');
        if (!this.analyticsData || !el || !this.gameState) return;
        const a = this.analyticsData, gs = this.gameState, pids = Object.keys(gs.players);
        let html = '';

        // Entropy
        if (a.entropy) {
            const pct = Math.round(a.entropy.normalized * 100);
            html += `<div class="metric"><div class="metric-name">Board Entropy</div>
                <div class="metric-bar"><div class="metric-bar-fill" style="width:${pct}%;background:var(--blue)"></div></div>
                <div class="metric-value">${a.entropy.entropy.toFixed(1)} bits · ${a.entropy.open_slots} open slots</div></div>`;
        }

        // Per-player metrics
        pids.forEach((pid, idx) => {
            const name = gs.players[pid]?.name || '?';
            const color = MEEPLE_COLORS[idx] || '#fff';

            // Greed
            const g = a.greed_index?.[pid];
            if (g) {
                const pct = Math.round(g.greed_index * 100);
                html += `<div class="metric"><div class="metric-name" style="color:${color}">${name} · Greed</div>
                    <div class="metric-bar"><div class="metric-bar-fill" style="width:${pct}%;background:var(--orange)"></div></div>
                    <div class="metric-value">${pct}% realized · ${g.potential} potential</div></div>`;
            }

            // Aggression
            const ag = a.aggression_index?.[pid];
            if (ag && ag.total_moves > 0) {
                const pct = Math.round(ag.index * 100);
                html += `<div class="metric"><div class="metric-name" style="color:${color}">${name} · Aggression</div>
                    <div class="metric-bar"><div class="metric-bar-fill" style="width:${Math.min(pct*2,100)}%;background:var(--red)"></div></div>
                    <div class="metric-value">${pct}% · ${ag.aggressive_moves} hostile moves</div></div>`;
            }

            // Voronoi
            const v = a.voronoi_control?.[pid];
            if (v && v.total_slots > 0) {
                const pct = Math.round(v.control * 100);
                html += `<div class="metric"><div class="metric-name" style="color:${color}">${name} · Territory</div>
                    <div class="metric-bar"><div class="metric-bar-fill" style="width:${pct}%;background:${color}"></div></div>
                    <div class="metric-value">${pct}% · ${v.area} tiles</div></div>`;
            }

            // Depth
            const d = a.depth_score?.[pid];
            if (d) html += `<div class="metric"><div class="metric-name" style="color:${color}">${name} · Play Style</div>
                <div class="metric-value">${d.interpretation} (depth ${d.depth.toFixed(2)})</div></div>`;

            // Luck
            const l = a.luck_curve?.players?.[pid];
            if (l) {
                const label = l.avg > 0.05 ? '🍀 Lucky' : l.avg < -0.05 ? '😤 Unlucky' : '😐 Neutral';
                html += `<div class="metric"><div class="metric-name" style="color:${color}">${name} · Luck</div>
                    <div class="metric-value">${label} (${l.avg.toFixed(3)})</div></div>`;
            }
        });

        // Conflict
        if (a.conflict_risk) html += `<div class="metric"><div class="metric-name">Conflict Risk</div>
            <div class="metric-value">${a.conflict_risk.count} zones · risk ${a.conflict_risk.total_risk.toFixed(2)}</div></div>`;

        el.innerHTML = html || '<span class="hint">No data yet</span>';
    }

    // ── Helpers ──

    showPanel(id, show) { const el = document.getElementById(id); if (el) el.style.display = show ? 'block' : 'none'; }
    setStatus(msg) { document.getElementById('status-bar').textContent = msg; }
    rotEdges(edges, rot) { const s = (rot/90)%4; const e = [...edges]; for (let i=0;i<s;i++) e.unshift(e.pop()); return e; }
}

window.gameClient = new GameClient();
window.gameClient.init();
