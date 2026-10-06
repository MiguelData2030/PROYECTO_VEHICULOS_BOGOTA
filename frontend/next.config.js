/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static site (HTML/JS only): hosted as a free static site on Render
  output: 'export',
  trailingSlash: true,
  images: {
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: '**.supabase.co' },
      { protocol: 'https', hostname: '**.onrender.com' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
    ],
    unoptimized: true,
  },
};

module.exports = nextConfig;
