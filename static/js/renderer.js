const TILE_SIZE = 80;

const COLORS = {
    0: '#4a7c3f',  // FIELD - green
    1: '#c4a35a',  // ROAD - sandy
    2: '#8b4513',  // CITY - brown
    monastery: '#8b0000',
    grid: '#2a2a4a',
    gridLine: '#3a3a5a',
};

function drawTile(layer, tile, x, y, size, opts = {}) {
    const group = new Konva.Group({ x, y });
    const s = size;
    const edges = tile.edges;
    const half = s / 2;
    const qtr = s / 4;

    // background
    group.add(new Konva.Rect({
        width: s, height: s,
        fill: COLORS[0],
        stroke: '#555',
        strokeWidth: 1,
    }));

    // draw each edge region
    const edgeShapes = [
        // N
        () => drawEdgeRegion(group, edges[0], 0, 0, s, qtr, 'N', s),
        // E
        () => drawEdgeRegion(group, edges[1], s - qtr, 0, qtr, s, 'E', s),
        // S
        () => drawEdgeRegion(group, edges[2], 0, s - qtr, s, qtr, 'S', s),
        // W
        () => drawEdgeRegion(group, edges[3], 0, 0, qtr, s, 'W', s),
    ];
    edgeShapes.forEach(fn => fn());

    // draw center
    drawCenter(group, tile, s);

    // draw internal connections (roads through tile)
    drawConnections(group, tile, s);

    if (opts.opacity !== undefined) group.opacity(opts.opacity);
    if (opts.listening === false) group.listening(false);
    if (opts.onClick) group.on('click tap', opts.onClick);

    layer.add(group);
    return group;
}

function drawEdgeRegion(group, edgeType, x, y, w, h, side, tileSize) {
    if (edgeType === 0) return; // field - already green

    const qtr = tileSize / 4;
    const half = tileSize / 2;

    if (edgeType === 2) { // city
        let points;
        switch (side) {
            case 'N': points = [0, 0, tileSize, 0, tileSize * 0.75, qtr, qtr, qtr]; break;
            case 'E': points = [tileSize, 0, tileSize, tileSize, tileSize - qtr, tileSize * 0.75, tileSize - qtr, qtr]; break;
            case 'S': points = [0, tileSize, tileSize, tileSize, tileSize * 0.75, tileSize - qtr, qtr, tileSize - qtr]; break;
            case 'W': points = [0, 0, 0, tileSize, qtr, tileSize * 0.75, qtr, qtr]; break;
        }
        group.add(new Konva.Line({
            points, fill: COLORS[2], closed: true, stroke: '#6b3410', strokeWidth: 1,
        }));
    } else if (edgeType === 1) { // road
        let points;
        const rw = tileSize * 0.15;
        switch (side) {
            case 'N': points = [half - rw, 0, half + rw, 0, half + rw, qtr, half - rw, qtr]; break;
            case 'E': points = [tileSize, half - rw, tileSize, half + rw, tileSize - qtr, half + rw, tileSize - qtr, half - rw]; break;
            case 'S': points = [half - rw, tileSize, half + rw, tileSize, half + rw, tileSize - qtr, half - rw, tileSize - qtr]; break;
            case 'W': points = [0, half - rw, 0, half + rw, qtr, half + rw, qtr, half - rw]; break;
        }
        group.add(new Konva.Line({
            points, fill: COLORS[1], closed: true,
        }));
    }
}

function drawCenter(group, tile, s) {
    const half = s / 2;
    const center = tile.center;

    if (center === 2) { // monastery
        group.add(new Konva.Rect({
            x: half - 12, y: half - 12, width: 24, height: 24,
            fill: COLORS.monastery, stroke: '#fff', strokeWidth: 1,
            cornerRadius: 3,
        }));
        group.add(new Konva.Line({
            points: [half, half - 18, half - 14, half - 6, half + 14, half - 6],
            fill: COLORS.monastery, closed: true,
        }));
    } else if (center === 3) { // city center
        group.add(new Konva.Circle({
            x: half, y: half, radius: s * 0.3,
            fill: COLORS[2], stroke: '#6b3410', strokeWidth: 1,
        }));
    } else if (center === 4) { // crossroad
        group.add(new Konva.Circle({
            x: half, y: half, radius: 6,
            fill: '#888', stroke: '#666', strokeWidth: 1,
        }));
    }
}

function drawConnections(group, tile, s) {
    const half = s / 2;
    const qtr = s / 4;
    const rw = s * 0.15;
    const edges = tile.edges;

    const sideCenter = {
        0: { x: half, y: qtr },   // N
        1: { x: s - qtr, y: half }, // E
        2: { x: half, y: s - qtr }, // S
        3: { x: qtr, y: half },   // W
    };

    // find connected road edges
    const roadEdges = [];
    for (let i = 0; i < 4; i++) {
        if (edges[i] === 1) roadEdges.push(i);
    }

    if (roadEdges.length === 2 && tile.center !== 4) {
        const [a, b] = roadEdges;
        const pa = sideCenter[a];
        const pb = sideCenter[b];
        group.add(new Konva.Line({
            points: [pa.x - rw, pa.y, pa.x + rw, pa.y, pb.x + rw, pb.y, pb.x - rw, pb.y],
            fill: COLORS[1], closed: true,
        }));
        // simplified: draw a rectangle between the two edge midpoints
        group.add(new Konva.Rect({
            x: Math.min(pa.x, pb.x) - rw,
            y: Math.min(pa.y, pb.y) - rw,
            width: Math.abs(pa.x - pb.x) + rw * 2,
            height: Math.abs(pa.y - pb.y) + rw * 2,
            fill: COLORS[1],
        }));
    }

    // city connections
    const cityEdges = [];
    for (let i = 0; i < 4; i++) {
        if (edges[i] === 2) cityEdges.push(i);
    }
    if (cityEdges.length >= 2 && tile.center === 3) {
        group.add(new Konva.Circle({
            x: half, y: half, radius: s * 0.35,
            fill: COLORS[2], stroke: '#6b3410', strokeWidth: 1,
        }));
    }

    if (tile.shield) {
        group.add(new Konva.Rect({
            x: half - 6, y: half - 6, width: 12, height: 14,
            fill: '#1a5276', stroke: '#fff', strokeWidth: 1, cornerRadius: [0, 0, 6, 6],
        }));
    }
}

function drawHandTile(container, tile, idx, selected, onClick) {
    const canvas = document.createElement('div');
    canvas.className = 'hand-tile' + (selected ? ' selected' : '');
    canvas.style.position = 'relative';
    canvas.id = `hand-tile-${idx}`;

    const stage = new Konva.Stage({
        container: canvas,
        width: 80,
        height: 80,
    });
    const layer = new Konva.Layer();
    stage.add(layer);

    drawTile(layer, tile, 0, 0, 80);
    layer.draw();

    canvas.addEventListener('click', () => onClick(idx));
    container.appendChild(canvas);
    return canvas;
}

export { drawTile, drawHandTile, TILE_SIZE, COLORS };
