import json
import os
import urllib.request

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Chat UI")

SEMANTIC_URL = os.environ.get("SEMANTIC_URL", "http://semantic:8300")

PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>دستیار سازمانی</title>
<style>
body { font-family: Tahoma, Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }
.card { max-width: 720px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.08); padding: 20px; }
h1 { font-size: 20px; margin: 0 0 16px; color: #333; }
#messages { height: 380px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fafafa; }
.msg { margin-bottom: 10px; padding: 8px 12px; border-radius: 8px; white-space: pre-wrap; line-height: 1.6; }
.user { background: #e7f3ff; text-align: left; }
.bot { background: #f0fdf4; text-align: right; }
.meta { font-size: 11px; color: #888; margin-top: 4px; }
.row { display: flex; gap: 8px; }
input[type=text] { flex: 1; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }
button { padding: 10px 18px; background: #2563eb; color: #fff; border: 0; border-radius: 8px; cursor: pointer; font-size: 14px; }
button:disabled { opacity: .5; }
</style>
</head>
<body>
<div class="card">
<h1>دستیار سازمانی (RAG + Semantic Routing)</h1>
<div id="messages"></div>
<div class="row">
  <input type="text" id="q" placeholder="سوال خود را بنویسید..." onkeydown="if(event.key==='Enter')send()">
  <button id="btn" onclick="send()">ارسال</button>
</div>
</div>
<script>
async function send() {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  add('user', q, '');
  document.getElementById('q').value = '';
  const btn = document.getElementById('btn');
  btn.disabled = true;
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: q})
    });
    const d = await r.json();
    const meta = 'مسیر: ' + d.route + ' | مدل: ' + d.model + ' | RAG: ' + (d.used_rag ? 'بله' : 'خیر') +
      (d.usage && d.usage.total_tokens ? ' | توکن: ' + d.usage.total_tokens : '');
    add('bot', d.answer || d.error || 'پاسخی دریافت نشد', meta);
  } catch (e) {
    add('bot', 'خطا: ' + e.message, '');
  }
  btn.disabled = false;
}
function add(role, text, meta) {
  const box = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    m.textContent = meta;
    div.appendChild(m);
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}
</script>
</body>
</html>
"""


class ChatIn(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.post("/api/chat")
def api_chat(body: ChatIn):
    payload = {"query": body.message}
    req = urllib.request.Request(
        SEMANTIC_URL.rstrip("/") + "/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())