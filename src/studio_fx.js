/* =====================================================================
   studio_fx.js - GetLayers Interactive Motion & Cursor Engine
   Injected into Streamlit parent window via components.html().
   Handles:
   1. Interactive Spring Cursor (Dot + Trailing Ring + Morph + Click Shockwave)
   2. Magnetic Button Pull (Subtle translation towards pointer)
   3. Interactive 2D Neural Constellation in the Hero Banner
   4. Command Palette (Ctrl+K / Cmd+K with fuzzy search & React Aria tab switching)
   5. Dynamic Tab Accent Colors & Scroll Progress Bar
   6. Automatic Caret Removal from Selectbox Inputs
   7. Memory Leak Prevention & Idempotency
   ===================================================================== */
(function () {
  try {
    var host = window.parent, doc = host.document, root = doc.documentElement;
    var VER = 'fx-v5';
    if (host.__studioFx && host.__studioFx.ver === VER) return;
    if (host.__studioFx && typeof host.__studioFx.destroy === 'function') host.__studioFx.destroy();

    var cleanups = [], nodes = [];
    function on(t, ev, fn, opt) { 
      t.addEventListener(ev, fn, opt); 
      cleanups.push(function () { t.removeEventListener(ev, fn, opt); }); 
    }
    function mk(tag, cls, parent) { 
      var n = doc.createElement(tag); 
      n.className = cls; 
      (parent || doc.body).appendChild(n); 
      nodes.push(n); 
      return n; 
    }
    function $(s, r) { return (r || doc).querySelector(s); }
    function $$(s, r) { return Array.prototype.slice.call((r || doc).querySelectorAll(s)); }
    function lite() { 
      var f = doc.getElementById('fx-flags'); 
      return !!(f && f.getAttribute('data-lite') === '1'); 
    }
    var reduced = host.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var coarse = host.matchMedia('(pointer: coarse)').matches;
    function fxOff() { return lite() || reduced; }

    /* ---------- State ---------- */
    var mx = -200, my = -200, rx = -200, ry = -200, ticking = false, ready = false;
    var dot = mk('div', 'fx-cursor-dot'), ring = mk('div', 'fx-cursor-ring');
    var bar = mk('div', 'fx-progress');

    /* ---------- Cursor Spring Loop ---------- */
    function frame() {
      ticking = false;
      if (lite() || coarse) { root.classList.remove('fx-cursor-on'); return; }
      rx += (mx - rx) * 0.22; 
      ry += (my - ry) * 0.22;
      dot.style.transform = 'translate3d(' + mx + 'px,' + my + 'px,0)';
      ring.style.transform = 'translate3d(' + rx + 'px,' + ry + 'px,0)';
      if (Math.abs(mx - rx) > 0.15 || Math.abs(my - ry) > 0.15) schedule();
    }
    function schedule() { 
      if (!ticking) { ticking = true; host.requestAnimationFrame(frame); } 
    }

    function hoverState(t) {
      if (!t || !t.closest) return;
      var isText = !!t.closest('input:not([readonly]),textarea,[contenteditable="true"]');
      var isLink = !isText && !!t.closest('button,a,[role="tab"],[role="option"],summary,[data-baseweb="select"],[data-testid="stToggle"],[data-testid="stCheckbox"],label,input[readonly]');
      ring.classList.toggle('is-text', isText); 
      dot.classList.toggle('is-text', isText);
      ring.classList.toggle('is-link', isLink);
    }

    /* ---------- Magnetic Button Pull ---------- */
    var magnetQueued = false, lastE = null;
    function magnets() {
      magnetQueued = false;
      if (!lastE || fxOff() || coarse) return;
      $$('[data-testid="stBaseButton-primary"],.stButton > button[kind="primary"]').forEach(function (b) {
        var r = b.getBoundingClientRect(); 
        if (!r.width) return;
        var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        var dx = lastE.clientX - cx, dy = lastE.clientY - cy;
        var near = Math.abs(dx) < r.width / 2 + 50 && Math.abs(dy) < r.height / 2 + 50;
        b.style.setProperty('--tx', near ? Math.max(-6, Math.min(6, dx * 0.12)) + 'px' : '0px');
        b.style.setProperty('--ty', near ? Math.max(-4, Math.min(4, dy * 0.18)) + 'px' : '0px');
      });
    }

    on(doc, 'pointermove', function (e) {
      if (e.pointerType === 'touch') return;
      mx = e.clientX; my = e.clientY; lastE = e;
      if (!ready || rx < -100) { rx = mx; ry = my; }
      if (coarse || lite()) {
        root.classList.remove('fx-cursor-on');
      } else {
        root.classList.add('fx-cursor-on'); 
        schedule();
      }
      root.style.setProperty('--mx', mx + 'px'); 
      root.style.setProperty('--my', my + 'px');
      
      var t = e.target;
      var card = t && t.closest ? t.closest('.fx-card,[class*="st-key-panel"]') : null;
      if (card) {
        var r = card.getBoundingClientRect(); 
        card.style.setProperty('--cx', (mx - r.left) + 'px'); 
        card.style.setProperty('--cy', (my - r.top) + 'px'); 
      }
      
      var tilt = t && t.closest ? t.closest('[data-testid="stImage"] img') : null;
      if (tilt && !fxOff()) {
        var tr = tilt.getBoundingClientRect();
        var px = (mx - tr.left) / tr.width - 0.5, py = (my - tr.top) / tr.height - 0.5;
        tilt.style.setProperty('--ry', (px * 8).toFixed(2) + 'deg'); 
        tilt.style.setProperty('--rx', (-py * 8).toFixed(2) + 'deg');
      }
      hoverState(t);
      if (!magnetQueued) { magnetQueued = true; host.requestAnimationFrame(magnets); }
    }, { passive: true });

    on(doc, 'pointerleave', function () { root.classList.remove('fx-cursor-on'); }, true);
    on(doc, 'pointerout', function (e) {
      var t = e.target; 
      if (t && t.matches && t.matches('[data-testid="stImage"] img')) { 
        t.style.setProperty('--rx', '0deg'); 
        t.style.setProperty('--ry', '0deg'); 
      }
    }, true);

    on(doc, 'pointerdown', function (e) {
      if (fxOff() || coarse) return;
      ring.classList.add('is-down');
      var r = mk('div', 'fx-ripple'); 
      r.style.left = e.clientX + 'px'; 
      r.style.top = e.clientY + 'px';
      host.setTimeout(function () { if (r.parentNode) r.parentNode.removeChild(r); }, 650);
    }, { passive: true });

    on(doc, 'pointerup', function () { ring.classList.remove('is-down'); }, { passive: true });

    /* ---------- Tab Dynamic Accent & Scroll Progress ---------- */
    function syncTab() {
      var list = $('.stTabs [role="tablist"]'); 
      if (!list) return;
      var tabs = $$('[role="tab"]', list), idx = 0;
      tabs.forEach(function (t, i) { 
        if (t.getAttribute('aria-selected') === 'true') idx = i; 
      });
      if (root.getAttribute('data-tab') !== String(idx)) {
        root.setAttribute('data-tab', String(idx));
      }
    }

    on(doc, 'scroll', function (e) {
      var t = e.target === doc ? doc.scrollingElement : e.target;
      if (!t || !t.scrollHeight) return;
      var max = t.scrollHeight - t.clientHeight; 
      if (max < 40) return;
      bar.style.transform = 'scaleX(' + Math.min(1, t.scrollTop / max).toFixed(4) + ')';
    }, { capture: true, passive: true });

    /* ---------- Interactive Chat Checklists & Task Persistence ---------- */
    function enhanceChecklists() {
      $$('[data-testid="stChatMessage"] li.task-list-item, [data-testid="stChatMessage"] ul.contains-task-list li, [data-testid="stChatMessage"] li:has(input[type="checkbox"])').forEach(function (li) {
        var cb = li.querySelector('input[type="checkbox"]');
        if (!cb) return;
        if (cb.getAttribute('data-interactive') === '1') return;
        cb.setAttribute('data-interactive', '1');
        cb.removeAttribute('disabled');
        cb.style.pointerEvents = 'auto';
        cb.style.cursor = 'pointer';
        
        var taskText = li.textContent.trim().replace(/\s+/g, ' ').substring(0, 100);
        var storageKey = 'aihub_task_' + taskText;
        try {
          if (host.localStorage && host.localStorage.getItem(storageKey) === '1') {
            cb.checked = true;
            li.classList.add('task-completed');
          }
        } catch (e) {}

        cb.addEventListener('change', function () {
          if (cb.checked) {
            li.classList.add('task-completed');
            try { if (host.localStorage) host.localStorage.setItem(storageKey, '1'); } catch (e) {}
          } else {
            li.classList.remove('task-completed');
            try { if (host.localStorage) host.localStorage.removeItem(storageKey); } catch (e) {}
          }
        });
      });
    }

    /* ---------- Decorate Components & Lock Dropdowns ---------- */
    var CARD = '[data-testid="stExpander"],[data-testid="stChatMessage"],[data-testid="stFileUploaderDropzone"],.step,.cred,.tele,.empty,.ph .cell,.hx-card,[class*="st-key-panel"]';
    function decorate() {
      $$(CARD).forEach(function (n) { 
        if (!n.classList.contains('fx-card')) n.classList.add('fx-card'); 
      });
      $$('div[data-baseweb="select"] input, [data-testid="stSelectbox"] input, .stSelectbox input, .react-aria-ComboBox input').forEach(function (i) { 
        if (i.tagName === 'INPUT' && !i.closest('[data-testid="stTextInput"],[data-testid="stTextArea"],.stTextInput,.stTextArea')) { 
          i.style.caretColor = 'transparent'; 
          i.style.cursor = 'pointer'; 
          i.setAttribute('readonly', 'readonly');
        } 
      });
      // Explicitly guarantee all text inputs and textareas allow full paste, typing, and selection
      $$('[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, .stTextInput input, .stTextArea textarea').forEach(function (i) {
        if (i.hasAttribute('readonly') && !i.dataset.keepReadonly) {
          i.removeAttribute('readonly');
        }
        i.style.caretColor = '#22d3ee';
        i.style.cursor = 'text';
        i.style.userSelect = 'text';
      });
      enhanceChecklists();
    }

    function checkFullscreen() {
      var isFs = !!doc.querySelector('button[aria-label*="Close fullscreen"], button[title*="Exit fullscreen" i], button[title*="close fullscreen" i]');
      doc.body.classList.toggle('in-fullscreen', isFs);
      root.classList.toggle('in-fullscreen', isFs);
    }

    var queued = false;
    function refresh() { 
      queued = false; 
      decorate(); 
      syncTab(); 
      startHero(); 
      checkFullscreen();
    }

    var mo = new host.MutationObserver(function () {
      if (!queued) { queued = true; host.requestAnimationFrame(refresh); }
    });
    mo.observe(doc.body, { childList: true, subtree: true });
    
    var mo2 = new host.MutationObserver(function () { syncTab(); });
    mo2.observe(doc.body, { attributes: true, attributeFilter: ['aria-selected'], subtree: true });
    cleanups.push(function () { mo.disconnect(); mo2.disconnect(); });

    /* ---------- Hero Constellation Canvas (Interactive Particles) ---------- */
    function startHero() {
      var slot = $('#fx-hero-slot'); 
      if (!slot || slot.getAttribute('data-bound') === '1') return;
      slot.setAttribute('data-bound', '1');
      var cv = doc.createElement('canvas'); 
      slot.appendChild(cv);
      var ctx = cv.getContext && cv.getContext('2d'); 
      if (!ctx) return;
      var W = 0, H = 0, dpr = Math.min(host.devicePixelRatio || 1, 1.5), N = 64, pts = [], visible = true, raf = 0;

      function size() {
        var r = slot.getBoundingClientRect(); 
        W = Math.max(1, r.width); 
        H = Math.max(1, r.height);
        cv.width = W * dpr; 
        cv.height = H * dpr; 
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      size();

      for (var i = 0; i < N; i++) {
        pts.push({ 
          x: Math.random() * W, 
          y: Math.random() * H, 
          vx: (Math.random() - 0.5) * 0.35, 
          vy: (Math.random() - 0.5) * 0.35 
        });
      }

      function col(name, fb) { 
        var v = host.getComputedStyle(root).getPropertyValue(name).trim(); 
        return v || fb; 
      }

      function draw(still) {
        if (!cv.isConnected) { host.cancelAnimationFrame(raf); return; }
        ctx.clearRect(0, 0, W, H);
        var a1 = col('--a1', '#6366f1'), a2 = col('--a2', '#22d3ee');
        var r = cv.getBoundingClientRect(), px = mx - r.left, py = my - r.top;
        var inside = px > 0 && py > 0 && px < W && py < H;

        for (var i = 0; i < N; i++) {
          var p = pts[i];
          if (!still) {
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0 || p.x > W) p.vx *= -1; 
            if (p.y < 0 || p.y > H) p.vy *= -1;
            if (inside) { 
              var dx = px - p.x, dy = py - p.y, d = Math.sqrt(dx * dx + dy * dy); 
              if (d < 140 && d > 1) { 
                p.x += (dx / d) * 0.55; 
                p.y += (dy / d) * 0.55; 
              } 
            }
          }
          for (var j = i + 1; j < N; j++) {
            var q = pts[j], ex = p.x - q.x, ey = p.y - q.y, dd = ex * ex + ey * ey;
            if (dd < 110 * 110) { 
              ctx.globalAlpha = (1 - Math.sqrt(dd) / 110) * 0.35; 
              ctx.strokeStyle = (i + j) % 2 ? a1 : a2; 
              ctx.lineWidth = 1; 
              ctx.beginPath(); 
              ctx.moveTo(p.x, p.y); 
              ctx.lineTo(q.x, q.y); 
              ctx.stroke(); 
            }
          }
          ctx.globalAlpha = 0.9; 
          ctx.fillStyle = i % 3 ? a2 : a1; 
          ctx.beginPath(); 
          ctx.arc(p.x, p.y, 1.6, 0, 6.2832); 
          ctx.fill();
        }
        ctx.globalAlpha = 1;
      }

      function loop() { 
        if (!cv.isConnected) return; 
        if (visible && !doc.hidden && !fxOff()) draw(false); 
        raf = host.requestAnimationFrame(loop); 
      }

      if (fxOff()) { draw(true); } else { loop(); }
      if (host.IntersectionObserver) { 
        var io = new host.IntersectionObserver(function (en) { visible = en[0].isIntersecting; }); 
        io.observe(slot); 
        cleanups.push(function () { io.disconnect(); }); 
      }
      on(host, 'resize', size);
      cleanups.push(function () { host.cancelAnimationFrame(raf); });
    }

    /* ---------- Robust React Aria Tab Switching ---------- */
    function selectTab(idx) {
      var tabList = doc.querySelector('.stTabs [role="tablist"], [data-testid="stTabs"] [role="tablist"]');
      var tabs = tabList ? Array.from(tabList.querySelectorAll('[role="tab"]')) : Array.from(doc.querySelectorAll('[data-testid="stTab"]'));
      if (!tabs.length) tabs = Array.from(doc.querySelectorAll('.stTabs [data-baseweb="tab"]'));
      var target = tabs[idx];
      if (!target) return;
      target.focus();
      try {
        target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, view: host }));
        target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: host }));
        target.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, view: host }));
        target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: host }));
        target.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', code: 'Space', keyCode: 32, bubbles: true }));
        target.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', code: 'Space', keyCode: 32, bubbles: true }));
        target.click();
      } catch (err) {
        target.click();
      }
    }

    /* ---------- Command Palette (Ctrl+K / Cmd+K) ---------- */
    var back = mk('div', 'fx-pal-back'), pal = mk('div', 'fx-pal', back);
    var inp = doc.createElement('input'), list = doc.createElement('ul');
    inp.placeholder = 'Type to search commands or switch tabs... (Esc to close)'; 
    inp.setAttribute('aria-label', 'Command palette'); 
    pal.appendChild(inp); 
    pal.appendChild(list);

    var sel = 0, shown = [];
    function clickText(sel_, text) { 
      var el = $$(sel_).filter(function (n) { return (n.textContent || '').toLowerCase().indexOf(text) > -1; })[0]; 
      if (el) el.click(); 
      return !!el; 
    }

    var CMDS = [
      { t: '⚡ Conversational Studio (Chat & Architecture)', k: '1', f: function () { selectTab(0); } },
      { t: '◈ Visual & Document Auditor (Multi-File)', k: '2', f: function () { selectTab(1); } },
      { t: '✦ Free Image & Video Studio (1024px & 30s MP4)', k: '3', f: function () { selectTab(2); } },
      { t: '↗ Deployment & Cloud AI Guide', k: '4', f: function () { selectTab(3); } },
      { t: '✦ New Chat Session', k: 'N', f: function () { clickText('button', 'new chat'); } },
      { t: '💬 Focus Chat Prompt', k: '/', f: function () { var ta = $('[data-testid="stChatInput"] textarea'); ta && ta.focus(); } },
      { t: '↻ Clear App Cache', k: 'C', f: function () { clickText('button', 'clear cache'); } },
      { t: '⚡ Toggle Lite Effects (0% GPU)', k: 'L', f: function () { clickText('label', 'lite effects'); } }
    ];

    function render() {
      var q = inp.value.toLowerCase().trim(); 
      shown = CMDS.filter(function (c) { return c.t.toLowerCase().indexOf(q) > -1; });
      if (sel >= shown.length) sel = 0; 
      list.innerHTML = '';
      shown.forEach(function (c, i) {
        var li = doc.createElement('li'); 
        li.className = i === sel ? 'sel' : ''; 
        li.innerHTML = '<span></span><small></small>';
        li.firstChild.textContent = c.t; 
        li.lastChild.textContent = c.k;
        li.addEventListener('mousedown', function (e) { 
          e.preventDefault(); 
          run(c); 
        }); 
        list.appendChild(li);
      });
    }

    function run(c) { 
      close(); 
      host.setTimeout(c.f, 40); 
    }
    
    function open() { 
      back.classList.add('open'); 
      inp.value = ''; 
      sel = 0; 
      render(); 
      host.setTimeout(function () { inp.focus(); }, 25); 
    }
    
    function close() { 
      back.classList.remove('open'); 
    }

    on(back, 'mousedown', function (e) { 
      if (e.target === back) close(); 
    });

    on(doc, 'click', function (e) {
      var pill = e.target && e.target.closest ? e.target.closest('.fx-cmd-pill, [data-action="open-palette"]') : null;
      if (pill) {
        e.preventDefault();
        e.stopPropagation();
        open();
        return;
      }
      var comboInp = e.target && e.target.closest ? e.target.closest('.react-aria-ComboBox input, [role="combobox"]') : null;
      if (comboInp) {
        var combo = comboInp.closest('.react-aria-ComboBox');
        var btn = combo ? combo.querySelector('button') : null;
        if (btn && comboInp.getAttribute('aria-expanded') === 'false') {
          btn.click();
        }
      }
    });
    
    on(inp, 'input', render);
    on(inp, 'keydown', function (e) {
      if (e.key === 'ArrowDown') { 
        sel = Math.min(sel + 1, shown.length - 1); 
        render(); 
        e.preventDefault(); 
      } else if (e.key === 'ArrowUp') { 
        sel = Math.max(sel - 1, 0); 
        render(); 
        e.preventDefault(); 
      } else if (e.key === 'Enter') { 
        if (shown[sel]) run(shown[sel]); 
        e.preventDefault(); 
      } else if (e.key === 'Escape') { 
        close(); 
      }
    });

    function handleKey(e) {
      var t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
      var code = e.code || '';
      var isK = (e.key === 'k' || e.key === 'K' || code === 'KeyK');
      if ((e.ctrlKey || e.metaKey) && isK) { 
        e.preventDefault(); 
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        back.classList.contains('open') ? close() : open(); 
        return; 
      }
      if (e.key === 'Escape') {
        if (back.classList.contains('open')) { 
          close(); 
          return; 
        }
        var fsBtn = doc.querySelector('[data-testid="StyledFullScreenButton"], button[title*="exit fullscreen" i], button[title*="close fullscreen" i], [data-testid="stFullScreenFrame"] button');
        if (fsBtn) {
          e.preventDefault();
          fsBtn.click();
          return;
        }
      }
      if (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey && !back.classList.contains('open')) {
        var ta = $('[data-testid="stChatInput"] textarea'); 
        if (ta) { e.preventDefault(); ta.focus(); }
      }
    }

    on(doc, 'keydown', handleKey, { capture: true });
    on(host, 'keydown', handleKey, { capture: true });
    window.addEventListener('keydown', handleKey, { capture: true });

    /* ---------- Boot Sequence ---------- */
    decorate(); 
    syncTab(); 
    startHero();
    root.classList.add('fx-ready');
    host.setTimeout(function () { ready = true; root.setAttribute('data-hero-played', '1'); }, 1500);

    host.__studioFx = {
      ver: VER,
      openPalette: open,
      closePalette: close,
      selectTab: selectTab,
      destroy: function () {
        cleanups.forEach(function (f) { try { f(); } catch (e) { } });
        nodes.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
        root.classList.remove('fx-cursor-on', 'fx-ready'); 
        delete host.__studioFx;
      }
    };
  } catch (err) { 
    try { console.warn('[studio-fx]', err); } catch (e) { } 
  }
})();
