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
║      S W E E P E R   v4.0  WORLD-CLASS EDITION              ║
║      by  yoonchan  ·  harness mode  ·  beast mode            ║
╚═══════════════════════════════════════════════════════════════╝

모드:
  SWEEP   맵 체계적 순회 (기본)
  SPIRAL  나선형 확장 (커버리지 최대)
  GRID    격자 정밀 수집
  RANDOM  랜덤 이동 (봇 감지 우회)
  VISION  화면 색상 감지 아이템 추적
  SMART   VISION + SWEEP 자동 전환 혼합 ★최고급★
  BEAST   World Best Practice 인간형 하드코어 모드 🔥

단축키:
  F9   시작/중지  |  F8 모드 전환  |  F7 통계
  F6   설정 출력  |  F5 대시보드 열기  |  F10 종료

웹 대시보드: http://localhost:7777
"""

# ── 임포트 ──────────────────────────────────────────────────
import sys, os, time, threading, logging
from datetime import timedelta

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# engine 패키지를 경로에 추가
_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

import pyautogui
import keyboard

from engine.state   import MacroState, save_cfg, MODES
from engine.antiafk import AntiAFKWorker

# 선택적 엔진 (패키지 존재 시 로드)
def _try_import(mod_path, cls_name):
    try:
        import importlib
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)
    except Exception as e:
        return None

MovementEngine = _try_import("engine.movement", "MovementEngine")
VisionEngine   = _try_import("engine.vision",   "VisionEngine")
Dashboard      = _try_import("engine.dashboard", "Dashboard")

# ── ANSI 색상 ───────────────────────────────────────────────
class C:
    R="\033[0m";BD="\033[1m";DM="\033[2m"
    RED="\033[91m";GRN="\033[92m";YLW="\033[93m"
    BLU="\033[94m";MGT="\033[95m";CYN="\033[96m";WHT="\033[97m"

def cp(msg, color=C.WHT, bold=False):
    print(f"{C.BD if bold else ''}{color}{msg}{C.R}")

# ── 로거 ────────────────────────────────────────────────────
def _setup_logger(cfg):
    from datetime import datetime
    handlers = [logging.StreamHandler(sys.stdout)]
    if cfg.get("log_file"):
        lf = os.path.join(_BASE, f"yoonchan_{datetime.now():%Y%m%d}.log")
        handlers.append(logging.FileHandler(lf, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )

# ── 공유 상태 ────────────────────────────────────────────────
state = MacroState()
_setup_logger(state.cfg)
log = logging.getLogger("YoonchanSweeper")

# ── 런타임 엔진 인스턴스 ─────────────────────────────────────
_mv = None   # MovementEngine
_ve = None   # VisionEngine
_db = None   # Dashboard

def _init_engines():
    global _mv, _ve, _db
    if MovementEngine:
        _mv = MovementEngine(state.cfg)
        log.info("MovementEngine 로드 완료")
    else:
        _mv = _FallbackMovement(state.cfg)
        log.warning("MovementEngine 없음 → 내장 폴백 사용")

    if VisionEngine:
        _ve = VisionEngine(state.cfg)
        log.info("VisionEngine 로드 완료")
    else:
        _ve = _FallbackVision()
        log.warning("VisionEngine 없음 → 기본 스캔 사용")

    if Dashboard and state.cfg.get("dashboard"):
        _db = Dashboard(state)
        _db.start()
        log.info("대시보드 시작 → http://localhost:%d", state.cfg["dashboard_port"])


# ── 폴백 구현 (engine 모듈 없을 때) ──────────────────────────
class _FallbackMovement:
    """engine/movement.py 없을 때 사용하는 내장 이동 엔진"""
    def __init__(self, cfg):
        self.cfg = cfg
        from engine.state import MacroState as _
        import random as _r, math as _m
        self._r = _r
        self.ad = self  # AntiDetection 역할도 겸함

    # -- AntiDetection interface --
    def jitter(self, base: float) -> float:
        if not self.cfg["jitter"]: return base
        import random
        return max(0.03, base + random.gauss(0, self.cfg["jitter_max"] * 0.5))

    def vary_speed(self, base: float) -> float:
        return self.jitter(base)

    # -- MovementEngine interface --
    def move(self, direction: str, duration: float,
             do_interact: bool = True, do_jump: bool = True):
        cfg = self.cfg
        last_pick = time.time()
        last_jump = time.time()
        keyboard.press(direction)
        t0 = time.time()
        try:
            while time.time() - t0 < duration:
                if state.stop.is_set(): break
                now = time.time()
                if do_interact and now - last_pick >= self.jitter(cfg["interact_interval"]):
                    keyboard.press_and_release("e")
                    state.add_pickup()
                    last_pick = now
                ji = cfg["jump_interval"]
                if do_jump and ji > 0 and now - last_jump >= self.jitter(ji):
                    keyboard.press_and_release("space")
                    last_jump = now
                time.sleep(0.04)
        finally:
            keyboard.release(direction)

    def burst_interact(self, count: int = 3):
        for _ in range(count):
            keyboard.press_and_release("e")
            state.add_pickup()
            time.sleep(self.jitter(0.12))

    def human_pause(self, mn: float = 0.1, mx: float = 0.4):
        import random
        time.sleep(random.uniform(mn, mx))

    def release_all(self):
        for k in "wasd":
            try: keyboard.release(k)
            except: pass


class _FallbackVision:
    """engine/vision.py 없을 때 사용하는 기본 스캐너"""
    def __init__(self):
        self._ok = False
        try:
            from PIL import ImageGrab
            import numpy as np
            self._ok = True
        except ImportError:
            pass

    def scan(self):
        if not self._ok: return None
        try:
            from PIL import ImageGrab
            import numpy as np
            import pyautogui as _pg
            arr = np.array(ImageGrab.grab())
            sw, sh = _pg.size()
            for c in state.cfg["vision_colors"]:
                mask = (
                    (arr[:,:,0]>=c["r"][0])&(arr[:,:,0]<=c["r"][1])&
                    (arr[:,:,1]>=c["g"][0])&(arr[:,:,1]<=c["g"][1])&
                    (arr[:,:,2]>=c["b"][0])&(arr[:,:,2]<=c["b"][1])
                )
                cnt = int(np.sum(mask))
                if cnt >= state.cfg["vision_min_pixels"]:
                    ys, xs = np.where(mask)
                    cx, cy = int(xs.mean()), int(ys.mean())
                    dx, dy = cx - sw//2, cy - sh//2
                    nd = ("d" if dx>0 else "a") if abs(dx)>abs(dy) else ("s" if dy>0 else "w")
                    class _D:
                        name="item"; confidence=0.8; direction_hint=nd; pixel_count=cnt
                    return _D()
        except Exception:
            pass
        return None

    def is_disconnected(self): return False
    def is_loading(self): return False


# ── 매크로 러너 선택 ─────────────────────────────────────────
def _get_runner(mode: str):
    from engine.modes import (run_sweep, run_spiral, run_grid,
                               run_random, run_vision, run_smart, run_beast)
    runners = {
        "SWEEP":  lambda: run_sweep(state, _mv),
        "SPIRAL": lambda: run_spiral(state, _mv),
        "GRID":   lambda: run_grid(state, _mv),
        "RANDOM": lambda: run_random(state, _mv),
        "VISION": lambda: run_vision(state, _mv, _ve),
        "SMART":  lambda: run_smart(state, _mv, _ve),
        "BEAST":  lambda: run_beast(state, _mv, _ve),
    }
    return runners.get(mode, runners["SWEEP"])


# ── 매크로 메인 워커 ──────────────────────────────────────────
def _macro_worker():
    state.reset()
    log.info("▶ YoonchanSweeper v4.0 시작 — 모드: %s", state.mode)

    # Anti-AFK
    if state.cfg["anti_afk"]:
        AntiAFKWorker(state, _ve).start()

    try:
        runner = _get_runner(state.mode)
        runner()
    except Exception as e:
        log.error("매크로 오류: %s", e, exc_info=True)
    finally:
        _mv.release_all()
        _print_stats()
        state.running = False
        log.info("■ 매크로 정지")


# ── 통계 출력 ────────────────────────────────────────────────
def _print_stats():
    s    = state.stats
    e    = s.elapsed()
    rpm  = s.rate_per_min()
    r1m  = s.recent_rate(60)
    bar_n = min(int(rpm), 40)
    bar  = "█" * bar_n + "░" * (40 - bar_n)

    cp("\n" + "═"*58, C.CYN, bold=True)
    cp("  YoonchanSweeper v4.0  통계", C.CYN, bold=True)
    cp("═"*58, C.CYN)
    cp(f"  모드          : {state.mode}", C.WHT)
    cp(f"  실행 시간     : {timedelta(seconds=int(e))}", C.WHT)
    cp(f"  총 픽업       : {s.pickups} 회", C.GRN, bold=True)
    cp(f"  사이클        : {s.cycles} 회", C.WHT)
    cp(f"  픽업 속도     : {rpm:.1f}/분  (최근1분: {r1m})", C.YLW)
    cp(f"  [{bar}]", C.GRN)
    cp(f"  아이템 감지   : {s.detected} 회", C.MGT)
    cp(f"  희귀 아이템   : {s.rare_detected} 회", C.MGT, bold=True)
    cp(f"  Anti-AFK      : {s.afk_triggers} 회", C.DM)
    cp(f"  재연결        : {s.reconnects} 회", C.DM)
    cp("═"*58 + "\n", C.CYN)


# ── 단축키 핸들러 ────────────────────────────────────────────
def on_f9():
    if not state.running:
        state.running = True
        state.stop.clear()
        threading.Thread(target=_macro_worker, daemon=True).start()
        cp(f"\n{'═'*50}", C.GRN, bold=True)
        cp(f"  ▶  ON  —  모드: {state.mode}", C.GRN, bold=True)
        cp(f"{'═'*50}\n", C.GRN)
    else:
        cp("  ⏸ 중지 중...", C.YLW)
        state.stop.set()
        state.running = False

def on_f8():
    was = state.running
    if was:
        state.stop.set(); state.running = False; time.sleep(0.35)
    old = state.mode
    state.next_mode()
    cp(f"\n  🔄  {old} → {state.mode}\n", C.CYN, bold=True)
    if was:
        state.stop.clear(); state.running = True
        threading.Thread(target=_macro_worker, daemon=True).start()

def on_f7():
    _print_stats()

def on_f6():
    cp("\n  설정 (yoonchan_config.json)", C.YLW, bold=True)
    for k, v in state.cfg.items():
        if k not in ("vision_colors",):
            cp(f"    {k:<28}: {v}", C.WHT)
    print()

def on_f5():
    import webbrowser
    port = state.cfg.get("dashboard_port", 7777)
    webbrowser.open(f"http://localhost:{port}")
    cp(f"  대시보드 → http://localhost:{port}", C.CYN)

def on_f10():
    cp("\n  YoonchanSweeper 종료 중...", C.RED)
    state.stop.set(); state.running = False
    time.sleep(0.3)
    save_cfg(state.cfg)
    log.info("종료")
    sys.exit(0)


# ── 배너 ────────────────────────────────────────────────────
BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║   ██╗   ██╗ ██████╗  ██████╗ ███╗   ██╗ ██████╗██╗  ██╗     ║
║   ╚██╗ ██╔╝██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║     ║
║    ╚████╔╝ ██║   ██║██║   ██║██╔██╗ ██║██║     ███████║     ║
║     ╚██╔╝  ██║   ██║██║   ██║██║╚██╗██║██║     ██╔══██║     ║
║      ██║   ╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║  ██║     ║
║      ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝     ║
║    S W E E P E R   v4.0   WORLD-CLASS   by yoonchan          ║
╚═══════════════════════════════════════════════════════════════╝
"""

