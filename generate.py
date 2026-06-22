#!/usr/bin/env python3
"""
Génère build/index.html depuis le vault Obsidian.
Usage: python generate.py
"""
import os, re, json
from pathlib import Path
from datetime import date

VAULT = Path("/home/raphael/Documents/Nō.te")
BUILD = Path(__file__).parent / "build"

# ── parsing ────────────────────────────────────────────────────────────────

def parse_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---\n?(.*)', text, re.DOTALL)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2).strip()
    fm = {}
    for line in fm_text.splitlines():
        kv = re.match(r'^(\w+):\s*(.+)', line)
        if kv:
            k, v = kv.group(1), kv.group(2).strip().strip('"\'')
            if v.lower() not in ('none', ''):
                fm[k] = v
    # tags: [a, b, c]
    tags_m = re.search(r'^tags:\s*\[([^\]]+)\]', fm_text, re.MULTILINE)
    if tags_m:
        fm['tags'] = [t.strip().strip('"\'') for t in tags_m.group(1).split(',')]
    else:
        block = re.search(r'^tags:\n((?:[ \t]+-[ \t]+.+\n?)+)', fm_text, re.MULTILINE)
        if block:
            fm['tags'] = re.findall(r'-\s+(.+)', block.group(1))
    return fm, body

def clean_wikilinks(text):
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    return text

def get_cats(tags):
    cats = set()
    for t in tags:
        parts = t.split('/')
        if parts[0] == 'recette' and len(parts) > 1:
            cats.add(parts[1])
        elif parts[0] not in ('recette',):
            cats.add(parts[0])
    return sorted(cats)

# ── collect ─────────────────────────────────────────────────────────────────

recipes = []
for root, dirs, files in os.walk(VAULT):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in files:
        if not fname.endswith('.md'):
            continue
        path = Path(root) / fname
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            continue
        fm, body = parse_frontmatter(text)
        if fm.get('type') != 'recette':
            continue
        tags = fm.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        recipes.append({
            'id':     re.sub(r'[^\w-]', '-', fname.replace('.md', '')),
            'title':  fname.replace('.md', ''),
            'tags':   [t for t in tags if t != 'recette'],
            'cats':   get_cats(tags),
            'origine': fm.get('origine', ''),
            'body':   clean_wikilinks(body),
        })

recipes.sort(key=lambda r: r['title'].lower())

cat_counts = {}
for r in recipes:
    for c in r['cats']:
        cat_counts[c] = cat_counts.get(c, 0) + 1
cats_sorted = sorted(cat_counts.items(), key=lambda x: -x[1])

origines = sorted({r['origine'] for r in recipes if r['origine']})
print(f"  {len(recipes)} recettes | {len(cat_counts)} catégories | {len(origines)} origines")

# ── meta ─────────────────────────────────────────────────────────────────────

CAT_COLORS = {
    'fermentation': '#16a34a',
    'dessert':      '#db2777',
    'sauce':        '#dc2626',
    'koyo':         '#4f46e5',
    'plat':         '#2563eb',
    'condiment':    '#d97706',
    'boisson':      '#0891b2',
    'vegan':        '#65a30d',
    'tapas':        '#9333ea',
    'bizarre':      '#7c3aed',
    'sousvide':     '#0369a1',
    'amino':        '#047857',
}
CAT_LABELS = {
    'fermentation': 'Fermentation',
    'dessert':      'Desserts',
    'sauce':        'Sauces',
    'koyo':         'Koyo',
    'plat':         'Plats',
    'condiment':    'Condiments',
    'boisson':      'Boissons',
    'vegan':        'Végétal',
    'tapas':        'Tapas',
    'bizarre':      'Bizarre',
    'sousvide':     'Sous-vide',
    'amino':        'Amino / Garum',
}

categories = [
    {
        'id':    c,
        'label': CAT_LABELS.get(c, c.capitalize()),
        'count': n,
        'color': CAT_COLORS.get(c, '#6b7280'),
    }
    for c, n in cats_sorted
]

