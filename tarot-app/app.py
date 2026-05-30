import streamlit as st
import anthropic
import random
import json
from tarot_data import TAROT_CARDS

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tarot by Zoey",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display:none!important; }
.block-container {
    padding:0!important;
    max-width:430px!important;
    margin:0 auto!important;
}
section[data-testid="stSidebar"] { display:none!important; }
iframe { border:none!important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "step": "question",
        "question": "",
        "shuffled_deck": [],
        "reversed_map": {},
        "selected_ids": [],
        "readings": {},
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def reset_all():
    st.session_state.update({
        "step": "question",
        "question": "",
        "shuffled_deck": [],
        "reversed_map": {},
        "selected_ids": [],
        "readings": {},
    })

def do_shuffle():
    deck = list(range(78))
    random.shuffle(deck)
    st.session_state.shuffled_deck = deck
    st.session_state.reversed_map = {i: (random.random() < 0.25) for i in range(78)}
    st.session_state.selected_ids = []
    st.session_state.readings = {}

def get_client():
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        import os
        key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("⚠️ Chưa có ANTHROPIC_API_KEY trong Streamlit secrets.")
        st.stop()
    return anthropic.Anthropic(api_key=key)

def generate_readings(question, cards_with_rev):
    """cards_with_rev: list of (card_dict, is_reversed) for [past, present, future]"""
    positions = ["Quá khứ", "Hiện tại", "Tương lai"]
    card_lines = []
    for i, (card, rev) in enumerate(cards_with_rev):
        meaning = card["reversed"] if rev else card["upright"]
        kw = ", ".join((card["keywords_rev"] if rev else card["keywords_up"])[:3])
        suffix = " (ngược)" if rev else ""
        card_lines.append(
            f"{positions[i]}: {card['name']}{suffix}\n  Ý nghĩa: {meaning}\n  Từ khóa: {kw}"
        )
    prompt = (
        f'Bạn là nhà tiên tri tarot huyền bí. Hãy giải bài cho câu hỏi: "{question}"\n\n'
        + "\n".join(card_lines)
        + "\n\nViết 2-3 câu cho mỗi vị trí, kết nối trực tiếp với câu hỏi. Dùng đúng định dạng:\n\n"
        "QUÁ KHỨ:\n[giải thích]\n\nHIỆN TẠI:\n[giải thích]\n\nTƯƠNG LAI:\n[giải thích]\n\n"
        "Giọng thần bí, ấm áp, tiếng Việt tự nhiên."
    )
    resp = get_client().messages.create(
        model="claude-opus-4-5",
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}]
    )
    text = resp.content[0].text
    markers = ["QUÁ KHỨ:", "HIỆN TẠI:", "TƯƠNG LAI:"]
    out = {}
    for i, m in enumerate(markers):
        s = text.find(m)
        if s == -1:
            out[i] = "Hãy lắng nghe trực giác của bạn về lá bài này."
            continue
        s += len(m)
        e = text.find(markers[i + 1]) if i < 2 else len(text)
        if e == -1:
            e = len(text)
        out[i] = text[s:e].strip()
    return out

# ─────────────────────────────────────────────────────────────
# QUERY PARAMS HANDLER
# ─────────────────────────────────────────────────────────────
params = st.query_params

if "q" in params:
    q = params["q"].strip()
    if q:
        st.session_state.question = q
        st.session_state.step = "meditation"
    st.query_params.clear()
    st.rerun()

elif "step" in params:
    val = params["step"]
    if val == "shuffle":
        do_shuffle()
        st.session_state.step = "shuffle"
    elif val == "pick":
        st.session_state.step = "pick"
    elif val == "restart":
        reset_all()
    st.query_params.clear()
    st.rerun()

elif "picked" in params:
    raw = params["picked"]
    parts = [x.strip() for x in raw.split(",") if x.strip().isdigit()]
    if len(parts) == 3:
        deck = st.session_state.shuffled_deck
        sel = [deck[int(p)] for p in parts if int(p) < len(deck)]
        if len(sel) == 3:
            st.session_state.selected_ids = sel
            st.session_state.step = "reading"
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────────────────────────
# SHARED HTML PIECES
# ─────────────────────────────────────────────────────────────

FONTS = '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400;1,500&display=swap" rel="stylesheet">'

