# Cyber Breach — How to Run and Play

## What This Project Is

Cyber Breach is a puzzle game built for the Formal Languages & Automata (FLA) course.
You play as a hacker sending data packets past a firewall modeled as a real NFA,
converted to a DFA, and then minimized — the same automaton theory from class, made
interactive and playable in a browser.

**Two graded components:**
- JFLAP Implementation (10 marks) — NFA design, NFA→DFA conversion, DFA minimization
- GUI Implementation (10 marks) — browser-based game interface driven by the DFA

---

## Project Files

```
fla_project2/
├── server.py                  ← Run this to start the game
├── index.html                 ← Browser UI (auto-served by server.py)
├── automaton.py               ← NFA, DFA, minimization algorithms
├── missions.py                ← 5 mission definitions
├── main_pygame_legacy.py      ← Original pygame version (kept for reference)
├── README.md                  ← Transition tables and automaton design
├── HOW_TO_RUN_AND_PLAY.md     ← This file
├── jflap/
│   ├── cyber_breach_nfa.jff       Open in JFLAP 7.1 (NFA, 8 states)
│   ├── cyber_breach_dfa.jff       Open in JFLAP 7.1 (DFA, 7 states)
│   └── cyber_breach_min_dfa.jff   Open in JFLAP 7.1 (Min-DFA, 6 states)
└── tests/
    └── test_automaton.py      ← 98 automated tests
```

---

## Step 1 — Install Python

You need Python 3.9 or later. No other packages required — `server.py` uses only the
Python standard library.

```bash
python3 --version
```

---

## Step 2 — Run the Game

```bash
cd fla_project2
python3 server.py
```

You will see:

```
Cyber Breach server running at http://localhost:8080/
Press Ctrl+C to stop.
```

Open **http://localhost:8080** in any browser (Chrome, Firefox, Safari, Edge).

To stop the server: press `Ctrl+C` in the terminal.

---

## Step 3 — Run the Automated Tests (optional)

```bash
pip install pytest          # one-time install
pytest tests/test_automaton.py -v
```

Expected: **98 passed, 0 failed** — covers ε-closure, subset construction,
minimization, trap state absorption, and all 5 mission solutions.

---

## Step 4 — Open in JFLAP 7.1

