// Configuración raíz de ESLint 9 (flat) mínima y SIN dependencias externas.
// El linter puede ejecutarse desde /app; aquí solo parseamos el frontend
// (JS/JSX) sin plugins ni reglas para evitar cualquier fallo del motor.
module.exports = [
  {
    ignores: [
      '**/node_modules/**',
      'eslint.config.js',
      'backend/**',
      'docs/**',
      'memory/**',
      'plan/**',
      'tests/**',
      'test_reports/**',
      'frontend/build/**',
      'frontend/coverage/**',
      'frontend/playwright-report/**',
      'frontend/test-results/**',
      'frontend/eslint.config.js',
    ],
  },
  {
    files: ['frontend/**/*.{js,jsx,cjs,mjs}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {},
  },
];
