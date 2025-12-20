import type { RequestHandler } from '@sveltejs/kit';
import { json } from '@sveltejs/kit';
import {
  readLeaderboard,
  addEntry,
  qualifies,
  sanitizeName,
  LEADERBOARD_CAP
} from '$lib/server/leaderboard';

/**
 * GET /api/leaderboard
 * Returns the current top-N leaderboard entries.
 */
export const GET: RequestHandler = async () => {
  try {
    const entries = await readLeaderboard();
    return json({ entries, cap: LEADERBOARD_CAP });
  } catch {
    // If something goes wrong, return an empty leaderboard to keep UX responsive
    return json({ entries: [], cap: LEADERBOARD_CAP }, { status: 500 });
  }
};

/**
 * POST /api/leaderboard
 * Body: { name: string, score: number }
 * Inserts an entry if it qualifies for top-N; otherwise returns 409.
 */
export const POST: RequestHandler = async ({ request }) => {
  let name = 'Player';
  let score = 0;

  try {
    const body = await request.json();
    name = typeof body?.name === 'string' ? body.name : 'Player';
    score = Number(body?.score);
  } catch {
    return json({ message: 'Invalid payload' }, { status: 400 });
  }

  if (!Number.isFinite(score) || score < 0) {
    return json({ message: 'Invalid score' }, { status: 400 });
  }

  try {
    const current = await readLeaderboard();
    const doesQualify = qualifies(score, current, LEADERBOARD_CAP);

    if (!doesQualify) {
      const min = current.length ? current[current.length - 1].score : 0;
      return json(
        { message: 'Not a top score', min, cap: LEADERBOARD_CAP },
        { status: 409 }
      );
    }

    const { rank, entries } = await addEntry(sanitizeName(name), score);
    return json({ rank, entries, cap: LEADERBOARD_CAP }, { status: 201 });
  } catch {
    return json({ message: 'Unable to save score' }, { status: 500 });
  }
};