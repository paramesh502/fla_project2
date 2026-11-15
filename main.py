"""
main.py — Cyber Breach: NFA/DFA-Based Firewall Infiltration Game
GUI implemented with pygame-ce.

Architecture:
  - automaton.py    : NFA, DFA, minimized DFA logic
  - missions.py     : mission definitions
  - main.py         : pygame GUI (this file)

Screens:
  MENU      → mission select
  GAME      → gameplay: send packets, watch state machine animate
  RESULT    → win/lose screen
  ABOUT     → shows DFA transition table

Controls:
  Button clicks to select packets (P, A, E, X, L)
  SEND    → advance automaton one step
  RESET   → restart current mission
  BACK    → return to menu
  TABLE   → show automaton state table overlay
"""

import sys
import pygame
from automaton import build_nfa, build_dfa, build_min_dfa, TRAP
from missions import MISSIONS

# ── Initialise ────────────────────────────────────────────────────────────────
pygame.init()

W, H = 1000, 700
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Cyber Breach — Firewall Infiltration Game")
clock = pygame.time.Clock()

# ── Fonts ─────────────────────────────────────────────────────────────────────
F_TITLE  = pygame.font.SysFont("monospace", 36, bold=True)
F_LARGE  = pygame.font.SysFont("monospace", 28, bold=True)
F_MED    = pygame.font.SysFont("monospace", 20)
F_SMALL  = pygame.font.SysFont("monospace", 15)

# ── Colour palette ────────────────────────────────────────────────────────────
BLACK   = (  0,   0,   0)
WHITE   = (255, 255, 255)
GRAY    = (120, 120, 120)
LGRAY   = (200, 200, 200)
DGRAY   = ( 40,  40,  40)
GREEN   = ( 50, 205,  50)
RED     = (220,  50,  50)
YELLOW  = (255, 220,   0)
CYAN    = (  0, 220, 220)
ORANGE  = (255, 140,   0)
BLUE    = ( 30, 100, 220)
PURPLE  = (160,  32, 240)
TEAL    = (  0, 180, 160)

BG      = ( 10,  12,  20)
PANEL   = ( 20,  25,  40)
BORDER  = ( 50,  60,  90)

# ── Packet meta ───────────────────────────────────────────────────────────────
PACKET_INFO = {
    "P": {"label": "Ping",    "color": CYAN,   "key": pygame.K_p},
    "A": {"label": "Auth",    "color": GREEN,  "key": pygame.K_a},
    "E": {"label": "Encrypt", "color": YELLOW, "key": pygame.K_e},
    "X": {"label": "Proxy",   "color": ORANGE, "key": pygame.K_x},
    "L": {"label": "Payload", "color": RED,    "key": pygame.K_l},
}
PACKET_ORDER = ["P", "A", "E", "X", "L"]

# ── State colours ─────────────────────────────────────────────────────────────
STATE_COLOR_NORMAL  = BLUE
STATE_COLOR_CURRENT = YELLOW
STATE_COLOR_ACCEPT  = GREEN
STATE_COLOR_TRAP    = RED
STATE_COLOR_MERGED  = TEAL


# ══════════════════════════════════════════════════════════════════════════════
#  Helper drawing utilities
# ══════════════════════════════════════════════════════════════════════════════

def draw_text(surface, text, font, color, x, y, align="left"):
    img = font.render(text, True, color)
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    surface.blit(img, (x, y))
    return img.get_height()


