(() => {
  const model = JSON.parse(document.querySelector('#page-model').textContent);
  const input = document.querySelector('#command');
  const feedback = document.querySelector('#feedback');
  const help = document.querySelector('#help');
  const viewer = document.querySelector('#viewer');
  let imageIndex = 0, imageOpener = null, selected = -1;
  let keysEnabled = true;
  try { keysEnabled = localStorage.getItem('we-explorer-keys') !== 'off'; } catch (_) {}
  const go = url => { location.href = url; };
  const list = () => [...document.querySelectorAll('#directory-bar .entry-token')];
  function select(index) {
    const items = list(); if (!items.length) return;
    selected = (index + items.length) % items.length;
    items.forEach((e,i) => e.classList.toggle('selected', i === selected));
    items[selected].focus();
  }
  function openElement(element) { if (element.dataset.url) go(element.dataset.url); else if (element.href) go(element.href); }
  function back() {
    // Follow same-origin history when available, otherwise use the parent directory.
    if (document.referrer && new URL(document.referrer).origin === location.origin) history.back();
    else go(model.up);
  }
  function raw() {
    const pre = document.querySelector('.raw'), article = document.querySelector('.markdown');
    pre.hidden = !pre.hidden; article.hidden = !pre.hidden;
    document.querySelector('#mode-label').textContent = pre.hidden ? 'HTML' : 'RAW MARKDOWN';
  }
  function toggleKeys() {
    keysEnabled = !keysEnabled;
    try { localStorage.setItem('we-explorer-keys', keysEnabled ? 'on' : 'off'); } catch (_) {}
    feedback.textContent = keysEnabled ? 'Single-key shortcuts enabled.' : 'Single-key shortcuts disabled. Arrows, Tab, Enter and clicks still work.';
    document.querySelector('[data-action=keys]').setAttribute('aria-pressed', String(keysEnabled));
  }
  document.querySelector('[data-action=keys]').setAttribute('aria-pressed', String(keysEnabled));
  function action(name) {
    if (name === 'help') help.showModal();
    else if (name === 'raw') raw();
    else if (name === 'keys') toggleKeys();
    else if (name === 'back') back();
    else if (name === 'home') go('/');
    else if (name === 'up') go(model.up);
  }
  document.querySelectorAll('[data-action]').forEach(e => e.addEventListener('click', event => {event.preventDefault(); action(e.dataset.action);}));
  document.querySelectorAll('[data-close]').forEach(e => e.addEventListener('click', () => document.querySelector('#' + e.dataset.close).close()));
  function image(index, opener=null) {
    if (!model.images.length) return;
    imageIndex = Math.max(0, Math.min(index, model.images.length - 1));
    if (opener) imageOpener = opener;
    const item = model.images[imageIndex];
    const display = document.querySelector('#viewer-image'); display.src = item.url; display.alt = item.alt;
    document.querySelector('#image-caption').textContent = item.alt;
    document.querySelector('#image-position').textContent = `IMAGE ${imageIndex + 1} / ${model.images.length}`;
    document.querySelector('#previous-image').disabled = imageIndex === 0;
    document.querySelector('#next-image').disabled = imageIndex + 1 === model.images.length;
    if (!viewer.open) viewer.showModal();
  }
  document.querySelectorAll('[data-image]').forEach(e => {
    e.addEventListener('click', () => image(Number(e.dataset.image), e));
    e.addEventListener('keydown', event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); image(Number(e.dataset.image), e);}});
  });
  document.querySelector('#previous-image').addEventListener('click', () => image(imageIndex - 1));
  document.querySelector('#next-image').addEventListener('click', () => image(imageIndex + 1));
  viewer.addEventListener('close', () => imageOpener?.focus());
  function run(command) {
    const value = command.trim();
    if (['home','up','back','help','raw','keys'].includes(value)) return action(value);
    if (value === 'ls') { feedback.textContent = model.entries.map(e=>e.label).join('  ') || 'No listed documents.'; return; }
    const match = /^(?:cd|open|cat)\s+(.+)$/.exec(value);
    if (match) {
      let path = match[1].trim().replace(/^(["'])(.*)\1$/, '$2');
      if (path === '..') return go(model.up);
      if (path === '/' || path === '~') return go('/');
      const found = model.entries.find(e => e.label === path || e.label.replace(/\/$/,'') === path || e.path === path);
      if (found) return go(found.url);
      // Resolve a known path without exposing the filesystem or running a shell.
      const base = '/' + (model.directory === '.' ? '' : model.directory + '/');
      if (/^[\w@./ -]+$/.test(path) && !path.split('/').some(p=>p.startsWith('.') && p !== '..' && p !== '.')) {
        if (path.endsWith('/index.md')) path = path.slice(0,-8);
        else if (path === 'index.md') path = './';
        else if (path.endsWith('.md')) path = path.slice(0,-3) + '/';
        else if (!path.endsWith('/')) path += '/';
        const target = new URL(path, location.origin + base);
        if (target.origin === location.origin) return go(target.pathname);
      }
    }
    feedback.textContent = 'Navigation only: ls, cd <folder>, open <document>, cd .., home, help. Edit in your actual terminal.';
  }
  document.querySelector('#command-form').addEventListener('submit', e => {e.preventDefault(); run(input.value);});
  document.addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;
    if (viewer.open) {
      if (e.key === 'ArrowLeft') {e.preventDefault(); image(imageIndex - 1);}
      if (e.key === 'ArrowRight') {e.preventDefault(); image(imageIndex + 1);}
      return;
    }
    if (help.open) return;
    if (e.target.matches('input,textarea,select') || e.target.isContentEditable) {
      if (e.key === 'Escape') {e.preventDefault(); e.target.blur();} return;
    }
    if (e.key === 'Escape') {
      const opened = document.querySelector('details[open]');
      if (opened) {e.preventDefault(); opened.open=false; opened.querySelector('summary').focus();}
      else {e.preventDefault(); back();} return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      // Let submenu links retain ordinary Tab/Enter behavior.
      if (e.target.closest('.submenu')) return;
      if (e.key === 'ArrowRight' && e.target.matches('summary')) {e.preventDefault(); e.target.parentElement.open=true; return;}
      e.preventDefault(); select(selected + (e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? -1 : 1)); return;
    }
    if (e.key === 'Enter' && selected >= 0 && list()[selected] === document.activeElement) {e.preventDefault(); openElement(list()[selected]); return;}
    if (!keysEnabled) return;
    if (e.key === '/') {e.preventDefault(); input.focus(); return;}
    const target = [...document.querySelectorAll('[data-key]')].find(x => x.dataset.key === e.key.toLowerCase());
    if (target) {e.preventDefault(); if (target.dataset.action) action(target.dataset.action); else openElement(target);}
  });
})();
