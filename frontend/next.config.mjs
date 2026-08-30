/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Export a fully static build so a plain web server (or Laravel's public/)
  // can serve it without a Node runtime.
  output: "export",
  images: { unoptimized: true },

  // Where the exported site will be served from.
  //
  // Leave both empty when the app is deployed at the domain root. If the app
  // is hosted under a sub-path (e.g. https://example.com/dashboard), set both
  // to that path when building:
  //   NEXT_PUBLIC_BASE_PATH=/dashboard NEXT_PUBLIC_ASSET_PREFIX=/dashboard npm run build
  //
  // Do NOT hardcode a machine-local path (e.g. /dex-liquidity-predictor/public)
  // here — it bakes an absolute URL into every CSS/JS asset and breaks the UI
  // on any other host.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || "",
  assetPrefix: process.env.NEXT_PUBLIC_ASSET_PREFIX || "",
};

export default nextConfig;
