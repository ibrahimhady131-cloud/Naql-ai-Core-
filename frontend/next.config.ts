import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    process.env.REPLIT_DEV_DOMAIN ?? "",
    "*.replit.dev",
    "*.picard.replit.dev",
    "*.spock.replit.dev",
  ].filter(Boolean),
};

export default nextConfig;
