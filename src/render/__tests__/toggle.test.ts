// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from "vitest";
import { positionTooltip, applyToggleMode } from "../toggle.js";
import { SUMMARY_JS } from "../../games/innovation/render.js";

describe("positionTooltip", () => {
  let tip: HTMLElement;

  beforeEach(() => {
    tip = document.createElement("div");
    document.body.appendChild(tip);
    // Default viewport: 1024x768
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: 768, writable: true, configurable: true });
  });

  it("positions tooltip offset from cursor", () => {
    // jsdom getBoundingClientRect returns all zeros; fallback widths 375/275 apply
    positionTooltip(tip, 100, 100);
    expect(tip.style.left).toBe("112px");
    expect(tip.style.top).toBe("112px");
  });

  it("flips to left of cursor when near right edge", () => {
    positionTooltip(tip, 900, 100);
    // 900 + 12 + 375 > 1024, so x = 900 - 375 - 12 = 513
    expect(tip.style.left).toBe("513px");
    expect(tip.style.top).toBe("112px");
  });

  it("flips above cursor when near bottom edge", () => {
    positionTooltip(tip, 100, 700);
    // 700 + 12 + 275 > 768, so y = 700 - 275 - 12 = 413
    expect(tip.style.left).toBe("112px");
    expect(tip.style.top).toBe("413px");
  });

  it("positions normally when tooltip fits within viewport", () => {
    positionTooltip(tip, 10, 10);
    // 10 + 12 + 375 > 1024? 397 < 1024, so no flip on x: x = 22
    // 10 + 12 + 275 > 768? 297 < 768, so no flip on y: y = 22
    expect(tip.style.left).toBe("22px");
    expect(tip.style.top).toBe("22px");
  });

  it("clamps to minimum 4px when flip goes negative", () => {
    // Near edge with small viewport
    Object.defineProperty(window, "innerWidth", { value: 100, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: 100, configurable: true });
    positionTooltip(tip, 50, 50);
    // 50 + 12 + 375 > 100, flip: 50 - 375 - 12 = -337 → clamped to 4
    // 50 + 12 + 275 > 100, flip: 50 - 275 - 12 = -237 → clamped to 4
    expect(tip.style.left).toBe("4px");
    expect(tip.style.top).toBe("4px");
  });
});

describe("applyToggleMode", () => {
  let container: HTMLElement;

  function buildToggle(targetId: string, modes: string[], activeMode?: string): HTMLElement {
    const toggle = document.createElement("span");
    toggle.className = "tri-toggle";
    toggle.setAttribute("data-target", targetId);
    for (const mode of modes) {
      const opt = document.createElement("span");
      opt.className = "tri-opt" + (mode === activeMode ? " active" : "");
      opt.setAttribute("data-mode", mode);
      opt.textContent = mode;
      toggle.appendChild(opt);
    }
    return toggle;
  }

  beforeEach(() => {
    document.body.innerHTML = "";
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  it("activates the correct tri-opt and deactivates others", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    document.body.appendChild(target);

    const toggle = buildToggle("test-section", ["all", "none"], "all");
    container.appendChild(toggle);

    applyToggleMode(toggle, "none", "test-section");

    const opts = toggle.querySelectorAll(".tri-opt");
    expect(opts[0].classList.contains("active")).toBe(false);
    expect(opts[1].classList.contains("active")).toBe(true);
  });

  it("hides target when mode is none", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    document.body.appendChild(target);

    const toggle = buildToggle("test-section", ["all", "none"]);
    container.appendChild(toggle);

    applyToggleMode(toggle, "none", "test-section");
    expect(target.style.display).toBe("none");
  });

  it("shows target and filters data-set children for composite modes", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    const baseDiv = document.createElement("div");
    baseDiv.setAttribute("data-set", "base");
    const echoesDiv = document.createElement("div");
    echoesDiv.setAttribute("data-set", "echoes");
    target.appendChild(baseDiv);
    target.appendChild(echoesDiv);
    document.body.appendChild(target);

    const toggle = buildToggle("test-section", ["base", "echoes", "none"]);
    container.appendChild(toggle);

    applyToggleMode(toggle, "echoes", "test-section");
    expect(target.style.display).toBe("");
    expect(baseDiv.style.display).toBe("none");
    expect(echoesDiv.style.display).toBe("");
  });

  it("toggles mode-unknown class for all/unknown modes", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    document.body.appendChild(target);

    const toggle = buildToggle("test-section", ["all", "unknown"]);
    container.appendChild(toggle);

    applyToggleMode(toggle, "unknown", "test-section");
    expect(target.classList.contains("mode-unknown")).toBe(true);

    applyToggleMode(toggle, "all", "test-section");
    expect(target.classList.contains("mode-unknown")).toBe(false);
  });

  it("switches wide/tall layout elements", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    document.body.appendChild(target);

    const wide = document.createElement("div");
    wide.className = "layout-wide";
    wide.setAttribute("data-list", "test-section");
    const tall = document.createElement("div");
    tall.className = "layout-tall";
    tall.setAttribute("data-list", "test-section");
    document.body.appendChild(wide);
    document.body.appendChild(tall);

    const toggle = buildToggle("test-section", ["wide", "tall"]);
    container.appendChild(toggle);

    applyToggleMode(toggle, "tall", "test-section");
    expect(wide.style.display).toBe("none");
    expect(tall.style.display).toBe("");

    applyToggleMode(toggle, "wide", "test-section");
    expect(wide.style.display).toBe("");
    expect(tall.style.display).toBe("none");
  });

  it("hides sibling toggles when primary toggle sets none", () => {
    const target = document.createElement("div");
    target.id = "test-section";
    document.body.appendChild(target);

    const primary = buildToggle("test-section", ["all", "none"]);
    const secondary = buildToggle("test-section", ["wide", "tall"]);
    container.appendChild(primary);
    container.appendChild(secondary);

    applyToggleMode(primary, "none", "test-section");
    expect(secondary.style.display).toBe("none");

    applyToggleMode(primary, "all", "test-section");
    expect(secondary.style.display).toBe("");
  });

  it("does nothing when target does not exist", () => {
    const toggle = buildToggle("nonexistent", ["all", "none"]);
    container.appendChild(toggle);
    // Should not throw
    applyToggleMode(toggle, "none", "nonexistent");
  });
});

describe("SUMMARY_JS", () => {
  it("is valid standalone JavaScript", () => {
    // new Function() parses the code; throws SyntaxError if invalid
    expect(() => new Function(SUMMARY_JS)).not.toThrow();
  });

  it("contains the serialized shared functions", () => {
    expect(SUMMARY_JS).toContain("positionTooltip");
    expect(SUMMARY_JS).toContain("applyToggleMode");
  });
});
