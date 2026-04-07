"""
YoonchanSweeper — All Macro Modes
  SWEEP · SPIRAL · GRID · RANDOM · VISION · SMART
"""
from __future__ import annotations
import time, random, logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state    import MacroState
    from .movement import MovementEngine
    from .vision   import VisionEngine

log = logging.getLogger("YoonchanSweeper.modes")

OPPOSITE = {"w": "s", "s": "w", "a": "d", "d": "a"}


def stopped(state: "MacroState") -> bool:
    return state.stop.is_set()


# ══════════════════════════════════════════════════════════
# 공통 헬퍼
# ══════════════════════════════════════════════════════════

def _progress(state: "MacroState", tag: str):
    s = state.stats
    log.info("[%s] 사이클 %d | 픽업 %d (%.1f/분)",
             tag, s.cycles, s.pickups, s.rate_per_min())


# ══════════════════════════════════════════════════════════
# SWEEP — 지그재그 체계적 순회
# ══════════════════════════════════════════════════════════

SWEEP_PAT = [
    ("w",1.8),("d",1.0),("w",1.8),("d",1.0),
    ("s",1.8),("a",1.0),("s",1.8),("a",1.0),
    ("w",2.5),("d",2.0),("s",2.5),("a",2.0),
]

def run_sweep(state: "MacroState", mv: "MovementEngine"):
    log.info("[SWEEP] 시작")
    idx = 0
    while not stopped(state):
        d, t = SWEEP_PAT[idx]
        mv.move(d, mv.ad.vary_speed(t))
        idx = (idx + 1) % len(SWEEP_PAT)
        if idx == 0:
            state.add_cycle()
            _progress(state, "SWEEP")
        mv.human_pause(0.05, 0.15)


# ══════════════════════════════════════════════════════════
# SPIRAL — 나선형 확장
# ══════════════════════════════════════════════════════════

def run_spiral(state: "MacroState", mv: "MovementEngine"):
    log.info("[SPIRAL] 시작")
    max_r  = state.cfg["spiral_max_radius"]
    radius = 0.4
    dirs   = ["w", "d", "s", "a"]
    while not stopped(state):
        for d in dirs:
            mv.move(d, mv.ad.vary_speed(radius))
            if stopped(state): return
        radius = min(radius + 0.15, max_r)
        state.add_cycle()
        if state.stats.cycles % 8 == 0:
            radius = 0.4
            log.info("[SPIRAL] 반경 리셋 | 픽업 %d", state.stats.pickups)
        mv.human_pause(0.03, 0.10)


# ══════════════════════════════════════════════════════════
# GRID — 격자 패턴 정밀 수집
# ══════════════════════════════════════════════════════════

def run_grid(state: "MacroState", mv: "MovementEngine"):
    cols = state.cfg["grid_cols"]
    rows = state.cfg["grid_rows"]
    log.info("[GRID] 시작 (%dx%d)", cols, rows)
    step = state.cfg["step_time"]
    while not stopped(state):
        for r in range(rows):
            lr = "d" if r % 2 == 0 else "a"
            for _ in range(cols):
                mv.move(lr, mv.ad.vary_speed(step))
                if stopped(state): return
            if r < rows - 1:
                mv.move("s", mv.ad.vary_speed(step * 0.7))
                if stopped(state): return
        # 원점 복귀
        mv.move("w", mv.ad.vary_speed(step * rows * 0.7))
        mv.move("a" if cols % 2 == 0 else "d", mv.ad.vary_speed(step * cols * 0.5))
        state.add_cycle()
        _progress(state, "GRID")


# ══════════════════════════════════════════════════════════
# RANDOM — 봇 감지 우회 랜덤 이동
# ══════════════════════════════════════════════════════════

def run_random(state: "MacroState", mv: "MovementEngine"):
    log.info("[RANDOM] 시작")
    prev = None
    dirs = ["w", "a", "s", "d"]
    while not stopped(state):
        choices = [d for d in dirs if d != OPPOSITE.get(prev)]
        d = random.choice(choices)
        prev = d
        t = random.uniform(0.4, 2.4)
        mv.move(d, mv.ad.vary_speed(t))
        # 가끔 제자리 연속 픽업
        if random.random() < 0.28:
            mv.burst_interact(random.randint(2, 6))
        state.add_cycle()
        mv.human_pause(0.04, mv.ad.jitter(0.22))


# ══════════════════════════════════════════════════════════
# VISION — 화면 색상 감지 추적
# ══════════════════════════════════════════════════════════

