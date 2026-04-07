"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗   ██╗ ██████╗  ██████╗ ███╗   ██╗ ██████╗██╗  ██╗     ║
║   ╚██╗ ██╔╝██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║     ║
║    ╚████╔╝ ██║   ██║██║   ██║██╔██╗ ██║██║     ███████║     ║
║     ╚██╔╝  ██║   ██║██║   ██║██║╚██╗██║██║     ██╔══██║     ║
║      ██║   ╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║  ██║     ║
║      ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝     ║
║                                                               ║
║        S W E E P E R   v3.0   —   by  yoonchan              ║
║        Sol's RNG 알줍기 하네스 모드 매크로                   ║
║        직접 제작 · 악성코드 없는 100% 안전한 버전            ║
╚═══════════════════════════════════════════════════════════════╝

이동 모드:
  SWEEP   맵 체계적 순회 (기본 추천)
  SPIRAL  나선형 확장 이동 (커버리지 최대)
  GRID    격자 패턴 정밀 수집
  RANDOM  랜덤 이동 (봇 감지 우회)
  VISION  화면 색상 감지로 알 추적 (최고급)

단축키:
  F9   시작 / 중지 토글
  F8   모드 순환 전환
  F7   실시간 통계 출력
  F6   현재 설정 출력
  F10  프로그램 완전 종료
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 임포트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import sys, os, json, time, random, threading, logging
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

import pyautogui
import keyboard

try:
    from PIL import ImageGrab
    import numpy as np
    VISION_OK = True
except ImportError:
    VISION_OK = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANSI 색상 (터미널 컬러 출력)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"

def cprint(msg: str, color: str = C.WHITE, bold: bool = False):
    prefix = (C.BOLD if bold else "") + color
    print(f"{prefix}{msg}{C.RESET}")

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 설정 (Config)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yoonchan_config.json")

