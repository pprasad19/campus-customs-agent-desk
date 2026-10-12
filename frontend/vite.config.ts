import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// npm run dev opens the desk in the browser on http://localhost:5173,
// which is the origin the backend allows in its CORS settings.
export default defineConfig({
  plugins: [react()],
  server: {
    // Prefer 5173, the origin the backend allows by default. If something else
    // already holds it, Vite steps to 5174 or 5175, which the backend also
    // allows, rather than refusing to start.
    port: 5173,
    strictPort: false,
    open: true,
  },
});