def draw_button(surface, rect, text, font, fg=WHITE, bg=PANEL, border=BORDER,
                hover=False, disabled=False):
    col = (60, 70, 110) if hover else bg
    col = (40, 40, 40)  if disabled else col
    pygame.draw.rect(surface, col, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)
    fc = GRAY if disabled else fg
    img = font.render(text, True, fc)
    surface.blit(img, (rect.centerx - img.get_width()//2,
                       rect.centery - img.get_height()//2))


def draw_panel(surface, rect, title=None):
    pygame.draw.rect(surface, PANEL, rect, border_radius=10)
    pygame.draw.rect(surface, BORDER, rect, 2, border_radius=10)
    if title:
        draw_text(surface, title, F_MED, CYAN,
                  rect.centerx, rect.top + 6, align="center")


def draw_circle_state(surface, x, y, r, label, is_current=False,
                      is_accept=False, is_trap=False, is_start=False):
    if is_trap:
        col = STATE_COLOR_TRAP
    elif is_current:
        col = STATE_COLOR_CURRENT
    elif is_accept:
        col = STATE_COLOR_ACCEPT
    else:
        col = STATE_COLOR_NORMAL

    pygame.draw.circle(surface, col, (x, y), r)
    pygame.draw.circle(surface, WHITE, (x, y), r, 2)
    if is_accept:
        pygame.draw.circle(surface, WHITE, (x, y), r - 5, 2)
    if is_start:
        pts = [(x - r - 20, y), (x - r, y - 10), (x - r, y + 10)]
        pygame.draw.polygon(surface, WHITE, pts)

    img = F_SMALL.render(label, True, BLACK if is_current else WHITE)
    surface.blit(img, (x - img.get_width()//2, y - img.get_height()//2))


def draw_arrow(surface, x1, y1, x2, y2, label="", color=LGRAY, offset=0):
    """Draw an arrow from (x1,y1) to (x2,y2) with optional label."""
    import math
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    # Shorten endpoints to circle edges (r=22)
    r = 22
    sx = x1 + dx/dist * r
    sy = y1 + dy/dist * r
    ex = x2 - dx/dist * r
    ey = y2 - dy/dist * r
    # Draw line
    pygame.draw.line(surface, color, (int(sx), int(sy)), (int(ex), int(ey)), 2)
    # Arrowhead
    angle = math.atan2(ey - sy, ex - sx)
    head_len = 10
    for da in [0.4, -0.4]:
        ax = ex - head_len * math.cos(angle - da)
        ay = ey - head_len * math.sin(angle - da)
        pygame.draw.line(surface, color, (int(ex), int(ey)), (int(ax), int(ay)), 2)
    # Label
    if label:
        mx = (sx + ex) / 2
        my = (sy + ey) / 2
        draw_text(surface, label, F_SMALL, YELLOW,
                  int(mx) + offset, int(my) + offset)


# ══════════════════════════════════════════════════════════════════════════════
#  Game state machine
# ══════════════════════════════════════════════════════════════════════════════

class GameState:
    MENU   = "menu"
    GAME   = "game"
    RESULT = "result"
    ABOUT  = "about"


class CyberBreachGame:
    def __init__(self):
        self.nfa   = build_nfa()
        self.dfa   = build_dfa()
        self.mdfa  = build_min_dfa()

        # State name lists for display
        self.dfa_state_order = self._order_dfa_states()

        self.screen_state  = GameState.MENU
        self.mission_index = 0
        self.mission       = MISSIONS[0]

        # Gameplay vars
        self.current_dfa_state: str = self.dfa.start
        self.packet_sequence: list  = []
        self.selected_packet: str   = "P"
        self.flash_timer: int       = 0    # frames to show accept/reject flash
        self.flash_msg: str         = ""
        self.flash_color            = WHITE
        self.show_table: bool       = False
        self.won_missions: set      = set()
        self.anim_pulse: int        = 0    # animation frame counter

        # Button rects (built in draw phase)
        self._btn_rects: dict = {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _order_dfa_states(self):
        """Return DFA states in a stable display order."""
        order = [self.dfa.start]
        for s in sorted(self.dfa.states):
            if s not in order:
                order.append(s)
        return order

    def reset_mission(self):
        self.current_dfa_state = self.dfa.start
        self.packet_sequence   = []
        self.flash_timer       = 0
        self.show_table        = False

    def send_packet(self, sym: str):
        if self.flash_timer > 0:
            return   # wait for flash to clear
        nxt = self.dfa.transitions.get(self.current_dfa_state, {}).get(sym, TRAP)
        self.current_dfa_state = nxt
        self.packet_sequence.append(sym)

        if nxt == TRAP:
            self.flash_msg   = "🚨  INTRUSION ALARM — TRAPPED!"
            self.flash_color = RED
            self.flash_timer = 90
        elif nxt in self.dfa.accept:
            self.flash_msg   = "✅  ACCESS GRANTED — BREACH SUCCESSFUL!"
            self.flash_color = GREEN
            self.flash_timer = 90
            self.won_missions.add(self.mission["id"])
        else:
            self.flash_msg   = f"→  Packet '{sym}' sent  |  State: {nxt}"
            self.flash_color = CYAN
            self.flash_timer = 30

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = clock.tick(60)
            self.anim_pulse = (self.anim_pulse + 1) % 120
            if self.flash_timer > 0:
                self.flash_timer -= 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.handle_event(event)

            screen.fill(BG)
            if self.screen_state == GameState.MENU:
                self.draw_menu()
            elif self.screen_state == GameState.GAME:
                self.draw_game()
            elif self.screen_state == GameState.RESULT:
                self.draw_result()
            elif self.screen_state == GameState.ABOUT:
                self.draw_about()

            pygame.display.flip()

    # ── Event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        mpos = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._btn_rects.items():
                if rect.collidepoint(mpos):
                    self.handle_button(name)
                    return
        if event.type == pygame.KEYDOWN and self.screen_state == GameState.GAME:
            for sym, info in PACKET_INFO.items():
                if event.key == info["key"]:
                    self.selected_packet = sym
                    return
            if event.key == pygame.K_RETURN:
                self.send_packet(self.selected_packet)
            if event.key == pygame.K_r:
                self.reset_mission()
            if event.key == pygame.K_t:
                self.show_table = not self.show_table

    def handle_button(self, name: str):
        if name.startswith("mission_"):
            idx = int(name.split("_")[1])
            self.mission_index = idx
            self.mission = MISSIONS[idx]
            self.reset_mission()
            self.screen_state = GameState.GAME
        elif name.startswith("pkt_"):
            sym = name.split("_")[1]
            self.selected_packet = sym
        elif name == "send":
            self.send_packet(self.selected_packet)
        elif name == "reset":
            self.reset_mission()
        elif name == "back":
            self.screen_state = GameState.MENU
        elif name == "table":
            self.show_table = not self.show_table
        elif name == "about":
            self.screen_state = GameState.ABOUT
        elif name == "about_back":
            self.screen_state = GameState.MENU
        elif name == "result_menu":
            self.screen_state = GameState.MENU
        elif name == "result_next":
            if self.mission_index < len(MISSIONS) - 1:
                self.mission_index += 1
                self.mission = MISSIONS[self.mission_index]
                self.reset_mission()
                self.screen_state = GameState.GAME
            else:
                self.screen_state = GameState.MENU
        elif name == "next_mission":
            if self.mission_index < len(MISSIONS) - 1:
                self.mission_index += 1
                self.mission = MISSIONS[self.mission_index]
                self.reset_mission()
            else:
                self.screen_state = GameState.MENU

    # ── MENU screen ───────────────────────────────────────────────────────────

    def draw_menu(self):
        self._btn_rects = {}
        # Title
        draw_text(screen, "CYBER BREACH", F_TITLE, CYAN, W//2, 40, align="center")
        draw_text(screen, "NFA/DFA Firewall Infiltration", F_MED, YELLOW,
                  W//2, 90, align="center")
        draw_text(screen, "Select Mission", F_LARGE, WHITE, W//2, 140, align="center")

        # Mission buttons
        bw, bh = 460, 60
        for i, m in enumerate(MISSIONS):
            x = W//2 - bw//2
            y = 190 + i * 80
            won  = m["id"] in self.won_missions
            rect = pygame.Rect(x, y, bw, bh)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            col   = (20, 80, 20) if won else PANEL
            bc    = GREEN if won else BORDER
            pygame.draw.rect(screen, col, rect, border_radius=10)
            pygame.draw.rect(screen, bc,  rect, 2, border_radius=10)
            tick = "✓ " if won else "   "
            draw_text(screen, f"{tick}{m['name']}", F_MED, WHITE,
                      rect.centerx, rect.centery - 10, align="center")
            draw_text(screen, m["description"].split("\n")[0], F_SMALL, LGRAY,
                      rect.centerx, rect.centery + 12, align="center")
            self._btn_rects[f"mission_{i}"] = rect

        # About button
        ab = pygame.Rect(W//2 - 80, H - 70, 160, 44)
        draw_button(screen, ab, "ABOUT / TABLE", F_SMALL,
                    hover=ab.collidepoint(pygame.mouse.get_pos()))
        self._btn_rects["about"] = ab

    # ── GAME screen ───────────────────────────────────────────────────────────

    def draw_game(self):
        self._btn_rects = {}
        m = self.mission

        # Header
        draw_text(screen, m["name"], F_LARGE, CYAN, W//2, 10, align="center")
        draw_text(screen, m["description"].replace("\n", "  "), F_SMALL, LGRAY,
                  W//2, 50, align="center")

        # --- DFA state diagram (left panel) ---
        diag_rect = pygame.Rect(10, 70, 480, 340)
        draw_panel(screen, diag_rect, "Automaton State Diagram (DFA)")
        self.draw_dfa_diagram(diag_rect)

        # --- Packet log (right panel) ---
        log_rect = pygame.Rect(500, 70, 490, 180)
        draw_panel(screen, log_rect, "Packet Log")
        seq_str = " → ".join(self.packet_sequence) if self.packet_sequence else "(no packets sent)"
        draw_text(screen, seq_str, F_SMALL, WHITE,
                  log_rect.left + 10, log_rect.top + 32)
        draw_text(screen, f"Current DFA state: {self.current_dfa_state}",
                  F_SMALL, YELLOW, log_rect.left + 10, log_rect.top + 60)
        status = "ACCEPT" if self.current_dfa_state in self.dfa.accept else \
                 "TRAP"   if self.current_dfa_state == TRAP else "RUNNING"
        sc = GREEN if status == "ACCEPT" else RED if status == "TRAP" else WHITE
        draw_text(screen, f"Status: {status}", F_MED, sc,
                  log_rect.left + 10, log_rect.top + 85)

        # hint
        draw_text(screen, m["hint"], F_SMALL, TEAL,
                  log_rect.left + 10, log_rect.top + 120)

        # --- Packet selector (right panel) ---
        sel_rect = pygame.Rect(500, 260, 490, 150)
        draw_panel(screen, sel_rect, "Select Packet  (keyboard: P A E X L)")
        bw, bh = 80, 44
        for i, sym in enumerate(PACKET_ORDER):
            info = PACKET_INFO[sym]
            x = sel_rect.left + 10 + i * (bw + 8)
            y = sel_rect.top + 32
            rect = pygame.Rect(x, y, bw, bh)
            border_col = WHITE if sym == self.selected_packet else BORDER
            bg_col     = info["color"] if sym == self.selected_packet else PANEL
            pygame.draw.rect(screen, bg_col, rect, border_radius=8)
            pygame.draw.rect(screen, border_col, rect, 2, border_radius=8)
            draw_text(screen, sym, F_MED, BLACK if sym == self.selected_packet else WHITE,
                      rect.centerx, rect.top + 5, align="center")
            draw_text(screen, info["label"], F_SMALL,
                      BLACK if sym == self.selected_packet else LGRAY,
                      rect.centerx, rect.top + 25, align="center")
            self._btn_rects[f"pkt_{sym}"] = rect

        # Send / Reset / Back / Table
        ctrl_y = sel_rect.bottom + 10
        btns = [
            ("send",  "SEND  [Enter]",  BLUE),
            ("reset", "RESET [R]",      ORANGE),
            ("table", "TABLE [T]",      PURPLE),
            ("back",  "BACK",           DGRAY),
        ]
        for i, (name, label, col) in enumerate(btns):
            x = 500 + i * 123
            rect = pygame.Rect(x, ctrl_y, 118, 44)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, col if hover else PANEL, rect, border_radius=8)
            pygame.draw.rect(screen, BORDER, rect, 2, border_radius=8)
            draw_text(screen, label, F_SMALL, WHITE, rect.centerx, rect.centery - 8, align="center")
            self._btn_rects[name] = rect

        # Mission nav
        nav_y = ctrl_y + 55
        if self.mission_index > 0:
            pr = pygame.Rect(500, nav_y, 120, 36)
            draw_button(screen, pr, "◀ Prev", F_SMALL,
                        hover=pr.collidepoint(pygame.mouse.get_pos()))
            self._btn_rects["mission_" + str(self.mission_index - 1)] = pr
        if self.mission_index < len(MISSIONS) - 1:
            nr = pygame.Rect(870, nav_y, 120, 36)
            draw_button(screen, nr, "Next ▶", F_SMALL,
                        hover=nr.collidepoint(pygame.mouse.get_pos()))
            self._btn_rects["mission_" + str(self.mission_index + 1)] = nr

        # Flash message
        if self.flash_timer > 0:
            alpha = min(255, self.flash_timer * 4)
            msg_surf = F_LARGE.render(self.flash_msg, True, self.flash_color)
            msg_surf.set_alpha(alpha)
            screen.blit(msg_surf, (W//2 - msg_surf.get_width()//2, H - 60))

        # Table overlay
        if self.show_table:
            self.draw_table_overlay()

    def draw_dfa_diagram(self, rect):
        """Draw the DFA states and transitions inside rect."""
        import math

        cx, cy = rect.centerx, rect.centery + 20
        states = [s for s in self.dfa_state_order if s in self.dfa.states]
        n      = len(states)
        radius = min(rect.width, rect.height) // 2 - 36

        # Positions on a circle
        positions: dict = {}
        for i, s in enumerate(states):
            angle  = -math.pi/2 + 2*math.pi * i / n
            px     = int(cx + radius * math.cos(angle))
            py     = int(cy + radius * math.sin(angle))
            positions[s] = (px, py)

        # Pulse animation for current state
        pulse_r = 22 + int(4 * math.sin(self.anim_pulse * math.pi / 60))

        # Draw edges (abbreviated: only first symbol per pair)
        drawn_pairs: dict = {}
        for src in states:
            for sym in PACKET_ORDER:
                dst = self.dfa.transitions.get(src, {}).get(sym, TRAP)
                if dst not in positions:
                    continue
                pair = (src, dst)
                label = drawn_pairs.get(pair, "")
                drawn_pairs[pair] = (label + "," + sym).lstrip(",")
        for (src, dst), label in drawn_pairs.items():
            x1, y1 = positions[src]
            x2, y2 = positions[dst]
            if src == dst:
                # Self-loop: draw small arc above
                loop_r = 14
                loop_x = x1
                loop_y = y1 - 22 - loop_r
                pygame.draw.circle(screen, LGRAY, (loop_x, loop_y), loop_r, 2)
                draw_text(screen, label, F_SMALL, YELLOW, loop_x, loop_y - loop_r - 2, align="center")
            else:
                draw_arrow(screen, x1, y1, x2, y2, label, LGRAY, offset=-6)

        # Draw state circles
        for s, (px, py) in positions.items():
            is_cur    = (s == self.current_dfa_state)
            is_accept = (s in self.dfa.accept)
            is_trap   = (s == TRAP)
            is_start  = (s == self.dfa.start)
            r         = pulse_r if is_cur else 22
            # Short label
            if s == TRAP:
                lbl = "TRAP"
            elif s == self.dfa.start:
                lbl = "D0"
            else:
                idx = self.dfa_state_order.index(s)
                lbl = f"D{idx}"
            draw_circle_state(screen, px, py, r, lbl, is_cur, is_accept, is_trap, is_start)

    # ── TABLE overlay ─────────────────────────────────────────────────────────

    def draw_table_overlay(self):
        ow, oh = 760, 420
        ox     = (W - ow) // 2
        oy     = (H - oh) // 2
        surf   = pygame.Surface((ow, oh), pygame.SRCALPHA)
        surf.fill((10, 15, 30, 230))
        screen.blit(surf, (ox, oy))
        pygame.draw.rect(screen, BORDER, (ox, oy, ow, oh), 2, border_radius=12)

        draw_text(screen, "Minimized DFA Transition Table", F_MED, CYAN,
                  ox + ow//2, oy + 10, align="center")

        # State name map
        state_map = {
            self.mdfa.start: "M0 (start)",
        }
        for s in sorted(self.mdfa.states):
            if s not in state_map:
                idx = sorted(self.mdfa.states).index(s)
                state_map[s] = f"M{idx}"

        col_w  = 100
        row_h  = 32
        hdr_y  = oy + 44
        symbols = sorted(self.mdfa.alphabet)

        # Header row
        draw_text(screen, "State", F_SMALL, YELLOW, ox + 20, hdr_y)
        for ci, sym in enumerate(symbols):
            draw_text(screen, sym + " (" + {"P": "Ping", "A": "Auth",
                      "E": "Enc", "X": "Prx", "L": "Pay"}[sym] + ")",
                      F_SMALL, YELLOW, ox + 130 + ci * col_w, hdr_y)

        pygame.draw.line(screen, BORDER,
                         (ox + 10, hdr_y + 20), (ox + ow - 10, hdr_y + 20), 1)

        # Rows
        for ri, s in enumerate(sorted(self.mdfa.states)):
            y = hdr_y + 24 + ri * row_h
            lbl = state_map.get(s, s[:12])
            if s in self.mdfa.accept:
                lbl += " ✓"
            sc = GREEN if s in self.mdfa.accept else \
                 RED   if "TRAP" in s else \
                 YELLOW if s == self.mdfa.start else WHITE
            draw_text(screen, lbl, F_SMALL, sc, ox + 20, y)
            for ci, sym in enumerate(symbols):
                dst = self.mdfa.transitions.get(s, {}).get(sym, TRAP)
                dst_lbl = state_map.get(dst, dst[:10])
                dc = RED if "TRAP" in dst else GREEN if dst in self.mdfa.accept else LGRAY
                draw_text(screen, dst_lbl, F_SMALL, dc, ox + 130 + ci * col_w, y)

        draw_text(screen, "Press T or click TABLE to close", F_SMALL, GRAY,
                  ox + ow//2, oy + oh - 24, align="center")

    # ── ABOUT screen ──────────────────────────────────────────────────────────

    def draw_about(self):
        self._btn_rects = {}
        draw_text(screen, "CYBER BREACH — Automaton Design", F_LARGE, CYAN, W//2, 20, align="center")

        lines = [
            ("NFA Design", YELLOW),
            ("  States : q0 (start), q1, q2, q3, q4 (accept), q5, q6, q7", WHITE),
            ("  Alphabet: P=Ping  A=Auth  E=Encrypt  X=Proxy  L=Payload", WHITE),
            ("  ε-transitions: q0→q2 (proxy tunnel), q1→q3, q5→q6", CYAN),
            ("  Total NFA states: 8", LGRAY),
            ("", WHITE),
            ("NFA→DFA (Subset Construction)", YELLOW),
            ("  Start  = ε-closure({q0}) = {q0,q2}  →  D0", WHITE),
            ("  D0 --P--> ε-closure({q1}) = {q1,q3} → D1", WHITE),
            ("  D0 --E--> ε-closure({q3}) = {q3}    → D2", WHITE),
            ("  D0 --X--> ε-closure({q5,q6}) = {q5,q6} → D4", WHITE),
            ("  Total DFA states: 7  (D0..D5 + TRAP)", LGRAY),
            ("", WHITE),
            ("DFA Minimization (Table-Filling / Myhill-Nerode)", YELLOW),
            ("  Accept D3={q4} distinguished from all others in round 0", WHITE),
            ("  D2={q3} and D5={q7} have identical future language → MERGED", GREEN),
            ("  Total minimized DFA states: 6  (reduction: 7→6)", TEAL),
            ("", WHITE),
            ("Trap State", YELLOW),
            ("  Undefined transitions → TRAP (absorbing, no escape)", RED),
            ("  E.g. D0 --A--> TRAP, D0 --L--> TRAP", LGRAY),
        ]
        y = 65
        for text, col in lines:
            h = draw_text(screen, text, F_SMALL, col, 60, y)
            y += h + 4

        # Back button
        br = pygame.Rect(W//2 - 80, H - 60, 160, 40)
        draw_button(screen, br, "BACK TO MENU", F_SMALL,
                    hover=br.collidepoint(pygame.mouse.get_pos()))
        self._btn_rects["about_back"] = br

    # ── RESULT screen ─────────────────────────────────────────────────────────

    def draw_result(self):
        self._btn_rects = {}
        draw_text(screen, "MISSION COMPLETE", F_TITLE, GREEN, W//2, 200, align="center")
        draw_text(screen, f"{self.mission['name']}", F_LARGE, YELLOW, W//2, 280, align="center")

        mr = pygame.Rect(W//2 - 100, 360, 200, 50)
        draw_button(screen, mr, "MENU", F_MED, hover=mr.collidepoint(pygame.mouse.get_pos()))
        self._btn_rects["result_menu"] = mr

        nr = pygame.Rect(W//2 - 100, 430, 200, 50)
        draw_button(screen, nr, "NEXT MISSION", F_MED,
                    hover=nr.collidepoint(pygame.mouse.get_pos()),
                    disabled=self.mission_index >= len(MISSIONS) - 1)
        self._btn_rects["result_next"] = nr


# ══════════════════════════════════════════════════════════════════════════════

def main():
    game = CyberBreachGame()
    game.run()


if __name__ == "__main__":
    main()
