// Sihirbaz: adım adım ilerleme, koşullu alanlar, özet ve MySQL bağlantı testi.
// JS kapalıysa tüm adımlar tek sayfada görünür ve form yine gönderilebilir.
(() => {
  const form = document.getElementById('wizard');
  if (!form) return;
  form.classList.add('js');
  const steps = [...form.querySelectorAll('fieldset[data-step]')];
  const labels = [...form.querySelectorAll('[data-step-label]')];
  const prev = form.querySelector('[data-prev]');
  const next = form.querySelector('[data-next]');
  const submit = form.querySelector('[data-submit]');
  let current = 0;

  const value = (name) => (form.querySelector(`[name="${name}"]:checked`) || form.elements[name] || {}).value || '';

  function syncConditional() {
    form.querySelectorAll('[data-show-when]').forEach((el) => {
      const [name, val] = el.dataset.showWhen.split('=');
      el.hidden = value(name) !== val;
    });
  }

  function summary() {
    const rows = [
      ['İşletme', value('brand_name')],
      ['Sektör', `${value('sector')} · ${value('location')}`],
      ['Logo', form.elements.logo?.files?.length ? form.elements.logo.files[0].name : 'harf logosu yapılacak'],
      ['Mevcut site', value('own_site') || 'yok'],
      ['İletişim', [value('contact_phone'), value('contact_email')].filter(Boolean).join(' · ') || 'örnek bilgi yazılacak'],
      ['Görünüm', {auto: 'Ajan karar versin', light: 'Aydınlık ve sade', dark: 'Koyu', colorful: 'Canlı ve renkli', minimal: 'Çok sade'}[value('style')] || '—'],
      ['Yapay zekâ', value('ai_backend') === 'api' ? 'Claude API anahtarı' : 'Claude Code oturumu'],
      ['Veri', value('db_type') === 'mysql' ? `MySQL · ${value('db_host')}/${value('db_database')}` : 'Yerel (SQLite)'],
    ];
    form.querySelector('[data-summary]').innerHTML = rows
      .map(([k, v]) => `<dt>${k}</dt><dd>${(v || '—').replace(/</g, '&lt;')}</dd>`).join('');
  }

  function valid(i) {
    const fields = [...steps[i].querySelectorAll('input, select, textarea')].filter((f) => !f.closest('[hidden]'));
    for (const f of fields) {
      if (!f.checkValidity()) { f.reportValidity(); return false; }
    }
    const require = (n, msg) => {
      form.elements[n].setCustomValidity(msg); form.elements[n].reportValidity(); form.elements[n].setCustomValidity('');
      return false;
    };
    if (i === 2 && value('ai_backend') === 'api' && !value('api_key') && !form.dataset.hasKey) {
      return require('api_key', 'API anahtarı girin');
    }
    if (i === 3 && value('db_type') === 'mysql') {
      for (const n of ['db_host', 'db_database', 'db_username']) {
        if (!value(n)) return require(n, 'Bu alan gerekli');
      }
    }
    return true;
  }

  function show(i) {
    current = i;
    steps.forEach((s, j) => { s.hidden = j !== i; });
    labels.forEach((l, j) => { l.classList.toggle('on', j <= i); });
    prev.hidden = i === 0;
    next.hidden = i === steps.length - 1;
    submit.hidden = i !== steps.length - 1;
    if (i === steps.length - 1) summary();
    steps[i].querySelector('input:not([type=radio]):not([hidden]), select, textarea')?.focus();
  }

  next.addEventListener('click', () => { if (valid(current)) show(current + 1); });
  prev.addEventListener('click', () => show(current - 1));
  form.addEventListener('change', syncConditional);
  form.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT' && current < steps.length - 1) { e.preventDefault(); next.click(); }
  });
  form.addEventListener('submit', () => { submit.disabled = true; submit.textContent = 'Başlatılıyor…'; });

  form.querySelector('[data-db-test]')?.addEventListener('click', async (e) => {
    const out = form.querySelector('[data-db-result]');
    out.textContent = 'Deneniyor…';
    const body = new FormData();
    [['host', 'db_host'], ['port', 'db_port'], ['database', 'db_database'], ['username', 'db_username'], ['password', 'db_password']]
      .forEach(([k, n]) => body.append(k, value(n)));
    try {
      const r = await (await fetch('/api/db-test', { method: 'POST', body })).json();
      out.textContent = r.message;
      out.className = 'small ' + (r.ok ? 'ok-text' : 'bad');
    } catch (err) { out.textContent = 'Test edilemedi.'; }
  });

  syncConditional();
  // ?step=2 gibi bir parametreyle doğrudan o adımda açılır (bağlantı paylaşmak/test için)
  const start = Math.min(Math.max(Number(new URLSearchParams(location.search).get('step') || 1) - 1, 0), steps.length - 1);
  show(start);
})();
