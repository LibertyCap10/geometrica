// src/lib/config.ts
// Centralized gameplay configuration loaded from PUBLIC_* environment variables.
// IMPORTANT: In SvelteKit, use $env/static/public (not import.meta.env) so values are
// replaced at build/startup. After changing your .env, restart the dev server.
//
// Usage:
//   import { CFG, DERIVED, spawnInterval, randSpeed } from '$lib/config';

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
  PUBLIC_TRAIL_MAX
} from '$env/static/public';

type SpawnMode = 'exp' | 'lin';

function num(raw: string | undefined, fallback: number): number {
  if (raw == null || raw === '') return fallback;
  const v = Number(raw);
  return Number.isFinite(v) ? v : fallback;
}

function str<T extends string>(raw: string | undefined, fallback: T, allowed: readonly T[]): T {
  if (!raw) return fallback;
  if (allowed.includes(raw as T)) return raw as T;
  return fallback;
}

export const CFG = {
  world: {
    scale: num(PUBLIC_WORLD_SCALE, 1.25),
    gridSpacing: num(PUBLIC_GRID_SPACING, 60)
  },
  player: {
    baseSpeed: num(PUBLIC_PLAYER_BASE_SPEED, 240),
    boostMultiplier: num(PUBLIC_PLAYER_BOOST_MULTIPLIER, 1.8),
    boostDuration: num(PUBLIC_PLAYER_BOOST_DURATION, 15),
    fireRate: num(PUBLIC_PLAYER_FIRE_RATE, 9) // bullets per second
  },
  bullet: {
    speed: num(PUBLIC_BULLET_SPEED, 580),
    life: num(PUBLIC_BULLET_LIFE, 1.2),
    radius: num(PUBLIC_BULLET_RADIUS, 4)
  },
  spawn: {
    mode: str<SpawnMode>(PUBLIC_SPAWN_MODE, 'exp', ['exp', 'lin']),
    baseInterval: num(PUBLIC_SPAWN_BASE_INTERVAL, 1.0),
    minInterval: num(PUBLIC_SPAWN_MIN_INTERVAL, 0.1),
    decayPerSec: num(PUBLIC_SPAWN_DECAY_PER_SEC, 0.999),
    linearSlope: num(PUBLIC_SPAWN_LINEAR_SLOPE, 0.05),
    groupChance: num(PUBLIC_SPAWN_GROUP_CHANCE, 0.15)
  },
  enemies: {
    maxEnemies: num(PUBLIC_MAX_ENEMIES, 80),
    trapSpeedMin: num(PUBLIC_TRAP_SPEED_MIN, 40),
    trapSpeedMax: num(PUBLIC_TRAP_SPEED_MAX, 80),
    squareSpeedMin: num(PUBLIC_SQUARE_SPEED_MIN, 40),
    squareSpeedMax: num(PUBLIC_SQUARE_SPEED_MAX, 120),
    triangleSpeedBaseMin: num(PUBLIC_TRIANGLE_SPEED_BASE_MIN, 60),
    triangleSpeedBaseMax: num(PUBLIC_TRIANGLE_SPEED_BASE_MAX, 160),
    triangleDashBonus: num(PUBLIC_TRIANGLE_DASH_BONUS, 80)
  },
  orbs: {
    magnetRange: num(PUBLIC_ORB_MAGNET_RANGE, 260),
    seekSpeed: num(PUBLIC_ORB_SEEK_SPEED, 180),
    wanderForce: num(PUBLIC_ORB_WANDER_FORCE, 40)
  },
  gates: {
    length: num(PUBLIC_GATE_LENGTH, 180),
    thickness: num(PUBLIC_GATE_THICKNESS, 4),
    aoeRadius: num(PUBLIC_GATE_AOE_RADIUS, 220),
    spawnInterval: num(PUBLIC_GATE_SPAWN_INTERVAL, 4),
    maxGates: num(PUBLIC_MAX_GATES, 6)
  },
  trail: {
    max: num(PUBLIC_TRAIL_MAX, 40)
  }
};

// Derived constants that depend on core config.
export const DERIVED = {
  // Global fire interval used by the player
  fireInterval: CFG.player.fireRate > 0 ? 1 / CFG.player.fireRate : 1 / 9,
  player: {
    radius: 14,
    turnRate: Math.PI * 4
  },
  enemies: {
    baseRadius: 12
  },
  orbs: {
    radius: 5,
    spawnRadius: 24
  }
};

/**
 * Compute the enemy spawn interval based on elapsed time.
 * Supports exponential and linear modes.
 *
 * Backwards-compatible: you can call spawnInterval(elapsedSec)
 * and it will use CFG.spawn.mode by default.
 */
export function spawnInterval(
  elapsedSec: number,
  mode: SpawnMode = CFG.spawn.mode,
  s = CFG.spawn
): number {
  if (mode === 'lin') {
    const t = Math.max(0, elapsedSec);
    const val = Math.max(s.baseInterval - s.linearSlope * t, s.minInterval);
    return val;
  }
  // Exponential (default): interval decays exponentially over time
  const t = Math.max(0, elapsedSec);
  const val = s.baseInterval * Math.pow(s.decayPerSec, t);
  return Math.max(s.minInterval, val);
}

/**
 * Utility to get a random speed within [min, max].
 */
export function randSpeed(min: number, max: number): number {
  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  return lo + Math.random() * (hi - lo);
}
