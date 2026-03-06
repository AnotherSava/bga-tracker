// Side panel: receives data from background, renders summary, handles downloads.

import { renderSummary, renderFullPage, setAssetResolver } from "../render/summary.js";
import { CardDatabase } from "../models/types.js";
import { GameState } from "../engine/game_state.js";
import type { PipelineResults } from "../background.js";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentResults: PipelineResults | null = null;
let currentCss: string | null = null;

// ---------------------------------------------------------------------------
// Asset URL resolution for Chrome extension context
// ---------------------------------------------------------------------------

if (typeof chrome !== "undefined" && chrome.runtime?.getURL) {
  setAssetResolver((path: string) => chrome.runtime.getURL(path));
}

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------

function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadHtml(html: string, filename: string): void {
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Tooltip positioning (mouse-follow)
// ---------------------------------------------------------------------------

let tooltipsInitialized = false;

function setupTooltips(): void {
  if (tooltipsInitialized) return;
  tooltipsInitialized = true;
  document.addEventListener("mousemove", (e: MouseEvent) => {
    const tips = document.querySelectorAll<HTMLElement>(".card:hover > .card-tip, .card:hover > .card-tip-text");
    tips.forEach((tip) => {
      const rect = tip.getBoundingClientRect();
      const w = rect.width || 375;
      const h = rect.height || 275;
      let x = e.clientX + 12;
      let y = e.clientY + 12;
      if (x + w > window.innerWidth) x = e.clientX - w - 12;
      if (y + h > window.innerHeight) y = e.clientY - h - 12;
      if (x < 0) x = 4;
      if (y < 0) y = 4;
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    });
  });
}

// ---------------------------------------------------------------------------
// Toggle handlers (visibility + layout)
// ---------------------------------------------------------------------------

function setupToggles(): void {
  document.querySelectorAll<HTMLElement>(".tri-toggle").forEach((toggle) => {
    toggle.addEventListener("click", (e: Event) => {
      const opt = (e.target as HTMLElement).closest(".tri-opt") as HTMLElement | null;
      if (!opt) return;
      const mode = opt.getAttribute("data-mode");
      const targetId = toggle.getAttribute("data-target");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target || !mode) return;

      toggle.querySelectorAll(".tri-opt").forEach((o) => o.classList.remove("active"));
      opt.classList.add("active");

      if (mode === "none") {
        target.style.display = "none";
        target.classList.remove("mode-unknown");
      } else if (mode === "all") {
        target.style.display = "";
        target.classList.remove("mode-unknown");
      } else if (mode === "unknown") {
        target.style.display = "";
        target.classList.add("mode-unknown");
      } else if (mode === "wide" || mode === "tall") {
        document.querySelectorAll<HTMLElement>(`.layout-wide[data-list="${targetId}"]`).forEach((el) => {
          el.style.display = mode === "wide" ? "" : "none";
        });
        document.querySelectorAll<HTMLElement>(`.layout-tall[data-list="${targetId}"]`).forEach((el) => {
          el.style.display = mode === "tall" ? "" : "none";
        });
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function render(results: PipelineResults): void {
  const contentEl = document.getElementById("content")!;
  const toolbarEl = document.getElementById("toolbar")!;

  const cardInfoUrl = typeof chrome !== "undefined" && chrome.runtime?.getURL
    ? chrome.runtime.getURL("assets/card_info.json")
    : "assets/card_info.json";
  fetchCardDb(cardInfoUrl).then((db) => {
    renderWithDb(db, results, contentEl, toolbarEl);
  }).catch(() => {
    contentEl.innerHTML = '<div class="status">Error loading card database</div>';
  });
}

async function fetchCardDb(url: string): Promise<CardDatabase> {
  const response = await fetch(url);
  const data = await response.json();
  return new CardDatabase(data);
}

function renderWithDb(cardDb: CardDatabase, results: PipelineResults, contentEl: HTMLElement, toolbarEl: HTMLElement): void {
  const { gameLog, gameState: serializedState } = results;

  // Reconstruct GameState from serialized form
  const players = Object.keys(serializedState.hands);
  const perspective = gameLog.currentPlayerId && gameLog.players[gameLog.currentPlayerId] ? gameLog.players[gameLog.currentPlayerId] : players[0];
  const gameState = GameState.fromJSON(serializedState, cardDb, players, perspective);
  const tableId = "game";

  // Render summary HTML
  const summaryHtml = renderSummary(gameState, cardDb, perspective, players, tableId);
  contentEl.innerHTML = summaryHtml;

  // Show toolbar
  toolbarEl.style.display = "flex";

  // Set up interactivity
  setupTooltips();
  setupToggles();

  // Cache CSS for downloads
  loadCss();

  // Wire download buttons (use onclick to replace any previous handler on re-render)
  const btnGameLog = document.getElementById("btn-game-log");
  if (btnGameLog) btnGameLog.onclick = () => { downloadJson(gameLog, "game_log.json"); };

  const btnGameState = document.getElementById("btn-game-state");
  if (btnGameState) btnGameState.onclick = () => { downloadJson(serializedState, "game_state.json"); };

  const btnSummary = document.getElementById("btn-summary");
  if (btnSummary) btnSummary.onclick = () => {
    const css = currentCss ?? "";
    // Use relative asset paths for standalone HTML (chrome-extension:// URLs don't work outside the extension)
    setAssetResolver((path: string) => path);
    try {
      const fullHtml = renderFullPage(gameState, cardDb, perspective, players, tableId, css);
      downloadHtml(fullHtml, "summary.html");
    } finally {
      if (typeof chrome !== "undefined" && chrome.runtime?.getURL) {
        setAssetResolver((path: string) => chrome.runtime.getURL(path));
      }
    }
  };
}

async function loadCss(): Promise<void> {
  if (currentCss !== null) return;
  try {
    const sheets = document.styleSheets;
    let css = "";
    for (let i = 0; i < sheets.length; i++) {
      try {
        const rules = sheets[i].cssRules;
        for (let j = 0; j < rules.length; j++) {
          css += rules[j].cssText + "\n";
        }
      } catch {
        // Cross-origin stylesheet, skip
      }
    }
    currentCss = css;
  } catch {
    currentCss = "";
  }
}

// ---------------------------------------------------------------------------
// Message listener
// ---------------------------------------------------------------------------

if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
  // Request data from background on load
  chrome.runtime.sendMessage({ type: "getResults" }).then((response: PipelineResults | null) => {
    if (response) {
      currentResults = response;
      render(response);
    }
  }).catch(() => {
    document.getElementById("content")!.innerHTML = '<div class="status">Connection lost. Click the extension icon to re-extract.</div>';
  });

  // Listen for pushed updates when re-extraction occurs while panel is open
  chrome.runtime.onMessage.addListener((message: { type: string }) => {
    if (message.type === "resultsReady") {
      chrome.runtime.sendMessage({ type: "getResults" }).then((response: PipelineResults | null) => {
        if (response) {
          currentResults = response;
          render(response);
        }
      }).catch(() => {
        document.getElementById("content")!.innerHTML = '<div class="status">Connection lost. Click the extension icon to re-extract.</div>';
      });
    }
    return undefined;
  });
}

// Export for testing
export { render, setupTooltips, setupToggles, downloadJson, downloadHtml, fetchCardDb };
