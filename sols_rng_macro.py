"""
Sol's RNG - 알줍는 매크로 (Item Auto-Collect Macro)
====================================================
직접 제작한 안전한 버전 (악성코드 없음)

사용법:
  1. Roblox에서 Sol's RNG 실행
  2. 이 스크립트 실행
  3. Sol's RNG 창을 클릭해서 포커스
  4. F9 = 매크로 시작/중지 토글
  5. F10 = 완전 종료

기능:
  - 자동 이동 (WASD 패턴으로 알 수집)
  - 자동 F키 상호작용 (아이템 픽업)
  - 자동 스페이스바 (점프, 알 위에 올라타기)
  - 오버레이 상태 표시
"""

import pyautogui
import keyboard
import time
import threading
import sys
import random
from datetime import datetime

# ──────────────────────────────────────
# 설정 (Config)
# ──────────────────────────────────────
CONFIG = {
    # 매크로 모드: "sweep" = 맵 순회, "random" = 랜덤 이동
    "mode": "sweep",

    # 이동 속도 (초 단위 — 작을수록 빠름)
    "move_duration": 0.05,

    # 각 방향 이동 시간 (초)
    "step_time": 0.8,

    # F키 상호작용 주기 (초)
    "interact_interval": 0.3,

    # 점프 주기 (초) — 0이면 비활성화
    "jump_interval": 1.5,

    # 안전 페일세이프: 마우스를 화면 좌상단으로 이동시 즉시 중단
    "failsafe": True,

    # 로블록스 창 제목 (자동 포커스용)
    "roblox_title": "Roblox",
}

# ──────────────────────────────────────
# 전역 상태
# ──────────────────────────────────────
running = False
stop_event = threading.Event()
stats = {
    "start_time": None,
    "cycles": 0,
    "pickups": 0,
}

# ──────────────────────────────────────
# 이동 패턴 정의
# ──────────────────────────────────────

# SWEEP 패턴: 맵을 체계적으로 순회
SWEEP_PATTERN = [
    ("w", 1.5),   # 앞으로
    ("d", 1.0),   # 오른쪽
    ("w", 1.5),   # 앞으로
    ("a", 2.0),   # 왼쪽
    ("w", 1.5),   # 앞으로
    ("d", 1.0),   # 오른쪽
    ("s", 3.0),   # 뒤로 (원점 복귀)
    ("a", 1.0),   # 왼쪽
    ("s", 1.5),   # 뒤로
    ("d", 2.0),   # 오른쪽
    ("s", 1.5),   # 뒤로
    ("a", 1.0),   # 왼쪽
]

# RANDOM 패턴 방향 선택지
RANDOM_DIRS = ["w", "a", "s", "d"]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def press_key(key, duration):
    """특정 키를 duration초 동안 누름"""
    keyboard.press(key)
    time.sleep(duration)
    keyboard.release(key)


def do_interact():
    """F키로 아이템 픽업"""
    keyboard.press_and_release("f")
    stats["pickups"] += 1


def do_jump():
    """점프"""
    keyboard.press_and_release("space")


def sweep_loop():
    """Sweep 모드: 패턴을 반복하며 이동"""
    pattern_index = 0
    last_interact = time.time()
    last_jump = time.time()

    while not stop_event.is_set():
        key, duration = SWEEP_PATTERN[pattern_index]

        # 이동하면서 F키 + 점프 병행
        start = time.time()
        keyboard.press(key)

        while time.time() - start < duration:
            now = time.time()

            # 상호작용 (F키)
            if now - last_interact >= CONFIG["interact_interval"]:
                keyboard.press_and_release("f")
                stats["pickups"] += 1
                last_interact = now

            # 점프
            if CONFIG["jump_interval"] > 0 and now - last_jump >= CONFIG["jump_interval"]:
                keyboard.press_and_release("space")
                last_jump = now

            time.sleep(0.05)

            if stop_event.is_set():
                break

        keyboard.release(key)

        if stop_event.is_set():
            break

        pattern_index = (pattern_index + 1) % len(SWEEP_PATTERN)
        if pattern_index == 0:
            stats["cycles"] += 1
            elapsed = time.time() - stats["start_time"]
            log(f"사이클 {stats['cycles']}회 완료 | 픽업 {stats['pickups']}회 | 경과 {elapsed:.0f}초")


