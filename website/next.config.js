/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/darkerdb/:path*",
        destination: "https://api.darkerdb.com/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
