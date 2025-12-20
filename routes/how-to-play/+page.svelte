<script>
  // How To Play screen
</script>

<div class="how-container">
  <div class="card">
    <h1>How To Play</h1>

    <div class="section">
      <h2>Controls</h2>
      <ul>
        <li>W/A/S/D — Move</li>
        <li>Space — Speed boost for 15 seconds</li>
        <li>Auto-aim and auto-fire at the nearest enemy</li>
        <li>P or Esc — Pause</li>
        <li>R — Reset game</li>
      </ul>
    </div>

    <div class="section">
      <h2>Rules</h2>
      <ul>
        <li>You have 3 lives. Touching any enemy costs 1 life, clears the map, and triggers a 3–2–1 respawn countdown.</li>
        <li>The arena is larger than the screen (about 1.25×). The camera follows your ship.</li>
        <li>Gates are small golden lines that float around. Passing through one triggers an AOE pulse that damages nearby enemies and then the gate disappears.</li>
        <li>Golden multiplier orbs drop from killed enemies. They have a light glow and gently float when far away. Coming close attracts them to you.</li>
      </ul>
    </div>

    <div class="section">
      <h2>Scoring</h2>
      <ul>
        <li>Base points per enemy: Crystal = 1, Square = 3, Triangle = 5</li>
        <li>Final points = Base × Current Multiplier</li>
        <li>Picking up a multiplier orb increases the multiplier by 1 and shows the new total (e.g., ×3)</li>
      </ul>
    </div>

    <div class="section">
      <h2>Enemies</h2>
      <ul>
        <li>Crystal (light blue star): Spawns in groups from corners and swarms the player.</li>
        <li>Square (blue): Attacks at a changing angle relative to you.</li>
        <li>Triangle (red): Upright triangle that moves fast and dashes periodically.</li>
      </ul>
    </div>

    <div class="actions">
      <a class="btn" href="/">Back</a>
      <a class="btn primary" href="/game">Start Game</a>
    </div>
  </div>
</div>

<style>
  .how-container {
    width: 100vw;
    height: 100vh;
    display: grid;
    place-items: center;
    background:
      radial-gradient(1000px 600px at 20% 30%, rgba(0, 234, 255, 0.06) 0%, rgba(0,0,0,0) 60%),
      radial-gradient(900px 600px at 80% 70%, rgba(255, 110, 199, 0.05) 0%, rgba(0,0,0,0) 65%),
      #0b0e14;
    color: #ffffff;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }
  .card {
    width: min(900px, 92vw);
    max-height: 86vh;
    overflow: auto;
    background: #0f1420;
    border: 1px solid #1f2630;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  h1 {
    margin: 0 0 6px;
    font-size: 28px;
  }
  h2 {
    margin: 18px 0 8px;
    font-size: 18px;
    color: #9bd4ff;
  }
  ul {
    margin: 0;
    padding-left: 20px;
    line-height: 1.5;
    opacity: 0.9;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 18px;
  }
  .btn {
    appearance: none;
    border: 1px solid #2c3e50;
    background: #11151d;
    color: #ffffff;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    text-decoration: none;
  }
  .btn:hover { background: #1a1f29; }
  .btn.primary {
    border-color: #00a8ff;
    background: #0f1822;
    box-shadow: 0 0 18px rgba(0, 168, 255, 0.15);
  }
  .btn.primary:hover {
    background: #132032;
    box-shadow: 0 0 22px rgba(0, 168, 255, 0.25);
  }
</style>