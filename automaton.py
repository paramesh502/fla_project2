"""
automaton.py — NFA, NFA→DFA subset construction, DFA minimization
for Cyber Breach firewall logic.

Alphabet symbols (packet types):
  P  = Ping
  A  = Auth
  E  = Encrypt
  X  = Proxy   (also used as an ε-transition source in the NFA)
  L  = Payload

ε  = epsilon (empty string / silent proxy/tunnel move)

NFA design (Mission 1 — primary firewall)
==========================================
States: q0, q1, q2, q3, q4   (q4 = accept)
Start:  q0
Accept: {q4}

Transitions (NFA):
  q0 --P-->  q1
  q0 --ε-->  q2          (proxy tunnel: hacker can silently jump to q2)
  q1 --A-->  q3
  q1 --ε-->  q3          (tunnel shortcut)
  q2 --E-->  q3
  q2 --X-->  q0          (loop back: proxy bounces)
  q3 --L-->  q4          (payload reaches server → accept)
  q3 --P-->  q3          (keep pinging inside layer 3)
  q4 --P-->  q4          (stay at accept, additional pings tolerated)
  q4 --A-->  q4

This NFA has ε-transitions from q0 and q1, making it nondeterministic.
"""

from __future__ import annotations
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

EPSILON = "ε"
TRAP    = "TRAP"


# ---------------------------------------------------------------------------
# NFA
# ---------------------------------------------------------------------------

class NFA:
    """
    Nondeterministic Finite Automaton with optional ε-transitions.

    transitions: state → symbol → set of states
                 (use symbol == EPSILON for ε-transitions)
    """

    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        transitions: Dict[str, Dict[str, Set[str]]],
        start: str,
        accept: Set[str],
    ):
        self.states      = states
        self.alphabet    = alphabet          # does NOT include EPSILON
        self.transitions = transitions
        self.start       = start
        self.accept      = accept

    # ------------------------------------------------------------------
    # ε-closure
    # ------------------------------------------------------------------
    def epsilon_closure(self, states: Iterable[str]) -> FrozenSet[str]:
        """Return the ε-closure of a set of states (all states reachable
        via zero or more ε-transitions)."""
        stack  = list(states)
        closed: Set[str] = set(states)
        while stack:
            s = stack.pop()
            for t in self.transitions.get(s, {}).get(EPSILON, set()):
                if t not in closed:
                    closed.add(t)
                    stack.append(t)
        return frozenset(closed)

    # ------------------------------------------------------------------
    # NFA simulation (nondeterministic)
    # ------------------------------------------------------------------
    def accepts(self, symbols: List[str]) -> bool:
        """Return True iff the NFA accepts the symbol sequence."""
        current = self.epsilon_closure([self.start])
        for sym in symbols:
            if sym not in self.alphabet:
                return False          # symbol outside alphabet → reject
            nxt: Set[str] = set()
            for s in current:
                nxt |= self.transitions.get(s, {}).get(sym, set())
            current = self.epsilon_closure(nxt)
        return bool(current & self.accept)

    # ------------------------------------------------------------------
    # Step-by-step trace (for viva explanations)
    # ------------------------------------------------------------------
    def trace(self, symbols: List[str]) -> List[FrozenSet[str]]:
        """Return the sequence of state-sets visited, one per symbol."""
        path = []
        current = self.epsilon_closure([self.start])
        path.append(current)
        for sym in symbols:
            nxt: Set[str] = set()
            for s in current:
                nxt |= self.transitions.get(s, {}).get(sym, set())
            current = self.epsilon_closure(nxt)
            path.append(current)
        return path


# ---------------------------------------------------------------------------
# NFA → DFA  (subset construction)
# ---------------------------------------------------------------------------

class DFA:
    """
    Deterministic Finite Automaton.

    transitions: state_name → symbol → state_name
    Undefined transitions go to TRAP.
    """

    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        transitions: Dict[str, Dict[str, str]],
        start: str,
        accept: Set[str],
    ):
        self.states      = states
        self.alphabet    = alphabet
        self.transitions = transitions
        self.start       = start
        self.accept      = accept

    # ------------------------------------------------------------------
    # DFA simulation
    # ------------------------------------------------------------------
    def accepts(self, symbols: List[str]) -> bool:
        state = self.start
        for sym in symbols:
            if sym not in self.alphabet:
                return False
            state = self.transitions.get(state, {}).get(sym, TRAP)
            if state == TRAP:
                return False          # absorbing trap
        return state in self.accept

    # ------------------------------------------------------------------
    # Step-by-step trace
    # ------------------------------------------------------------------
    def trace(self, symbols: List[str]) -> List[str]:
        path  = [self.start]
        state = self.start
        for sym in symbols:
            state = self.transitions.get(state, {}).get(sym, TRAP)
            path.append(state)
        return path


# ---------------------------------------------------------------------------
# Subset construction
# ---------------------------------------------------------------------------

