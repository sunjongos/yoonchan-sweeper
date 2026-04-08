"""
YoonchanSweeper — Movement AI + Anti-Detection Engine
  베지에 커브 타이밍 · 가우시안 지터 · 피로도 모델 · 인간 시뮬레이션
"""
from __future__ import annotations
import time, random, math, threading, logging
from typing import List

import keyboard

log = logging.getLogger("YoonchanSweeper.movement")

OPPOSITE = {"w": "s", "s": "w", "a": "d", "d": "a"}
ALL_DIRS = ["w", "a", "s", "d"]


# ══════════════════════════════════════════════════════════
# Anti-Detection Engine
# ══════════════════════════════════════════════════════════

class AntiDetection:
    """
    봇 감지 우회 전략:
    1. 가우시안 지터 — 타이밍 정규분포 변동
    2. 피로도 모델  — 장시간 시 자연스럽게 느려짐
    3. 확률적 휴식  — 가끔 랜덤 일시 정지
    4. 속도 변동    — 일정하지 않은 이동 속도
    """
    def __init__(self, config: dict):
        self.cfg       = config
        self._start    = time.time()
        self._op_count = 0       # 누적 동작 수

    # ── 가우시안 지터 ─────────────────────────────────────────
    def jitter(self, base: float) -> float:
        if not self.cfg.get("jitter", True):
            return base
        sigma = self.cfg.get("jitter_max", 0.12) * 0.4
        return max(0.03, base + random.gauss(0, sigma))

    # ── 피로도 배율 (1.0 → 최대 1.45) ───────────────────────
    def fatigue_factor(self) -> float:
        if not self.cfg.get("fatigue_mode", True):
            return 1.0
        import datetime
        elapsed_min = (time.time() - self._start) / 60.0
        hour = datetime.datetime.now().hour
        # 야간(22시~6시)은 피로도 더 빠르게 축적 (더 자연스럽게 느려짐)
        rate = 0.0025 if (hour >= 22 or hour < 6) else 0.0015
        return min(1.45, 1.0 + elapsed_min * rate)

    # ── 확률적 일시 정지 ─────────────────────────────────────
    def should_pause(self) -> bool:
        self._op_count += 1
        # 200동작마다 약 5% 확률로 짧은 정지
        if self._op_count % 200 == 0 and random.random() < 0.05:
            return True
        return False

    # ── 인간 지연 ─────────────────────────────────────────────
    def human_delay(self):
        if random.random() < 0.15:
            time.sleep(random.uniform(0.08, 0.45))

    # ── 속도 변동 ─────────────────────────────────────────────
    def vary_speed(self, base: float) -> float:
        return self.jitter(base * self.fatigue_factor())

    # ── 패턴 변형 ─────────────────────────────────────────────
    def get_pattern_variation(self, pattern: list) -> list:
        """패턴을 약간 섞어 예측 불가능하게 만듦"""
        if random.random() < 0.3:
            # 30% 확률로 처음 2개 순서 교환
            p = pattern.copy()
            if len(p) >= 2:
                p[0], p[1] = p[1], p[0]
            return p
        return pattern


# ══════════════════════════════════════════════════════════
# Movement Engine
# ══════════════════════════════════════════════════════════

