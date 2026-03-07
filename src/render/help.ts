// Help page content for the side panel.

export function renderHelp(notAGameUrl?: string): string {
  const notAGameNote = notAGameUrl !== undefined
    ? `<div class="help-note"><span class="help-note-icon">&#x26A0;</span> This page is not a BGA Innovation game.<br><span class="help-note-hint">Navigate to an Innovation table on <a href="https://boardgamearena.com" target="_blank">boardgamearena.com</a> and click the extension icon.</span></div>`
    : "";

  return `${notAGameNote}
<div class="help">
  <div class="help-hero">
    <div class="help-hero-title">BGA Assistant</div>
    <div class="help-hero-sub">Game assistant for <a href="https://boardgamearena.com" target="_blank">Board Game Arena</a></div>
  </div>

  <p>Turn-based games on BGA can stretch across days or weeks. By the time it's your turn,
  you may have forgotten what was drawn, returned, transferred, or scored several moves ago.</p>
  <p>BGA Assistant reads the game log and reconstructs the complete game state for you —
  deck stack order, hand contents, score piles — so you can focus
  on strategy instead of trying to remember what happened.</p>

  <div class="help-section">
    <div class="help-section-title">How to use</div>
    <ol class="help-steps">
      <li>Open an Innovation game on <a href="https://boardgamearena.com" target="_blank">BGA</a></li>
      <li>Click the extension icon in your toolbar</li>
      <li>The side panel opens with the game summary</li>
    </ol>
  </div>

  <div class="help-section">
    <div class="help-section-title">Top bar</div>
    <div class="help-sections-grid">
      <div class="help-grid-item"><span class="help-grid-label"><span class="help-btn"><svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg></span> <span class="help-btn"><svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg></span></span><span> Zoom out / in (also <b>Ctrl</b>+<b>\u2212</b> / <b>Ctrl</b>+<b>=</b>)</span></div>
      <div class="help-grid-item"><span class="help-grid-label"><span class="help-btn"><svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg></span></span><span> Download a zip archive with raw packets, game log, game state, and summary page</span></div>
      <div class="help-grid-item"><span class="help-grid-label"><span class="help-btn help-btn-text">?</span></span><span> This help page</span></div>
    </div>
  </div>

  <div class="help-section">
    <div class="help-section-title">Sections</div>
    <div class="help-sections-grid">
      <div class="help-grid-item"><span class="help-grid-label">Hands</span> Your cards and what your opponent knows about them, and vice versa</div>
      <div class="help-grid-item"><span class="help-grid-label">Scores</span> Same for the score piles</div>
      <div class="help-grid-item"><span class="help-grid-label">Decks</span> Cards remaining in each deck, in draw order — including information on returned cards</div>
      <div class="help-grid-item"><span class="help-grid-label">Achievements</span> What cards were sidelined as standard achievements for ages 1–8</div>
      <div class="help-grid-item"><span class="help-grid-label">Card lists</span> Full list of all cards, highlighting ones still unknown</div>
    </div>
  </div>

  <div class="help-section">
    <div class="help-section-title">Visibility toggles</div>
    <div class="help-sections-grid">
      <div class="help-grid-item"><span class="help-grid-label">Hide</span> Collapse the section entirely</div>
      <div class="help-grid-item"><span class="help-grid-label">Show</span> Display all cards in the section</div>
      <div class="help-grid-item"><span class="help-grid-label">Unknown</span> Only show cards the opponent doesn't know you know</div>
    </div>
  </div>

  <div class="help-section">
    <div class="help-section-title">Layout toggles</div>
    <div class="help-sections-grid">
      <div class="help-grid-item"><span class="help-grid-label">Wide</span> One horizontal row per age</div>
      <div class="help-grid-item"><span class="help-grid-label">Tall</span> Columnar grid grouped by color</div>
    </div>
  </div>

  <div class="help-section">
    <div class="help-section-title">Card tooltips</div>
    <div class="help-sections-grid">
      <div class="help-grid-item">Hover over any known base card to see its full card image; cities cards show their name</div>
    </div>
  </div>
</div>`;
}

