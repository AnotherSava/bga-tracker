import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const thisDir = dirname(fileURLToPath(import.meta.url));

describe("smoke tests", () => {
  it("imports from models/types without errors", async () => {
    const module = await import("../models/types");
    expect(module).toBeDefined();
  });

  it("imports from engine/process_log without errors", async () => {
    const module = await import("../engine/process_log");
    expect(module).toBeDefined();
  });

  it("imports from engine/game_state without errors", async () => {
    const module = await import("../engine/game_state");
    expect(module).toBeDefined();
  });

  it("imports from render/summary without errors", async () => {
    const module = await import("../render/summary");
    expect(module).toBeDefined();
  });

  it("imports from render/config without errors", async () => {
    const module = await import("../render/config");
    expect(module).toBeDefined();
  });

  it("loads card_info.json asset", () => {
    const cardInfoPath = resolve(thisDir, "../../assets/bga/innovation/card_info.json");
    const data = JSON.parse(readFileSync(cardInfoPath, "utf-8"));
    expect(data).toBeDefined();
    expect(Array.isArray(data) || typeof data === "object").toBe(true);
  });

  it("verifies build output exists after vite build", () => {
    const distDir = resolve(thisDir, "../../dist");
    expect(existsSync(resolve(distDir, "background.js"))).toBe(true);
    expect(existsSync(resolve(distDir, "extract.js"))).toBe(true);
    expect(existsSync(resolve(distDir, "sidepanel.html"))).toBe(true);
  });
});
