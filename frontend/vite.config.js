import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const nm = path.resolve(__dirname, "node_modules");

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    fs: {
      allow: [repoRoot],
    },
  },
  resolve: {
    alias: {
      react: path.join(nm, "react"),
      "react/jsx-dev-runtime": path.join(nm, "react/jsx-dev-runtime.js"),
      "react-dom": path.join(nm, "react-dom"),
      "react-dom/client": path.join(nm, "react-dom/client"),
      "react-router-dom": path.join(nm, "react-router-dom"),
      "@testing-library/react": path.join(nm, "@testing-library/react"),
      "@testing-library/jest-dom": path.join(nm, "@testing-library/jest-dom"),
    },
  },
  test: {
    root: repoRoot,
    globals: true,
    environment: "jsdom",
    setupFiles: [path.join(__dirname, "vitest.setup.js")],
    include: ["tests/frontend/**/*.{test,spec}.{js,jsx}"],
  },
});
