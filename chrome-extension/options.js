document.addEventListener('DOMContentLoaded', async () => {
  const data = await chrome.storage.local.get(['apiUrl', 'apiToken']);
  document.getElementById('api-url').value = data.apiUrl || 'http://127.0.0.1:8765';
  document.getElementById('api-token').value = data.apiToken || '';

  document.getElementById('save').addEventListener('click', async () => {
    const apiUrl = document.getElementById('api-url').value.trim();
    const apiToken = document.getElementById('api-token').value.trim();
    await chrome.storage.local.set({ apiUrl, apiToken });
    document.getElementById('status').textContent = '✓ Salvo';
    setTimeout(() => (document.getElementById('status').textContent = ''), 2000);
  });
});
