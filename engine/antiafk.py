"""
YoonchanSweeper — Anti-AFK + Auto-Reconnect Worker
"""
from __future__ import annotations
import time, logging, threading
import pyautogui
import keyboard as kb

log = logging.getLogger("YoonchanSweeper.antiafk")


class AntiAFKWorker:
    def __init__(self, state):
        self._state = state
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("[AntiAFK] 시작 (주기 %d초)", self._state.cfg["anti_afk_sec"])

    def _loop(self):
        state  = self._state
        period = state.cfg["anti_afk_sec"]
        ticks  = period * 10
        while not state.stop.is_set():
            for _ in range(ticks):
                if state.stop.is_set():
                    return
                time.sleep(0.1)
            if not state.running:
                continue
            # 마우스 미세 이동 + 점프
            try:
                pyautogui.moveRel(2, 0, duration=0.08)
                pyautogui.moveRel(-2, 0, duration=0.08)
                kb.press_and_release("space")
            except Exception as e:
                log.debug("[AntiAFK] 오류: %s", e)
            with state._lock:
                state.stats.afk_triggers += 1
            log.debug("[AntiAFK] 동작 실행 (#%d)", state.stats.afk_triggers)
