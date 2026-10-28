/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_ENABLE_CODE_PROTECTION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
