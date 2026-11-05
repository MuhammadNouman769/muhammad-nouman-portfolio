/* Muhammad Nouman: public site behaviour. No dependencies. */
(function () {
  'use strict';
  var root = document.documentElement;
  root.classList.add('js');

  /* ---- theme toggle ---- */
  var themeBtn = document.getElementById('theme-toggle');
  function isDark() {
    var t = root.getAttribute('data-theme');
    return t !== 'light';
  }
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = isDark() ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
    });
  }

  /* ---- mobile menu ---- */
  var burger = document.getElementById('nav-toggle');
  var links = document.getElementById('nav-links');
  if (burger && links) {
    burger.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && links.classList.contains('open')) { links.classList.remove('open'); burger.setAttribute('aria-expanded', 'false'); burger.focus(); }
    });
    links.addEventListener('click', function (e) { if (e.target.tagName === 'A') links.classList.remove('open'); });
  }

  /* ---- hero response panel: types itself once, with syntax colours ---- */
  var panel = document.getElementById('response');
  if (panel) {
    var body = panel.querySelector('.r-body');
    var raw = body.textContent;
    var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
    var paint = function (text) {
      return esc(text)
        .replace(/("[^"\n]*")(\s*:)/g, '<span class="k">$1</span>$2')
        .replace(/:\s*("[^"\n]*")/g, function (m, s) { return m.replace(s, '<span class="s">' + s + '</span>'); })
        .replace(/(\[|, )("[^"\n]*")/g, '$1<span class="s">$2</span>')
        .replace(/:\s*(\d+|true|false)/g, function (m, n) { return m.replace(n, '<span class="n">' + n + '</span>'); });
    };
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      body.innerHTML = paint(raw);
    } else {
      panel.style.minHeight = panel.offsetHeight + 'px';
      body.textContent = '';
      var i = 0, step = 3;
      setTimeout(function tick() {
        i += step;
        var done = i >= raw.length;
        body.innerHTML = paint(raw.slice(0, i)) + (done ? '' : '<span class="r-caret"></span>');
        if (!done) setTimeout(tick, 16);
      }, 700);
    }
  }

  /* ---- projects page: filter by status, text and technology ---- */
  var idx = document.getElementById('index');
  var filters = document.getElementById('filters');
  if (idx && filters) {
    var rows = Array.prototype.slice.call(idx.querySelectorAll('.row'));
    var q = document.getElementById('q'), tag = document.getElementById('tag');
    var count = document.getElementById('count'), none = document.getElementById('none');
    var status = '';
    var apply = function () {
      var term = q.value.trim().toLowerCase(), t = tag.value, shown = 0;
      rows.forEach(function (r) {
        var ok = (!status || r.dataset.status === status) &&
                 (!term || r.dataset.text.indexOf(term) > -1) &&
                 (!t || r.dataset.tags.indexOf('|' + t + '|') > -1);
        r.hidden = !ok; if (ok) shown++;
      });
      count.textContent = shown + (shown === 1 ? ' project' : ' projects');
      none.hidden = shown !== 0;
    };
    filters.querySelectorAll('[data-status]').forEach(function (b) {
      b.addEventListener('click', function () {
        filters.querySelectorAll('[data-status]').forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on'); status = b.dataset.status; apply();
      });
    });
    q.addEventListener('input', apply); tag.addEventListener('change', apply);
    var pre = new URLSearchParams(location.search).get('tech');
    if (pre) { tag.value = pre; apply(); }
  }

  /* ---- lamp: a pendant light with a pull chain. Real pendulum swing, click sound, warm-up flicker. ---- */
  var reduceM = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var lamp = document.querySelector('[data-lamp]');
  if (lamp) {
    var swing = lamp.querySelector('.lamp-swing'), chain = lamp.querySelector('.lamp-chain'), lbody = lamp.querySelector('.lamp-body');
    var beam = document.querySelector('.lamp-beam'), dust = beam && beam.querySelector('.lamp-dust');
    var isOn = function () { return !root.classList.contains('lamp-off'); };
    var origin = function () {
      var r = lbody.getBoundingClientRect();
      root.style.setProperty('--lx', (r.left + r.width / 2) + 'px');
      root.style.setProperty('--ly', (r.top + r.height * .8) + 'px');
    };
    var lock = function () {
      var dark = !isOn();
      document.querySelectorAll('header.nav, nav.tabbar, footer, main > *, .banner > *').forEach(function (el) {
        el.inert = dark && !el.contains(chain) && el !== lamp;
      });
      chain.setAttribute('aria-pressed', isOn() ? 'true' : 'false');
      chain.setAttribute('aria-label', isOn() ? 'Pull the chain to turn the light off' : 'Pull the chain to turn the light on');
    };

    /* click sound, synthesised so no audio file is needed; only ever played after a user gesture */
    var actx = null;
    var click = function (on) {
      try {
        actx = actx || new (window.AudioContext || window.webkitAudioContext)();
        if (actx.state === 'suspended') actx.resume();
        var t = actx.currentTime, len = Math.floor(actx.sampleRate * .045), buf = actx.createBuffer(1, len, actx.sampleRate), d = buf.getChannelData(0);
        for (var i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 5);
        var src = actx.createBufferSource(); src.buffer = buf;
        var bp = actx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = on ? 2600 : 1900; bp.Q.value = 1.2;
        var g = actx.createGain(); g.gain.value = .55;
        src.connect(bp); bp.connect(g); g.connect(actx.destination); src.start(t);
        var o = actx.createOscillator(), og = actx.createGain();
        o.type = 'triangle'; o.frequency.setValueAtTime(on ? 190 : 140, t); o.frequency.exponentialRampToValueAtTime(60, t + .09);
        og.gain.setValueAtTime(.22, t); og.gain.exponentialRampToValueAtTime(.001, t + .11);
        o.connect(og); og.connect(actx.destination); o.start(t); o.stop(t + .12);
      } catch (e) {}
    };

    /* pendulum: damped spring toward a tiny breeze, kicked by every pull */
    var ang = 0, vel = 0, last = 0, lean = 0, running = false, visible = true;
    var frame = function (now) {
      var dt = Math.min(.034, (now - last) / 1000 || .016); last = now;
      var breeze = reduceM ? 0 : Math.sin(now / 1900) * .7;
      var acc = -34 * (ang - breeze - lean) - 2.6 * vel;
      vel += acc * dt; ang += vel * dt;
      swing.style.transform = 'rotate(' + ang.toFixed(3) + 'deg)';
      if (beam) beam.style.setProperty('--sway', ang.toFixed(3) + 'deg');
      if (running && visible && !reduceM) requestAnimationFrame(frame);
      else running = false;
    };
    var kick = function (v) { vel += v; if (!running && !reduceM) { running = true; last = performance.now(); requestAnimationFrame(frame); } };
    var run = function () { if (!running && visible && !reduceM) { running = true; last = performance.now(); requestAnimationFrame(frame); } };
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; if (visible) { run(); dustStart(); } }).observe(lamp);
    run();

    /* dust motes drifting through the beam while the light is on */
    var motes = [], dctx = dust && dust.getContext('2d'), dustOn = false;
    var dustStart = function () {
      if (!dctx || reduceM || dustOn || !isOn()) return;
      var W = dust.width = beam.clientWidth, H = dust.height = beam.clientHeight;
      if (!motes.length) for (var i = 0; i < 46; i++) motes.push({ x: Math.random(), y: Math.random(), r: Math.random() * 1.4 + .5, s: Math.random() * .00006 + .00002, a: Math.random() * 6 });
      dustOn = true;
      (function draw(now) {
        if (!dustOn || !isOn() || !visible) { dustOn = false; return; }
        dctx.clearRect(0, 0, W, H);
        motes.forEach(function (m) {
          m.y += m.s * 16; m.x += Math.sin(now / 2400 + m.a) * .0003; if (m.y > 1) { m.y = .08; m.x = Math.random(); }
          dctx.globalAlpha = (.25 + .6 * Math.abs(Math.sin(now / 1600 + m.a))) * Math.min(1, m.y * 3);
          dctx.fillStyle = '#ffe2a0'; dctx.beginPath(); dctx.arc(m.x * W, m.y * H, m.r, 0, 6.283); dctx.fill();
        });
        if (!visible) { dustOn = false; return; }
        requestAnimationFrame(draw);
      })(0);
    };

    var set = function (on) {
      origin();
      if (!on) window.scrollTo(0, 0);
      root.classList.toggle('lamp-off', !on);
      if (on) { lamp.classList.add('lamp-warm'); setTimeout(function () { lamp.classList.remove('lamp-warm'); }, 1250); setTimeout(dustStart, 600); }
      try { sessionStorage.setItem('lamp', on ? 'on' : 'off'); } catch (e) {}
      lock(); click(on);
      if (navigator.vibrate) { try { navigator.vibrate(12); } catch (e) {} }
    };
    var pull = function () { kick(on0() ? 46 : -46); set(!isOn()); };
    var on0 = function () { return isOn(); };
    origin(); lock(); dustStart();
    var _lw = window.innerWidth; window.addEventListener('resize', function () { if (window.innerWidth === _lw) return; _lw = window.innerWidth; origin(); if (dust && dustOn) { dust.width = beam.clientWidth; dust.height = beam.clientHeight; } });

    /* drag the chain down to pull; a tap or Enter/Space works too */
    var startY = null, moved = false, fired = false;
    var PULL_AT = 12;   /* px of downward drag that switches the light: lower = more sensitive */
    chain.addEventListener('pointerdown', function (e) { startY = e.clientY; moved = false; fired = false; chain.classList.remove('snap'); chain.setPointerCapture(e.pointerId); });
    chain.addEventListener('pointermove', function (e) {
      if (startY === null) return;
      var dy = Math.max(0, Math.min(38, e.clientY - startY));
      chain.style.setProperty('--drag', dy + 'px'); lean = dy * .09; run();
      if (dy >= PULL_AT && !fired) { fired = true; moved = true; pull(); }   /* switches the moment the chain is pulled down */
    });
    var release = function () {
      if (startY === null) return;
      startY = null; lean = 0; chain.classList.add('snap'); chain.style.setProperty('--drag', '0px');
    };
    chain.addEventListener('pointerup', release);
    chain.addEventListener('pointercancel', function () { startY = null; lean = 0; chain.classList.add('snap'); chain.style.setProperty('--drag', '0px'); });
    chain.addEventListener('click', function (e) {
      if (moved) { moved = false; return; }
      chain.classList.add('snap'); chain.style.setProperty('--drag', '24px');
      setTimeout(function () { chain.style.setProperty('--drag', '0px'); }, 110);
      pull();
    });
  }

  /* ======================================================================
     Motion system. Everything below is progressive: without JS the page is
     fully visible, and prefers-reduced-motion skips all of it.
     ====================================================================== */
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  /* ---- split headings into words that slide up ---- */
  $$('.hero h1, .page-head h1, .block-head h2, .block > .wrap > h2, .foot-cta h2, .split-title h2').forEach(function (h) {
    if (h.querySelector('*')) return;
    var words = h.textContent.trim().split(/\s+/);
    h.setAttribute('aria-label', h.textContent.trim());
    h.innerHTML = words.map(function (w, i) { return '<span class="w" aria-hidden="true"><span style="--wi:' + i + '">' + w.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</span></span>'; }).join(' ');
    h.classList.add('split');
    if (h.closest('.hero, .page-head')) h.style.setProperty('--base', '200ms');
  });

  /* ---- scroll reveal with automatic stagger among siblings ---- */
  var auto = '.row, .role, .service-grid li, .svc-list li, .manifest-group, .skill-row, .timeline > li, .ledger li, .ticks li, .prose > *, .detail-side, .shot, .facts, .block-head .link-quiet, .lede, .avail, .row-actions, .about-photo, .foot-cta p, .foot-cta .btn, .foot-grid > *, .pager a, .filters, .skill-card, .cs-tile, .post, .feat, .mag-card, .pr-grid li, .cs-story, .cs-arch, .metric, .flow li, .steps li, .commits > li, .tri, .case-card, .art-cta, .cs-cta';
  $$(auto).forEach(function (el) {
    if (el.hasAttribute('data-reveal') || el.closest('.hero-stage') || el.closest('.case-card') && !el.matches('.case-card') || el.matches('.tri, .case-card')) return;
    el.setAttribute('data-reveal', '');
    var sibs = Array.prototype.filter.call(el.parentNode.children, function (c) { return c.matches(auto); });
    el.style.setProperty('--i', Math.min(sibs.indexOf(el), 7));
  });
  var targets = $$('[data-reveal], .split, .timeline > li');
  if (reduce || !('IntersectionObserver' in window)) {
    targets.forEach(function (t) { t.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { var t = en.target; t.classList.add('in'); io.unobserve(t); if (t.hasAttribute('data-reveal')) setTimeout(function () { t.removeAttribute('data-reveal'); t.style.removeProperty('--i'); }, 1300 + (parseInt(t.style.getPropertyValue('--i'), 10) || 0) * 80); } });
    }, { threshold: .12, rootMargin: '0px 0px -6% 0px' });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* ---- count-up numbers ---- */
  $$('[data-count]').forEach(function (el) {
    var end = parseInt(el.dataset.count, 10) || 0, suf = el.dataset.suffix || '';
    if (reduce || !('IntersectionObserver' in window)) { el.textContent = end + suf; return; }
    el.textContent = '0' + suf;
    var o = new IntersectionObserver(function (en) {
      if (!en[0].isIntersecting) return; o.disconnect();
      var t0 = performance.now(), dur = 1400;
      (function f(t) {
        var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4);
        el.textContent = Math.round(end * e) + suf;
        if (p < 1) requestAnimationFrame(f);
      })(t0);
    }, { threshold: .6 });
    o.observe(el);
  });

  /* ---- scroll progress bar + nav shadow + timeline draw ---- */
  var bar = document.getElementById('progress'), nav = document.querySelector('.nav'), tl = document.querySelector('.timeline');
  /* one animation frame per burst of scroll/resize events (phones fire these constantly) */
  var raf1 = function (fn) { var q = false; return function () { if (q) return; q = true; requestAnimationFrame(function () { q = false; fn(); }); }; };
  /* mobile URL bars fire resize on every scroll; only react to real width changes */
  var onWidth = function (fn) { var w = window.innerWidth; window.addEventListener('resize', function () { if (window.innerWidth !== w) { w = window.innerWidth; fn(); } }); };
  var ticking = false;
  var onScroll = function () {
    ticking = false;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    if (bar) bar.style.transform = 'scaleX(' + (h > 0 ? Math.min(1, window.scrollY / h) : 0) + ')';
    if (nav) nav.classList.toggle('scrolled', window.scrollY > 8);
    if (tl) {
      var r = tl.getBoundingClientRect(), p = (window.innerHeight * .6 - r.top) / r.height;
      tl.style.setProperty('--p', Math.max(0, Math.min(1, p)).toFixed(3));
    }
  };
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onWidth(onScroll); onScroll();

  if (!reduce && fine) {
    /* ---- cursor glow, spotlight cards ---- */
    var glow = document.getElementById('glow');
    if (glow) {
      var gx = 0, gy = 0, gt = false;
      window.addEventListener('pointermove', function (e) {
        gx = e.clientX; gy = e.clientY;
        if (!gt) { gt = true; requestAnimationFrame(function () { glow.style.transform = 'translate(' + gx + 'px,' + gy + 'px)'; glow.classList.add('on'); gt = false; }); }
      }, { passive: true });
      document.addEventListener('pointerleave', function () { glow.classList.remove('on'); });
    }
    $$('.spot, .spot-card, .stat, .service-grid li, .svc-list li, .role, .c-card').forEach(function (c) {
      c.classList.add('spot');
      c.addEventListener('pointermove', function (e) {
        var r = c.getBoundingClientRect();
        c.style.setProperty('--mx', (e.clientX - r.left) + 'px'); c.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
    /* ---- tilt the portrait ---- */
    var tilt = document.querySelector('[data-tilt] .arch-wrap');
    if (tilt) {
      var host = tilt.parentNode;
      host.addEventListener('pointermove', function (e) {
        var r = host.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        tilt.style.transform = 'rotateY(' + (x * 12).toFixed(2) + 'deg) rotateX(' + (-y * 10).toFixed(2) + 'deg)';
      });
      host.addEventListener('pointerleave', function () { tilt.style.transform = ''; });
    }
    /* ---- magnetic buttons ---- */
    $$('.btn-lg, .hero .btn, .foot .btn').forEach(function (b) {
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        b.style.translate = ((e.clientX - r.left - r.width / 2) * .18).toFixed(1) + 'px ' + ((e.clientY - r.top - r.height / 2) * .28).toFixed(1) + 'px';
      });
      b.addEventListener('pointerleave', function () { b.style.translate = ''; });
    });
  }

  /* ======================================================================
     Contact form: floating labels, live validation, AJAX send, confetti.
     Falls back to a normal POST + redirect if fetch is unavailable.
     ====================================================================== */
  var form = document.getElementById('contact-form');
  if (form) {
    var card = form.closest('.form-card'), success = document.getElementById('success');
    var errBox = document.getElementById('form-error'), btn = form.querySelector('.send');
    var counter = document.getElementById('counter');
    var rules = {
      name: function (v) { return v.trim().length >= 2 ? '' : 'Please tell me your name.'; },
      email: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) ? '' : 'That email address looks incomplete.'; },
      message: function (v) { return v.trim().length >= 10 ? '' : 'Please write at least a sentence so I can reply properly.'; }
    };
    var mark = function (name, msg, show) {
      var f = form.querySelector('[data-field="' + name + '"]'); if (!f) return;
      var inp = f.querySelector('input, textarea');
      f.classList.toggle('bad', !!msg); f.classList.toggle('ok', !msg && show && inp.value.trim() !== '');
      var e = f.querySelector('.err'); if (e) e.textContent = msg || '';
      inp.setAttribute('aria-invalid', msg ? 'true' : 'false');
    };
    Object.keys(rules).forEach(function (n) {
      var inp = form.elements[n]; if (!inp) return;
      inp.addEventListener('blur', function () { mark(n, rules[n](inp.value), true); });
      inp.addEventListener('input', function () { if (inp.closest('.field').classList.contains('bad')) mark(n, rules[n](inp.value), true); else if (rules[n](inp.value) === '') mark(n, '', true); });
    });
    if (form.elements.message && counter) {
      var upd = function () { counter.textContent = form.elements.message.value.length + ' / 2000'; };
      form.elements.message.addEventListener('input', upd); upd();
    }
    var restart = function (f) { f.classList.remove('bad'); void f.offsetWidth; f.classList.add('bad'); };
    form.addEventListener('submit', function (e) {
      var first = null;
      Object.keys(rules).forEach(function (n) {
        var inp = form.elements[n], m = rules[n](inp.value);
        mark(n, m, true); if (m) { restart(inp.closest('.field')); if (!first) first = inp; }
      });
      if (first) { e.preventDefault(); first.focus(); return; }
      if (!window.fetch) { btn.disabled = true; return; }
      e.preventDefault();
      errBox.hidden = true; btn.classList.add('loading');
      fetch(form.action || location.href, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
        .then(function (r) { return r.json().then(function (j) { return { r: r, j: j }; }); })
        .then(function (o) {
          btn.classList.remove('loading');
          if (o.j.ok) return done();
          if (o.j.errors) { Object.keys(o.j.errors).forEach(function (n) { mark(n, o.j.errors[n][0], true); var f = form.querySelector('[data-field="' + n + '"]'); if (f) restart(f); }); }
          errBox.textContent = o.j.error || 'Some fields need attention. Check the highlighted ones and send again.'; errBox.hidden = false;
        })
        .catch(function () { btn.classList.remove('loading'); errBox.textContent = 'Could not send. Check your connection and try again, or email me directly.'; errBox.hidden = false; });
    });
    var done = function () {
      card.style.minHeight = card.offsetHeight + 'px';
      form.classList.add('is-done');
      setTimeout(function () { success.classList.add('show'); success.focus({ preventScroll: true }); if (!reduce) confetti(document.getElementById('confetti'), card.getBoundingClientRect()); }, 350);
    };
    var again = document.getElementById('again');
    if (again) again.addEventListener('click', function () {
      form.reset(); $$('.field', form).forEach(function (f) { f.classList.remove('ok', 'bad'); });
      if (counter) counter.textContent = '0 / 2000';
      success.classList.remove('show'); form.classList.remove('is-done'); card.style.minHeight = '';
    });

  }

  function confetti(cv, r) {
    if (!cv) return;
    var ctx = cv.getContext('2d'), W = cv.width = window.innerWidth, H = cv.height = window.innerHeight;
    var cols = ['#6c8aff', '#35d4f0', '#f5b642', '#3fc3a1', '#ffffff'];
    var ps = []; for (var i = 0; i < 110; i++) ps.push({ x: r.left + r.width / 2, y: r.top + 120, vx: (Math.random() - .5) * 14, vy: -Math.random() * 13 - 4, s: Math.random() * 7 + 4, a: Math.random() * 6, va: (Math.random() - .5) * .4, c: cols[i % cols.length], life: 1 });
    (function f() {
      ctx.clearRect(0, 0, W, H); var alive = false;
      ps.forEach(function (p) {
        p.vy += .38; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.a += p.va; p.life -= .008;
        if (p.life > 0 && p.y < H + 20) { alive = true; ctx.save(); ctx.globalAlpha = Math.max(0, p.life); ctx.translate(p.x, p.y); ctx.rotate(p.a); ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore(); }
      });
      if (alive) requestAnimationFrame(f); else ctx.clearRect(0, 0, W, H);
    })();
  }

  /* ---- copy email card ---- */
  $$('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var tag = b.querySelector('.copied'), val = b.dataset.copy;
      var ok = function () { if (tag) { tag.classList.add('show'); setTimeout(function () { tag.classList.remove('show'); }, 1600); } };
      if (navigator.clipboard) navigator.clipboard.writeText(val).then(ok, function () { location.href = 'mailto:' + val; });
      else location.href = 'mailto:' + val;
    });
  });

  /* ======================================================================
     v4 behaviours: hire dialog, nudge, app sheet, accordion, tabs, scroll-linked sequences
     ====================================================================== */
  /* ---- hire dialog ---- */
  var dlg = document.getElementById('hire-dialog'), hform = document.getElementById('hire-form');
  var more = document.getElementById('more-sheet'), moreBack = document.getElementById('sheet-back'), moreBtn = document.getElementById('more-btn');
  var closeSheet = function () {
    if (!more || !more.classList.contains('open')) return;
    more.classList.remove('open'); moreBack.classList.remove('open');
    setTimeout(function () { more.hidden = true; moreBack.hidden = true; }, 420);
  };
  var openSheet = function () {
    more.hidden = false; moreBack.hidden = false; void more.offsetWidth;
    more.classList.add('open'); moreBack.classList.add('open');
  };
  if (moreBtn && more) {
    moreBtn.addEventListener('click', function () { more.classList.contains('open') ? closeSheet() : openSheet(); });
    moreBack.addEventListener('click', closeSheet);
    more.addEventListener('click', function (e) { if (e.target.closest('a')) closeSheet(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeSheet(); });
    var sy = null;
    more.addEventListener('touchstart', function (e) { sy = e.touches[0].clientY; }, { passive: true });
    more.addEventListener('touchmove', function (e) { if (sy !== null && e.touches[0].clientY - sy > 70) { sy = null; closeSheet(); } }, { passive: true });
  }
  var hireOpen = function (kind) {
    closeSheet();
    if (!dlg || !dlg.showModal) { location.href = '/contact/'; return; }
    if (kind && hform) { var rad = hform.querySelector('input[name=kind][value="' + kind + '"]'); if (rad) rad.checked = true; }
    if (!dlg.open) dlg.showModal();
    setTimeout(function () { var n = document.getElementById('hd-name'); if (n && !('ontouchstart' in window)) n.focus(); }, 60);
  };
  document.addEventListener('click', function (e) {
    var h = e.target.closest('[data-hire]');
    if (h) { e.preventDefault(); hireOpen(h.getAttribute('data-hire')); return; }
    if (dlg && e.target.closest('[data-close]')) dlg.close();
    if (dlg && e.target === dlg) dlg.close();
  });
  if (dlg && hform) {
    var view = document.getElementById('hd-view'), ok = document.getElementById('hd-success'), herr = document.getElementById('hd-error'), hbtn = hform.querySelector('.send');
    dlg.addEventListener('close', function () {
      if (ok.classList.contains('show')) { setTimeout(function () { hform.reset(); view.classList.remove('is-done'); ok.classList.remove('show'); }, 300); }
    });
    hform.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = hform.elements.name.value.trim(), email = hform.elements.email.value.trim();
      var msg = !name ? 'Please tell me your name.' : !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) ? 'That email address looks incomplete.' : '';
      if (msg) { herr.textContent = msg; herr.hidden = false; (!name ? hform.elements.name : hform.elements.email).focus(); return; }
      herr.hidden = true; hbtn.classList.add('loading');
      fetch(hform.action, { method: 'POST', body: new FormData(hform), headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          hbtn.classList.remove('loading');
          if (j.ok) {
            view.classList.add('is-done'); ok.classList.add('show');
            if (!reduce) {
              var cv = document.getElementById('confetti'); if (cv) { dlg.appendChild(cv); confetti(cv, dlg.getBoundingClientRect()); }
            }
            return;
          }
          var first = j.errors && Object.keys(j.errors)[0];
          herr.textContent = j.error || (first ? j.errors[first][0] : 'Could not send. Please try again.'); herr.hidden = false;
        })
        .catch(function () { hbtn.classList.remove('loading'); herr.textContent = 'Could not send. Check your connection or email me directly.'; herr.hidden = false; });
    });
  }

  /* ---- hiring nudge: shown once per session after the visitor has looked around ---- */
  var nudge = document.getElementById('nudge');
  if (nudge) {
    var seen = false; try { seen = sessionStorage.getItem('nudge') === '1'; } catch (e) {}
    if (!seen) {
      var show = function () {
        if (root.classList.contains('lamp-off') || (dlg && dlg.open)) return setTimeout(show, 4000);
        nudge.hidden = false; try { sessionStorage.setItem('nudge', '1'); } catch (e) {}
      };
      setTimeout(show, 28000);
    }
    nudge.addEventListener('click', function (e) { if (e.target.closest('[data-nudge-close],[data-hire]')) { nudge.hidden = true; try { sessionStorage.setItem('nudge', '1'); } catch (er) {} } });
  }

  /* ---- hire triptych: one card open at a time ---- */
  $$('[data-accordion]').forEach(function (acc) {
    var cards = $$('.tri', acc);
    var open = function (c) { cards.forEach(function (x) { x.classList.toggle('on', x === c); }); };
    cards.forEach(function (c) {
      c.addEventListener('click', function () { open(c); });
      c.addEventListener('focus', function () { open(c); });
      if (fine) c.addEventListener('mouseenter', function () { open(c); });
    });
  });

  /* ---- tabs with arrow-key support ---- */
  $$('[data-tabs]').forEach(function (box) {
    var tabs = $$('[role=tab]', box), panels = $$('[role=tabpanel]', box);
    var pick = function (t, focus) {
      tabs.forEach(function (x, i) { var on = x === t; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1; panels[i].hidden = !on; });
      if (focus) t.focus();
      if (t.scrollIntoView) t.scrollIntoView({ inline: 'center', block: 'nearest', behavior: reduce ? 'auto' : 'smooth' });
    };
    tabs.forEach(function (t, i) {
      t.tabIndex = i ? -1 : 0;
      t.addEventListener('click', function () { pick(t); });
      t.addEventListener('keydown', function (e) {
        var k = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (!k) return;
        e.preventDefault(); pick(tabs[(i + k + tabs.length) % tabs.length], true);
      });
    });
  });

  /* ---- scroll-linked sequences: progress line + items lighting up ---- */
  var seqs = $$('[data-progress]');
  var seqUpdate = function () {
    var vh = window.innerHeight;
    seqs.forEach(function (el) {
      var r = el.getBoundingClientRect(), p = Math.max(0, Math.min(1, (vh * .62 - r.top) / r.height));
      el.style.setProperty('--p', p.toFixed(3));
      $$('li', el).forEach(function (li) { li.classList.toggle('in', li.getBoundingClientRect().top < vh * .62); });
    });
  };
  if (seqs.length) { window.addEventListener('scroll', raf1(seqUpdate), { passive: true }); onWidth(seqUpdate); seqUpdate(); }

  /* ---- scrub text: words light up as you scroll ---- */
  $$('[data-scrub]').forEach(function (el) {
    var words = el.textContent.trim().split(/\s+/);
    el.setAttribute('aria-label', el.textContent.trim());
    el.innerHTML = words.map(function (w) { return '<span class="sw" aria-hidden="true">' + w.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</span>'; }).join(' ');
    var sw = $$('.sw', el);
    var upd = function () {
      var r = el.getBoundingClientRect(), vh = window.innerHeight;
      var p = reduce ? 1 : Math.max(0, Math.min(1, (vh * .85 - r.top) / (r.height + vh * .35)));
      var n = Math.round(p * sw.length);
      sw.forEach(function (w, i) { w.classList.toggle('on', i < n); });
    };
    window.addEventListener('scroll', raf1(upd), { passive: true }); onWidth(upd); upd();
  });

  /* ---- article: table of contents follows the reader; copy link ---- */
  var toc = $$('.toc a');
  if (toc.length && 'IntersectionObserver' in window) {
    var map = {}; toc.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var hio = new IntersectionObserver(function (en) {
      en.forEach(function (x) { if (x.isIntersecting) { toc.forEach(function (a) { a.classList.remove('on'); }); var a = map[x.target.id]; if (a) a.classList.add('on'); } });
    }, { rootMargin: '-15% 0px -70% 0px' });
    Object.keys(map).forEach(function (id) { var h = document.getElementById(id); if (h) hio.observe(h); });
  }
  $$('[data-copylink]').forEach(function (b) {
    b.addEventListener('click', function () {
      var lbl = b.textContent;
      var done = function () { b.textContent = 'Link copied'; setTimeout(function () { b.textContent = lbl; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done); else done();
    });
  });
})();
