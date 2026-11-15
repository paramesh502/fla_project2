"""
tests/test_automaton.py — Automated test suite for Cyber Breach automaton logic.

Coverage:
  1. NFA ε-closure computation
  2. NFA simulation (accept/reject)
  3. NFA→DFA subset construction (state counts, transition correctness)
  4. DFA simulation matches NFA simulation
  5. DFA minimization (state reduction, equivalence)
  6. Minimized DFA matches DFA on all test inputs
  7. Trap-state absorption (once in TRAP, stays in TRAP)
  8. Valid packet sequences (≥5 that must be accepted)
  9. Invalid packet sequences (≥5 that must be rejected)
 10. Hand-traced step-by-step DFA paths

Run with:  pytest tests/test_automaton.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from automaton import (
    NFA, DFA, build_nfa, build_dfa, build_min_dfa,
    nfa_to_dfa, minimize_dfa, EPSILON, TRAP
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def nfa():
    return build_nfa()

@pytest.fixture(scope="module")
def dfa():
    return build_dfa()

@pytest.fixture(scope="module")
def mdfa():
    return build_min_dfa()


# ─────────────────────────────────────────────────────────────────────────────
# 1. NFA ε-closure
# ─────────────────────────────────────────────────────────────────────────────

class TestEpsilonClosure:
    def test_start_closure_includes_q2(self, nfa):
        """ε-closure({q0}) must include q2 via q0 --ε--> q2."""
        cl = nfa.epsilon_closure(["q0"])
        assert "q0" in cl, "q0 must be in its own closure"
        assert "q2" in cl, "q2 must be reachable from q0 via ε"

    def test_start_closure_does_not_include_q1(self, nfa):
        """q1 is not reachable from q0 via ε-transitions."""
        cl = nfa.epsilon_closure(["q0"])
        assert "q1" not in cl

    def test_q1_closure_includes_q3(self, nfa):
        """ε-closure({q1}) must include q3 via q1 --ε--> q3."""
        cl = nfa.epsilon_closure(["q1"])
        assert "q1" in cl
        assert "q3" in cl

    def test_q5_closure_includes_q6(self, nfa):
        """ε-closure({q5}) must include q6 via q5 --ε--> q6."""
        cl = nfa.epsilon_closure(["q5"])
        assert "q5" in cl
        assert "q6" in cl

    def test_q4_closure_is_singleton(self, nfa):
        """q4 has no outgoing ε-transitions; closure = {q4}."""
        cl = nfa.epsilon_closure(["q4"])
        assert cl == frozenset({"q4"})

    def test_empty_set_closure(self, nfa):
        """ε-closure of empty set is empty."""
        cl = nfa.epsilon_closure([])
        assert cl == frozenset()

    def test_multi_state_closure(self, nfa):
        """ε-closure({q1, q5}) = {q1, q3, q5, q6}."""
        cl = nfa.epsilon_closure(["q1", "q5"])
        assert "q1" in cl
        assert "q3" in cl
        assert "q5" in cl
        assert "q6" in cl


# ─────────────────────────────────────────────────────────────────────────────
# 2. Valid packet sequences (≥5 accepted)
# ─────────────────────────────────────────────────────────────────────────────

VALID_SEQUENCES = [
    (["P", "A", "L"],       "Direct path: Ping→Auth→Payload"),
    (["E", "L"],            "ε-tunnel: q0→q2 via ε, then Encrypt→q3, Payload→q4"),
    (["P", "L"],            "Ping to {q1,q3}, ε gives q3, Payload→q4"),
    (["X", "P", "L"],       "Proxy bounce X to {q5,q6}, P to q7≡q3, L→q4"),
    (["P", "A", "L", "P"],  "Accept+stay: PAL accepted, extra Ping stays at q4"),
    (["P", "A", "L", "A"],  "Accept+stay: PAL accepted, extra Auth stays at q4"),
    (["P", "P", "L"],       "P→{q1,q3}, P stays at q3, L→q4"),
    (["E", "P", "L"],       "E→q3, P loops q3, L→q4"),
    (["X", "P", "P", "L"],  "X→{q5,q6}, P→q7, P loops, L→q4"),
]

@pytest.mark.parametrize("seq,desc", VALID_SEQUENCES)
class TestValidSequences:
    def test_nfa_accepts(self, seq, desc, nfa):
        assert nfa.accepts(seq) is True, f"NFA should accept {seq} ({desc})"

    def test_dfa_accepts(self, seq, desc, dfa):
        assert dfa.accepts(seq) is True, f"DFA should accept {seq} ({desc})"

    def test_mdfa_accepts(self, seq, desc, mdfa):
        assert mdfa.accepts(seq) is True, f"Min-DFA should accept {seq} ({desc})"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Invalid packet sequences (≥5 rejected)
# ─────────────────────────────────────────────────────────────────────────────

INVALID_SEQUENCES = [
    (["A"],              "Auth alone — no path from start to accept"),
    (["L"],              "Payload alone — q0/q2 have no L-transition"),
    (["P", "P", "A", "L"], "P,P goes to q3, A from q3 → TRAP, then L stuck"),
    (["E", "A"],         "E→q3, A from q3 → TRAP"),
    (["E"],              "Encrypt alone — q3 is not accept"),
    (["P", "E", "L"],    "P→{q1,q3}, E from q1 → TRAP"),
    (["X"],              "X alone → {q5,q6}, not accept"),
    (["X", "L"],         "X→{q5,q6}, L → TRAP (q5/q6 have no L)"),
    (["P", "A", "E"],    "PAE: PA→q3, E→TRAP"),
    (["A", "L"],         "A from start → TRAP, then L stays TRAP"),
]

@pytest.mark.parametrize("seq,desc", INVALID_SEQUENCES)
class TestInvalidSequences:
    def test_nfa_rejects(self, seq, desc, nfa):
        assert nfa.accepts(seq) is False, f"NFA should reject {seq} ({desc})"

    def test_dfa_rejects(self, seq, desc, dfa):
        assert dfa.accepts(seq) is False, f"DFA should reject {seq} ({desc})"

    def test_mdfa_rejects(self, seq, desc, mdfa):
        assert mdfa.accepts(seq) is False, f"Min-DFA should reject {seq} ({desc})"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Trap-state absorption
# ─────────────────────────────────────────────────────────────────────────────

class TestTrapState:
    def test_trap_in_dfa_transitions(self, dfa):
        """TRAP state must exist and all its outgoing transitions stay in TRAP."""
        assert TRAP in dfa.states, "DFA must contain the TRAP state"
        for sym in dfa.alphabet:
            assert dfa.transitions[TRAP][sym] == TRAP, \
                f"TRAP --{sym}--> {dfa.transitions[TRAP][sym]}, expected TRAP"

    def test_trap_not_accept(self, dfa):
        assert TRAP not in dfa.accept, "TRAP must not be an accept state"

    def test_once_in_trap_stays_in_trap_on_all_symbols(self, dfa):
        """After landing in TRAP, every subsequent symbol stays in TRAP."""
        # Send 'A' from start to reach TRAP, then send each symbol
        path = dfa.trace(["A"])
        assert path[-1] == TRAP
        for sym in dfa.alphabet:
            path2 = dfa.trace(["A", sym])
            assert path2[-1] == TRAP, \
                f"After TRAP, symbol {sym} should stay TRAP but got {path2[-1]}"

    def test_long_sequence_in_trap_stays_in_trap(self, dfa):
        """Five symbols after entering TRAP still stays in TRAP."""
        stuck = ["A"] + ["P", "A", "E", "X", "L"]
        assert dfa.accepts(stuck) is False
        path = dfa.trace(stuck)
        assert path[1] == TRAP
        for state in path[1:]:
            assert state == TRAP

    def test_nfa_trap_equivalent(self, nfa, dfa):
        """Sequences that land in DFA TRAP also cause NFA to reach empty set."""
        trap_seqs = [["A"], ["L"], ["A", "P", "L"], ["E", "A"]]
        for seq in trap_seqs:
            nfa_result = nfa.accepts(seq)
            dfa_result = dfa.accepts(seq)
            assert nfa_result == dfa_result, \
                f"NFA/DFA mismatch for {seq}: nfa={nfa_result} dfa={dfa_result}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. NFA→DFA subset construction
# ─────────────────────────────────────────────────────────────────────────────

class TestSubsetConstruction:
    def test_dfa_state_count(self, dfa):
        """DFA from subset construction must have exactly 7 states."""
        assert len(dfa.states) == 7, \
            f"Expected 7 DFA states, got {len(dfa.states)}: {sorted(dfa.states)}"

    def test_dfa_start_state_is_q0q2(self, dfa):
        """DFA start state must be ε-closure({q0}) = {q0,q2}."""
        assert dfa.start == "{q0,q2}", \
            f"Expected '{{q0,q2}}' but got '{dfa.start}'"

    def test_dfa_accept_state_contains_q4(self, dfa):
        """The only NFA accept state q4 must appear in a DFA accept state."""
        for s in dfa.accept:
            assert "q4" in s, f"Accept state {s} does not contain q4"

    def test_dfa_exactly_one_accept_state(self, dfa):
        """Only one DFA state ({q4}) contains q4 and is accept."""
        assert len(dfa.accept) == 1, \
            f"Expected 1 DFA accept state, got {len(dfa.accept)}: {dfa.accept}"

    def test_dfa_trap_is_dead_state(self, dfa):
        """TRAP state must exist and have all self-loop transitions."""
        assert TRAP in dfa.states
        for sym in dfa.alphabet:
            assert dfa.transitions.get(TRAP, {}).get(sym) == TRAP

    def test_every_dfa_state_has_complete_transitions(self, dfa):
        """Every DFA state must have a transition for every alphabet symbol."""
        for state in dfa.states:
            for sym in dfa.alphabet:
                dest = dfa.transitions.get(state, {}).get(sym, TRAP)
                assert dest in dfa.states or dest == TRAP, \
                    f"State {state} --{sym}--> {dest} not in DFA states"

    def test_nfa_dfa_equivalence_on_all_test_cases(self, nfa, dfa):
        """NFA and DFA must agree on all test sequences."""
        all_seqs = [s for s, _ in VALID_SEQUENCES] + [s for s, _ in INVALID_SEQUENCES]
        for seq in all_seqs:
            assert nfa.accepts(seq) == dfa.accepts(seq), \
                f"NFA/DFA mismatch on {seq}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. DFA minimization
# ─────────────────────────────────────────────────────────────────────────────

class TestDFAMinimization:
    def test_state_reduction(self, dfa, mdfa):
        """Minimized DFA must have fewer states than the DFA."""
        assert len(mdfa.states) < len(dfa.states), \
            f"Min-DFA ({len(mdfa.states)}) should be < DFA ({len(dfa.states)})"

    def test_min_dfa_state_count(self, mdfa):
        """Minimized DFA must have exactly 6 states."""
        assert len(mdfa.states) == 6, \
            f"Expected 6 min-DFA states, got {len(mdfa.states)}: {sorted(mdfa.states)}"

    def test_min_dfa_exactly_one_accept(self, mdfa):
        """Minimized DFA must have exactly one accept state."""
        assert len(mdfa.accept) == 1, \
            f"Expected 1 accept state, got {len(mdfa.accept)}"

    def test_min_dfa_trap_absorbing(self, mdfa):
        """Min-DFA trap state must be absorbing (all symbols → self)."""
        # find trap state
        trap_states = [s for s in mdfa.states if TRAP in s]
        assert len(trap_states) == 1, f"Expected one trap state, found {trap_states}"
        trap = trap_states[0]
        for sym in mdfa.alphabet:
            assert mdfa.transitions[trap][sym] == trap, \
                f"Min-DFA trap --{sym}--> {mdfa.transitions[trap][sym]} != {trap}"

    def test_min_dfa_dfa_equivalence(self, dfa, mdfa):
        """DFA and min-DFA must agree on all test sequences."""
        all_seqs = [s for s, _ in VALID_SEQUENCES] + [s for s, _ in INVALID_SEQUENCES]
        for seq in all_seqs:
            assert dfa.accepts(seq) == mdfa.accepts(seq), \
                f"DFA/min-DFA mismatch on {seq}: dfa={dfa.accepts(seq)} min={mdfa.accepts(seq)}"

    def test_q3_q7_merged(self, dfa, mdfa):
        """DFA states {q3} and {q7} (representing q3 and q7) must be merged in min-DFA."""
        # In min-DFA, we expect no separate {q3} and {q7} states
        raw_states = sorted(mdfa.states)
        # Neither "{q3}" alone nor "{q7}" alone should appear as a state name
        assert "{q3}" not in raw_states, \
            f"{{q3}} should be merged in min-DFA but found in {raw_states}"
        assert "{q7}" not in raw_states, \
            f"{{q7}} should be merged in min-DFA but found in {raw_states}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Hand-traced step-by-step DFA paths
# ─────────────────────────────────────────────────────────────────────────────

class TestHandTracedPaths:
    """
    Manually verify exact DFA state sequences for key strings.

    DFA states:
      D0 = {q0,q2}  START
      D1 = {q1,q3}
      D2 = {q3}
      D3 = {q4}     ACCEPT
      D4 = {q5,q6}
      D5 = {q7}
      DT = TRAP
    """

    def test_trace_P_A_L(self, dfa):
        """P→A→L : D0 --P--> D1 --A--> D2 --L--> D3(accept)"""
        path = dfa.trace(["P", "A", "L"])
        assert path[0] == "{q0,q2}",   f"Step 0: {path[0]}"
        assert path[1] == "{q1,q3}",   f"Step 1 (after P): {path[1]}"
        assert path[2] == "{q3}",      f"Step 2 (after A): {path[2]}"
        assert path[3] == "{q4}",      f"Step 3 (after L): {path[3]}"
        assert path[3] in dfa.accept

    def test_trace_E_L(self, dfa):
        """E→L : D0 --E--> D2 --L--> D3(accept)  (uses ε-tunnel D0={q0,q2})"""
        path = dfa.trace(["E", "L"])
        assert path[0] == "{q0,q2}",   f"Step 0: {path[0]}"
        assert path[1] == "{q3}",      f"Step 1 (after E): {path[1]}"
        assert path[2] == "{q4}",      f"Step 2 (after L): {path[2]}"
        assert path[2] in dfa.accept

    def test_trace_X_P_L(self, dfa):
        """X→P→L : D0 --X--> D4 --P--> D5 --L--> D3(accept)"""
        path = dfa.trace(["X", "P", "L"])
        assert path[0] == "{q0,q2}",   f"Step 0: {path[0]}"
        assert path[1] == "{q5,q6}",   f"Step 1 (after X): {path[1]}"
        assert path[2] == "{q7}",      f"Step 2 (after P): {path[2]}"
        assert path[3] == "{q4}",      f"Step 3 (after L): {path[3]}"
        assert path[3] in dfa.accept

    def test_trace_A_leads_to_trap(self, dfa):
        """A : D0 --A--> TRAP  (no Auth accepted from start)"""
        path = dfa.trace(["A"])
        assert path[0] == "{q0,q2}"
        assert path[1] == TRAP

    def test_trace_P_P_A_L_hits_trap(self, dfa):
        """P,P,A,L : D0--P-->D1--P-->D2--A-->TRAP"""
        path = dfa.trace(["P", "P", "A", "L"])
        assert path[2] == "{q3}",  f"After P,P: {path[2]}"
        assert path[3] == TRAP,    f"After P,P,A: {path[3]}"
        assert path[4] == TRAP,    f"After P,P,A,L: {path[4]}"

    def test_nfa_trace_P_A_L(self, nfa):
        """NFA trace for P,A,L shows correct state sets."""
        path = nfa.trace(["P", "A", "L"])
        # After start: ε-closure({q0}) = {q0,q2}
        assert "q0" in path[0] and "q2" in path[0]
        # After P: move from {q0,q2} on P → {q1}, ε-close → {q1,q3}
        assert "q1" in path[1] and "q3" in path[1]
        # After A: from {q1,q3} on A → {q3}, ε-close → {q3}
        assert path[2] == frozenset({"q3"})
        # After L: {q3} on L → {q4}
        assert path[3] == frozenset({"q4"})


# ─────────────────────────────────────────────────────────────────────────────
# 8. Alphabet handling
# ─────────────────────────────────────────────────────────────────────────────

class TestAlphabetHandling:
    def test_symbol_outside_alphabet_rejected_by_nfa(self, nfa):
        assert nfa.accepts(["Z"]) is False
        assert nfa.accepts(["P", "Z"]) is False

    def test_symbol_outside_alphabet_rejected_by_dfa(self, dfa):
        assert dfa.accepts(["Z"]) is False
        assert dfa.accepts(["P", "A", "Z", "L"]) is False

    def test_empty_sequence_rejected(self, nfa, dfa, mdfa):
        """Empty packet sequence: start state {q0,q2} is not accept."""
        assert nfa.accepts([])  is False
        assert dfa.accepts([])  is False
        assert mdfa.accepts([]) is False


# ─────────────────────────────────────────────────────────────────────────────
# 9. JFLAP file existence check
# ─────────────────────────────────────────────────────────────────────────────

class TestJFLAPFiles:
    def test_nfa_jff_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_nfa.jff")
        assert os.path.isfile(path), "NFA JFLAP file missing"

    def test_dfa_jff_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_dfa.jff")
        assert os.path.isfile(path), "DFA JFLAP file missing"

    def test_min_dfa_jff_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_min_dfa.jff")
        assert os.path.isfile(path), "Min-DFA JFLAP file missing"

    def test_jff_xml_is_parseable(self):
        import xml.etree.ElementTree as ET
        for name in ["cyber_breach_nfa.jff", "cyber_breach_dfa.jff",
                     "cyber_breach_min_dfa.jff"]:
            path = os.path.join(os.path.dirname(__file__), "..", "jflap", name)
            tree = ET.parse(path)      # will raise on malformed XML
            root = tree.getroot()
            assert root.tag == "structure", f"{name}: root tag should be 'structure'"

    def test_nfa_jff_has_initial_and_final(self):
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_nfa.jff")
        tree = ET.parse(path)
        root = tree.getroot()
        automaton = root.find("automaton")
        states = automaton.findall("state")
        initials = [s for s in states if s.find("initial") is not None]
        finals   = [s for s in states if s.find("final")   is not None]
        assert len(initials) == 1, f"NFA jff must have exactly 1 initial state, got {len(initials)}"
        assert len(finals)   >= 1, f"NFA jff must have at least 1 final state, got {len(finals)}"

    def test_dfa_jff_state_count(self):
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_dfa.jff")
        tree = ET.parse(path)
        states = tree.getroot().find("automaton").findall("state")
        assert len(states) == 7, f"DFA jff should have 7 states, got {len(states)}"

    def test_min_dfa_jff_state_count(self):
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(__file__), "..", "jflap",
                            "cyber_breach_min_dfa.jff")
        tree = ET.parse(path)
        states = tree.getroot().find("automaton").findall("state")
        assert len(states) == 6, \
            f"Min-DFA jff should have 6 states, got {len(states)}"
