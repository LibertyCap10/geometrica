![Geometrica](assets/banner.png)

# 🌌 **GEOMETRICA**  
### *A fast-paced, neon-geometry bullet-evade arena built with Python + Pygame*

> _“Dodge. Drift. Detonate. Ascend.”_

**Geometrica** is an arcade-style, Geometry-Wars-inspired survival game where you pilot a tiny geometric ship through an expanding battlefield of glowing shapes. You auto-target enemies, weave through bullets and swarms, collect multipliers, trigger gates, and unleash bombs while the arena escalates into sacred-geometry bullet hell.

The battlefield grows more intense over time, with new threats, smarter enemies, drifting gates, and multi-phase bosses that resemble mandalas.

---

## 🎮 Features

- ⚡ **Fast, fluid movement** with smooth rotation and auto-aim
- 🖥️ **Fullscreen neon arena** with a scrolling grid background
- 📈 **Scaling difficulty** via spawn rate, new enemies, and bosses
- ✨ **Score multiplier system** with golden orbs and no cap
- 💥 **Gates, bombs, and powerups** for battlefield control
- 🧿 **Four unique mandala bosses**, each with health bars and distinct patterns
- ⏱️ **HUD timer & stats**, plus a detailed pause menu and enemy/boss catalogue
- 🔊 Simple, focused controls so you can stay in flow

---

## 🕹️ Controls

| Action                     | Key(s)                       | Description                                   |
|----------------------------|------------------------------|-----------------------------------------------|
| Move                       | **WASD** or **Arrow Keys**   | Smooth 360° movement                          |
| Boost                      | **SPACE**                    | Speed x2 for a short burst (20s cooldown)     |
| Bomb                       | **E**                        | Clears all non-boss enemies, drops orbs       |
| Pause / Resume             | **ESC**                      | Pause game / open stats screen                |
| Quit from Pause            | **Q** (while paused)         | Immediately close the game                    |
| Start Game (Start Screen)  | **ENTER** or **SPACE**       | Begin playing from the title screen           |
| Restart After Game Over    | **R**                        | Restart a fresh run                           |

---

## 🧭 Game Flow

1. Launch the game → you see the **Start Screen**:
   - Title: **GEOMETRICA**
   - “START” prompt
   - Press **ENTER** or **SPACE** to begin.
2. Once you start:
   - The **timer begins**.
   - Enemies spawn from corners and chase you.
   - You **auto-aim** and auto-fire at the nearest threat.
3. As you survive:
   - Fire rate increases.
   - New enemies (like **Star Swarms**) appear.
   - Bosses enter at specific **time** and **score** thresholds.
4. Use:
   - **Gates** for AoE kills,
   - **Bombs** to clear the screen,
   - **Boost** for emergency dodges.
5. Survive as long as possible and chase insane scores with your **multiplier**.

---

## 💠 Core Mechanics

### 🔄 Player Movement & Rotation

- Movement is handled with **WASD or Arrow keys**, freely in all directions.
- The ship is a **U-shaped** outline; its opening is the *front*.
- The ship **rotates smoothly** toward the current auto-target:
  - Targets nearest **boss** (if any), otherwise nearest **enemy**.
- Bullets always fire from the **front opening** of the U-shape in the facing direction.

---

### 🔫 Auto-Fire

- You don’t aim manually — the game auto-aims for you.
- You always fire in the direction the ship is facing.
- Base fire rate: **2 shots/second**.
- Fire rate increases via:
  - **Fire-rate powerups** (+1.0 shots/sec each).
  - **Score milestones**:
    - At **10,000**, **50,000**, and **100,000** points, fire rate is *doubled* (2×).
- Fire rate increases are shown via floating text and logged in the pause screen event list.

---

### ✨ Score & Multipliers

- Every kill awards a **base score** depending on the enemy (see Enemies section).
- Kills are multiplied by your **current multiplier**.
- **Golden Orbs** increase your multiplier:

  - +1× per orb collected.
  - There is **no cap** on multiplier.
  - Orbs are sucked toward you if you get close.

- Bosses drop **large amounts of orbs** and award big base score values.

---

### 🟢 Boost (Speed Burst)

