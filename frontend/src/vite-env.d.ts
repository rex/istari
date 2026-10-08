/// <reference types="vite/client" />

/** Injected at build time by `define` in vite.config.ts (version file and git commit). */
declare const __WEB_VERSION__: string;
declare const __WEB_COMMIT__: string;

declare module "*.module.css" {
  const classes: Readonly<Record<string, string>>;
  export default classes;
}
