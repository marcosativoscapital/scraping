// Solve Scraper — Dashboard
// Comunica com FastAPI local (mesma origem por padrão).

(() => {
  'use strict';

  const DEFAULT_API = window.location.origin;
  let API_URL = localStorage.getItem('apiUrl') || DEFAULT_API;
  let API_TOKEN = localStorage.getItem('apiToken') || 'solve-scraper-dev-token';

  // ====== HELPERS ======
  async function api(path, opts = {}) {
    const url = `${API_URL}${path}`;
    const res = await fetch(url, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Token': API_TOKEN,
        ...(opts.headers || {}),
      },
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  }

  function toast(msg, type = 'info') {
    const wrap = document.getElementById('toast-wrap');
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = msg;
    wrap.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 200ms';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 250);
    }, 3000);
  }

  function showModal(title, html) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = html;
    document.getElementById('modal').hidden = false;
  }
  function closeModal() { document.getElementById('modal').hidden = true; }

  function scoreClass(score) {
    if (!score) return 'badge';
    if (score >= 80) return 'badge badge--success';
    if (score >= 60) return 'badge badge--brand';
    if (score >= 40) return 'badge badge--warning';
    return 'badge';
  }

  function verticalLabel(v) {
    return {
      betting: 'Betting',
      pagamentos: 'Pagamentos',
      cobranca: 'Cobrança',
      saas_b2b: 'SaaS B2B',
    }[v] || v;
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  // ====== NAV ======
  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.nav-item').forEach((b) => b.classList.toggle('is-active', b === btn));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('is-active', p.dataset.panel === tab));
      document.getElementById('page-title').textContent = btn.textContent.trim();
      onTabChange(tab);
    });
  });

  function onTabChange(tab) {
    if (tab === 'overview') loadOverview();
    if (tab === 'leads') loadLeads();
    if (tab === 'events') loadEvents();
    if (tab === 'outbound') loadOutboundOptions();
    if (tab === 'settings') loadSettings();
    if (tab === 'sdr') loadSDR();
    if (tab === 'playbooks') loadPlaybooks();
  }

  // ====== HEALTH ======
  async function checkHealth() {
    const pill = document.getElementById('server-status');
    try {
      const data = await api('/');
      pill.classList.remove('is-offline');
      pill.classList.add('is-online');
      pill.querySelector('.label').textContent = `Online · ${data.jobs_ativos || 0} jobs`;
    } catch (e) {
      pill.classList.remove('is-online');
      pill.classList.add('is-offline');
      pill.querySelector('.label').textContent = 'Offline';
    }
  }

  // ====== OVERVIEW ======
  async function loadOverview() {
    try {
      const stats = await api('/stats');
      document.getElementById('m-total').textContent = stats.total.toLocaleString('pt-BR');
      const hot = (stats.score_buckets.q80 || 0) + (stats.score_buckets.q60 || 0);
      document.getElementById('m-hot').textContent = hot.toLocaleString('pt-BR');
      document.getElementById('m-hot-pct').textContent = stats.total ? `${((hot / stats.total) * 100).toFixed(1)}% do total` : '—';
      document.getElementById('m-verticais').textContent = Object.keys(stats.por_vertical || {}).length;

      // Score buckets
      const total = stats.total || 1;
      const buckets = stats.score_buckets || {};
      const labelToKey = { hot: 'q80', warm: 'q60', nurture: 'q40', cold: 'q0' };
      document.querySelectorAll('.bucket').forEach((el) => {
        const k = labelToKey[el.dataset.tier];
        const v = buckets[k] || 0;
        el.querySelector('.bucket__fill').style.width = `${(v / total) * 100}%`;
        el.querySelector('.bucket__count').textContent = v;
      });

      // Verticais
      const vlist = document.getElementById('vertical-list');
      vlist.innerHTML = Object.entries(stats.por_vertical || {})
        .sort((a, b) => b[1] - a[1])
        .map(([v, n]) => {
          const pct = (n / total) * 100;
          return `
            <div class="vertical-row">
              <span class="vertical-row__name">${verticalLabel(v)}</span>
              <span class="bucket__bar"><span class="bucket__fill" style="width:${pct}%"></span></span>
              <span class="vertical-row__count">${n}</span>
            </div>`;
        })
        .join('') || '<div class="empty">Nenhum lead coletado ainda.</div>';

      // Últimos leads
      const tbody = document.querySelector('#recent-table tbody');
      tbody.innerHTML = (stats.ultimos || []).map((l) => `
        <tr>
          <td>${l.empresa || '—'}</td>
          <td><span class="badge badge--brand">${verticalLabel(l.vertical)}</span></td>
          <td class="muted">—</td>
          <td><span class="${scoreClass(l.score_icp)}">${l.score_icp ?? '—'}</span></td>
          <td class="muted">${fmtDate(l.criado_em)}</td>
        </tr>
      `).join('') || '<tr><td colspan="5" class="empty">Sem coletas recentes.</td></tr>';

      // Última coleta
      if (stats.ultimos && stats.ultimos[0]) {
        document.getElementById('m-last').textContent = fmtDate(stats.ultimos[0].criado_em);
        document.getElementById('m-last-vertical').textContent = verticalLabel(stats.ultimos[0].vertical);
      }
    } catch (e) {
      console.error(e);
      toast('Erro ao carregar overview', 'error');
    }
  }

  // ====== LEADS ======
  async function loadLeads() {
    try {
      const vertical = document.getElementById('f-vertical').value;
      const minScore = parseInt(document.getElementById('f-score').value || '0', 10);
      const search = (document.getElementById('f-search').value || '').toLowerCase();

      const params = new URLSearchParams({
        vertical,
        min_score: String(minScore),
        limit: '300',
      });
      const data = await api(`/db/leads?${params.toString()}`);
      let rows = data.leads || [];
      if (search) {
        rows = rows.filter((l) => {
          const haystack = [l.empresa, l.decisor_nome, l.cnpj, l.razao_social].filter(Boolean).join(' ').toLowerCase();
          return haystack.includes(search);
        });
      }

      const tbody = document.querySelector('#leads-table tbody');
      tbody.innerHTML = rows.map((l) => `
        <tr data-lead-id="${l.id}">
          <td><strong>${l.empresa || '—'}</strong>${l.site ? `<br><a href="${l.site}" target="_blank" class="muted">${l.site.replace(/^https?:\/\//, '')}</a>` : ''}</td>
          <td class="muted">${l.cnpj || '—'}</td>
          <td><span class="badge badge--brand">${verticalLabel(l.vertical)}</span></td>
          <td>${l.decisor_nome || '—'}<br><span class="muted">${l.decisor_cargo || ''}</span></td>
          <td class="muted">${l.email_provavel || '—'}</td>
          <td><span class="${scoreClass(l.score_icp)}">${l.score_icp ?? '—'}</span></td>
          <td><span class="badge">${l.recomendacao || '—'}</span></td>
          <td>
            <button class="chip-btn" data-action="detail" data-id="${l.id}">Ver</button>
            ${l.score_icp >= 60 ? `<button class="chip-btn" data-action="outbound" data-id="${l.id}">Outbound</button>` : ''}
          </td>
        </tr>
      `).join('') || '<tr><td colspan="8" class="empty">Nenhum lead encontrado.</td></tr>';

      document.getElementById('leads-count').textContent = `${rows.length} lead(s)`;

      // Bind actions
      tbody.querySelectorAll('button[data-action]').forEach((b) => {
        b.addEventListener('click', () => {
          const id = b.dataset.id;
          if (b.dataset.action === 'detail') showLeadDetail(id);
          if (b.dataset.action === 'outbound') triggerOutbound(id);
        });
      });
    } catch (e) {
      console.error(e);
      toast('Erro ao carregar leads', 'error');
    }
  }

  async function showLeadDetail(id) {
    try {
      const data = await api(`/db/leads/${id}`);
      const lead = data.lead;
      const fields = [
        ['Empresa', lead.empresa],
        ['Razão social', lead.razao_social],
        ['CNPJ', lead.cnpj],
        ['Vertical', verticalLabel(lead.vertical)],
        ['Site', lead.site],
        ['Porte', lead.porte_estimado],
        ['Decisor', `${lead.decisor_nome || '—'} (${lead.decisor_cargo || '—'})`],
        ['LinkedIn', lead.decisor_linkedin],
        ['E-mail', lead.email_provavel],
        ['Score ICP', lead.score_icp],
        ['Recomendação', lead.recomendacao],
        ['Gatilho', lead.gatilho_personalizado],
        ['Observações', lead.observacoes],
        ['Fonte', lead.fonte],
        ['Atualizado em', fmtDate(lead.atualizado_em)],
      ];
      const html = `
        <dl class="lead-detail">
          ${fields.map(([k, v]) => `<div><strong>${k}:</strong> ${v || '—'}</div>`).join('')}
        </dl>
        <style>.lead-detail > div { padding: 6px 0; border-bottom: 1px solid var(--color-border-secondary); font-size: 13px; }</style>
      `;
      showModal('Detalhe do lead', html);
    } catch (e) {
      console.error(e);
      toast('Erro ao carregar lead', 'error');
    }
  }

  async function triggerOutbound(id) {
    toast('Gerando mensagens com Gemini...');
    try {
      const data = await api(`/outbound/generate/${id}`, { method: 'POST' });
      let html = '';
      const labels = {
        sms: 'SMS',
        email_subject: 'E-mail · Assunto',
        email_body: 'E-mail · Corpo',
        linkedin_connection: 'LinkedIn · Connection',
        linkedin_followup: 'LinkedIn · Follow-up',
      };
      for (const [k, label] of Object.entries(labels)) {
        if (data.messages[k]) {
          html += `<div class="message-block"><div class="message-block__head"><strong>${label}</strong></div><div class="message-block__body">${data.messages[k]}</div></div>`;
        }
      }
      showModal(`Outbound — ${data.empresa || ''}`, html);
    } catch (e) {
      console.error(e);
      toast(`Erro: ${e.message}`, 'error');
    }
  }

  // ====== MONITOR ======
  document.querySelectorAll('[data-monitor]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const v = btn.dataset.monitor;
      btn.disabled = true;
      btn.textContent = `Verificando ${verticalLabel(v)}...`;
      const result = document.getElementById('monitor-result');
      result.innerHTML = '<div class="empty">Coletando, parseando e comparando snapshots... pode levar até 1 minuto.</div>';
      try {
        const data = await api(`/monitor/${v}`, { method: 'POST' });
        let html = `<div class="monitor-block">
          <div class="monitor-block__title">📊 ${verticalLabel(v)}</div>
          Total atual: <strong>${data.total}</strong> · Snapshot anterior: <strong>${data.previous_total}</strong>
        </div>`;
        if (data.novas?.length) {
          html += `<div class="monitor-block monitor-block--success">
            <div class="monitor-block__title">🆕 ${data.novas.length} nova(s) empresa(s)</div>
            <ul>${data.novas.slice(0, 20).map((e) => `<li>${e.empresa || '?'} ${e.cnpj ? `· ${e.cnpj}` : ''}</li>`).join('')}</ul>
          </div>`;
        }
        if (data.sumiram?.length) {
          html += `<div class="monitor-block monitor-block--warning">
            <div class="monitor-block__title">⚠️ ${data.sumiram.length} sumiram</div>
            <ul>${data.sumiram.slice(0, 10).map((e) => `<li>${e.empresa || '?'}</li>`).join('')}</ul>
          </div>`;
        }
        if (data.mudancas_status?.length) {
          html += `<div class="monitor-block monitor-block--warning">
            <div class="monitor-block__title">🔄 ${data.mudancas_status.length} mudança(s) de status</div>
            <ul>${data.mudancas_status.map((m) => `<li>${m.empresa}: ${m.status_anterior} → ${m.status_atual}</li>`).join('')}</ul>
          </div>`;
        }
        if (!data.novas?.length && !data.sumiram?.length && !data.mudancas_status?.length) {
          html += `<div class="monitor-block">Nenhuma mudança desde o último snapshot.</div>`;
        }
        result.innerHTML = html;
        toast('Monitor concluído', 'success');
      } catch (e) {
        result.innerHTML = `<div class="monitor-block monitor-block--warning">Erro: ${e.message}</div>`;
        toast(`Erro: ${e.message}`, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = `Verificar ${verticalLabel(v)}`;
      }
    });
  });

  // ====== OUTBOUND PICKER ======
  async function loadOutboundOptions() {
    try {
      const data = await api('/db/leads?min_score=60&limit=100');
      const select = document.getElementById('outbound-lead-select');
      select.innerHTML = data.leads.map((l) => `<option value="${l.id}">[${l.score_icp}] ${l.empresa} · ${verticalLabel(l.vertical)}</option>`).join('');
      if (!data.leads.length) {
        select.innerHTML = '<option>Nenhum lead com score ≥ 60 ainda.</option>';
      }
    } catch (e) {
      console.error(e);
    }
  }
  document.getElementById('btn-gen-outbound').addEventListener('click', async () => {
    const id = document.getElementById('outbound-lead-select').value;
    if (!id || isNaN(parseInt(id))) return;
    const btn = document.getElementById('btn-gen-outbound');
    btn.disabled = true;
    btn.textContent = 'Gerando...';
    try {
      const data = await api(`/outbound/generate/${id}`, { method: 'POST' });
      const wrap = document.getElementById('outbound-messages');
      const labels = {
        sms: 'SMS',
        email_subject: 'E-mail · Assunto',
        email_body: 'E-mail · Corpo',
        linkedin_connection: 'LinkedIn · Connection',
        linkedin_followup: 'LinkedIn · Follow-up',
      };
      wrap.innerHTML = Object.entries(labels)
        .filter(([k]) => data.messages[k])
        .map(([k, label]) => `
          <div class="message-block">
            <div class="message-block__head"><strong>${label}</strong></div>
            <div class="message-block__body">${data.messages[k]}</div>
          </div>
        `).join('');
      toast('Mensagens geradas e salvas', 'success');
    } catch (e) {
      toast(`Erro: ${e.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<svg width="18" height="18"><use href="#i-zap"/></svg> Gerar mensagens`;
    }
  });

  // ====== EVENTS ======
  async function loadEvents() {
    try {
      const data = await api('/events?limit=50');
      const ul = document.getElementById('events-list');
      ul.innerHTML = (data.events || []).map((e) => {
        const payload = typeof e.payload_json === 'string' ? JSON.parse(e.payload_json) : e.payload_json;
        const summary = Object.entries(payload || {}).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).slice(0, 60) : v}`).join(' · ');
        return `
          <li class="event-row">
            <span class="event-row__type">${e.tipo}</span>
            <span class="muted">${summary || '—'}</span>
            <span class="event-row__time">${fmtDate(e.criado_em)}</span>
          </li>
        `;
      }).join('') || '<div class="empty">Sem eventos ainda.</div>';
    } catch (e) {
      console.error(e);
    }
  }

  // ====== SETTINGS ======
  function loadSettings() {
    document.getElementById('set-api-url').value = API_URL;
    document.getElementById('set-api-token').value = API_TOKEN;
    refreshScheduler();
  }
  document.getElementById('btn-save-settings').addEventListener('click', () => {
    API_URL = document.getElementById('set-api-url').value.trim();
    API_TOKEN = document.getElementById('set-api-token').value.trim();
    localStorage.setItem('apiUrl', API_URL);
    localStorage.setItem('apiToken', API_TOKEN);
    toast('Configurações salvas', 'success');
    checkHealth();
  });

  async function refreshScheduler() {
    try {
      const data = await api('/scheduler/status');
      const txt = data.ativo
        ? `Status: <strong style="color:var(--color-fg-success-primary)">Ativo</strong>`
        : `Status: <span class="muted">Parado</span>`;
      const last = Object.entries(data.last_monitor || {}).map(([k, v]) => `${k}: ${fmtDate(v)}`).join(' · ') || '—';
      document.getElementById('scheduler-status').innerHTML = `${txt}<br><span class="muted" style="font-size:12px;">Último monitor: ${last}</span>`;
    } catch (e) {
      document.getElementById('scheduler-status').textContent = 'Status: indisponível';
    }
  }
  document.getElementById('btn-scheduler-start').addEventListener('click', async () => {
    try { await api('/scheduler/start', { method: 'POST' }); toast('Scheduler iniciado', 'success'); refreshScheduler(); }
    catch (e) { toast(`Erro: ${e.message}`, 'error'); }
  });
  document.getElementById('btn-scheduler-stop').addEventListener('click', async () => {
    try { await api('/scheduler/stop', { method: 'POST' }); toast('Scheduler parado'); refreshScheduler(); }
    catch (e) { toast(`Erro: ${e.message}`, 'error'); }
  });
  document.getElementById('btn-rescore-now').addEventListener('click', async () => {
    try {
      toast('Re-scoring em andamento...');
      const data = await api('/rescore', { method: 'POST' });
      toast(`Re-score: ${data.atualizados} atualizados, ${data.promovidos.length} promovidos`, 'success');
      loadOverview();
    } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
  });

  // ====== TOP ACTIONS ======
  document.getElementById('btn-refresh').addEventListener('click', () => {
    const active = document.querySelector('.tab-panel.is-active').dataset.panel;
    onTabChange(active);
    checkHealth();
    toast('Atualizado');
  });
  document.getElementById('btn-scrape').addEventListener('click', async () => {
    const html = `
      <div class="settings-grid">
        <div class="setting-row">
          <label class="filter-label">Vertical</label>
          <select id="scr-vert" class="select">
            <option value="all">Todas</option>
            <option value="betting">Betting</option>
            <option value="pagamentos">Pagamentos</option>
            <option value="cobranca">Cobrança</option>
            <option value="saas_b2b">SaaS B2B</option>
          </select>
        </div>
        <div class="setting-row">
          <label class="filter-label">Limite (opcional)</label>
          <input type="number" id="scr-limit" class="input" placeholder="50" />
        </div>
        <div class="setting-row">
          <button class="btn btn--primary" id="scr-go">▶ Disparar</button>
        </div>
      </div>
    `;
    showModal('Disparar coleta', html);
    document.getElementById('scr-go').addEventListener('click', async () => {
      const vertical = document.getElementById('scr-vert').value;
      const limit = parseInt(document.getElementById('scr-limit').value, 10);
      try {
        const data = await api('/scrape', {
          method: 'POST',
          body: JSON.stringify({ vertical, limit: isNaN(limit) ? null : limit, enrich_email: false }),
        });
        toast(`Job ${data.job_id.slice(0, 8)} disparado`, 'success');
        closeModal();
      } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
    });
  });

  // ====== FILTERS WIRING ======
  document.getElementById('f-vertical').addEventListener('change', loadLeads);
  document.getElementById('f-score').addEventListener('change', loadLeads);
  document.getElementById('f-search').addEventListener('input', () => {
    clearTimeout(window.__searchT);
    window.__searchT = setTimeout(loadLeads, 250);
  });
  document.getElementById('btn-export').addEventListener('click', async () => {
    try {
      const vertical = document.getElementById('f-vertical').value;
      const r = await fetch(`${API_URL}/db/export.csv?vertical=${vertical}`, { headers: { 'X-API-Token': API_TOKEN } });
      const blob = await r.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `leads_${vertical}_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      toast('CSV gerado', 'success');
    } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
  });

  // ====== SDR ======
  function sdrEmail() {
    return (document.getElementById('sdr-email')?.value || localStorage.getItem('sdrEmail') || '').trim();
  }

  document.getElementById('sdr-email').addEventListener('change', (e) => {
    localStorage.setItem('sdrEmail', e.target.value.trim());
    loadSDR();
  });

  document.getElementById('btn-auto-assign').addEventListener('click', async () => {
    const email = sdrEmail();
    if (!email) return toast('Informe seu e-mail', 'error');
    try {
      const data = await api(`/sdr/auto-assign?sdr_email=${encodeURIComponent(email)}&min_score=60&max_n=10`, { method: 'POST' });
      toast(`${data.leads_atribuidos} leads atribuídos`, 'success');
      loadSDR();
    } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
  });

  async function loadSDR() {
    const email = sdrEmail();
    document.getElementById('sdr-email').value = email;
    if (!email) {
      document.getElementById('sdr-queue').innerHTML = '<div class="empty">Informe seu e-mail acima e clique em auto-atribuir.</div>';
      document.getElementById('sdr-metrics').innerHTML = '';
      return;
    }
    try {
      const [m, q] = await Promise.all([
        api(`/sdr/metrics?sdr_email=${encodeURIComponent(email)}`),
        api(`/sdr/queue?sdr_email=${encodeURIComponent(email)}`),
      ]);

      // Métricas
      const acts = m.atividades_hoje || {};
      const status = m.por_status || {};
      document.getElementById('sdr-metrics').innerHTML = `
        <div class="sdr-metric"><span class="sdr-metric__label">Atribuídos</span><span class="sdr-metric__value">${m.total_atribuidos || 0}</span></div>
        <div class="sdr-metric"><span class="sdr-metric__label">A contatar</span><span class="sdr-metric__value">${status.a_contatar || 0}</span></div>
        <div class="sdr-metric"><span class="sdr-metric__label">Contatados</span><span class="sdr-metric__value">${status.contatado || 0}</span></div>
        <div class="sdr-metric"><span class="sdr-metric__label">Responderam</span><span class="sdr-metric__value">${status.respondeu || 0}</span></div>
        <div class="sdr-metric"><span class="sdr-metric__label">Qualificados</span><span class="sdr-metric__value">${status.qualificado || 0}</span></div>
        <div class="sdr-metric"><span class="sdr-metric__label">Toques hoje</span><span class="sdr-metric__value">${acts.toque_enviado || 0}</span></div>
      `;

      // Fila
      const wrap = document.getElementById('sdr-queue');
      if (!q.queue.length) {
        wrap.innerHTML = '<div class="empty">Nenhum lead atribuído. Use auto-atribuir.</div>';
        return;
      }
      wrap.innerHTML = q.queue.map((l) => renderSDRCard(l)).join('');
      // Carrega playbooks de cada lead
      q.queue.forEach((l) => loadPlaybooksForLead(l.id));
      // Bind ações
      bindSDRActions();
    } catch (e) {
      console.error(e);
      toast(`Erro SDR: ${e.message}`, 'error');
    }
  }

  function renderSDRCard(lead) {
    const status = lead.sdr_status || 'a_contatar';
    return `
      <div class="sdr-card" data-lead-id="${lead.id}">
        <div class="sdr-card__head">
          <div>
            <div class="sdr-card__title">${lead.empresa}</div>
            <div class="sdr-card__sub">
              <span class="badge badge--brand">${verticalLabel(lead.vertical)}</span>
              <span class="${scoreClass(lead.score_icp)}">${lead.score_icp ?? '—'}</span>
              <span class="sdr-status sdr-status--${status}">${status.replace(/_/g, ' ')}</span>
              ${lead.email_provavel ? `<span class="muted">${lead.email_provavel}</span>` : ''}
              ${lead.decisor_nome ? `<span class="muted">· ${lead.decisor_nome}</span>` : ''}
            </div>
          </div>
        </div>
        <div class="sdr-card__playbooks" id="pb-for-${lead.id}">
          <div class="muted" style="font-size:12px;">Carregando playbooks...</div>
        </div>
        <div class="sdr-card__actions">
          <button class="chip-btn act-touch" data-lead-id="${lead.id}" data-tipo="toque_enviado">📤 Toque enviado</button>
          <button class="chip-btn act-touch" data-lead-id="${lead.id}" data-tipo="resposta_recebida">📬 Respondeu</button>
          <button class="chip-btn act-touch" data-lead-id="${lead.id}" data-tipo="reuniao_agendada">📅 Reunião</button>
          <button class="chip-btn act-touch" data-lead-id="${lead.id}" data-tipo="qualificado">✅ Qualificado</button>
          <button class="chip-btn act-touch" data-lead-id="${lead.id}" data-tipo="descartado">❌ Descartar</button>
          <button class="chip-btn act-regen" data-lead-id="${lead.id}">🔁 Re-gerar playbooks</button>
        </div>
      </div>
    `;
  }

  async function loadPlaybooksForLead(leadId) {
    try {
      const data = await api(`/leads/${leadId}/playbooks`);
      const wrap = document.getElementById(`pb-for-${leadId}`);
      if (!wrap) return;
      if (!data.playbooks || !data.playbooks.length) {
        wrap.innerHTML = '<div class="muted" style="font-size:12px;">Sem playbooks. Clique em re-gerar.</div>';
        return;
      }
      wrap.innerHTML = data.playbooks.map((pb) => `
        <div class="playbook-pill">
          <div class="playbook-pill__ordem">${pb.ordem || '·'}</div>
          <div class="playbook-pill__main">
            <div class="playbook-pill__name">${pb.playbook_nome || pb.nome}</div>
            <div style="font-size: 12px; color: var(--color-text-primary);">${pb.justificativa || pb.gatilho || ''}</div>
            <div class="playbook-pill__meta">🎯 ${pb.sinal_detectado || pb.dor_alvo || ''}</div>
          </div>
        </div>
      `).join('');
    } catch (e) {
      console.error('Falha ao carregar playbooks', leadId, e);
    }
  }

  function bindSDRActions() {
    document.querySelectorAll('.act-touch').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const email = sdrEmail();
        if (!email) return toast('Informe seu e-mail', 'error');
        const lead_id = parseInt(btn.dataset.leadId, 10);
        const tipo = btn.dataset.tipo;
        try {
          await api('/sdr/activity', {
            method: 'POST',
            body: JSON.stringify({ lead_id, sdr_email: email, tipo }),
          });
          toast(`Registrado: ${tipo.replace(/_/g, ' ')}`, 'success');
          loadSDR();
        } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
      });
    });
    document.querySelectorAll('.act-regen').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const lead_id = parseInt(btn.dataset.leadId, 10);
        toast('Re-gerando playbooks...');
        try {
          await api(`/leads/${lead_id}/playbooks/regenerate`, { method: 'POST' });
          toast('Playbooks atualizados', 'success');
          loadPlaybooksForLead(lead_id);
        } catch (e) { toast(`Erro: ${e.message}`, 'error'); }
      });
    });
  }

  // ====== PLAYBOOKS (biblioteca) ======
  async function loadPlaybooks() {
    try {
      const data = await api('/playbooks');
      const grid = document.getElementById('playbooks-grid');
      grid.innerHTML = (data.playbooks || []).map((p) => `
        <div class="playbook-card">
          <span class="playbook-card__categoria">${p.categoria}</span>
          <div class="playbook-card__nome">${p.nome}</div>
          <div class="playbook-card__gatilho">🎯 <strong>Gatilho:</strong> ${p.gatilho}</div>
          <div class="playbook-card__dor"><strong>Dor:</strong> ${p.dor_alvo}</div>
          <div class="playbook-card__dor"><strong>Decisor:</strong> ${p.decisor_primario}${p.decisor_secundario ? ` / ${p.decisor_secundario}` : ''}</div>
          <div class="playbook-card__msg">${p.mensagem_central}</div>
          <details style="margin-top:10px;">
            <summary style="cursor:pointer; font-size:12px; color: var(--color-text-secondary);">Ver sequência (${p.sequencia?.length || 0} toques)</summary>
            <div style="margin-top:8px; display:flex; flex-direction:column; gap:6px;">
              ${(p.sequencia || []).map((s) => `
                <div style="border-left: 2px solid var(--color-border-brand); padding: 6px 10px; font-size: 12px;">
                  <strong>${s.toque}. ${s.canal.toUpperCase()}</strong> (${s.timing})<br>
                  <span style="color: var(--color-text-secondary);">${s.template_subject ? `Subject: ${s.template_subject}<br>` : ''}${s.template || s.template_body || ''}</span>
                </div>
              `).join('')}
            </div>
          </details>
        </div>
      `).join('');

      const obj = document.getElementById('objecoes-list');
      obj.innerHTML = (data.objecoes || []).map((o) => `
        <div class="objecao-card">
          <div class="objecao-card__titulo">"${o.titulo}"</div>
          <div class="objecao-card__resposta">${o.resposta}</div>
        </div>
      `).join('');
    } catch (e) {
      console.error(e);
      toast(`Erro: ${e.message}`, 'error');
    }
  }

  // ====== MODAL CLOSE ======
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.querySelector('.modal__backdrop').addEventListener('click', closeModal);

  // ====== INIT ======
  document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadOverview();
    setInterval(checkHealth, 10000);
  });
})();
