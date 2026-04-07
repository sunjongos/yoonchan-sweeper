# YoonchanSweeper v3.0

> Sol's RNG 알줍기 하네스 모드 매크로 — 직접 제작 · 악성코드 없는 100% 안전한 버전

```
╔═══════════════════════════════════════════════════════════════╗
║   ██╗   ██╗ ██████╗  ██████╗ ███╗   ██╗ ██████╗██╗  ██╗     ║
║   ╚██╗ ██╔╝██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║     ║
║    ╚████╔╝ ██║   ██║██║   ██║██╔██╗ ██║██║     ███████║     ║
║     ╚██╔╝  ██║   ██║██║   ██║██║╚██╗██║██║     ██╔══██║     ║
║      ██║   ╚██████╔╝╚██████╔╝██║ ╚████║╚██████╗██║  ██║     ║
║      ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝     ║
║       S W E E P E R   v3.0        by  yoonchan              ║
╚═══════════════════════════════════════════════════════════════╝
```

## 소개

유튜브에 돌아다니는 Sol's RNG 매크로는 대부분 **악성코드(RAT, 스틸러)가 삽입**되어 있습니다.  
이 프로젝트는 **Python으로 직접 작성한 안전한 오픈소스 버전**입니다.  
소스코드가 공개되어 있으므로 직접 확인하고 사용할 수 있습니다.

## 기능

| 기능 | 설명 |
|------|------|
| 🗺️ **5가지 이동 모드** | SWEEP · SPIRAL · GRID · RANDOM · VISION |
| 👁️ **Vision 아이템 감지** | 화면 색상 분석으로 알 자동 추적 |
| 🛡️ **Anti-AFK** | 110초마다 자동 동작, 로블록스 킥 방지 |
| 🎲 **지터 시스템** | 타이밍 랜덤 변동으로 봇 감지 우회 |
| 📊 **실시간 통계** | 픽업/분 속도 바 그래프, 경과 시간 |
| 💾 **설정 파일** | `yoonchan_config.json`으로 세부 조정 |
| 🔴 **Failsafe** | 마우스 좌상단 이동 시 즉시 비상정지 |
| 📝 **로그 파일** | 날짜별 자동 저장 |

## 이동 모드 설명

### SWEEP (기본 추천)
맵을 체계적으로 지그재그 순회합니다. 대부분의 상황에 최적.

### SPIRAL
중심에서 바깥쪽으로 나선형으로 확장하며 이동. 커버리지 최대화.

### GRID
격자 패턴으로 칸칸이 이동. 빠짐없이 수집하고 싶을 때.

### RANDOM
완전 랜덤 방향 이동. 봇 감지 우회에 유리.

### VISION ⭐ 최고급
`numpy` + `PIL`로 화면을 실시간 분석하여 알/아이템 색상을 감지,  
해당 방향으로 자동 이동합니다.

## 설치

### 요구사항
- Python 3.8+
- Windows 10/11

### 패키지 설치
```bash
pip install pyautogui keyboard pynput pillow numpy
```

## 실행 방법

```bash
python yoonchan_sweeper.py
```

1. Sol's RNG 실행 (Roblox)
2. `yoonchan_sweeper.py` 실행
3. Sol's RNG 창을 클릭하여 포커스
4. **F9** 눌러 시작

## 단축키

| 키 | 동작 |
|----|------|
| `F9` | 매크로 시작 / 중지 토글 |
| `F8` | 모드 순환 (SWEEP→SPIRAL→GRID→RANDOM→VISION) |
| `F7` | 실시간 통계 출력 |
| `F6` | 현재 설정 출력 |
| `F10` | 프로그램 완전 종료 |

## 설정 파일 (`yoonchan_config.json`)

처음 실행 시 자동 생성됩니다. 주요 설정:

```json
{
  "mode": "SWEEP",
  "interact_interval": 0.22,
  "jump_interval": 1.3,
  "anti_afk": true,
  "anti_afk_sec": 110,
  "jitter": true,
  "jitter_max": 0.12,
  "failsafe": true,
  "vision_scan_interval": 0.4,
  "vision_min_pixels": 25
}
```

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `interact_interval` | F키 누르는 주기 (초) | 0.22 |
| `jump_interval` | 점프 주기 (초), 0=비활성 | 1.3 |
| `anti_afk_sec` | AFK 방지 동작 주기 (초) | 110 |
| `jitter_max` | 타이밍 랜덤 변동 최대폭 | 0.12 |
| `vision_min_pixels` | 아이템 감지 최소 픽셀 수 | 25 |

## Vision 모드 색상 커스텀

`yoonchan_config.json`의 `vision_colors` 배열에서 RGB 범위를 조정:

```json
"vision_colors": [
  {"name": "golden_egg",  "r": [200,255], "g": [180,255], "b": [80,180]},
  {"name": "rare_purple", "r": [120,210], "g": [40,130],  "b": [190,255]},
  {"name": "item_white",  "r": [230,255], "g": [230,255], "b": [230,255]},
  {"name": "cyan_aura",   "r": [40,140],  "g": [200,255], "b": [200,255]}
]
```

## 파일 구조

```
sols_rng_macro/
├── yoonchan_sweeper.py      # 메인 매크로 (v3.0)
├── yoonchan_config.json     # 설정 파일 (자동 생성)
├── yoonchan_YYYYMMDD.log    # 로그 파일 (자동 생성)
├── alphasweeper.py          # 이전 버전 (v2.0)
├── sols_rng_macro.py        # 초기 버전 (v1.0)
└── README.md
```

## 주의사항

- ⚠️ 로블록스 ToS 위반 가능성 있음 — 계정 밴 위험을 인지하고 사용하세요.
- ⚠️ 교육·연구 목적의 자동화 도구입니다.
- ✅ Failsafe: 마우스를 화면 **좌상단 모서리**로 이동하면 즉시 정지합니다.

## 라이선스

MIT License — by yoonchan
