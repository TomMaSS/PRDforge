"""PRD Forge Web UI — FastAPI application."""

import os
import sys
import uuid as _uuid
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.settings import DEFAULT_PROJECT_SETTINGS, validate_settings

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    yield
    if pool:
        await pool.close()


app = FastAPI(title="PRD Forge UI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


def dt(v):
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def row_dict(r):
    d = dict(r)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRD Forge</title>
<link rel="stylesheet" href="/static/fonts.css">
<script src="/static/marked.min.js"></script>
<script src="/static/highlight.min.js"></script>
<link rel="stylesheet" href="/static/github-dark.min.css" id="hljs-theme">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#2b2d35;--surface:#33353f;--secondary:#3c3e4a;--border:#44465a;--border-muted:#52546a;
  --text:#e2e4ea;--text-sec:#9496ad;--text-muted:#7a7c94;
  --accent:#6366f1;
  --approved:#10b981;--review:#f59e0b;--in_progress:#3b82f6;--draft:#7a7c94;--outdated:#ef4444;
  --notes-accent:#f59e0b;
}
[data-theme="light"]{
  --bg:#f5f5f7;--surface:#ffffff;--secondary:#e8e8ed;--border:#d1d1d6;--border-muted:#c7c7cc;
  --text:#1d1d1f;--text-sec:#636366;--text-muted:#8e8e93;
  --accent:#4f46e5;
  --approved:#059669;--review:#d97706;--in_progress:#2563eb;--draft:#8e8e93;--outdated:#dc2626;
  --notes-accent:#d97706;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;height:100vh;overflow:hidden}
code,pre{font-family:'JetBrains Mono',monospace}

/* Nav Rail */
.nav-rail{width:140px;min-width:140px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;justify-content:space-between;padding:12px 8px}
.nav-icons,.nav-bottom{display:flex;flex-direction:column;gap:2px}
.nav-icon{height:34px;display:flex;align-items:center;gap:8px;padding:0 10px;border-radius:8px;cursor:pointer;color:var(--text-sec);transition:all .15s;font-size:13px;white-space:nowrap}
.nav-icon:hover{background:var(--secondary);color:var(--text)}
.nav-icon.active{background:var(--accent);color:#fff}
.nav-icon svg{width:16px;height:16px;flex-shrink:0}
.nav-icon .nav-label{overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
body.collapsed .nav-rail{width:48px;min-width:48px;padding:12px 6px;align-items:center}
body.collapsed .nav-icon{width:36px;height:36px;padding:0;justify-content:center;gap:0}
body.collapsed .nav-label{display:none}

/* Sidebar Panel */
.sidebar-panel{width:280px;min-width:280px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;transition:width .2s,min-width .2s}
body.collapsed .sidebar-panel{width:0;min-width:0;overflow:hidden}

.sidebar-header{padding:16px;border-bottom:1px solid var(--border)}
.sidebar-header h1{font-size:18px;font-weight:700;margin-bottom:4px}
.sidebar-header .meta{font-size:12px;color:var(--text-sec)}
.sidebar-header select{width:100%;margin-top:8px;padding:6px 8px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px}
.sidebar-header .export-btn{display:inline-block;margin-top:8px;padding:4px 12px;background:var(--accent);color:#fff;border-radius:6px;font-size:12px;text-decoration:none;font-weight:500}
.filters{padding:8px 12px;display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--border);align-items:center}
.chip{padding:2px 8px;border-radius:12px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:var(--text-sec);transition:all .15s}
.chip:hover,.chip.active{border-color:var(--accent);color:var(--accent)}
.tag-dropdown{position:relative;display:inline-block}
.tag-dropdown-btn{padding:2px 8px;border-radius:12px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:var(--text-sec);transition:all .15s;background:none;font-family:inherit;display:flex;align-items:center;gap:4px}
.tag-dropdown-btn:hover,.tag-dropdown-btn.active{border-color:var(--accent);color:var(--accent)}
.tag-dropdown-btn svg{width:10px;height:10px}
.tag-dropdown-menu{display:none;position:absolute;top:calc(100% + 4px);left:0;background:var(--secondary);border:1px solid var(--border);border-radius:8px;padding:6px;min-width:220px;max-height:300px;z-index:100;box-shadow:0 4px 12px rgba(0,0,0,.3)}
.tag-dropdown-menu.open{display:flex;flex-direction:column;gap:6px}
.tag-search{width:100%;padding:5px 8px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:12px;font-family:inherit;outline:none;box-sizing:border-box}
.tag-search:focus{border-color:var(--accent)}
.tag-search::placeholder{color:var(--text-muted)}
.tag-list{display:flex;flex-wrap:wrap;gap:4px;overflow-y:auto;max-height:220px;padding:2px 0}
.tag-item{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;cursor:pointer;transition:all .15s;border:1.5px solid transparent;user-select:none}
.tag-item:hover{opacity:.85}
.tag-item.selected{border-color:#fff3;box-shadow:0 0 0 1px rgba(255,255,255,.15)}
.tag-item.all-tag{background:var(--bg);color:var(--text-sec);border:1px solid var(--border)}
.tag-item.all-tag.selected{border-color:var(--accent);color:var(--accent)}
.tag-count{background:var(--accent);color:#fff;border-radius:8px;padding:0 5px;font-size:10px;font-weight:600;min-width:14px;text-align:center}
.section-list{flex:1;overflow-y:auto;padding:4px 0}
.section-item{padding:10px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background .1s}
.section-item:hover{background:var(--secondary)}
.section-item.active{background:var(--secondary);border-left:3px solid var(--accent)}
.section-item .title{font-size:14px;font-weight:500;display:flex;align-items:center;gap:6px}
.section-item .meta-line{font-size:11px;color:var(--text-muted);margin-top:2px}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0}

/* Main Panel */
.main{flex:1;overflow-y:auto;padding:40px 56px;display:flex;justify-content:center;position:relative}
.main.graph-mode{padding:0;overflow:hidden}
.content-wrap{max-width:780px;width:100%}
.section-title{font-size:26px;font-weight:700;margin-bottom:8px;color:var(--text)}
.meta-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:16px;font-size:13px;color:var(--text-sec)}
.meta-row .badge{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;color:#fff}
.summary-box{padding:16px 20px;border:1px solid var(--border);border-radius:8px;margin-bottom:20px;font-size:15px;line-height:1.75;color:var(--text-sec);background:var(--surface)}
.notes-box{padding:16px 20px;border:1px solid var(--notes-accent);border-radius:8px;margin-bottom:20px;font-size:15px;line-height:1.75;background:rgba(245,158,11,0.08);color:#e8c060}
.notes-box .label{font-weight:600;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between}
.notes-box textarea{width:100%;min-height:80px;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.25);border-radius:6px;color:#e8c060;font-family:'Inter',sans-serif;font-size:14px;line-height:1.7;padding:10px 12px;resize:vertical;margin-top:8px}
.notes-box textarea:focus{outline:none;border-color:var(--notes-accent)}
.notes-box textarea::placeholder{color:rgba(232,192,96,0.4)}
.notes-actions{display:flex;gap:8px;margin-top:8px;align-items:center}
.notes-actions button{padding:4px 14px;border-radius:6px;font-size:12px;font-weight:500;cursor:pointer;border:none;transition:all .15s}
.notes-save{background:var(--notes-accent);color:#1a1a1a}
.notes-save:hover{opacity:0.85}
.notes-cancel{background:var(--secondary);color:var(--text-sec);border:1px solid var(--border) !important}
.notes-status{font-size:12px;color:var(--approved);opacity:0;transition:opacity .3s}
.notes-status.show{opacity:1}
.add-notes-btn{padding:6px 14px;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid rgba(245,158,11,0.3);background:rgba(245,158,11,0.06);color:#e8c060;margin-bottom:20px;transition:all .15s}
.add-notes-btn:hover{background:rgba(245,158,11,0.12);border-color:var(--notes-accent)}
.tag-chip{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;background:var(--secondary);color:var(--text-sec);margin-right:4px}

/* Prose */
.prose{line-height:1.85;font-size:16px;color:var(--text)}
.prose h1,.prose h2,.prose h3{font-weight:600;color:var(--text)}
.prose h1{font-size:22px;margin:32px 0 12px}.prose h2{font-size:19px;margin:28px 0 10px}.prose h3{font-size:17px;margin:24px 0 8px}
.prose p{margin:12px 0}
.prose ul,.prose ol{margin:8px 0 20px 20px;color:var(--text-sec)}
.prose li{margin:8px 0;color:var(--text)}
.prose li::marker{color:var(--text-muted)}
.prose ul+p>strong:first-child,.prose ol+p>strong:first-child{display:inline-block;margin-top:8px}
.prose p>strong:only-child{display:block;margin-top:20px;font-size:17px;color:var(--text)}
.prose code{background:var(--secondary);padding:2px 6px;border-radius:4px;font-size:13px}
.prose pre{background:var(--code-bg,#252730);border:1px solid var(--border);border-radius:8px;padding:16px 20px;overflow-x:auto;margin:20px 0}
.prose pre code{background:none;padding:0;font-family:'JetBrains Mono',monospace;font-size:13px}
[data-theme="light"]{--code-bg:#f6f8fa}
[data-theme="light"] .hljs{background:#f6f8fa !important;color:#24292e}
[data-theme="light"] .graph-popup{box-shadow:0 8px 30px rgba(0,0,0,.15)}
[data-theme="light"] select,[data-theme="light"] input,[data-theme="light"] textarea{color:var(--text);background:var(--surface);border-color:var(--border)}
.prose table{width:100%;border-collapse:collapse;margin:16px 0}
.prose th,.prose td{padding:8px 12px;border:1px solid var(--border);text-align:left;font-size:13px}
.prose th{background:var(--surface);font-weight:600}
.prose blockquote{border-left:3px solid var(--accent);padding-left:12px;margin:16px 0;color:var(--text-sec)}
.prose strong{font-weight:600;color:var(--text)}
.prose a{color:var(--accent)}
.prose hr{border:none;border-top:1px solid var(--border);margin:24px 0}

/* Deps & Revisions */
.deps-panel{margin-top:24px;padding:16px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
.deps-panel h3{font-size:14px;font-weight:600;margin-bottom:8px}
.dep-chip{display:inline-block;padding:4px 10px;margin:2px;border-radius:6px;font-size:12px;cursor:pointer;background:var(--secondary);color:var(--accent);border:1px solid var(--border);transition:all .15s}
.dep-chip:hover{border-color:var(--accent)}
.dep-type{font-size:10px;color:var(--text-muted);margin-left:4px}
.rev-table{width:100%;margin-top:8px;font-size:13px}
.rev-table th,.rev-table td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--border)}
.rev-table th{color:var(--text-sec);font-weight:500}

/* Changelog Tab */
.changelog-list{padding:8px 16px;overflow-y:auto;flex:1}
.cl-item{padding:8px 0;border-bottom:1px solid var(--border);font-size:13px}
.cl-item .cl-section{color:var(--accent);font-weight:500}
.cl-item .cl-desc{color:var(--text-sec)}
.cl-item .cl-time{color:var(--text-muted);font-size:11px}

/* Deps Graph Tab */
.deps-graph{padding:16px;overflow-y:auto;flex:1;font-size:13px}
.dep-row{display:flex;align-items:center;gap:4px;padding:7px 10px;border-bottom:1px solid var(--border);font-size:11px;flex-wrap:wrap}
.dep-row:hover{background:var(--secondary)}
.dep-from,.dep-to{font-weight:500;color:var(--text);cursor:pointer}
.dep-from:hover,.dep-to:hover{color:var(--accent)}
.dep-arrow{color:var(--accent);flex-shrink:0}
.dep-type-lbl{padding:1px 5px;border-radius:4px;font-size:9px;font-weight:500;flex-shrink:0;margin-left:auto}
.dep-type-references{background:rgba(99,102,241,0.12);color:#818cf8}
.dep-type-implements{background:rgba(59,130,246,0.12);color:#60a5fa}
.dep-type-extends{background:rgba(16,185,129,0.12);color:#34d399}
.dep-type-blocks{background:rgba(239,68,68,0.12);color:#f87171}
.graph-wrap{position:absolute;inset:0;overflow:hidden}
.graph-wrap canvas{width:100%;height:100%;display:block}
.graph-legend{position:absolute;bottom:12px;left:12px;display:flex;gap:12px;font-size:11px;color:#9496ad;background:rgba(43,45,53,0.9);padding:6px 14px;border-radius:8px;backdrop-filter:blur(4px)}
.graph-legend span{display:flex;align-items:center;gap:4px}
.graph-legend i{width:20px;height:3px;border-radius:2px;display:inline-block}
.graph-status-legend{position:absolute;top:12px;right:12px;display:flex;flex-direction:column;gap:4px;font-size:11px;color:#9496ad;background:rgba(43,45,53,0.9);padding:8px 12px;border-radius:8px;backdrop-filter:blur(4px)}
.graph-status-legend span{display:flex;align-items:center;gap:6px}
.graph-status-legend i{width:10px;height:10px;border-radius:50%;display:inline-block}
.graph-popup{position:absolute;width:300px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:0;box-shadow:0 8px 30px rgba(0,0,0,.5);z-index:200;overflow:hidden}
.graph-popup-header{padding:12px 14px;cursor:pointer;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--border);transition:background .1s}
.graph-popup-header:hover{background:var(--secondary)}
.graph-popup-header .status-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.graph-popup-header h4{font-size:14px;font-weight:600;color:var(--accent);margin:0;flex:1}
.graph-popup-header .open-icon{color:var(--text-muted);font-size:11px}
.graph-popup-body{padding:10px 14px;font-size:12px;color:var(--text-sec);line-height:1.5;max-height:180px;overflow-y:auto}
.graph-popup-meta{padding:8px 14px;border-top:1px solid var(--border);font-size:11px;color:var(--text-muted);display:flex;gap:8px;flex-wrap:wrap}
.graph-popup-tags{display:flex;gap:3px;flex-wrap:wrap;padding:0 14px 10px}
.graph-popup-tags span{padding:1px 6px;border-radius:4px;font-size:10px;color:#fff;font-weight:500}

/* Inline comments */
.comment-hl{background:rgba(245,158,11,0.18);border-bottom:2px solid var(--notes-accent);cursor:pointer;transition:background .15s;border-radius:2px}
.comment-hl:hover,.comment-hl.active{background:rgba(245,158,11,0.35)}
.comment-hl.resolved{background:rgba(16,185,129,0.08);border-bottom-color:var(--approved);opacity:0.7}
.comment-btn{position:absolute;background:var(--notes-accent);color:#1a1a1a;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;z-index:50;box-shadow:0 4px 12px rgba(0,0,0,0.4);white-space:nowrap}
.comment-btn:hover{opacity:0.85}
.comment-popover{position:fixed;width:320px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;box-shadow:0 8px 30px rgba(0,0,0,0.4);z-index:200;font-size:13px}
.comment-popover textarea{width:100%;min-height:70px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-family:'Inter',sans-serif;font-size:13px;line-height:1.6;resize:vertical}
.comment-popover textarea:focus{outline:none;border-color:var(--accent)}
.comment-popover .quoted{font-size:12px;color:var(--text-muted);margin-bottom:10px;padding:6px 8px;background:var(--secondary);border-radius:4px;border-left:3px solid var(--notes-accent)}
.comments-panel{margin-top:24px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}
.comments-panel-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.comments-panel-header h3{font-size:14px;font-weight:600;color:var(--notes-accent)}
.comment-card{padding:12px 16px;border-bottom:1px solid var(--border);transition:background .1s}
.comment-card:hover{background:var(--secondary)}
.comment-card.resolved-card{opacity:0.5}
.comment-card .anchor{font-size:12px;color:var(--text-muted);margin-bottom:4px}
.comment-card .anchor em{color:var(--notes-accent)}
.comment-card .body{font-size:13px;line-height:1.6;margin-bottom:6px}
.comment-card .actions{display:flex;gap:8px;font-size:11px}
.comment-card .actions button{background:none;border:1px solid var(--border);color:var(--text-sec);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:11px}
.comment-card .actions button:hover{border-color:var(--accent);color:var(--text)}
.comment-card .actions .del-btn:hover{border-color:var(--outdated);color:var(--outdated)}

/* Comment replies */
.reply-card{margin-left:16px;padding:8px 12px;border-left:2px solid var(--border-muted);font-size:12px;color:var(--text-sec)}
.reply-card .reply-author{font-weight:600;font-size:11px;margin-bottom:2px}
.reply-card .reply-author.claude{color:var(--accent)}
.reply-card .reply-author.user{color:var(--notes-accent)}
.reply-form{margin-left:16px;margin-top:4px;display:flex;gap:6px}
.reply-form textarea{flex:1;min-height:36px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px;font-family:'Inter',sans-serif;font-size:12px;resize:vertical}
.reply-form button{padding:4px 10px;border-radius:4px;font-size:11px;font-weight:500;cursor:pointer;border:none;background:var(--accent);color:#fff}

/* Settings panel */
.settings-panel{padding:0;overflow-y:auto;flex:1}
.settings-title{padding:14px 16px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600;color:var(--text)}
.setting-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:1px solid var(--border)}
.setting-info{flex:1;min-width:0}
.setting-info label{font-size:12px;font-weight:500;color:var(--text);cursor:pointer;display:block}
.setting-info .setting-desc{font-size:10px;color:var(--text-muted);margin-top:2px}
.toggle{position:relative;width:36px;min-width:36px;height:20px;cursor:pointer;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0}
.toggle .slider{position:absolute;inset:0;background:var(--secondary);border-radius:10px;transition:.2s;border:1px solid var(--border)}
.toggle .slider:before{content:'';position:absolute;height:14px;width:14px;left:2px;bottom:2px;background:var(--text-sec);border-radius:50%;transition:.2s}
.toggle input:checked+.slider{background:var(--accent);border-color:var(--accent)}
.toggle input:checked+.slider:before{transform:translateX(16px);background:#fff}
.settings-note{padding:12px 16px;font-size:11px;color:var(--text-muted);line-height:1.5}

/* Empty state */
.empty{display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:16px}

/* Tab content */
.tab-content{display:none;flex:1;overflow-y:auto}
.tab-content.active{display:flex;flex-direction:column}
</style>
</head>
<body>
<div class="nav-rail" id="navRail">
  <div class="nav-icons">
    <div class="nav-icon active" data-tab="sections" onclick="switchTab('sections')" title="Sections">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 13H8"/><path d="M16 17H8"/><path d="M16 13h-2"/></svg>
      <span class="nav-label">Sections</span>
    </div>
    <div class="nav-icon" data-tab="comments" onclick="switchTab('comments')" title="Comments">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="nav-label">Comments</span>
    </div>
    <div class="nav-icon" data-tab="deps" onclick="switchTab('deps')" title="Deps">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" x2="6" y1="3" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>
      <span class="nav-label">Dependencies</span>
    </div>
    <div class="nav-icon" data-tab="changelog" onclick="switchTab('changelog')" title="Changelog">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
      <span class="nav-label">Changelog</span>
    </div>
  </div>
  <div class="nav-bottom">
    <div class="nav-icon" onclick="toggleTheme()" id="themeBtn" title="Toggle theme">
      <svg id="themeIcon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
      <span class="nav-label" id="themeLabel">Light</span>
    </div>
    <div class="nav-icon" data-tab="settings" onclick="switchTab('settings')" title="Settings">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      <span class="nav-label">Settings</span>
    </div>
    <div class="nav-icon" onclick="toggleSidebar()" id="collapseBtn" title="Collapse">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
      <span class="nav-label">Collapse</span>
    </div>
  </div>
</div>
<div class="sidebar-panel" id="sidebarPanel">
  <div class="sidebar-header">
    <h1 id="projName">PRD Forge</h1>
    <div class="meta" id="projMeta"></div>
    <select id="projSelect" onchange="switchProject(this.value)"></select>
    <div style="display:flex;gap:8px;margin-top:8px">
      <a class="export-btn" id="exportBtn" href="#" download>Export</a>
      <a class="export-btn" href="#" onclick="loadFullPRD();return false" style="background:var(--secondary);border:1px solid var(--border)">View Full PRD</a>
    </div>
  </div>
  <div class="tab-content active" id="tab-sections">
    <div class="filters" id="filters"></div>
    <div class="section-list" id="sectionList"></div>
  </div>
  <div class="tab-content" id="tab-comments">
    <div class="filters" id="commentFilters"></div>
    <div class="section-list" id="globalCommentsList"></div>
  </div>
  <div class="tab-content" id="tab-deps">
    <div class="deps-graph" id="depsGraph"></div>
  </div>
  <div class="tab-content" id="tab-changelog">
    <div class="changelog-list" id="changelogList"></div>
  </div>
  <div class="tab-content" id="tab-settings">
    <div class="settings-panel" id="settingsPanel">
      <div class="settings-title">Project Settings</div>
      <div class="setting-row">
        <div class="setting-info">
          <label for="settingClaudeReplies">Claude comment replies</label>
          <div class="setting-desc">Auto-reply to comments before resolving</div>
        </div>
        <label class="toggle">
          <input type="checkbox" id="settingClaudeReplies" onchange="saveSetting('claude_comment_replies',this.checked)">
          <span class="slider"></span>
        </label>
      </div>
      <div class="settings-note">Settings are per-project and synced with MCP tools. Changes take effect immediately.</div>
    </div>
  </div>
</div>
<div class="main">
  <div class="content-wrap" id="mainContent">
    <div class="empty">Select a section to view</div>
  </div>
</div>

<script>
// Theme
function applyTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  const icon=document.getElementById('themeIcon');
  const label=document.getElementById('themeLabel');
  if(t==='light'){
    icon.innerHTML='<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>';
    label.textContent='Dark';
  }else{
    icon.innerHTML='<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>';
    label.textContent='Light';
  }
}
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme')||'dark';
  const next=cur==='dark'?'light':'dark';
  localStorage.setItem('prdforge-theme',next);
  applyTheme(next);
}
applyTheme(localStorage.getItem('prdforge-theme')||'dark');

const renderer=new marked.Renderer();
renderer.code=function({text,lang}){const hl=lang&&hljs.getLanguage(lang)?hljs.highlight(text,{language:lang}).value:hljs.highlightAuto(text).value;return `<pre><code class="hljs language-${lang||''}">${hl}</code></pre>`;};
marked.setOptions({renderer});
const STATUS_COLORS={approved:'var(--approved)',review:'var(--review)',in_progress:'var(--in_progress)',draft:'var(--draft)',outdated:'var(--outdated)'};
let currentProject=null,projectData=null,activeSection=null,activeFilter=null;

async function init(){
  const res=await fetch('/api/projects');
  const projects=await res.json();
  const sel=document.getElementById('projSelect');
  sel.innerHTML=projects.map(p=>`<option value="${p.slug}">${p.name}</option>`).join('');
  if(projects.length)switchProject(projects[0].slug);
}

async function switchProject(slug){
  currentProject=slug;
  const res=await fetch(`/api/projects/${slug}`);
  projectData=await res.json();
  document.getElementById('projName').textContent=projectData.project.name;
  document.getElementById('projMeta').textContent=`v${projectData.project.version} · ${projectData.stats.sections} sections · ${projectData.stats.words} words`;
  document.getElementById('exportBtn').href=`/api/projects/${slug}/export`;
  document.getElementById('exportBtn').download=`${slug}.md`;
  renderFilters();
  renderSections();
  renderChangelog();
  renderDepsGraph();
  loadGlobalComments();
  activeSection=null;activeFilter=null;activeTags=[];
  clearGraph();
  document.getElementById('mainContent').innerHTML='<div class="empty">Select a section to view</div>';
}

let activeTags=[];
const TAG_COLORS=['#6c5ce7','#636e72','#00b894','#e17055','#0984e3','#d63031','#fdcb6e','#00cec9','#e84393','#55efc4','#74b9ff','#fab1a0','#a29bfe','#ffeaa7','#dfe6e9','#b2bec3','#fd79a8','#81ecec'];
function tagColor(t){let h=0;for(let i=0;i<t.length;i++)h=t.charCodeAt(i)+((h<<5)-h);return TAG_COLORS[Math.abs(h)%TAG_COLORS.length]}
function renderFilters(){
  const statuses=[...new Set(projectData.sections.map(s=>s.status))];
  const tags=[...new Set(projectData.sections.flatMap(s=>s.tags||[]))].sort();
  let html=statuses.map(s=>`<span class="chip ${activeFilter===s?'active':''}" onclick="toggleFilter('${s}')">${s.replace('_',' ')}</span>`).join('');
  if(tags.length){
    const count=activeTags.length;
    html+=`<div class="tag-dropdown"><button class="tag-dropdown-btn ${count?'active':''}" onclick="toggleTagMenu(event)">Tags${count?` <span class='tag-count'>${count}</span>`:''} <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 5l3 3 3-3"/></svg></button>`;
    html+=`<div class="tag-dropdown-menu" id="tagMenu">`;
    html+=`<input class="tag-search" type="text" placeholder="Search tags..." oninput="filterTagList(this.value)">`;
    html+=`<div class="tag-list" id="tagList">`;
    html+=`<span class="tag-item all-tag ${!activeTags.length?'selected':''}" onclick="clearTags()">All</span>`;
    html+=tags.map(t=>{const bg=tagColor(t);return`<span class="tag-item ${activeTags.includes(t)?'selected':''}" style="background:${bg};color:#fff" onclick="toggleTag('${t}')" data-tag="${t}">${t}</span>`}).join('');
    html+=`</div></div></div>`;
  }
  document.getElementById('filters').innerHTML=html;
}

function toggleFilter(f){activeFilter=activeFilter===f?null:f;renderFilters();renderSections()}
function toggleTag(t){const i=activeTags.indexOf(t);if(i>=0)activeTags.splice(i,1);else activeTags.push(t);renderFilters();renderSections();reopenTagMenu()}
function clearTags(){activeTags=[];renderFilters();renderSections();reopenTagMenu()}
function reopenTagMenu(){const m=document.getElementById('tagMenu');if(m)m.classList.add('open')}
function toggleTagMenu(e){e.stopPropagation();const m=document.getElementById('tagMenu');m.classList.toggle('open')}
function filterTagList(q){const items=document.querySelectorAll('#tagList .tag-item[data-tag]');q=q.toLowerCase();items.forEach(el=>{el.style.display=el.dataset.tag.toLowerCase().includes(q)?'':'none'})}
document.addEventListener('click',e=>{const m=document.getElementById('tagMenu');if(m&&!m.contains(e.target)&&!e.target.closest('.tag-dropdown-btn'))m.classList.remove('open')})

function renderSections(){
  let secs=projectData.sections;
  if(activeFilter)secs=secs.filter(s=>s.status===activeFilter);
  if(activeTags.length)secs=secs.filter(s=>activeTags.some(t=>(s.tags||[]).includes(t)));
  document.getElementById('sectionList').innerHTML=secs.map(s=>`
    <div class="section-item ${activeSection===s.slug?'active':''}" onclick="loadSection('${s.slug}')">
      <div class="title"><span class="status-dot" style="background:${STATUS_COLORS[s.status]||'var(--draft)'}"></span>${s.title}</div>
      <div class="meta-line">${s.section_type} · ${s.word_count} words · ${s.revision_count||0} revs${(s.tags||[]).length?' · '+s.tags.join(', '):''}</div>
    </div>`).join('');
}

function renderChangelog(){
  const cl=projectData.changelog||[];
  document.getElementById('changelogList').innerHTML=cl.length?cl.map(c=>`
    <div class="cl-item">
      <span class="cl-section">${c.section_title}</span> rev ${c.revision_number}
      <div class="cl-desc">${c.change_description||'—'}</div>
      <div class="cl-time">${new Date(c.created_at).toLocaleString()}</div>
    </div>`).join(''):'<div class="empty">No revisions yet</div>';
}

function renderDepsGraph(){
  const deps=projectData.dependencies||[];
  const container=document.getElementById('depsGraph');
  if(!deps.length){container.innerHTML='<div class="empty" style="padding:40px">No dependencies</div>';return}
  let html=deps.map(d=>{
    const t=d.dependency_type||'references';
    return `<div class="dep-row">
      <span class="dep-from" onclick="loadSection('${d.from_slug}')">${d.from_slug}</span>
      <span class="dep-arrow">→</span>
      <span class="dep-to" onclick="loadSection('${d.to_slug}')">${d.to_slug}</span>
      <span class="dep-type-lbl dep-type-${t}">${t}</span>
    </div>`;
  }).join('');
  container.innerHTML=html;
}

function wrapTextInCircle(ctx,text,cx,cy,r,fontSize){
  const words=text.split(/\s+/);const lh=fontSize*1.2;const lines=[];let line='';
  for(const w of words){const test=line?line+' '+w:w;if(ctx.measureText(test).width>r*1.6&&line){lines.push(line);line=w}else line=test}
  if(line)lines.push(line);
  if(lines.length===1&&ctx.measureText(lines[0]).width>r*1.6){const t=lines[0];lines.length=0;const mid=Math.ceil(t.length/2);let bp=t.lastIndexOf(' ',mid);if(bp<1)bp=mid;lines.push(t.slice(0,bp).trim());lines.push(t.slice(bp).trim())}
  const maxLines=3;if(lines.length>maxLines){lines.length=maxLines;lines[maxLines-1]=lines[maxLines-1].slice(0,-1)+'…'}
  const startY=cy-((lines.length-1)*lh)/2;
  lines.forEach((l,i)=>ctx.fillText(l,cx,startY+i*lh));
}
let _graphAnim=null,_graphObserver=null;
function clearGraph(){
  if(_graphAnim){cancelAnimationFrame(_graphAnim);_graphAnim=null}
  if(_graphObserver){_graphObserver.disconnect();_graphObserver=null}
  document.querySelector('.main').classList.remove('graph-mode');
}
function showMainGraph(){
  if(_graphAnim){cancelAnimationFrame(_graphAnim);_graphAnim=null}
  if(_graphObserver){_graphObserver.disconnect();_graphObserver=null}
  const deps=projectData.dependencies||[];
  const mainEl=document.querySelector('.main');
  const mc=document.getElementById('mainContent');
  if(!deps.length){mainEl.classList.remove('graph-mode');mc.innerHTML='<div class="empty">No dependencies defined</div>';return}
  mainEl.classList.add('graph-mode');
  mc.innerHTML=`<div class="graph-wrap"><canvas id="mainGraphCanvas"></canvas><div class="graph-legend"><span><i style="background:#818cf8"></i>references</span><span><i style="background:#60a5fa"></i>implements</span><span><i style="background:#34d399"></i>extends</span><span><i style="background:#f87171"></i>blocks</span></div><div class="graph-status-legend"><span><i style="background:#9496ad"></i>draft</span><span><i style="background:#6366f1"></i>in progress</span><span><i style="background:#f59e0b"></i>review</span><span><i style="background:#10b981"></i>approved</span><span><i style="background:#ef4444"></i>outdated</span></div></div>`;
  const wrap=mc.querySelector('.graph-wrap');
  const canvas=document.getElementById('mainGraphCanvas');
  const ctx=canvas.getContext('2d');
  const dpr=window.devicePixelRatio||1;
  function resize(){const r=wrap.getBoundingClientRect();canvas.width=r.width*dpr;canvas.height=r.height*dpr;canvas.style.width=r.width+'px';canvas.style.height=r.height+'px';ctx.setTransform(dpr,0,0,dpr,0,0)}
  resize();
  const W=()=>canvas.width/dpr,H=()=>canvas.height/dpr;
  const EDGE_COLORS={references:'#818cf8',implements:'#60a5fa',extends:'#34d399',blocks:'#f87171'};
  const NODE_COLORS={draft:'#9496ad',in_progress:'#6366f1',review:'#f59e0b',approved:'#10b981',outdated:'#ef4444'};
  const slugSet=new Set();
  deps.forEach(d=>{slugSet.add(d.from_slug);slugSet.add(d.to_slug)});
  const nodeMap={};
  const secs=projectData.sections||[];
  slugSet.forEach(slug=>{
    const s=secs.find(x=>x.slug===slug)||{};
    nodeMap[slug]={slug,title:s.title||slug,status:s.status||'draft',x:W()/2+(Math.random()-.5)*W()*.6,y:H()/2+(Math.random()-.5)*H()*.6,vx:0,vy:0,pinned:false};
  });
  const nodes=Object.values(nodeMap);
  const edges=deps.map(d=>({from:d.from_slug,to:d.to_slug,type:d.dependency_type||'references'}));
  const REPULSION=5000,SPRING=0.005,SPRING_LEN=200,DAMPING=0.85,CENTER=0.001,PAD=60;
  let dragging=null,hovered=null,offX=0,offY=0,dragMoved=false;
  function nodeRadius(){return 40}
  function tick(){
    nodes.forEach(a=>{if(a.pinned)return;
      nodes.forEach(b=>{if(a===b)return;let dx=a.x-b.x,dy=a.y-b.y;let d=Math.sqrt(dx*dx+dy*dy)||1;let f=REPULSION/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f});
      edges.forEach(e=>{let other=null;if(e.from===a.slug)other=nodeMap[e.to];else if(e.to===a.slug)other=nodeMap[e.from];else return;
        let dx=a.x-other.x,dy=a.y-other.y,d=Math.sqrt(dx*dx+dy*dy)||1;let f=SPRING*(d-SPRING_LEN);a.vx-=dx/d*f;a.vy-=dy/d*f});
      a.vx+=(W()/2-a.x)*CENTER;a.vy+=(H()/2-a.y)*CENTER;
      a.vx*=DAMPING;a.vy*=DAMPING;a.x+=a.vx;a.y+=a.vy;
      a.x=Math.max(PAD,Math.min(W()-PAD,a.x));a.y=Math.max(PAD,Math.min(H()-PAD,a.y))
    });
  }
  function drawArrow(x1,y1,x2,y2,color){
    const dx=x2-x1,dy=y2-y1,d=Math.sqrt(dx*dx+dy*dy)||1;
    const r=nodeRadius()+2;const ax=x1+dx/d*r,ay=y1+dy/d*r,bx=x2-dx/d*r,by=y2-dy/d*r;
    ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.globalAlpha=0.6;ctx.stroke();ctx.globalAlpha=1;
    const hl=8,ha=Math.atan2(by-ay,bx-ax);
    ctx.beginPath();ctx.moveTo(bx,by);ctx.lineTo(bx-hl*Math.cos(ha-.35),by-hl*Math.sin(ha-.35));ctx.lineTo(bx-hl*Math.cos(ha+.35),by-hl*Math.sin(ha+.35));ctx.closePath();ctx.fillStyle=color;ctx.globalAlpha=0.8;ctx.fill();ctx.globalAlpha=1;
  }
  function draw(){
    ctx.clearRect(0,0,W(),H());
    edges.forEach(e=>{const a=nodeMap[e.from],b=nodeMap[e.to];if(!a||!b)return;
      const isHL=hovered&&(e.from===hovered.slug||e.to===hovered.slug);
      if(!isHL)drawArrow(a.x,a.y,b.x,b.y,EDGE_COLORS[e.type]||'#818cf8')});
    edges.forEach(e=>{const a=nodeMap[e.from],b=nodeMap[e.to];if(!a||!b)return;
      const isHL=hovered&&(e.from===hovered.slug||e.to===hovered.slug);
      if(isHL){ctx.save();ctx.lineWidth=2.5;ctx.globalAlpha=1;drawArrow(a.x,a.y,b.x,b.y,EDGE_COLORS[e.type]||'#818cf8');ctx.restore()}});
    nodes.forEach(n=>{
      const r=nodeRadius();const isHov=hovered===n;const isDrag=dragging===n;
      const isConn=hovered&&hovered!==n&&edges.some(e=>(e.from===hovered.slug&&e.to===n.slug)||(e.to===hovered.slug&&e.from===n.slug));
      ctx.beginPath();ctx.arc(n.x,n.y,r,0,Math.PI*2);
      ctx.fillStyle=NODE_COLORS[n.status]||'#9496ad';ctx.globalAlpha=isHov||isDrag||isConn?1:hovered?0.4:0.85;ctx.fill();ctx.globalAlpha=1;
      const isLight=document.documentElement.getAttribute('data-theme')==='light';
      if(isHov||isDrag){ctx.strokeStyle=isLight?'#1d1d1f':'#fff';ctx.lineWidth=2.5;ctx.stroke()}
      else if(isConn){ctx.strokeStyle=isLight?'rgba(0,0,0,0.3)':'rgba(255,255,255,0.4)';ctx.lineWidth=1.5;ctx.stroke()}
      ctx.fillStyle='#fff';const fs=isHov?11:10;ctx.font=`${isHov?'600':'500'} ${fs}px Inter,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.globalAlpha=isHov||isDrag||isConn?1:hovered?0.4:1;
      wrapTextInCircle(ctx,n.title,n.x,n.y,r-6,fs);ctx.globalAlpha=1;
    });
  }
  function animate(){tick();draw();_graphAnim=requestAnimationFrame(animate)}
  animate();
  function getNode(mx,my){return nodes.find(n=>{const dx=mx-n.x,dy=my-n.y;return dx*dx+dy*dy<=nodeRadius()*nodeRadius()})}
  function getMousePos(e){const r=canvas.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
  canvas.addEventListener('mousedown',e=>{if(e.target===canvas&&!getNode(...Object.values(getMousePos(e))))closeGraphPopup();const{x,y}=getMousePos(e);const n=getNode(x,y);if(n){dragging=n;n.pinned=true;dragMoved=false;offX=x-n.x;offY=y-n.y;canvas.style.cursor='grabbing'}});
  canvas.addEventListener('mousemove',e=>{const{x,y}=getMousePos(e);if(dragging){const dx=x-offX-dragging.x,dy=y-offY-dragging.y;if(Math.abs(dx)>3||Math.abs(dy)>3)dragMoved=true;dragging.x=x-offX;dragging.y=y-offY}else{const n=getNode(x,y);hovered=n;canvas.style.cursor=n?'pointer':'default'}});
  canvas.addEventListener('mouseup',e=>{if(dragging){const wasClick=!dragMoved;const node=dragging;dragging.pinned=false;dragging=null;canvas.style.cursor='default';if(wasClick)showGraphPopup(node,e,wrap)}});
  canvas.addEventListener('mouseleave',()=>{if(dragging)dragging.pinned=false;dragging=null;hovered=null;canvas.style.cursor='default'});
  _graphObserver=new ResizeObserver(()=>{resize()});_graphObserver.observe(wrap);
}

function closeGraphPopup(){const p=document.querySelector('.graph-popup');if(p)p.remove()}
function showGraphPopup(node,e,wrap){
  closeGraphPopup();
  const sec=(projectData.sections||[]).find(s=>s.slug===node.slug);
  const summary=sec&&sec.summary?sec.summary:'No summary available';
  const status=sec?sec.status:'draft';
  const tags=sec&&sec.tags?sec.tags:[];
  const words=sec?sec.word_count:0;
  const type=sec?sec.section_type:'general';
  const sc=STATUS_COLORS[status]||'var(--draft)';
  const pop=document.createElement('div');
  pop.className='graph-popup';
  let tagsHtml=tags.length?'<div class="graph-popup-tags">'+tags.map(t=>`<span style="background:${tagColor(t)}">${t}</span>`).join('')+'</div>':'';
  pop.innerHTML=`<div class="graph-popup-header" onclick="closeGraphPopup();loadSection('${node.slug}')"><span class="status-dot" style="background:${sc}"></span><h4>${sec?sec.title:node.slug}</h4><span class="open-icon">Open →</span></div><div class="graph-popup-body">${summary}</div>${tagsHtml}<div class="graph-popup-meta"><span>${type}</span><span>${words} words</span><span>${status.replace('_',' ')}</span></div>`;
  const rect=wrap.getBoundingClientRect();
  let left=e.clientX-rect.left+12,top=e.clientY-rect.top-20;
  if(left+310>rect.width)left=left-324;
  if(top+250>rect.height)top=Math.max(10,rect.height-260);
  if(top<10)top=10;
  pop.style.left=left+'px';pop.style.top=top+'px';
  wrap.appendChild(pop);
}

async function loadSection(slug){
  clearGraph();
  activeSection=slug;
  renderSections();
  const res=await fetch(`/api/projects/${currentProject}/sections/${slug}`);
  const data=await res.json();
  const s=data.section;
  const sc=STATUS_COLORS[s.status]||'var(--draft)';
  let html=`<div class="section-title">${s.title}</div>
    <div class="meta-row">
      <span class="badge" style="background:${sc}">${s.status.replace('_',' ')}</span>
      <span>${s.section_type}</span>
      <span>${s.word_count} words</span>
      <span>Updated ${new Date(s.updated_at).toLocaleDateString()}</span>
      ${(s.tags||[]).map(t=>`<span class="tag-chip">${t}</span>`).join('')}
    </div>`;
  if(s.summary)html+=`<div class="summary-box">${s.summary}</div>`;
  html+=renderNotesBox(s.notes||'',s.slug);
  html+=`<div class="prose">${marked.parse(s.content||'')}</div>`;
  if(data.depends_on&&data.depends_on.length){
    html+=`<div class="deps-panel"><h3>Depends On</h3>`;
    html+=data.depends_on.map(d=>`<span class="dep-chip" onclick="loadSection('${d.slug}')">${d.title}<span class="dep-type">${d.dep_type}</span></span>`).join('');
    if(data.depends_on.length)html+=`<div style="margin-top:8px;font-size:12px;color:var(--text-muted)">Context summaries loaded with this section</div>`;
    html+=`</div>`;
  }
  if(data.depended_by&&data.depended_by.length){
    html+=`<div class="deps-panel" style="margin-top:12px"><h3>Depended By</h3>`;
    html+=data.depended_by.map(d=>`<span class="dep-chip" onclick="loadSection('${d.slug}')">${d.title}<span class="dep-type">${d.dep_type}</span></span>`).join('');
    html+=`</div>`;
  }
  if(data.revisions&&data.revisions.length){
    html+=`<div class="deps-panel" style="margin-top:12px"><h3>Revision History</h3>
      <table class="rev-table"><tr><th>#</th><th>Description</th><th>Date</th></tr>`;
    html+=data.revisions.map(r=>`<tr><td>${r.revision_number}</td><td>${r.change_description||'—'}</td><td>${new Date(r.created_at).toLocaleString()}</td></tr>`).join('');
    html+=`</table></div>`;
  }
  document.getElementById('mainContent').innerHTML=html;
  if(data.comments&&data.comments.length){
    applyCommentHighlights(data.comments);
    renderCommentsPanel(data.comments);
  }
}

function renderNotesBox(notes,slug){
  if(notes){
    return `<div class="notes-box" id="notesBox">
      <div class="label"><span>Notes</span><button class="notes-cancel" onclick="toggleNotesEdit(true)" style="font-size:11px;padding:2px 8px">Edit</button></div>
      <div id="notesDisplay">${marked.parse(notes)}</div>
      <div id="notesEdit" style="display:none">
        <textarea id="notesTextarea">${notes.replace(/</g,'&lt;')}</textarea>
        <div class="notes-actions">
          <button class="notes-save" onclick="saveNotes('${slug}')">Save</button>
          <button class="notes-cancel" onclick="toggleNotesEdit(false)">Cancel</button>
          <span class="notes-status" id="notesStatus">Saved</span>
        </div>
      </div>
    </div>`;
  }
  return `<button class="add-notes-btn" onclick="addNotesBox('${slug}')">+ Add Notes</button>
    <div class="notes-box" id="notesBox" style="display:none">
      <div class="label"><span>Notes</span></div>
      <textarea id="notesTextarea" placeholder="Add change requests, feedback, or requirements for Claude to implement..."></textarea>
      <div class="notes-actions">
        <button class="notes-save" onclick="saveNotes('${slug}')">Save</button>
        <button class="notes-cancel" onclick="document.getElementById('notesBox').style.display='none';document.querySelector('.add-notes-btn').style.display=''">Cancel</button>
        <span class="notes-status" id="notesStatus">Saved</span>
      </div>
    </div>`;
}
function addNotesBox(slug){document.querySelector('.add-notes-btn').style.display='none';document.getElementById('notesBox').style.display=''}
function toggleNotesEdit(show){document.getElementById('notesDisplay').style.display=show?'none':'';document.getElementById('notesEdit').style.display=show?'':'none'}
async function saveNotes(slug){
  const notes=document.getElementById('notesTextarea').value;
  const res=await fetch(`/api/projects/${currentProject}/sections/${slug}/notes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({notes})});
  if(res.ok){
    const st=document.getElementById('notesStatus');st.classList.add('show');setTimeout(()=>st.classList.remove('show'),2000);
    loadSection(slug);
  }
}

/* --- Inline comments --- */
let _commentSelection=null;
document.addEventListener('mouseup',function(e){
  if(e.target.closest('.comment-btn')||e.target.closest('.comment-popover'))return;
  document.querySelectorAll('.comment-btn').forEach(b=>b.remove());
  const sel=window.getSelection();
  if(!sel||sel.isCollapsed||!activeSection)return;
  const prose=document.querySelector('.prose');
  if(!prose||!prose.contains(sel.anchorNode))return;
  const text=sel.toString().trim();
  if(!text||text.length<3)return;
  const range=sel.getRangeAt(0);
  _commentSelection={text,range:range.cloneRange()};
  const rect=range.getBoundingClientRect();
  const mainEl=document.querySelector('.main');
  if(!mainEl)return;
  const btn=document.createElement('button');
  btn.className='comment-btn';
  btn.textContent='+ Comment';
  btn.style.position='fixed';
  btn.style.top=(rect.top-36)+'px';
  btn.style.left=rect.left+'px';
  btn.style.zIndex='1000';
  document.body.appendChild(btn);
  btn.addEventListener('click',function(ev){
    ev.preventDefault();ev.stopPropagation();
    showCommentInput(_commentSelection.text,_commentSelection.range);
  });
});
document.addEventListener('mousedown',function(e){
  if(e.target.closest('.comment-btn')||e.target.closest('.comment-popover'))return;
  document.querySelectorAll('.comment-btn').forEach(b=>b.remove());
  document.querySelectorAll('.comment-popover').forEach(p=>p.remove());
});

function getAnchorContext(range){
  const prose=document.querySelector('.prose');
  if(!prose)return{anchor_text:range.toString().trim(),anchor_prefix:'',anchor_suffix:''};
  const full=prose.textContent;
  const text=range.toString().trim();
  const walker=document.createTreeWalker(prose,NodeFilter.SHOW_TEXT);
  let offset=0,found=false;
  while(walker.nextNode()){
    if(walker.currentNode===range.startContainer){offset+=range.startOffset;found=true;break}
    offset+=walker.currentNode.textContent.length;
  }
  const prefix=found?full.substring(Math.max(0,offset-40),offset):'';
  const suffix=found?full.substring(offset+text.length,offset+text.length+40):'';
  return{anchor_text:text,anchor_prefix:prefix,anchor_suffix:suffix};
}

function showCommentInput(text,range){
  document.querySelectorAll('.comment-btn,.comment-popover').forEach(b=>b.remove());
  const anchor=getAnchorContext(range);
  const rect=range.getBoundingClientRect();
  const pop=document.createElement('div');
  pop.className='comment-popover';
  pop.style.top=(rect.bottom+8)+'px';
  pop.style.left=Math.min(rect.left,window.innerWidth-340)+'px';
  const short=text.length>80?text.substring(0,80)+'...':text;
  pop.innerHTML=`<div class="quoted">"${short.replace(/</g,'&lt;')}"</div>
    <textarea placeholder="Your comment..."></textarea>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="notes-save" onclick="submitComment(this)">Save</button>
      <button class="notes-cancel" onclick="this.closest('.comment-popover').remove()">Cancel</button>
    </div>`;
  pop.dataset.anchor=JSON.stringify(anchor);
  document.body.appendChild(pop);
  pop.querySelector('textarea').focus();
}

async function submitComment(btn){
  const pop=btn.closest('.comment-popover');
  const anchor=JSON.parse(pop.dataset.anchor);
  const body=pop.querySelector('textarea').value.trim();
  if(!body)return;
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments`,{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({...anchor,body})
  });
  pop.remove();
  window.getSelection().removeAllRanges();
  loadSection(activeSection);
}

function applyCommentHighlights(comments){
  const prose=document.querySelector('.prose');
  if(!prose)return;
  const open=comments.filter(c=>!c.resolved);
  open.forEach(c=>{
    highlightInDOM(prose,c.anchor_text,c.anchor_prefix,c.anchor_suffix,c.id);
  });
}

function highlightInDOM(root,text,prefix,suffix,cid){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let nodes=[],full='';
  while(walker.nextNode()){nodes.push({node:walker.currentNode,start:full.length});full+=walker.currentNode.textContent}
  let searchCtx=prefix+text+suffix;
  let idx=full.indexOf(searchCtx);
  let startIdx,endIdx;
  if(idx!==-1){startIdx=idx+prefix.length;endIdx=startIdx+text.length}
  else{idx=full.indexOf(text);if(idx===-1)return;startIdx=idx;endIdx=idx+text.length}
  // Find start and end text nodes
  let sn=null,so=0,en=null,eo=0;
  for(const n of nodes){
    const nEnd=n.start+n.node.textContent.length;
    if(!sn&&startIdx<nEnd){sn=n.node;so=startIdx-n.start}
    if(endIdx<=nEnd){en=n.node;eo=endIdx-n.start;break}
  }
  if(!sn||!en)return;
  try{
    const range=document.createRange();
    range.setStart(sn,so);
    range.setEnd(en,eo);
    const mark=document.createElement('mark');
    mark.className='comment-hl';
    mark.dataset.commentId=cid;
    mark.onclick=function(){scrollToComment(cid)};
    range.surroundContents(mark);
  }catch(e){/* cross-element selection — skip highlight, comment still in panel */}
}

function scrollToComment(cid){
  const card=document.querySelector(`.comment-card[data-id="${cid}"]`);
  if(card){card.scrollIntoView({behavior:'smooth',block:'center'});card.style.background='var(--secondary)';setTimeout(()=>card.style.background='',1500)}
}

async function resolveComment(cid){
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}/resolve`,{method:'POST'});
  loadSection(activeSection);
}
async function deleteComment(cid){
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}`,{method:'DELETE'});
  loadSection(activeSection);
}

function renderCommentsPanel(comments){
  if(!comments.length)return;
  const wrap=document.querySelector('.content-wrap');
  const open=comments.filter(c=>!c.resolved);
  const resolved=comments.filter(c=>c.resolved);
  let html=`<div class="comments-panel"><div class="comments-panel-header"><h3>Comments (${open.length} open${resolved.length?', '+resolved.length+' resolved':''})</h3></div>`;
  comments.forEach(c=>{
    const short=c.anchor_text.length>60?c.anchor_text.substring(0,60)+'...':c.anchor_text;
    html+=`<div class="comment-card ${c.resolved?'resolved-card':''}" data-id="${c.id}">
      <div class="anchor">on "<em>${short.replace(/</g,'&lt;')}</em>" · ${new Date(c.created_at).toLocaleString()}</div>
      <div class="body">${marked.parse(c.body)}</div>`;
    // Render replies
    if(c.replies&&c.replies.length){
      c.replies.forEach(r=>{
        html+=`<div class="reply-card">
          <div class="reply-author ${r.author}">${r.author} · ${new Date(r.created_at).toLocaleString()}</div>
          <div>${marked.parse(r.body)}</div>
        </div>`;
      });
    }
    html+=`<div class="actions">
        <button onclick="resolveComment('${c.id}')">${c.resolved?'Reopen':'Resolve'}</button>
        <button onclick="editComment('${c.id}')">Edit</button>
        <button onclick="showReplyForm('${c.id}')">Reply</button>
        <button class="del-btn" onclick="deleteComment('${c.id}')">Delete</button>
      </div>
      <div class="reply-form" id="reply-form-${c.id}" style="display:none">
        <textarea placeholder="Write a reply..."></textarea>
        <button onclick="submitReply('${c.id}',this)">Send</button>
      </div>
    </div>`;
  });
  html+='</div>';
  wrap.insertAdjacentHTML('beforeend',html);
}

function showReplyForm(cid){
  const f=document.getElementById('reply-form-'+cid);
  f.style.display=f.style.display==='none'?'flex':'none';
  if(f.style.display==='flex')f.querySelector('textarea').focus();
}

async function submitReply(cid,btn){
  const form=btn.closest('.reply-form');
  const body=form.querySelector('textarea').value.trim();
  if(!body)return;
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}/replies`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({body})
  });
  loadSection(activeSection);
}

function editComment(cid){
  const card=document.querySelector(`.comment-card[data-id="${cid}"]`);
  if(!card)return;
  const bodyEl=card.querySelector('.body');
  const actionsEl=card.querySelector('.actions');
  const raw=bodyEl.textContent.trim();
  bodyEl.innerHTML=`<textarea class="edit-comment-ta" style="width:100%;min-height:60px;background:var(--secondary);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-family:'Inter',sans-serif;font-size:13px;line-height:1.6;resize:vertical">${raw.replace(/</g,'&lt;')}</textarea>`;
  actionsEl.innerHTML=`<button onclick="saveComment('${cid}',this)">Save</button><button onclick="loadSection(activeSection)">Cancel</button>`;
  bodyEl.querySelector('textarea').focus();
}
async function saveComment(cid,btn){
  const card=btn.closest('.comment-card');
  const body=card.querySelector('.edit-comment-ta').value.trim();
  if(!body)return;
  await fetch(`/api/projects/${currentProject}/sections/${activeSection}/comments/${cid}`,{
    method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({body})
  });
  loadSection(activeSection);
}

/* --- Global comments tab --- */
let _globalComments=[],_commentFilter='all';
async function loadGlobalComments(){
  const res=await fetch(`/api/projects/${currentProject}/comments`);
  _globalComments=await res.json();
  renderGlobalCommentFilters();
  renderGlobalComments();
}
function renderGlobalCommentFilters(){
  const total=_globalComments.length;
  const openCount=_globalComments.filter(c=>!c.resolved).length;
  const resolvedCount=total-openCount;
  const f=document.getElementById('commentFilters');
  f.innerHTML=[
    {key:'all',label:`All (${total})`},{key:'open',label:`Open (${openCount})`},{key:'resolved',label:`Resolved (${resolvedCount})`}
  ].map(c=>`<span class="chip ${_commentFilter===c.key?'active':''}" onclick="setCommentFilter('${c.key}')">${c.label}</span>`).join('');
}
function setCommentFilter(f){_commentFilter=f;renderGlobalCommentFilters();renderGlobalComments()}
function renderGlobalComments(){
  let list=_globalComments;
  if(_commentFilter==='open')list=list.filter(c=>!c.resolved);
  else if(_commentFilter==='resolved')list=list.filter(c=>c.resolved);
  const el=document.getElementById('globalCommentsList');
  if(!list.length){el.innerHTML='<div class="empty" style="padding:40px">No comments</div>';return}
  el.innerHTML=list.map(c=>{
    const short=c.anchor_text.length>50?c.anchor_text.substring(0,50)+'...':c.anchor_text;
    const time=new Date(c.created_at).toLocaleString();
    const status=c.resolved?'<span style="color:var(--approved)">Resolved ✓</span>':'<span style="color:var(--text-sec)">Open</span>';
    return `<div class="section-item ${c.resolved?'':'active'}" style="${c.resolved?'opacity:0.55':''};border-left:3px solid ${c.resolved?'var(--approved)':'var(--accent)'}" onclick="goToComment('${c.section_slug}','${c.id}')">
      <div class="title" style="font-size:12px;font-weight:600;color:var(--accent)">${c.section_title||c.section_slug}</div>
      <div style="font-size:12px;font-style:italic;color:var(--text);margin:2px 0">"${short.replace(/</g,'&lt;')}"</div>
      <div style="font-size:12px;color:var(--text-sec);margin:2px 0">${c.body.length>80?c.body.substring(0,80).replace(/</g,'&lt;')+'...':c.body.replace(/</g,'&lt;')}</div>
      <div class="meta-line">${time} · ${status}</div>
    </div>`;
  }).join('');
}
function goToComment(sectionSlug,commentId){
  switchTab('sections');
  loadSection(sectionSlug).then(()=>{
    setTimeout(()=>{
      const hl=document.querySelector(`.comment-hl[data-comment-id="${commentId}"]`);
      if(hl){hl.scrollIntoView({behavior:'smooth',block:'center'});hl.classList.add('active');setTimeout(()=>hl.classList.remove('active'),2000)}
      scrollToComment(commentId);
    },200);
  });
}

async function loadFullPRD(){
  activeSection=null;
  renderSections();
  const res=await fetch(`/api/projects/${currentProject}/export`);
  const md=await res.text();
  document.getElementById('mainContent').innerHTML=`<div class="section-title">Full PRD</div><div class="prose">${marked.parse(md)}</div>`;
}

function switchTab(tab){
  document.querySelectorAll('.nav-icon[data-tab]').forEach(n=>n.classList.toggle('active',n.dataset.tab===tab));
  document.querySelectorAll('.tab-content').forEach(tc=>tc.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  if(document.body.classList.contains('collapsed'))document.body.classList.remove('collapsed');
  if(tab==='comments')loadGlobalComments();
  if(tab==='settings')loadSettings();
  if(tab==='deps'){activeSection=null;renderSections();showMainGraph()}
  else{clearGraph()}
}

function toggleSidebar(){
  document.body.classList.toggle('collapsed');
  const btn=document.getElementById('collapseBtn');
  const collapsed=document.body.classList.contains('collapsed');
  btn.innerHTML=collapsed
    ?'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>'
    :'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>';
}

async function loadSettings(){
  if(!currentProject)return;
  const res=await fetch(`/api/projects/${currentProject}/settings`);
  const data=await res.json();
  document.getElementById('settingClaudeReplies').checked=data.claude_comment_replies!==false;
}

async function saveSetting(key,value){
  if(!currentProject)return;
  await fetch(`/api/projects/${currentProject}/settings`,{
    method:'PUT',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({[key]:value})
  });
}

init();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/projects")
async def list_projects():
    rows = await pool.fetch("""
        SELECT p.slug, p.name, p.description, p.version,
               COUNT(s.id) AS section_count,
               COALESCE(SUM(s.word_count), 0) AS total_words
        FROM projects p
        LEFT JOIN sections s ON s.project_id = p.id
        GROUP BY p.id ORDER BY p.created_at
    """)
    return [row_dict(r) for r in rows]


@app.get("/api/projects/{slug}")
async def get_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sections = await pool.fetch("""
        SELECT slug, title, section_type, sort_order, status, summary, tags,
               word_count, parent_slug, revision_count, updated_at
        FROM section_tree WHERE project_id = $1 ORDER BY sort_order
    """, proj["id"])

    deps = await pool.fetch("""
        SELECT s1.slug AS from_slug, s1.title AS from_title,
               s2.slug AS to_slug, s2.title AS to_title,
               d.dependency_type
        FROM section_dependencies d
        JOIN sections s1 ON s1.id = d.section_id
        JOIN sections s2 ON s2.id = d.depends_on_id
        WHERE d.project_id = $1
    """, proj["id"])

    changelog = await pool.fetch("""
        SELECT section_slug, section_title, revision_number,
               change_description, created_at
        FROM project_changelog WHERE project_slug = $1
        ORDER BY created_at DESC LIMIT 20
    """, slug)

    status_counts = {}
    total_words = 0
    for s in sections:
        st = s["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        total_words += s["word_count"]

    return {
        "project": {"slug": proj["slug"], "name": proj["name"], "description": proj["description"],
                     "version": proj["version"], "created_at": dt(proj["created_at"])},
        "stats": {"sections": len(sections), "words": total_words, "by_status": status_counts},
        "sections": [row_dict(r) for r in sections],
        "dependencies": [row_dict(r) for r in deps],
        "changelog": [row_dict(r) for r in changelog],
    }


@app.get("/api/projects/{slug}/sections/{section}")
async def get_section(slug: str, section: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sec = await pool.fetchrow("""
        SELECT s.slug, s.title, s.content, s.summary, s.status, s.section_type,
               s.tags, s.notes, s.word_count, s.updated_at
        FROM sections s WHERE s.project_id = $1 AND s.slug = $2
    """, proj["id"], section)
    if not sec:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)

    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )

    depends_on = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.depends_on_id
        WHERE d.section_id = $1
    """, sec_id)

    depended_by = await pool.fetch("""
        SELECT s.slug, s.title, s.summary, s.status,
               d.dependency_type AS dep_type, d.description AS dep_reason
        FROM section_dependencies d
        JOIN sections s ON s.id = d.section_id
        WHERE d.depends_on_id = $1
    """, sec_id)

    revisions = await pool.fetch("""
        SELECT revision_number, change_description, created_at
        FROM section_revisions WHERE section_id = $1
        ORDER BY revision_number DESC
    """, sec_id)

    comments = await pool.fetch("""
        SELECT id, anchor_text, anchor_prefix, anchor_suffix, body, resolved, created_at
        FROM section_comments WHERE section_id = $1
        ORDER BY created_at
    """, sec_id)

    # Batch-fetch replies
    comment_ids = [c["id"] for c in comments]
    replies = await pool.fetch(
        "SELECT id, comment_id, author, body, created_at "
        "FROM comment_replies WHERE comment_id = ANY($1) ORDER BY created_at",
        comment_ids,
    ) if comment_ids else []

    replies_by_comment = {}
    for r in replies:
        cid = str(r["comment_id"])
        replies_by_comment.setdefault(cid, []).append(row_dict(r))

    comment_dicts = []
    for c in comments:
        cd = row_dict(c)
        cd["replies"] = replies_by_comment.get(str(c["id"]), [])
        comment_dicts.append(cd)

    return {
        "section": row_dict(sec),
        "depends_on": [row_dict(r) for r in depends_on],
        "depended_by": [row_dict(r) for r in depended_by],
        "revisions": [row_dict(r) for r in revisions],
        "comments": comment_dicts,
    }


@app.post("/api/projects/{slug}/sections/{section}/notes")
async def update_notes(slug: str, section: str, request: Request):
    body = await request.json()
    notes = body.get("notes", "")
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    result = await pool.execute(
        "UPDATE sections SET notes = $1 WHERE project_id = $2 AND slug = $3",
        notes, proj["id"], section,
    )
    if result.split()[-1] == "0":
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    return {"ok": True, "notes": notes}


@app.post("/api/projects/{slug}/sections/{section}/comments")
async def create_comment(slug: str, section: str, request: Request):
    body = await request.json()
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    sec_id = await pool.fetchval(
        "SELECT id FROM sections WHERE project_id = $1 AND slug = $2", proj["id"], section
    )
    if not sec_id:
        return JSONResponse({"error": f"section '{section}' not found"}, 404)
    row = await pool.fetchrow("""
        INSERT INTO section_comments (section_id, anchor_text, anchor_prefix, anchor_suffix, body)
        VALUES ($1, $2, $3, $4, $5) RETURNING *
    """, sec_id, body["anchor_text"], body.get("anchor_prefix", ""),
        body.get("anchor_suffix", ""), body["body"])
    return row_dict(row)


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/resolve")
async def resolve_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id, c.resolved FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("UPDATE section_comments SET resolved = $1 WHERE id = $2", not row["resolved"], row["id"])
    return {"ok": True, "resolved": not row["resolved"]}


@app.patch("/api/projects/{slug}/sections/{section}/comments/{comment_id}")
async def update_comment(slug: str, section: str, comment_id: str, request: Request):
    body = await request.json()
    new_body = body.get("body", "").strip()
    if not new_body:
        return JSONResponse({"error": "body required"}, 400)
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("UPDATE section_comments SET body = $1 WHERE id = $2", new_body, row["id"])
    return {"ok": True}


@app.delete("/api/projects/{slug}/sections/{section}/comments/{comment_id}")
async def delete_comment(slug: str, section: str, comment_id: str):
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    await pool.execute("DELETE FROM section_comments WHERE id = $1", row["id"])
    return {"ok": True}


@app.post("/api/projects/{slug}/sections/{section}/comments/{comment_id}/replies")
async def add_comment_reply(slug: str, section: str, comment_id: str, request: Request):
    body = await request.json()
    reply_body = body.get("body", "").strip()
    if not reply_body:
        return JSONResponse({"error": "body required"}, 400)
    cid = _uuid.UUID(comment_id)
    row = await pool.fetchrow("""
        SELECT c.id FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        JOIN projects p ON p.id = s.project_id
        WHERE c.id = $1 AND p.slug = $2 AND s.slug = $3
    """, cid, slug, section)
    if not row:
        return JSONResponse({"error": "comment not found"}, 404)
    reply = await pool.fetchrow(
        "INSERT INTO comment_replies (comment_id, author, body) VALUES ($1, 'user', $2) RETURNING *",
        row["id"], reply_body,
    )
    return row_dict(reply)


@app.get("/api/projects/{slug}/settings")
async def get_settings(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    if row:
        import json as _json2
        raw = row["settings"]
        db_settings = _json2.loads(raw) if isinstance(raw, str) else dict(raw)
    else:
        db_settings = {}
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.put("/api/projects/{slug}/settings")
async def update_settings(slug: str, request: Request):
    body = await request.json()
    clean, errors = validate_settings(body)
    if errors:
        return JSONResponse({"error": f"invalid settings: {'; '.join(errors)}"}, 400)
    if not clean:
        return JSONResponse({"error": "no valid settings provided"}, 400)
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    import json as _json
    await pool.execute("""
        INSERT INTO project_settings (project_id, settings)
        VALUES ($1, $2::jsonb)
        ON CONFLICT (project_id)
        DO UPDATE SET settings = project_settings.settings || $2::jsonb
    """, proj["id"], _json.dumps(clean))
    row = await pool.fetchrow(
        "SELECT settings FROM project_settings WHERE project_id = $1", proj["id"]
    )
    raw = row["settings"]
    db_settings = _json.loads(raw) if isinstance(raw, str) else dict(raw)
    merged = {**DEFAULT_PROJECT_SETTINGS, **db_settings}
    return merged


@app.get("/api/projects/{slug}/comments")
async def list_project_comments(slug: str):
    proj = await pool.fetchrow("SELECT id FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)
    rows = await pool.fetch("""
        SELECT c.id, c.anchor_text, c.anchor_prefix, c.anchor_suffix,
               c.body, c.resolved, c.created_at, c.updated_at,
               s.slug AS section_slug, s.title AS section_title,
               COALESCE(rc.cnt, 0) AS reply_count
        FROM section_comments c
        JOIN sections s ON s.id = c.section_id
        LEFT JOIN (SELECT comment_id, COUNT(*) AS cnt FROM comment_replies GROUP BY comment_id) rc
            ON rc.comment_id = c.id
        WHERE s.project_id = $1
        ORDER BY c.created_at DESC
    """, proj["id"])
    return [row_dict(r) for r in rows]


@app.get("/api/projects/{slug}/export")
async def export_project(slug: str):
    proj = await pool.fetchrow("SELECT * FROM projects WHERE slug = $1", slug)
    if not proj:
        return JSONResponse({"error": f"project '{slug}' not found"}, 404)

    sections = await pool.fetch("""
        SELECT title, section_type, status, content
        FROM sections WHERE project_id = $1 ORDER BY sort_order
    """, proj["id"])

    lines = [f"# {proj['name']}\n"]
    for s in sections:
        lines.append(f"## {s['title']}")
        lines.append(f"*{s['section_type']} | {s['status']}*\n")
        lines.append(s["content"])
        lines.append("\n---\n")

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/health")
async def health():
    try:
        await pool.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse({"status": "error", "db": "error"}, 503)