class MovementEngine:
    """
    키 입력 기반 이동 엔진.
    - F키 / 점프를 이동 중 비동기 처리
    - 베지에 커브 타이밍으로 가속/감속 시뮬레이션
    - Anti-Detection 통합
    """

    def __init__(self, config: dict):
        self.cfg = config
        self.ad  = AntiDetection(config)
        self._lock = threading.Lock()

    # ── 베지에 커브 슬립 ──────────────────────────────────────
    @staticmethod
    def _bezier_sleep(total: float, steps: int = 20):
        """
        총 슬립 시간을 베지에 커브로 분배.
        시작과 끝을 느리게, 중간을 빠르게 → 자연스러운 가속/감속
        """
        if total <= 0: return
        # 이차 베지에: t^2 → 앞뒤 느리게
        deltas = []
        for i in range(steps):
            t0 = i / steps
            t1 = (i + 1) / steps
            # 적분 근사: 속도 곡선 = 6t(1-t) (0~1 사이 최대 1.5)
            area = (6 * t0 * (1 - t0) + 6 * t1 * (1 - t1)) / 2 / steps
            deltas.append(area)
        s = sum(deltas) or 1
        for d in deltas:
            time.sleep(total * d / s)

    # ── 메인 이동 ─────────────────────────────────────────────
    def move(self, direction, duration: float,
             do_interact: bool = True, do_jump: bool = True):
        """
        방향키(단일 문자열 혹은 리스트)를 duration초 누르면서 상호작용/점프 병행.
        다방향 이동 (대각선 등) 지원.
        """
        from engine.state import MacroState
        import importlib
        state_mod = importlib.import_module("engine.state")

        ii  = self.cfg.get("interact_interval", 0.22)
        ji  = self.cfg.get("jump_interval", 1.2)

        last_pick = time.time()
        last_jump = time.time()

        dirs = [direction] if isinstance(direction, str) else direction
        for d in dirs:
            keyboard.press(d)
            
        t0 = time.time()

        try:
            while time.time() - t0 < duration:
                now = time.time()

                if do_interact and now - last_pick >= self.ad.jitter(ii):
                    keyboard.press_and_release("e")
                    last_pick = now
                    if random.random() < 0.08:
                        time.sleep(self.ad.jitter(0.05))
                        keyboard.press_and_release("e")

                if do_jump and ji > 0 and now - last_jump >= self.ad.jitter(ji):
                    keyboard.press_and_release("space")
                    last_jump = now

                time.sleep(0.04)

        finally:
            for d in dirs:
                keyboard.release(d)

        # 가끔 산만한 동작
        if self.ad.should_pause():
            self.simulate_distraction()

    # ── 주변 둘러보기 (오가닉 스티어링) ─────────────────────────
    def smooth_look(self, max_offset=250, duration=0.8):
        """기계적인 확 꺾임을 방지하고, S자를 그리듯 부드럽게 시야 확보"""
        import pyautogui
        import math
        try:
            sw, sh = pyautogui.size()
            cx, cy = sw // 2, sh // 2
            
            # 랜덤 이동폭 (너무 크지 않게, 좌/우 중 랜덤)
            ox = random.choice([-1, 1]) * random.randint(int(max_offset * 0.5), max_offset)
            oy = random.randint(-15, 15)  # 상하 움직임은 최소화
            
            pyautogui.FAILSAFE = False
            # 먼저 화면 중심으로 커서 안착 (이동 과정 생략, 즉시 이동)
            pyautogui.moveTo(cx, cy)
            
            # 우클릭으로 부드럽게 드래그하며 스티어링
            pyautogui.mouseDown(button='right')
            # 꿀렁이는 느낌을 주어 진짜 사람이 마우스를 돌리는 듯한 가감속 적용
            pyautogui.moveRel(ox, oy, duration=duration, tween=pyautogui.easeInOutQuad)
            pyautogui.mouseUp(button='right')
            
            # 마우스 이탈을 막기 위해 다시 안보이게 센터로
            pyautogui.moveTo(cx, cy)
            
            pyautogui.FAILSAFE = self.cfg.get("failsafe", True)
        except Exception as e:
            log.warning("시야 회전 중 오류: %s", e)

    # ── 연속 픽업 ─────────────────────────────────────────────
    def burst_interact(self, count: int = 3):
        """F키를 count회 빠르게 연타"""
        for _ in range(count):
            keyboard.press_and_release("e")
            time.sleep(self.ad.jitter(0.11))

    # ── 인간 일시 정지 ────────────────────────────────────────
    def human_pause(self, mn: float = 0.1, mx: float = 0.5):
        """인간처럼 자연스러운 일시 정지"""
        time.sleep(random.uniform(mn, mx))

    # ── 산만 동작 시뮬레이션 ──────────────────────────────────
    def simulate_distraction(self):
        """
        가끔 실제 사람처럼 짧게 멈추거나 랜덤 키 입력 후 복귀.
        봇 감지 우회에 효과적.
        """
        pause = random.uniform(0.3, 1.2)
        log.debug("[AntiDetect] 산만 동작 (%.2f초)", pause)
        time.sleep(pause)
        # 아주 가끔 카메라 회전 흉내 (마우스 이동)
        if random.random() < 0.3:
            import pyautogui
            ox, oy = random.randint(-8, 8), random.randint(-4, 4)
            pyautogui.moveRel(ox, oy, duration=0.15)
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.moveRel(-ox, -oy, duration=0.15)

    # ── 베지에 커브 슬립 (cubic smoothstep: 3t²-2t³) ────────────
    @staticmethod
    def _bezier_sleep(total: float, steps: int = 20):
        """
        총 시간을 cubic smoothstep으로 분배:
        f(t) = 3t² - 2t³  — 시작/끝 느리고 중간 빠름 (자연스러운 가속·감속)
        """
        if total <= 0:
            return
        steps = max(5, int(total / 0.04))
        prev_f = 0.0
        for i in range(1, steps + 1):
            t = i / steps
            f = 3 * t**2 - 2 * t**3   # cubic smoothstep
            delta = f - prev_f
            prev_f = f
            time.sleep(max(0.0, total * delta))

    # ── 모든 키 해제 ─────────────────────────────────────────
    def release_all(self):
        for k in "wasd":
            try: keyboard.release(k)
            except: pass
