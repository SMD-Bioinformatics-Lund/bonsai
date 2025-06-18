import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";


export default defineConfig([
  { files: ["frontend/web/**/*.{js,mjs,cjs,ts}"] },
  tseslint.configs.recommended
]);