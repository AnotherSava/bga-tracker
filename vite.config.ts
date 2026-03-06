import { defineConfig, type Plugin } from "vite";
import { resolve } from "path";

/**
 * Strip ES module export statements from extract.js output.
 * extract.ts is injected into BGA pages via chrome.scripting.executeScript
 * and must be a plain script (not an ES module). The last expression
 * (extractGameData()) returns a Promise whose resolved value becomes
 * the injection result.
 */
function stripExtractExports(): Plugin {
  return {
    name: "strip-extract-exports",
    generateBundle(_, bundle) {
      for (const [fileName, chunk] of Object.entries(bundle)) {
        if (fileName === "extract.js" && chunk.type === "chunk") {
          chunk.code = chunk.code.replace(/^export\s*\{[^}]*\}\s*;?\s*$/gm, "").trimEnd() + "\n";
        }
      }
    },
  };
}

export default defineConfig({
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: resolve(__dirname, "src/background.ts"),
        extract: resolve(__dirname, "src/extract.ts"),
        sidepanel: resolve(__dirname, "sidepanel.html"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },
    target: "es2022",
    minify: false,
    sourcemap: true,
  },
  plugins: [stripExtractExports()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  test: {
    globals: true,
    environment: "node",
    coverage: {
      include: ["src/**/*.ts"],
      exclude: ["src/__tests__/**"],
    },
  },
});
