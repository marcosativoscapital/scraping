// Content script — roda nas páginas do LinkedIn
// Captura dados visíveis e envia para o popup quando solicitado

(() => {
  'use strict';

  // ====== DETECTORES DE PÁGINA ======
  function pageType() {
    const u = window.location.href;
    if (u.includes('/sales/search/people')) return 'sales_nav_people';
    if (u.includes('/sales/search/company')) return 'sales_nav_company';
    if (u.includes('/sales/lists/')) return 'sales_nav_list';
    if (u.includes('/search/results/people')) return 'search_people';
    if (u.includes('/in/')) return 'profile';
    if (u.includes('/company/')) return 'company';
    return 'unknown';
  }

  // ====== EXTRATORES POR TIPO ======
  function extractSalesNavPeople() {
    const items = [];
    // Sales Navigator lista pessoas em cards específicos
    const cards = document.querySelectorAll(
      '[data-x-search-result], .artdeco-list__item, [class*="search-results__result-item"]'
    );
    cards.forEach((card) => {
      const nameEl = card.querySelector('[data-anonymize="person-name"], [class*="result-lockup__name"] a, .ember-view a span');
      const titleEl = card.querySelector('[data-anonymize="title"], [class*="result-lockup__highlight-keyword"], [class*="t-14"]');
      const companyEl = card.querySelector('[data-anonymize="company-name"], [class*="result-lockup__position-company"] a');
      const link = card.querySelector('a[href*="/in/"], a[href*="/sales/lead/"]');

      if (nameEl && nameEl.textContent.trim()) {
        items.push({
          nome: cleanText(nameEl.textContent),
          cargo: titleEl ? cleanText(titleEl.textContent) : null,
          empresa: companyEl ? cleanText(companyEl.textContent) : null,
          url: link ? new URL(link.href, window.location.origin).href : null,
        });
      }
    });
    return items;
  }

  function extractSearchPeople() {
    const items = [];
    const cards = document.querySelectorAll('.reusable-search__result-container, li.search-result');
    cards.forEach((card) => {
      const nameEl = card.querySelector('span[aria-hidden="true"], .entity-result__title-text a');
      const titleEl = card.querySelector('.entity-result__primary-subtitle, .subline-level-1');
      const companyEl = card.querySelector('.entity-result__secondary-subtitle, .subline-level-2');
      const link = card.querySelector('a[href*="/in/"]');

      if (nameEl && nameEl.textContent.trim()) {
        items.push({
          nome: cleanText(nameEl.textContent),
          cargo: titleEl ? cleanText(titleEl.textContent) : null,
          empresa: companyEl ? cleanText(companyEl.textContent) : null,
          url: link ? new URL(link.href, window.location.origin).href : null,
        });
      }
    });
    return items;
  }

  function extractProfile() {
    const nameEl = document.querySelector('h1');
    const titleEl = document.querySelector('.text-body-medium, .top-card-layout__headline');
    const companyEl = document.querySelector(
      '[data-control-name="position_see_more"], .pv-text-details__right-panel button span'
    );

    if (!nameEl) return [];

    return [
      {
        nome: cleanText(nameEl.textContent),
        cargo: titleEl ? cleanText(titleEl.textContent) : null,
        empresa: companyEl ? cleanText(companyEl.textContent) : null,
        url: window.location.href,
      },
    ];
  }

  function extractCompany() {
    const nameEl = document.querySelector('h1');
    const taglineEl = document.querySelector('.org-top-card-summary__tagline, .top-card-layout__headline');

    if (!nameEl) return [];

    return [
      {
        empresa: cleanText(nameEl.textContent),
        cargo: null,
        nome: null,
        url: window.location.href,
        descricao: taglineEl ? cleanText(taglineEl.textContent) : null,
      },
    ];
  }

  function cleanText(s) {
    return (s || '').replace(/\s+/g, ' ').trim();
  }

  // ====== CAPTURA PRINCIPAL ======
  function capture() {
    const type = pageType();
    let items = [];

    switch (type) {
      case 'sales_nav_people':
      case 'sales_nav_list':
        items = extractSalesNavPeople();
        break;
      case 'sales_nav_company':
        items = extractSalesNavPeople();
        break;
      case 'search_people':
        items = extractSearchPeople();
        break;
      case 'profile':
        items = extractProfile();
        break;
      case 'company':
        items = extractCompany();
        break;
      default:
        items = [];
    }

    return {
      source: 'linkedin_' + type,
      url: window.location.href,
      items,
      captured_at: new Date().toISOString(),
    };
  }

  // ====== MESSAGE LISTENER ======
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.action === 'capture') {
      try {
        const data = capture();
        sendResponse(data);
      } catch (e) {
        sendResponse({ error: e.message, items: [] });
      }
    }
    return true; // mantém canal aberto
  });

  // ====== BADGE VISUAL (opcional) ======
  function injectBadge() {
    if (document.getElementById('solve-scraper-badge')) return;
    const badge = document.createElement('div');
    badge.id = 'solve-scraper-badge';
    badge.className = 'solve-scraper-badge';
    badge.textContent = '🎯 Solve Scraper';
    badge.title = 'Página detectada pelo Solve Scraper';
    document.body.appendChild(badge);

    setTimeout(() => {
      badge.style.opacity = '0.4';
    }, 3000);
  }

  if (pageType() !== 'unknown') {
    injectBadge();
  }
})();
