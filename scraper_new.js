(async function scrapeColonistGame() {

  // ───────────────────────────────────────────────────────────────────────────
  // Config
  // ───────────────────────────────────────────────────────────────────────────

  const FEEDS_SEL = '[class*="gameFeedsContainer"]';
  const SCROLLER_SEL = '[class^="virtualScroller-"]';
  const ITEM_SEL     = '[class^="scrollItemContainer-"]';
  const MSG_SEL      = '[class^="messagePart-"]';

  const SCROLL_STEP_PX = 50;
  const STEP_DELAY_MS  = 250;
  const FINAL_WAIT_MS  = 1000;

  // ───────────────────────────────────────────────────────────────────────────
  // Helpers
  // ───────────────────────────────────────────────────────────────────────────

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

  function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;

    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Message cleaner
  // ───────────────────────────────────────────────────────────────────────────

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

  // ───────────────────────────────────────────────────────────────────────────
  // Player summary (unchanged)
  // ───────────────────────────────────────────────────────────────────────────

  function scrapePlayerSummary() {
    const tabContent = document.querySelector("div[class^='tabContent']");
    if (!tabContent) return [];

    const playerRows = [...tabContent.querySelectorAll("div[class^='row-vWs3tVp5']")];

    const players = [];

    for (const row of playerRows) {
      const name = row.querySelector("div[class^='name-']")?.textContent.trim();
      const vp   = row.querySelector("div[class^='victoryPoint-']")?.textContent.trim();

      if (!name) continue;

      players.push({
        name,
        victoryPoints: vp ? parseInt(vp, 10) : null
      });
    }

    return players;
  }

  // ───────────────────────────────────────────────────────────────────────────
  // 🔥 KEY FIX: isolate LOG panel ONLY
  // ───────────────────────────────────────────────────────────────────────────

  const feeds = document.querySelector(FEEDS_SEL);

  if (!feeds || feeds.children.length < 1) {
    console.error('[GameLog] Could not find feeds container.');
    return;
  }

  const logPanel = feeds.children[0]; // 👈 THIS is the game log

  const scroller = logPanel.querySelector(SCROLLER_SEL);

  if (!scroller) {
    console.error('[GameLog] Could not find log scroller.');
    return;
  }

  const scrollContainer = scroller.parentElement;

  // ───────────────────────────────────────────────────────────────────────────
  // Harvest
  // ───────────────────────────────────────────────────────────────────────────

  const collected = new Map();

  function harvest() {

    logPanel.querySelectorAll(ITEM_SEL).forEach(item => {

      const idx = parseInt(item.getAttribute('data-index'), 10);
      if (isNaN(idx)) return;

      const msgEl = item.querySelector(MSG_SEL);
      if (!msgEl) return;

      const text = messageToText(msgEl);

      if (!collected.has(idx)) {
        collected.set(idx, {
          index: idx,
          text,
          html: msgEl.innerHTML
        });
      }
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Scroll + collect
  // ───────────────────────────────────────────────────────────────────────────

  console.log('[GameLog] Starting collection...');

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

  // ───────────────────────────────────────────────────────────────────────────
  // Output
  // ───────────────────────────────────────────────────────────────────────────

  const sortedItems = [...collected.values()]
    .sort((a, b) => a.index - b.index);

  if (!sortedItems.length) {
    console.error('[GameLog] No items collected.');
    return;
  }

  const players = scrapePlayerSummary();
  const timestamp = createTimestamp();

  const gameData = {
    timestamp,
    playerSummary: players,
    events: sortedItems
  };

  const filename = `colonist_game_${timestamp}.json`;

  downloadFile(
    JSON.stringify(gameData, null, 2),
    filename,
    'application/json'
  );

  window.__colonistGameData = gameData;
  window.__colonistEvents = sortedItems;
  window.__colonistPlayers = players;

  console.log(`[Done] ${sortedItems.length} events collected.`);
  console.log(`[Done] ${players.length} players collected.`);

  return gameData;

})();
