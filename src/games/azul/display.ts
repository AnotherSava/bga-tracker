// Azul display options: shimmer toggle with localStorage persistence.

import { loadSetting, saveSetting } from "../../sidepanel/settings.js";

const KEY = "bgaa_azul_display";
const DEFAULTS = { shimmer: true };

type AzulDisplayState = typeof DEFAULTS;

export function buildAzulDisplayMenu(panel: HTMLElement): void {
  panel.innerHTML = "";

  const header = document.createElement("div");
  header.className = "dropdown-header";
  header.textContent = "Display options:";
  panel.appendChild(header);

  const state = loadSetting(KEY, DEFAULTS);
  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = state.shimmer;
  label.appendChild(checkbox);
  label.appendChild(document.createTextNode("Shimmer"));
  panel.appendChild(label);

  checkbox.addEventListener("change", () => {
    const current = loadSetting(KEY, DEFAULTS);
    current.shimmer = checkbox.checked;
    saveSetting(KEY, current);
    applyAzulDisplayOptions();
  });
}

export function applyAzulDisplayOptions(): void {
  const state = loadSetting(KEY, DEFAULTS);
  document.querySelectorAll<HTMLElement>(".azul-tile-icon").forEach((el) => {
    el.classList.toggle("shimmer-off", !state.shimmer);
  });
}
