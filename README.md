# YoonchanSweeper v4.0 — World-Class Edition

> Sol's RNG 알줍기 World-Class 하네스 매크로 — by yoonchan  
> 직접 제작 · 악성코드 없는 100% 오픈소스

```
╔═══════════════════════════════════════════════════════════════╗
║   ██╗   ██╗ ██████╗  ██████╗ ███╗   ██╗ ██████╗██╗  ██╗     ║
║   ╚██╗ ██╔╝██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║     ║
║    ╚████╔╝ ██║   ██║██║   ██║██╔██╗ ██║██║     ███████║     ║
║     ╚██╔╝  ██║   ██║██║   ██║██║╚██╗██║██║     ██╔══██║     ║
║      ██║   ╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║  ██║     ║
║      ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝     ║
║    S W E E P E R   v4.0   WORLD-CLASS   by yoonchan          ║
╚═══════════════════════════════════════════════════════════════╝
```

## 왜 이 매크로인가?

유튜브에 퍼진 Sol's RNG 매크로 대부분은 **RAT·스틸러가 삽입된 악성코드**입니다.  
YoonchanSweeper는 Python으로 직접 작성한 **100% 오픈소스 안전한 버전**입니다.

## 아키텍처

```
sols_rng_macro/
├── yoonchan_sweeper.py      # 메인 진입점 (핫키, 배너, 오케스트레이터)
└── engine/
    ├── state.py             # 공유 상태 · 통계 · 설정
    ├── modes.py             # 6가지 이동 모드
    ├── movement.py          # 이동 AI + 안티감지 엔진
    ├── vision.py            # 화면 색상/CV 감지 엔진
    ├── dashboard.py         # 웹 대시보드 (Flask)
    └── antiafk.py           # Anti-AFK 워커
```

## 기능 총람

| 카테고리 | 기능 |
|----------|------|
| **이동 모드** | SWEEP · SPIRAL · GRID · RANDOM · VISION · **SMART** |
| **Vision AI** | numpy + PIL + OpenCV 연결 클러스터 감지, 방향 자동 계산 |
| **SMART 모드** | Vision 감지 실패 30초 시 SWEEP 자동 전환, 감지 재개 시 Vision 복귀 |
| **Anti-Detection** | 가우시안 지터 · 피로도 모델 · 베지에 커브 타이밍 · 확률적 정지 |
| **Anti-AFK** | 105초마다 마우스 미세 이동 + 점프 (킥 방지) |
| **웹 대시보드** | http://localhost:7777 실시간 통계 · 모드 전환 · 시작/중지 |
| **사운드 알림** | 희귀 아이템 감지 시 비프음 패턴 |
| **Failsafe** | 마우스 좌상단 이동 즉시 비상정지 |
| **로그 파일** | 날짜별 자동 저장 |

## 이동 모드 상세

| 모드 | 설명 | 추천 상황 |
|------|------|----------|
| **SWEEP** | 지그재그 체계적 순회 | 일반 수집 |
| **SPIRAL** | 중심→바깥 나선형 확장 | 넓은 맵 |
| **GRID** | 격자 패턴 정밀 수집 | 특정 구역 집중 |
| **RANDOM** | 완전 랜덤 이동 | 봇 감지 우회 |
| **VISION** | 화면 색상 감지 추적 | 아이템 집중 구역 |
| **SMART** ★ | Vision + Sweep 자동 전환 | 최고 효율 |

## 안티 감지 시스템

- **가우시안 지터**: 모든 타이밍에 정규분포 랜덤 변동 (σ = jitter_max × 0.4)
- **피로도 모델**: 30분 이상 사용 시 최대 35% 자연스럽게 느려짐
- **베지에 커브**: 이동 시작/끝 가속·감속 타이밍 시뮬레이션
- **확률적 정지**: 200동작마다 5% 확률로 짧은 랜덤 정지
- **산만 동작**: 가끔 카메라 회전 흉내 (마우스 미세 이동)

## 설치

### 요구사항
- Python 3.8+
- Windows 10/11

### 패키지 설치
```bash
pip install pyautogui keyboard pynput pillow numpy opencv-python-headless flask
```

## 실행

```bash
python yoonchan_sweeper.py
```

1. Sol's RNG 실행 (Roblox)
2. `yoonchan_sweeper.py` 실행
3. Sol's RNG 창 클릭하여 포커스
4. **F9** 눌러 시작
5. 브라우저에서 http://localhost:7777 접속 (대시보드)

## 단축키

| 키 | 동작 |
|----|------|
| `F9`  | 매크로 시작 / 중지 토글 |
| `F8`  | 모드 순환 (SWEEP→SPIRAL→GRID→RANDOM→VISION→SMART) |
| `F7`  | 실시간 통계 출력 |
| `F6`  | 현재 설정 출력 |
| `F5`  | 웹 대시보드 열기 |
| `F10` | 프로그램 완전 종료 |

## 설정 (`yoonchan_config.json`)

최초 실행 시 자동 생성. 주요 항목:

```json
{
  "mode": "SMART",
  "interact_interval": 0.20,
  "jump_interval": 1.2,
  "anti_afk": true,
  "anti_afk_sec": 105,
  "jitter": true,
  "jitter_max": 0.13,
  "fatigue_mode": true,
  "dashboard": true,
  "dashboard_port": 7777,
  "beep_on_rare": true
}
```

## Vision 색상 커스텀

`vision_colors` 배열에서 RGB 범위 조정:

```json
"vision_colors": [
  {"name": "golden_egg",  "r": [195,255], "g": [175,255], "b": [70,175]},
  {"name": "rare_purple", "r": [110,215], "g": [35,135],  "b": [185,255]},
  {"name": "item_white",  "r": [225,255], "g": [225,255], "b": [225,255]},
  {"name": "cyan_aura",   "r": [30,140],  "g": [195,255], "b": [195,255]},
  {"name": "red_rare",    "r": [200,255], "g": [30,100],  "b": [30,100]}
]
```

## 주의사항

- ⚠️ 로블록스 ToS 위반 가능성 — 계정 밴 위험을 인지하고 사용하세요.
- ⚠️ 교육·연구 목적의 자동화 도구입니다.
- ✅ Failsafe: 마우스를 **화면 좌상단 모서리**로 이동하면 즉시 정지.

## 라이선스

MIT License — by yoonchan
