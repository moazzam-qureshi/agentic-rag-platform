import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produce a minimal self-contained server bundle in .next/standalone.
  // The Docker runtime stage copies just that + the public/ + .next/static.
  output: "standalone",

  // In production we sit behind Coolify's Traefik; the API and web share a
  // domain. NEXT_PUBLIC_API_BASE_URL is used at build time for the client
  // and left empty in production (relative URLs hit the same origin).
};

export default nextConfig;
