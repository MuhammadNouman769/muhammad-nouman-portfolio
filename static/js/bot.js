/* Portfolio Q&A and email updates robot. */
(function () {
  'use strict';
  var root = document.getElementById('bot'); if (!root) return;
  var fab = document.getElementById('bot-fab'), panel = document.getElementById('bot-panel'), log = document.getElementById('bot-log'),
      quick = document.getElementById('bot-quick'), form = document.getElementById('bot-form'), input = document.getElementById('bot-in'),
      bubble = document.getElementById('bot-bubble'), send = form.querySelector('.bot-send'), closeBtn = document.getElementById('bot-x');
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var store = { get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  var step = 'idle', name = '', started = false, busy = false;

  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, reduce ? 0 : ms); }); };
  var scroll = function () { log.scrollTop = log.scrollHeight; };
  var add = function (text, who) { var d = document.createElement('div'); d.className = 'bot-msg ' + who; d.textContent = text; log.appendChild(d); scroll(); return d; };
  var addSources = function (sources) {
    if (!Array.isArray(sources) || !sources.length) return;
    var list = document.createElement('div'); list.className = 'bot-msg nova bot-sources';
    sources.forEach(function (source) {
      try {
        var url = new URL(source.url, window.location.origin);
        if (url.origin !== window.location.origin) return;
        var link = document.createElement('a'); link.href = url.href; link.textContent = source.title; list.appendChild(link);
      } catch (e) {}
    });
    if (list.childNodes.length) { log.appendChild(list); scroll(); }
  };
  var say = function (text) {
    var t = document.createElement('div'); t.className = 'bot-msg nova typing'; t.innerHTML = '<i></i><i></i><i></i>'; log.appendChild(t); scroll();
    return wait(520 + Math.min(text.length * 9, 600)).then(function () { t.remove(); add(text, 'nova'); });
  };
  var enable = function (on, ph, type) { input.disabled = send.disabled = !on; if (ph) input.placeholder = ph; if (type) input.type = type; if (on) { input.value = ''; input.focus({ preventScroll: true }); } };
  var chips = function (list) {
    quick.innerHTML = '';
    list.forEach(function (c) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = c[0];
      b.onclick = function () { quick.innerHTML = ''; add(c[0], 'me'); c[1](); };
      quick.appendChild(b);
    });
  };

  var askQuestion = function () {
    step = 'question';
    return say('Ask me about the projects, skills, services, experience, or articles on this website.')
      .then(function () { enable(true, 'Ask a question', 'text'); input.autocomplete = 'off'; });
  };
  var askName = function () {
    if (store.get('botDone')) { step = 'idle'; return say('You are already subscribed. You can still ask me about the portfolio.').then(showChoices); }
    step = 'name';
    return say('Great. What should I call you?').then(function () { enable(true, 'Your name', 'text'); input.autocomplete = 'name'; });
  };
  var askEmail = function () { step = 'email'; return say('Nice to meet you, ' + name + '. Which email should I use?').then(function () { enable(true, 'you@company.com', 'email'); input.autocomplete = 'email'; input.inputMode = 'email'; }); };
  var done = function () { step = 'done'; enable(false, 'Subscribed'); input.type = 'text'; store.set('botDone', '1'); root.classList.add('seen'); showChoices(); };
  var showChoices = function () {
    chips([['Ask a question', askQuestion], ['Email updates', askName]]);
  };
  var start = function () {
    if (started) return; started = true;
    say('Hi, I am Nova, the portfolio assistant for ' + (root.dataset.owner || 'this site') + '.')
      .then(function () { return say('I can answer questions using public website content, or sign you up for email updates.'); })
      .then(showChoices);
  };

  var open = function () {
    panel.hidden = false; fab.setAttribute('aria-expanded', 'true'); bubble.hidden = true; root.classList.add('seen'); store.set('botSeen', '1');
    start(); if (!input.disabled) input.focus({ preventScroll: true });
  };
  var close = function () { panel.hidden = true; fab.setAttribute('aria-expanded', 'false'); fab.focus({ preventScroll: true }); };
  fab.addEventListener('click', function () { panel.hidden ? open() : close(); });
  closeBtn.addEventListener('click', close);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(); });

  var askServer = function (url, data) {
    return fetch(url, { method: 'POST', body: data, headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
      .then(function (response) {
        return response.json().then(function (payload) {
          if (!response.ok) throw new Error(payload.error || 'Something went wrong. Please try again.');
          return payload;
        });
      });
  };

  form.addEventListener('submit', function (e) {
    e.preventDefault(); if (busy || input.disabled) return;
    var v = input.value.trim(); if (!v) return;
    if (step === 'question') {
      add(v, 'me'); enable(false, 'Searching the website…'); busy = true;
      var questionData = new FormData(form); questionData.set('question', v); questionData.set('website', '');
      askServer(root.dataset.chatUrl, questionData)
        .then(function (payload) { return say(payload.answer).then(function () { addSources(payload.sources); }); })
        .catch(function (error) { return say(error.message || 'I could not reach the server. Please try again.'); })
        .then(function () { busy = false; step = 'question'; enable(true, 'Ask another question', 'text'); });
    } else if (step === 'name') {
      if (v.replace(/[^A-Za-z؀-ۿ]/g, '').length < 2) { add(v, 'me'); enable(false); say('Please type your name, at least two letters.').then(function () { enable(true); }); return; }
      name = v.slice(0, 80); add(v, 'me'); enable(false); askEmail();
    } else if (step === 'email') {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) { add(v, 'me'); enable(false); say('That email does not look right. Could you check it?').then(function () { enable(true); input.value = v; }); return; }
      add(v, 'me'); enable(false); busy = true;
      var fd = new FormData(form); fd.set('name', name); fd.set('email', v);
      say('Adding you to the list…').then(function () { return askServer(root.dataset.url, fd); })
        .then(function (payload) {
          busy = false;
          if (payload.ok) return say('Done, ' + name.split(' ')[0] + '! I sent a welcome email to ' + v + '. You will hear from me when something new is published.').then(done);
          throw new Error(payload.error || 'Something went wrong. Please try again in a moment.');
        }).catch(function (error) {
          busy = false;
          say(error.message || 'I could not reach the server. Please check your connection and try again.')
            .then(function () { step = 'email'; enable(true, 'you@company.com', 'email'); input.value = v; });
        });
    }
  });

  if (!store.get('botSeen')) {
    setTimeout(function () {
      if (!panel.hidden || document.documentElement.classList.contains('lamp-off')) return;
      bubble.hidden = false; setTimeout(function () { bubble.hidden = true; }, 9000);
    }, 22000);
  }
})();
