"""
YoonchanSweeper — Anti-AFK + Auto-Reconnect Worker
"""
from __future__ import annotations
import time, logging, threading
import pyautogui
import keyboard as kb

log = logging.getLogger("YoonchanSweeper.antiafk")


class AntiAFKWorker:
    def __init__(self, state, ve=None):
        self._state = state
        self._ve = ve
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("[AntiAFK/AutoReconnect] 백그라운드 파견 완료 (주기 %d초)", self._state.cfg["anti_afk_sec"])

    def _send_discord(self, msg: str):
        webhook_url = self._state.cfg.get("discord_webhook", "")
        if not webhook_url: return
        def _post():
            try:
                import urllib.request, json
                req = urllib.request.Request(webhook_url, method="POST")
                req.add_header('Content-Type', 'application/json')
                data = json.dumps({"content": msg}).encode('utf-8')
                urllib.request.urlopen(req, data=data, timeout=5)
            except Exception as e:
                log.debug("Discord 전송 에러: %s", e)
        threading.Thread(target=_post, daemon=True).start()

    def _loop(self):
        state  = self._state
        ve     = self._ve
        period = state.cfg["anti_afk_sec"]
        ticks  = period * 10
        tick_count = 0
        
        while not state.stop.is_set():
            time.sleep(0.1)
            tick_count += 1
            
            # --- Auto-Reconnect 수면 모니터링 (대략 10초마다) ---
            if state.running and state.cfg.get("auto_reconnect", True) and (tick_count % 100 == 0):
                if ve and ve.is_disconnected():
                    log.error("💥 [Auto-Reconnect] 로블록스 튕김/연결 끊김 감지! 자동 재접속 시도...")
                    state.stats.reconnects += 1
                    try:
                        self._send_discord("🚨 [YoonchanSweeper] 매크로가 서버 튕김을 감지하고 Auto-Reconnect(자동 재접속) 기동을 시작합니다!")
                        try: kb.release("w")
                        except: pass
                        
                        # 화면 하단부 다중 타겟 휩쓸며 클릭 (Grid Click)
                        # 해상도가 달라도 끊김/Leave 버튼을 적중시키기 위한 설계
                        sw, sh = pyautogui.size()
                        start_y = sh // 2
                        end_y = sh // 2 + 100
                        span_x = 150
                        center_x = sw // 2
                        
                        for cy in range(start_y, end_y + 1, 30):
                            for cx in range(center_x - span_x, center_x + span_x + 1, 50):
                                pyautogui.moveTo(cx, cy)
                                pyautogui.click()
                                time.sleep(0.05)
                        
                        kb.press_and_release("enter")
                        
                        log.info("🔌 재접속 버튼 타격. 맵 로딩 대기 시간 적용 (25초)...")
                        time.sleep(25)
                        
                        log.info("✔️ 로딩 완료 및 인게임 복귀 추정. 파밍을 재개합니다.")
                        try: kb.press("w")
                        except: pass
                        self._send_discord(f"✅ [YoonchanSweeper] 재접속 대기 시간 종료. 파밍을 강제 재개했습니다! (현재 재접속 횟수: {state.stats.reconnects}회)")
                    except Exception as e:
                        log.debug("재접속 시도 중 오류: %s", e)

            # --- Anti AFK (기존 로직) ---
            if tick_count >= ticks:
                tick_count = 0
                if not state.running:
                    continue
                try:
                    pyautogui.moveRel(2, 0, duration=0.08)
                    pyautogui.moveRel(-2, 0, duration=0.08)
                    kb.press_and_release("space")
                except Exception as e:
                    log.debug("[AntiAFK] 오류: %s", e)
                with state._lock:
                    state.stats.afk_triggers += 1
                log.debug("[AntiAFK] 생존 신호 발송 (#%d)", state.stats.afk_triggers)