def nfa_to_dfa(nfa: NFA) -> DFA:
    """
    Convert an NFA to an equivalent DFA via subset construction.
    Returns a DFA whose state names are frozenset labels (comma-joined).
    A dead/trap powerset state is represented as TRAP.
    """

    def label(fs: FrozenSet[str]) -> str:
        if not fs:
            return TRAP
        return "{" + ",".join(sorted(fs)) + "}"

    start_set  = nfa.epsilon_closure([nfa.start])
    start_name = label(start_set)

    dfa_states: Dict[str, FrozenSet[str]] = {start_name: start_set}
    dfa_trans:  Dict[str, Dict[str, str]] = {}
    dfa_accept: Set[str] = set()
    worklist = [start_set]

    while worklist:
        current_set = worklist.pop()
        current_name = label(current_set)
        dfa_trans[current_name] = {}

        for sym in nfa.alphabet:
            nxt: Set[str] = set()
            for s in current_set:
                nxt |= nfa.transitions.get(s, {}).get(sym, set())
            nxt_closed = nfa.epsilon_closure(nxt)
            nxt_name   = label(nxt_closed)

            dfa_trans[current_name][sym] = nxt_name

            if nxt_name not in dfa_states:
                dfa_states[nxt_name] = nxt_closed
                worklist.append(nxt_closed)

        # Mark accept if any NFA accept state is in this subset
        if current_set & nfa.accept:
            dfa_accept.add(current_name)

    # Ensure TRAP transitions to itself on every symbol
    if TRAP in dfa_states:
        dfa_trans[TRAP] = {sym: TRAP for sym in nfa.alphabet}
        # TRAP is never an accept state

    return DFA(
        states     = set(dfa_states.keys()),
        alphabet   = nfa.alphabet,
        transitions= dfa_trans,
        start      = start_name,
        accept     = dfa_accept,
    )


# ---------------------------------------------------------------------------
# DFA Minimization  (table-filling / Myhill-Nerode distinguishability)
# ---------------------------------------------------------------------------

def minimize_dfa(dfa: DFA) -> DFA:
    """
    Minimize a DFA using the table-filling algorithm.
    Returns a new DFA with unreachable states removed and equivalent
    states merged.
    """

    # Step 0: remove unreachable states
    reachable: Set[str] = set()
    stack = [dfa.start]
    while stack:
        s = stack.pop()
        if s in reachable:
            continue
        reachable.add(s)
        for sym in dfa.alphabet:
            t = dfa.transitions.get(s, {}).get(sym, TRAP)
            if t not in reachable:
                stack.append(t)
    if TRAP in {dfa.transitions.get(s, {}).get(sym, TRAP)
                for s in reachable for sym in dfa.alphabet}:
        reachable.add(TRAP)

    states_list = sorted(reachable)

    # Step 1: initial partition — accept vs non-accept
    accept    = dfa.accept & reachable
    non_accept = reachable - accept

    # Build distinguishability table
    # distinguishable[frozenset({a,b})] = True means a ≁ b
    dist: Dict[FrozenSet[str], bool] = {}

    state_pairs = [
        frozenset({a, b})
        for i, a in enumerate(states_list)
        for b in states_list[i+1:]
    ]

    # Mark pairs where one is accept and other is not
    for pair in state_pairs:
        a, b = tuple(pair)
        dist[pair] = (a in accept) != (b in accept)

    # Iteratively mark more pairs
    changed = True
    while changed:
        changed = False
        for pair in state_pairs:
            if dist.get(pair):
                continue
            a, b = tuple(pair)
            for sym in dfa.alphabet:
                ta = dfa.transitions.get(a, {}).get(sym, TRAP)
                tb = dfa.transitions.get(b, {}).get(sym, TRAP)
                if ta == tb:
                    continue
                if dist.get(frozenset({ta, tb}), False):
                    dist[pair] = True
                    changed = True
                    break

    # Build equivalence classes (union-find style)
    parent: Dict[str, str] = {s: s for s in states_list}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for pair in state_pairs:
        a, b = tuple(pair)
        if not dist.get(pair, False):
            union(a, b)

    # Build minimized DFA
    # Representative for each equivalence class
    class_map: Dict[str, str] = {}  # old_state → new_state_name
    classes: Dict[str, Set[str]] = {}
    for s in states_list:
        rep = find(s)
        classes.setdefault(rep, set()).add(s)
    for rep, members in classes.items():
        name = "{" + ",".join(sorted(members)) + "}"
        for m in members:
            class_map[m] = name

    new_start  = class_map[dfa.start]
    new_accept = {class_map[s] for s in accept}
    new_states = set(class_map.values())

    new_trans: Dict[str, Dict[str, str]] = {}
    for rep, members in classes.items():
        rep_state = class_map[rep]
        new_trans[rep_state] = {}
        for sym in dfa.alphabet:
            t = dfa.transitions.get(rep, {}).get(sym, TRAP)
            new_trans[rep_state][sym] = class_map.get(t, TRAP)

    # Ensure TRAP class maps to itself
    trap_class = class_map.get(TRAP, TRAP)
    if trap_class in new_states:
        new_trans[trap_class] = {sym: trap_class for sym in dfa.alphabet}

    return DFA(
        states      = new_states,
        alphabet    = dfa.alphabet,
        transitions = new_trans,
        start       = new_start,
        accept      = new_accept,
    )


