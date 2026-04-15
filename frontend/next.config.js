/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: [
    process.env.REPLIT_DEV_DOMAIN || "",
    "*.replit.dev",
    "*.picard.replit.dev",
    "*.spock.replit.dev",
  ].filter(Boolean),
};

module.exports = nextConfig;