# ── HTML template ─────────────────────────────────────────────────────────────
# Uses __PLACEHOLDER__ sentinels to avoid conflicts with CSS/JS braces.

TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Recettes — Atelier Bizarre</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:       #F8F5F0;
      --card-bg:  #FFFFFF;
      --sidebar:  #18181B;
      --side-t:   #E4E4E7;
      --accent:   #C2410C;
      --border:   #E7E3DA;
      --text:     #1C1917;
      --muted:    #78716C;
      --radius:   8px;
      --sidebar-w: 210px;
      --header-h:  56px;
    }

    html, body { height: 100%; font-family: 'DM Sans', system-ui, sans-serif;
      background: var(--bg); color: var(--text); font-size: 15px; line-height: 1.5; }

    /* ── Header ── */
    header {
      position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
      display: flex; align-items: center; gap: 16px; padding: 0 24px;
      background: var(--sidebar); z-index: 200; border-bottom: 1px solid #27272A;
    }
    .site-title {
      font-family: 'DM Serif Display', Georgia, serif; font-size: 18px;
      color: #E4E4E7; letter-spacing: 0.02em; white-space: nowrap;
    }
    .site-title em { color: var(--accent); font-style: italic; }
    .search-wrap { flex: 1; max-width: 420px; margin-left: auto; }
    #search {
      width: 100%; padding: 7px 14px; border-radius: 6px;
      border: 1px solid #3F3F46; background: #27272A; color: #E4E4E7;
      font-size: 14px; font-family: inherit; outline: none; transition: border-color .15s;
    }
    #search::placeholder { color: #71717A; }
    #search:focus { border-color: var(--accent); }

    /* ── Layout ── */
    .layout {
      display: flex; padding-top: var(--header-h); height: 100vh;
    }

    /* ── Sidebar ── */
    aside {
      position: fixed; top: var(--header-h); bottom: 0; left: 0;
      width: var(--sidebar-w); background: var(--sidebar);
      overflow-y: auto; padding: 20px 0; z-index: 100;
    }
    .side-section { margin-bottom: 8px; }
    .side-label {
      font-size: 10px; font-weight: 500; letter-spacing: .12em;
      text-transform: uppercase; color: #52525B; padding: 0 16px 8px;
    }
    .cat-btn {
      display: flex; align-items: center; gap: 8px;
      width: 100%; padding: 7px 16px; background: transparent; border: none;
      color: #A1A1AA; font-family: inherit; font-size: 14px;
      cursor: pointer; text-align: left;
      transition: color .15s, background .15s;
      border-left: 2px solid transparent;
    }
    .cat-btn:hover { color: #E4E4E7; background: #27272A; }
    .cat-btn.active { color: #fff; background: #27272A; border-left-color: var(--accent); }
    .cat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .cat-count { margin-left: auto; font-size: 12px; color: #52525B; }
    .cat-btn.active .cat-count { color: #71717A; }

    /* ── Grid area ── */
    .grid-area {
      margin-left: var(--sidebar-w); flex: 1;
      overflow-y: auto; padding: 28px 28px 60px; position: relative;
    }
    .grid-meta { font-size: 13px; color: var(--muted); margin-bottom: 18px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 16px;
    }

    /* ── Cards ── */
    .card {
      background: var(--card-bg); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 18px 20px;
      cursor: pointer; transition: box-shadow .15s, transform .1s;
    }
    .card:hover { box-shadow: 0 4px 20px rgba(0,0,0,.08); transform: translateY(-2px); }
    .card-title {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 16px; line-height: 1.3; margin-bottom: 10px; color: var(--text);
    }
    .card-origine { font-size: 12px; color: var(--muted); margin-bottom: 10px; }
    .tags { display: flex; flex-wrap: wrap; gap: 5px; }
    .tag {
      font-size: 11px; font-weight: 500; padding: 2px 8px;
      border-radius: 999px; color: #fff; letter-spacing: .02em;
    }

    /* ── Detail panel ── */
    #detail {
      position: fixed;
      top: var(--header-h); left: var(--sidebar-w); right: 0; bottom: 0;
      background: var(--bg); overflow-y: auto;
      transform: translateX(100%);
      transition: transform .25s cubic-bezier(.4,0,.2,1);
      z-index: 150;
    }
    #detail.open { transform: none; }
    .detail-inner { max-width: 720px; margin: 0 auto; padding: 36px 40px 80px; }
    .detail-back {
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 13px; color: var(--muted); cursor: pointer;
      border: none; background: none; font-family: inherit;
      padding: 0 0 28px; transition: color .15s;
    }
    .detail-back:hover { color: var(--text); }
    .detail-title {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 30px; line-height: 1.2; margin-bottom: 10px;
    }
    .detail-origine { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
    .detail-tags {
      display: flex; flex-wrap: wrap; gap: 6px;
      margin-bottom: 32px; padding-bottom: 32px; border-bottom: 1px solid var(--border);
    }
    /* Rendered markdown */
    .body h1, .body h2, .body h3, .body h4 {
      font-family: 'DM Serif Display', Georgia, serif;
      margin: 1.4em 0 .5em; color: var(--text);
    }
    .body h2 { font-size: 20px; }
    .body h3 { font-size: 17px; }
    .body p  { margin-bottom: .75em; }
    .body ul, .body ol { padding-left: 1.4em; margin-bottom: .75em; }
    .body li { margin-bottom: .25em; }
    .body li ul, .body li ol { margin-top: .2em; margin-bottom: 0; }
    .body strong { font-weight: 500; }
    .body em { font-style: italic; color: var(--muted); }
    .body hr { border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }
    .body blockquote {
      border-left: 3px solid var(--border); padding-left: 16px;
      color: var(--muted); margin: 1em 0;
    }
    .body a { color: var(--accent); text-decoration: none; }
    .body a:hover { text-decoration: underline; }
    .body table { border-collapse: collapse; width: 100%; margin-bottom: .75em; }
    .body th, .body td { border: 1px solid var(--border); padding: 6px 10px; }
    .body th { background: #F0EDE6; font-weight: 500; }

    /* ── Empty ── */
    .empty {
      grid-column: 1 / -1; text-align: center;
      padding: 80px 20px; color: var(--muted);
    }
    .empty-title {
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 20px; color: var(--text); margin: 12px 0 6px;
    }

    /* ── Mobile ── */
    @media (max-width: 680px) {
      :root { --sidebar-w: 0px; }
      aside { display: none; }
      .cat-pills { display: flex; gap: 8px; overflow-x: auto; padding: 12px 20px; }
      .grid-area { padding: 16px; }
      .grid { grid-template-columns: 1fr 1fr; gap: 12px; }
      .detail-inner { padding: 24px 20px 60px; }
      #detail { left: 0; }
    }
  </style>
</head>
<body>

<header>
  <div class="site-title">Recettes <em>Bizarre</em></div>
  <div class="search-wrap">
    <input id="search" type="search" placeholder="Recette, ingrédient…" autocomplete="off">
  </div>
</header>

<div class="layout">
  <aside id="sidebar"></aside>
  <div class="grid-area">
    <div class="grid-meta" id="meta"></div>
    <div class="grid" id="grid"></div>
  </div>
</div>

<div id="detail"></div>

<script>
const RECIPES    = __RECIPES_JSON__;
const CATEGORIES = __CATS_JSON__;
const CAT_COLORS = __COLORS_JSON__;

let state = { cat: null, query: '', recipe: null };

const $sidebar = document.getElementById('sidebar');
const $grid    = document.getElementById('grid');
const $meta    = document.getElementById('meta');
const $detail  = document.getElementById('detail');
const $search  = document.getElementById('search');

// ── Sidebar ────────────────────────────────────────────────────────────────

function buildSidebar() {
  let h = '<div class="side-section"><div class="side-label">Catégories</div>';
  const allActive = state.cat === null ? 'active' : '';
  h += `<button class="cat-btn ${allActive}" data-cat="">
    <span class="cat-dot" style="background:#52525B"></span>
    Toutes <span class="cat-count">${RECIPES.length}</span>
  </button>`;
  for (const c of CATEGORIES) {
    const active = state.cat === c.id ? 'active' : '';
    h += `<button class="cat-btn ${active}" data-cat="${c.id}">
      <span class="cat-dot" style="background:${c.color}"></span>
      ${c.label} <span class="cat-count">${c.count}</span>
    </button>`;
  }
  h += '</div>';
  $sidebar.innerHTML = h;
  $sidebar.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.cat    = btn.dataset.cat || null;
      state.recipe = null;
      render();
    });
  });
}

// ── Filter ─────────────────────────────────────────────────────────────────

function filtered() {
  let r = RECIPES;
  if (state.cat)   r = r.filter(x => x.cats.includes(state.cat));
  if (state.query) {
    const q = state.query.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    r = r.filter(x => {
      const t = (x.title + ' ' + x.body).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
      return t.includes(q);
    });
  }
  return r;
}

// ── Tag chip ───────────────────────────────────────────────────────────────

function chip(cat) {
  const color = CAT_COLORS[cat] || '#6b7280';
  const meta  = CATEGORIES.find(c => c.id === cat);
  const label = meta ? meta.label : cat;
  return `<span class="tag" style="background:${color}">${label}</span>`;
}

// ── Grid ───────────────────────────────────────────────────────────────────

function renderGrid() {
  const list = filtered();
  $meta.textContent = `${list.length} recette${list.length !== 1 ? 's' : ''}`;

  if (!list.length) {
    $grid.innerHTML = `<div class="empty">
      <div style="font-size:40px">🍽</div>
      <div class="empty-title">Aucune recette trouvée</div>
      <div>Essayez d'autres mots ou d'autres filtres.</div>
    </div>`;
    return;
  }

  $grid.innerHTML = list.map(r => {
    const origine = r.origine ? `<div class="card-origine">${r.origine}</div>` : '';
    const tags    = r.cats.map(chip).join('');
    return `<div class="card" data-id="${r.id}">
      <div class="card-title">${r.title}</div>
      ${origine}
      <div class="tags">${tags}</div>
    </div>`;
  }).join('');

  $grid.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => {
      const r = RECIPES.find(x => x.id === card.dataset.id);
      if (r) openDetail(r);
    });
  });
}

