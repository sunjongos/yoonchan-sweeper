"""
╔══════════════════════════════════════════════════════════╗
║          AlphaSweeper v2.0  —  알파스위퍼                ║
║          Sol's RNG 전용 하네스 모드 매크로               ║
║          직접 제작 (악성코드 없는 안전한 버전)           ║
╚══════════════════════════════════════════════════════════╝

모드:
  SWEEP    — 맵 체계적 순회 (기본)
  SPIRAL   — 나선형 이동 (커버리지 극대화)
  GRID     — 격자 패턴 (정밀 수집)
  RANDOM   — 랜덤 이동 (봇 감지 회피)
  VISION   — 화면 색상 감지로 아이템 추적 (최고급)

단축키:
  F9       — 매크로 시작/중지 토글
  F8       — 모드 순환 전환
  F7       — 통계 출력
  F10      — 종료
"""

import pyautogui
import keyboard
import time
import threading
import sys
import random
import json
import os
import logging
from datetime import datetime, timedelta
from collections import deque

try:
    from PIL import ImageGrab, Image
    import numpy as np
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

# ══════════════════════════════════════════════════════════
#  설정 파일 로드 / 기본값
# ══════════════════════════════════════════════════════════

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "alphasweeper_config.json")

DEFAULT_CONFIG = {
    "mode": "SWEEP",             # SWEEP / SPIRAL / GRID / RANDOM / VISION
    "interact_interval": 0.25,   # F키 누르는 주기 (초)
    "jump_interval": 1.2,        # 점프 주기 (초) — 0이면 비활성화
    "step_base": 1.0,            # 기본 이동 시간 (초)
    "anti_afk": True,            # 로블록스 AFK 킥 방지
    "anti_afk_interval": 120,    # AFK 방지 동작 주기 (초)
    "random_jitter": True,       # 타이밍에 랜덤 변동 추가 (봇 감지 회피)
    "jitter_range": 0.1,         # 지터 최대 범위 (초)
    "failsafe": True,            # 마우스 좌상단 이동시 비상 정지
    "log_to_file": True,         # 로그 파일 저장
    "sound_alert": False,        # 소리 알림 (Windows only)

    # VISION 모드: 아이템 색상 (HSV 범위)
    "vision": {
        "enabled": True,
        "scan_interval": 0.5,       # 화면 스캔 주기 (초)
        # 알/아이템 색상 범위 (RGB) — Sol's RNG 기준
        "target_colors": [
            {"name": "egg_glow", "r": [200, 255], "g": [200, 255], "b": [100, 200]},  # 황금빛 알
            {"name": "rare_aura", "r": [150, 230], "g": [50, 150],  "b": [200, 255]}, # 보라빛 레어
            {"name": "item_white","r": [220, 255], "g": [220, 255], "b": [220, 255]}, # 흰색 아이템
        ],
        "min_pixel_count": 30,      # 최소 감지 픽셀 수
        "screen_region": None,      # None = 전체 화면, [x,y,w,h] = 특정 영역
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            # 기본값 위에 사용자 설정 덮어씌우기
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(user_cfg)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


CONFIG = load_config()

# ══════════════════════════════════════════════════════════
#  로깅
# ══════════════════════════════════════════════════════════

log_handlers = [logging.StreamHandler(sys.stdout)]
if CONFIG.get("log_to_file"):
    log_dir = os.path.dirname(__file__)
    log_file = os.path.join(log_dir, f"alphasweeper_{datetime.now():%Y%m%d}.log")
    log_handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=log_handlers,
)
logger = logging.getLogger("AlphaSweeper")

# ══════════════════════════════════════════════════════════
#  전역 상태
# ══════════════════════════════════════════════════════════

class MacroState:
    running = False
    mode = CONFIG["mode"]
    stop_event = threading.Event()
    stats = {
        "session_start": None,
        "cycles": 0,
        "pickups": 0,
        "items_detected": 0,
        "anti_afk_triggers": 0,
        "pickup_rate_history": deque(maxlen=60),  # 분당 픽업 기록
    }
    lock = threading.Lock()

state = MacroState()
MODES = ["SWEEP", "SPIRAL", "GRID", "RANDOM", "VISION"]

# ══════════════════════════════════════════════════════════
#  유틸리티
# ══════════════════════════════════════════════════════════

def jitter(base: float) -> float:
    """랜덤 지터 추가 (봇 감지 회피)"""
    if not CONFIG["random_jitter"]:
        return base
    delta = random.uniform(-CONFIG["jitter_range"], CONFIG["jitter_range"])
    return max(0.05, base + delta)


def safe_press(key: str, duration: float = 0.05):
    """키를 duration초 동안 누름 (예외 안전)"""
    try:
        keyboard.press(key)
        time.sleep(duration)
        keyboard.release(key)
    except Exception as e:
        logger.debug(f"safe_press 오류 ({key}): {e}")


def do_interact():
    """F키 아이템 픽업"""
    keyboard.press_and_release("f")
    with state.lock:
        state.stats["pickups"] += 1


def do_jump():
    """스페이스 점프"""
    keyboard.press_and_release("space")


def release_all_keys():
    """모든 이동 키 해제"""
    for k in ["w", "a", "s", "d"]:
        try:
            keyboard.release(k)
        except Exception:
            pass


def move_with_actions(direction: str, duration: float):
    """이동하면서 F/점프 동시 처리"""
    last_interact = time.time()
    last_jump = time.time()

    keyboard.press(direction)
    start = time.time()

    try:
        while time.time() - start < duration:
            if state.stop_event.is_set():
                break

            now = time.time()

            if now - last_interact >= jitter(CONFIG["interact_interval"]):
                do_interact()
                last_interact = now

            ji = CONFIG["jump_interval"]
            if ji > 0 and now - last_jump >= jitter(ji):
                do_jump()
                last_jump = now

            time.sleep(0.04)
    finally:
        keyboard.release(direction)


# ══════════════════════════════════════════════════════════
#  Anti-AFK 시스템
# ══════════════════════════════════════════════════════════

def anti_afk_loop():
    """별도 스레드: AFK 킥 방지"""
    logger.info("[Anti-AFK] 시작")
    while not state.stop_event.is_set():
        interval = CONFIG["anti_afk_interval"]
        for _ in range(int(interval * 10)):
            if state.stop_event.is_set():
                return
            time.sleep(0.1)

        if not state.running:
            continue

        # AFK 방지 동작: 마우스 미세 이동 + 점프
        cur_x, cur_y = pyautogui.position()
        pyautogui.moveRel(1, 0, duration=0.1)
        pyautogui.moveRel(-1, 0, duration=0.1)
        keyboard.press_and_release("space")

        with state.lock:
            state.stats["anti_afk_triggers"] += 1

        logger.debug("[Anti-AFK] 동작 실행")


# ══════════════════════════════════════════════════════════
#  SWEEP 모드 패턴
# ══════════════════════════════════════════════════════════

SWEEP_PATTERN = [
    ("w", 2.0), ("d", 1.2), ("w", 2.0),
    ("a", 2.4), ("w", 2.0), ("d", 1.2),
    ("s", 4.0), ("a", 1.2), ("s", 2.0),
    ("d", 2.4), ("s", 2.0), ("a", 1.2),
]

def run_sweep():
    logger.info("[SWEEP] 맵 순회 모드 시작")
    idx = 0
    while not state.stop_event.is_set():
        direction, base_dur = SWEEP_PATTERN[idx]
        move_with_actions(direction, jitter(base_dur))

        idx = (idx + 1) % len(SWEEP_PATTERN)
        if idx == 0:
            with state.lock:
                state.stats["cycles"] += 1
            logger.info(f"[SWEEP] 순회 {state.stats['cycles']}회 완료 | 픽업 {state.stats['pickups']}회")

        time.sleep(jitter(0.1))


# ══════════════════════════════════════════════════════════
#  SPIRAL 모드
# ══════════════════════════════════════════════════════════

def run_spiral():
    """나선형 이동 — 커버리지 극대화"""
    logger.info("[SPIRAL] 나선형 모드 시작")
    radius = 0.5
    while not state.stop_event.is_set():
        for direction in ["w", "d", "s", "a"]:
            move_with_actions(direction, jitter(radius))
            if state.stop_event.is_set():
                return
            time.sleep(0.05)

        radius = min(radius + 0.1, 3.0)  # 점점 넓은 범위로

        with state.lock:
            state.stats["cycles"] += 1

        if state.stats["cycles"] % 10 == 0:
            # 10 사이클마다 원점 복귀 시도
            radius = 0.5
            logger.info(f"[SPIRAL] 원점 복귀 | 총 픽업 {state.stats['pickups']}회")

        time.sleep(jitter(0.05))


# ══════════════════════════════════════════════════════════
#  GRID 모드
# ══════════════════════════════════════════════════════════

GRID_SIZE = 4  # 격자 크기

def run_grid():
    """격자 패턴 — 빠짐없이 수집"""
    logger.info("[GRID] 격자 패턴 모드 시작")
    while not state.stop_event.is_set():
        for row in range(GRID_SIZE):
            direction = "d" if row % 2 == 0 else "a"
            for col in range(GRID_SIZE):
                move_with_actions(direction, jitter(1.0))
                if state.stop_event.is_set():
                    return

            if row < GRID_SIZE - 1:
                move_with_actions("w", jitter(1.0))
                if state.stop_event.is_set():
                    return

        # 원점 복귀
        move_with_actions("s", jitter(GRID_SIZE * 1.0))
        move_with_actions("a", jitter(GRID_SIZE * 0.5))

        with state.lock:
            state.stats["cycles"] += 1
        logger.info(f"[GRID] 격자 스캔 {state.stats['cycles']}회 완료 | 픽업 {state.stats['pickups']}회")


# ══════════════════════════════════════════════════════════
#  RANDOM 모드
# ══════════════════════════════════════════════════════════

def run_random():
    """랜덤 이동 — 봇 감지 우회"""
    logger.info("[RANDOM] 랜덤 이동 모드 시작")
    dirs = ["w", "a", "s", "d"]
    prev = None

    while not state.stop_event.is_set():
        # 이전과 반대 방향 제외 (벽 끼임 방지)
        opposite = {"w": "s", "s": "w", "a": "d", "d": "a"}
        choices = [d for d in dirs if d != opposite.get(prev)]
        direction = random.choice(choices)
        prev = direction

        duration = random.uniform(0.4, 2.2)
        move_with_actions(direction, jitter(duration))

        with state.lock:
            state.stats["cycles"] += 1

        # 가끔 제자리 상호작용
        if random.random() < 0.3:
            for _ in range(random.randint(2, 5)):
                do_interact()
                time.sleep(jitter(0.15))

        time.sleep(jitter(random.uniform(0.05, 0.3)))


# ══════════════════════════════════════════════════════════
#  VISION 모드 (화면 색상 감지)
# ══════════════════════════════════════════════════════════

def scan_screen_for_items():
    """화면에서 아이템 색상 감지 → 위치 반환"""
    if not VISION_AVAILABLE:
        return None

    try:
        region = CONFIG["vision"].get("screen_region")
        if region:
            img = ImageGrab.grab(bbox=region)
            offset_x, offset_y = region[0], region[1]
        else:
            img = ImageGrab.grab()
            offset_x, offset_y = 0, 0

        arr = np.array(img)
        h, w = arr.shape[:2]

        for color_def in CONFIG["vision"]["target_colors"]:
            r_range = color_def["r"]
            g_range = color_def["g"]
            b_range = color_def["b"]

            mask = (
                (arr[:, :, 0] >= r_range[0]) & (arr[:, :, 0] <= r_range[1]) &
                (arr[:, :, 1] >= g_range[0]) & (arr[:, :, 1] <= g_range[1]) &
                (arr[:, :, 2] >= b_range[0]) & (arr[:, :, 2] <= b_range[1])
            )

            pixel_count = np.sum(mask)
            if pixel_count >= CONFIG["vision"]["min_pixel_count"]:
                # 감지된 픽셀의 중심 계산
                ys, xs = np.where(mask)
                cx = int(np.mean(xs)) + offset_x
                cy = int(np.mean(ys)) + offset_y
                return (cx, cy, color_def["name"], pixel_count)

    except Exception as e:
        logger.debug(f"[VISION] 스캔 오류: {e}")

    return None


def run_vision():
    """VISION 모드: 아이템 감지 후 이동"""
    if not VISION_AVAILABLE:
        logger.warning("[VISION] numpy/pillow 없어서 RANDOM으로 대체")
        run_random()
        return

    logger.info("[VISION] 화면 감지 모드 시작")
    last_scan = 0
    last_interact = time.time()
    last_jump = time.time()
    holding_dir = None

    while not state.stop_event.is_set():
        now = time.time()

        # F키 상호작용
        if now - last_interact >= jitter(CONFIG["interact_interval"]):
            do_interact()
            last_interact = now

        # 점프
        ji = CONFIG["jump_interval"]
        if ji > 0 and now - last_jump >= jitter(ji):
            do_jump()
            last_jump = now

        # 화면 스캔
        if now - last_scan >= CONFIG["vision"]["scan_interval"]:
            result = scan_screen_for_items()
            last_scan = now

            if result:
                cx, cy, name, count = result
                screen_w, screen_h = pyautogui.size()
                screen_cx = screen_w // 2
                screen_cy = screen_h // 2

                dx = cx - screen_cx
                dy = cy - screen_cy

                # 화면 중심 기준으로 이동 방향 결정
                if holding_dir:
                    keyboard.release(holding_dir)
                    holding_dir = None

                if abs(dx) > abs(dy):
                    new_dir = "d" if dx > 0 else "a"
                else:
                    new_dir = "s" if dy > 0 else "w"

                keyboard.press(new_dir)
                holding_dir = new_dir

                with state.lock:
                    state.stats["items_detected"] += 1

                logger.info(f"[VISION] {name} 감지 ({count}px) → {new_dir} 방향 이동")
            else:
                # 아이템 없으면 랜덤 이동
                if holding_dir:
                    keyboard.release(holding_dir)
                    holding_dir = None

                direction = random.choice(["w", "a", "s", "d"])
                move_with_actions(direction, jitter(0.8))

                with state.lock:
                    state.stats["cycles"] += 1

        time.sleep(0.04)

    if holding_dir:
        try:
            keyboard.release(holding_dir)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  매크로 메인 스레드
# ══════════════════════════════════════════════════════════

MODE_RUNNERS = {
    "SWEEP":  run_sweep,
    "SPIRAL": run_spiral,
    "GRID":   run_grid,
    "RANDOM": run_random,
    "VISION": run_vision,
}

def macro_main():
    state.stats["session_start"] = time.time()
    state.stats["cycles"] = 0
    state.stats["pickups"] = 0
    state.stats["items_detected"] = 0

    logger.info(f"▶ AlphaSweeper 시작 — 모드: {state.mode}")

    # Anti-AFK 스레드
    if CONFIG["anti_afk"]:
        afk_thread = threading.Thread(target=anti_afk_loop, daemon=True)
        afk_thread.start()

    try:
        runner = MODE_RUNNERS.get(state.mode, run_sweep)
        runner()
    except Exception as e:
        logger.error(f"매크로 오류: {e}", exc_info=True)
    finally:
        release_all_keys()
        elapsed = time.time() - state.stats["session_start"]
        print_stats(elapsed)
        state.running = False


def print_stats(elapsed=None):
    if elapsed is None and state.stats["session_start"]:
        elapsed = time.time() - state.stats["session_start"]
    elapsed = elapsed or 0

    rate = state.stats["pickups"] / max(elapsed / 60, 0.01)
    print("\n" + "─" * 50)
    print(f"  AlphaSweeper 통계")
    print("─" * 50)
    print(f"  모드           : {state.mode}")
    print(f"  실행 시간      : {timedelta(seconds=int(elapsed))}")
    print(f"  총 픽업        : {state.stats['pickups']}회")
    print(f"  사이클         : {state.stats['cycles']}회")
    print(f"  픽업 속도      : {rate:.1f}회/분")
    if VISION_AVAILABLE:
        print(f"  아이템 감지    : {state.stats['items_detected']}회")
    print(f"  Anti-AFK 동작  : {state.stats['anti_afk_triggers']}회")
    print("─" * 50 + "\n")


# ══════════════════════════════════════════════════════════
#  단축키 핸들러
# ══════════════════════════════════════════════════════════

def on_toggle():
    """F9: 시작/중지"""
    if not state.running:
        state.running = True
        state.stop_event.clear()
        t = threading.Thread(target=macro_main, daemon=True)
        t.start()
        print(f"\n{'═'*50}")
        print(f"  ▶ 매크로 ON — 모드: {state.mode}")
        print(f"{'═'*50}")
    else:
        print("  ⏸ 중지 중...")
        state.stop_event.set()
        state.running = False


def on_mode_cycle():
    """F8: 모드 순환"""
    was_running = state.running
    if was_running:
        state.stop_event.set()
        state.running = False
        time.sleep(0.3)

    idx = MODES.index(state.mode)
    state.mode = MODES[(idx + 1) % len(MODES)]
    print(f"\n  🔄 모드 변경 → {state.mode}")

    if was_running:
        state.stop_event.clear()
        state.running = True
        t = threading.Thread(target=macro_main, daemon=True)
        t.start()


def on_stats():
    """F7: 통계 출력"""
    print_stats()


def on_quit():
    """F10: 종료"""
    if state.running:
        state.stop_event.set()
        state.running = False
        time.sleep(0.3)
    logger.info("AlphaSweeper 종료")
    save_config(CONFIG)
    sys.exit(0)


# ══════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║    ___  _     _           ____                           ║
║   / _ \| |   | |         / ___|_      _____  ___ _ __   ║
║  / /_\ \ |   | |_| |__  / /  _\ \ /\ / / _ \/ _ \ '_ \ ║
║  |  _  | |   | |_| '_ \ \ \_\ \ V  V /  __/  __/ |_) | ║
║  |_| |_|_|   |_(_)_| |_| \____/ \_/\_/ \___|\___| .__/ ║
║  알파스위퍼 v2.0   Sol's RNG 전용 하네스 매크로   |_|   ║
╚══════════════════════════════════════════════════════════╝
"""

def print_help():
    print(BANNER)
    print("  단축키")
    print("  ──────────────────────────────────────────────")
    print("  F9   매크로 시작 / 중지 토글")
    print("  F8   모드 순환 (SWEEP→SPIRAL→GRID→RANDOM→VISION)")
    print("  F7   실시간 통계 출력")
    print("  F10  프로그램 완전 종료")
    print()
    print(f"  현재 모드  : {state.mode}")
    print(f"  Vision     : {'사용 가능' if VISION_AVAILABLE else '불가 (pip install numpy)'}")
    print(f"  Anti-AFK   : {'ON' if CONFIG['anti_afk'] else 'OFF'}")
    print(f"  Jitter     : {'ON' if CONFIG['random_jitter'] else 'OFF'}")
    print(f"  Failsafe   : {'ON' if CONFIG['failsafe'] else 'OFF'}")
    print()
    print("  ⚠️  Sol's RNG 창을 클릭해서 포커스한 뒤 F9 누르세요")
    print("  ⚠️  Failsafe: 마우스를 화면 좌상단 이동 시 즉시 정지")
    print("  ─────────────────────────────────────────────")
    print()


def main():
    pyautogui.FAILSAFE = CONFIG["failsafe"]

    print_help()
    save_config(CONFIG)  # 설정 파일 생성

    keyboard.add_hotkey("f9",  on_toggle,     suppress=False)
    keyboard.add_hotkey("f8",  on_mode_cycle, suppress=False)
    keyboard.add_hotkey("f7",  on_stats,      suppress=False)
    keyboard.add_hotkey("f10", on_quit,       suppress=False)

    logger.info("대기 중... Sol's RNG 창 클릭 후 F9 눌러 시작")

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        on_quit()


if __name__ == "__main__":
    main()
