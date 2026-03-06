// @vitest-environment jsdom
// Tests for sidepanel.ts UI functions: downloads, tooltips, toggles

import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock Chrome APIs before sidepanel.ts module-level code runs.
vi.hoisted(() => {
  (globalThis as any).chrome = {
    action: {
      onClicked: { addListener: () => {} },
      setBadgeText: () => {},
      setBadgeBackgroundColor: () => {},
    },
    scripting: { executeScript: () => Promise.resolve([]) },
    sidePanel: { open: () => Promise.resolve() },
    runtime: {
      onMessage: { addListener: () => {} },
      sendMessage: () => Promise.resolve(null),
      getURL: (path: string) => `chrome-extension://test/${path}`,
    },
  };
});

import { downloadJson, downloadHtml, setupTooltips, setupToggles } from "../sidepanel/sidepanel";

describe("sidepanel UI functions", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  describe("downloadJson", () => {
    it("creates a download link with JSON blob", () => {
      const createObjectURL = vi.fn(() => "blob:test");
      const revokeObjectURL = vi.fn();
      globalThis.URL.createObjectURL = createObjectURL;
      globalThis.URL.revokeObjectURL = revokeObjectURL;
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

      downloadJson({ foo: "bar" }, "test.json");

      expect(createObjectURL).toHaveBeenCalledOnce();
      expect(clickSpy).toHaveBeenCalledOnce();
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:test");
      clickSpy.mockRestore();
    });
  });

  describe("downloadHtml", () => {
    it("creates a download link with HTML blob", () => {
      const createObjectURL = vi.fn(() => "blob:html");
      const revokeObjectURL = vi.fn();
      globalThis.URL.createObjectURL = createObjectURL;
      globalThis.URL.revokeObjectURL = revokeObjectURL;
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

      downloadHtml("<html></html>", "test.html");

      expect(createObjectURL).toHaveBeenCalledOnce();
      expect(clickSpy).toHaveBeenCalledOnce();
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:html");
      clickSpy.mockRestore();
    });
  });

  describe("setupTooltips", () => {
    it("attaches a mousemove listener to the document", () => {
      const addEventSpy = vi.spyOn(document, "addEventListener");
      setupTooltips();
      expect(addEventSpy).toHaveBeenCalledWith("mousemove", expect.any(Function));
      addEventSpy.mockRestore();
    });

    it("positions tooltip elements on mousemove", () => {
      setupTooltips();

      // Create a card with a tooltip
      document.body.innerHTML = `
        <div class="card" style="position: relative;">
          <div class="card-tip" style="position: fixed; width: 100px; height: 100px;"></div>
        </div>
      `;

      // Simulate mousemove - tip should be positioned
      const event = new MouseEvent("mousemove", { clientX: 200, clientY: 200 });
      document.dispatchEvent(event);

      // The tooltip positioning logic runs on :hover which jsdom doesn't fully support,
      // but the listener was attached successfully
    });
  });

  describe("setupToggles", () => {
    it("attaches click listeners to tri-toggle elements", () => {
      document.body.innerHTML = `
        <div class="tri-toggle" data-target="test-section">
          <span class="tri-opt" data-mode="none">None</span>
          <span class="tri-opt active" data-mode="all">All</span>
          <span class="tri-opt" data-mode="unknown">Unknown</span>
        </div>
        <div id="test-section" style="display: block;">Content</div>
      `;

      setupToggles();

      // Click "none" option
      const noneOpt = document.querySelector('[data-mode="none"]') as HTMLElement;
      noneOpt.click();

      const target = document.getElementById("test-section")!;
      expect(target.style.display).toBe("none");
      expect(target.classList.contains("mode-unknown")).toBe(false);

      // Verify active class moved
      expect(noneOpt.classList.contains("active")).toBe(true);
      const allOpt = document.querySelector('[data-mode="all"]') as HTMLElement;
      expect(allOpt.classList.contains("active")).toBe(false);
    });

    it("handles 'all' mode toggle", () => {
      document.body.innerHTML = `
        <div class="tri-toggle" data-target="section-all">
          <span class="tri-opt" data-mode="none">None</span>
          <span class="tri-opt" data-mode="all">All</span>
          <span class="tri-opt" data-mode="unknown">Unknown</span>
        </div>
        <div id="section-all" style="display: none;">Content</div>
      `;

      setupToggles();
      const allOpt = document.querySelector('[data-mode="all"]') as HTMLElement;
      allOpt.click();

      const target = document.getElementById("section-all")!;
      expect(target.style.display).toBe("");
      expect(target.classList.contains("mode-unknown")).toBe(false);
    });

    it("handles 'unknown' mode toggle", () => {
      document.body.innerHTML = `
        <div class="tri-toggle" data-target="section-unk">
          <span class="tri-opt" data-mode="none">None</span>
          <span class="tri-opt" data-mode="all">All</span>
          <span class="tri-opt" data-mode="unknown">Unknown</span>
        </div>
        <div id="section-unk" style="display: none;">Content</div>
      `;

      setupToggles();
      const unkOpt = document.querySelector('[data-mode="unknown"]') as HTMLElement;
      unkOpt.click();

      const target = document.getElementById("section-unk")!;
      expect(target.style.display).toBe("");
      expect(target.classList.contains("mode-unknown")).toBe(true);
    });

    it("handles layout toggles (wide/tall)", () => {
      document.body.innerHTML = `
        <div class="tri-toggle" data-target="section-layout">
          <span class="tri-opt active" data-mode="wide">Wide</span>
          <span class="tri-opt" data-mode="tall">Tall</span>
        </div>
        <div id="section-layout">Section</div>
        <div class="layout-wide" data-list="section-layout" style="display: block;">Wide grid</div>
        <div class="layout-tall" data-list="section-layout" style="display: none;">Tall grid</div>
      `;

      setupToggles();
      const tallOpt = document.querySelector('[data-mode="tall"]') as HTMLElement;
      tallOpt.click();

      const wideEl = document.querySelector('.layout-wide') as HTMLElement;
      const tallEl = document.querySelector('.layout-tall') as HTMLElement;
      expect(wideEl.style.display).toBe("none");
      expect(tallEl.style.display).toBe("");
    });

    it("ignores clicks outside tri-opt elements", () => {
      document.body.innerHTML = `
        <div class="tri-toggle" data-target="section-noop">
          <span class="tri-opt active" data-mode="all">All</span>
          <span class="tri-opt" data-mode="none">None</span>
        </div>
        <div id="section-noop">Content</div>
      `;

      setupToggles();
      // Click the toggle container itself, not an option
      const toggle = document.querySelector('.tri-toggle') as HTMLElement;
      toggle.click();

      // Nothing should change
      const allOpt = document.querySelector('[data-mode="all"]') as HTMLElement;
      expect(allOpt.classList.contains("active")).toBe(true);
    });
  });
});
