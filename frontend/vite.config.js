import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite refuses any request whose Host header it does not recognise. That is the
// right default, and it is also why a tunnelled dev server answers "Blocked
// request. This host is not allowed." Tunnels mint a fresh hostname every run,
// so these are wildcards rather than a list; a leading dot matches subdomains.
const TUNNEL_HOSTS = [
  ".ngrok.app",
  ".ngrok-free.app",
  ".ngrok.io",
  ".trycloudflare.com",
];

// 5300 deliberately: blossom-fe and Surmount's own frontend both default to 4001.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5300,
    strictPort: true,
    host: "localhost",
    allowedHosts: TUNNEL_HOSTS,
  },
});
