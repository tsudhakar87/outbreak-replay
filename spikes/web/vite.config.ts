import { defineConfig } from "vite";

export default defineConfig({
  // WASM requires SharedArrayBuffer which needs cross-origin isolation headers
  plugins: [
    {
      name: "cross-origin-isolation",
      configureServer(server) {
        server.middlewares.use((_req, res, next) => {
          res.setHeader("Cross-Origin-Opener-Policy", "same-origin");
          res.setHeader("Cross-Origin-Embedder-Policy", "require-corp");
          next();
        });
      },
    },
  ],
  optimizeDeps: {
    exclude: ["@relate/relate-wasm"],
  },
  worker: {
    format: "es",
  },
});
