// Server-side leaderboard utilities.
// Persists a top-N list of { name, score, ts } in a JSON file.
//
// Reads environment:
//   - LEADERBOARD_CAP (default 25)
//   - LEADERBOARD_PATH (default ./data/leaderboard.json)
//
// Exports:
//  - readLeaderboard(): Promise<LeaderboardEntry[]>
//  - qualifies(score, current, cap?): boolean
//  - addEntry(name, score): Promise<{ rank: number; entries: LeaderboardEntry[] }>
//  - sanitizeName(name): string
//
// Notes:
//  - Sorting: score DESC, then timestamp ASC (earlier first), then name ASC.
//  - Writes are atomic (temp file + rename).
//  - Missing or malformed file initializes to an empty array.

import { promises as fs } from 'fs';
import path from 'path';

export type LeaderboardEntry = {
  name: string;
  score: number;
  ts: number; // unix ms timestamp (used for tie-breaking)
};

// Resolve cap from env (default 25)
function getCapFromEnv(): number {
  const raw = process.env.LEADERBOARD_CAP;
  const n = raw ? Number(raw) : NaN;
  if (Number.isFinite(n) && n > 0) return Math.floor(n);
  return 25;
}

export const LEADERBOARD_CAP = getCapFromEnv();

// Resolve storage path (env override supported)
function getStoragePath(): string {
  const envPath = process.env.LEADERBOARD_PATH;
  if (envPath && envPath.trim().length > 0) {
    return path.resolve(envPath);
  }
  return path.join(process.cwd(), 'data', 'leaderboard.json');
}

async function ensureParentDir(filePath: string): Promise<void> {
  const dir = path.dirname(filePath);
  try {
    await fs.mkdir(dir, { recursive: true });
  } catch {
    // no-op if already exists or cannot be created
  }
}

function sortEntries(entries: LeaderboardEntry[]): LeaderboardEntry[] {
  // Sort by score desc, then timestamp asc (earlier first), then name asc
  return entries.slice().sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.ts !== b.ts) return a.ts - b.ts;
    return a.name.localeCompare(b.name);
  });
}

function clampTop(entries: LeaderboardEntry[], cap = LEADERBOARD_CAP): LeaderboardEntry[] {
  const sorted = sortEntries(entries);
  return sorted.slice(0, cap);
}

export async function readLeaderboard(): Promise<LeaderboardEntry[]> {
  const filePath = getStoragePath();
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    const parsed = JSON.parse(raw) as LeaderboardEntry[] | unknown;
    if (!Array.isArray(parsed)) return [];
    // Filter to valid structure
    const cleaned: LeaderboardEntry[] = parsed
      .map((e) => ({
        name: typeof (e as any).name === 'string' ? (e as any).name : 'Player',
        score: Number((e as any).score) || 0,
        ts: Number((e as any).ts) || Date.now()
      }))
      .filter((e) => Number.isFinite(e.score) && e.score >= 0);
    return clampTop(cleaned);
  } catch (err: any) {
    // If file missing, initialize it
    if (err && err.code === 'ENOENT') {
      await ensureParentDir(filePath);
      await atomicWrite(filePath, JSON.stringify([], null, 2));
      return [];
    }
    // Any other error: return empty and allow recovery
    return [];
  }
}

// Atomic write: write to temp file, then rename over target
async function atomicWrite(filePath: string, data: string): Promise<void> {
  await ensureParentDir(filePath);
  const tmp = `${filePath}.tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  await fs.writeFile(tmp, data, 'utf8');
  await fs.rename(tmp, filePath);
}

export function sanitizeName(input: string): string {
  // Trim, collapse whitespace, strip control chars, limit length
  const trimmed = (input ?? '').trim();
  // Remove non-printable ASCII
  let safe = trimmed.replace(/[^\x20-\x7E]/g, '');
  // Collapse whitespace runs
  safe = safe.replace(/\s+/g, ' ');
  // Limit length
  if (safe.length > 24) safe = safe.slice(0, 24);
  // Basic fallback
  if (safe.length === 0) safe = 'Player';
  return safe;
}

export function qualifies(
  score: number,
  current: LeaderboardEntry[],
  cap = LEADERBOARD_CAP
): boolean {
  if (!Number.isFinite(score) || score < 0) return false;
  if (current.length < cap) return true;
  const sorted = sortEntries(current);
  const min = sorted[sorted.length - 1]?.score ?? 0;
  return score > min;
}

export async function addEntry(
  name: string,
  score: number
): Promise<{ rank: number; entries: LeaderboardEntry[] }> {
  const filePath = getStoragePath();
  const entries = await readLeaderboard();

  const entry: LeaderboardEntry = {
    name: sanitizeName(name),
    score: Math.max(0, Math.floor(score || 0)),
    ts: Date.now()
  };

  // Insert and clamp
  const updated = clampTop([...entries, entry]);

  // Find rank (1-based)
  const sorted = sortEntries(updated);
  const idx = sorted.findIndex(
    (e) => e.name === entry.name && e.score === entry.score && e.ts === entry.ts
  );
  const rank = idx >= 0 ? idx + 1 : -1;

  // Persist
  await atomicWrite(filePath, JSON.stringify(updated, null, 2));

  return { rank, entries: updated };
}