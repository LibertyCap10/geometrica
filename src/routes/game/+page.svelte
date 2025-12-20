<script>
  // /src/routes/game/+page.svelte

  import { onMount, onDestroy } from 'svelte';
  import { CFG, DERIVED, spawnInterval, randSpeed } from '$lib/config';

  // Canvas and render state
  let canvas;
  let ctx;
  let width = 0;   // viewport width
  let height = 0;  // viewport height
  let dpr = 1;

  // World (slightly larger than viewport: env-driven)
  let worldWidth = 0;
  let worldHeight = 0;

  // Camera
  const camera = { x: 0, y: 0 };

  // Game state
  let score = 0;
  let multiplier = 1;
  let lives = 3;
  let bombs = 3;
  let paused = false;
  let gameOver = false;
  let respawning = false;
  let respawnTime = 0; // seconds remaining for countdown
  let showHelp = true;

  // Leaderboard prompt state
  let showNamePrompt = false;
  let playerName = '';
  let submitting = false;
  let lbError = '';
  let cap = 25; // fetched from API for qualifies check

  // Points
  const BASE_POINTS = {
    trapezoid: 1,
    square: 3,
    triangle: 5
  };

  // Player (white glowing U ship)
  const player = {
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    baseSpeed: CFG.player.baseSpeed,
    radius: 12,     // hit radius
    angle: 0,       // aim direction (smoothed)
    turnRate: 8.5,  // rad/s max turn speed
    fireRate: CFG.player.fireRate,    // bullets/s
    fireInterval: DERIVED.fireInterval,
    lastFireTime: 0
  };

  // Ship trail (orange glow ribbon)
  const trail = [];
  const trailMax = CFG.trail.max;

  // Boost (env-driven)
  const boost = {
    active: false,
    duration: CFG.player.boostDuration,
    endTime: 0,
    multiplier: CFG.player.boostMultiplier
  };

  // Collections
  const bullets = [];
  const enemies = [];
  const orbs = [];
  const gates = [];
  const floaters = [];   // floating texts (kill scores, orb multipliers)
  const aoeEffects = []; // visual AOE highlight rings when gates trigger

  // Background stars
  const stars = [];
  function makeStars() {
    stars.length = 0;
    const count = Math.floor((worldWidth * worldHeight) / (9000)); // density
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * worldWidth,
        y: Math.random() * worldHeight,
        r: Math.random() * 1.6 + 0.4,
        a: Math.random() * 0.6 + 0.2
      });
    }
  }

  // Timing
  let rafId = 0;
  let lastTime = 0;
  let elapsed = 0; // seconds since start

  // Spawning (env-driven)
  let spawnTimer = 0;
  const maxEnemies = CFG.spawn.maxEnemies;

  // Gates (env-driven)
  let gateSpawnTimer = 0;
  const maxGates = CFG.gates.maxGates;

  // Input
  const keys = new Set();

  // Colors — neon palette inspired by GW
  const COLORS = {
    bg: '#06080f',
    grid: 'rgba(40,80,120,0.35)', // single faint grid color
    bullet: '#ffffff',
    // Player ship
    playerStroke: '#ffffff',
    playerStrokeDim: '#e6efff',
    playerGlow: '#ffffff',
    trail: '#ffb64c',
    // Enemies
    trapStroke: '#8feaff',
    trapGlow: '#bdf5ff',
    square: '#3ec3ff',
    triangle: '#ff5a6d',
    // UI and misc
    uiGreen: '#9aff4f',
    gateLine: '#FFD65C',
    gateGlow: '#FFEAA5',
    timerBg: 'rgba(12,18,26,0.7)',
    timerDigit: '#9aff4f',
    floaterKill: '#FFF59D', // thin light yellow
    orbFill: '#FFD65C',
    orbStroke: '#FFF0B2',
    orbGlow: '#FFEAA5'
  };

  // Utility functions
  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
  }
  function randRange(min, max) {
    return Math.random() * (max - min) + min;
  }
  function normalize(x, y) {
    const len = Math.hypot(x, y);
    return len > 0 ? { x: x / len, y: y / len } : { x: 0, y: 0 };
  }
  function angleTo(ax, ay, bx, by) {
    return Math.atan2(by - ay, bx - ax);
  }
  function nearestEnemy(px, py) {
    if (!enemies.length) return null;
    let best = null;
    let bestDist = Infinity;
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      const dx = e.x - px;
      const dy = e.y - py;
      const d2 = dx * dx + dy * dy;
      if (d2 < bestDist) {
        bestDist = d2;
        best = e;
      }
    }
    return best;
  }
  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const mm = m.toString().padStart(2, '0');
    const ss = s.toString().padStart(2, '0');
    return `${mm}:${ss}`;
  }
  function pointSegmentDistance(px, py, x1, y1, x2, y2) {
    const sx = x2 - x1, sy = y2 - y1;
    const len2 = sx * sx + sy * sy;
    if (len2 === 0) return Math.hypot(px - x1, py - y1);
    const t = Math.max(0, Math.min(1, ((px - x1) * sx + (py - y1) * sy) / len2));
    const cx = x1 + t * sx;
    const cy = y1 + t * sy;
    return Math.hypot(px - cx, py - cy);
  }
  function shortestAngleDiff(a, b) {
    let diff = (b - a + Math.PI) % (2 * Math.PI) - Math.PI;
    if (diff < -Math.PI) diff += 2 * Math.PI;
    return diff;
  }

  // Drawing helpers
  function drawTrapezoid(wTop, wBottom, h) {
    // Upright trapezoid centered at (0,0), top narrower than bottom
    const halfTop = wTop / 2;
    const halfBottom = wBottom / 2;
    const halfH = h / 2;
    ctx.beginPath();
    ctx.moveTo(-halfTop, -halfH); // top-left
    ctx.lineTo(halfTop, -halfH);  // top-right
    ctx.lineTo(halfBottom, halfH); // bottom-right
    ctx.lineTo(-halfBottom, halfH); // bottom-left
    ctx.closePath();
  }

  // Leaderboard prompt helpers (client-side qualifies check)
  async function checkLeaderboardAndPrompt() {
    try {
      const res = await fetch('/api/leaderboard');
      if (!res.ok) {
        showNamePrompt = false;
        return;
      }
      const data = await res.json();
      const entries = Array.isArray(data?.entries) ? data.entries : [];
      cap = typeof data?.cap === 'number' ? data.cap : 25;
      // qualifies if list shorter than cap or score greater than min score
      let qualifiesFlag = false;
      if (entries.length < cap) {
        qualifiesFlag = true;
      } else {
        const minScore = entries[entries.length - 1]?.score ?? 0;
        qualifiesFlag = score > minScore;
      }
      if (qualifiesFlag) {
        // Prefill from localStorage if available
        try {
          const cached = localStorage.getItem('gw_player_name');
          if (cached) playerName = cached;
        } catch {}
        showNamePrompt = true;
        lbError = '';
      }
    } catch {
      // swallow errors; just don't show prompt
      showNamePrompt = false;
    }
  }

  async function submitScore() {
    if (submitting) return;
    const name = (playerName ?? '').trim();
    if (name.length === 0) {
      lbError = 'Please enter a name';
      return;
    }
    submitting = true;
    lbError = '';
    try {
      const res = await fetch('/api/leaderboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, score })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        lbError = data?.message || 'Unable to save score';
      } else {
        // Cache name for convenience
        try {
          localStorage.setItem('gw_player_name', name);
        } catch {}
        showNamePrompt = false;
        // Optional: navigate to leaderboard
        window.location.assign('/leaderboard');
      }
    } catch {
      lbError = 'Network error. Please try again.';
    } finally {
      submitting = false;
    }
  }

  function skipSubmit() {
    showNamePrompt = false;
  }

  // Input handlers
  function onKeyDown(e) {
    const code = e.code;

    // If name prompt is open, handle Enter/Escape and don't move the ship
    if (showNamePrompt) {
      if (code === 'Enter') {
        e.preventDefault();
        submitScore();
        return;
      }
      if (code === 'Escape') {
        e.preventDefault();
        skipSubmit();
        return;
      }
      // Allow typing in the input; don't consume other keys here
    }

    if (
      code === 'KeyW' || code === 'KeyA' || code === 'KeyS' || code === 'KeyD' ||
      code === 'Space' || code.startsWith('Arrow')
    ) {
      e.preventDefault();
    }
    if (code === 'KeyP') {
      paused = !paused;
      if (!paused) lastTime = performance.now();
    } else if (code === 'KeyR') {
      //resetGame();
    } else if (code === 'Escape') {
      paused = !paused;
      if (!paused) lastTime = performance.now();
    } else if (code === 'Space') {
      startBoost();
    } else if (code === 'KeyE') {
      useBomb();
    } else if (code === 'KeyH') {
      showHelp = !showHelp;
    } else if (code === 'KeyW' || code === 'KeyA' || code === 'KeyS' || code === 'KeyD') {
      keys.add(code);
    }
  }
  function onKeyUp(e) {
    const code = e.code;
    if (code === 'KeyW' || code === 'KeyA' || code === 'KeyS' || code === 'KeyD') {
      keys.delete(code);
    }
  }

  function startBoost() {
    if (boost.active) return;
    boost.active = true;
    boost.endTime = elapsed + boost.duration;
  }

  function useBomb() {
    if (respawning || gameOver) return;
    if (bombs <= 0) return;
    bombs -= 1;
    if (enemies.length === 0) return;

    // Kill all enemies and drop orbs; award points for each kill
    for (let j = enemies.length - 1; j >= 0; j--) {
      killEnemyAtIndex(j);
    }
    // Global AOE flash for feedback
    aoeEffects.push({
      x: player.x,
      y: player.y,
      radius: Math.max(worldWidth, worldHeight) * 0.35,
      duration: 0.5,
      time: 0
    });
  }

  function onResize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    width = Math.floor(rect.width);
    height = Math.floor(rect.height);
    dpr = Math.max(1, Math.min(2.5, window.devicePixelRatio || 1)); // clamp dpr
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // draw in CSS pixels

    // World is env-driven scale of viewport
    worldWidth = Math.round(width * CFG.world.scale);
    worldHeight = Math.round(height * CFG.world.scale);

    makeStars();

    // Keep player within world bounds after resize
    player.x = clamp(player.x, player.radius, worldWidth - player.radius);
    player.y = clamp(player.y, player.radius, worldHeight - player.radius);

    // Update camera to follow player
    camera.x = clamp(player.x - width / 2, 0, Math.max(0, worldWidth - width));
    camera.y = clamp(player.y - height / 2, 0, Math.max(0, worldHeight - height));
  }

  function resetGame() {
    score = 0;
    multiplier = 1;
    lives = 3;
    bombs = 3;
    gameOver = false;
    respawning = false;
    respawnTime = 0;
    showHelp = true;

    showNamePrompt = false;
    playerName = '';
    submitting = false;
    lbError = '';

    bullets.length = 0;
    enemies.length = 0;
    orbs.length = 0;
    gates.length = 0;
    floaters.length = 0;
    trail.length = 0;
    aoeEffects.length = 0;

    elapsed = 0;
    spawnTimer = 0;
    gateSpawnTimer = 0;

    boost.active = false;
    boost.endTime = 0;

    player.x = worldWidth / 2;
    player.y = worldHeight / 2;
    player.vx = 0;
    player.vy = 0;
    player.angle = 0;
    player.lastFireTime = 0;

    // Initial spawns
    for (let i = 0; i < 3; i++) spawnTrapezoidGroup(groupSizeForTime(elapsed));
    for (let i = 0; i < 6; i++) spawnEnemy(weightedType(elapsed));
    if (gates.length < maxGates) spawnGate();
  }

  function clearMap() {
    bullets.length = 0;
    enemies.length = 0;
    orbs.length = 0;
    gates.length = 0;
    floaters.length = 0;
    trail.length = 0;
    aoeEffects.length = 0;
    spawnTimer = 0;
    gateSpawnTimer = 0;
  }

  // Spawning helpers
  function weightedType(tSec) {
    // Increase triangles over time, keep some squares; trapezoids handled by group spawns more frequently
    const t = clamp(tSec / 90, 0, 1);
    let wTriangle = 0.45 + 0.35 * t;
    let wSquare = 0.55 - 0.25 * t;
    const sum = wTriangle + wSquare;
    const r = Math.random() * sum;
    return r < wTriangle ? 'triangle' : 'square';
  }

  function randomCornerPosition(radius) {
    const margin = radius + 12;
    const corner = Math.floor(Math.random() * 4); // 0: TL, 1: TR, 2: BR, 3: BL
    let x = margin;
    let y = margin;
    if (corner === 0) { // TL
      x = margin; y = margin;
    } else if (corner === 1) { // TR
      x = worldWidth - margin; y = margin;
    } else if (corner === 2) { // BR
      x = worldWidth - margin; y = worldHeight - margin;
    } else if (corner === 3) { // BL
      x = margin; y = worldHeight - margin;
    }
    return { x, y, corner };
  }

  function groupSizeForTime(tSec) {
    // 4..8, increases slightly over time
    const t = clamp(tSec / 120, 0, 1);
    return 4 + Math.floor(4 * t);
  }

  function spawnTrapezoidGroup(count) {
    if (enemies.length >= maxEnemies) return;
    const baseRadius = 12;
    const basePos = randomCornerPosition(baseRadius);
    const groupId = Math.random().toString(36).slice(2);
    for (let i = 0; i < count && enemies.length < maxEnemies; i++) {
      const offset = 24;
      const jitterX = randRange(-offset, offset);
      const jitterY = randRange(-offset, offset);
      const e = {
        id: Math.random().toString(36).slice(2),
        type: 'trapezoid',
        x: clamp(basePos.x + jitterX, baseRadius, worldWidth - baseRadius),
        y: clamp(basePos.y + jitterY, baseRadius, worldHeight - baseRadius),
        vx: 0,
        vy: 0,
        speed: randSpeed(CFG.enemies.trap.speedMin, CFG.enemies.trap.speedMax),
        radius: baseRadius, // collision radius
        stroke: COLORS.trapStroke,
        groupId,
        rot: randRange(0, Math.PI * 2),
        rotVel: randRange(-0.8, 0.8)
      };
      const dir = normalize(worldWidth / 2 - e.x, worldHeight / 2 - e.y);
      e.vx = dir.x * e.speed;
      e.vy = dir.y * e.speed;
      enemies.push(e);
    }
  }

  function spawnEnemy(type) {
    if (enemies.length >= maxEnemies) return;
    let enemy = {
      id: Math.random().toString(36).slice(2),
      type,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      speed: 0,
      radius: 0,
      color: '#999',
      changeDirTimer: 0,
      offsetAngle: 0,
      dashTimer: 0,
      rot: 0,
      rotVel: 0
    };

    if (type === 'square') {
      enemy.radius = 14;
      enemy.speed = randSpeed(CFG.enemies.square.speedMin, CFG.enemies.square.speedMax);
      enemy.color = COLORS.square;
      enemy.changeDirTimer = randRange(0.8, 1.4);
      const sign = Math.random() < 0.5 ? -1 : 1;
      enemy.offsetAngle = sign * randRange(Math.PI / 6, Math.PI / 3);
      enemy.rotVel = randRange(-0.6, 0.6);
    } else if (type === 'triangle') {
      enemy.radius = 10;
      enemy.speed = randSpeed(CFG.enemies.triangle.baseMin, CFG.enemies.triangle.baseMax); // fast!
      enemy.color = COLORS.triangle;
      enemy.dashTimer = randRange(1.1, 2.0); // occasional sprints
    }

    const pos = randomCornerPosition(enemy.radius);
    enemy.x = pos.x;
    enemy.y = pos.y;

    const dir = normalize(worldWidth / 2 - enemy.x, worldHeight / 2 - enemy.y);
    enemy.vx = dir.x * enemy.speed;
    enemy.vy = dir.y * enemy.speed;

    enemies.push(enemy);
  }

  function spawnGate() {
    const length = CFG.gates.length;
    const thickness = CFG.gates.thickness;
    const margin = length / 2 + 20; // keep full segment in world
    const g = {
      id: Math.random().toString(36).slice(2),
      x: randRange(margin, worldWidth - margin),
      y: randRange(margin, worldHeight - margin),
      vx: randRange(-60, 60),
      vy: randRange(-60, 60),
      length,
      thickness,
      angle: randRange(0, Math.PI * 2),
      angVel: randRange(-0.3, 0.3)
    };
    gates.push(g);
  }

  function spawnOrb(x, y) {
    const o = {
      id: Math.random().toString(36).slice(2),
      x, y,
      vx: randRange(-20, 20),
      vy: randRange(-20, 20),
      radius: 2,
      magnetRange: CFG.orbs.magnetRange,
      seed: Math.random() * Math.PI * 2
    };
    orbs.push(o);
  }

  function addFloaterKill(text, x, y, value = 0) {
    floaters.push({
      type: 'kill',
      text,
      x,
      y,
      duration: 1.2,
      time: 0,
      startY: y,
      peakOffset: 24,
      value
    });
  }
  function addFloaterOrb(text, x, y) {
    floaters.push({
      type: 'orb',
      text,
      x,
      y,
      duration: 1.2,
      time: 0,
      startY: y,
      peakOffset: 26
    });
  }

  function killEnemyAtIndex(j) {
    const e = enemies[j];
    const pts = (BASE_POINTS[e.type] || 1) * multiplier;
    score += pts;

    // thin, light yellow kill numbers
    addFloaterKill(`+${pts}`, e.x, e.y - (e.radius + 6), pts);

    // drop golden orb
    spawnOrb(e.x, e.y);

    enemies.splice(j, 1);
  }

  function onPlayerHit() {
    if (respawning || gameOver) return;
    lives -= 1;
    clearMap();
    // center player
    player.x = worldWidth / 2;
    player.y = worldHeight / 2;
    player.vx = 0;
    player.vy = 0;
    respawning = true;
    respawnTime = 3; // 3..2..1 countdown
    if (lives <= 0) {
      gameOver = true;
      respawning = false;
      // Check leaderboard and prompt for name if qualifies
      checkLeaderboardAndPrompt();
    }
  }

  // Update functions
  function update(dt) {
    if (paused) return;

    elapsed += dt;

    // Boost management
    if (boost.active && elapsed >= boost.endTime) {
      boost.active = false;
    }

    if (gameOver) return;

    // Handle respawn countdown
    if (respawning) {
      respawnTime -= dt;
      if (respawnTime <= 0) {
        respawning = false;
      }
      camera.x = clamp(player.x - width / 2, 0, Math.max(0, worldWidth - width));
      camera.y = clamp(player.y - height / 2, 0, Math.max(0, worldHeight - height));
      return;
    }

    // Movement (env-driven)
    const currentSpeed = player.baseSpeed * (boost.active ? boost.multiplier : 1);
    let mx = 0, my = 0;
    if (keys.has('KeyA')) mx -= 1;
    if (keys.has('KeyD')) mx += 1;
    if (keys.has('KeyW')) my -= 1;
    if (keys.has('KeyS')) my += 1;
    if (mx !== 0 || my !== 0) {
      const dir = normalize(mx, my);
      player.vx = dir.x * currentSpeed;
      player.vy = dir.y * currentSpeed;
    } else {
      player.vx = 0;
      player.vy = 0;
    }

    player.x = clamp(player.x + player.vx * dt, player.radius, worldWidth - player.radius);
    player.y = clamp(player.y + player.vy * dt, player.radius, worldHeight - player.radius);

    camera.x = clamp(player.x - width / 2, 0, Math.max(0, worldWidth - width));
    camera.y = clamp(player.y - height / 2, 0, Math.max(0, worldHeight - height));

    // Auto-aim with smooth rotation
    const target = nearestEnemy(player.x, player.y);
    if (target) {
      const targetAngle = angleTo(player.x, player.y, target.x, target.y);
      const diff = shortestAngleDiff(player.angle, targetAngle);
      const maxStep = player.turnRate * dt;
      const step = clamp(diff, -maxStep, maxStep);
      player.angle += step;
    }

    // Auto-fire
    if (target) {
      const nowSec = elapsed;
      if (nowSec - player.lastFireTime >= player.fireInterval) {
        fireBullet();
        player.lastFireTime = nowSec;
      }
    }

    // Update ship trail (rear point attached smoothly)
    const rearX = player.x - Math.cos(player.angle) * (player.radius + 2);
    const rearY = player.y - Math.sin(player.angle) * (player.radius + 2);
    trail.push({ x: rearX, y: rearY, life: 0 });
    while (trail.length > trailMax) trail.shift();
    for (let i = 0; i < trail.length; i++) {
      trail[i].life += dt;
    }

    // Update bullets (env-driven)
    for (let i = bullets.length - 1; i >= 0; i--) {
      const b = bullets[i];
      b.x += b.vx * dt;
      b.y += b.vy * dt;
      b.life -= dt;
      if (b.life <= 0 || b.x < -20 || b.x > worldWidth + 20 || b.y < -20 || b.y > worldHeight + 20) {
        bullets.splice(i, 1);
        continue;
      }
      // Collision with enemies
      let hit = false;
      for (let j = enemies.length - 1; j >= 0; j--) {
        const e = enemies[j];
        const dx = e.x - b.x;
        const dy = e.y - b.y;
        const rr = (e.radius + CFG.bullet.radius);
        if (dx * dx + dy * dy <= rr * rr) {
          bullets.splice(i, 1);
          killEnemyAtIndex(j);
          hit = true;
          break;
        }
      }
      if (hit) continue;
    }

    // Prepare trapezoid group centroids for swarming
    const centroids = new Map();
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      if (e.type === 'trapezoid' && e.groupId) {
        const entry = centroids.get(e.groupId);
        if (!entry) {
          centroids.set(e.groupId, { x: e.x, y: e.y, count: 1 });
        } else {
          entry.x += e.x; entry.y += e.y; entry.count += 1;
        }
      }
    }
    centroids.forEach((v) => {
      v.x /= v.count; v.y /= v.count;
    });

    // Update enemies (env-driven speeds)
    let playerTouched = false;
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      if (e.type === 'trapezoid') {
        const toPlayer = normalize(player.x - e.x, player.y - e.y);
        let toGroup = { x: 0, y: 0 };
        if (e.groupId && centroids.has(e.groupId)) {
          const c = centroids.get(e.groupId);
          toGroup = normalize(c.x - e.x, c.y - e.y);
        }
        const wPlayer = 0.72;
        const wGroup = 0.28;
        const dir = normalize(toPlayer.x * wPlayer + toGroup.x * wGroup, toPlayer.y * wPlayer + toGroup.y * wGroup);
        e.vx = dir.x * e.speed;
        e.vy = dir.y * e.speed;
        e.rot += e.rotVel * dt;
      } else if (e.type === 'square') {
        e.changeDirTimer -= dt;
        if (e.changeDirTimer <= 0) {
          e.changeDirTimer = randRange(0.8, 1.4);
          const sign = Math.random() < 0.5 ? -1 : 1;
          e.offsetAngle = sign * randRange(Math.PI / 6, Math.PI / 3);
        }
        const baseAngle = angleTo(e.x, e.y, player.x, player.y);
        const angled = baseAngle + e.offsetAngle;
        e.vx = Math.cos(angled) * e.speed;
        e.vy = Math.sin(angled) * e.speed;
        e.rot += (e.rotVel || 0) * dt;
      } else if (e.type === 'triangle') {
        e.dashTimer -= dt;
        const leadTime = 0.2;
        const aimX = player.x + player.vx * leadTime;
        const aimY = player.y + player.vy * leadTime;
        const dir = normalize(aimX - e.x, aimY - e.y);
        let speed = e.speed;
        if (e.dashTimer <= 0) {
          speed = e.speed + CFG.enemies.triangle.dashBonus;
          e.dashTimer = randRange(1.2, 2.2);
        }
        e.vx = dir.x * speed;
        e.vy = dir.y * speed;
      }

      e.x += e.vx * dt;
      e.y += e.vy * dt;

      // bounce off world bounds
      if (e.x < e.radius) {
        e.x = e.radius;
        e.vx = Math.abs(e.vx);
      } else if (e.x > worldWidth - e.radius) {
        e.x = worldWidth - e.radius;
        e.vx = -Math.abs(e.vx);
      }
      if (e.y < e.radius) {
        e.y = e.radius;
        e.vy = Math.abs(e.vy);
      } else if (e.y > worldHeight - e.radius) {
        e.y = worldHeight - e.radius;
        e.vy = -Math.abs(e.vy);
      }

      // Check player touch
      const dxp = e.x - player.x;
      const dyp = e.y - player.y;
      const rr = (e.radius + player.radius) * (e.radius + player.radius);
      if (dxp * dxp + dyp * dyp <= rr) {
        playerTouched = true;
      }
    }

    if (playerTouched) {
      onPlayerHit();
      return;
    }

    // Update orbs (env-driven magnet + seek + wander)
    for (let i = orbs.length - 1; i >= 0; i--) {
      const o = orbs[i];
      let dx = player.x - o.x;
      let dy = player.y - o.y;
      let dist = Math.hypot(dx, dy);
      if (dist < o.magnetRange) {
        const dir = normalize(dx, dy);
        const targetVx = dir.x * CFG.orbs.seekSpeed;
        const targetVy = dir.y * CFG.orbs.seekSpeed;
        o.vx = o.vx * 0.85 + targetVx * 0.15;
        o.vy = o.vy * 0.85 + targetVy * 0.15;
      } else {
        // gentle wander
        o.vx += Math.cos(elapsed * 0.8 + o.seed) * CFG.orbs.wanderForce * dt;
        o.vy += Math.sin(elapsed * 0.8 + o.seed) * CFG.orbs.wanderForce * dt;
        o.vx *= 0.995;
        o.vy *= 0.995;
        const sp = Math.hypot(o.vx, o.vy);
        if (sp > 40) {
          const n = normalize(o.vx, o.vy);
          o.vx = n.x * 40;
          o.vy = n.y * 40;
        }
      }
      o.x += o.vx * dt;
      o.y += o.vy * dt;

      o.x = clamp(o.x, o.radius, worldWidth - o.radius);
      o.y = clamp(o.y, o.radius, worldHeight - o.radius);

      dx = player.x - o.x;
      dy = player.y - o.y;
      dist = Math.hypot(dx, dy);

      if (dist <= player.radius + o.radius) {
        multiplier += 1;
        addFloaterOrb(`×${multiplier}`, player.x, player.y - (player.radius + 10));
        orbs.splice(i, 1);
      }
    }

    // Update gates (env-driven properties)
    for (let i = gates.length - 1; i >= 0; i--) {
      const g = gates[i];
      g.angle += g.angVel * dt;
      g.x += g.vx * dt;
      g.y += g.vy * dt;

      const hx = Math.cos(g.angle) * (g.length / 2);
      const hy = Math.sin(g.angle) * (g.length / 2);
      const marginX = Math.abs(hx) + 10;
      const marginY = Math.abs(hy) + 10;

      if (g.x < marginX) { g.x = marginX; g.vx = Math.abs(g.vx); }
      else if (g.x > worldWidth - marginX) { g.x = worldWidth - marginX; g.vx = -Math.abs(g.vx); }
      if (g.y < marginY) { g.y = marginY; g.vy = Math.abs(g.vy); }
      else if (g.y > worldHeight - marginY) { g.y = worldHeight - marginY; g.vy = -Math.abs(g.vy); }

      const x1 = g.x - hx, y1 = g.y - hy;
      const x2 = g.x + hx, y2 = g.y + hy;
      const distToLine = pointSegmentDistance(player.x, player.y, x1, y1, x2, y2);
      if (distToLine <= player.radius + g.thickness / 2) {
        triggerGateAOE(g);
        gates.splice(i, 1); // gate disappears
      }
    }

    // AOE visual effects
    for (let i = aoeEffects.length - 1; i >= 0; i--) {
      const fx = aoeEffects[i];
      fx.time += dt;
      if (fx.time >= fx.duration) {
        aoeEffects.splice(i, 1);
      }
    }

    // Update floaters
    for (let i = floaters.length - 1; i >= 0; i--) {
      const f = floaters[i];
      f.time += dt;
      const t = f.time / f.duration;
      if (t >= 1) {
        floaters.splice(i, 1);
        continue;
      }
      const ease = 1 - Math.pow(1 - t, 2);
      const offset = ease * f.peakOffset;
      f.y = f.startY - offset;
    }

    // Spawns (env-driven exponential/linear)
    const interval = spawnInterval(elapsed);
    spawnTimer += dt;
    if (spawnTimer >= interval) {
      spawnTimer = 0;
      if (enemies.length < maxEnemies) {
        const r = Math.random();
        if (r < CFG.spawn.groupChance) {
          spawnTrapezoidGroup(groupSizeForTime(elapsed));
        } else {
          spawnEnemy(weightedType(elapsed));
        }
      }
    }

    // Gate spawning at regular intervals (env-driven)
    gateSpawnTimer += dt;
    if (gateSpawnTimer >= CFG.gates.spawnInterval) {
      gateSpawnTimer = 0;
      if (gates.length < maxGates) {
        spawnGate();
      }
    }
  }

  function triggerGateAOE(gate) {
    // Kill enemies within AOE radius from gate center
    for (let j = enemies.length - 1; j >= 0; j--) {
      const e = enemies[j];
      const dx = e.x - gate.x;
      const dy = e.y - gate.y;
      if (dx * dx + dy * dy <= CFG.gates.aoeRadius * CFG.gates.aoeRadius) {
        killEnemyAtIndex(j);
      }
    }
    // Visual AOE circle highlight (no text)
    aoeEffects.push({
      x: gate.x,
      y: gate.y,
      radius: CFG.gates.aoeRadius,
      duration: 0.65,
      time: 0
    });
  }

  function fireBullet() {
    const bulletSpeed = CFG.bullet.speed;
    const bulletLife = CFG.bullet.life;
    const bRadius = CFG.bullet.radius;
    // U-ship front is along +x local, so spawn at front edge
    const frontOffset = player.radius + 2;
    const bx = player.x + Math.cos(player.angle) * frontOffset;
    const by = player.y + Math.sin(player.angle) * frontOffset;
    const bvx = Math.cos(player.angle) * bulletSpeed;
    const bvy = Math.sin(player.angle) * bulletSpeed;
    bullets.push({
      x: bx,
      y: by,
      vx: bvx,
      vy: bvy,
      radius: bRadius,
      life: bulletLife
    });
  }

  // Drawing
  function drawGrid() {
    // Single faint, fixed grid (env-driven spacing)
    const spacing = CFG.world.gridSpacing;
    ctx.save();
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;

    // Vertical
    for (
      let x = Math.floor(camera.x / spacing) * spacing;
      x <= Math.min(camera.x + width, worldWidth);
      x += spacing
    ) {
      ctx.beginPath();
      ctx.moveTo(x, camera.y);
      ctx.lineTo(x, camera.y + height);
      ctx.stroke();
    }

    // Horizontal
    for (
      let y = Math.floor(camera.y / spacing) * spacing;
      y <= Math.min(camera.y + height, worldHeight);
      y += spacing
    ) {
      ctx.beginPath();
      ctx.moveTo(camera.x, y);
      ctx.lineTo(camera.x + width, y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawStars() {
    ctx.save();
    for (let i = 0; i < stars.length; i++) {
      const s = stars[i];
      if (s.x < camera.x - 2 || s.x > camera.x + width + 2 || s.y < camera.y - 2 || s.y > camera.y + height + 2) continue;
      ctx.globalAlpha = s.a;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function drawPlayer() {
    // White glowing U bracket ship, with coherent tapered orange glow trail
    ctx.save();
    ctx.translate(player.x, player.y);
    ctx.rotate(player.angle);

    const r = player.radius;
    const t = 6; // line thickness
    ctx.lineWidth = t;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Ship glow
    ctx.shadowColor = COLORS.playerGlow;
    ctx.shadowBlur = 14;

    // Top segment
    ctx.strokeStyle = COLORS.playerStroke;
    ctx.beginPath();
    ctx.moveTo(-r, -r);
    ctx.lineTo(r, -r);
    ctx.stroke();

    // Bottom segment
    ctx.beginPath();
    ctx.moveTo(-r, r);
    ctx.lineTo(r, r);
    ctx.stroke();

    // Back (left) vertical segment (slightly dimmer to suggest depth)
    ctx.strokeStyle = COLORS.playerStrokeDim;
    ctx.beginPath();
    ctx.moveTo(-r, -r);
    ctx.lineTo(-r, r);
    ctx.stroke();

    ctx.shadowBlur = 0;
    ctx.restore();

    // Tapered glow ribbon trail attached to rear
    ctx.save();
    for (let i = 1; i < trail.length; i++) {
      const p0 = trail[i - 1];
      const p1 = trail[i];
      const life = trail[i].life;
      const a = clamp(1 - life * 1.8, 0, 1);
      if (a <= 0) continue;

      // Width tapers over life
      const w = 6 * a;

      // Draw as a stroked line with shadow, then a thinner inner stroke for brightness
      ctx.strokeStyle = COLORS.trail;
      ctx.lineWidth = w;
      ctx.shadowColor = COLORS.trail;
      ctx.shadowBlur = 8 * a;
      ctx.globalAlpha = a * 0.7;

      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();

      // inner bright core
      ctx.lineWidth = Math.max(1, w * 0.4);
      ctx.globalAlpha = a;
      ctx.shadowBlur = 0;
      ctx.strokeStyle = '#ffd78a';
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function drawBullets() {
    ctx.save();
    ctx.fillStyle = COLORS.bullet;
    ctx.shadowColor = COLORS.bullet;
    ctx.shadowBlur = 8;
    for (let i = 0; i < bullets.length; i++) {
      const b = bullets[i];
      ctx.beginPath();
      ctx.arc(b.x, b.y, CFG.bullet.radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  function drawEnemies() {
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      ctx.save();
      ctx.translate(e.x, e.y);
      ctx.lineWidth = 2;

      if (e.type === 'trapezoid') {
        // Neon trapezoid outline with glow
        ctx.rotate(e.rot);
        const wTop = e.radius * 1.0;
        const wBottom = e.radius * 1.8;
        const h = e.radius * 1.6;

        ctx.shadowColor = COLORS.trapGlow;
        ctx.shadowBlur = 16;
        ctx.strokeStyle = COLORS.trapStroke;
        ctx.fillStyle = 'transparent';
        drawTrapezoid(wTop, wBottom, h);
        ctx.stroke();
        ctx.shadowBlur = 0;
      } else if (e.type === 'square') {
        ctx.rotate(e.rot);
        ctx.shadowColor = '#aee7ff';
        ctx.shadowBlur = 12;
        ctx.strokeStyle = COLORS.square;
        ctx.fillStyle = 'transparent';
        ctx.beginPath();
        ctx.rect(-e.radius, -e.radius, e.radius * 2, e.radius * 2);
        ctx.stroke();
        ctx.shadowBlur = 0;
      } else if (e.type === 'triangle') {
        // Upright red triangles (do not rotate with velocity)
        ctx.shadowColor = '#ffb3bd';
        ctx.shadowBlur = 12;
        ctx.strokeStyle = COLORS.triangle;
        ctx.fillStyle = 'transparent';
        ctx.beginPath();
        ctx.moveTo(0, -e.radius);             // top
        ctx.lineTo(e.radius, e.radius);       // bottom right
        ctx.lineTo(-e.radius, e.radius);      // bottom left
        ctx.closePath();
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      ctx.restore();
    }
  }

  function drawOrbs() {
    ctx.save();
    for (let i = 0; i < orbs.length; i++) {
      const o = orbs[i];
      // Small golden dot with a thin ring, light glow
      ctx.shadowColor = COLORS.orbGlow;
      ctx.shadowBlur = 6;
      ctx.fillStyle = COLORS.orbFill;
      ctx.strokeStyle = COLORS.orbStroke;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(o.x, o.y, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;
      // tiny inner dot
      ctx.fillStyle = '#FFF6CC';
      ctx.beginPath();
      ctx.arc(o.x, o.y, 0.8, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawGates() {
    ctx.save();
    for (let i = 0; i < gates.length; i++) {
      const g = gates[i];
      const hx = Math.cos(g.angle) * (g.length / 2);
      const hy = Math.sin(g.angle) * (g.length / 2);
      const x1 = g.x - hx, y1 = g.y - hy;
      const x2 = g.x + hx, y2 = g.y + hy;

      // Glow
      ctx.strokeStyle = COLORS.gateGlow;
      ctx.lineWidth = g.thickness + 4;
      ctx.globalAlpha = 0.25;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Main golden line
      ctx.globalAlpha = 1;
      ctx.strokeStyle = COLORS.gateLine;
      ctx.lineWidth = g.thickness;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawAOEEffects() {
    ctx.save();
    for (let i = 0; i < aoeEffects.length; i++) {
      const fx = aoeEffects[i];
      const t = fx.time / fx.duration; // 0..1
      const alpha = 1 - t;
      // Outer pulse ring
      ctx.globalAlpha = Math.max(0, alpha * 0.7);
      ctx.strokeStyle = COLORS.gateGlow;
      ctx.lineWidth = 6 * alpha + 2;
      ctx.beginPath();
      ctx.arc(fx.x, fx.y, fx.radius, 0, Math.PI * 2);
      ctx.stroke();

      // Inner crisp ring
      ctx.globalAlpha = Math.max(0, alpha);
      ctx.strokeStyle = COLORS.gateLine;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(fx.x, fx.y, fx.radius - 4, 0, Math.PI * 2);
      ctx.stroke();

      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  function drawBoostStatus() {
    if (!boost.active) return;
    const remaining = Math.max(0, boost.endTime - elapsed);
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.fillRect(10, height - 40, 160, 28);
    ctx.fillStyle = COLORS.uiGreen;
    ctx.font = 'bold 14px Menlo, Consolas, Monaco, monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(`Boost: ${remaining.toFixed(1)}s`, 16, height - 26);
    ctx.restore();
  }

  function drawTimer() {
    const t = formatTime(elapsed);
    ctx.save();
    const blockWidth = 220;
    const blockHeight = 40;
    const x = width / 2 - blockWidth / 2;
    const y = 8;

    ctx.fillStyle = COLORS.timerBg;
    ctx.fillRect(x, y, blockWidth, blockHeight);

    ctx.strokeStyle = '#1f2630';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, blockWidth, blockHeight);

    ctx.fillStyle = COLORS.timerDigit;
    ctx.font = 'bold 28px Menlo, Consolas, Monaco, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = COLORS.uiGreen;
    ctx.shadowBlur = 8;
    ctx.fillText(t, x + blockWidth / 2, y + blockHeight / 2);
    ctx.shadowBlur = 0;

    ctx.restore();
  }

  function drawBackground() {
    ctx.save();
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  }

  function drawFloaters() {
    ctx.save();
    for (let i = 0; i < floaters.length; i++) {
      const f = floaters[i];
      const t = f.time / f.duration;
      const alpha = 1 - t;
      const scale = 1.0 - 0.05 * t;

      ctx.save();
      ctx.translate(f.x, f.y);
      ctx.scale(scale, scale);
      ctx.globalAlpha = alpha;

      if (f.type === 'kill') {
        // Thin, light yellow kill numbers
        ctx.font = '300 18px Menlo, Consolas, Monaco, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = COLORS.floaterKill;
        ctx.fillText(f.text, 0, 0);
      } else {
        // Neon arcade gradient for orb multiplier pickup (show new total multiplier)
        const grad = ctx.createLinearGradient(0, -20, 0, 20);
        grad.addColorStop(0, '#ff6ec7'); // pink
        grad.addColorStop(1, '#00eaff'); // aqua

        ctx.font = 'bold 20px Menlo, Consolas, Monaco, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';

        // Outline
        ctx.lineWidth = 3;
        ctx.strokeStyle = '#ffffff';
        ctx.strokeText(f.text, 0, 0);

        // Fill gradient
        ctx.fillStyle = grad;
        ctx.fillText(f.text, 0, 0);
      }

      ctx.restore();
    }
    ctx.restore();
  }

  function drawRespawnCountdown() {
    if (!respawning) return;
    const seconds = Math.ceil(respawnTime);
    if (seconds <= 0) return;
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = COLORS.uiGreen;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 64px Menlo, Consolas, Monaco, monospace';
    ctx.shadowColor = COLORS.uiGreen;
    ctx.shadowBlur = 12;
    ctx.fillText(`${seconds}`, width / 2, height / 2);
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  function drawGameOver() {
    if (!gameOver) return;
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 36px system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
    ctx.fillText('Game Over', width / 2, height / 2 - 20);
    ctx.font = 'bold 16px system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
    ctx.fillText('Use the Reset button to play again', width / 2, height / 2 + 20);
    ctx.restore();
  }

  function draw() {
    // Clear & overlay background
    drawBackground();

    // World draw (apply camera transform)
    ctx.save();
    ctx.translate(-camera.x, -camera.y);

    drawStars();
    drawGrid();
    drawBullets();
    drawEnemies();
    drawOrbs();
    drawGates();
    drawAOEEffects(); // visual highlight for triggered gates
    drawPlayer();
    drawFloaters();

    ctx.restore();

    // Overlay HUD
    drawTimer();
    drawBoostStatus();

    // Paused overlay
    if (paused && !gameOver) {
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.45)';
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = 'bold 24px system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
      ctx.fillText('Paused', width / 2, height / 2);
      ctx.restore();
    }

    // Respawn countdown overlay
    drawRespawnCountdown();

    // Game over overlay
    drawGameOver();
  }

  function loop(now) {
    if (!lastTime) lastTime = now;
    let dt = (now - lastTime) / 1000;
    dt = Math.min(dt, 0.05);
    lastTime = now;

    update(dt);
    draw();

    rafId = requestAnimationFrame(loop);
  }

  // Store handlers so we can remove them safely
  const onBlur = () => {
    paused = true;
  };
  const onVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      paused = true;
    } else {
      paused = false;
      lastTime = performance.now();
    }
  };

  onMount(() => {
    ctx = canvas.getContext('2d', { alpha: false });
    onResize();

    // Center player in world
    player.x = worldWidth / 2;
    player.y = worldHeight / 2;

    // Initial spawns
    for (let i = 0; i < 3; i++) spawnTrapezoidGroup(groupSizeForTime(elapsed));
    for (let i = 0; i < 6; i++) spawnEnemy(weightedType(elapsed));
    if (gates.length < maxGates) spawnGate();

    window.addEventListener('keydown', onKeyDown, { passive: false });
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('resize', onResize);
    window.addEventListener('blur', onBlur);
    document.addEventListener('visibilitychange', onVisibilityChange);

    rafId = requestAnimationFrame(loop);
  });

  onDestroy(() => {
    // Guard for SSR — only run in browser
    if (typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(rafId);
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('blur', onBlur);
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', onVisibilityChange);
    }
  });
</script>

<div class="game-container">
  <canvas bind:this={canvas} class="game-canvas"></canvas>

  <div class="hud">
    <div class="stat">Score: {score.toLocaleString()}</div>
    <div class="stat">×{multiplier}</div>
    <div class="stat">Lives: {'♥'.repeat(lives)}</div>
    <div class="stat">Bombs: {bombs}</div>

    <div class="controls">
      <button class="btn" on:click={() => { if (!gameOver) { paused = !paused; if (!paused) lastTime = performance.now(); } }}>
        {paused && !gameOver ? 'Resume' : 'Pause'}
      </button>
      <button class="btn" on:click={resetGame}>Reset</button>
      <a class="btn" href="/">Exit</a>
    </div>
  </div>

{#if showHelp}
  <div class="hint">
    WASD: Move • Space: Boost • E: Bomb • H: Help • Touch enemy = lose life • Gates cause AOE
  </div>
{/if}


  {#if showNamePrompt}
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-content">
        <h2 class="modal-title">New High Score!</h2>
        <p class="modal-desc">You made the Top {cap}. Enter your name to save your score.</p>
        <input
          class="input"
          type="text"
          maxlength="24"
          bind:value={playerName}
          placeholder="Your name"
          autofocus
        />
        {#if lbError}
          <p class="modal-desc" style="color:#ff8585;">{lbError}</p>
        {/if}
        <div class="modal-actions">
          <button class="btn primary" disabled={submitting} on:click={submitScore}>
            {submitting ? 'Saving...' : 'Save Score'}
          </button>
          <button class="btn" disabled={submitting} on:click={skipSubmit}>Skip</button>
        </div>
      </div>
    </div>
  {/if}
</div>