1. Download JFLAP 7.1 from [jflap.org](https://www.jflap.org).
2. Open JFLAP → **File → Open** → select any `.jff` file from `jflap/`.
3. Test strings: **Input → Multiple Run** → type e.g. `PAL`, click Run.
4. NFA→DFA: open the NFA file → **Convert → Convert to DFA**.
5. Minimize: open the DFA file → **Convert → Minimize DFA**.

---

## How to Play

### The Goal

Send the right sequence of data packets to reach the **target server** (accept state).
A wrong order triggers the **intrusion alarm** (trap state) — game over for that round.

### The Alphabet — 5 Packet Types

| Key | Packet  | Description              |
|-----|---------|--------------------------|
| P   | Ping    | Test the connection       |
| A   | Auth    | Send authentication       |
| E   | Encrypt | Open an encrypted channel |
| X   | Proxy   | Bounce through proxy node |
| L   | Payload | Drop the final payload    |

---

### The Game Screen

```
┌─────────────────────────────────────────────────────────┐
│  CYBER BREACH           Mission 1    ⚡ Theory           │  ← Header
├──────────────┬──────────────────────────────────────────┤
│  MISSIONS    │  Mission 1: Layer 1 Breach               │  ← Mission info
│  ① Mission 1 │  "Send Ping → Auth → Payload"            │
│  ② Mission 2 │  💡 Try P → A → L                        │
│  ③ Mission 3 │──────────────────────────────────────────│
│  ④ Mission 4 │  [STATUS: Current state: {q0,q2}]        │  ← Status banner
│  ⑤ Mission 5 │──────────────────────────────────────────│
│              │  [ Live DFA State Diagram — SVG ]        │  ← State diagram
│              │    States: circles, arrows with labels   │
│              │    Yellow = current  Green = accept      │
│              │    Red = trap                            │
│              │──────────────────────────────────────────│
│              │  [P Ping] [A Auth] [E Encrypt]           │  ← Packet tiles
│              │  [X Proxy] [L Payload]                   │
│              │──────────────────────────────────────────│
│              │  [▶ SEND]  [↺ RESET]  [📋 SHOW TABLE]   │  ← Controls
│              │──────────────────────────────────────────│
│              │  Log: P → A → ...                        │  ← Packet log
└──────────────┴──────────────────────────────────────────┘
```

### Controls

| Action              | Mouse                    | Keyboard    |
|---------------------|--------------------------|-------------|
| Select Ping         | Click **P** tile         | `P`         |
| Select Auth         | Click **A** tile         | `A`         |
| Select Encrypt      | Click **E** tile         | `E`         |
| Select Proxy        | Click **X** tile         | `X`         |
| Select Payload      | Click **L** tile         | `L`         |
| Send selected packet| Click **▶ SEND**         | `Enter`     |
| Reset mission       | Click **↺ RESET**        | `R`         |
| Toggle table        | Click **📋 SHOW TABLE**  | `T`         |
| View theory         | Click **⚡ Theory**      | —           |
| Close modal         | Click **✕ Close**        | `Escape`    |

### Reading the State Diagram

The DFA state diagram updates live after every packet sent.

| Circle colour | Meaning                              |
|---------------|--------------------------------------|
| Yellow (pulsing) | Current state (where you are now) |
| Green (double ring) | Accept state — server reached   |
| Red           | Trap state — intrusion alarm         |
| Dark blue     | Regular intermediate state           |

The **→** arrow into the leftmost state marks the DFA start state.

### The TABLE Overlay

Press **T** to show the Minimized DFA transition table. The current state row
highlights in amber, the accept row in green, and the trap row in red.

### The Theory Panel

Click **⚡ Theory** to open the full NFA → DFA → minimization explanation, including
both transition tables as HTML — useful for the viva.

---

## The 5 Missions

Completed missions show a green **✓** in the sidebar. All progress persists until
you reload the page.

---

### Mission 1 — Layer 1 Breach

**Story:** The firewall expects a simple authenticated packet burst.

**Solution:** `P → A → L`

| Step | Packet | State after |
|------|--------|-------------|
| Start | — | {q0,q2} |
| 1 | P | {q1,q3} |
| 2 | A | {q3} |
| 3 | L | **{q4} ✓ BREACH** |

**Why it works:** Ping opens the route. Auth moves into the authenticated zone (q3).
Payload is the only packet q3 accepts.

**Wrong tries:**
- `A, L` → A from start → TRAP immediately
- `P, P, A, L` → second P loops in q3, then A from q3 → TRAP

---

### Mission 2 — Epsilon Tunnel

**Story:** Use the proxy ε-tunnel to skip Layer 1.

**Solution:** `E → L`

| Step | Packet | State after |
|------|--------|-------------|
| Start | — | {q0,q2} |
| 1 | E | {q3} |
| 2 | L | **{q4} ✓ BREACH** |

**Why it works:** The DFA start state is `{q0,q2}` — not just `{q0}`. The
ε-transition `q0 →ε→ q2` is consumed at automaton construction time (ε-closure of
{q0} = {q0,q2}). q2 has an E-transition, so the DFA start state accepts Encrypt even
though q0 alone does not. This is the central NFA insight the game demonstrates.

---

### Mission 3 — Proxy Bounce

**Story:** Bounce through the Proxy node to confuse the firewall.

**Solution:** `X → P → L`

| Step | Packet | State after |
|------|--------|-------------|
| Start | — | {q0,q2} |
| 1 | X | {q5,q6} |
| 2 | P | {q7} |
| 3 | L | **{q4} ✓ BREACH** |

**Why it works:** X sends you down the redundant proxy path (q5 → q6 → q7). State
q7 behaves identically to q3 — it also accepts Payload to reach q4. In the minimized
DFA, q3 and q7 are merged into the same state because they are indistinguishable by
Myhill-Nerode table-filling.

---

### Mission 4 — Stealth Payload

**Story:** Stay low — avoid Pings, the IDS watches for them.

**Solution:** `E → L`

Same as Mission 2. Two missions can share a solution because the DFA has one accept
state reachable by multiple paths.

**Avoid:** `P, P, A, L` — the double-Ping pattern loops in q3, then A from q3 → TRAP.

---

### Mission 5 — Full Chain Infiltration

**Story:** Reach the server and authenticate again to hold the connection.

**Solution:** `P → A → L → A`

| Step | Packet | State after |
|------|--------|-------------|
| Start | — | {q0,q2} |
| 1 | P | {q1,q3} |
| 2 | A | {q3} |
| 3 | L | {q4} ← server reached |
| 4 | A | **{q4} ✓ still accepted** |

**Why it works:** The accept state q4 has self-loops on both P and A — sending more
P or A packets after reaching the server keeps you accepted. Sending E, X, or L from
q4 goes to TRAP.

---

## Why Some Sequences Fail

| Sequence | Fails because |
|----------|---------------|
| A | No A-transition from {q0,q2} → TRAP |
| L | No L-transition from {q0,q2} → TRAP |
| E (alone) | Reaches {q3} but {q3} is not accept |
| X (alone) | Reaches {q5,q6}, not accept |
| P, A, E | PA → {q3}; E from {q3} → TRAP |
| P, E, L | P → {q1,q3}; E from {q1,q3} → TRAP |
| X, L | X → {q5,q6}; L from {q5,q6} → TRAP |
| Anything after TRAP | TRAP absorbs every symbol — no recovery |

---

## Viva / Exam Quick-Reference

**Q: Why does E,L get accepted when q0 has no E-transition?**
The DFA start state is `{q0,q2}`, not `{q0}` alone. ε-closure({q0}) = {q0,q2}
because of the ε-transition q0→q2. q2 has an E-transition to q3, so the DFA start
state does too.

**Q: Why do D2={q3} and D5={q7} merge in minimization?**
Table-filling (Myhill-Nerode): every symbol produces the same successor class from
both states — TRAP on A/E/X, accept state on L, self-loop on P. No string
distinguishes them, so they are merged into one state.

**Q: What is the trap state?**
A non-accept absorbing state added during subset construction wherever the NFA
produces the empty set. `δ(TRAP, a) = TRAP` for all `a ∈ Σ`. It models the firewall
alarm: once triggered, no further packet can undo it.

**Q: What is an ε-transition?**
A state change that consumes no input symbol. Here, `q0 →ε→ q2` means the proxy route
is silently available from the start. The NFA simulation takes ε-closure at every
step; the DFA start state must be ε-closure({q0}) = {q0,q2}.

---

## API Reference (for developers)

The backend exposes these endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serves index.html |
| GET | `/api/missions` | Returns all 5 mission definitions (JSON array) |
| GET | `/api/automaton` | Returns NFA, DFA, and min-DFA transition tables (JSON) |
| POST | `/api/step` | `{"state":"...", "packet":"P"}` → `{"next_state":"...", "accepted":bool, "trapped":bool}` |
| POST | `/api/check` | `{"sequence":["P","A","L"]}` → `{"accepted":bool, "path":[...], "trapped":bool}` |

---

*Project: Cyber Breach | Course: Formal Languages & Automata | JFLAP 7.1 + Python + HTML/CSS/JS*
