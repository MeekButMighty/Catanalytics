/**
 * Colonist.io Full Game Scraper
 *
 * Exports:
 *   1. Full event log JSON
 *
 */

(async function scrapeColonistGame() {

  // ───────────────────────────────────────────────────────────────────────────
  // Config
  // ───────────────────────────────────────────────────────────────────────────

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

  function toCSV(rows) {
    if (!rows.length) return '';

    const headers = [
      ...new Set(rows.flatMap(r => Object.keys(r)))
    ];

    return [
      headers.join(','),
      ...rows.map(row =>
        headers.map(h => {
          const value = row[h] ?? '';
          return `"${String(value).replace(/"/g, '""')}"`;
        }).join(',')
      )
    ].join('\n');
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Message Parser
  // ───────────────────────────────────────────────────────────────────────────

  function messageToText(el) {
    const clone = el.cloneNode(true);

    clone.querySelectorAll('img.lobby-chat-text-icon, img[alt]')
      .forEach(img => {
        const alt = img.getAttribute('alt');

        if (alt) {
          img.replaceWith(`[${alt}]`);
        } else {
          img.replaceWith('');
        }
      });

    const avatarContainer = clone.querySelector('[class*="avatar-"]');

    if (avatarContainer) {
      avatarContainer.remove();
    }

    clone.querySelectorAll('img').forEach(img => img.remove());

    return clone.textContent.replace(/\s+/g, ' ').trim();
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Player Summary Scraper
  // ───────────────────────────────────────────────────────────────────────────

  function scrapePlayerSummary() {

    const tabContent = document.querySelector("div[class^='tabContent']");

    if (!tabContent) {
      console.warn('[Summary] Could not find stats tab.');
      return [];
    }

    // ───────────────────────────────────────────────────────────────────────
    // Players
    // ───────────────────────────────────────────────────────────────────────

    const playerRows = [
      ...tabContent.querySelectorAll("div[class^='row-vWs3tVp5']")
    ];

    const players = [];

    for (const row of playerRows) {

      const nameEl = row.querySelector("div[class^='name-']");
      const vpEl   = row.querySelector("div[class^='victoryPoint-']");

      const name = nameEl?.textContent.trim();
      const vp   = vpEl?.textContent.trim();

      if (!name) continue;

      players.push({
        name,
        victoryPoints: vp ? parseInt(vp, 10) : null
      });
    }

    // ───────────────────────────────────────────────────────────────────────
    // Extract headers from icon filenames
    // ───────────────────────────────────────────────────────────────────────

    const headerIcons = [
      ...tabContent.querySelectorAll(
        "div[class*='headerContainer'] img"
      )
    ];

    const headers = headerIcons.map(img => {

      const src = img.getAttribute('src') || '';

      // Example:
      // stat_longest_road.7448547.svg

      const filename = src.split('/').pop() || '';

      let name = filename
        .replace(/\.[a-z0-9]+\.svg$/i, '')
        .replace(/\.svg$/i, '');

      // Normalize names

      if (name.startsWith('settlement')) {
        return 'settlements';
      }

      if (name.startsWith('city')) {
        return 'cities';
      }

      if (name.startsWith('stat_vp')) {
        return 'vp_breakdown';
      }

      if (name.startsWith('stat_largest_army')) {
        return 'largest_army';
      }

      if (name.startsWith('stat_longest_road')) {
        return 'longest_road';
      }

      if (name.startsWith('stat_mmr_change')) {
        return 'mmr_change';
      }

      return name
        .replace(/^stat_/, '')
        .replace(/[^a-z0-9_]/gi, '');
    });

    console.log('[Summary] Headers detected:', headers);

    // ───────────────────────────────────────────────────────────────────────
    // Stat rows
    // ───────────────────────────────────────────────────────────────────────

    const statRows = [
      ...tabContent.querySelectorAll("div[class^='rowContainer']")
    ];

    const statData = statRows
      .map(row => {

        const cells = [
          ...row.querySelectorAll("div.value-myGdPGIC")
        ];

        if (cells.length === 0) return null;

        const values = cells.map(c => c.textContent.trim());

        const obj = {};

        headers.forEach((header, i) => {
          obj[header] = values[i] ?? null;
        });

        return obj;

      })
      .filter(Boolean);

    // ───────────────────────────────────────────────────────────────────────
    // Merge player + stats
    // ───────────────────────────────────────────────────────────────────────

    return players.map((p, i) => ({
      ...p,
      ...(statData[i] || {})
    }));
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Find Virtual Scroller
  // ───────────────────────────────────────────────────────────────────────────

  const scroller = document.querySelector(SCROLLER_SEL);

  if (!scroller) {
    console.error('[GameLog] Could not find virtual scroller.');
    return;
  }

  let scrollContainer = scroller.parentElement;

  while (scrollContainer && scrollContainer !== document.body) {

    const style = getComputedStyle(scrollContainer);

    if (
      style.overflowY === 'auto' ||
      style.overflowY === 'scroll' ||
      style.overflowY === 'overlay'
    ) {
      break;
    }

    scrollContainer = scrollContainer.parentElement;
  }

  if (!scrollContainer || scrollContainer === document.body) {
    scrollContainer = scroller.parentElement;

    console.warn(
      '[GameLog] Could not detect scrollable parent, using fallback.'
    );
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Scroll + Harvest
  // ───────────────────────────────────────────────────────────────────────────

  const collected = new Map();

  function harvest() {

    document.querySelectorAll(ITEM_SEL).forEach(item => {

      const idx = parseInt(item.getAttribute('data-index'), 10);

      if (isNaN(idx)) return;

      const msgEl = item.querySelector(MSG_SEL);

      if (!msgEl) return;

      const text = messageToText(msgEl);

      if (
        !collected.has(idx) ||
        text.length > collected.get(idx).text.length
      ) {

        collected.set(idx, {
          index : idx,
          text,
          html  : msgEl.innerHTML
        });

      }

    });

  }

  console.log('[GameLog] Starting collection...');

  scrollContainer.scrollTop = 0;

  await sleep(FINAL_WAIT_MS);

  harvest();

  const maxScroll =
    scrollContainer.scrollHeight - scrollContainer.clientHeight;

  for (
    let pos = 0;
    pos <= maxScroll;
    pos += SCROLL_STEP_PX
  ) {

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
  // Build Outputs
  // ───────────────────────────────────────────────────────────────────────────

  const sortedItems = [...collected.values()]
    .sort((a, b) => a.index - b.index);

  if (sortedItems.length === 0) {

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

  // ───────────────────────────────────────────────────────────────────────────
  // Export JSON
  // ───────────────────────────────────────────────────────────────────────────

  const jsonFilename =
    `colonist_game_${timestamp}.json`;

  downloadFile(
    JSON.stringify(gameData, null, 2),
    jsonFilename,
    'application/json'
  );

  console.log(`[Export] JSON downloaded: ${jsonFilename}`);
  
  // ───────────────────────────────────────────────────────────────────────────
  // Save Globally
  // ───────────────────────────────────────────────────────────────────────────

  window.__colonistGameData = gameData;
  window.__colonistEvents = sortedItems;
  window.__colonistPlayers = players;

  // ───────────────────────────────────────────────────────────────────────────
  // Done
  // ───────────────────────────────────────────────────────────────────────────

  console.log(
    `[Done] ${sortedItems.length} events collected.`
  );

  console.log(
    `[Done] ${players.length} players collected.`
  );

  return gameData;

})();
