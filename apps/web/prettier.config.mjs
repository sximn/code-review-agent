/** @type {import("prettier").Config} */
const config = {
  plugins: ["prettier-plugin-tailwindcss"],
  semi: true,
  tailwindFunctions: ["cn", "cva"],
  tailwindStylesheet: "./app/globals.css",
};

export default config;
