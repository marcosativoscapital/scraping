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
    if (tab === 'oportunidades') loadOportunidades();
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

  // ====== PLAYBOOKS (biblioteca visual) ======
  let _allPlaybooks = [];
  let _currentCategoria = 'all';
  const _tplStore = new Map();  // armazena templates por id (evita escaping no HTML)

  const CANAL_ICONS = {
    linkedin: '💼 LinkedIn',
    email: '✉️ E-mail',
    sms: '📱 SMS',
    whatsapp: '🟢 WhatsApp',
    voz: '📞 Voz',
  };

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderPlaybook(p) {
    const seq = p.sequencia || [];
    const sinais = (p.sinais_para_aplicar || []).slice(0, 3)
      .map((s) => `<span class="badge" style="margin-right:4px;">${escapeHtml(s)}</span>`).join('');
    return `
      <article class="pb" data-categoria="${escapeHtml(p.categoria)}" data-id="${escapeHtml(p.id)}">
        <header class="pb__head">
          <span class="pb__cat">${escapeHtml(p.categoria.replace(/_/g, ' '))}</span>
          <h3 class="pb__nome">${escapeHtml(p.nome)}</h3>
          <p class="pb__gatilho">🎯 ${escapeHtml(p.gatilho)}</p>
        </header>
        <div class="pb__body">
          <div class="pb__row">
            <span class="pb__row-icon">🔥</span>
            <div class="pb__row-content">
              <span class="pb__row-label">Dor-alvo</span>
              <div class="pb__row-value">${escapeHtml(p.dor_alvo)}</div>
            </div>
          </div>
          <div class="pb__row">
            <span class="pb__row-icon">👤</span>
            <div class="pb__row-content">
              <span class="pb__row-label">Decisor</span>
              <div class="pb__row-value">${escapeHtml(p.decisor_primario || '')}${p.decisor_secundario ? ` &middot; <span class="muted">${escapeHtml(p.decisor_secundario)}</span>` : ''}</div>
            </div>
          </div>
          <div class="pb__row">
            <span class="pb__row-icon">📡</span>
            <div class="pb__row-content">
              <span class="pb__row-label">Sinais para aplicar</span>
              <div class="pb__row-value">${sinais}</div>
            </div>
          </div>
          <div class="pb__mensagem">${escapeHtml(p.mensagem_central)}</div>

          <div class="pb__trail-head" data-toggle-pb="${escapeHtml(p.id)}">
            <h4>🧭 Trilha de outbound</h4>
            <span class="pb__trail-head__count">${seq.length} ${seq.length === 1 ? 'toque' : 'toques'} <span class="pb__trail-toggle">⌄</span></span>
          </div>
          <div class="pb__trail">
            ${seq.map((s, i) => renderTouch(p.id, s, i)).join('')}
          </div>
        </div>
      </article>
    `;
  }

  function renderTouch(pbId, t, idx) {
    const canal = CANAL_ICONS[t.canal] || (t.canal || '').toUpperCase();
    const tplKey = `${pbId}__${idx}`;
    const tplFull = (t.template_subject ? `Assunto: ${t.template_subject}\n\n` : '') + (t.template || t.template_body || '');
    _tplStore.set(tplKey, tplFull);
    return `
      <div class="pb__touch">
        <div class="pb__touch-num">${escapeHtml(String(t.toque || idx + 1))}</div>
        <div class="pb__touch-body">
          <div class="pb__touch-meta">
            <span class="pb__touch-canal">${escapeHtml(canal)}</span>
            <span class="pb__touch-timing">⏰ ${escapeHtml(t.timing || '')}</span>
          </div>
          ${t.template_subject ? `<div class="pb__touch-subject">📧 ${escapeHtml(t.template_subject)}</div>` : ''}
          <div class="pb__touch-body-text">${escapeHtml(t.template || t.template_body || '')}</div>
          <div class="pb__touch-actions">
            <button class="pb__copy-btn" data-tpl-key="${escapeHtml(tplKey)}">📋 Copiar template</button>
          </div>
        </div>
      </div>
    `;
  }

  function bindPlaybookEvents() {
    // Toggle trilha
    document.querySelectorAll('[data-toggle-pb]').forEach((el) => {
      el.addEventListener('click', () => {
        el.closest('.pb').classList.toggle('is-open');
      });
    });
    // Copiar templates
    document.querySelectorAll('.pb__copy-btn').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const key = btn.dataset.tplKey;
        const text = key ? _tplStore.get(key) : (btn.dataset.tpl || '');
        const orig = btn.textContent;
        try {
          await navigator.clipboard.writeText(text || '');
          btn.classList.add('is-copied');
          btn.textContent = '✓ Copiado!';
          setTimeout(() => { btn.classList.remove('is-copied'); btn.textContent = orig; }, 1800);
        } catch (e2) {
          console.error('clipboard error:', e2);
          toast('Não consegui copiar — selecione manual.', 'error');
        }
      });
    });
    // Filtros
    document.querySelectorAll('.pb-filter').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pb-filter').forEach((b) => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        _currentCategoria = btn.dataset.cat;
        renderPlaybookGrid();
      });
    });
  }

  function renderPlaybookGrid() {
    const grid = document.getElementById('playbooks-grid');
    if (!grid) return;
    let filtered = _allPlaybooks;
    if (_currentCategoria !== 'all') {
      filtered = _allPlaybooks.filter((p) => p.categoria === _currentCategoria || (p.categoria || '').includes(_currentCategoria));
    }
    grid.innerHTML = filtered.length
      ? filtered.map(renderPlaybook).join('')
      : '<div class="empty" style="grid-column: 1/-1;">Nenhum playbook nessa categoria.</div>';
    bindPlaybookEvents();
  }

  async function loadPlaybooks() {
    const grid = document.getElementById('playbooks-grid');
    if (grid) grid.innerHTML = '<div class="empty" style="grid-column: 1/-1;">Carregando playbooks...</div>';
    try {
      const data = await api('/playbooks');
      _allPlaybooks = data.playbooks || [];
      renderPlaybookGrid();

      const obj = document.getElementById('objecoes-list');
      if (obj) {
        obj.innerHTML = (data.objecoes || []).map((o, i) => {
          const k = `obj__${i}`;
          _tplStore.set(k, o.resposta);
          return `
            <div class="objecao-card">
              <div class="objecao-card__titulo">"${escapeHtml(o.titulo)}"</div>
              <div class="objecao-card__resposta">${escapeHtml(o.resposta)}</div>
              <button class="pb__copy-btn" data-tpl-key="${k}" style="margin-top:8px;">📋 Copiar resposta</button>
            </div>
          `;
        }).join('');
      }
      bindPlaybookEvents();
    } catch (e) {
      console.error('Falha ao carregar playbooks:', e);
      if (grid) grid.innerHTML = `<div class="empty" style="grid-column: 1/-1; color: var(--color-fg-error-primary);">Erro ao carregar: ${e.message}. Verifique o token na aba Configurações.</div>`;
      toast(`Erro playbooks: ${e.message}`, 'error');
    }
  }

  // ====== OPORTUNIDADES (vendas) ======
  const TIPO_LABEL = {
    ligacao: 'Ligação', videochamada: 'Videochamada', email: 'E-mail',
    visita: 'Visita', almoco: 'Almoço', personalizado: 'Personalizado',
  };
  const TEMP_LABEL = {
    muito_quente: 'Muito quente', quente: 'Quente', frio: 'Frio', muito_frio: 'Muito frio',
  };
  const PIPE_LABEL = {
    potencial_cliente: 'Potencial cliente', leads: 'Leads',
    oportunidades: 'Oportunidades', pos_venda: 'Pós-venda',
  };
  const STATUS_LABEL = {
    a_fazer: 'A fazer', executada: 'Executada', atrasada: 'Atrasada',
    reagendada: 'Reagendada', cancelada: 'Cancelada',
  };
  const PIPE_ORDER = ['potencial_cliente', 'leads', 'oportunidades', 'pos_venda'];
  const TIPO_ICON = { ligacao: 'i-phone', videochamada: 'i-video', email: 'i-mail', visita: 'i-flag', almoco: 'i-flag', personalizado: 'i-target' };
  function tipoIcon(t) { return TIPO_ICON[t] || 'i-flag'; }

  // Tooltip flutuante dos ticks da timeline (uma instância reutilizável no body)
  let _tlTipEl = null;
  function tlTip() {
    if (!_tlTipEl) {
      _tlTipEl = document.createElement('div');
      _tlTipEl.className = 'tl-tip';
      _tlTipEl.hidden = true;
      document.body.appendChild(_tlTipEl);
    }
    return _tlTipEl;
  }
  function hideTlTip() { if (_tlTipEl) _tlTipEl.hidden = true; }
  function showTlTip(el) {
    const tip = tlTip();
    tip.innerHTML = `
      <div class="tl-tip__time">${escapeHtml(el.dataset.hora || '')}</div>
      <div class="tl-tip__row"><span class="temp-dot temp-dot--${el.dataset.temp || 'none'}"></span><span class="tl-tip__client">${escapeHtml(el.dataset.emp || '')}</span></div>
      <div class="tl-tip__row"><svg class="tl-tip__ico" width="16" height="16"><use href="#${el.dataset.ico || 'i-flag'}"/></svg><span class="tl-tip__act">${escapeHtml(el.dataset.titulo || '')}</span></div>`;
    tip.hidden = false;
    const r = el.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = r.left + r.width / 2 - tw / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
    let top = r.top - th - 8;
    if (top < 8) top = r.bottom + 8;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  let _oppView = 'lista';
  let _oppBound = false;
  let _oppLeads = [];
  let _calRef = new Date();
  let _calEscala = 'mes';
  let _tlRef = new Date();
  let _tlEscala = 'mes';
  const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const MESES_ABBR = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const DOW = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
  function isoDate(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }
  function sameDay(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
  function fmtTimeOnly(iso) { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }); }
  function statusLabel(s) { return { em_andamento: 'Em andamento', ganho: 'Ganho', congelado: 'Congelado', perdido: 'Perdido' }[s] || s; }

  function tipoLabel(t) { return TIPO_LABEL[t] || '—'; }
  function tempPill(t) { return t ? `<span class="temp-pill temp-pill--${t}">${TEMP_LABEL[t] || t}</span>` : '—'; }
  function pipeBadge(p) { return p ? `<span class="pipe-badge pipe-badge--${p}">${PIPE_LABEL[p] || p}</span>` : '—'; }
  function parseTags(tags) {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags;
    try { const a = JSON.parse(tags); return Array.isArray(a) ? a : []; }
    catch { return String(tags).split(',').map((s) => s.trim()).filter(Boolean); }
  }
  function renderTags(tags) {
    const a = parseTags(tags);
    return a.length ? a.map((t) => `<span class="atv-tag">${escapeHtml(t)}</span>`).join(' ') : '—';
  }
  function emptyState(title, sub) {
    return `<div class="opp-empty"><strong>${escapeHtml(title)}</strong>${escapeHtml(sub || '')}</div>`;
  }
  function pipeOptions(sel) {
    return Object.entries(PIPE_LABEL).map(([k, v]) => `<option value="${k}" ${k === sel ? 'selected' : ''}>${v}</option>`).join('');
  }
  function statusOptions(sel) {
    return Object.entries(STATUS_LABEL).map(([k, v]) => `<option value="${k}" ${k === sel ? 'selected' : ''}>${v}</option>`).join('');
  }

  function oppQuery() {
    const qs = new URLSearchParams();
    const periodo = document.getElementById('opp-f-periodo').value;
    const tipo = document.getElementById('opp-f-tipo').value;
    const temp = document.getElementById('opp-f-temp').value;
    const pipe = document.getElementById('opp-f-pipeline').value;
    if (periodo && periodo !== 'todos') qs.set('periodo', periodo);
    if (tipo) qs.set('tipo', tipo);
    if (temp) qs.set('temperatura', temp);
    if (pipe) qs.set('pipeline', pipe);
    return qs.toString();
  }

  async function renderOppView() {
    const root = document.getElementById('opp-view-root');
    if (!root) return;
    const periodoSel = document.getElementById('opp-f-periodo');
    if (periodoSel) periodoSel.disabled = (_oppView === 'calendario' || _oppView === 'timeline');
    if (_oppView === 'calendario') { renderCalendario(); return; }
    if (_oppView === 'timeline') { renderTimeline(); return; }
    root.innerHTML = emptyState('Carregando…', '');
    const view = _oppView;
    try {
      const q = oppQuery();
      const data = await api('/atividades' + (q ? '?' + q : ''));
      if (_oppView !== view) return; // view trocou durante o fetch
      const items = data.atividades || [];
      if (view === 'lista') renderLista(items);
      else renderQuadro(items);
    } catch (e) {
      if (_oppView !== view) return;
      root.innerHTML = emptyState('Erro ao carregar', e.message);
      toast('Erro: ' + e.message, 'error');
    }
  }

  function renderLista(items) {
    const root = document.getElementById('opp-view-root');
    if (!items.length) { root.innerHTML = emptyState('Nenhuma atividade', 'Crie a primeira com “Nova atividade”.'); return; }
    const rows = items.map((a) => `
      <tr data-atv="${a.id}" tabindex="0">
        <td>${fmtDate(a.inicio_em)}</td>
        <td>${tipoLabel(a.tipo)}</td>
        <td class="cliente">${escapeHtml(a.cliente_empresa || '—')}</td>
        <td>${escapeHtml(a.titulo || '—')}</td>
        <td>${tempPill(a.temperatura)}</td>
        <td>${escapeHtml(a.responsavel || '—')}</td>
        <td>${pipeBadge(a.pipeline)}</td>
        <td>${renderTags(a.tags)}</td>
      </tr>`).join('');
    root.innerHTML = `
      <div class="opp-table-wrap">
        <table class="data-table">
          <thead><tr>
            <th>Horário</th><th>Tipo</th><th>Cliente alvo</th><th>Nome</th>
            <th>Temperatura</th><th>Responsável</th><th>Pipeline</th><th>Tags</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="opp-foot">${items.length} atividade(s)</div>`;
    root.querySelectorAll('[data-atv]').forEach((tr) => {
      tr.addEventListener('click', () => showAtividade(tr.dataset.atv));
      tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') showAtividade(tr.dataset.atv); });
    });
  }

  function atvCard(a) {
    return `<button class="atv-card" data-atv="${a.id}" data-pipe="${a.pipeline || ''}" draggable="true" type="button">
      <div class="atv-card__top">
        <span class="atv-card__date">${fmtDate(a.inicio_em)}</span>
        ${tempPill(a.temperatura)}
      </div>
      <div class="atv-card__title">${escapeHtml(a.titulo || 'Sem título')}</div>
      <span class="type-chip">${tipoLabel(a.tipo)}</span>
      <div class="atv-card__meta">
        <div><svg width="14" height="14"><use href="#i-building"/></svg>${escapeHtml(a.cliente_empresa || '—')}</div>
        <div><svg width="14" height="14"><use href="#i-user"/></svg>${escapeHtml(a.contato_nome || a.cliente_decisor || '—')}</div>
        <div><svg width="14" height="14"><use href="#i-clock"/></svg>${a.duracao_min ? a.duracao_min + ' min' : '—'}</div>
      </div>
    </button>`;
  }

  function renderQuadro(items) {
    const root = document.getElementById('opp-view-root');
    const byPipe = {};
    PIPE_ORDER.forEach((k) => { byPipe[k] = []; });
    items.forEach((a) => { (byPipe[a.pipeline] || (byPipe[a.pipeline] = [])).push(a); });
    root.innerHTML = '<div class="opp-kanban">' + PIPE_ORDER.map((k) => {
      const cards = byPipe[k] || [];
      return `<div class="opp-col" data-pipe="${k}">
        <div class="opp-col__head"><span class="opp-col__title">${PIPE_LABEL[k]}</span><span class="opp-col__count">${cards.length}</span></div>
        ${cards.length ? cards.map(atvCard).join('') : '<div class="opp-col__empty">Vazio</div>'}
      </div>`;
    }).join('') + '</div>';
    root.querySelectorAll('.atv-card').forEach((card) => {
      card.addEventListener('click', () => showAtividade(card.dataset.atv));
      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', card.dataset.atv);
        e.dataTransfer.effectAllowed = 'move';
        card.classList.add('atv-card--dragging');
      });
      card.addEventListener('dragend', () => card.classList.remove('atv-card--dragging'));
    });
    root.querySelectorAll('.opp-col').forEach((col) => {
      col.addEventListener('dragover', (e) => { e.preventDefault(); col.classList.add('opp-col--dragover'); });
      col.addEventListener('dragleave', () => col.classList.remove('opp-col--dragover'));
      col.addEventListener('drop', async (e) => {
        e.preventDefault();
        col.classList.remove('opp-col--dragover');
        const id = e.dataTransfer.getData('text/plain');
        const pipe = col.dataset.pipe;
        const card = root.querySelector(`.atv-card[data-atv="${id}"]`);
        if (!id || !pipe || (card && card.dataset.pipe === pipe)) return;
        try {
          await api('/atividades/' + id, { method: 'PATCH', body: JSON.stringify({ pipeline: pipe }) });
          toast('Movido para ' + PIPE_LABEL[pipe], 'success');
          renderOppView();
        } catch (err) { toast('Erro ao mover: ' + err.message, 'error'); }
      });
    });
  }

  async function ensureLeads() {
    if (_oppLeads.length) return _oppLeads;
    try { const d = await api('/db/leads?limit=300'); _oppLeads = d.leads || []; }
    catch { _oppLeads = []; }
    return _oppLeads;
  }

  async function openNovaAtividade() {
    await ensureLeads();
    const leadOpts = ['<option value="">Defina um cliente</option>']
      .concat(_oppLeads.map((l) => `<option value="${l.id}">${escapeHtml(l.empresa || ('Lead #' + l.id))}</option>`)).join('');
    const tipoChips = Object.entries(TIPO_LABEL)
      .map(([k, v]) => `<button type="button" class="atv-chip" data-tipo="${k}">${v}</button>`).join('');
    const html = `
      <form class="atv-form" id="atv-form">
        <div class="atv-form__natureza">
          <button type="button" class="atv-nat is-active" data-nat="evento">Evento</button>
          <button type="button" class="atv-nat" data-nat="tarefa">Tarefa</button>
          <button type="button" class="atv-nat" data-nat="lembrete">Lembrete</button>
        </div>
        <div class="atv-chips" id="atv-tipos">${tipoChips}</div>
        <div class="atv-field atv-field--full">
          <label for="atv-titulo">Nome</label>
          <input class="input" id="atv-titulo" placeholder="Defina um nome" required />
        </div>
        <div class="atv-grid">
          <div class="atv-field"><label for="atv-inicio">Dia e horário</label><input class="input" type="datetime-local" id="atv-inicio" /></div>
          <div class="atv-field"><label for="atv-duracao">Duração (min)</label><input class="input" type="number" min="0" step="5" id="atv-duracao" placeholder="30" /></div>
          <div class="atv-field"><label for="atv-repeticao">Repetição</label>
            <select class="input" id="atv-repeticao">
              <option value="nenhuma">Nenhuma</option><option value="diaria">Diária</option>
              <option value="semanal">Semanal</option><option value="mensal">Mensal</option>
            </select></div>
          <div class="atv-field" style="justify-content:flex-end">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="checkbox" id="atv-diainteiro" /> Dia inteiro</label>
          </div>
          <div class="atv-field"><label for="atv-cliente">Cliente</label><select class="input" id="atv-cliente">${leadOpts}</select></div>
          <div class="atv-field"><label for="atv-contato">Contato do cliente</label><input class="input" id="atv-contato" placeholder="Nome do contato" /></div>
          <div class="atv-field"><label for="atv-temp">Temperatura</label>
            <select class="input" id="atv-temp">
              <option value="">—</option><option value="muito_quente">Muito quente</option>
              <option value="quente">Quente</option><option value="frio">Frio</option><option value="muito_frio">Muito frio</option>
            </select></div>
          <div class="atv-field"><label for="atv-pipeline">Pipeline</label>
            <select class="input" id="atv-pipeline">${pipeOptions('potencial_cliente')}</select></div>
        </div>
        <div class="atv-field atv-field--full"><label for="atv-desc">Descrição</label><textarea class="input" id="atv-desc" placeholder="Sobre o que você vai tratar?"></textarea></div>
        <div class="atv-field atv-field--full"><label for="atv-tags">Tags</label><input class="input" id="atv-tags" placeholder="ex.: oportunidade, setor do cliente" /></div>
        <div class="atv-form__foot">
          <button type="button" class="btn btn--secondary" id="atv-cancel">Cancelar</button>
          <button type="submit" class="btn btn--primary">Salvar</button>
        </div>
      </form>`;
    showModal('Nova atividade', html);

    let natureza = 'evento';
    let tipo = null;
    document.querySelectorAll('.atv-nat').forEach((b) => b.addEventListener('click', () => {
      natureza = b.dataset.nat;
      document.querySelectorAll('.atv-nat').forEach((x) => x.classList.toggle('is-active', x === b));
    }));
    document.getElementById('atv-tipos').addEventListener('click', (e) => {
      const c = e.target.closest('.atv-chip');
      if (!c) return;
      tipo = c.dataset.tipo;
      document.querySelectorAll('.atv-chip').forEach((x) => x.classList.toggle('is-active', x === c));
    });
    document.getElementById('atv-cancel').addEventListener('click', closeModal);
    document.getElementById('atv-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const titulo = document.getElementById('atv-titulo').value.trim();
      if (!titulo) { toast('Informe um nome', 'error'); return; }
      const payload = {
        titulo, natureza, tipo,
        inicio_em: document.getElementById('atv-inicio').value || null,
        duracao_min: parseInt(document.getElementById('atv-duracao').value || '', 10) || null,
        dia_inteiro: document.getElementById('atv-diainteiro').checked,
        repeticao: document.getElementById('atv-repeticao').value,
        lead_id: parseInt(document.getElementById('atv-cliente').value || '', 10) || null,
        contato_nome: document.getElementById('atv-contato').value.trim() || null,
        temperatura: document.getElementById('atv-temp').value || null,
        pipeline: document.getElementById('atv-pipeline').value,
        descricao: document.getElementById('atv-desc').value.trim() || null,
        tags: (document.getElementById('atv-tags').value || '').split(',').map((s) => s.trim()).filter(Boolean),
      };
      const btn = e.submitter;
      if (btn) { btn.disabled = true; btn.textContent = 'Salvando…'; }
      try {
        await api('/atividades', { method: 'POST', body: JSON.stringify(payload) });
        closeModal();
        toast('Atividade criada', 'success');
        renderOppView();
      } catch (err) {
        toast('Erro ao salvar: ' + err.message, 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Salvar'; }
      }
    });
  }

  async function showAtividade(id) {
    try {
      const data = await api('/atividades/' + id);
      const a = data.atividade;
      const tags = parseTags(a.tags);
      const html = `
        <div class="atv-detail">
          <span class="type-chip">${tipoLabel(a.tipo)}</span>
          <div class="atv-detail__row">
            <div><svg width="16" height="16"><use href="#i-clock"/></svg>${fmtDate(a.inicio_em)}${a.duracao_min ? ' · ' + a.duracao_min + ' min' : ''}</div>
          </div>
          <div class="atv-detail__row">
            <div><svg width="16" height="16"><use href="#i-building"/></svg>${escapeHtml(a.cliente_empresa || '—')}</div>
            <div><svg width="16" height="16"><use href="#i-user"/></svg>${escapeHtml(a.contato_nome || a.cliente_decisor || '—')}</div>
          </div>
          <div class="atv-detail__row">${tempPill(a.temperatura)} ${pipeBadge(a.pipeline)}</div>
          ${a.descricao ? `<div><div class="atv-detail__label">Descrição</div><div class="atv-detail__desc">${escapeHtml(a.descricao)}</div></div>` : ''}
          ${tags.length ? `<div><div class="atv-detail__label">Tags</div><div class="atv-detail__tags">${tags.map((t) => `<span class="atv-tag">${escapeHtml(t)}</span>`).join('')}</div></div>` : ''}
          <div class="atv-grid">
            <div class="atv-field"><label for="atv-d-pipeline">Pipeline</label><select class="input" id="atv-d-pipeline">${pipeOptions(a.pipeline)}</select></div>
            <div class="atv-field"><label for="atv-d-status">Status</label><select class="input" id="atv-d-status">${statusOptions(a.status)}</select></div>
          </div>
          <div class="atv-form__foot"><button class="btn btn--primary" id="atv-d-save">Salvar alterações</button></div>
        </div>`;
      showModal(a.titulo || 'Atividade', html);
      document.getElementById('atv-d-save').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        try {
          await api('/atividades/' + id, {
            method: 'PATCH',
            body: JSON.stringify({
              pipeline: document.getElementById('atv-d-pipeline').value,
              status: document.getElementById('atv-d-status').value,
            }),
          });
          closeModal();
          toast('Atividade atualizada', 'success');
          renderOppView();
        } catch (err) { toast('Erro: ' + err.message, 'error'); btn.disabled = false; }
      });
    } catch (e) { toast('Erro: ' + e.message, 'error'); }
  }

  // ---- Calendário ----
  function calFilterQuery() {
    const qs = new URLSearchParams();
    const tipo = document.getElementById('opp-f-tipo').value;
    const temp = document.getElementById('opp-f-temp').value;
    const pipe = document.getElementById('opp-f-pipeline').value;
    if (tipo) qs.set('tipo', tipo);
    if (temp) qs.set('temperatura', temp);
    if (pipe) qs.set('pipeline', pipe);
    return qs;
  }
  function shiftCal(dir) {
    if (_calEscala === 'semana') _calRef.setDate(_calRef.getDate() + 7 * dir);
    else _calRef.setMonth(_calRef.getMonth() + dir);
    _calRef = new Date(_calRef);
  }
  function bindCalControls() {
    const prev = document.getElementById('cal-prev');
    const next = document.getElementById('cal-next');
    const today = document.getElementById('cal-today');
    const seg = document.getElementById('cal-seg');
    if (prev) prev.onclick = () => { shiftCal(-1); renderCalendario(); };
    if (next) next.onclick = () => { shiftCal(1); renderCalendario(); };
    if (today) today.onclick = () => { _calRef = new Date(); renderCalendario(); };
    if (seg) seg.onclick = (e) => { const b = e.target.closest('.opp-seg__btn'); if (!b) return; _calEscala = b.dataset.esc; renderCalendario(); };
  }
  function calEv(a) {
    return `<button class="cal-ev" data-atv="${a.id}" type="button" title="${escapeHtml(a.titulo || '')}">
      <span class="temp-dot temp-dot--${a.temperatura || 'none'}"></span>
      <span class="cal-ev__t">${a.inicio_em ? fmtTimeOnly(a.inicio_em) : ''}</span>
      <span class="cal-ev__c">${escapeHtml(a.cliente_empresa || a.titulo || '—')}</span>
    </button>`;
  }
  function calMonth(byDay) {
    const ref = _calRef;
    const first = new Date(ref.getFullYear(), ref.getMonth(), 1);
    const start = new Date(first);
    start.setDate(1 - first.getDay());
    const today = new Date();
    let cells = '';
    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const list = byDay[isoDate(d)] || [];
      const cls = ['cal-cell'];
      if (d.getMonth() !== ref.getMonth()) cls.push('cal-cell--out');
      if (sameDay(d, today)) cls.push('cal-cell--today');
      const evs = list.slice(0, 3).map(calEv).join('');
      const more = list.length > 3 ? `<div class="cal-more">+${list.length - 3}</div>` : '';
      cells += `<div class="${cls.join(' ')}"><div class="cal-daynum">${d.getDate()}</div>${evs}${more}</div>`;
    }
    const head = DOW.map((x) => `<div class="cal-dow">${x}</div>`).join('');
    return `<div class="cal-grid"><div class="cal-weekhead">${head}</div><div class="cal-cells">${cells}</div></div>`;
  }
  function calWeek(byDay) {
    const ws = new Date(_calRef);
    ws.setDate(ws.getDate() - ws.getDay());
    const today = new Date();
    let head = '';
    let cells = '';
    for (let i = 0; i < 7; i++) {
      const d = new Date(ws);
      d.setDate(ws.getDate() + i);
      head += `<div class="cal-dow">${DOW[i]} ${d.getDate()}</div>`;
      const list = byDay[isoDate(d)] || [];
      const evs = list.map(calEv).join('') || '<div class="cal-more">—</div>';
      cells += `<div class="cal-cell cal-cell--week ${sameDay(d, today) ? 'cal-cell--today' : ''}">${evs}</div>`;
    }
    return `<div class="cal-grid cal-grid--week"><div class="cal-weekhead cal-weekhead--week">${head}</div><div class="cal-cells cal-cells--week">${cells}</div></div>`;
  }
  function calControls() {
    const isWeek = _calEscala === 'semana';
    let label;
    if (isWeek) {
      const ws = new Date(_calRef); ws.setDate(ws.getDate() - ws.getDay());
      const we = new Date(ws); we.setDate(we.getDate() + 6);
      label = `${ws.getDate()} ${MESES_ABBR[ws.getMonth()]} – ${we.getDate()} ${MESES_ABBR[we.getMonth()]} ${we.getFullYear()}`;
    } else {
      label = `${MESES[_calRef.getMonth()]} de ${_calRef.getFullYear()}`;
    }
    return `<div class="opp-subbar">
      <div class="opp-nav">
        <button class="icon-btn" id="cal-prev" aria-label="Anterior"><svg width="16" height="16"><use href="#i-chev-left"/></svg></button>
        <span class="opp-nav__label">${label}</span>
        <button class="icon-btn" id="cal-next" aria-label="Próximo"><svg width="16" height="16"><use href="#i-chev-right"/></svg></button>
        <button class="btn btn--secondary btn--sm" id="cal-today">Hoje</button>
      </div>
      <div class="opp-seg" id="cal-seg">
        <button class="opp-seg__btn ${!isWeek ? 'is-active' : ''}" data-esc="mes">Mês</button>
        <button class="opp-seg__btn ${isWeek ? 'is-active' : ''}" data-esc="semana">Semana</button>
      </div>
    </div>`;
  }
  async function renderCalendario() {
    const root = document.getElementById('opp-view-root');
    const controls = calControls();
    root.innerHTML = controls + '<div class="opp-empty">Carregando…</div>';
    bindCalControls();
    try {
      const qs = calFilterQuery();
      qs.set('ref', isoDate(_calRef));
      qs.set('escala', _calEscala);
      const data = await api('/atividades/calendario?' + qs.toString());
      if (_oppView !== 'calendario') return; // saiu da view durante o fetch
      const byDay = {};
      (data.atividades || []).forEach((a) => { const k = (a.inicio_em || '').slice(0, 10); (byDay[k] || (byDay[k] = [])).push(a); });
      root.innerHTML = controls + (_calEscala === 'semana' ? calWeek(byDay) : calMonth(byDay));
      bindCalControls();
      root.querySelectorAll('[data-atv]').forEach((el) => el.addEventListener('click', () => showAtividade(el.dataset.atv)));
    } catch (e) {
      root.innerHTML = controls + emptyState('Erro ao carregar', e.message);
      bindCalControls();
    }
  }

  // ---- Timeline ----
  function shiftTl(dir) {
    if (_tlEscala === 'ano') _tlRef.setFullYear(_tlRef.getFullYear() + dir);
    else if (_tlEscala === 'trimestre') _tlRef.setMonth(_tlRef.getMonth() + 3 * dir);
    else _tlRef.setMonth(_tlRef.getMonth() + dir);
    _tlRef = new Date(_tlRef);
  }
  function bindTlControls() {
    const prev = document.getElementById('tl-prev');
    const next = document.getElementById('tl-next');
    const today = document.getElementById('tl-today');
    const seg = document.getElementById('tl-seg');
    if (prev) prev.onclick = () => { shiftTl(-1); renderTimeline(); };
    if (next) next.onclick = () => { shiftTl(1); renderTimeline(); };
    if (today) today.onclick = () => { _tlRef = new Date(); renderTimeline(); };
    if (seg) seg.onclick = (e) => { const b = e.target.closest('.opp-seg__btn'); if (!b) return; _tlEscala = b.dataset.esc; renderTimeline(); };
  }
  function tlAxis(start, end, esc) {
    const span = (end - start) || 1;
    const ticks = [];
    if (esc === 'ano') {
      for (let m = 0; m < 12; m++) { const d = new Date(start.getFullYear(), m, 1); ticks.push([(d - start) / span * 100, MESES_ABBR[m]]); }
    } else if (esc === 'trimestre') {
      for (let i = 0; i < 3; i++) { const d = new Date(start.getFullYear(), start.getMonth() + i, 1); ticks.push([(d - start) / span * 100, MESES_ABBR[d.getMonth()]]); }
    } else {
      const days = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
      for (let day = 1; day <= days; day += 5) { const d = new Date(start.getFullYear(), start.getMonth(), day); ticks.push([(d - start) / span * 100, String(day)]); }
    }
    return ticks.map(([l, t]) => `<span class="tl-axis__lbl" style="left:${l}%">${t}</span>`).join('');
  }
  function tlControls() {
    const escLabel = { mes: 'Mês', trimestre: 'Trimestre', ano: 'Ano' };
    let label;
    if (_tlEscala === 'ano') label = `${_tlRef.getFullYear()}`;
    else if (_tlEscala === 'trimestre') label = `${Math.floor(_tlRef.getMonth() / 3) + 1}º trimestre · ${_tlRef.getFullYear()}`;
    else label = `${MESES[_tlRef.getMonth()]} de ${_tlRef.getFullYear()}`;
    return `<div class="opp-subbar">
      <div class="opp-nav">
        <button class="icon-btn" id="tl-prev" aria-label="Anterior"><svg width="16" height="16"><use href="#i-chev-left"/></svg></button>
        <span class="opp-nav__label">${label}</span>
        <button class="icon-btn" id="tl-next" aria-label="Próximo"><svg width="16" height="16"><use href="#i-chev-right"/></svg></button>
        <button class="btn btn--secondary btn--sm" id="tl-today">Hoje</button>
      </div>
      <div class="opp-seg" id="tl-seg">
        ${['mes', 'trimestre', 'ano'].map((k) => `<button class="opp-seg__btn ${_tlEscala === k ? 'is-active' : ''}" data-esc="${k}">${escLabel[k]}</button>`).join('')}
      </div>
    </div>`;
  }
  async function renderTimeline() {
    const root = document.getElementById('opp-view-root');
    const controls = tlControls();
    root.innerHTML = controls + '<div class="opp-empty">Carregando…</div>';
    bindTlControls();
    try {
      const tlqs = calFilterQuery();
      tlqs.set('ref', isoDate(_tlRef));
      tlqs.set('escala', _tlEscala);
      const data = await api('/atividades/timeline?' + tlqs.toString());
      if (_oppView !== 'timeline') return; // saiu da view durante o fetch
      const start = new Date(data.inicio);
      const end = new Date(data.fim);
      const span = (end - start) || 1;
      const pct = (iso) => Math.max(0, Math.min(100, (new Date(iso) - start) / span * 100));
      const ops = data.oportunidades || [];
      if (!ops.length) {
        root.innerHTML = controls + emptyState('Sem oportunidades no período', 'Crie atividades vinculadas a um cliente.');
        bindTlControls();
        return;
      }
      const rows = ops.map((o) => {
        const sorted = o.atividades.filter((a) => a.inicio_em).slice()
          .sort((a, b) => (a.inicio_em < b.inicio_em ? -1 : (a.inicio_em > b.inicio_em ? 1 : 0)));
        const barL = sorted.length ? pct(sorted[0].inicio_em) : 0;
        const barR = sorted.length ? pct(sorted[sorted.length - 1].inicio_em) : 0;
        const stage = sorted.length ? (sorted[0].titulo || 'Primeiro contato') : '';
        const ticks = o.atividades.filter((a) => a.inicio_em).map((a) =>
          `<span class="tl-tick temp-dot--${a.temperatura || 'none'}" style="left:${pct(a.inicio_em)}%" data-atv="${a.id}" data-hora="${escapeHtml(fmtTimeOnly(a.inicio_em))}" data-emp="${escapeHtml(o.empresa)}" data-titulo="${escapeHtml(a.titulo || '')}" data-temp="${a.temperatura || 'none'}" data-ico="${tipoIcon(a.tipo)}"></span>`).join('');
        return `<div class="tl-row">
          <div class="tl-row__label">
            <div class="tl-row__emp">${escapeHtml(o.empresa)}</div>
            <div class="tl-row__meta">Ciclo: ${o.ciclo_dias}d · <select class="tl-status-sel tl-status--${o.status}" data-lead="${o.lead_id}" aria-label="Status da oportunidade">${['em_andamento', 'ganho', 'congelado', 'perdido'].map((s) => `<option value="${s}" ${s === o.status ? 'selected' : ''}>${statusLabel(s)}</option>`).join('')}</select></div>
          </div>
          <div class="tl-track">
            <div class="tl-bar-rest" style="left:${barR}%;width:${Math.max(0, 100 - barR)}%"></div>
            <div class="tl-bar tl-bar--${o.status}" style="left:${barL}%;width:${Math.max(1, barR - barL)}%"></div>
            ${o.status === 'ganho' ? `<span class="tl-won" style="left:${barR}%"><svg width="13" height="13"><use href="#i-star"/></svg>Negócio ganho</span>` : ''}
            ${stage ? `<span class="tl-stage" style="left:${barL}%">${escapeHtml(stage)}</span>` : ''}
            ${ticks}
          </div>
        </div>`;
      }).join('');
      root.innerHTML = controls + `<div class="tl">
        <div class="tl-row tl-row--axis"><div class="tl-row__label tl-row__label--axis">Cliente · ciclo</div><div class="tl-track tl-axis">${tlAxis(start, end, _tlEscala)}</div></div>
        ${rows}
      </div>`;
      bindTlControls();
      root.querySelectorAll('.tl-tick[data-atv]').forEach((el) => el.addEventListener('click', () => showAtividade(el.dataset.atv)));
      const tlEl = root.querySelector('.tl');
      if (tlEl) {
        tlEl.addEventListener('mouseover', (e) => { const t = e.target.closest('.tl-tick'); if (t) showTlTip(t); });
        tlEl.addEventListener('mouseout', (e) => { const t = e.target.closest('.tl-tick'); if (t) hideTlTip(); });
      }
      root.querySelectorAll('.tl-status-sel').forEach((sel) => sel.addEventListener('change', async (e) => {
        e.stopPropagation();
        try {
          await api('/db/leads/' + sel.dataset.lead, { method: 'PATCH', body: JSON.stringify({ pipeline_status: sel.value }) });
          toast('Status atualizado', 'success');
          renderTimeline();
        } catch (err) { toast('Erro: ' + err.message, 'error'); }
      }));
    } catch (e) {
      root.innerHTML = controls + emptyState('Erro ao carregar', e.message);
      bindTlControls();
    }
  }

  // Na 1ª abertura, abre Calendário/Timeline no mês da atividade mais recente
  let _oppDateInit = false;
  async function initDefaultMonth() {
    if (_oppDateInit) return;
    _oppDateInit = true;
    try {
      const data = await api('/atividades?order=desc&limit=1');
      const a = (data.atividades || [])[0];
      if (a && a.inicio_em) {
        const d = new Date(a.inicio_em);
        if (!isNaN(d)) { _calRef = d; _tlRef = d; }
      }
    } catch (e) { /* mantém o mês atual */ }
  }

  async function loadOportunidades() {
    if (!_oppBound) {
      _oppBound = true;
      document.getElementById('opp-views').addEventListener('click', (e) => {
        const btn = e.target.closest('.opp-view');
        if (!btn) return;
        _oppView = btn.dataset.view;
        document.querySelectorAll('.opp-view').forEach((b) => b.classList.toggle('is-active', b === btn));
        renderOppView();
      });
      ['opp-f-periodo', 'opp-f-tipo', 'opp-f-temp', 'opp-f-pipeline'].forEach((id) =>
        document.getElementById(id).addEventListener('change', renderOppView));
      document.getElementById('opp-nova').addEventListener('click', openNovaAtividade);
    }
    await initDefaultMonth();
    renderOppView();
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
