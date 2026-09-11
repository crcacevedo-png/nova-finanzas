// Configuración raíz de ESLint 9 (flat). El linter a veces se ejecuta desde /app,
// por lo que aquí solo cubrimos el frontend y resolvemos los plugins desde
// frontend/node_modules. Todo lo demás (backend, docs, tests, etc.) se ignora.
const path = require('path');
const FE = path.join(__dirname, 'frontend', 'node_modules');
const js = require(path.join(FE, '@eslint', 'js'));
const globals = require(path.join(FE, 'globals'));
const reactPlugin = require(path.join(FE, 'eslint-plugin-react'));
const reactHooks = require(path.join(FE, 'eslint-plugin-react-hooks'));

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
    ],
  },
  js.configs.recommended,
  {
    files: ['frontend/**/*.{js,jsx,cjs,mjs}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
        vi: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
      },
    },
    plugins: { react: reactPlugin, 'react-hooks': reactHooks },
    settings: { react: { version: 'detect' } },
    rules: {
      'no-unused-vars': 'off',
      'no-undef': 'off',
      'react/prop-types': 'off',
      'react/react-in-jsx-scope': 'off',
      'react/no-unescaped-entities': 'off',
      'react/display-name': 'off',
      'no-empty': 'off',
      'no-useless-escape': 'off',
      'no-constant-condition': 'off',
      'no-control-regex': 'off',
    },
  },
];