def _print_banner():
    print(C.CYN + C.BD + BANNER + C.R)
    cp("  Sol's RNG 알줍기 World-Class 하네스 매크로", C.WHT, bold=True)
    print()
    cp("  단축키", C.YLW, bold=True)
    print("  " + "─"*48)
    for k, desc in [
        ("F9 ","시작 / 중지"),("F8 ","모드 순환 (SWEEP→SPIRAL→GRID→RANDOM→VISION→SMART→BEAST)"),
        ("F7 ","실시간 통계"),("F6 ","설정 출력"),
        ("F5 ","웹 대시보드 열기"),("F10","완전 종료"),
    ]:
        cp(f"  {k}  {desc}", C.WHT)
    print()
    cp(f"  현재 모드  : {state.mode}", C.YLW, bold=True)
    cp(f"  SMART 모드 : Vision + Sweep 자동 전환 ★", C.MGT)
    cp(f"  BEAST 모드 : World Best Practice 곡선 주행 및 카메라 휙휙 🔥", C.RED)
    cp(f"  Dashboard  : http://localhost:{state.cfg.get('dashboard_port',7777)}", C.CYN)
    cp(f"  Vision     : {'사용 가능' if VisionEngine or True else '불가'}", C.WHT)
    cp(f"  Anti-AFK   : {'ON' if state.cfg['anti_afk'] else 'OFF'}", C.WHT)
    cp(f"  Jitter     : {'ON' if state.cfg['jitter'] else 'OFF'}", C.WHT)
    cp(f"  Failsafe   : ON — 마우스 좌상단 이동 시 비상정지", C.WHT)
    print()
    cp("  ⚠  Sol's RNG 창을 클릭해서 포커스한 뒤 F9 누르세요!", C.YLW, bold=True)
    print()


# ── main ────────────────────────────────────────────────────
def main():
    if sys.platform == "win32":
        os.system("color")   # ANSI 활성화

    pyautogui.FAILSAFE = state.cfg["failsafe"]
    save_cfg(state.cfg)

    _init_engines()
    _print_banner()

    log.info("YoonchanSweeper v4.0 대기 중")

    keyboard.add_hotkey("f9",  on_f9,  suppress=False)
    keyboard.add_hotkey("f8",  on_f8,  suppress=False)
    keyboard.add_hotkey("f7",  on_f7,  suppress=False)
    keyboard.add_hotkey("f6",  on_f6,  suppress=False)
    keyboard.add_hotkey("f5",  on_f5,  suppress=False)
    keyboard.add_hotkey("f10", on_f10, suppress=False)

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        on_f10()


if __name__ == "__main__":
    main()