BASE_CSS = """
:root {
  --bg-dark:#0a0a12; --bg-dark2:#14141f;
  --ink:#f5f3ee; --ink-dim:rgba(245,243,238,0.62); --ink-faint:rgba(245,243,238,0.34);
  --cream-ink:#2a2a3a; --cream-ink-dim:#6a6a7a;
  --glow:#c5cbf5; --glow-strong:#e8ebff;
  --serif:'Cormorant Garamond',Georgia,serif;
  --display:'Poppins',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;overflow:hidden;}
button{cursor:pointer;}
"""

def wrap(extra_css, body_html, dark=True):
    bg = "background:#0a0a12;" if dark else ""
    return f"""<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
{FONTS}
<style>{BASE_CSS}{extra_css}</style>
</head><body style="{bg}">{body_html}</body></html>"""


def rays_html(count=48):
    parts = []
    for i in range(count):
        angle = (i / count) * 360
        length = 38 + (i % 3) * 6
        w = 1.2 if i % 2 == 0 else 0.6
        op = 0.55 if i % 4 == 0 else 0.28
        parts.append(
            f'<div style="position:absolute;left:50%;top:50%;width:{w}px;height:{length}%;'
            f'background:linear-gradient(to bottom,transparent 0%,rgba(200,210,255,{op}) 30%,transparent 100%);'
            f'transform-origin:top center;transform:translate(-50%,0) rotate({angle}deg);">'
            f'</div>'
        )
    return (
        '<div style="position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:0;">'
        + "".join(parts)
        + '</div>'
    )


CARD_BACK_MINI = """<div style="width:60px;height:96px;border-radius:8px;flex-shrink:0;
background:radial-gradient(ellipse at 50% 45%,#b8bee8 0%,#6e74a8 35%,#2a2c44 75%,#1a1a26 100%);
box-shadow:0 4px 12px rgba(0,0,0,0.5),inset 0 0 12px rgba(0,0,0,0.4);
display:flex;align-items:center;justify-content:center;overflow:hidden;">
<svg viewBox="0 0 60 96" style="width:70%;height:auto;">
<ellipse cx="24" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
<ellipse cx="36" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
</svg></div>"""

CARD_BACK_BIG = """<div style="position:relative;width:100%;aspect-ratio:0.625;border-radius:14px;
background:radial-gradient(ellipse at 50% 45%,#b8bee8 0%,#6e74a8 35%,#2a2c44 75%,#1a1a26 100%);
box-shadow:0 0 60px rgba(197,203,245,0.45),0 0 120px rgba(197,203,245,0.22),inset 0 0 30px rgba(0,0,0,0.4);
overflow:hidden;display:flex;align-items:center;justify-content:center;">
<svg viewBox="0 0 200 280" style="width:78%;height:auto;">
<ellipse cx="80" cy="140" rx="56" ry="92" fill="none" stroke="rgba(20,20,30,0.7)" stroke-width="1.1"/>
<ellipse cx="120" cy="140" rx="56" ry="92" fill="none" stroke="rgba(20,20,30,0.7)" stroke-width="1.1"/>
</svg>
<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(255,255,255,0.18) 0%,transparent 60%);"></div>
</div>"""

# ─────────────────────────────────────────────────────────────
# SCREEN: QUESTION
# ─────────────────────────────────────────────────────────────

