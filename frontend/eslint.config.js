// Configuración de ESLint 9 (flat) mínima y SIN dependencias externas.
// Solo parseamos el código (JS/JSX) sin plugins ni reglas para evitar
// cualquier fallo del motor del linter en distintos entornos.
module.exports = [
  {
    ignores: [
      '**/node_modules/**',
      'eslint.config.js',
      'build/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
    ],
  },
  {
    files: ['**/*.{js,jsx,cjs,mjs}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {},
  },
];
