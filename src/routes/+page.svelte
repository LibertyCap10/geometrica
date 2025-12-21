<!-- src/routes/game/+page.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import { CFG, DERIVED, spawnInterval, randSpeed } from '$lib/config';

  // Canvas and render state
  let canvas;
  let ctx;
  let width = 0;
  let height = 0;
  let dpr = 1;

  // Zoom
  const ZOOMS = [1, 0.75, 0.5];
  let zoomIndex = 0;
  let zoomInitialized = false;
  $: zoom = ZOOMS[zoomIndex] ?? 1;

  function cycleZoom() {
    zoomIndex = (zoomIndex + 1) % ZOOMS.length;
    makeStars();
    updateCamera();
  }

  // World
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
  let respawnTime = 0;
  let showHelp = true;

  // Leaderboard state
  let showNamePrompt = false;
  let playerName = '';
  let submitting = false;
  let lbError = '';
  let cap = 25;

  // HUD auto-hide
  let hudVisible = true;
  let hudHideTimer;
  let activityHandler;

  function bumpHudActivity() {
    hudVisible = true;
    if (hudHideTimer) clearTimeout(hudHideTimer);
    hudHideTimer = setTimeout(() => {
      if (!paused && !gameOver) {
        hudVisible = false;
      }
    }, 3000);
  }

  // Orientation hint (used only in pause menu now)
  let showRotateHint = false;

  function evaluateOrientation() {
    if (!isTouchLike) {
      showRotateHint = false;
      return;
    }
    showRotateHint = window.innerHeight > window.innerWidth * 1.8;
  }

  // Fullscreen state
  let isFullscreen = false;

  async function toggleFullscreen() {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    try {
      if (!document.fullscreenElement && root.requestFullscreen) {
        await root.requestFullscreen();
      } else if (document.fullscreenElement && document.exitFullscreen) {
        await document.exitFullscreen();
      }
    } catch (err) {
      console.error('Fullscreen toggle failed', err);
    }
  }

  function handleFullscreenChange() {
    if (typeof document === 'undefined') return;
    isFullscreen = !!document.fullscreenElement;
  }

  // Points
  const BASE_POINTS = {
    trapezoid: 1,
    square: 3,
    triangle: 5
  };

  // Player
  const player = {
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    baseSpeed: CFG.player.baseSpeed,
    radius: 12,
    angle: 0,
    turnRate: 8.5,
    fireRate: CFG.player.fireRate,
    fireInterval:
      DERIVED.player ? 1 / CFG.player.fireRate : DERIVED.fireInterval ?? 1 / CFG.player.fireRate,
    lastFireTime: 0
  };

  // Trail
  const trail = [];
  const trailMax = CFG.trail.max;

  // Boost
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
  const floaters = [];
  const aoeEffects = [];

  // Stars
  const stars = [];
  function makeStars() {
    stars.length = 0;
    if (!worldWidth || !worldHeight) return;
    const count = Math.floor((worldWidth * worldHeight) / 9000);
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
  let elapsed = 0;

  // Spawning
  let spawnTimer = 0;
  const maxEnemies = CFG.enemies.maxEnemies ?? CFG.spawn.maxEnemies ?? 80;
  let gateSpawnTimer = 0;
  const maxGates = CFG.gates.maxGates;

  // Keyboard input
  const keys = new Set();

  // Touch controls
  let isTouchLike = false;
  let stickEl;
  let stickKnobEl;

  const stick = {
    active: false,
    pointerId: null,
    cx: 0,
    cy: 0,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0
  };

  function detectTouchLike() {
    isTouchLike =
      (typeof window !== 'undefined' &&
        (window.matchMedia?.('(pointer: coarse)').matches ||
          window.matchMedia?.('(hover: none)').matches)) ||
      (typeof navigator !== 'undefined' &&
        (navigator.maxTouchPoints || navigator.msMaxTouchPoints));

    if (isTouchLike && !zoomInitialized) {
      zoomIndex = 1; // 0.75x on mobile
      zoomInitialized = true;
      if (width && height) setWorldSize();
    } else if (!zoomInitialized) {
      zoomInitialized = true;
    }
  }

  function setStickFromPointer(clientX, clientY) {
    if (!stickEl) return;
    const r = stickEl.getBoundingClientRect();
    const px = clientX - r.left;
    const py = clientY - r.top;

    const dx = px - stick.cx;
    const dy = py - stick.cy;

    const radius = Math.min(r.width, r.height) * 0.42;
    const len = Math.hypot(dx, dy);
    const clampedLen = Math.min(len, radius);
    const nx = len > 0 ? dx / len : 0;
    const ny = len > 0 ? dy / len : 0;

    stick.x = stick.cx + nx * clampedLen;
    stick.y = stick.cy + ny * clampedLen;
    stick.vx = radius > 0 ? (nx * clampedLen) / radius : 0;
    stick.vy = radius > 0 ? (ny * clampedLen) / radius : 0;

    if (stickKnobEl) {
      stickKnobEl.style.transform = `translate(${stick.x}px, ${stick.y}px) translate(-50%, -50%)`;
    }
  }

  function resetStick() {
    stick.active = false;
    stick.pointerId = null;
    stick.vx = 0;
    stick.vy = 0;
    if (stickKnobEl) stickKnobEl.style.transform = '';
  }

  function onStickPointerDown(e) {
    if (!isTouchLike) return;
    if (stick.active) return;
    e.preventDefault();
    stick.active = true;
    stick.pointerId = e.pointerId;

    if (stickEl) {
      stickEl.setPointerCapture?.(e.pointerId);
      const r = stickEl.getBoundingClientRect();
      stick.cx = e.clientX - r.left;
      stick.cy = e.clientY - r.top;
      stick.x = stick.cx;
      stick.y = stick.cy;
      if (stickKnobEl) {
        stickKnobEl.style.transform = `translate(${stick.x}px, ${stick.y}px) translate(-50%, -50%)`;
      }
      setStickFromPointer(e.clientX, e.clientY);
    }
  }

  function onStickPointerMove(e) {
    if (!stick.active) return;
    if (e.pointerId !== stick.pointerId) return;
    e.preventDefault();
    setStickFromPointer(e.clientX, e.clientY);
  }

  function onStickPointerUp(e) {
    if (!stick.active) return;
    if (e.pointerId !== stick.pointerId) return;
    e.preventDefault();
    resetStick();
  }

  // Colors
  const COLORS = {
    bg: '#06080f',
    grid: 'rgba(40,80,120,0.35)',
    bullet: '#ffffff',
    playerStroke: '#ffffff',
    playerStrokeDim: '#e6efff',
    playerGlow: '#ffffff',
    trail: '#ffb64c',
    trapStroke: '#8feaff',
    trapGlow: '#bdf5ff',
    square: '#3ec3ff',
    triangle: '#ff5a6d',
    uiGreen: '#9aff4f',
    gateLine: '#FFD65C',
    gateGlow: '#FFEAA5',
    timerBg: 'rgba(12,18,26,0.7)',
    timerDigit: '#9aff4f',
    floaterKill: '#FFF59D',
    orbFill: '#FFD65C',
    orbStroke: '#FFF0B2',
    orbGlow: '#FFEAA5'
  };

  // Gamepad / Backbone support -----------------------------------------------
  let gamepadIndex = null;
  let gamepadAxes = { x: 0, y: 0 };
  let gamepadLastButtons = [];
  let isGamepadActive = false;

  function applyDeadzone(v, dz) {
    if (Math.abs(v) < dz) return 0;
    return (v - Math.sign(v) * dz) / (1 - dz);
  }

  function handleGamepadConnected(e) {
    if (gamepadIndex === null) {
      gamepadIndex = e.gamepad.index;
    }
  }

  function handleGamepadDisconnected(e) {
    if (gamepadIndex === e.gamepad.index) {
      gamepadIndex = null;
      gamepadAxes.x = 0;
      gamepadAxes.y = 0;
      gamepadLastButtons = [];
      isGamepadActive = false;
    }
  }

  function pollGamepad(nowMs) {
    if (typeof navigator === 'undefined' || !navigator.getGamepads) {
      isGamepadActive = false;
      return;
    }

    const pads = navigator.getGamepads();
    let gp = null;

    if (gamepadIndex != null && pads[gamepadIndex]) {
      gp = pads[gamepadIndex];
    }

    if (!gp) {
      for (const p of pads) {
        if (p && p.connected) {
          gp = p;
          gamepadIndex = p.index;
          break;
        }
      }
    }

    if (!gp) {
      gamepadAxes.x = 0;
      gamepadAxes.y = 0;
      isGamepadActive = false;
      return;
    }

    const DEADZONE = 0.18;
    const axX = applyDeadzone(gp.axes?.[0] ?? 0, DEADZONE);
    const axY = applyDeadzone(gp.axes?.[1] ?? 0, DEADZONE);

    gamepadAxes.x = axX;
    gamepadAxes.y = axY;

    const buttons = gp.buttons ?? [];
    const prev = gamepadLastButtons;

    const boostButtons = [0, 4]; // A / LB
    const bombButtons = [1, 5]; // B / RB
    const pauseButtons = [9]; // Start / Options
    const resetButtons = [8]; // Select / Share

    const isPressed = (i) => {
      const b = buttons[i];
      return !!(b && b.pressed);
    };

    const wasPressed = (i) => !!prev[i];

    const anyNow = (indices) => indices.some(isPressed);
    const anyPrev = (indices) => indices.some(wasPressed);

    const boostNow = anyNow(boostButtons);
    const bombNow = anyNow(bombButtons);
    const pauseNow = anyNow(pauseButtons);
    const resetNow = anyNow(resetButtons);

    if (boostNow && !anyPrev(boostButtons)) startBoost();
    if (bombNow && !anyPrev(bombButtons)) useBomb();
    if (pauseNow && !anyPrev(pauseButtons)) {
      if (!gameOver) {
        paused = !paused;
        if (!paused) lastTime = performance.now();
      }
    }
    if (resetNow && !anyPrev(resetButtons)) {
      resetGame();
    }

    gamepadLastButtons = buttons.map((b) => !!b?.pressed);

    isGamepadActive =
      Math.abs(axX) > 0.05 ||
      Math.abs(axY) > 0.05 ||
      boostNow ||
      bombNow ||
      pauseNow ||
      resetNow;
  }

  // Preference: hide mobile on-screen controls
  let hideTouchControls = false;

  function loadTouchPreference() {
    if (typeof window === 'undefined') return;
    try {
      const raw = localStorage.getItem('gw_hide_touch_controls');
      hideTouchControls = raw === '1';
    } catch {
      hideTouchControls = false;
    }
  }

  function persistHideTouchControls() {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem('gw_hide_touch_controls', hideTouchControls ? '1' : '0');
    } catch {
      // ignore
    }
  }

  // Utility helpers
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
    const sx = x2 - x1,
      sy = y2 - y1;
    const len2 = sx * sx + sy * sy;
    if (len2 === 0) return Math.hypot(px - x1, py - y1);
    const t = Math.max(0, Math.min(1, ((px - x1) * sx + (py - y1) * sy) / len2));
    const cx = x1 + t * sx;
    const cy = y1 + t * sy;
    return Math.hypot(px - cx, py - cy);
  }
  function shortestAngleDiff(a, b) {
    let diff = ((b - a + Math.PI) % (2 * Math.PI)) - Math.PI;
    if (diff < -Math.PI) diff += 2 * Math.PI;
    return diff;
  }

  // Camera helpers
  function updateCamera() {
    const viewW = width / zoom;
    const viewH = height / zoom;

    if (viewW >= worldWidth) {
      camera.x = (worldWidth - viewW) / 2;
    } else {
      camera.x = clamp(player.x - viewW / 2, 0, Math.max(0, worldWidth - viewW));
    }

    if (viewH >= worldHeight) {
      camera.y = (worldHeight - viewH) / 2;
    } else {
      camera.y = clamp(player.y - viewH / 2, 0, Math.max(0, worldHeight - viewH));
    }
  }

  // Drawing utilities
  function drawTrapezoid(wTop, wBottom, h) {
    const halfTop = wTop / 2;
    const halfBottom = wBottom / 2;
    const halfH = h / 2;
    ctx.beginPath();
    ctx.moveTo(-halfTop, -halfH);
    ctx.lineTo(halfTop, -halfH);
    ctx.lineTo(halfBottom, halfH);
    ctx.lineTo(-halfBottom, halfH);
    ctx.closePath();
  }

  // Leaderboard helpers
  async function checkLeaderboardAndPrompt() {
    try {
      const res = await fetch('/api/leaderboard');
      if (!res.ok) {
        showNamePrompt = false;
        return;
      }
      const data = await res.json();
      const entries = Array.isArray(data?.entries) ? data.entries : [];
      const newCap = typeof data?.cap === 'number' ? data.cap : 25;
      cap = newCap;

      let qualifiesFlag = false;
      if (entries.length < newCap) {
        qualifiesFlag = true;
      } else {
        const minScore = entries[entries.length - 1]?.score ?? 0;
        qualifiesFlag = score > minScore;
      }

      if (qualifiesFlag) {
        try {
          const cached = localStorage.getItem('gw_player_name');
          if (cached) playerName = cached;
        } catch {
          // ignore
        }
        showNamePrompt = true;
        lbError = '';
      }
    } catch {
      showNamePrompt = false;
    }
  }

  async function submitScore() {
    if (submitting) return;
    const name = (playerName ?? '').trim();
    if (!name) {
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
        try {
          localStorage.setItem('gw_player_name', name);
        } catch {
          // ignore
        }
        showNamePrompt = false;
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

  // Keyboard input handlers
  function onKeyDown(e) {
    const code = e.code;
    bumpHudActivity();

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
    }

    if (
      code === 'KeyW' ||
      code === 'KeyA' ||
      code === 'KeyS' ||
      code === 'KeyD' ||
      code === 'Space' ||
      code.startsWith('Arrow')
    ) {
      e.preventDefault();
    }

    if (code === 'KeyP' || code === 'Escape') {
      if (!gameOver) {
        paused = !paused;
        if (!paused) lastTime = performance.now();
      }
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

    for (let j = enemies.length - 1; j >= 0; j--) {
      killEnemyAtIndex(j);
    }
    aoeEffects.push({
      x: player.x,
      y: player.y,
      radius: Math.max(worldWidth, worldHeight) * 0.35,
      duration: 0.5,
      time: 0
    });
  }

  function setWorldSize() {
    const baseW = Math.max(1, width) * CFG.world.scale;
    const baseH = Math.max(1, height) * CFG.world.scale;

    worldWidth = Math.round(baseW);
    worldHeight = Math.round(baseH);

    player.x = clamp(player.x, player.radius, worldWidth - player.radius);
    player.y = clamp(player.y, player.radius, worldHeight - player.radius);

    updateCamera();
    makeStars();
  }

  function onResize() {
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    width = Math.floor(rect.width);
    height = Math.floor(rect.height);
    dpr = Math.max(1, Math.min(2.5, window.devicePixelRatio || 1));
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    setWorldSize();
    player.x = clamp(player.x, player.radius, worldWidth - player.radius);
    player.y = clamp(player.y, player.radius, worldHeight - player.radius);
    updateCamera();
    evaluateOrientation();
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

    updateCamera();

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

  // Spawning logic
  function weightedType(tSec) {
    const t = clamp(tSec / 90, 0, 1);
    let wTriangle = 0.45 + 0.35 * t;
    let wSquare = 0.55 - 0.25 * t;
    const sum = wTriangle + wSquare;
    const r = Math.random() * sum;
    return r < wTriangle ? 'triangle' : 'square';
  }

  function randomCornerPosition(radius) {
    const margin = radius + 12;
    const corner = Math.floor(Math.random() * 4);
    let x = margin;
    let y = margin;
    if (corner === 1) {
      x = worldWidth - margin;
      y = margin;
    } else if (corner === 2) {
      x = worldWidth - margin;
      y = worldHeight - margin;
    } else if (corner === 3) {
      x = margin;
      y = worldHeight - margin;
    }
    return { x, y, corner };
  }

  function groupSizeForTime(tSec) {
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
        speed: randSpeed(CFG.enemies.trapSpeedMin, CFG.enemies.trapSpeedMax),
        radius: baseRadius,
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
      enemy.speed = randSpeed(CFG.enemies.squareSpeedMin, CFG.enemies.squareSpeedMax);
      enemy.color = COLORS.square;
      enemy.changeDirTimer = randRange(0.8, 1.4);
      const sign = Math.random() < 0.5 ? -1 : 1;
      enemy.offsetAngle = sign * randRange(Math.PI / 6, Math.PI / 3);
      enemy.rotVel = randRange(-0.6, 0.6);
    } else if (type === 'triangle') {
      enemy.radius = 10;
      enemy.speed = randSpeed(CFG.enemies.triangleSpeedBaseMin, CFG.enemies.triangleSpeedBaseMax);
      enemy.color = COLORS.triangle;
      enemy.dashTimer = randRange(1.1, 2.0);
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
    const margin = length / 2 + 20;
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
      x,
      y,
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
    addFloaterKill(`+${pts}`, e.x, e.y - (e.radius + 6), pts);
    spawnOrb(e.x, e.y);
    enemies.splice(j, 1);
  }

  function onPlayerHit() {
    if (respawning || gameOver) return;
    lives -= 1;
    clearMap();
    player.x = worldWidth / 2;
    player.y = worldHeight / 2;
    player.vx = 0;
    player.vy = 0;
    respawning = true;
    respawnTime = 3;

    updateCamera();

    if (lives <= 0) {
      gameOver = true;
      respawning = false;
      checkLeaderboardAndPrompt();
    }
  }

  // Update loop
  function update(dt) {
    if (paused) return;

    elapsed += dt;

    if (boost.active && elapsed >= boost.endTime) {
      boost.active = false;
    }

    if (gameOver) return;

    if (respawning) {
      respawnTime -= dt;
      if (respawnTime <= 0) {
        respawning = false;
      }
      updateCamera();
      return;
    }

    const currentSpeed = player.baseSpeed * (boost.active ? boost.multiplier : 1);
    let mx = 0,
      my = 0;

    // Keyboard
    if (keys.has('KeyA')) mx -= 1;
    if (keys.has('KeyD')) mx += 1;
    if (keys.has('KeyW')) my -= 1;
    if (keys.has('KeyS')) my += 1;

    // Touch stick
    if (isTouchLike) {
      mx += stick.vx;
      my += stick.vy;
    }

    // Gamepad (Backbone etc.)
    if (isGamepadActive) {
      mx += gamepadAxes.x;
      my += gamepadAxes.y;
    }

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

    updateCamera();

    const target = nearestEnemy(player.x, player.y);
    if (target) {
      const targetAngle = angleTo(player.x, player.y, target.x, target.y);
      const diff = shortestAngleDiff(player.angle, targetAngle);
      const maxStep = player.turnRate * dt;
      const step = clamp(diff, -maxStep, maxStep);
      player.angle += step;
    }

    if (target) {
      const nowSec = elapsed;
      if (nowSec - player.lastFireTime >= player.fireInterval) {
        fireBullet();
        player.lastFireTime = nowSec;
      }
    }

    const rearX = player.x - Math.cos(player.angle) * (player.radius + 2);
    const rearY = player.y - Math.sin(player.angle) * (player.radius + 2);
    trail.push({ x: rearX, y: rearY, life: 0 });
    while (trail.length > trailMax) trail.shift();
    for (let i = 0; i < trail.length; i++) {
      trail[i].life += dt;
    }

    // Bullets
    for (let i = bullets.length - 1; i >= 0; i--) {
      const b = bullets[i];
      b.x += b.vx * dt;
      b.y += b.vy * dt;
      b.life -= dt;
      if (
        b.life <= 0 ||
        b.x < -20 ||
        b.x > worldWidth + 20 ||
        b.y < -20 ||
        b.y > worldHeight + 20
      ) {
        bullets.splice(i, 1);
        continue;
      }
      let hit = false;
      for (let j = enemies.length - 1; j >= 0; j--) {
        const e = enemies[j];
        const dx = e.x - b.x;
        const dy = e.y - b.y;
        const rr = e.radius + CFG.bullet.radius;
        if (dx * dx + dy * dy <= rr * rr) {
          bullets.splice(i, 1);
          killEnemyAtIndex(j);
          hit = true;
          break;
        }
      }
      if (hit) continue;
    }

    // Enemy AI
    const centroids = new Map();
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      if (e.type === 'trapezoid' && e.groupId) {
        const entry = centroids.get(e.groupId);
        if (!entry) {
          centroids.set(e.groupId, { x: e.x, y: e.y, count: 1 });
        } else {
          entry.x += e.x;
          entry.y += e.y;
          entry.count += 1;
        }
      }
    }
    centroids.forEach((v) => {
      v.x /= v.count;
      v.y /= v.count;
    });

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
        const dir = normalize(
          toPlayer.x * wPlayer + toGroup.x * wGroup,
          toPlayer.y * wPlayer + toGroup.y * wGroup
        );
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
        e.rot += e.rotVel || 0 * dt;
      } else if (e.type === 'triangle') {
        e.dashTimer -= dt;
        const leadTime = 0.2;
        const aimX = player.x + player.vx * leadTime;
        const aimY = player.y + player.vy * leadTime;
        const dir = normalize(aimX - e.x, aimY - e.y);
        let speed = e.speed;
        if (e.dashTimer <= 0) {
          speed = e.speed + CFG.enemies.triangleDashBonus;
          e.dashTimer = randRange(1.2, 2.2);
        }
        e.vx = dir.x * speed;
        e.vy = dir.y * speed;
      }

      e.x += e.vx * dt;
      e.y += e.vy * dt;

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

    // Orbs
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

    // Gates
    for (let i = gates.length - 1; i >= 0; i--) {
      const g = gates[i];
      g.angle += g.angVel * dt;
      g.x += g.vx * dt;
      g.y += g.vy * dt;

      const hx = Math.cos(g.angle) * (g.length / 2);
      const hy = Math.sin(g.angle) * (g.length / 2);
      const marginX = Math.abs(hx) + 10;
      const marginY = Math.abs(hy) + 10;

      if (g.x < marginX) {
        g.x = marginX;
        g.vx = Math.abs(g.vx);
      } else if (g.x > worldWidth - marginX) {
        g.x = worldWidth - marginX;
        g.vx = -Math.abs(g.vx);
      }
      if (g.y < marginY) {
        g.y = marginY;
        g.vy = Math.abs(g.vy);
      } else if (g.y > worldHeight - marginY) {
        g.y = worldHeight - marginY;
        g.vy = -Math.abs(g.vy);
      }

      const x1 = g.x - hx,
        y1 = g.y - hy;
      const x2 = g.x + hx,
        y2 = g.y + hy;
      const distToLine = pointSegmentDistance(player.x, player.y, x1, y1, x2, y2);
      if (distToLine <= player.radius + g.thickness / 2) {
        triggerGateAOE(g);
        gates.splice(i, 1);
      }
    }

    // AOE effects
    for (let i = aoeEffects.length - 1; i >= 0; i--) {
      const fx = aoeEffects[i];
      fx.time += dt;
      if (fx.time >= fx.duration) {
        aoeEffects.splice(i, 1);
      }
    }

    // Floaters
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

    // Spawn new enemies / gates
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

    gateSpawnTimer += dt;
    if (gateSpawnTimer >= CFG.gates.spawnInterval) {
      gateSpawnTimer = 0;
      if (gates.length < maxGates) {
        spawnGate();
      }
    }
  }

  function triggerGateAOE(gate) {
    for (let j = enemies.length - 1; j >= 0; j--) {
      const e = enemies[j];
      const dx = e.x - gate.x;
      const dy = e.y - gate.y;
      if (dx * dx + dy * dy <= CFG.gates.aoeRadius * CFG.gates.aoeRadius) {
        killEnemyAtIndex(j);
      }
    }
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

  // Rendering
  function drawBackground() {
    ctx.save();
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  }

  function drawGrid() {
    const spacing = CFG.world.gridSpacing;
    const viewW = width / zoom;
    const viewH = height / zoom;
    ctx.save();
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;

    for (
      let x = Math.floor(camera.x / spacing) * spacing;
      x <= Math.min(camera.x + viewW, worldWidth);
      x += spacing
    ) {
      ctx.beginPath();
      ctx.moveTo(x, camera.y);
      ctx.lineTo(x, camera.y + viewH);
      ctx.stroke();
    }

    for (
      let y = Math.floor(camera.y / spacing) * spacing;
      y <= Math.min(camera.y + viewH, worldHeight);
      y += spacing
    ) {
      ctx.beginPath();
      ctx.moveTo(camera.x, y);
      ctx.lineTo(camera.x + viewW, y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawStars() {
    ctx.save();
    const viewW = width / zoom;
    const viewH = height / zoom;
    for (let i = 0; i < stars.length; i++) {
      const s = stars[i];
      if (
        s.x < camera.x - 2 ||
        s.x > camera.x + viewW + 2 ||
        s.y < camera.y - 2 ||
        s.y > camera.y + viewH + 2
      )
        continue;
      ctx.globalAlpha = s.a;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function drawWorldBounds() {
    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,255,0.55)';
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(255,255,255,0.5)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.rect(0, 0, worldWidth, worldHeight);
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  function drawPlayer() {
    ctx.save();
    ctx.translate(player.x, player.y);
    ctx.rotate(player.angle);

    const r = player.radius;
    const t = 6;
    ctx.lineWidth = t;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.shadowColor = COLORS.playerGlow;
    ctx.shadowBlur = 14;

    ctx.strokeStyle = COLORS.playerStroke;
    ctx.beginPath();
    ctx.moveTo(-r, -r);
    ctx.lineTo(r, -r);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(-r, r);
    ctx.lineTo(r, r);
    ctx.stroke();

    ctx.strokeStyle = COLORS.playerStrokeDim;
    ctx.beginPath();
    ctx.moveTo(-r, -r);
    ctx.lineTo(-r, r);
    ctx.stroke();

    ctx.shadowBlur = 0;
    ctx.restore();

    ctx.save();
    for (let i = 1; i < trail.length; i++) {
      const p0 = trail[i - 1];
      const p1 = trail[i];
      const life = trail[i].life;
      const a = clamp(1 - life * 1.8, 0, 1);
      if (a <= 0) continue;

      const w = 6 * a;

      ctx.strokeStyle = COLORS.trail;
      ctx.lineWidth = w;
      ctx.shadowColor = COLORS.trail;
      ctx.shadowBlur = 8 * a;
      ctx.globalAlpha = a * 0.7;

      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();

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
        ctx.shadowColor = '#ffb3bd';
        ctx.shadowBlur = 12;
        ctx.strokeStyle = COLORS.triangle;
        ctx.fillStyle = 'transparent';
        ctx.beginPath();
        ctx.moveTo(0, -e.radius);
        ctx.lineTo(e.radius, e.radius);
        ctx.lineTo(-e.radius, e.radius);
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
      const x1 = g.x - hx,
        y1 = g.y - hy;
      const x2 = g.x + hx,
        y2 = g.y + hy;

      ctx.strokeStyle = COLORS.gateGlow;
      ctx.lineWidth = g.thickness + 4;
      ctx.globalAlpha = 0.25;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

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
      const t = fx.time / fx.duration;
      const alpha = 1 - t;
      ctx.globalAlpha = Math.max(0, alpha * 0.7);
      ctx.strokeStyle = COLORS.gateGlow;
      ctx.lineWidth = 6 * alpha + 2;
      ctx.beginPath();
      ctx.arc(fx.x, fx.y, fx.radius, 0, Math.PI * 2);
      ctx.stroke();

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
        ctx.font = '300 18px Menlo, Consolas, Monaco, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = COLORS.floaterKill;
        ctx.fillText(f.text, 0, 0);
      } else {
        const grad = ctx.createLinearGradient(0, -20, 0, 20);
        grad.addColorStop(0, '#ff6ec7');
        grad.addColorStop(1, '#00eaff');

        ctx.font = 'bold 20px Menlo, Consolas, Monaco, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';

        ctx.lineWidth = 3;
        ctx.strokeStyle = '#ffffff';
        ctx.strokeText(f.text, 0, 0);

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

  // Main loop
  function draw() {
    drawBackground();

    ctx.save();
    ctx.scale(zoom, zoom);
    ctx.translate(-camera.x, -camera.y);

    drawStars();
    drawGrid();
    drawWorldBounds();
    drawBullets();
    drawEnemies();
    drawOrbs();
    drawGates();
    drawAOEEffects();
    drawPlayer();
    drawFloaters();

    ctx.restore();

    drawTimer();
    drawBoostStatus();
    drawRespawnCountdown();
    drawGameOver();
  }

  function loop(now) {
    if (!lastTime) lastTime = now;
    let dt = (now - lastTime) / 1000;
    dt = Math.min(dt, 0.05);
    lastTime = now;

    pollGamepad(now);
    update(dt);
    draw();

    rafId = requestAnimationFrame(loop);
  }

  const onBlur = () => {
    paused = true;
  };

  const onVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      paused = true;
    } else {
      paused = false;
      lastTime = performance.now();
      bumpHudActivity();
    }
  };

  // --- NEW: prevent browser zoom gestures on mobile -------------------------
  let lastTouchEnd = 0;
  let doubleTapHandler;
  let gestureHandler;
  // --------------------------------------------------------------------------

  onMount(() => {
    detectTouchLike();
    loadTouchPreference();

    if (!canvas) return;
    ctx = canvas.getContext('2d', { alpha: false });
    onResize();

    player.x = worldWidth / 2;
    player.y = worldHeight / 2;

    updateCamera();

    for (let i = 0; i < 3; i++) spawnTrapezoidGroup(groupSizeForTime(elapsed));
    for (let i = 0; i < 6; i++) spawnEnemy(weightedType(elapsed));
    if (gates.length < maxGates) spawnGate();

    window.addEventListener('keydown', onKeyDown, { passive: false });
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('resize', onResize);
    window.addEventListener('resize', detectTouchLike);
    window.addEventListener('blur', onBlur);
    document.addEventListener('visibilitychange', onVisibilityChange);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    window.addEventListener('gamepadconnected', handleGamepadConnected);
    window.addEventListener('gamepaddisconnected', handleGamepadDisconnected);

    activityHandler = () => bumpHudActivity();
    window.addEventListener('pointerdown', activityHandler, { passive: true });
    window.addEventListener('pointermove', activityHandler, { passive: true });
    window.addEventListener('keydown', activityHandler);

    evaluateOrientation();
    bumpHudActivity();

    // --- NEW: globally block smart-zoom + pinch-zoom while on the game page
    doubleTapHandler = (e) => {
      const now = Date.now();
      if (now - lastTouchEnd <= 300) {
        // treat as double-tap → prevent zoom
        e.preventDefault();
      }
      lastTouchEnd = now;
    };

    gestureHandler = (e) => {
      // iOS Safari pinch/gesture zoom
      e.preventDefault();
    };

    document.addEventListener('touchend', doubleTapHandler, { passive: false });
    document.addEventListener('gesturestart', gestureHandler);
    document.addEventListener('gesturechange', gestureHandler);
    document.addEventListener('gestureend', gestureHandler);
    // ------------------------------------------------------------------------

    rafId = requestAnimationFrame(loop);
  });

  onDestroy(() => {
    if (typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(rafId);
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('resize', detectTouchLike);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('gamepadconnected', handleGamepadConnected);
      window.removeEventListener('gamepaddisconnected', handleGamepadDisconnected);

      if (activityHandler) {
        window.removeEventListener('pointerdown', activityHandler);
        window.removeEventListener('pointermove', activityHandler);
        window.removeEventListener('keydown', activityHandler);
      }
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);

      // NEW: clean up zoom-prevention handlers
      if (doubleTapHandler) {
        document.removeEventListener('touchend', doubleTapHandler);
      }
      if (gestureHandler) {
        document.removeEventListener('gesturestart', gestureHandler);
        document.removeEventListener('gesturechange', gestureHandler);
        document.removeEventListener('gestureend', gestureHandler);
      }
    }
    if (hudHideTimer) clearTimeout(hudHideTimer);
  });

  function togglePauseFromHUD() {
    if (!gameOver) {
      paused = !paused;
      if (!paused) lastTime = performance.now();
    }
  }
</script>

<div class="game-container">
  <canvas bind:this={canvas} class="game-canvas"></canvas>

  {#if isTouchLike && !isGamepadActive && !hideTouchControls}
    <div class="touch-ui" aria-hidden="true">
      <div
        class="stick"
        bind:this={stickEl}
        on:pointerdown={onStickPointerDown}
        on:pointermove={onStickPointerMove}
        on:pointerup={onStickPointerUp}
        on:pointercancel={onStickPointerUp}
        on:lostpointercapture={resetStick}
      >
        <div class="stick-ring"></div>
        <div class="stick-knob" bind:this={stickKnobEl}></div>
      </div>

      <div class="touch-buttons">
        <button
          class="touch-btn"
          on:pointerdown|preventDefault={() => startBoost()}
          aria-label="Boost"
          title="Boost"
        >
          BOOST
        </button>
        <button
          class="touch-btn"
          on:pointerdown|preventDefault={() => useBomb()}
          aria-label="Bomb"
          title="Bomb"
        >
          BOMB
        </button>
      </div>
    </div>
  {/if}

  <div class="hud" class:hud-dim={!hudVisible && !paused && !gameOver}>
    <div class="stat">Score: {score.toLocaleString()}</div>
    <div class="stat">×{multiplier}</div>
    <div class="stat">Lives: {'♥'.repeat(lives)}</div>
    <div class="stat">Bombs: {bombs}</div>

    <div class="controls">
      <button class="btn" on:click={togglePauseFromHUD}>
        {paused && !gameOver ? 'Resume' : 'Pause'}
      </button>
    </div>
  </div>

  {#if showHelp}
    <div class="hint">
      {#if isTouchLike}
        Left stick: Move • Right buttons: Boost/Bomb • Touch enemy = lose life • Gates cause AOE
      {:else}
        WASD: Move • Space: Boost • E: Bomb • Esc / P: Pause • Gates cause AOE
      {/if}
    </div>
  {/if}

  {#if paused && !gameOver}
    <div class="pause-overlay">
      <div class="pause-card">
        <div class="pause-title">Paused</div>
        <div class="pause-sub">
          Press <strong>Esc</strong> or <strong>Start</strong> on your controller to resume, or use
          the controls below.
        </div>

        <div class="pause-controls">
          <div class="pause-buttons">
            <button class="btn primary" on:click={togglePauseFromHUD}>Resume</button>
            <button class="btn" on:click={cycleZoom}>Zoom: {zoom}x</button>
            <button class="btn" on:click={toggleFullscreen}>
              {isFullscreen ? 'Windowed' : 'Fullscreen'}
            </button>
            <button class="btn" on:click={resetGame}>Reset</button>
            <a class="btn" href="/">Exit</a>
          </div>

          {#if isTouchLike}
            <label class="pause-toggle">
              <input
                type="checkbox"
                bind:checked={hideTouchControls}
                on:change={persistHideTouchControls}
              />
              <span>Hide on-screen mobile controls (for Backbone/controllers)</span>
            </label>
          {/if}

          <div class="pause-howto">
            <h3>How To Play</h3>
            <div class="howto-grid">
              <section>
                <h4>Keyboard</h4>
                <ul>
                  <li><strong>WASD</strong> – Move</li>
                  <li><strong>Space</strong> – Boost</li>
                  <li><strong>E</strong> – Bomb</li>
                  <li><strong>Esc / P</strong> – Pause / Resume</li>
                </ul>
              </section>
              <section>
                <h4>Backbone / Controller</h4>
                <ul>
                  <li><strong>Left Stick</strong> – Move</li>
                  <li><strong>A / L1</strong> – Boost</li>
                  <li><strong>B / R1</strong> – Bomb</li>
                  <li><strong>Start / Options</strong> – Pause / Resume</li>
                  <li><strong>Select / Share</strong> – Reset</li>
                </ul>
              </section>
            </div>

            {#if isTouchLike && showRotateHint}
              <p class="pause-rotate-hint">
                For the best experience on mobile, rotate your device to landscape while playing.
              </p>
            {/if}
          </div>
        </div>
      </div>
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

<style>
  :root {
    --bg-base: #06080f;
    --ui-green: #9aff4f;
    --ui-green-dim: #6de63c;
    --ui-blue: #00eaff;
    --ui-blue2: #51b3ff;
    --ui-pink: #ff6ec7;
    --ui-aqua: #00eaff;
    --hud-bg: rgba(10, 18, 26, 0.6);
    --hud-border: rgba(40, 80, 40, 0.5);
    --hud-shadow: rgba(154, 255, 79, 0.35);
    --grid: rgba(40, 80, 120, 0.35);
    --btn-bg: #11151d;
    --btn-bg-hover: #1a1f29;
    --btn-border: #2c3e50;
    --title-grad-start: #00eaff;
    --title-grad-end: #51b3ff;
    --subtitle-color: #9bd4ff;
    --modal-overlay: rgba(0, 0, 0, 0.55);
  }

  html,
  body {
    margin: 0;
    height: 100%;
    background: var(--bg-base);
    overflow: hidden;
  }

  * {
    box-sizing: border-box;
  }

  body,
  .game-container,
  .game-container *,
  .hud,
  .hud *,
  .touch-ui,
  .touch-ui *,
  .hint {
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
  }

  .btn {
    appearance: none;
    border: 1px solid var(--btn-border);
    background: var(--btn-bg);
    color: #ffffff;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s ease, transform 0.06s ease;
    min-height: 44px;
    min-width: 60px;
  }

  .btn:hover {
    background: var(--btn-bg-hover);
    transform: translateY(-1px);
  }

  .btn.primary {
    border-color: #00a8ff;
    background: #0f1822;
    box-shadow: 0 0 18px rgba(0, 168, 255, 0.15);
  }

  .btn.primary:hover {
    background: #132032;
    box-shadow: 0 0 22px rgba(0, 168, 255, 0.25);
  }

  .game-container {
    position: relative;
    width: 100vw;
    height: 100vh;
    background: var(--bg-base);
    touch-action: none; /* NEW: help prevent pinch/double-tap zoom */
  }

  .game-canvas {
    width: 100%;
    height: 100%;
    display: block;
    touch-action: none;
  }

  .touch-ui {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 20;
  }

  .stick {
    position: absolute;
    left: calc(env(safe-area-inset-left, 0px) + 24px);
    bottom: calc(env(safe-area-inset-bottom, 0px) + 24px);
    width: clamp(120px, 32vw, 180px);
    aspect-ratio: 1;
    border-radius: 999px;
    pointer-events: auto;
    touch-action: none;
  }

  .stick-ring {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    background: rgba(10, 18, 26, 0.22);
    border: 1px solid rgba(44, 62, 80, 0.75);
    box-shadow: 0 0 18px rgba(154, 255, 79, 0.1);
    backdrop-filter: blur(2px);
  }

  .stick-knob {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 36%;
    height: 36%;
    border-radius: 999px;
    transform: translate(-50%, -50%);
    background: rgba(154, 255, 79, 0.12);
    border: 1px solid rgba(154, 255, 79, 0.35);
    box-shadow: 0 0 18px rgba(154, 255, 79, 0.22);
  }

  .touch-buttons {
    position: absolute;
    right: calc(env(safe-area-inset-right, 0px) + 24px);
    bottom: calc(env(safe-area-inset-bottom, 0px) + 24px);
    display: flex;
    flex-direction: column;
    gap: 14px;
    pointer-events: auto;
  }

  .touch-btn {
    width: clamp(96px, 22vw, 150px);
    height: clamp(44px, 9vh, 64px);
    border-radius: 14px;
    border: 1px solid rgba(44, 62, 80, 0.85);
    background: rgba(10, 18, 26, 0.5);
    color: #ffffff;
    font-weight: 800;
    letter-spacing: 0.08em;
    font-size: 14px;
    text-transform: uppercase;
    box-shadow: 0 0 18px rgba(0, 234, 255, 0.08);
    -webkit-tap-highlight-color: transparent;
    touch-action: none;
  }

  .touch-btn:active {
    transform: translateY(1px);
    background: rgba(10, 18, 26, 0.65);
  }

  .hud {
    position: absolute;
    top: calc(max(8px, env(safe-area-inset-top, 0px)));
    left: env(safe-area-inset-left, 0px);
    right: env(safe-area-inset-right, 0px);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    color: var(--ui-green);
    font-family: Menlo, Consolas, Monaco, monospace;
    pointer-events: none;
    padding: 0 8px;
    opacity: 1;
    transition: opacity 0.25s ease;
    z-index: 30;
  }

  .hud-dim {
    opacity: 0.15;
  }

  .stat {
    font-weight: 700;
    font-size: 16px;
    background: var(--hud-bg);
    padding: 6px 10px;
    border-radius: 6px;
    text-shadow: 0 0 10px var(--hud-shadow), 0 0 3px rgba(154, 255, 79, 0.6);
    border: 1px solid var(--hud-border);
  }

  .controls {
    margin-left: auto;
    display: flex;
    gap: 8px;
    pointer-events: auto;
  }

  .hint {
    position: absolute;
    bottom: 10px;
    right: 10px;
    font-size: 12px;
    color: var(--ui-green);
    opacity: 0.85;
    background: var(--hud-bg);
    padding: 6px 10px;
    border-radius: 6px;
    text-shadow: 0 0 8px var(--hud-shadow);
    pointer-events: none;
    border: 1px solid var(--hud-border);
    z-index: 25;
  }

  .pause-overlay {
    position: absolute;
    inset: 0;
    z-index: 40;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(4px);
  }

  .pause-card {
    width: min(520px, 92vw);
    padding: 18px 18px 16px;
    border-radius: 12px;
    background: rgba(10, 18, 26, 0.94);
    border: 1px solid rgba(0, 234, 255, 0.24);
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
    color: #eafcff;
    text-align: left;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }

  .pause-title {
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 6px;
    font-size: 14px;
    color: var(--ui-blue2);
  }

  .pause-sub {
    font-size: 13px;
    opacity: 0.9;
  }

  .pause-controls {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .pause-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .pause-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 13px;
    color: #cfd8ff;
  }

  .pause-toggle input[type='checkbox'] {
    width: 16px;
    height: 16px;
  }

  .pause-howto {
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 10px;
    font-size: 13px;
  }

  .pause-howto h3 {
    margin: 0 0 6px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #9bd4ff;
  }

  .pause-howto h4 {
    margin: 0 0 4px;
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
  }

  .howto-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: space-between;
  }

  .howto-grid section {
    flex: 1 1 150px;
  }

  .pause-howto ul {
    margin: 0;
    padding-left: 18px;
    list-style: disc;
  }

  .pause-howto li {
    margin-bottom: 2px;
  }

  .pause-rotate-hint {
    margin: 8px 0 0;
    font-size: 12px;
    opacity: 0.85;
    color: #ffeaa5;
  }

  .modal {
    position: absolute;
    inset: 0;
    background: var(--modal-overlay);
    display: grid;
    place-items: center;
    z-index: 50;
  }

  .modal-content {
    width: min(560px, 90vw);
    background: #0f1420;
    border: 1px solid #1f2630;
    border-radius: 12px;
    padding: 18px;
    color: #ffffff;
    font-family: Menlo, Consolas, Monaco, monospace;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }

  .modal-title {
    font-weight: 800;
    font-size: 20px;
    color: var(--ui-green);
    margin: 0 0 8px;
    text-shadow: 0 0 10px var(--hud-shadow);
  }

  .modal-desc {
    font-size: 14px;
    opacity: 0.85;
    margin-bottom: 12px;
  }

  .input {
    width: 100%;
    padding: 10px 12px;
    font-size: 16px;
    border-radius: 8px;
    border: 1px solid #2c3e50;
    background: #11151d;
    color: #ffffff;
    outline: none;
  }

  .input:focus {
    border-color: #00a8ff;
    box-shadow: 0 0 10px rgba(0, 168, 255, 0.25);
  }

  .modal-actions {
    display: flex;
    gap: 10px;
    margin-top: 12px;
  }

  @media (pointer: coarse) {
    .hud {
      gap: 6px;
      padding-right: calc(env(safe-area-inset-right, 0px) + 4px);
      padding-left: calc(env(safe-area-inset-left, 0px) + 4px);
      flex-wrap: nowrap;
      overflow-x: auto;
      white-space: nowrap;
      scrollbar-width: none;
    }
    .hud::-webkit-scrollbar {
      display: none;
    }

    .stat {
      font-size: 13px;
    }

    .hud .controls {
      margin-left: auto;
      display: flex;
      flex-wrap: nowrap;
      gap: 6px;
    }

    .btn {
      padding: 6px 10px;
      font-size: 13px;
      border-radius: 10px;
      min-height: 44px;
    }

    .hint {
      bottom: auto;
      top: calc(max(8px, env(safe-area-inset-top)) + 54px);
      left: 8px;
      right: 8px;
      max-width: none;
    }
  }

  @media (max-height: 680px) and (pointer: coarse) {
    .hint {
      display: false;
    }
  }

  @media (max-width: 520px) {
    .hint {
      left: 10px;
      right: auto;
      max-width: 62vw;
    }
  }

  @media (hover: none) and (pointer: coarse) {
    .game-container button,
    .game-container a {
      outline: none;
      -webkit-tap-highlight-color: transparent;
    }
  }
</style>