def screen_question():
    prompts_json = json.dumps([
        "Tình yêu của tôi sẽ đi về đâu?",
        "Tôi nên chọn con đường nào?",
        "Điều gì đang chờ đợi tôi trong công việc?",
        "Tôi cần buông bỏ điều gì?",
    ])

    css = """
html,body{background:linear-gradient(180deg,#F2EFE6 0%,#E6E3DA 100%);}
.screen{display:flex;flex-direction:column;height:100%;}
.tnav{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 10px;}
.ttl{flex:1;text-align:center;font-family:var(--display);font-size:15px;font-weight:400;
letter-spacing:0.02em;color:var(--cream-ink);}
.tbody{flex:1;overflow-y:auto;padding:20px 28px 28px;display:flex;flex-direction:column;scrollbar-width:none;}
.tbody::-webkit-scrollbar{display:none;}
.hint{font-family:var(--serif);font-style:italic;font-size:15px;line-height:1.55;
color:var(--cream-ink-dim);text-align:center;margin-bottom:22px;}
.tawrap{background:rgba(255,255,255,0.55);border:1px solid rgba(108,108,180,0.18);border-radius:16px;
padding:18px;box-shadow:0 4px 18px rgba(108,108,180,0.08),inset 0 0 0 1px rgba(255,255,255,0.4);
min-height:140px;margin-bottom:16px;}
textarea{width:100%;min-height:110px;background:transparent;border:none;outline:none;resize:none;
font-family:var(--serif);font-size:17px;line-height:1.5;color:var(--cream-ink);}
textarea::placeholder{color:rgba(42,42,58,0.38);}
.lbl{font-family:var(--display);font-size:10px;letter-spacing:0.18em;text-transform:uppercase;
color:var(--cream-ink-dim);margin:4px 0 10px;}
.prompts{display:flex;flex-direction:column;gap:8px;margin-bottom:16px;}
.pb{text-align:left;padding:12px 16px;border-radius:12px;border:1px solid rgba(108,108,180,0.15);
background:rgba(255,255,255,0.35);font-family:var(--serif);font-style:italic;font-size:14px;
color:var(--cream-ink);transition:background 0.25s;width:100%;display:block;}
.pb:hover{background:rgba(255,255,255,0.7);}
.spacer{flex:1;min-height:12px;}
.cta{width:100%;padding:18px 28px;border-radius:999px;border:1px solid rgba(108,108,180,0.18);
font-family:var(--display);font-size:12px;letter-spacing:0.18em;text-transform:uppercase;
margin-top:18px;transition:all 0.3s;}
.cta:disabled{background:rgba(255,255,255,0.4);color:rgba(108,108,180,0.4);box-shadow:none;}
.cta:not(:disabled){background:linear-gradient(180deg,#ffffff 0%,#f3f1e8 100%);color:var(--cream-ink);
box-shadow:0 0 0 6px rgba(180,178,240,0.18),0 0 30px rgba(180,178,240,0.35),0 4px 14px rgba(0,0,0,0.06);}
"""

    body = f"""
<div class="screen">
  <div class="tnav">
    <div style="width:32px"></div>
    <div class="ttl">Câu hỏi của bạn</div>
    <div style="width:32px"></div>
  </div>
  <div class="tbody">
    <p class="hint">Hãy đặt cho lá bài một câu hỏi rõ ràng.<br>Câu hỏi càng cụ thể, lời đáp càng sâu sắc.</p>
    <div class="tawrap">
      <textarea id="q" placeholder="Nhập câu hỏi của bạn…" oninput="upd()"></textarea>
    </div>
    <div class="lbl">Gợi ý</div>
    <div class="prompts" id="prompts"></div>
    <div class="spacer"></div>
    <button class="cta" id="btn" disabled onclick="go()">Tiếp tục</button>
  </div>
</div>
<script>
const PS = {prompts_json};
const pc = document.getElementById('prompts');
PS.forEach(p => {{
  const b = document.createElement('button');
  b.className = 'pb'; b.textContent = p;
  b.onclick = () => {{ document.getElementById('q').value = p; upd(); }};
  pc.appendChild(b);
}});
function upd() {{
  document.getElementById('btn').disabled = !document.getElementById('q').value.trim();
}}
function go() {{
  const v = document.getElementById('q').value.trim();
  if (!v) return;
  
  window.parent.location.href = '/?q=' + encodeURIComponent(v);
}}
</script>
"""
    html = wrap(css, body, dark=False)
    st.components.v1.html(html, height=720, scrolling=False)

# ─────────────────────────────────────────────────────────────
# SCREEN: MEDITATION
# ─────────────────────────────────────────────────────────────

