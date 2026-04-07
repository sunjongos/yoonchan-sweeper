"""
YoonchanSweeper — Vision Engine
  numpy + PIL + OpenCV 기반 실시간 아이템 감지
"""
from __future__ import annotations
import time, logging, math
from dataclasses import dataclass
from typing import Optional, Tuple, List

import numpy as np
import pyautogui

try:
    from PIL import ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

log = logging.getLogger("YoonchanSweeper.vision")


# ── 감지 결과 ────────────────────────────────────────────────
@dataclass
class ItemDetection:
    x:              int
    y:              int
    name:           str
    pixel_count:    int
    confidence:     float          # 0.0 ~ 1.0
    direction_hint: str            # w/a/s/d

    def __repr__(self):
        return (f"<ItemDetection {self.name} @ ({self.x},{self.y}) "
                f"conf={self.confidence:.2f} dir={self.direction_hint}>")


# ── Vision 엔진 ──────────────────────────────────────────────
class VisionEngine:
    # 연결 끊김 / 로딩 감지용 색상 임계값
    _DISCONNECT_COLOR = (45, 45, 45)    # 어두운 배경
    _LOADING_THRESH   = 15              # 평균 밝기 임계값

    def __init__(self, config: dict):
        self.cfg        = config
        self._sw, self._sh = pyautogui.size()
        self._cx        = self._sw // 2
        self._cy        = self._sh // 2
        self._prev_frame: Optional[np.ndarray] = None
        self._last_scan  = 0.0
        self._scan_count = 0
        log.info("VisionEngine 초기화 (%dx%d)", self._sw, self._sh)

    # ── 메인 스캔 ─────────────────────────────────────────────
    def scan(self) -> Optional[ItemDetection]:
        """화면 스캔 → 가장 가까운/신뢰도 높은 아이템 반환"""
        if not _PIL_OK:
            return None
        try:
            frame = self._grab()
            if frame is None:
                return None
            self._prev_frame = frame
            self._scan_count += 1

            best: Optional[ItemDetection] = None
            best_score = 0.0

            for color_def in self.cfg.get("vision_colors", []):
                det = self._detect_color(frame, color_def)
                if det and det.confidence > best_score:
                    best = det
                    best_score = det.confidence

            return best
        except Exception as e:
            log.debug("scan 오류: %s", e)
            return None

    # ── 그랩 ─────────────────────────────────────────────────
    def _grab(self) -> Optional[np.ndarray]:
        region = self.cfg.get("vision_screen_region")
        if region:
            img = ImageGrab.grab(bbox=region)
        else:
            img = ImageGrab.grab()
        return np.array(img)

    # ── 색상 감지 ─────────────────────────────────────────────
    def _detect_color(self, frame: np.ndarray,
                      color_def: dict) -> Optional[ItemDetection]:
        r_lo, r_hi = color_def["r"]
        g_lo, g_hi = color_def["g"]
        b_lo, b_hi = color_def["b"]

        mask = (
            (frame[:,:,0] >= r_lo) & (frame[:,:,0] <= r_hi) &
            (frame[:,:,1] >= g_lo) & (frame[:,:,1] <= g_hi) &
            (frame[:,:,2] >= b_lo) & (frame[:,:,2] <= b_hi)
        )
        count = int(np.sum(mask))
        min_px = self.cfg.get("vision_min_pixels", 20)
        if count < min_px:
            return None

        # 가장 큰 클러스터 찾기
        cx, cy, cluster_count = self._nearest_cluster(mask)

        # 신뢰도: 픽셀 수 기반 (최대 500px 기준 정규화)
        confidence = min(cluster_count / 500.0, 1.0)

        # 화면 중심 대비 방향 계산
        direction = self._compute_direction(cx, cy)

        region = self.cfg.get("vision_screen_region")
        abs_x = cx + (region[0] if region else 0)
        abs_y = cy + (region[1] if region else 0)

        return ItemDetection(
            x=abs_x, y=abs_y,
            name=color_def.get("name", "unknown"),
            pixel_count=cluster_count,
            confidence=confidence,
            direction_hint=direction,
        )

    # ── 클러스터 중심 ─────────────────────────────────────────
    def _nearest_cluster(self, mask: np.ndarray) -> Tuple[int, int, int]:
        """
        마스크에서 화면 중심에 가장 가까운 클러스터의 (cx, cy, count) 반환.
        OpenCV 사용 가능 시 connected components, 없으면 단순 무게중심.
        """
        if _CV2_OK:
            try:
                m8 = mask.astype(np.uint8) * 255
                n, labels, stats, centroids = cv2.connectedComponentsWithStats(m8)
                if n <= 1:
                    ys, xs = np.where(mask)
                    return int(xs.mean()), int(ys.mean()), int(np.sum(mask))

                # 레이블 1부터 (0=배경)
                best_label = 1
                best_dist  = float("inf")
                for lbl in range(1, n):
                    cx_l, cy_l = centroids[lbl]
                    area = stats[lbl, cv2.CC_STAT_AREA]
                    if area < 5:
                        continue
                    dist = math.hypot(cx_l - self._cx, cy_l - self._cy)
                    # 거리 ÷ 면적의 sqrt로 가중 점수 (크고 가까울수록 우선)
                    score = dist / (math.sqrt(area) + 1e-6)
                    if score < best_dist:
                        best_dist  = score
                        best_label = lbl

                cx_b = int(centroids[best_label][0])
                cy_b = int(centroids[best_label][1])
                cnt  = int(stats[best_label, cv2.CC_STAT_AREA])
                return cx_b, cy_b, cnt
            except Exception:
                pass

        # fallback: 단순 무게중심
        ys, xs = np.where(mask)
        return int(xs.mean()), int(ys.mean()), int(len(xs))

    # ── 방향 계산 ─────────────────────────────────────────────
    def _compute_direction(self, cx: int, cy: int) -> str:
        """화면 중심 기준으로 아이템이 어느 방향인지 반환"""
        dx = cx - self._cx
        dy = cy - self._cy
        if abs(dx) > abs(dy):
            return "d" if dx > 0 else "a"
        else:
            return "s" if dy > 0 else "w"

    # ── 상태 감지 ─────────────────────────────────────────────
    def is_disconnected(self) -> bool:
        """로블록스 연결 끊김 화면 감지 (어두운 대화상자)"""
        if not _PIL_OK:
            return False
        try:
            frame = self._grab()
            if frame is None: return False
            # 화면 중앙 100x50 픽셀 평균 확인
            h, w = frame.shape[:2]
            crop = frame[h//2-25:h//2+25, w//2-50:w//2+50]
            mean = float(crop.mean())
            return mean < 60.0  # 매우 어두우면 연결 끊김으로 판단
        except Exception:
            return False

    def is_loading(self) -> bool:
        """로딩 화면 감지 (전체 화면 평균 밝기 < 임계값)"""
        if not _PIL_OK:
            return False
        try:
            frame = self._grab()
            if frame is None: return False
            return float(frame.mean()) < self._LOADING_THRESH
        except Exception:
            return False

    # ── 움직임 감지 ───────────────────────────────────────────
    def detect_new_drops(self) -> bool:
        """
        이전 프레임과 현재 프레임 비교 → 새 아이템 등장 감지
        변화량이 임계값 이상이면 True 반환
        """
        if not _PIL_OK or self._prev_frame is None:
            return False
        try:
            curr = self._grab()
            if curr is None: return False
            diff = np.abs(curr.astype(int) - self._prev_frame.astype(int))
            changed_px = int(np.sum(diff.max(axis=2) > 40))
            self._prev_frame = curr
            return changed_px > 500
        except Exception:
            return False
