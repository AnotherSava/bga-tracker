import { describe, it, expect, beforeEach } from "vitest";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { Card, CardDatabase, cardIndex } from "../types";
import { GameState } from "../game_state";
import { renderSummary } from "../render";

const thisDir = dirname(fileURLToPath(import.meta.url));

function loadCardDatabase(): CardDatabase {
  const path = resolve(thisDir, "../../../../assets/bga/innovation/card_info.json");
  const raw = JSON.parse(readFileSync(path, "utf-8"));
  return new CardDatabase(raw);
}

const PLAYERS = ["Alice", "Bob"];
const PERSPECTIVE = "Alice";

let cardDb: CardDatabase;

beforeEach(() => {
  cardDb = loadCardDatabase();
});

// ---------------------------------------------------------------------------
// bug: forecast cards shown as unresolved in Cards section
// ---------------------------------------------------------------------------

describe("bug: forecast cards shown as unresolved in Cards section", () => {
  it("marks forecast cards as resolved (data-known) in the Cards section", () => {
    const gs = new GameState(cardDb, PLAYERS, PERSPECTIVE);
    gs.initGame();

    // Place Sanitation directly into Alice's forecast
    const sanInfo = cardDb.get(cardIndex("sanitation"))!;
    const sanCard = new Card(sanInfo.age, sanInfo.cardSet, [cardIndex("sanitation")]);
    gs.forecast.get(PERSPECTIVE)!.push(sanCard);

    const html = renderSummary(gs, cardDb, PERSPECTIVE, PLAYERS, "test", { textTooltips: true });

    // In the Cards section, find the card div containing "Sanitation"
    const cardsSection = html.match(/data-section="cards"[\s\S]*?(?=<div class="section"|$)/);
    expect(cardsSection).not.toBeNull();

    // The Sanitation card within the Cards section should have data-known
    const cardsSectionHtml = cardsSection![0];
    expect(cardsSectionHtml).toContain("Sanitation");

    // Extract the card div that contains Sanitation's name
    const sanCardMatch = cardsSectionHtml.match(/<div class="card[^"]*"[^>]*>(?:[^<]|<(?!\/div><div class="card))*Sanitation/);
    expect(sanCardMatch).not.toBeNull();
    expect(sanCardMatch![0]).toContain("data-known");
  });
});