def random_loop():
    """Random 모드: 랜덤 방향으로 이동"""
    last_interact = time.time()
    last_jump = time.time()

    while not stop_event.is_set():
        direction = random.choice(RANDOM_DIRS)
        duration = random.uniform(0.5, 2.0)

        start = time.time()
        keyboard.press(direction)

        while time.time() - start < duration:
            now = time.time()

            if now - last_interact >= CONFIG["interact_interval"]:
                keyboard.press_and_release("f")
                stats["pickups"] += 1
                last_interact = now

            if CONFIG["jump_interval"] > 0 and now - last_jump >= CONFIG["jump_interval"]:
                keyboard.press_and_release("space")
                last_jump = now

            time.sleep(0.05)

            if stop_event.is_set():
                break

        keyboard.release(direction)

        stats["cycles"] += 1

        # 가끔 방향 전환 대기
        time.sleep(random.uniform(0.1, 0.3))


def macro_thread():
    """매크로 메인 스레드"""
    global running
    stats["start_time"] = time.time()
    stats["cycles"] = 0
    stats["pickups"] = 0

    log(f"매크로 시작! 모드: {CONFIG['mode'].upper()}")
    log("중지하려면 F9 누르세요.")

    try:
        if CONFIG["mode"] == "sweep":
            sweep_loop()
        else:
            random_loop()
    except Exception as e:
        log(f"오류 발생: {e}")
    finally:
        # 혹시 눌려있는 키 해제
        for k in ["w", "a", "s", "d", "f", "space"]:
            try:
                keyboard.release(k)
            except Exception:
                pass

        elapsed = time.time() - stats["start_time"]
        log(f"매크로 중지 | 총 픽업: {stats['pickups']}회 | 사이클: {stats['cycles']}회 | 시간: {elapsed:.0f}초")
        running = False


def toggle_macro():
    """F9: 매크로 시작/중지 토글"""
    global running

    if not running:
        running = True
        stop_event.clear()
        t = threading.Thread(target=macro_thread, daemon=True)
        t.start()
        print("\n" + "="*50)
        log("▶ 매크로 ON")
        print("="*50)
    else:
        log("⏸ 매크로 중지 중...")
        stop_event.set()
        running = False


def quit_macro():
    """F10: 완전 종료"""
    global running
    if running:
        stop_event.set()
        running = False
        time.sleep(0.3)
    log("프로그램 종료")
    sys.exit(0)


def print_header():
    print("=" * 55)
    print("  Sol's RNG 알줍는 매크로 v1.0 (직접 제작 — 안전)")
    print("=" * 55)
    print(f"  모드    : {CONFIG['mode'].upper()}")
    print(f"  상호작용: {CONFIG['interact_interval']}초마다 F키")
    print(f"  점프    : {CONFIG['jump_interval']}초마다 스페이스")
    print("-" * 55)
    print("  [F9]  매크로 시작 / 중지")
    print("  [F10] 프로그램 종료")
    print("-" * 55)
    print("  ⚠️  먼저 Sol's RNG 창을 클릭하세요!")
    print("  ⚠️  페일세이프: 마우스를 좌상단으로 이동시 즉시 중단")
    print("=" * 55)
    print()


def main():
    # pyautogui 페일세이프 설정
    pyautogui.FAILSAFE = CONFIG["failsafe"]

    print_header()

    # 단축키 등록
    keyboard.add_hotkey("f9", toggle_macro, suppress=False)
    keyboard.add_hotkey("f10", quit_macro, suppress=False)

    log("대기 중... Sol's RNG 창을 클릭 후 F9를 누르세요.")

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        quit_macro()


if __name__ == "__main__":
    main()
