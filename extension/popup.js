const DEFAULT_API_URL = 'https://api-catanalytics.meekconsulting.com/games';

// ============================================================================
// Injected into the Colonist.io tab. Must be fully self-contained: no
// references to anything outside this function's own body/args, since
// chrome.scripting.executeScript serializes and re-runs it in the page.
// ============================================================================
async function scrapeColonistGame() {
  const FEEDS_SEL    = '[class*="gameFeedsContainer"]';
  const SCROLLER_SEL = '[class^="virtualScroller-"]';
  const ITEM_SEL     = '[class^="scrollItemContainer-"]';
  const MSG_SEL      = '[class^="messagePart-"]';

  const SCROLL_STEP_PX = 50;
  const STEP_DELAY_MS  = 250;
  const FINAL_WAIT_MS  = 1000;

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function createTimestamp() {
    const now = new Date();
    return (
      now.getFullYear() + '-' +
      String(now.getMonth() + 1).padStart(2, '0') + '-' +
      String(now.getDate()).padStart(2, '0') + '_' +
      String(now.getHours()).padStart(2, '0') + '-' +
      String(now.getMinutes()).padStart(2, '0') + '-' +
      String(now.getSeconds()).padStart(2, '0')
    );
  }

  function messageToText(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('img.lobby-chat-text-icon, img[alt]')
      .forEach(img => {
        const alt = img.getAttribute('alt');
        img.replaceWith(alt ? `[${alt}]` : '');
      });
    clone.querySelectorAll('[class*="avatar"]').forEach(n => n.remove());
    clone.querySelectorAll('img').forEach(img => img.remove());
    return clone.textContent.replace(/\s+/g, ' ').trim();
  }

  function scrapePlayerSummary() {
    const tabContent = document.querySelector("div[class^='tabContent']");
    if (!tabContent) return [];

    const playerRows = [...tabContent.querySelectorAll("div[class^='row-vWs3tVp5']")];
    const players = [];

    for (const row of playerRows) {
      const nameEl = row.querySelector("div[class^='name-']");
      const vpEl   = row.querySelector("div[class^='victoryPoint-']");
      const name = nameEl?.textContent.trim();
      const vp   = vpEl?.textContent.trim();
      if (!name) continue;
      players.push({ name, victoryPoints: vp ? parseInt(vp, 10) : null });
    }

    const headerIcons = [...tabContent.querySelectorAll("div[class*='headerContainer'] img")];
    const headers = headerIcons.map(img => {
      const src = img.getAttribute('src') || '';
      const filename = src.split('/').pop() || '';
      let name = filename.replace(/\.[a-z0-9]+\.svg$/i, '').replace(/\.svg$/i, '');

      if (name.startsWith('settlement')) return 'settlements';
      if (name.startsWith('city')) return 'cities';
      if (name.startsWith('stat_vp')) return 'vp_breakdown';
      if (name.startsWith('stat_largest_army')) return 'largest_army';
      if (name.startsWith('stat_longest_road')) return 'longest_road';
      if (name.startsWith('stat_mmr_change')) return 'mmr_change';

      return name.replace(/^stat_/, '').replace(/[^a-z0-9_]/gi, '');
    });

    const statRows = [...tabContent.querySelectorAll("div[class^='rowContainer']")];
    const statData = statRows
      .map(row => {
        const cells = [...row.querySelectorAll("div.value-myGdPGIC")];
        if (!cells.length) return null;
        const values = cells.map(c => c.textContent.trim());
        const obj = {};
        headers.forEach((header, i) => { obj[header] = values[i] ?? null; });
        return obj;
      })
      .filter(Boolean);

    return players.map((p, i) => ({ ...p, ...(statData[i] || {}) }));
  }

  const feeds = document.querySelector(FEEDS_SEL);
  if (!feeds || feeds.children.length < 1) {
    return { ok: false, error: 'Could not find the game log panel. Are you on an active Colonist.io game page?' };
  }

  const logPanel = feeds.children[0];
  const scroller = logPanel.querySelector(SCROLLER_SEL);
  if (!scroller) {
    return { ok: false, error: 'Could not find the log scroller.' };
  }

  const scrollContainer = scroller.parentElement;
  const collected = new Map();

  function harvest() {
    logPanel.querySelectorAll(ITEM_SEL).forEach(item => {
      const idx = parseInt(item.getAttribute('data-index'), 10);
      if (isNaN(idx)) return;
      const msgEl = item.querySelector(MSG_SEL);
      if (!msgEl) return;
      const text = messageToText(msgEl);
      if (!collected.has(idx) || text.length > collected.get(idx).text.length) {
        collected.set(idx, { index: idx, text, html: msgEl.innerHTML });
      }
    });
  }

  scrollContainer.scrollTop = 0;
  await sleep(FINAL_WAIT_MS);
  harvest();

  const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight;
  for (let pos = 0; pos <= maxScroll; pos += SCROLL_STEP_PX) {
    scrollContainer.scrollTop = pos;
    for (let i = 0; i < 3; i++) {
      await sleep(STEP_DELAY_MS);
      harvest();
    }
  }

  scrollContainer.scrollTop = maxScroll;
  await sleep(FINAL_WAIT_MS);
  harvest();

  const sortedItems = [...collected.values()].sort((a, b) => a.index - b.index);
  if (!sortedItems.length) {
    return { ok: false, error: 'No game log events were found to collect.' };
  }

  const players = scrapePlayerSummary();
  const gameData = {
    timestamp: createTimestamp(),
    playerSummary: players,
    events: sortedItems
  };

  return { ok: true, data: gameData };
}

// ============================================================================
// Popup UI logic
// ============================================================================

function setStatus(message, kind) {
  const el = document.getElementById('status');
  el.textContent = message;
  el.className = kind || '';
}

async function getApiUrl() {
  const { apiUrl } = await chrome.storage.sync.get('apiUrl');
  return apiUrl || DEFAULT_API_URL;
}

async function getApiKey() {
  const { apiKey } = await chrome.storage.sync.get('apiKey');
  return apiKey || '';
}

document.addEventListener('DOMContentLoaded', async () => {
  const apiUrlInput = document.getElementById('apiUrl');
  const apiKeyInput = document.getElementById('apiKey');
  apiUrlInput.value = await getApiUrl();
  apiKeyInput.value = await getApiKey();

  document.getElementById('saveUrl').addEventListener('click', async () => {
    const apiUrl = apiUrlInput.value.trim();
    if (!apiUrl) return;
    await chrome.storage.sync.set({ apiUrl, apiKey: apiKeyInput.value.trim() });
    setStatus('API settings saved.', 'info');
  });

  document.getElementById('captureBtn').addEventListener('click', onCapture);
});

async function onCapture() {
  const btn = document.getElementById('captureBtn');
  btn.disabled = true;

  try {
    setStatus('Scraping current game...', 'info');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error('No active tab found.');

    const injectionResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: scrapeColonistGame
    });

    const scrapeResult = injectionResults?.[0]?.result;
    if (!scrapeResult || !scrapeResult.ok) {
      throw new Error(scrapeResult?.error || 'Scrape failed for an unknown reason.');
    }

    const gameData = scrapeResult.data;
    setStatus(
      `Captured ${gameData.events.length} events, ${gameData.playerSummary.length} players. Uploading...`,
      'info'
    );

    const apiUrl = await getApiUrl();
    const apiKey = await getApiKey();
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(gameData)
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`Upload failed: ${response.status} ${response.statusText} ${text}`.trim());
    }

    setStatus('Game uploaded successfully.', 'success');
  } catch (err) {
    setStatus(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}
