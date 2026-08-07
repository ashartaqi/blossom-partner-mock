import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 5300 deliberately: blossom-fe and Surmount's own frontend both default to 4001.
export default defineConfig({
  plugins: [react()],
  server: { port: 5300, strictPort: true, host: "localhost" },
});