def screen_meditation():
    css = """
html,body{background:linear-gradient(180deg,#F2EFE6 0%,#E6E3DA 100%);}
.screen{display:flex;flex-direction:column;height:100%;}
.tnav{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 10px;}
.ttl{flex:1;text-align:center;font-family:var(--display);font-size:15px;font-weight:400;
letter-spacing:0.02em;color:var(--cream-ink);}
.tnav button{background:none;border:none;font-size:20px;color:var(--cream-ink);padding:4px 8px;opacity:0.7;}
.tbody{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
padding:20px 28px 28px;text-align:center;}
.orb{width:90px;height:90px;border-radius:50%;
background:radial-gradient(circle at 40% 40%,#ffffff,#d8d6ee 45%,#a8a6c8 100%);
box-shadow:0 0 40px rgba(168,166,200,0.45),0 0 80px rgba(168,166,200,0.25);
margin-bottom:36px;animation:drift 6s ease-in-out infinite;}
@keyframes drift{
  0%,100%{transform:translateY(0) scale(1);}
  50%{transform:translateY(-12px) scale(1.04);}
}
.msg{font-family:var(--display);font-size:13px;line-height:1.7;letter-spacing:0.04em;
color:var(--cream-ink);max-width:280px;}
.spacer{flex:1;}
.cta{width:100%;max-width:340px;padding:20px 28px;border-radius:999px;
border:1px solid rgba(108,108,180,0.18);
background:linear-gradient(180deg,#ffffff 0%,#f3f1e8 100%);
box-shadow:0 0 0 6px rgba(180,178,240,0.18),0 0 30px rgba(180,178,240,0.35),0 4px 14px rgba(0,0,0,0.06);
color:var(--cream-ink);font-family:var(--display);font-size:13px;
letter-spacing:0.18em;text-transform:uppercase;margin-bottom:14px;}
.skip{background:none;border:none;color:rgba(108,108,180,0.7);font-family:var(--display);
font-size:11px;letter-spacing:0.18em;text-transform:uppercase;padding:10px 20px;}
"""

    body = """
<div class="screen">
  <div class="tnav">
    <button onclick="back()">←</button>
    <div class="ttl">Thiền định</div>
    <div style="width:32px"></div>
  </div>
  <div class="tbody">
    <div class="spacer"></div>
    <div class="orb"></div>
    <p class="msg">Trước khi đọc bài, hãy thanh lọc tâm trí.<br>
    Một thiền định ngắn sẽ dẫn lối cho bạn.<br>
    Hít thở sâu, giữ câu hỏi trong tim.</p>
    <div class="spacer"></div>
    <button class="cta" onclick="start()">Bắt đầu xáo bài</button>
    <button class="skip" onclick="start()">Bỏ qua</button>
  </div>
</div>
<script>
function go(qs) {
  
  window.parent.location.href = '/?' + qs;
}
function start() { go('step=shuffle'); }
function back()  { go('step=restart'); }
</script>
"""
    html = wrap(css, body, dark=False)
    st.components.v1.html(html, height=720, scrolling=False)

# ─────────────────────────────────────────────────────────────
# SCREEN: SHUFFLE
# ─────────────────────────────────────────────────────────────

def screen_shuffle():
    css = """
html,body{background:radial-gradient(ellipse at 50% 40%,#1c1c2a 0%,#0a0a12 70%);}
.screen{display:flex;flex-direction:column;height:100%;position:relative;}
.tnav{display:flex;align-items:center;justify-content:space-between;
padding:16px 20px 10px;position:relative;z-index:5;}
.ttl{flex:1;text-align:center;font-family:var(--display);font-size:15px;font-weight:400;
letter-spacing:0.06em;text-transform:lowercase;color:var(--ink);}
.tnav button{background:none;border:none;font-size:20px;color:var(--ink);padding:4px 8px;opacity:0.7;}
.tbody{flex:1;display:flex;flex-direction:column;align-items:center;padding:12px 24px 28px;
position:relative;z-index:2;}
.stack{position:relative;width:200px;height:240px;margin-bottom:36px;}
.hint{font-family:var(--serif);font-style:italic;font-size:15px;color:var(--ink-dim);
text-align:center;max-width:260px;line-height:1.55;margin-bottom:28px;}
.spacer{flex:1;}
.cta{width:78%;padding:16px 24px;border-radius:999px;border:1px solid rgba(255,255,255,0.18);
background:rgba(255,255,255,0.06);backdrop-filter:blur(10px);color:var(--ink);
font-family:var(--display);font-size:12px;letter-spacing:0.12em;text-transform:uppercase;
box-shadow:0 0 24px rgba(197,203,245,0.25);}
"""

    body = rays_html(48) + """
<div class="screen">
  <div class="tnav">
    <button onclick="back()">←</button>
    <div class="ttl">xáo bài</div>
    <div style="width:32px"></div>
  </div>
  <div class="tbody">
    <div class="spacer"></div>
    <div class="stack" id="stack"></div>
    <p class="hint">Giữ câu hỏi trong tâm trí.<br>Khi bạn cảm thấy đã đủ, hãy dừng lại.</p>
    <div class="spacer"></div>
    <button class="cta" onclick="done()">Đã đủ — Rút bài</button>
  </div>
</div>
<script>
let tick = 0;
const N = 7;
const stack = document.getElementById('stack');
const cards = [];

for (let i = 0; i < N; i++) {
  const card = document.createElement('div');
  card.style.cssText = `position:absolute;left:50%;top:50%;width:72px;height:115px;border-radius:9px;
background:radial-gradient(ellipse at 50% 45%,#b8bee8 0%,#6e74a8 35%,#2a2c44 75%,#1a1a26 100%);
box-shadow:0 4px 18px rgba(0,0,0,0.6),inset 0 0 12px rgba(0,0,0,0.4);
display:flex;align-items:center;justify-content:center;overflow:hidden;z-index:${i};
transition:transform 0.36s cubic-bezier(0.7,0,0.3,1);`;
  card.innerHTML = `<svg viewBox="0 0 60 96" style="width:65%;height:auto;">
<ellipse cx="24" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
<ellipse cx="36" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
</svg>`;
  stack.appendChild(card);
  cards.push(card);
}

function animate() {
  tick++;
  cards.forEach((card, i) => {
    const seed = (tick * 13 + i * 37) % 360;
    const x = Math.sin(seed * 0.0174) * 18;
    const y = Math.cos(seed * 0.0174) * 14 + (i - 3) * 1.2;
    const r = Math.sin((seed + i * 50) * 0.0174) * 14;
    card.style.transform = `translate(-50%,-50%) translate(${x}px,${y}px) rotate(${r}deg)`;
  });
}

const timer = setInterval(animate, 380);

function go(qs) {
  clearInterval(timer);
  
  window.parent.location.href = '/?' + qs;
}
function done() { go('step=pick'); }
function back() { go('step=restart'); }
</script>
"""
    html = wrap(css, body)
    st.components.v1.html(html, height=720, scrolling=False)

