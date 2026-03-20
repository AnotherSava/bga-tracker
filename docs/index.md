---
layout: default
title: BGA Assistant
---

[Innovation](pages/innovation) | [Azul](pages/azul) | [Crew](pages/crew) | [Development](pages/development)

---

A Chrome extension for [Board Game Arena](https://boardgamearena.com) that keeps track of the game state so you don't have to. Turn-based games on BGA can stretch across days or weeks — by the time it's your turn, you may have forgotten what was drawn, returned, transferred, or scored several moves ago. BGA Assistant reads the game log and reconstructs the complete picture for you.

## Install

[Install from Chrome Web Store](#) *(coming soon)*

## Supported Games

### [Innovation](pages/innovation)

Reads the full game log from [Innovation](https://boardgamegeek.com/boardgame/63888/innovation) 2-player tables and reconstructs the game state — hand contents and score piles according to revealed cards, and deck stack order with returned cards — displayed as a visual summary in a side panel. Supports the base game and the Echoes of the Past and Cities of Destiny expansions.

<a href="screenshots/innovation-hand.png"><img src="screenshots/innovation-hand.png" alt="Innovation hand and forecast tracking" width="460"></a>

### [Azul](pages/azul)

Tracks the tile bag and discard pile (box lid) for [Azul](https://boardgamegeek.com/boardgame/230802/azul) tables with any player count. Particularly helpful in 2-player games where the full bag is depleted in exactly 5 rounds. Displays remaining tile counts per color in a compact table so you always know what's left to draw.

<a href="screenshots/azul.png"><img src="screenshots/azul.png" alt="Azul tile counts" width="475"></a>

### [The Crew: Mission Deep Sea](pages/crew)

Tracks played cards and communication signals to deduce remaining cards in players' hands for [The Crew: Mission Deep Sea](https://boardgamegeek.com/boardgame/324856/the-crew-mission-deep-sea) tables with any player count. The side panel displays three sections — a card grid, a player-suit matrix, and a trick history — all updating live as cards are played.

<a href="screenshots/crew-cards.png"><img src="screenshots/crew-cards.png" alt="Crew card grid" width="152"></a>

## Usage

1. Navigate to a supported BGA game page in Chrome — the toolbar icon brightens up to indicate a supported game is detected
2. Click the BGA Assistant icon in the toolbar (or use a keyboard shortcut if configured via `chrome://extensions/shortcuts`)
3. The side panel opens with a visual summary of the game state
4. While viewing a game, the side panel automatically updates when the game progresses — a green dot in the status bar indicates active tracking
5. Switching to another supported game tab automatically updates the display
6. Use the auto-hide button in the side panel to choose when the panel closes — never, when leaving BGA, or when leaving game tables
7. Use the download button to save a zip with game data and a standalone summary
8. Click the ? icon for a built-in help page with a detailed guide on each game's sections, toggles, and controls

<a href="screenshots/help.png"><img src="screenshots/help.png" alt="Built-in help page" width="587"></a>

## Acknowledgments

Card icons and images are from [bga-innovation](https://github.com/micahstairs/bga-innovation), Micah Stairs' BGA implementation of [Innovation](https://boardgamegeek.com/boardgame/63888/innovation) (Carl Chudyk, Asmadi Games). Tile sprites are from BGA's implementation of [Azul](https://boardgamegeek.com/boardgame/230802/azul) (Michael Kiesling, Plan B Games).
