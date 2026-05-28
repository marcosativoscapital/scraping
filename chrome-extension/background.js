// Service worker — gerencia estado de background e notificações

chrome.runtime.onInstalled.addListener(() => {
  console.log('Solve Scraper instalado.');
  chrome.storage.local.get(['apiUrl', 'apiToken'], (data) => {
    if (!data.apiUrl) {
      chrome.storage.local.set({
        apiUrl: 'http://127.0.0.1:8765',
        apiToken: '',
      });
    }
  });
});

// Listener para notificações de job concluído (futuro)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'notify') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: msg.title || 'Solve Scraper',
      message: msg.message || '',
    });
    sendResponse({ ok: true });
  }
  return true;
});