// ── Detail ─────────────────────────────────────────────────────────────────

function openDetail(r) {
  state.recipe = r;
  const origine = r.origine ? `<div class="detail-origine">${r.origine}</div>` : '';
  const tags    = r.cats.map(chip).join('');
  const body    = marked.parse(r.body || '_Aucun contenu._');
  $detail.innerHTML = `<div class="detail-inner">
    <button class="detail-back" id="back">← Retour</button>
    <h1 class="detail-title">${r.title}</h1>
    ${origine}
    <div class="detail-tags">${tags}</div>
    <div class="body">${body}</div>
  </div>`;
  $detail.classList.add('open');
  $detail.scrollTop = 0;
  document.getElementById('back').addEventListener('click', closeDetail);
}

function closeDetail() {
  state.recipe = null;
  $detail.classList.remove('open');
}

// ── Render ─────────────────────────────────────────────────────────────────

function render() {
  buildSidebar();
  renderGrid();
}

// ── Events ─────────────────────────────────────────────────────────────────

$search.addEventListener('input', () => {
  state.query  = $search.value.trim();
  state.recipe = null;
  closeDetail();
  render();
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
});

// ── Init ───────────────────────────────────────────────────────────────────
render();
</script>
</body>
</html>
"""

html = (TEMPLATE
    .replace('__RECIPES_JSON__', json.dumps(recipes, ensure_ascii=False))
    .replace('__CATS_JSON__',    json.dumps(categories, ensure_ascii=False))
    .replace('__COLORS_JSON__',  json.dumps(CAT_COLORS, ensure_ascii=False))
)

BUILD.mkdir(exist_ok=True)
(BUILD / "index.html").write_text(html, encoding='utf-8')
size_kb = len(html.encode()) // 1024
print(f"  → build/index.html ({size_kb} KB) — généré le {date.today()}")
