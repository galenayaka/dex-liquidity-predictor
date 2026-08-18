/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Export a fully static build so Apache (via Laravel's public/) can serve it.
  output: "export",
  // The app is served from the Laravel public folder subpath.
  assetPrefix: "/dex-liquidity-predictor/public",
  images: { unoptimized: true },
};

export default nextConfig;
