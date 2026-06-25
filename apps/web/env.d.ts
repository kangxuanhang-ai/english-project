/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MINIO_ENDPOINT: string
  readonly VITE_SOCKET_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}