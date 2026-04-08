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
            kb.press_and_release("e")
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
            kb.press_and_release("e")
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


# ══════════════════════════════════════════════════════════
# BEAST — 최고 효율 비스트 모드 (World Best Practice)
# ══════════════════════════════════════════════════════════

def run_beast(state: "MacroState", mv: "MovementEngine", ve: "VisionEngine"):
    log.info("[BEAST] Strategic Hunter AI (정찰/사냥/대이동) 시작")
    import keyboard as kb
    import pyautogui
    
    ii = state.cfg["interact_interval"]
    ji = state.cfg["jump_interval"]
    
    m_state = "RADAR"  # 상태 머신: RADAR, HUNTING, RELOCATE
    state_start = time.time()
    
    last_pick = time.time()
    last_jump = time.time()
    last_steer = time.time()
    
    # 헬퍼 함수
    def release_w():
        try: kb.release("w")
        except: pass

    def press_w():
        try: kb.press("w")
        except: pass

    while not stopped(state):
        now = time.time()

        # E키 유기적 수확 (공통 - 수시로 타격)
        if now - last_pick >= mv.ad.jitter(ii):
            kb.press_and_release("e")
            state.add_pickup()
            last_pick = now

        # 간헐적 점프 (공통)
        if ji > 0 and now - last_jump >= mv.ad.jitter(ji):
            kb.press_and_release("space")
            last_jump = now

        # ==========================================
        # 1. RADAR (레이더 스캔 모드: 제자리 360도 정찰)
        # ==========================================
        if m_state == "RADAR":
            release_w() # 서서 스캔
            
            found_egg = False
            # 6회로 나누어 화면을 돌리며 360도 스캔 (가장 중요: 실시간 낚아채기 대응)
            for _ in range(6):
                if stopped(state): break
                det = ve.scan()
                if det:
                    if abs(det.dx) > 15 or abs(det.dy) > 15:
                        pyautogui.FAILSAFE = False
                        pyautogui.mouseDown(button='right')
                        duration = max(0.2, min(0.35, abs(det.dx) / 1000.0))
                        pyautogui.moveRel(int(det.dx * 0.5), int(det.dy * 0.4), duration=duration, tween=pyautogui.easeInOutQuad)
                        pyautogui.mouseUp(button='right')
                        pyautogui.FAILSAFE = state.cfg.get("failsafe", True)
                    
                    found_egg = True
                    m_state = "HUNTING"
                    state_start = time.time()
                    state.stats.detected += 1
                    state.stats.cycles += 1
                    press_w()
                    break
                else:
                    # 알이 없으면 ~60도 고개 돌림
                    mv.smooth_look(max_offset=280, duration=0.3)
                    time.sleep(0.05)
            
            # 스캔을 다 돌려도 알이 없으면 그 구역을 버리고 대이동
            if not found_egg and not stopped(state):
                log.info("💨 [RADAR] 타겟 없음. 바다 낙사 방지를 위해 방향 전환 후 대이동!")
                # 바다(맵 가장자리)로 뛰는 것을 막기 위해 90~180도 가량 크게 회전
                mv.smooth_look(max_offset=random.choice([-600, -800, 600, 800]), duration=0.5)
                m_state = "RELOCATE"
                state_start = time.time()
                press_w()

        # ==========================================
        # 2. HUNTING (목표 포착 및 사냥/마무리 모드)
        # ==========================================
        elif m_state == "HUNTING":
            # 표적을 향해 달리는 시간. 약 2.5~4.0초 뒤면 먹었다고 간주
            if now - state_start > random.uniform(2.5, 4.0):
                m_state = "RADAR"
                continue
                
            # W키 씹힘 방지
            if now - last_steer > 0.8:
                release_w(); press_w()
                last_steer = now

            # 사냥 중 벽에 막히면 (Anti-Stuck 위글 발동)
            if ve.is_stuck():
                log.warning("🚨 [HUNTING] 전진 중 벽 막힘. 능동 회피(Wiggle) 기동 후 스캔 복귀!")
                release_w()
                kb.press("s")
                # 단순 후진이 아닌 좌/우 대각선 스텝 혼합
                side_step = random.choice(["a", "d"])
                kb.press(side_step)
                for _ in range(2): 
                    kb.press_and_release("space")
                    time.sleep(0.3)
                kb.release("s")
                kb.release(side_step)
                mv.smooth_look(max_offset=random.choice([-600, 600]), duration=0.6)
                m_state = "RADAR"
            
            time.sleep(0.05)

        # ==========================================
        # 3. RELOCATE (새 구역 개척/거점 강제 이동)
        # ==========================================
        elif m_state == "RELOCATE":
            # 2.0~4.0초간 전진 (맵이 좁으므로 5초 이상 직진 시 바다에 빠져 죽음)
            if now - state_start > random.uniform(2.0, 4.0):
                log.info("🏁 [RELOCATE] 새 거점 도착. 정찰(Radar) 재개.")
                m_state = "RADAR"
                continue
            
            if now - last_steer > 0.8:
                release_w(); press_w()
                last_steer = now

            # 지형물을 잘 타고 넘기 위해 점프를 강제로 더 자주 섞음
            if now - last_jump > 1.2:
                kb.press_and_release("space")
                last_jump = now

            # 개척 중 막히면 비껴가도록 큼직하게 꺾는 능동 회피(Wiggle)
            if ve.is_stuck():
                log.warning("🚨 [RELOCATE] 개척 중 벽 막힘. Wiggle 회피 기동 발동!")
                release_w()
                kb.press("s")
                side_step = random.choice(["a", "d"])
                kb.press(side_step)
                kb.press_and_release("space")
                time.sleep(0.4)
                kb.release("s")
                kb.release(side_step)
                mv.smooth_look(max_offset=random.choice([-800, 800]), duration=0.7)
                press_w()
                
            time.sleep(0.05)

    release_w()

