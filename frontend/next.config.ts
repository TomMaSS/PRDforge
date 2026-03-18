import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://python-api:8088/api/:path*",
      },
      {
        source: "/health",
        destination: "http://python-api:8088/health",
      },
    ];
  },
};

export default nextConfig;
