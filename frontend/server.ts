/**
 * Custom Next.js server with WebSocket proxy.
 *
 * Proxies /ws/** upgrade requests to python-api:8088/ws/**
 * Same code path for dev and prod — no env-specific routing.
 */

import { createServer } from "http";
import { parse } from "url";
import next from "next";
import httpProxy from "http-proxy";

const dev = process.env.NODE_ENV !== "production";
const app = next({ dev });
const handle = app.getRequestHandler();

const PYTHON_API = process.env.PYTHON_API_URL || "http://python-api:8088";

const proxy = httpProxy.createProxyServer({
  target: PYTHON_API,
  ws: true,
});

proxy.on("error", (err) => {
  console.error("[ws-proxy] error:", err.message);
});

app.prepare().then(() => {
  const server = createServer((req, res) => {
    const parsedUrl = parse(req.url!, true);
    handle(req, res, parsedUrl);
  });

  // Handle WebSocket upgrades
  server.on("upgrade", (req, socket, head) => {
    const { pathname } = parse(req.url!, true);
    if (pathname?.startsWith("/ws/")) {
      proxy.ws(req, socket, head);
    } else {
      socket.destroy();
    }
  });

  const port = parseInt(process.env.PORT || "3000", 10);
  server.listen(port, () => {
    console.log(`> Ready on http://localhost:${port}`);
  });
});
