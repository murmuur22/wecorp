(() => {
  const nav = [...document.querySelectorAll('nav a[data-key]')];
  const command = document.querySelector('#command');
  const feedback = document.querySelector('#command-feedback');
  const handle = document.body.dataset.handle;
  const go = url => { window.location.href = url; };
  function back() {
    // Local parent routes avoid sending a visitor back to an unrelated site.
    const view = document.body.dataset.view;
    if (view === 'photo') go(`/@${handle}/gallery/`);
    else if (view === 'post') go(`/@${handle}/blog/`);
    else if (view === 'project') go(`/@${handle}/work/`);
    else if (view === 'portfolio') go('/');
    else go(handle ? `/@${handle}/` : '/');
  }
  for (const a of nav) if (a.dataset.command === 'back') a.addEventListener('click', e => {e.preventDefault(); back();});
  function run(value) {
    const parts = value.trim().split(/\s+/);
    const name = (parts[0] || '').toLowerCase();
    if (name === 'member' && /^[a-z0-9][a-z0-9-]{0,47}$/.test(parts[1] || '') && parts.length === 2) return go(`/@${parts[1]}/`);
    if (name === 'back') return back();
    if (name === 'open' && handle && /^[a-z0-9][a-z0-9-]{0,47}$/.test(parts[1] || '') && parts.length === 2) {
      const view = document.body.dataset.view;
      const section = view === 'gallery' || view === 'photo' ? 'gallery' : view === 'work' || view === 'project' ? 'work' : 'blog';
      return go(`/@${handle}/${section}/${parts[1]}/`);
    }
    const target = nav.find(a => a.dataset.command === name);
    if (target && parts.length === 1) return go(target.href);
    feedback.textContent = 'Navigation only here. Try home, member murmuur, or help. Editing happens in the SSH terminal.';
  }
  document.querySelector('#command-form').addEventListener('submit', e => { e.preventDefault(); run(command.value); });
  document.querySelector('.member-jump')?.addEventListener('submit', e => {
    e.preventDefault(); const input = e.currentTarget.querySelector('input');
    if (input.checkValidity()) go(`/@${input.value}/`);
  });
  document.addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
    const editing = e.target.matches('input, textarea, select') || e.target.isContentEditable;
    if (editing) { if (e.key === 'Escape') {e.target.blur(); e.preventDefault();} return; }
    if (e.key === '/') {e.preventDefault(); command.focus(); return;}
    if (e.key === 'Escape') {e.preventDefault(); back(); return;}
    const arrow = e.key === 'ArrowLeft' ? 'left' : e.key === 'ArrowRight' ? 'right' : null;
    const frame = arrow && document.querySelector(`[data-arrow="${arrow}"]`);
    if (frame) { e.preventDefault(); go(frame.href); return; }
    const link = nav.find(a => a.dataset.key === e.key.toLowerCase());
    if (link) {e.preventDefault(); go(link.href);}
  });
})();
