"""
YoonchanSweeper — Shared State & Config
"""
from __future__ import annotations
import json, os, threading, time
from dataclasses import dataclass, field
from collections import deque
from typing import Optional

# ── 경로 ────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "yoonchan_config.json")
LOG_DIR     = BASE_DIR

# ── 기본 설정 ────────────────────────────────────────────
DEFAULT_CFG: dict = {
    "mode": "BEAST",

    # 이동/픽업
    "interact_interval":  0.20,
    "jump_interval":      1.2,
    "step_time":          1.0,

    # 안티 감지
    "jitter":             True,
    "jitter_max":         0.13,
    "human_pauses":       True,
    "fatigue_mode":       True,       # 장시간 사용 시 자연스럽게 느려짐

    # AFK 방지
    "anti_afk":           True,
    "anti_afk_sec":       105,

    # 안전
    "failsafe":           True,
    "auto_reconnect":     True,       # 연결 끊김 감지 시 F9 재시작

    # Vision
    "vision_scan_interval": 0.35,
    "vision_min_pixels":    20,
    "vision_screen_region": None,     # None=전체, [x,y,w,h]=부분
    "vision_colors": [
        {"name": "golden_egg",  "r": [195,255], "g": [175,255], "b": [70,175]},
        {"name": "rare_purple", "r": [110,215], "g": [35,135],  "b": [185,255]},
        {"name": "item_white",  "r": [225,255], "g": [225,255], "b": [225,255]},
        {"name": "cyan_aura",   "r": [30,140],  "g": [195,255], "b": [195,255]},
        {"name": "red_rare",    "r": [200,255], "g": [30,100],  "b": [30,100]},
    ],

    # GRID
    "grid_cols":          5,
    "grid_rows":          4,

    # SPIRAL
    "spiral_max_radius":  3.5,

    # Dashboard
    "dashboard":          True,
    "dashboard_port":     7777,

    # 알림
    "beep_on_rare":       True,

    # 로그
    "log_file":           True,
}


def load_cfg() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            cfg = DEFAULT_CFG.copy()
            cfg.update(user)
            return cfg
        except Exception:
            pass
    return DEFAULT_CFG.copy()


def save_cfg(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── 통계 ─────────────────────────────────────────────────
@dataclass
class Stats:
    start:           Optional[float] = None
    pickups:         int             = 0
    cycles:          int             = 0
    detected:        int             = 0
    afk_triggers:    int             = 0
    rare_detected:   int             = 0
    reconnects:      int             = 0
    pickup_history:  deque           = field(default_factory=lambda: deque(maxlen=180))

    def elapsed(self) -> float:
        return (time.time() - self.start) if self.start else 0.0

    def rate_per_min(self) -> float:
        return self.pickups / max(self.elapsed() / 60, 0.01)

    def recent_rate(self, window_sec: int = 60) -> int:
        now = time.time()
        return sum(1 for t in self.pickup_history if now - t <= window_sec)

    def to_dict(self) -> dict:
        import datetime
        e = self.elapsed()
        return {
            "pickups":      self.pickups,
            "cycles":       self.cycles,
            "detected":     self.detected,
            "afk_triggers": self.afk_triggers,
            "rare_detected":self.rare_detected,
            "reconnects":   self.reconnects,
            "elapsed":      str(datetime.timedelta(seconds=int(e))),
            "rate_per_min": round(self.rate_per_min(), 1),
            "rate_1min":    self.recent_rate(60),
        }


# ── 공유 상태 ─────────────────────────────────────────────
MODES = ["SWEEP", "SPIRAL", "GRID", "RANDOM", "VISION", "SMART", "BEAST"]

class MacroState:
    def __init__(self):
        self.running   = False
        self.mode      = "SWEEP"
        self.stop      = threading.Event()
        self.stats     = Stats()
        self._lock     = threading.Lock()
        self.cfg       = load_cfg()
        self.mode      = self.cfg["mode"]

    def reset(self):
        with self._lock:
            self.stats = Stats(start=time.time())

    def next_mode(self) -> str:
        idx = MODES.index(self.mode) if self.mode in MODES else 0
        self.mode = MODES[(idx + 1) % len(MODES)]
        return self.mode

    def add_pickup(self):
        with self._lock:
            self.stats.pickups += 1
            self.stats.pickup_history.append(time.time())

    def add_cycle(self):
        with self._lock:
            self.stats.cycles += 1

    def snapshot(self) -> dict:
        with self._lock:
            d = self.stats.to_dict()
            d["mode"]    = self.mode
            d["running"] = self.running
            return d