def run_vision(state: "MacroState", mv: "MovementEngine", ve: "VisionEngine"):
    log.info("[VISION] 화면 감지 모드 시작")
    import keyboard as kb
    last_scan = 0
    last_pick = time.time()
    last_jump = time.time()
    holding   = None
    ii        = state.cfg["interact_interval"]
    ji        = state.cfg["jump_interval"]
    si        = state.cfg["vision_scan_interval"]

    while not stopped(state):
        now = time.time()

        # F키 픽업
        if now - last_pick >= mv.ad.jitter(ii):
            kb.press_and_release("f")
            state.add_pickup()
            last_pick = now

        # 점프
        if ji > 0 and now - last_jump >= mv.ad.jitter(ji):
            kb.press_and_release("space")
            last_jump = now

        # 스캔
        if now - last_scan >= si:
            last_scan = now
            det = ve.scan()
            if holding:
                try: kb.release(holding)
                except: pass
                holding = None

            if det:
                kb.press(det.direction_hint)
                holding = det.direction_hint
                with state._lock:
                    state.stats.detected += 1
                    state.stats.cycles  += 1
                log.info("[VISION] %s 감지 (신뢰도 %.2f) → %s",
                         det.name, det.confidence, det.direction_hint)
                # 희귀 아이템 알림
                if det.name in ("rare_purple", "red_rare") and state.cfg.get("beep_on_rare"):
                    try:
                        from .dashboard import play_beep
                        play_beep(1500, 300)
                        state.stats.rare_detected += 1
                    except Exception:
                        pass
            else:
                d = random.choice(["w","a","s","d"])
                mv.move(d, mv.ad.vary_speed(0.7))
                state.add_cycle()

        time.sleep(0.04)

    if holding:
        try: kb.release(holding)
        except: pass


# ══════════════════════════════════════════════════════════
# SMART — VISION + SWEEP 자동 전환 혼합 모드
# ══════════════════════════════════════════════════════════

def run_smart(state: "MacroState", mv: "MovementEngine", ve: "VisionEngine"):
    """
    SMART 모드:
    - Vision으로 감지 성공 시 → Vision 추적
    - 30초 이상 감지 없으면 → SWEEP으로 전환하여 새 구역 탐색
    - 아이템 발견 → 다시 Vision으로 전환
    """
    log.info("[SMART] 하이브리드 모드 시작")
    import keyboard as kb

    VISION_MODE, SWEEP_MODE = "VISION", "SWEEP"
    sub_mode       = VISION_MODE
    last_detection = time.time()
    TIMEOUT        = 30.0

    sweep_idx = 0
    last_pick = time.time()
    last_jump = time.time()
    holding   = None
    ii = state.cfg["interact_interval"]
    ji = state.cfg["jump_interval"]
    si = state.cfg["vision_scan_interval"]
    last_scan = 0

    while not stopped(state):
        now = time.time()

        # 공통: F키 + 점프
        if now - last_pick >= mv.ad.jitter(ii):
            kb.press_and_release("f")
            state.add_pickup()
            last_pick = now
        if ji > 0 and now - last_jump >= mv.ad.jitter(ji):
            kb.press_and_release("space")
            last_jump = now

        if sub_mode == VISION_MODE:
            if now - last_scan >= si:
                last_scan = now
                det = ve.scan()
                if holding:
                    try: kb.release(holding)
                    except: pass
                    holding = None
                if det:
                    kb.press(det.direction_hint)
                    holding = det.direction_hint
                    last_detection = now
                    state.stats.detected += 1
                    state.stats.cycles   += 1
                else:
                    d = random.choice(["w","a","s","d"])
                    mv.move(d, mv.ad.vary_speed(0.6))
                    state.add_cycle()

                # 30초 감지 없으면 SWEEP 전환
                if now - last_detection > TIMEOUT:
                    if holding:
                        try: kb.release(holding)
                        except: pass
                        holding = None
                    sub_mode = SWEEP_MODE
                    log.info("[SMART] 감지 없음 → SWEEP 전환")
            time.sleep(0.04)

        else:  # SWEEP_MODE
            if holding:
                try: kb.release(holding)
                except: pass
                holding = None
            d, t = SWEEP_PAT[sweep_idx]
            mv.move(d, mv.ad.vary_speed(t))
            sweep_idx = (sweep_idx + 1) % len(SWEEP_PAT)
            state.add_cycle()

            # Vision으로 복귀 시도
            det = ve.scan()
            if det:
                last_detection = time.time()
                sub_mode = VISION_MODE
                log.info("[SMART] 아이템 감지 → VISION 복귀")