DEFAULT_CFG = {
    "mode": "SWEEP",
    "interact_interval": 0.22,      # F키 주기 (초)
    "jump_interval": 1.3,           # 점프 주기 (초), 0=비활성화
    "step_time": 1.0,               # 기본 이동 시간
    "anti_afk": True,               # AFK 킥 방지
    "anti_afk_sec": 110,            # AFK 방지 주기 (초, 킥 기준보다 짧게)
    "jitter": True,                 # 랜덤 타이밍 지터
    "jitter_max": 0.12,             # 지터 최대 범위 (초)
    "failsafe": True,               # 마우스 좌상단 → 비상정지
    "log_file": True,               # 로그 파일 저장
    "spiral_max_radius": 3.5,       # SPIRAL 최대 반지름
    "grid_cols": 5,                 # GRID 가로 칸 수
    "grid_rows": 4,                 # GRID 세로 칸 수
    "vision_scan_interval": 0.4,    # VISION 스캔 주기
    "vision_min_pixels": 25,        # 감지 최소 픽셀
    "vision_colors": [
        {"name": "golden_egg",  "r": [200,255], "g": [180,255], "b": [80,180]},
        {"name": "rare_purple", "r": [120,210], "g": [40,130],  "b": [190,255]},
        {"name": "item_white",  "r": [230,255], "g": [230,255], "b": [230,255]},
        {"name": "cyan_aura",   "r": [40,140],  "g": [200,255], "b": [200,255]},
    ],
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

def save_cfg(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

CFG = load_cfg()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 로거
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

handlers = [logging.StreamHandler(sys.stdout)]
if CFG["log_file"]:
    _lf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"yoonchan_{datetime.now():%Y%m%d}.log")
    handlers.append(logging.FileHandler(_lf, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=handlers,
)
log = logging.getLogger("YoonchanSweeper")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 상태 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODES = ["SWEEP", "SPIRAL", "GRID", "RANDOM", "VISION"]

@dataclass
class Stats:
    start: Optional[float] = None
    pickups: int = 0
    cycles: int = 0
    detected: int = 0
    afk_triggers: int = 0
    pickup_history: deque = field(default_factory=lambda: deque(maxlen=120))

class State:
    def __init__(self):
        self.running = False
        self.mode = CFG["mode"]
        self.stop = threading.Event()
        self.stats = Stats()
        self._lock = threading.Lock()

    def reset_stats(self):
        with self._lock:
            self.stats = Stats(start=time.time())

state = State()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 유틸
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPPOSITE = {"w": "s", "s": "w", "a": "d", "d": "a"}

def jit(base: float) -> float:
    """타이밍 지터 — 봇 감지 우회"""
    if not CFG["jitter"]:
        return base
    return max(0.03, base + random.uniform(-CFG["jitter_max"], CFG["jitter_max"]))

def release_all():
    for k in "wasd":
        try: keyboard.release(k)
        except: pass

def pick():
    """F키 픽업"""
    keyboard.press_and_release("f")
    with state._lock:
        state.stats.pickups += 1
        state.stats.pickup_history.append(time.time())

def jump():
    keyboard.press_and_release("space")

def move(direction: str, dur: float, interact: bool = True):
    """
    방향키를 dur초 동안 누르면서
    - F키 interact_interval마다 누름
    - jump_interval마다 점프
    """
    last_pick = time.time()
    last_jump = time.time()
    keyboard.press(direction)
    t0 = time.time()
    try:
        while time.time() - t0 < dur:
            if state.stop.is_set():
                break
            now = time.time()
            if interact and now - last_pick >= jit(CFG["interact_interval"]):
                pick()
                last_pick = now
            ji = CFG["jump_interval"]
            if ji > 0 and now - last_jump >= jit(ji):
                jump()
                last_jump = now
            time.sleep(0.04)
    finally:
        keyboard.release(direction)

def stopped() -> bool:
    return state.stop.is_set()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Anti-AFK 시스템
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _anti_afk_worker():
    interval = CFG["anti_afk_sec"]
    log.info("[AntiAFK] 시작 (%d초 주기)", interval)
    while not state.stop.is_set():
        # 작은 슬립으로 stop 이벤트 빠르게 감지
        for _ in range(interval * 10):
            if state.stop.is_set(): return
            time.sleep(0.1)
        if not state.running: continue
        # 마우스 미세 이동
        px, py = pyautogui.position()
        pyautogui.moveRel(2, 0, duration=0.1)
        pyautogui.moveRel(-2, 0, duration=0.1)
        keyboard.press_and_release("space")
        with state._lock:
            state.stats.afk_triggers += 1
        log.debug("[AntiAFK] 동작 실행")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모드 1: SWEEP — 체계적 맵 순회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SWEEP_PAT = [
    ("w",1.8),("d",1.1),("w",1.8),("d",1.1),
    ("s",1.8),("a",1.1),("s",1.8),("a",1.1),
    ("w",2.5),("d",2.0),("s",2.5),("a",2.0),
]

def run_sweep():
    log.info("[SWEEP] 시작")
    idx = 0
    while not stopped():
        d, t = SWEEP_PAT[idx]
        move(d, jit(t))
        idx = (idx + 1) % len(SWEEP_PAT)
        if idx == 0:
            with state._lock: state.stats.cycles += 1
            _log_progress("SWEEP")
        time.sleep(jit(0.08))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모드 2: SPIRAL — 나선형 확장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_spiral():
    log.info("[SPIRAL] 시작")
    radius = 0.4
    max_r  = CFG["spiral_max_radius"]
    dirs   = ["w", "d", "s", "a"]
    while not stopped():
        for d in dirs:
            move(d, jit(radius))
            if stopped(): return
        radius = min(radius + 0.15, max_r)
        with state._lock: state.stats.cycles += 1
        if state.stats.cycles % 8 == 0:
            radius = 0.4  # 리셋
            log.info("[SPIRAL] 반경 리셋 | 픽업 %d회", state.stats.pickups)
        time.sleep(jit(0.05))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모드 3: GRID — 격자 패턴
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_grid():
    log.info("[GRID] 시작 (%dx%d)", CFG["grid_cols"], CFG["grid_rows"])
    cols = CFG["grid_cols"]
    rows = CFG["grid_rows"]
    step = jit(CFG["step_time"])
    while not stopped():
        for r in range(rows):
            lr = "d" if r % 2 == 0 else "a"   # 지그재그
            for _ in range(cols):
                move(lr, step)
                if stopped(): return
            if r < rows - 1:
                move("s", step * 0.7)
                if stopped(): return
        # 원점 복귀
        move("w", step * rows * 0.7)
        move("a" if cols % 2 == 0 else "d", step * cols * 0.5)
        with state._lock: state.stats.cycles += 1
        _log_progress("GRID")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모드 4: RANDOM — 봇 감지 우회 랜덤 이동
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_random():
    log.info("[RANDOM] 시작")
    prev = None
    dirs = list("wasd")
    while not stopped():
        choices = [d for d in dirs if d != OPPOSITE.get(prev)]
        d = random.choice(choices)
        prev = d
        t = random.uniform(0.4, 2.4)
        move(d, jit(t))
        # 가끔 연속 픽업
        if random.random() < 0.25:
            for _ in range(random.randint(2, 6)):
                if stopped(): break
                pick()
                time.sleep(jit(0.12))
        with state._lock: state.stats.cycles += 1
        time.sleep(jit(random.uniform(0.05, 0.25)))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 모드 5: VISION — 화면 색상 감지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _scan() -> Optional[Tuple[int, int, str, int]]:
    """화면에서 아이템 색상 감지 → (cx, cy, name, count) 또는 None"""
    try:
        img = ImageGrab.grab()
        arr = np.array(img)
        for c in CFG["vision_colors"]:
            mask = (
                (arr[:,:,0] >= c["r"][0]) & (arr[:,:,0] <= c["r"][1]) &
                (arr[:,:,1] >= c["g"][0]) & (arr[:,:,1] <= c["g"][1]) &
                (arr[:,:,2] >= c["b"][0]) & (arr[:,:,2] <= c["b"][1])
            )
            cnt = int(np.sum(mask))
            if cnt >= CFG["vision_min_pixels"]:
                ys, xs = np.where(mask)
                return int(xs.mean()), int(ys.mean()), c["name"], cnt
    except Exception as e:
        log.debug("[VISION] 스캔 오류: %s", e)
    return None

def run_vision():
    if not VISION_OK:
        cprint("[VISION] numpy/pillow 없음 → RANDOM으로 대체", C.YELLOW)
        run_random(); return

    log.info("[VISION] 화면 감지 모드 시작")
    last_scan = 0
    last_pick = time.time()
    last_jump = time.time()
    holding: Optional[str] = None
    sw, sh = pyautogui.size()
    cx0, cy0 = sw // 2, sh // 2

    while not stopped():
        now = time.time()
        if now - last_pick >= jit(CFG["interact_interval"]):
            pick(); last_pick = now
        ji = CFG["jump_interval"]
        if ji > 0 and now - last_jump >= jit(ji):
            jump(); last_jump = now

        if now - last_scan >= CFG["vision_scan_interval"]:
            last_scan = now
            result = _scan()
            if holding:
                keyboard.release(holding); holding = None

            if result:
                ix, iy, name, cnt = result
                dx, dy = ix - cx0, iy - cy0
                nd = ("d" if dx > 0 else "a") if abs(dx) > abs(dy) else ("s" if dy > 0 else "w")
                keyboard.press(nd); holding = nd
                with state._lock:
                    state.stats.detected += 1
                    state.stats.cycles += 1
                log.info("[VISION] %s 감지 %dpx → %s 이동", name, cnt, nd)
            else:
                # 아이템 없으면 랜덤 단기 이동
                d = random.choice(list("wasd"))
                move(d, jit(0.7))
                with state._lock: state.stats.cycles += 1

        time.sleep(0.04)

    if holding:
        try: keyboard.release(holding)
        except: pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 매크로 엔진
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RUNNERS = {
    "SWEEP":  run_sweep,
    "SPIRAL": run_spiral,
    "GRID":   run_grid,
    "RANDOM": run_random,
    "VISION": run_vision,
}

def _log_progress(tag: str):
    if state.stats.start:
        e = time.time() - state.stats.start
        rpm = state.stats.pickups / max(e / 60, 0.01)
        log.info("[%s] 사이클 %d | 픽업 %d (%.1f/분) | %s",
                 tag, state.stats.cycles, state.stats.pickups, rpm,
                 str(timedelta(seconds=int(e))))

def _macro_worker():
    state.reset_stats()
    log.info("▶ YoonchanSweeper 시작 — 모드: %s", state.mode)
    try:
        RUNNERS[state.mode]()
    except Exception as e:
        log.error("매크로 오류: %s", e, exc_info=True)
    finally:
        release_all()
        _print_stats()
        state.running = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 통계 출력
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _print_stats():
    s = state.stats
    elapsed = (time.time() - s.start) if s.start else 0
    rpm = s.pickups / max(elapsed / 60, 0.01)
    # 최근 1분 픽업 속도
    now = time.time()
    recent = sum(1 for t in s.pickup_history if now - t <= 60)
    bar_len = min(int(rpm), 40)
    bar = "█" * bar_len + "░" * (40 - bar_len)

    cprint("\n" + "═" * 58, C.CYAN, bold=True)
    cprint("  YoonchanSweeper 통계", C.CYAN, bold=True)
    cprint("═" * 58, C.CYAN)
    cprint(f"  모드          : {state.mode}", C.WHITE)
    cprint(f"  실행 시간     : {timedelta(seconds=int(elapsed))}", C.WHITE)
    cprint(f"  총 픽업       : {s.pickups} 회", C.GREEN, bold=True)
    cprint(f"  사이클        : {s.cycles} 회", C.WHITE)
    cprint(f"  픽업 속도     : {rpm:.1f} / 분  (최근1분: {recent})", C.YELLOW)
    cprint(f"  [{bar}]", C.GREEN)
    if VISION_OK:
        cprint(f"  아이템 감지   : {s.detected} 회", C.MAGENTA)
    cprint(f"  Anti-AFK      : {s.afk_triggers} 회", C.DIM)
    cprint("═" * 58 + "\n", C.CYAN)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 단축키 핸들러
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def on_f9():
    """F9: 시작 / 중지 토글"""
    if not state.running:
        state.running = True
        state.stop.clear()
        threading.Thread(target=_macro_worker, daemon=True).start()
        if CFG["anti_afk"]:
            threading.Thread(target=_anti_afk_worker, daemon=True).start()
        cprint(f"\n{'═'*50}", C.GREEN, bold=True)
        cprint(f"  ▶  ON  —  모드: {state.mode}", C.GREEN, bold=True)
        cprint(f"{'═'*50}\n", C.GREEN)
    else:
        cprint("  ⏸ 중지 중...", C.YELLOW)
        state.stop.set()
        state.running = False

def on_f8():
    """F8: 모드 순환"""
    was = state.running
    if was:
        state.stop.set(); state.running = False; time.sleep(0.4)
    idx = MODES.index(state.mode)
    state.mode = MODES[(idx + 1) % len(MODES)]
    cprint(f"\n  🔄 모드 → {state.mode}\n", C.CYAN, bold=True)
    if was:
        state.stop.clear(); state.running = True
        threading.Thread(target=_macro_worker, daemon=True).start()
        if CFG["anti_afk"]:
            threading.Thread(target=_anti_afk_worker, daemon=True).start()

def on_f7():
    """F7: 통계 출력"""
    _print_stats()

def on_f6():
    """F6: 현재 설정 출력"""
    cprint("\n  현재 설정 (yoonchan_config.json)", C.YELLOW, bold=True)
    for k, v in CFG.items():
        if k != "vision_colors":
            cprint(f"    {k:<25}: {v}", C.WHITE)
    cprint("")

def on_f10():
    """F10: 완전 종료"""
    cprint("\n  YoonchanSweeper 종료 중...", C.RED)
    state.stop.set(); state.running = False
    time.sleep(0.3)
    save_cfg(CFG)
    log.info("종료")
    sys.exit(0)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 헤드라인 배너
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗   ██╗ ██████╗  ██████╗ ███╗   ██╗ ██████╗██╗  ██╗     ║
║   ╚██╗ ██╔╝██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║     ║
║    ╚████╔╝ ██║   ██║██║   ██║██╔██╗ ██║██║     ███████║     ║
║     ╚██╔╝  ██║   ██║██║   ██║██║╚██╗██║██║     ██╔══██║     ║
║      ██║   ╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║  ██║     ║
║      ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝     ║
║                                                               ║
║      S W E E P E R   v3.0        by  yoonchan               ║
╚═══════════════════════════════════════════════════════════════╝
"""

def print_banner():
    print(C.CYAN + C.BOLD + BANNER + C.RESET)
    cprint("  Sol's RNG 알줍기 하네스 모드 매크로 (직접 제작 · 안전)", C.WHITE)
    print()
    cprint("  단축키", C.YELLOW, bold=True)
    print("  " + "─"*44)
    cprint("  F9   매크로 시작 / 중지", C.GREEN)
    cprint("  F8   모드 순환  (SWEEP→SPIRAL→GRID→RANDOM→VISION)", C.CYAN)
    cprint("  F7   실시간 통계 출력", C.WHITE)
    cprint("  F6   현재 설정 출력", C.WHITE)
    cprint("  F10  프로그램 종료", C.RED)
    print()
    cprint(f"  현재 모드  : {CFG['mode']}", C.YELLOW, bold=True)
    cprint(f"  Vision     : {'사용 가능 (numpy+pillow)' if VISION_OK else '불가 — pip install numpy'}", C.WHITE)
    cprint(f"  Anti-AFK   : {'ON' if CFG['anti_afk'] else 'OFF'}", C.WHITE)
    cprint(f"  지터(Jitter): {'ON' if CFG['jitter'] else 'OFF'}", C.WHITE)
    cprint(f"  Failsafe   : {'ON — 마우스 좌상단 이동시 비상정지' if CFG['failsafe'] else 'OFF'}", C.WHITE)
    print()
    cprint("  ⚠  Sol's RNG 창을 클릭해서 포커스한 뒤 F9 누르세요!", C.YELLOW, bold=True)
    print()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    # Windows 콘솔 ANSI 활성화
    if sys.platform == "win32":
        os.system("color")

    pyautogui.FAILSAFE = CFG["failsafe"]
    save_cfg(CFG)  # 최초 설정 파일 생성

    print_banner()
    log.info("YoonchanSweeper v3.0 대기 중")

    keyboard.add_hotkey("f9",  on_f9,  suppress=False)
    keyboard.add_hotkey("f8",  on_f8,  suppress=False)
    keyboard.add_hotkey("f7",  on_f7,  suppress=False)
    keyboard.add_hotkey("f6",  on_f6,  suppress=False)
    keyboard.add_hotkey("f10", on_f10, suppress=False)

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        on_f10()

if __name__ == "__main__":
    main()