# ─────────────────────────────────────────────────────────────
# SCREEN: PICK
# ─────────────────────────────────────────────────────────────

def screen_pick():
    css = """
html,body{background:radial-gradient(ellipse at 50% 40%,#1c1c2a 0%,#0a0a12 70%);}
.screen{display:flex;flex-direction:column;height:100%;position:relative;}
.tnav{display:flex;align-items:center;justify-content:space-between;
padding:16px 20px 10px;position:relative;z-index:5;}
.ttl{flex:1;text-align:center;font-family:var(--display);font-size:15px;font-weight:400;
letter-spacing:0.06em;text-transform:lowercase;color:var(--ink);}
.tnav button{background:none;border:none;font-size:20px;color:var(--ink);padding:4px 8px;opacity:0.7;}
.hint{padding:10px 24px 0;text-align:center;font-family:var(--serif);font-style:italic;
font-size:15px;color:var(--ink-dim);line-height:1.5;position:relative;z-index:2;}
.counter{font-size:12px;color:var(--ink-faint);font-style:normal;display:block;margin-top:4px;}
.fan-wrap{position:relative;width:100%;height:260px;display:flex;justify-content:center;
align-items:flex-end;flex-shrink:0;position:relative;z-index:2;}
"""

    body = rays_html(48) + """
<div class="screen">
  <div class="tnav">
    <button onclick="back()">←</button>
    <div class="ttl">chọn ba lá</div>
    <div style="width:32px"></div>
  </div>
  <div class="hint">
    Quá khứ &middot; Hiện tại &middot; Tương lai
    <span class="counter" id="counter">Đã chọn 0/3</span>
  </div>
  <div class="fan-wrap" id="fan"></div>
</div>
<script>
const TOTAL = 13;
const LABELS = ['Quá khứ', 'Hiện tại', 'Tương lai'];
let picked = [];

const fan = document.getElementById('fan');
const cardEls = [];

for (let i = 0; i < TOTAL; i++) {
  const mid = (TOTAL - 1) / 2;
  const offset = i - mid;
  const angle = offset * 5.2;
  const x = offset * 19;
  const y = Math.abs(offset) * 4;

  const wrap = document.createElement('div');
  wrap.style.cssText = `position:absolute;bottom:0;left:50%;width:60px;height:96px;
background:none;border:none;padding:0;z-index:${i};
transform:translate(-50%,0) translate(${x}px,${y}px) rotate(${angle}deg);
transition:transform 0.6s cubic-bezier(0.7,0,0.3,1);`;

  const card = document.createElement('div');
  card.style.cssText = `width:60px;height:96px;border-radius:8px;
background:radial-gradient(ellipse at 50% 45%,#b8bee8 0%,#6e74a8 35%,#2a2c44 75%,#1a1a26 100%);
box-shadow:0 4px 12px rgba(0,0,0,0.5),inset 0 0 12px rgba(0,0,0,0.4);
display:flex;align-items:center;justify-content:center;overflow:hidden;
transition:box-shadow 0.4s;position:relative;`;
  card.innerHTML = `<svg viewBox="0 0 60 96" style="width:70%;height:auto;">
<ellipse cx="24" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
<ellipse cx="36" cy="48" rx="14" ry="26" fill="none" stroke="rgba(20,20,30,0.8)" stroke-width="0.8"/>
</svg>`;

  const label = document.createElement('div');
  label.style.cssText = `position:absolute;top:-22px;left:50%;transform:translateX(-50%);
font-family:var(--display);font-size:10px;letter-spacing:0.16em;color:var(--glow-strong);
text-transform:uppercase;white-space:nowrap;display:none;`;

  wrap.appendChild(card);
  wrap.appendChild(label);
  wrap.onclick = () => toggle(i);
  fan.appendChild(wrap);
  cardEls.push({ wrap, card, label, angle, x, y });
}

function toggle(i) {
  const idx = picked.indexOf(i);
  if (idx !== -1) {
    picked.splice(idx, 1);
  } else {
    if (picked.length >= 3) return;
    picked.push(i);
  }
  updateFan();
  if (picked.length === 3) {
    setTimeout(submit, 700);
  }
}

function updateFan() {
  document.getElementById('counter').textContent = `Đã chọn ${picked.length}/3`;
  cardEls.forEach(({ wrap, card, label, angle, x, y }, i) => {
    const pickOrder = picked.indexOf(i);
    const isPicked = pickOrder !== -1;
    if (isPicked) {
      const spacing = 80;
      const startX = -(picked.length - 1) * spacing / 2;
      const px = startX + pickOrder * spacing;
      wrap.style.transform = `translate(-50%,0) translate(${px}px,-110px) rotate(0deg)`;
      wrap.style.zIndex = 50 + pickOrder;
      card.style.boxShadow = '0 0 22px rgba(197,203,245,0.7),0 0 40px rgba(197,203,245,0.35),0 4px 12px rgba(0,0,0,0.5)';
      label.textContent = LABELS[pickOrder];
      label.style.display = 'block';
    } else {
      wrap.style.transform = `translate(-50%,0) translate(${x}px,${y}px) rotate(${angle}deg)`;
      wrap.style.zIndex = i;
      card.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5),inset 0 0 12px rgba(0,0,0,0.4)';
      label.style.display = 'none';
    }
  });
}

function submit() {
  
  window.parent.location.href = '/?picked=' + picked.join(',');
}

function back() {
  
  window.parent.location.href = '/?step=shuffle';
}
</script>
"""
    html = wrap(css, body)
    st.components.v1.html(html, height=720, scrolling=False)

