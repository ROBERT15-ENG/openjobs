import type { NextConfig } from "next";

const LEGACY_BASE =
  process.env.NEXT_PUBLIC_LEGACY_BASE ?? "http://localhost:5700";

const nextConfig: NextConfig = {
  // Admin stays on the legacy Flask app — forward anyone who lands here.
  async redirects() {
    return [
      {
        source: "/admin",
        destination: `${LEGACY_BASE}/admin`,
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
