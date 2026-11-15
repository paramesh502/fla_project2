"""
missions.py — Mission definitions for Cyber Breach.

Each mission specifies:
  - name, description
  - the automaton to use (all use the same NFA/DFA engine)
  - the packet sequences the player must craft to reach the accept state
  - an unlock sequence (the correct answer)
  - a set of decoy/invalid sequences for the puzzle
"""

MISSIONS = [
    {
        "id": 1,
        "name": "Mission 1: Layer 1 Breach",
        "description": (
            "The firewall expects a simple authenticated packet burst.\n"
            "Send Ping → Auth → Payload to breach Layer 1."
        ),
        "hint": "Try P → A → L",
        "accept_sequences": [["P", "A", "L"], ["P", "L"]],
        "reject_samples":   [["A"], ["L"], ["P", "P", "A", "L"]],
        "solution":         ["P", "A", "L"],
    },
    {
        "id": 2,
        "name": "Mission 2: Epsilon Tunnel",
        "description": (
            "Use the proxy ε-tunnel to skip Layer 1 entirely.\n"
            "Send Encrypt → Payload using the silent proxy move."
        ),
        "hint": "Try E → L  (the ε-tunnel auto-routes you through Layer 2)",
        "accept_sequences": [["E", "L"]],
        "reject_samples":   [["E"], ["E", "A"], ["L"]],
        "solution":         ["E", "L"],
    },
    {
        "id": 3,
        "name": "Mission 3: Proxy Bounce",
        "description": (
            "Bounce through the Proxy node to confuse the firewall.\n"
            "X → P → L routes you back through Layer 2 then breaches."
        ),
        "hint": "Try X → P → L",
        "accept_sequences": [["X", "P", "L"]],
        "reject_samples":   [["X"], ["X", "L"], ["X", "A", "L"]],
        "solution":         ["X", "P", "L"],
    },
    {
        "id": 4,
        "name": "Mission 4: Stealth Payload",
        "description": (
            "Stay low: use Encrypt to enter then drop the Payload.\n"
            "Avoid Pings — the IDS watches for repeated Ping packets."
        ),
        "hint": "Try E → L",
        "accept_sequences": [["E", "L"], ["P", "L"]],
        "reject_samples":   [["P", "P", "A", "L"], ["P", "E", "L"]],
        "solution":         ["E", "L"],
    },
    {
        "id": 5,
        "name": "Mission 5: Full Chain Infiltration",
        "description": (
            "Full infiltration: Ping → Auth → Payload → Auth.\n"
            "Reach the server AND authenticate again to hold the connection."
        ),
        "hint": "Try P → A → L → A",
        "accept_sequences": [["P", "A", "L", "A"], ["P", "A", "L", "P"]],
        "reject_samples":   [["P", "A", "L", "E"], ["P", "A", "L", "X"]],
        "solution":         ["P", "A", "L", "A"],
    },
]