- Press **SPACE** to activate boost.
- Effects:
  - Movement speed becomes **2×** base for a short time.
  - The ship glows to indicate boost state.
- Duration: **2 seconds**.
- Cooldown: **20 seconds**.
- HUD shows:
  - **“Boost: READY (SPACE)”** when available.
  - Remaining seconds when cooling down.

---

### 💣 Bombs

- Press **E** to detonate a bomb.
- Effects:
  - Clears **all non-boss enemies** from the field.
  - All enemies destroyed by the bomb **still drop golden orbs**.
  - Bosses remain, but **their bullets are cleared**.
  - A large explosion effect at the player position.
- Bomb count:
  - Start with **2 bombs**.
  - Gain **+1 bomb at 500,000 points**.
  - Gain **+1 bomb at 1,000,000 points**.
- Bomb usage & bonuses are tracked in the pause stats.

---

### ❤️ Lives & Respawn

- You start with **3 lives**.
- Extra lives are granted at:
  - **1,000 points**
  - **5,000 points**
  - **10,000 points**
- When you lose a life:
  - The field is cleared (enemies, bullets, etc.).
  - You respawn in the center of the map.
  - A **3… 2… 1…** countdown is shown.
  - You’re temporarily **invincible** after respawn.

If you run out of lives → **Game Over** screen with prompt to **Restart (R)** or **Quit (ESC)**.

---

## 💀 Enemies

All standard enemies spawn from corners and gravitate toward the player.  
Each type has a base score value that is multiplied by your current multiplier.

### 🔹 Triangle — Fast Chaser

- **Color:** Teal  
- **Behavior:**  
  - Very fast straight-line chase toward the player.
  - Common early-game pressure enemy.
- **Base Points:** `5`

---

### 🔹 Square — Slow Tank

- **Color:** Yellow  
- **Behavior:**  
  - Slow, constant homing movement.
  - Acts as moving obstacles that force pathing decisions.
- **Base Points:** `2`

---

### 🔹 Pentagon — Wobbler

- **Color:** Magenta  
- **Behavior:**  
  - Moves toward the player with an added sinusoidal wobble.
  - Harder to predict and dodge.
- **Base Points:** `10`

---

### ⭐ Star Swarm — Predictive Hunters (Late Game)

- **Appearance Condition:**  
  - Appears once the player score reaches **750,000 points**.
- **Behavior:**
  - Spawns in **groups of 5**.
  - Very fast.
  - Coordinates as a group to **predict where the player is going**.
  - Attempts to **box the player in** from multiple angles.
- **Base Points:** `20` per star

These are among the most dangerous non-boss enemies and are meant to pressure even very powerful late-game builds.

---

## 🌈 Powerups & Objects

### 🟡 Golden Orbs

- Dropped by:
  - All regular enemies on death.
  - All bosses on death (in large numbers).
  - Enemies cleared via **bomb** or **gates** still drop orbs.
- **Behavior:**
  - Slowly float from their spawn point.
  - If the player is within a certain radius, they **attract** toward the ship.
- **Effect:**
  - Each orb increases score multiplier by **+1×**.
  - No upper limit.

---

### 🔷 Fire-Rate Powerups

- Appear periodically around the map.
- Like orbs, they get pulled toward the player within an attraction radius.
- On pickup:
  - Increases fire rate by **+1.0 shots/second**.
  - Shows a small floating text (e.g. `+1.00/s`) above the pickup location.
- Their collection and resulting fire rate are reflected in the HUD and the event log.

---

### 🟩 Gates (AoE Kill Zones)

- Visual: Small neon “gate” segments (short lines) drifting slowly around the arena.  
- Behavior:
  - They **move and bounce** off the world’s edges.
  - When the player passes through a gate, it triggers once and then deactivates.
- Effect:
  - Emits an **area-of-effect blast** around the gate.
  - Kills enemies in a small radius around it.
  - Enemies killed by gates:
    - Drop orbs.
    - Award points as normal (affected by multiplier).
  - A new gate spawns elsewhere to keep the flow going.
- Stats:
  - Number of gates triggered is tracked and shown in pause stats.

---

## 🧿 Bosses

Bosses are large sacred-geometry entities, each with:

