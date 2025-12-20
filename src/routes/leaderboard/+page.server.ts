import type { PageServerLoad } from './$types';
import { readLeaderboard, LEADERBOARD_CAP } from '$lib/server/leaderboard';

export const load: PageServerLoad = async () => {
  const entries = await readLeaderboard();
  return {
    entries,
    cap: LEADERBOARD_CAP
  };
};