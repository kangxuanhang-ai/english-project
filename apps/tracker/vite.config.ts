import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import dts from 'vite-plugin-dts'
export default defineConfig({
  plugins: [
    dts({
      outDir: 'dist', //输出目录
      entryRoot: '.' //入口根目录
    })
  ],
  build: {
    minify: true, //压缩
    outDir: 'dist', //输出目录
    emptyOutDir: true, //清空输出目录
    sourcemap: false, //生成源映射
    lib: {
      entry: 'index.ts', //入口文件
      name: 'tracker', //库名称
      fileName: 'tracker', //文件名
      formats: ['es', 'cjs', 'umd', 'iife'] //格式
    },
  },
  server: {
    proxy: {
      '/api': {
        target: `http://localhost:3000`,
        changeOrigin: true
      },
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})