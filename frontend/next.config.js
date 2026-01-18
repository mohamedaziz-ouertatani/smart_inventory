/** @type {import('next').NextConfig} */
const nextConfig = {
  // ...other config,
  turbopack: {
    root: __dirname, // use this directory as the workspace root
  },
};
module.exports = nextConfig;
