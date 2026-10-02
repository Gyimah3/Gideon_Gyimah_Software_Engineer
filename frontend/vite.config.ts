import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Lets the dev UI call the API on :8000 without CORS concerns in the browser.
    proxy: { "/api": "http://127.0.0.1:8010" },
  },
});
