// Centralized gameplay configuration loaded from PUBLIC_* environment variables.
// IMPORTANT: In SvelteKit, use $env/static/public (not import.meta.env) so values are
// replaced at build/startup. After changing your .env, restart the dev server.
//
// Example .env:
//   PUBLIC_PLAYER_BASE_SPEED=300
//   PUBLIC_PLAYER_FIRE_RATE=12
//   PUBLIC_SPAWN_MODE=exp
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
  PUBLIC_TRAIL_MAX,
  PUBLIC_ZOOM_WORLD_EXPONENT
} from '$env/static/public';

type SpawnMode = 'exp' | 'lin';

function num(raw: string | undefined, fallback: number): number {
  if (raw == null || raw === '') return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function str(raw: string | undefined, fallback: string): string {
  return raw == null || raw === '' ? fallback : String(raw);
}

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

export const CFG = {
  world: {
    scale: num(PUBLIC_WORLD_SCALE, 1.25),
    gridSpacing: num(PUBLIC_GRID_SPACING, 60),
    // How strongly the in-game Zoom setting changes world size.
    // 1.0 = world scales in direct proportion to zoom (keeps same relative framing).
    // <1.0 = zooming out reveals relatively more of the world (edges appear sooner).
    // >1.0 = zooming out increases world faster than view (feels more "zoomed in" overall).
    zoomWorldExponent: num(PUBLIC_ZOOM_WORLD_EXPONENT, 1.0)
  },
  player: {
    baseSpeed: num(PUBLIC_PLAYER_BASE_SPEED, 240),
    boostMultiplier: num(PUBLIC_PLAYER_BOOST_MULTIPLIER, 1.8),
    boostDuration: num(PUBLIC_PLAYER_BOOST_DURATION, 15),
    fireRate: num(PUBLIC_PLAYER_FIRE_RATE, 9) // bullets per second
  },
  bullet: {
    speed: num(PUBLIC_BULLET_SPEED, 580),
    life: num(PUBLIC_BULLET_LIFE, 1.8),
    radius: num(PUBLIC_BULLET_RADIUS, 3)
  },
  spawn: {
    mode: (str(PUBLIC_SPAWN_MODE, 'exp').toLowerCase() as SpawnMode) || 'exp',
    baseInterval: num(PUBLIC_SPAWN_BASE_INTERVAL, 1.15),
    minInterval: num(PUBLIC_SPAWN_MIN_INTERVAL, 0.1),
    decayPerSec: num(PUBLIC_SPAWN_DECAY_PER_SEC, 0.986),
    linearSlope: num(PUBLIC_SPAWN_LINEAR_SLOPE, 0.006),
    groupChance: clamp(num(PUBLIC_SPAWN_GROUP_CHANCE, 0.6), 0, 1),
    maxEnemies: num(PUBLIC_MAX_ENEMIES, 110)
  },
  enemies: {
    trap: {
      speedMin: num(PUBLIC_TRAP_SPEED_MIN, 85),
      speedMax: num(PUBLIC_TRAP_SPEED_MAX, 105)
    },
    square: {
      speedMin: num(PUBLIC_SQUARE_SPEED_MIN, 90),
      speedMax: num(PUBLIC_SQUARE_SPEED_MAX, 110)
    },
    triangle: {
      baseMin: num(PUBLIC_TRIANGLE_SPEED_BASE_MIN, 170),
      baseMax: num(PUBLIC_TRIANGLE_SPEED_BASE_MAX, 195),
      dashBonus: num(PUBLIC_TRIANGLE_DASH_BONUS, 70)
    }
  },
  orbs: {
    magnetRange: num(PUBLIC_ORB_MAGNET_RANGE, 260),
    seekSpeed: num(PUBLIC_ORB_SEEK_SPEED, 320),
    wanderForce: num(PUBLIC_ORB_WANDER_FORCE, 9)
  },
  gates: {
    length: num(PUBLIC_GATE_LENGTH, 100),
    thickness: num(PUBLIC_GATE_THICKNESS, 3),
    aoeRadius: num(PUBLIC_GATE_AOE_RADIUS, 150),
    spawnInterval: num(PUBLIC_GATE_SPAWN_INTERVAL, 7),
    maxGates: num(PUBLIC_MAX_GATES, 3)
  },
  trail: {
    max: num(PUBLIC_TRAIL_MAX, 80)
  }
} as const;

// Convenience derived values
export const DERIVED = {
  fireInterval: 1 / CFG.player.fireRate
} as const;

/**
 * Compute the enemy spawn interval at a given elapsed time (seconds),
 * based on configured mode and parameters.
 */
export function spawnInterval(elapsedSec: number): number {
  const s = CFG.spawn;
  if (s.mode === 'lin') {
    // Linear: interval decreases linearly over time
    const t = Math.max(0, elapsedSec);
    return Math.max(s.minInterval, s.baseInterval - s.linearSlope * t);
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