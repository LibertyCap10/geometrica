import {
  PUBLIC_WORLD_SCALE,
  PUBLIC_GRID_SPACING,
  PUBLIC_PLAYER_BASE_SPEED,
  PUBLIC_PLAYER_BOOST_MULTIPLIER,
  PUBLIC_PLAYER_BOOST_DURATION,
  PUBLIC_PLAYER_FIRE_RATE,
  PUBLIC_BULLET_SPEED,
  PUBLIC_BULLET_LIFE,
  PUBLIC_BULLET_RADIUS,
  PUBLIC_SPAWN_MODE,
  PUBLIC_SPAWN_BASE_INTERVAL,
  PUBLIC_SPAWN_MIN_INTERVAL,
  PUBLIC_SPAWN_DECAY_PER_SEC,
  PUBLIC_SPAWN_LINEAR_SLOPE,
  PUBLIC_SPAWN_GROUP_CHANCE,
  PUBLIC_MAX_ENEMIES,
  PUBLIC_TRAP_SPEED_MIN,
  PUBLIC_TRAP_SPEED_MAX,
  PUBLIC_SQUARE_SPEED_MIN,
  PUBLIC_SQUARE_SPEED_MAX,
  PUBLIC_TRIANGLE_SPEED_BASE_MIN,
  PUBLIC_TRIANGLE_SPEED_BASE_MAX,
  PUBLIC_TRIANGLE_DASH_BONUS,
  PUBLIC_ORB_MAGNET_RANGE,
  PUBLIC_ORB_SEEK_SPEED,
  PUBLIC_ORB_WANDER_FORCE,
  PUBLIC_GATE_LENGTH,
  PUBLIC_GATE_THICKNESS,
  PUBLIC_GATE_AOE_RADIUS,
  PUBLIC_GATE_SPAWN_INTERVAL,
  PUBLIC_MAX_GATES,
  PUBLIC_TRAIL_MAX,
  PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_1,
  PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_2,
  PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_3,
  PUBLIC_FIRE_RATE_THRESH_1,
  PUBLIC_FIRE_RATE_THRESH_2,
  PUBLIC_FIRE_RATE_THRESH_3
} from '$env/static/public';

type SpawnMode = 'constant' | 'linear' | 'exp';

function num(env: string | undefined, fallback: number): number {
  const v = env ? Number(env) : NaN;
  return Number.isFinite(v) ? v : fallback;
}

function clampNum(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

export const CFG = {
  world: {
    scale: num(PUBLIC_WORLD_SCALE, 1.25),
    gridSpacing: num(PUBLIC_GRID_SPACING, 60)
  },

  player: {
    baseSpeed: num(PUBLIC_PLAYER_BASE_SPEED, 240),
    boostMultiplier: num(PUBLIC_PLAYER_BOOST_MULTIPLIER, 1.8),
    boostDuration: num(PUBLIC_PLAYER_BOOST_DURATION, 5)
  },

  bullets: {
    speed: num(PUBLIC_BULLET_SPEED, 720),
    life: num(PUBLIC_BULLET_LIFE, 0.9),
    radius: num(PUBLIC_BULLET_RADIUS, 4)
  },

  spawn: {
    mode: (PUBLIC_SPAWN_MODE as SpawnMode) ?? 'exp',
    baseInterval: num(PUBLIC_SPAWN_BASE_INTERVAL, 1.0),
    minInterval: num(PUBLIC_SPAWN_MIN_INTERVAL, 0.12),
    decayPerSec: num(PUBLIC_SPAWN_DECAY_PER_SEC, 0.985),
    linearSlope: num(PUBLIC_SPAWN_LINEAR_SLOPE, -0.02),
    groupChance: clampNum(num(PUBLIC_SPAWN_GROUP_CHANCE, 0.22), 0, 1),
    maxEnemies: Math.max(10, Math.floor(num(PUBLIC_MAX_ENEMIES, 120)))
  },

  enemies: {
    trapSpeedMin: num(PUBLIC_TRAP_SPEED_MIN, 40),
    trapSpeedMax: num(PUBLIC_TRAP_SPEED_MAX, 110),
    squareSpeedMin: num(PUBLIC_SQUARE_SPEED_MIN, 70),
    squareSpeedMax: num(PUBLIC_SQUARE_SPEED_MAX, 160),
    triangleBaseSpeedMin: num(PUBLIC_TRIANGLE_SPEED_BASE_MIN, 80),
    triangleBaseSpeedMax: num(PUBLIC_TRIANGLE_SPEED_BASE_MAX, 180),
    triangleDashBonus: num(PUBLIC_TRIANGLE_DASH_BONUS, 1.9)
  },

  orbs: {
    magnetRange: num(PUBLIC_ORB_MAGNET_RANGE, 260),
    seekSpeed: num(PUBLIC_ORB_SEEK_SPEED, 240),
    wanderForce: num(PUBLIC_ORB_WANDER_FORCE, 12)
  },

  gates: {
    length: num(PUBLIC_GATE_LENGTH, 220),
    thickness: num(PUBLIC_GATE_THICKNESS, 22),
    aoeRadius: num(PUBLIC_GATE_AOE_RADIUS, 120),
    spawnInterval: num(PUBLIC_GATE_SPAWN_INTERVAL, 14),
    maxGates: Math.max(1, Math.floor(num(PUBLIC_MAX_GATES, 4)))
  },

  trail: {
    maxPoints: Math.max(10, Math.floor(num(PUBLIC_TRAIL_MAX, 40)))
  },

  fireRateScaling: {
    multAtThresh1: num(PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_1, 1.2),
    multAtThresh2: num(PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_2, 1.4),
    multAtThresh3: num(PUBLIC_PLAYER_FIRE_RATE_MULT_AT_THRESH_3, 1.6),
    thresh1: num(PUBLIC_FIRE_RATE_THRESH_1, 50_000),
    thresh2: num(PUBLIC_FIRE_RATE_THRESH_2, 150_000),
    thresh3: num(PUBLIC_FIRE_RATE_THRESH_3, 300_000)
  }
};

export const DERIVED = {
  spawnMode: CFG.spawn.mode as SpawnMode
};

export function spawnInterval(elapsedSec: number): number {
  const s = CFG.spawn;
  if (s.mode === 'constant') {
    return s.baseInterval;
  }
  if (s.mode === 'linear') {
    const val = s.baseInterval + s.linearSlope * elapsedSec;
    return Math.max(s.minInterval, val);
  }
  const t = Math.max(0, elapsedSec);
  const val = s.baseInterval * Math.pow(s.decayPerSec, t);
  return Math.max(s.minInterval, val);
}

export function randSpeed(min: number, max: number): number {
  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  return lo + Math.random() * (hi - lo);
}
