"""
YoonchanSweeper — Web Dashboard + Sound Notifications
  Flask 기반 실시간 대시보드 (localhost:7777)
"""
from __future__ import annotations
import threading, logging, time, json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import MacroState

log = logging.getLogger("YoonchanSweeper.dashboard")

# ── 사운드 알림 ──────────────────────────────────────────────
def play_beep(frequency: int = 1000, duration: int = 200):
    try:
        import winsound
        winsound.Beep(frequency, duration)
    except Exception:
        pass

def notify_rare_item(item_name: str):
    """희귀 아이템 감지 시 특수 비프음 패턴"""
    patterns = {
        "rare_purple": [(800,150),(1000,150),(1200,300)],
        "red_rare":    [(1200,100),(800,100),(1200,200)],
    }
    seq = patterns.get(item_name, [(1000, 300)])
    for freq, dur in seq:
        play_beep(freq, dur)
        time.sleep(0.05)


# ── 인라인 HTML 대시보드 ─────────────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YoonchanSweeper Dashboard</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;padding:20px}
  h1{font-size:1.4rem;color:#58a6ff;margin-bottom:4px}
  .sub{font-size:.8rem;color:#8b949e;margin-bottom:20px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}
  .card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px}
  .card .val{font-size:1.8rem;font-weight:700;color:#58a6ff}
  .card .lbl{font-size:.75rem;color:#8b949e;margin-top:4px}
  .bar-wrap{background:#21262d;border-radius:4px;height:10px;margin:12px 0;overflow:hidden}
  .bar{height:100%;border-radius:4px;background:linear-gradient(90deg,#238636,#2ea043);transition:width .5s}
  .mode-btns{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
  .btn{padding:7px 14px;border-radius:6px;border:1px solid #30363d;
       background:#21262d;color:#e6edf3;cursor:pointer;font-size:.85rem;transition:.2s}
  .btn:hover{border-color:#58a6ff;color:#58a6ff}
  .btn.active{background:#1f6feb;border-color:#1f6feb;color:#fff}
  .btn.stop{background:#da3633;border-color:#da3633}
  .btn.start{background:#238636;border-color:#238636}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  td,th{padding:8px 10px;border-bottom:1px solid #21262d;text-align:left}
  th{color:#8b949e;font-weight:500}
  .status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
  .on{background:#2ea043} .off{background:#da3633}
  .rare{color:#f78166;font-weight:700}
</style>
</head>
<body>
<h1>⚡ YoonchanSweeper v4.0</h1>
<p class="sub">Sol's RNG World-Class Macro Dashboard</p>

<div class="mode-btns" id="modeBtns"></div>

<button class="btn" id="toggleBtn" onclick="toggleMacro()">▶ 시작</button>
&nbsp;
<span id="statusDot"><span class="status off"></span> 정지</span>

<div class="grid" id="statsGrid"></div>
<div class="bar-wrap"><div class="bar" id="rateBar" style="width:0%"></div></div>

<table>
  <thead><tr><th>항목</th><th>값</th></tr></thead>
  <tbody id="statsTable"></tbody>
</table>

<script>
const MODES = ['SWEEP','SPIRAL','GRID','RANDOM','VISION','SMART'];
let currentMode = 'SWEEP', running = false;

function renderModeBtns(mode){
  const c = document.getElementById('modeBtns');
  c.innerHTML = MODES.map(m =>
    `<button class="btn${m===mode?' active':''}" onclick="setMode('${m}')">${m}</button>`
  ).join('');
}

async function setMode(m){
  await fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({mode:m})});
  currentMode=m; renderModeBtns(m);
}

async function toggleMacro(){
  await fetch('/api/toggle',{method:'POST'});
  refreshStats();
}

function fmt(d){
  const cards=[
    {val:d.pickups,       lbl:'총 픽업'},
    {val:d.rate_per_min+'<small>/분</small>', lbl:'픽업 속도'},
    {val:d.cycles,        lbl:'사이클'},
    {val:d.detected,      lbl:'아이템 감지'},
    {val:`<span class="rare">${d.rare_detected}</span>`, lbl:'희귀 아이템'},
    {val:d.elapsed,       lbl:'경과 시간'},
  ];
  document.getElementById('statsGrid').innerHTML = cards.map(c=>
    `<div class="card"><div class="val">${c.val}</div><div class="lbl">${c.lbl}</div></div>`
  ).join('');

  const rows=[
    ['모드', d.mode],
    ['픽업/분', d.rate_per_min],
    ['최근 1분', d.rate_1min+'회'],
    ['Anti-AFK', d.afk_triggers+'회'],
    ['재연결', d.reconnects+'회'],
  ];
  document.getElementById('statsTable').innerHTML = rows.map(r=>
    `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`
  ).join('');

  const barW = Math.min(d.rate_per_min/60*100, 100);
  document.getElementById('rateBar').style.width = barW+'%';

  running = d.running;
  const dot = running
    ? '<span class="status on"></span> 실행 중'
    : '<span class="status off"></span> 정지';
  document.getElementById('statusDot').innerHTML = dot;
  document.getElementById('toggleBtn').textContent = running ? '⏸ 중지' : '▶ 시작';
  document.getElementById('toggleBtn').className = 'btn ' + (running?'stop':'start');
  renderModeBtns(d.mode);
}

async function refreshStats(){
  try{
    const r = await fetch('/api/stats');
    const d = await r.json();
    fmt(d);
  }catch(e){}
}

refreshStats();
setInterval(refreshStats, 1500);
renderModeBtns(currentMode);
</script>
</body>
</html>"""


# ── Dashboard 클래스 ─────────────────────────────────────────
class Dashboard:
    def __init__(self, state: "MacroState"):
        self._state  = state
        self._thread: threading.Thread | None = None
        self._app    = None

    def start(self):
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        pass  # daemon thread auto-stops

    def _serve(self):
        try:
            from flask import Flask, jsonify, request, Response
            import logging as _lg
            _lg.getLogger("werkzeug").setLevel(_lg.ERROR)

            app   = Flask("YoonchanSweeper")
            state = self._state

            @app.route("/")
            def index():
                return Response(_HTML, mimetype="text/html")

            @app.route("/api/stats")
            def stats():
                return jsonify(state.snapshot())

            @app.route("/api/config")
            def config():
                return jsonify(state.cfg)

            @app.route("/api/mode", methods=["POST"])
            def set_mode():
                data = request.get_json(force=True) or {}
                new_mode = data.get("mode", "SWEEP").upper()
                from engine.state import MODES
                if new_mode in MODES:
                    state.mode = new_mode
                    log.info("[Dashboard] 모드 변경 → %s", new_mode)
                    return jsonify({"ok": True, "mode": new_mode})
                return jsonify({"ok": False}), 400

            @app.route("/api/toggle", methods=["POST"])
            def toggle():
                # 단축키 핸들러 트리거 (이벤트 방식)
                state._dashboard_toggle = True
                return jsonify({"ok": True, "running": state.running})

            port = state.cfg.get("dashboard_port", 7777)
            app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
        except Exception as e:
            log.error("[Dashboard] 시작 실패: %s", e)
