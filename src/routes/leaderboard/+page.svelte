<script>
  export let data;
  const entries = data?.entries ?? [];
  const cap = data?.cap ?? 25;
</script>

<div class="leaderboard-container">
  <div class="card">
    <div class="lb-header">
      <h1 class="lb-title">Leaderboard</h1>
      <div class="lb-sub">Top {cap} Scores</div>
    </div>

    <table class="lb-table">
      <thead>
        <tr>
          <th style="width: 80px;">Rank</th>
          <th>Name</th>
          <th style="text-align: right;">Score</th>
        </tr>
      </thead>
      <tbody>
        {#if entries.length === 0}
          <tr>
            <td colspan="3" style="opacity: 0.8;">No scores yet. Be the first!</td>
          </tr>
        {:else}
          {#each entries as e, i}
            <tr>
              <td>{i + 1}</td>
              <td>{e.name}</td>
              <td style="text-align: right;">{e.score.toLocaleString()}</td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>

    <div class="lb-actions">
      <a class="btn" href="/">Back</a>
      <a class="btn primary" href="/game">Start Game</a>
    </div>
  </div>
</div>