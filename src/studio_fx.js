/* =====================================================================
   studio_fx.js - Minimalist, Zero-Overhead Interaction Layer
   Matches production standards of Claude, ChatGPT, and Vercel:
   1. Fast native scrolling & jump-to-bottom button
   2. Seamless keyboard navigation (Escape dialog/fullscreen, '/' focus prompt)
   3. Dropdown click helpers & caret suppression
   4. Tab state synchronization without layout recalculation
   Zero simulated loops, zero canvas particles, zero layout thrashing.
   ===================================================================== */
(function () {
  try {
    var host = window.parent, doc = host.document, root = doc.documentElement;
    var VER = 'fx-v8-smooth';
    if (host.__studioFx && host.__studioFx.ver === VER) return;
    if (host.__studioFx && typeof host.__studioFx.destroy === 'function') host.__studioFx.destroy();

    if (host.history && 'scrollRestoration' in host.history) {
      host.history.scrollRestoration = 'manual';
    }
    var greeting = doc.querySelector('.chat-empty-greeting');
    if (greeting) {
      var scrollerInit = doc.querySelector('[data-testid="stMain"]') || doc.querySelector('section.main') || doc.scrollingElement || doc.body;
      if (scrollerInit && scrollerInit.scrollTop > 10) {
        scrollerInit.scrollTop = 0;
      }
    }

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

    /* ---------- Floating Jump to Bottom Button ---------- */
    var downBtn = mk('button', 'fx-scroll-bottom-btn');
    downBtn.id = 'fx-scroll-bottom-btn';
    downBtn.setAttribute('aria-label', 'Scroll to bottom');
    downBtn.setAttribute('title', 'Jump to latest response');
    downBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>';
    
    on(downBtn, 'click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var scroller = doc.querySelector('[data-testid="stMain"]') || doc.querySelector('section.main') || doc.scrollingElement || doc.body;
      if (scroller) {
        scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' });
      }
      var ta = doc.querySelector('[data-testid="stChatInput"] textarea');
      if (ta) ta.focus();
    });

    /* ---------- Tab Dynamic Accent & Active Sync ---------- */
    function syncTab() {
      var seg = doc.querySelector('[data-testid="stSegmentedControl"]');
      if (seg) {
        var btns = Array.prototype.slice.call(seg.querySelectorAll('button'));
        btns.forEach(function (b, i) {
          if (b.getAttribute('aria-checked') === 'true' || b.getAttribute('aria-selected') === 'true' || b.hasAttribute('data-active')) {
            if (root.getAttribute('data-tab') !== String(i)) root.setAttribute('data-tab', String(i));
          }
        });
        return;
      }
      var radioGroup = doc.querySelector('.st-key-nav_wrapper [role="radiogroup"], .st-key-hub_nav_radio [role="radiogroup"], .st-key-nav [role="radiogroup"]');
      if (radioGroup) {
        var labels = Array.prototype.slice.call(radioGroup.querySelectorAll('label'));
        labels.forEach(function (l, i) {
          var input = l.querySelector('input');
          if (input && input.checked) {
            if (root.getAttribute('data-tab') !== String(i)) root.setAttribute('data-tab', String(i));
          }
        });
        return;
      }
    }

    /* ---------- Scroll Listener for Jump Button ---------- */
    var scrollTicking = false;
    function checkScroll() {
      var scroller = doc.querySelector('[data-testid="stMain"]') || doc.querySelector('section.main') || doc.scrollingElement || doc.body;
      if (scroller && scroller.scrollHeight) {
        var diff = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
        if (diff > 200) {
          downBtn.classList.add('visible');
        } else {
          downBtn.classList.remove('visible');
        }
      }
      scrollTicking = false;
    }
    function onScroll() {
      if (!scrollTicking) {
        host.requestAnimationFrame(checkScroll);
        scrollTicking = true;
      }
    }
    on(doc, 'scroll', onScroll, { passive: true, capture: true });
    var mainEl = doc.querySelector('[data-testid="stMain"]');
    if (mainEl) on(mainEl, 'scroll', onScroll, { passive: true });

    /* ---------- Dropdown Caret Suppression ---------- */
    function suppressCarets() {
      var inputs = doc.querySelectorAll('div[data-testid="stSelectbox"] input, .react-aria-ComboBox input, input[role="combobox"]');
      for (var i = 0; i < inputs.length; i++) {
        inputs[i].style.caretColor = 'transparent';
        inputs[i].style.cursor = 'pointer';
      }
    }

    var queued = false;
    function refresh() {
      queued = false;
      syncTab();
      suppressCarets();
    }

    var mo = new host.MutationObserver(function () {
      if (!queued) {
        queued = true;
        host.requestAnimationFrame(refresh);
      }
    });
    mo.observe(doc.body, { childList: true, subtree: true });
    cleanups.push(function () { mo.disconnect(); });

    /* ---------- Selectbox & Dropdown helpers ---------- */
    on(doc, 'click', function (e) {
      var comboInp = e.target && e.target.closest ? e.target.closest('.react-aria-ComboBox input, [role="combobox"]') : null;
      if (comboInp) {
        var combo = comboInp.closest('.react-aria-ComboBox');
        var btn = combo ? combo.querySelector('button') : null;
        if (btn && comboInp.getAttribute('aria-expanded') === 'false') {
          btn.click();
        }
      }
    });

    /* ---------- Keyboard Shortcuts ---------- */
    function handleKey(e) {
      var t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
      if (e.key === 'Escape') {
        var dialogClose = doc.querySelector('div[role="dialog"] button[aria-label="Close"], [data-testid="stDialog"] button[aria-label="Close"]');
        if (dialogClose) {
          e.preventDefault();
          dialogClose.click();
          return;
        }
        var fsBtn = doc.querySelector('[data-testid="StyledFullScreenButton"], [data-testid="stFullScreenFrame"] button');
        if (fsBtn) {
          e.preventDefault();
          fsBtn.click();
          return;
        }
      }
      if (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        var ta = doc.querySelector('[data-testid="stChatInput"] textarea'); 
        if (ta) { 
          e.preventDefault(); 
          ta.focus(); 
        }
      }
    }

    on(doc, 'keydown', handleKey, { capture: true });
    on(host, 'keydown', handleKey, { capture: true });

    /* ---------- Init ---------- */
    refresh();

    host.__studioFx = {
      ver: VER,
      refresh: refresh,
      checkGreeting: function () {
        var greeting = doc.querySelector('.chat-empty-greeting');
        if (greeting) {
          var scroller = doc.querySelector('[data-testid="stMain"]') || doc.querySelector('section.main') || doc.scrollingElement || doc.body;
          if (scroller && scroller.scrollTop > 10) {
            scroller.scrollTop = 0;
          }
        }
      },
      destroy: function () {
        cleanups.forEach(function (f) { try { f(); } catch (e) { } });
        nodes.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
        delete host.__studioFx;
      }
    };
  } catch (err) { 
    try { console.warn('[studio-fx]', err); } catch (e) { } 
  }
})();