- **Health bar** above them.
- Unique multi-ring mandala visuals.
- Distinct movement and bullet patterns.
- **Huge base point values** and **large orb drops** on death.

### 👁️ Boss I — *Violet Guardian*

- **Spawn Condition:**  
  - Appears at **1:00** game time.
- **Health:** `50`
- **Base Points:** `1,000`
- **Colors:** Violet / Lavender / White  
- **Behavior:**
  - Slowly moves toward the player.
  - Periodically shoots aimed bullets at the player.
- **Rewards:**
  - Drops roughly **15 golden orbs** on death.
  - Big score boost when multiplier is high.

---

### 🌸 Boss II — *Silver Blossom*

- **Spawn Condition:**  
  - Appears when score reaches **250,000**.
- **Health:** `200`
- **Base Points:** `5,000`
- **Colors:** White / Silver / Pink  
- **Behavior:**
  - More complex mandala with petals.
  - Similar homing + shooting, but more resilient than Boss I.
- **Rewards:**
  - Drops around **25 golden orbs**.
  - Excellent mid-run score injection.

---

### 🔥 Boss III — *Golden Inferno*

- **Spawn Condition:**  
  - Appears when score reaches **500,000**.
- **Health:** `1000`
- **Base Points:** `15,000`
- **Colors:** Gold / Red / Black  
- **Behavior:**
  - Larger, densely ornamented mandala.
  - More threatening presence on the field.
- **Rewards:**
  - Drops around **40 golden orbs**.
  - Massive scoring and multiplier boost potential.

---

### 💀🌟 Boss IV — *Grand Mandala (Bullet-Hell King)*

- **Spawn Condition:**  
  - Appears when score reaches **1,000,000**.
- **Health:** `1000` (reduced for fairness)
- **Base Points:** `50,000`
- **Size:** ~2× larger than Boss III  
- **Colors:** Golden / Red / Black  
- **Behavior:**
  - Oscillates horizontally across the arena.
  - Has **8 evenly spaced emitters** around its circle.
  - Continuously fires rotating bullet streams.
  - Creates complex, beautiful bullet patterns that challenge movement.
- **Rewards:**
  - Drops around **70 golden orbs**.
  - Huge point payout, especially at high multipliers.

---

## ⏱ HUD & Timer

- The HUD shows:
  - **Centered top timer** in **MM:SS** format (scoreboard style).
  - Score, multiplier, fire rate.
  - Boost status (ready or cooldown).
  - Bomb count.
  - Remaining lives.
- Timer starts when you exit the **start screen** and begin playing.

---

## ⏸ Pause Screen

Press **ESC** during gameplay to open the **Pause Menu**, which includes:

### 📊 Stats

- Time survived
- Current score
- Current multiplier
- Current fire rate
- Lives remaining and extra lives earned
- Bombs remaining and bombs used
- Total enemies killed
- Enemies killed via gates
- Orbs and fire powerups collected
- Gates triggered
- Boost uses
- Which bosses have been defeated
- Number of times your fire rate has been doubled

### 📚 Enemy & Boss Catalogue

- Short descriptions of:
  - Triangle, Square, Pentagon
  - Star Swarm
  - Boss I, Boss II, Boss III, Boss IV

### 📝 Event Log

- A scrolling list of recent game events, e.g.:
  - Boss spawns
  - Boss defeats
  - Fire rate milestones
  - Extra lives gained
  - Bomb gains/uses
  - Triangle burst waves
  - Gate triggers

### ⏹ Quit Option

- While paused, press **Q** to quit the game immediately.

---

## 🧪 Early Game & Difficulty Scaling

- At the start:
  - Enemies spawn rapidly from all corners.
  - Frequent **triangle bursts** are added to keep you moving early.
- Over time:
  - Spawn intervals shrink.
  - More enemies are on screen.
  - Fire rate increases via powerups and milestones.
- Late game:
  - Star Swarms appear to aggressively **box you in**.
  - High-health bosses spawn based on score thresholds.
  - The final boss introduces a bullet-hell pattern challenge.

---

## ⚙️ Running the Game

### Requirements

- **Python** 3.10+ (3.11/3.12+ are also fine)
- **Pygame** 2.x

### Installation

```bash
pip install pygame
