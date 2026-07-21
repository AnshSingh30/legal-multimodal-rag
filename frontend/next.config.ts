import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo root has an unrelated stray package-lock.json from outside this
  // frontend (see project root) that otherwise makes Turbopack infer the
  // wrong workspace root. Pin it explicitly to this directory.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
