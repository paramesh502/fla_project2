#!/usr/bin/env python3
"""
server.py — Cyber Breach browser UI backend.
Python standard library only. Run with: python3 server.py
Then open http://localhost:8080 in any browser.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Add the project directory to path so we can import automaton and missions
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from automaton import build_nfa, build_dfa, build_min_dfa, TRAP
from missions import MISSIONS

# Build automata once at startup
_nfa = build_nfa()
_dfa = build_dfa()
_min_dfa = build_min_dfa()


def _serialize_nfa(nfa):
    trans = {}
    for state, sym_map in nfa.transitions.items():
        trans[state] = {sym: sorted(targets) for sym, targets in sym_map.items()}
    return {
        "states": sorted(nfa.states),
        "alphabet": sorted(nfa.alphabet),
        "transitions": trans,
        "start": nfa.start,
        "accept": sorted(nfa.accept),
    }


def _serialize_dfa(dfa, label_prefix=""):
    return {
        "states": sorted(dfa.states),
        "alphabet": sorted(dfa.alphabet),
        "transitions": {s: dict(t) for s, t in dfa.transitions.items()},
        "start": dfa.start,
        "accept": sorted(dfa.accept),
        "trap": TRAP,
    }


def _get_automaton_data():
    dfa_data = _serialize_dfa(_dfa)
    min_dfa_data = _serialize_dfa(_min_dfa)

    # Identify trap states
    def find_trap(dfa):
        for s in dfa.states:
            if s not in dfa.accept:
                is_trap = True
                for sym in dfa.alphabet:
                    if dfa.transitions.get(s, {}).get(sym, TRAP) != s:
                        is_trap = False
                        break
                if is_trap:
                    return s
        return TRAP

    dfa_trap = find_trap(_dfa)
    min_dfa_trap = find_trap(_min_dfa)

    dfa_data["trap_state"] = dfa_trap
    min_dfa_data["trap_state"] = min_dfa_trap

    return {
        "nfa": _serialize_nfa(_nfa),
        "dfa": dfa_data,
        "min_dfa": min_dfa_data,
    }


def _handle_step(body):
    state = body.get("state")
    packet = body.get("packet")
    if state is None or packet is None:
        return None, 400
    next_state = _dfa.transitions.get(state, {}).get(packet, TRAP)
    accepted = next_state in _dfa.accept
    trapped = (next_state == TRAP) or (
        next_state not in _dfa.accept and
        all(_dfa.transitions.get(next_state, {}).get(sym, TRAP) == next_state
            for sym in _dfa.alphabet)
    )
    return {"next_state": next_state, "accepted": accepted, "trapped": trapped}, 200


def _handle_check(body):
    sequence = body.get("sequence", [])
    path = _dfa.trace(sequence)
    final = path[-1] if path else _dfa.start
    accepted = final in _dfa.accept
    trapped = (final == TRAP) or (
        final not in _dfa.accept and
        all(_dfa.transitions.get(final, {}).get(sym, TRAP) == final
            for sym in _dfa.alphabet)
    )
    return {"accepted": accepted, "path": path, "trapped": trapped}, 200


INDEX_PATH = os.path.join(SCRIPT_DIR, "index.html")


class CyberBreachServer(HTTPServer):
    # Disable SO_REUSEADDR globally — we handle socket options ourselves
    # Windows rejects SO_REUSEADDR on TCP sockets (WinError 10022)
    allow_reuse_address = False

    def server_bind(self):
        import socket
        if sys.platform == "win32":
            # Windows: use SO_EXCLUSIVEADDRUSE to prevent port hijacking;
            # do NOT set SO_REUSEADDR — it is invalid on Windows TCP sockets
            try:
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
                )
            except (AttributeError, OSError):
                pass  # older Windows builds may not have this constant
        else:
            # macOS / Linux: SO_REUSEADDR is fine and prevents "address in use"
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} - {fmt % args}")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_error(404, "index.html not found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/" or path == "/index.html":
            self._send_html(INDEX_PATH)
        elif path == "/api/missions":
            self._send_json(MISSIONS)
        elif path == "/api/automaton":
            self._send_json(_get_automaton_data())
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, 400)
            return
        if path == "/api/step":
            result, status = _handle_step(body)
            if result is None:
                self._send_json({"error": "missing state or packet"}, status)
            else:
                self._send_json(result, status)
        elif path == "/api/check":
            result, status = _handle_check(body)
            self._send_json(result, status)
        else:
            self.send_error(404)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cyber Breach game server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)),
                        help="Port to listen on (default: 8080)")
    args = parser.parse_args()
    port = args.port
    HTTPServer.allow_reuse_address = False
    server = CyberBreachServer(("0.0.0.0", port), Handler)
    print(f"\nCyber Breach server running at http://localhost:{port}/")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