# ─────────────────────────────────────────────────────────────
# SCREEN: READING
# ─────────────────────────────────────────────────────────────

def screen_reading():
    ids = st.session_state.selected_ids
    rev_map = st.session_state.reversed_map
    question = st.session_state.question

    # Build card info
    cards_with_rev = [(TAROT_CARDS[cid], rev_map.get(cid, False)) for cid in ids]

    # Generate readings if not yet done
    if not st.session_state.readings:
        with st.spinner("🔮 Đang giải bài…"):
            st.session_state.readings = generate_readings(question, cards_with_rev)

    readings = st.session_state.readings
    positions = ["Quá khứ", "Hiện tại", "Tương lai"]

    # Build card data for JS
    cards_js = []
    for i, (card, rev) in enumerate(cards_with_rev):
        cards_js.append({
            "name": card["name"],
            "image": card.get("image", ""),
            "reversed": rev,
            "position": positions[i],
            "summary": readings.get(i, ""),
        })
    cards_json = json.dumps(cards_js, ensure_ascii=False)
    question_esc = question.replace('"', '\\"').replace('\n', ' ')

    css = """
html,body{background:radial-gradient(ellipse at 50% 40%,#1c1c2a 0%,#0a0a12 70%);}
.screen{display:flex;flex-direction:column;height:100%;position:relative;}
.tnav{display:flex;align-items:center;justify-content:space-between;
padding:14px 20px 8px;position:relative;z-index:5;}
.ttl{flex:1;text-align:center;font-family:var(--display);font-size:15px;font-weight:400;
letter-spacing:0.06em;text-transform:lowercase;color:var(--ink);}
.tnav button{background:none;border:none;font-size:18px;color:var(--ink);padding:4px 8px;opacity:0.75;}
.qecho{position:relative;z-index:4;text-align:center;font-family:var(--serif);font-style:italic;
font-size:13px;color:var(--ink-dim);padding:0 28px 4px;line-height:1.4;}
.pos-label{position:relative;z-index:4;text-align:center;font-family:var(--display);
font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:var(--glow-strong);
opacity:0.85;padding:4px 0;}
.tbody{flex:1;overflow-y:auto;display:flex;flex-direction:column;align-items:center;
padding:6px 16px 16px;position:relative;z-index:2;scrollbar-width:none;}
.tbody::-webkit-scrollbar{display:none;}

/* Card flip */
.card-scene{width:62%;perspective:1400px;cursor:pointer;margin:4px 0;}
.card-inner{width:100%;position:relative;transform-style:preserve-3d;
transition:transform 1.0s cubic-bezier(0.7,0,0.3,1);}
.card-inner.flipped{transform:rotateY(180deg);}
.card-face,.card-back-face{width:100%;backface-visibility:hidden;-webkit-backface-visibility:hidden;}
.card-back-face{position:absolute;inset:0;transform:rotateY(180deg);}
.card-img{width:100%;aspect-ratio:0.625;border-radius:12px;object-fit:cover;
box-shadow:0 12px 40px rgba(0,0,0,0.6);}

/* Summary panel */
.summary{margin-top:14px;padding:16px 18px;border-radius:14px;
background:rgba(50,50,70,0.55);backdrop-filter:blur(10px);
border:1px solid rgba(255,255,255,0.08);box-shadow:0 0 30px rgba(197,203,245,0.15);
width:92%;animation:fadeUp 0.5s ease;}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
.sum-label{font-family:var(--display);font-size:10px;letter-spacing:0.2em;text-transform:uppercase;
color:var(--glow-strong);opacity:0.8;margin-bottom:6px;}
.sum-text{font-family:var(--serif);font-size:15px;line-height:1.55;color:var(--ink);}

/* Thumbnail strip */
.thumbs{display:flex;gap:14px;margin:14px 0 10px;align-items:flex-end;justify-content:center;}
.thumb-btn{background:none;border:none;padding:0;display:flex;flex-direction:column;
align-items:center;gap:5px;transition:all 0.35s ease;}
.thumb-btn.active{transform:translateY(-4px) scale(1.07);}
.thumb-btn:not(.active){opacity:0.5;}
.thumb-outline{border-radius:7px;outline-offset:3px;}
.thumb-btn.active .thumb-outline{outline:1px solid rgba(232,235,255,0.7);}
.thumb-lbl{font-family:var(--display);font-size:9px;letter-spacing:0.16em;text-transform:uppercase;}
.thumb-btn.active .thumb-lbl{color:var(--glow-strong);}
.thumb-btn:not(.active) .thumb-lbl{color:var(--ink-faint);}

/* Flip button */
.flip-btn{width:78%;padding:15px 24px;border-radius:999px;border:1px solid rgba(255,255,255,0.14);
background:rgba(40,40,55,0.55);backdrop-filter:blur(10px);color:var(--ink);
font-family:var(--display);font-size:12px;letter-spacing:0.14em;text-transform:uppercase;
margin-top:6px;}
.restart-btn{background:none;border:none;color:var(--ink-faint);font-family:var(--display);
font-size:10px;letter-spacing:0.14em;text-transform:uppercase;padding:12px 20px;margin-top:4px;}
"""

    body = f"""
{rays_html(64)}
<div class="screen">
  <div class="tnav">
    <button onclick="back()">←</button>
    <div class="ttl" id="title-lbl"></div>
    <div style="width:32px"></div>
  </div>
  <div class="qecho">"{question_esc}"</div>
  <div class="pos-label" id="pos-lbl"></div>

  <div class="tbody" id="tbody">
    <!-- Big focused card -->
    <div class="card-scene" onclick="flipCurrent()">
      <div class="card-inner" id="card-inner">
        <div class="card-face">{CARD_BACK_BIG}</div>
        <div class="card-back-face">
          <img class="card-img" id="card-img" src="" alt="" onerror="this.style.display='none'">
        </div>
      </div>
    </div>

    <!-- Summary panel (hidden until flip) -->
    <div class="summary" id="summary" style="display:none;">
      <div class="sum-label" id="sum-label"></div>
      <div class="sum-text" id="sum-text"></div>
    </div>

    <!-- Thumbnail strip -->
    <div class="thumbs" id="thumbs"></div>

    <!-- Flip button -->
    <button class="flip-btn" id="flip-btn" onclick="flipCurrent()">Lật bài</button>
    <button class="restart-btn" onclick="restart()">✦ Bói lại</button>
  </div>
</div>

<script>
const CARDS = {cards_json};
let focus = 1;
const flipped = [false, false, false];

const thumbsEl = document.getElementById('thumbs');
CARDS.forEach((c, i) => {{
  const btn = document.createElement('button');
  btn.className = 'thumb-btn' + (i === focus ? ' active' : '');
  btn.onclick = () => setFocus(i);

  const outline = document.createElement('div');
  outline.className = 'thumb-outline';
  outline.innerHTML = `<div style="width:42px;height:67px;border-radius:7px;
background:radial-gradient(ellipse at 50% 45%,#b8bee8 0%,#6e74a8 35%,#2a2c44 75%,#1a1a26 100%);
box-shadow:0 2px 8px rgba(0,0,0,0.5);"
id="thumb-img-${{i}}"></div>`;

  const lbl = document.createElement('div');
  lbl.className = 'thumb-lbl';
  lbl.textContent = c.position;

  btn.appendChild(outline);
  btn.appendChild(lbl);
  thumbsEl.appendChild(btn);
}});

function setFocus(i) {{
  focus = i;
  render();
}}

function flipCurrent() {{
  flipped[focus] = !flipped[focus];
  render();
}}

function render() {{
  const c = CARDS[focus];

  // Title / position
  document.getElementById('title-lbl').textContent = c.name;
  document.getElementById('pos-lbl').textContent = c.position;

  // Card inner
  const inner = document.getElementById('card-inner');
  inner.className = 'card-inner' + (flipped[focus] ? ' flipped' : '');

  // Card image
  const img = document.getElementById('card-img');
  img.src = c.image;
  if (c.reversed) img.style.transform = 'rotate(180deg)';
  else img.style.transform = '';

  // Summary
  const sumEl = document.getElementById('summary');
  if (flipped[focus]) {{
    document.getElementById('sum-label').textContent = c.position + ' · ' + c.name;
    document.getElementById('sum-text').textContent = c.summary;
    sumEl.style.display = 'block';
  }} else {{
    sumEl.style.display = 'none';
  }}

  // Flip button
  document.getElementById('flip-btn').style.display = flipped[focus] ? 'none' : 'block';

  // Thumbnails
  const btns = thumbsEl.querySelectorAll('.thumb-btn');
  btns.forEach((btn, i) => {{
    btn.className = 'thumb-btn' + (i === focus ? ' active' : '');
    const thumbImg = document.getElementById('thumb-img-' + i);
    if (flipped[i] && CARDS[i].image) {{
      thumbImg.style.background = 'none';
      thumbImg.style.padding = '0';
      thumbImg.innerHTML = `<img src="${{CARDS[i].image}}" style="width:42px;height:67px;
object-fit:cover;border-radius:7px;${{CARDS[i].reversed ? 'transform:rotate(180deg);' : ''}}">`;
    }}
  }});
}}

function back() {{
  
  window.parent.location.href = '/?step=pick';
}}

function restart() {{
  
  window.parent.location.href = '/?step=restart';
}}

render();
</script>
"""
    html = wrap(css, body)
    st.components.v1.html(html, height=780, scrolling=False)

# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────

step = st.session_state.step

if step == "question":
    screen_question()
elif step == "meditation":
    screen_meditation()
elif step == "shuffle":
    screen_shuffle()
elif step == "pick":
    screen_pick()
elif step == "reading":
    screen_reading()
else:
    reset_all()
    st.rerun()
