# Space Shooter Game Plan

## Context
Building a browser-based Space Invaders-style game for children (ages 8-12) to run in Chrome. Modern neon/glow aesthetic, classic horizontal-only player movement, grid-formation enemies. Personalized with photos of two daughters (`gili.png`, `tamar.jpg`) as enemy sprites. Includes Web Audio sound effects and child-friendly difficulty pacing.

---

## Game Characterization Summary

| Aspect | Choice |
|---|---|
| Visual style | Modern neon/glow — glowing vector shapes, particle FX, dark space background |
| Player movement | Horizontal only — ship at bottom, moves left/right |
| Controls | Keyboard: Arrow keys / WASD to move, Space to shoot |
| Enemy behavior | Grid formation, march side-to-side, descend on wall hit |
| Enemy waves | Multiple waves, each slightly faster/denser |
| Boss enemies | Boss at end of each wave — large photo, HP bar, fires patterns |
| Power-ups | Drop from enemies: spread shot, shield, speed boost, rapid fire |
| Player lives | 3 lives |
| Difficulty | Easy (ages 8-12): slow-medium pace, enemies shoot infrequently |
| Audio | Sound effects via Web Audio API (no external files) |
| Leaderboard | Top 5 scores saved to `localStorage` |
| Tech stack | Single `index.html` — embedded CSS + JS, plain Canvas 2D, no dependencies |

---

## File Structure

```
claudeCodeChallenge/
├── index.html      ← entire game (HTML + <style> + <script>)
├── gili.png        ← daughter 1 photo (user provides)
└── tamar.jpg       ← daughter 2 photo (user provides)
```

---

## Child-Friendly Difficulty Settings (Easy / ages 8-12)

| Parameter | Value |
|---|---|
| Enemy march speed (start) | 40 px/s (vs 80 for normal) |
| Enemy bullet speed | 120 px/s (vs 220 for normal) |
| Enemy shoot interval | Every 3–5 seconds per enemy (rare) |
| Player bullet speed | 350 px/s (fast, feels responsive) |
| Player move speed | 200 px/s |
| Lives | 3 |
| Wave speed increase | +10% per wave (gentle ramp) |
| Boss HP | 20 hits |
| Boss bullet speed | 100 px/s |

---

## Sound Effects (Web Audio API — no files needed)

All sounds synthesized in JS using `AudioContext`. No external audio files required.

| Event | Sound Description | Synthesis |
|---|---|---|
| Player shoot | Short high-pitched "pew" | Oscillator, 880Hz → 220Hz, 0.1s |
| Enemy hit | Soft "pop" burst | Noise burst + low-pass filter, 0.15s |
| Enemy killed | Satisfying "zap" | Descending tone, 440Hz → 110Hz, 0.2s |
| Player hit | Low "thud" + rumble | Low freq noise, 0.3s |
| Power-up collect | Rising chime | Ascending 3-note arpeggio, 0.4s |
| Boss spawn | Dramatic low rumble | Sub-bass oscillator swell, 1s |
| Boss hit | Heavy "clang" | FM synthesis hit, 0.2s |
| Boss dies | Victory fanfare | Ascending melody 5 notes, 0.8s |
| Game over | Descending "wah-wah" | Two descending tones, 0.6s |
| Wave complete | Short jingle | 3-note ascending chime, 0.5s |

**Audio helper pattern:**
```js
const audioCtx = new AudioContext();

function playShoot() {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.frequency.setValueAtTime(880, audioCtx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(220, audioCtx.currentTime + 0.1);
  gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.1);
  osc.start(); osc.stop(audioCtx.currentTime + 0.1);
}
```

AudioContext is created on first user interaction (keyboard press) to comply with browser autoplay policy.

---

## Enemy Photo Integration

| Enemy Rows | Photo | Size | Color Ring | Points |
|---|---|---|---|---|
| Rows 1–2 (small) | `gili.png` | 32px radius | Magenta `#ff00ff` | 10 pts |
| Rows 3–5 (large) | `tamar.jpg` | 44px radius | Green `#00ff88` | 20 pts |
| **Boss** | `tamar.jpg` | 80px radius | Red `#ff3300` | 500 pts |

Photos rendered as circular cropped portraits with neon glow rings using Canvas `clip()`.

---

## Architecture

### Game States
```
START → PLAYING → WAVE_CLEAR → BOSS → BOSS_DEAD → [next wave or GAME_OVER]
                                                           ↓
                                                      LEADERBOARD → START
```

### Core Systems

**Game Loop**
- `requestAnimationFrame`, delta-time capped at 50ms
- Separate `update(dt)` and `draw()` calls

**Canvas:** 600×800px, centered, dark background `#070715`

**Player**
- Glowing cyan triangle `#00ffff`
- Spread shot (3-way), shield (absorbs 1 hit), power-up arc timer display

**Enemies**
- 5 rows × 10 columns grid
- Rows 1–2: Gili (magenta), Rows 3–5: Tamar (green)
- March sideways, descend on wall hit, speed gently increases

**Boss**
- Large Tamar circular photo, red glow
- Phase 1 (>50% HP): slow spread; Phase 2 (<50% HP): aimed shots
- HP bar at top of screen

**Power-ups** (15% drop + guaranteed boss drop)
- Spread Shot (purple "S"), Shield (blue "B"), Speed Boost (yellow "V"), Rapid Fire (orange "R")

**Particles**
- Enemy death burst (enemy ring color), player death explosion, power-up ripple

**Scoring & Leaderboard**
- Top 5 in `localStorage`, 3-char name entry on game over

---

## Implementation Steps

1. **HTML skeleton** — canvas 600×800, CSS centering, neon border
2. **Image preloading** — load `gili.png` + `tamar.jpg`, show "Loading..." until ready
3. **Audio system** — `AudioContext` + all sound functions, initialized on first keypress
4. **CONFIG object** — all easy-difficulty tuning values in one place
5. **Entity classes** — Player, Bullet, Enemy (with `drawCircularPhoto`), EnemyGrid, Boss, PowerUp, Particle
6. **Game state machine** — transition functions for all states
7. **Input handling** — `keys` Set from keydown/keyup events
8. **Collision detection** — AABB for bullets/enemies/player/power-ups
9. **Neon rendering helpers** — `drawGlow()`, star field (80 dots), UI elements
10. **Leaderboard screen** — canvas-rendered table, name entry via `prompt()`

---

## Verification

1. Place `gili.png` and `tamar.jpg` in project folder alongside `index.html`
2. Open `index.html` in Chrome — brief "Loading..." then start screen
3. Press any key — `AudioContext` initializes, start game
4. Confirm Gili (rows 1–2, magenta) and Tamar (rows 3–5, green) render as circular photos
5. Shoot enemy — hear "pew" + "zap" sounds on hit
6. Get hit — hear "thud" sound, lose a life
7. Collect power-up — hear chime, confirm effect + arc timer
8. Kill all enemies → hear wave complete jingle, boss spawns with rumble sound
9. Kill boss → hear victory fanfare, next wave starts (slightly faster)
10. Lose all 3 lives → game over sound, score entry prompt
11. Confirm `localStorage` persists scores after page refresh
12. Check Chrome DevTools console — no errors