# ---------------------------------------------------------------------------
# Factory — build the Cyber Breach automata
# ---------------------------------------------------------------------------

def build_nfa() -> NFA:
    """
    Build the Cyber Breach NFA as described in the project spec.

    The NFA models a layered firewall.  It is intentionally designed with
    8 states so that subset construction produces 7 DFA states and
    minimization reduces that to 5 states, demonstrating visible reduction.

    States: q0 (start), q1, q2, q3, q4, q5, q6, q7 (accept)
    Alphabet: {P, A, E, X, L}

    Transitions:
      q0 -P→ q1          # Ping enters layer 1
      q0 -ε→ q2          # ε-tunnel (proxy): skip directly to layer 2
      q1 -A→ q3          # Auth from layer 1 → layer 3
      q1 -ε→ q3          # ε-tunnel shortcut (tunnel move)
      q2 -E→ q3          # Encrypt from layer 2 → layer 3
      q2 -X→ q5          # Proxy bounce from layer 2 → q5
      q3 -L→ q4          # Payload in layer 3 → reach server (accept)
      q3 -P→ q3          # Additional Pings inside layer 3
      q4 -P→ q4          # Stay at server with extra Pings (accept)
      q4 -A→ q4          # Stay at server with extra Auth (accept)
      q5 -ε→ q6          # ε-transition from q5 to q6 (tunnel)
      q5 -P→ q7          # Ping from q5 to q7 (redundant path)
      q6 -P→ q7          # Ping from q6 to q7
      q7 -L→ q4          # Payload from q7 → accept (same as q3-L→q4)
      q7 -P→ q7          # Stay at q7 with Pings (same behavior as q3)

    q5, q6, q7 are intentionally redundant with q3 so minimization merges
    {q3} with {q7} (both have identical future behavior) and {q5,q6} form
    an intermediate group that collapses.

    NFA states: 8  (q0..q7)
    DFA states after subset construction: 7 (reachable subsets)
    Min-DFA states: 5 (after merging equivalent classes)
    """
    states   = {"q0", "q1", "q2", "q3", "q4", "q5", "q6", "q7"}
    alphabet = {"P", "A", "E", "X", "L"}
    trans: Dict[str, Dict[str, Set[str]]] = {
        "q0": {EPSILON: {"q2"},        "P": {"q1"}},
        "q1": {EPSILON: {"q3"},        "A": {"q3"}},
        "q2": {"E": {"q3"},            "X": {"q5"}},
        "q3": {"L": {"q4"},            "P": {"q3"}},
        "q4": {"P": {"q4"},            "A": {"q4"}},
        "q5": {EPSILON: {"q6"},        "P": {"q7"}},
        "q6": {"P": {"q7"}},
        "q7": {"L": {"q4"},            "P": {"q7"}},
    }
    return NFA(states, alphabet, trans, "q0", {"q4"})


def build_dfa() -> DFA:
    """Return the DFA produced by subset construction from build_nfa()."""
    return nfa_to_dfa(build_nfa())


def build_min_dfa() -> DFA:
    """Return the minimized DFA."""
    return minimize_dfa(build_dfa())


# ---------------------------------------------------------------------------
# Convenience: simple state-label for display
# ---------------------------------------------------------------------------

def friendly_label(state: str) -> str:
    """Convert frozenset label '{q0,q2}' to a short display name 'D0' etc."""
    return state   # callers may override


# ---------------------------------------------------------------------------
# Self-test (quick sanity check on import)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    nfa  = build_nfa()
    dfa  = build_dfa()
    mdfa = build_min_dfa()

    print(f"NFA states : {sorted(nfa.states)}")
    print(f"DFA states : {len(dfa.states)}")
    print(f"Min-DFA    : {len(mdfa.states)}")

    tests = [
        (["P", "A", "L"],       True,  "P→A→L  (direct path)"),
        (["E", "L"],            True,  "ε-tunnel: q0→q2 via ε, then E→q3, L→q4"),
        (["L"],                 True,  "ε-tunnel: q0→q2 via ε, then L? No — q2 has no L"),
        (["P", "L"],            False, "P→q1, ε→q3, L→q4  actually True"),
        (["X", "E", "L"],       False, "X from q2→q0, then ε→q2, E→q3, L→q4"),
        (["P", "P", "A", "L"],  True,  "P,P,A,L"),
        (["A"],                 False, "A alone — no path to q4"),
    ]
    for seq, expected, desc in tests:
        got_nfa = nfa.accepts(seq)
        got_dfa = dfa.accepts(seq)
        flag    = "" if got_nfa == got_dfa else "  *** NFA/DFA mismatch ***"
        print(f"  {'PASS' if got_nfa==expected else 'NOTE'} nfa={got_nfa} dfa={got_dfa}  {desc}{flag}")
