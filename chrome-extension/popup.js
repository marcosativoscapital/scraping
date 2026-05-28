// Popup principal — orquestra UI da extensão e fala com servidor local
(() => {
  const DEFAULT_API_URL = 'http://127.0.0.1:8765';

  let apiUrl = DEFAULT_API_URL;
  let apiToken = '';

  // ====== STORAGE ======
  async function loadSettings() {
    const data = await chrome.storage.local.get(['apiUrl', 'apiToken']);
    apiUrl = data.apiUrl || DEFAULT_API_URL;
    apiToken = data.apiToken || '';
    document.getElementById('api-url-input').value = apiUrl;
    document.getElementById('api-token-input').value = apiToken;
    document.getElementById('api-url').textContent = apiUrl;
  }

  async function saveSettings() {
    apiUrl = document.getElementById('api-url-input').value.trim();
    apiToken = document.getElementById('api-token-input').value.trim();
    await chrome.storage.local.set({ apiUrl, apiToken });
    document.getElementById('api-url').textContent = apiUrl;
    setStatus('Configuração salva.');
    checkConnection();
  }

  // ====== API HELPERS ======
  async function apiCall(path, options = {}) {
    const url = `${apiUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Token': apiToken,
      ...(options.headers || {}),
    };
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      throw new Error(`API ${res.status}: ${await res.text()}`);
    }
    return res.json();
  }

  // ====== CONEXÃO ======
  async function checkConnection() {
    const badge = document.getElementById('connection-status');
    try {
      const data = await apiCall('/');
      badge.textContent = `● Online (${data.jobs_ativos} jobs)`;
      badge.className = 'badge connected';
      document.getElementById('jobs-count').textContent = data.jobs_ativos;
    } catch (e) {
      badge.textContent = '● Offline';
      badge.className = 'badge disconnected';
    }
  }

  // ====== DISPARAR SCRAPE ======
  async function triggerScrape() {
    const vertical = document.getElementById('vertical-select').value;
    const limitVal = document.getElementById('limit-input').value;
    const enrichEmail = document.getElementById('enrich-email').checked;

    const btn = document.getElementById('trigger-scrape');
    btn.disabled = true;
    btn.textContent = 'Disparando...';

    try {
      const data = await apiCall('/scrape', {
        method: 'POST',
        body: JSON.stringify({
          vertical,
          limit: limitVal ? parseInt(limitVal, 10) : null,
          enrich_email: enrichEmail,
        }),
      });
      setStatus(`Job ${data.job_id.slice(0, 8)} disparado!`);
      loadJobs();
    } catch (e) {
      setStatus(`Erro: ${e.message}`, true);
    } finally {
      btn.disabled = false;
      btn.textContent = '▶ Disparar';
    }
  }

  // ====== LIST JOBS ======
  async function loadJobs() {
    try {
      const jobs = await apiCall('/jobs');
      const ul = document.getElementById('jobs-list');
      if (!jobs.length) {
        ul.innerHTML = '<div class="hint">Nenhum job ainda.</div>';
        return;
      }
      ul.innerHTML = jobs
        .sort((a, b) => b.criado_em.localeCompare(a.criado_em))
        .slice(0, 5)
        .map((j) => {
          const csv = j.csv_path
            ? `<br><a href="#" data-path="${j.csv_path}" class="open-output">📄 ${j.csv_path.split('/').pop()}</a>`
            : '';
          return `
            <div class="job-item">
              <span class="job-status ${j.status}">${j.status}</span>
              <strong>${j.vertical}</strong>
              <span class="job-id">${j.id.slice(0, 8)}</span><br>
              <small>${j.leads || 0} leads · ${new Date(j.criado_em).toLocaleString('pt-BR')}</small>
              ${csv}
            </div>
          `;
        })
        .join('');
    } catch (e) {
      document.getElementById('jobs-list').innerHTML = `<div class="hint">Não conectado.</div>`;
    }
  }

  // ====== LIST OUTPUTS ======
  async function loadOutputs() {
    try {
      const outputs = await apiCall('/outputs');
      const div = document.getElementById('outputs-list');
      if (!outputs.length) {
        div.innerHTML = '<div class="hint">Nenhum CSV ainda.</div>';
        return;
      }
      div.innerHTML = outputs
        .slice(0, 5)
        .map(
          (o) => `
        <div class="output-item">
          📄 <strong>${o.arquivo}</strong><br>
          <small>${(o.tamanho / 1024).toFixed(1)} KB · ${new Date(o.modificado).toLocaleString('pt-BR')}</small>
        </div>`
        )
        .join('');
    } catch (e) {
      document.getElementById('outputs-list').innerHTML = '<div class="hint">Não conectado.</div>';
    }
  }

  // ====== CAPTURE LINKEDIN ======
  async function captureLinkedIn() {
    const btn = document.getElementById('capture-linkedin');
    btn.disabled = true;
    btn.textContent = 'Capturando...';

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab.url || !tab.url.includes('linkedin.com')) {
        setLinkedInStatus('Abra uma página do LinkedIn primeiro.', true);
        return;
      }

      // Envia mensagem para content script extrair dados
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'capture' });
      if (!response || !response.items || response.items.length === 0) {
        setLinkedInStatus('Nenhum lead encontrado na página atual.', true);
        return;
      }

      setLinkedInStatus(`${response.items.length} leads capturados. Enviando ao servidor...`);

      // Envia ao backend
      const result = await apiCall('/linkedin/ingest', {
        method: 'POST',
        body: JSON.stringify(response),
      });
      setLinkedInStatus(`✓ ${result.leads_processados} leads processados! CSV: ${result.csv}`);

      // Preview
      document.getElementById('linkedin-preview').innerHTML = (result.leads || [])
        .slice(0, 3)
        .map(
          (l) => `
        <div class="job-item">
          <strong>${l.decisor_nome || l.empresa || 'sem nome'}</strong><br>
          <small>${l.decisor_cargo || ''} · ${l.empresa || ''}</small><br>
          <small>Score: ${l.score_icp || 0} · ${l.recomendacao || ''}</small>
        </div>
      `
        )
        .join('');
    } catch (e) {
      setLinkedInStatus(`Erro: ${e.message}`, true);
    } finally {
      btn.disabled = false;
      btn.textContent = '📥 Capturar página atual';
    }
  }

  // ====== UTILS ======
  function setStatus(msg, isError = false) {
    console.log('[Solve Scraper]', msg);
  }

  function setLinkedInStatus(msg, isError = false) {
    const el = document.getElementById('linkedin-status');
    el.textContent = msg;
    el.style.color = isError ? '#fb7185' : '#4ade80';
  }

  // ====== TABS ======
  function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
      });
    });
  }

  // ====== INIT ======
  document.addEventListener('DOMContentLoaded', async () => {
    setupTabs();
    await loadSettings();
    await checkConnection();
    await loadJobs();
    await loadOutputs();

    document.getElementById('trigger-scrape').addEventListener('click', triggerScrape);
    document.getElementById('capture-linkedin').addEventListener('click', captureLinkedIn);
    document.getElementById('save-settings').addEventListener('click', saveSettings);

    // Polling de jobs a cada 3s
    setInterval(() => {
      if (document.getElementById('tab-dashboard').classList.contains('active')) {
        checkConnection();
        loadJobs();
        loadOutputs();
      }
    }, 3000);
  });
})();
