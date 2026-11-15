# Cyber Breach — NFA/DFA-Based Firewall Infiltration Game

A puzzle-strategy game in which a hacker infiltrates a secured network by
sending sequences of data packets past a layered firewall modeled as an NFA,
its equivalent DFA, and the minimized DFA.

## Project Components

| Component | Marks | Description |
|---|---|---|
| JFLAP Implementation | 10 | NFA design, NFA→DFA, DFA minimization, test strings |
| GUI Implementation   | 10 | pygame game interface, state highlighting, trap state, 5 missions |

## Running the Game

```bash
pip install pygame-ce
python3 main.py
```

## Running Tests

```bash
pip install pytest
pytest tests/test_automaton.py -v
```

## Automaton Design

### Alphabet (packet types)

| Symbol | Packet type |
|---|---|
| P | Ping |
| A | Auth |
| E | Encrypt |
| X | Proxy (also ε-transition source) |
| L | Payload |

### NFA (8 states)

```
States: q0 (start), q1, q2, q3, q4 (accept), q5, q6, q7
ε-transitions: q0→q2  q1→q3  q5→q6
```

| State | P | A | E | X | L | ε |
|---|---|---|---|---|---|---|
| q0 | {q1} | — | — | — | — | {q2} |
| q1 | — | {q3} | — | — | — | {q3} |
| q2 | — | — | {q3} | {q5} | — | — |
| q3 | {q3} | — | — | — | {q4} | — |
| q4 | {q4} | {q4} | — | — | — | — |
| q5 | {q7} | — | — | — | — | {q6} |
| q6 | {q7} | — | — | — | — | — |
| q7 | {q7} | — | — | — | {q4} | — |

### DFA (7 states, subset construction)

| State | P | A | E | L | X |
|---|---|---|---|---|---|
| **D0={q0,q2}** | D1 | TRAP | D2 | TRAP | D4 |
| D1={q1,q3} | D2 | D2 | TRAP | D3 | TRAP |
| D2={q3} | D2 | TRAP | TRAP | D3 | TRAP |
| **D3={q4}** ✓ | D3 | D3 | TRAP | TRAP | TRAP |
| D4={q5,q6} | D5 | TRAP | TRAP | TRAP | TRAP |
| D5={q7} | D5 | TRAP | TRAP | D3 | TRAP |
| TRAP | TRAP | TRAP | TRAP | TRAP | TRAP |

### Minimized DFA (6 states, Myhill-Nerode)

D2={q3} and D5={q7} are indistinguishable → merged into M2={q3,q7}.

| State | P | A | E | L | X |
|---|---|---|---|---|---|
| **M0** | M1 | MT | M2 | MT | M4 |
| M1 | M2 | M2 | MT | M3 | MT |
| M2 | M2 | MT | MT | M3 | MT |
| **M3** ✓ | M3 | M3 | MT | MT | MT |
| M4 | M2 | MT | MT | MT | MT |
| MT | MT | MT | MT | MT | MT |

Reduction: **7 → 6 states** (14% reduction).

## JFLAP Files

| File | Description |
|---|---|
| `jflap/cyber_breach_nfa.jff` | NFA (8 states, ε-transitions) |
| `jflap/cyber_breach_dfa.jff` | DFA (7 states, subset construction) |
| `jflap/cyber_breach_min_dfa.jff` | Minimized DFA (6 states) |

Open each in JFLAP 7.1. Use `Test → Run Multiple Inputs` to verify test strings.

## Missions

| Mission | Solve with | Concept demonstrated |
|---|---|---|
| 1 | P → A → L | Direct path through firewall |
| 2 | E → L | ε-tunnel (proxy bypass) |
| 3 | X → P → L | Proxy bounce through redundant path |
| 4 | E → L | Stealth: avoid Ping-based IDS |
| 5 | P → A → L → A | Full chain + hold connection |

## File Map

```
cyber_breach/
├── automaton.py          NFA, DFA, minimization algorithms
├── main.py               pygame GUI entry point
├── missions.py           Mission definitions
├── README.md             This file
├── jflap/
│   ├── cyber_breach_nfa.jff
│   ├── cyber_breach_dfa.jff
│   └── cyber_breach_min_dfa.jff
└── tests/
    └── test_automaton.py 98 automated tests
```
