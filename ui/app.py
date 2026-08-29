import json
import os
import urllib.request
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChatUI")

app = FastAPI(title="Enterprise Sovereign AI Chat UI")

SEMANTIC_URL = os.environ.get("SEMANTIC_URL", "http://semantic:8300")

PAGE_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>دستیار هوش مصنوعی سازمانی</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>
  body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
  .chat-bubble-user { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
  .chat-bubble-bot { background-color: #1e293b; border: 1px solid #334155; }
  pre { background-color: #0f172a !important; padding: 12px; border-radius: 8px; font-family: monospace; direction: ltr; text-align: left; overflow-x: auto; margin-top: 8px; margin-bottom: 8px; }
  code { font-family: monospace; background: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
</style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">

  <!-- Header -->
  <header class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-lg">
    <div class="flex items-center gap-3">
      <div class="bg-blue-600 p-2.5 rounded-xl shadow-md shadow-blue-500/20">
        <i class="fa-solid fa-brain text-xl text-white"></i>
      </div>
      <div>
        <h1 class="font-bold text-lg text-slate-100 flex items-center gap-2">
          پلتفرم متمرکز هوش مصنوعی سازمانی
          <span class="text-xs font-medium px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Sovereign AI</span>
        </h1>
        <p class="text-xs text-slate-400">مسیریابی هوشمند سمنتیک + RAG اختصاصی + کنترل چندمستاجری</p>
      </div>
    </div>
    <div class="flex items-center gap-4 text-xs text-slate-400">
      <div class="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>شبکه نودها: آنلاین</span>
      </div>
    </div>
  </header>

  <!-- Main Layout -->
  <main class="flex-1 max-w-5xl w-full mx-auto p-4 flex flex-col gap-4 overflow-hidden">

    <!-- Messages Container -->
    <div id="messages" class="flex-1 bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 overflow-y-auto space-y-6 shadow-inner">
      <!-- Welcome Message -->
      <div class="chat-bubble-bot p-5 rounded-2xl max-w-3xl border border-slate-700/60 shadow-md">
        <div class="flex items-center gap-2 text-blue-400 font-semibold mb-2 text-sm">
          <i class="fa-solid fa-sparkles"></i>
          <span>دستیار هوش مصنوعی سازمان خوش آمدید!</span>
        </div>
        <p class="text-sm text-slate-300 leading-relaxed">
          می‌توانید درباره <b>آیین‌نامه‌ها و قوانین HR</b>، <b>اشکال‌زدایی کدهای نرم‌افزاری</b>، <b>استدلال‌های ریاضی و تحلیل</b> یا سوالات عمومی بپرسید. سیستم به صورت خودکار سوال شما را تحلیل کرده و به مناسب‌ترین مدل هدایت می‌کند.
        </p>
      </div>
    </div>

    <!-- Input Bar -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-3 shadow-xl flex flex-col gap-2">
      <div class="flex items-center gap-3">
        <textarea id="promptInput" rows="2" 
          placeholder="سوال یا پیام خود را بنویسید (مثلاً: سیاست مرخصی استحقاقی چیست؟ یا این کد پایتون را دیباگ کن)..." 
          class="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none px-2"
          onkeydown="if(event.key==='Enter' && !event.shiftKey){ event.preventDefault(); sendQuery(); }"></textarea>
        
        <button id="sendBtn" onclick="sendQuery()" 
          class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-5 py-3 rounded-xl transition shadow-lg shadow-blue-600/20 flex items-center gap-2 disabled:opacity-50">
          <span>ارسال</span>
          <i class="fa-solid fa-paper-plane text-xs"></i>
        </button>
      </div>

      <!-- Quick Action Badges -->
      <div class="flex items-center gap-2 text-xs text-slate-400 px-2 pt-1 border-t border-slate-800/60">
        <span class="text-slate-500">نمونه سوالات:</span>
        <button onclick="setPrompt('سیاست مرخصی استحقاقی شرکت چیست؟')" class="hover:text-blue-400 transition bg-slate-800 px-2 py-1 rounded">📚 قوانین HR</button>
        <button onclick="setPrompt('یک کوئری SQL برای حذف رکوردهای تکراری بنویس')" class="hover:text-blue-400 transition bg-slate-800 px-2 py-1 rounded">💻 برنامه‌نویسی</button>
        <button onclick="setPrompt('اثبات کن جذر ۲ گنگ است')" class="hover:text-blue-400 transition bg-slate-800 px-2 py-1 rounded">🔬 استدلال ریاضی</button>
      </div>
    </div>

  </main>

  <script>
    function setPrompt(text) {
      document.getElementById('promptInput').value = text;
    }

    async function sendQuery() {
      const input = document.getElementById('promptInput');
      const query = input.value.trim();
      if (!query) return;

      const btn = document.getElementById('sendBtn');
      btn.disabled = true;
      input.value = '';

      appendMessage('user', query);

      // Loading Indicator
      const loadingId = appendLoading();

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query })
        });

        const data = await res.json();
        removeLoading(loadingId);

        if (res.status !== 200) {
          appendMessage('bot', '❌ خطا: ' + (data.detail || data.error || 'پاسخی دریافت نشد'));
        } else {
          appendBotResponse(data);
        }
      } catch (err) {
        removeLoading(loadingId);
        appendMessage('bot', '❌ خطای شبکه: ' + err.message);
      }

      btn.disabled = false;
    }

    function appendMessage(role, text) {
      const container = document.getElementById('messages');
      const div = document.createElement('div');
      div.className = role === 'user' ? 'flex justify-start' : 'flex justify-end';

      const bubble = document.createElement('div');
      bubble.className = role === 'user' 
        ? 'chat-bubble-user text-white p-4 rounded-2xl max-w-2xl shadow-md text-sm leading-relaxed' 
        : 'chat-bubble-bot p-5 rounded-2xl max-w-3xl text-slate-200 text-sm leading-relaxed shadow-md border border-slate-800';

      bubble.textContent = text;
      div.appendChild(bubble);
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    function appendBotResponse(data) {
      const container = document.getElementById('messages');
      const div = document.createElement('div');
      div.className = 'flex justify-start';

      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble-bot p-5 rounded-2xl max-w-3xl text-slate-200 text-sm leading-relaxed shadow-md border border-slate-800 w-full space-y-3';

      // Meta Header (Route Badge + Model + Tokens)
      const routeBadges = {
        'rag': '<span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full text-xs">📚 RAG Document QA</span>',
        'coding': '<span class="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full text-xs">💻 Specialist Coding</span>',
        'reasoning': '<span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full text-xs">🔬 Reasoning Engine</span>',
        'general': '<span class="bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full text-xs">💬 General Chat</span>'
      };

      const metaHtml = `
        <div class="flex items-center justify-between text-xs border-b border-slate-800 pb-2 mb-3">
          <div class="flex items-center gap-2">
            ${routeBadges[data.route] || routeBadges['general']}
            <span class="text-slate-400">نقش مدل: <b class="text-slate-200">${data.model}</b></span>
          </div>
          <div class="text-slate-500">
            ${data.usage && data.usage.total_tokens ? 'توکن: ' + data.usage.total_tokens : ''} | اطمینان: ${Math.round((data.confidence || 0.8)*100)}%
          </div>
        </div>
      `;

      // Rendered Answer HTML via Marked.js
      const bodyHtml = `<div>${marked.parse(data.answer || '')}</div>`;

      // RAG Sources Box (if used)
      let sourcesHtml = '';
      if (data.used_rag && data.rag_sources && data.rag_sources.length > 0) {
        sourcesHtml = `
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-xs">
            <div class="font-semibold text-emerald-400 mb-2 flex items-center gap-1.5">
              <i class="fa-solid fa-file-invoice"></i> مراجع و اسناد استخراج شده از RAG:
            </div>
            <div class="space-y-1.5">
              ${data.rag_sources.map((s, i) => `
                <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-300">
                  <span class="text-emerald-400 font-semibold">[منبع ${i+1}]:</span> ${s.content.substring(0, 140)}...
                  <span class="text-slate-500 block text-[10px] mt-1">مرجع: ${s.metadata ? s.metadata.source : 'اسناد داخلی'}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      bubble.innerHTML = metaHtml + bodyHtml + sourcesHtml;
      div.appendChild(bubble);
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    function appendLoading() {
      const container = document.getElementById('messages');
      const id = 'loading-' + Date.now();
      const div = document.createElement('div');
      div.id = id;
      div.className = 'flex justify-start';
      div.innerHTML = `
        <div class="chat-bubble-bot p-4 rounded-2xl text-slate-400 text-sm flex items-center gap-3">
          <i class="fa-solid fa-circle-notch animate-spin text-blue-500 text-lg"></i>
          <span>در حال تحلیل سمنتیک پرامپت و تولید پاسخ...</span>
        </div>
      `;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
      return id;
    }

    function removeLoading(id) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }
  </script>
</body>
</html>
"""


class ChatIn(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE_HTML


@app.post("/api/chat")
def api_chat(body: ChatIn):
    payload = {"query": body.message}
    req = urllib.request.Request(
        SEMANTIC_URL.rstrip("/") + "/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        try:
            err_json = json.loads(err_body)
            raise HTTPException(status_code=e.code, detail=err_json.get("detail") or err_json)
        except Exception:
            raise HTTPException(status_code=e.code, detail=err_body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))