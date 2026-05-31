import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// GitHub Pages 배포 시 BASE_PATH=/<repo-name>/ 형태로 주입.
// 사용자 정의 도메인을 쓰는 경우 BASE_PATH=/ (기본).
const base = process.env.BASE_PATH || "/";

export default defineConfig({
  base,
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  server: {
    port: 5173,
  },
});
