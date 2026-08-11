/**
 * Configuración de Playwright para E2E Testing
 * NovaVision ERP - Suite de Testing End-to-End
 */

import { defineConfig, devices } from '@playwright/test'

// URL base de la aplicación (usa variable de entorno o default)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
const apiURL = process.env.PLAYWRIGHT_API_URL || 'http://localhost:8001'

export default defineConfig({
  // Directorio de tests E2E
  testDir: './tests/e2e',
  
  // Configuración de ejecución
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  // Reporters
  reporter: [
    ['list'],
    ['html', { outputFolder: '../test_reports/playwright/html' }],
    ['json', { outputFile: '../test_reports/playwright/results.json' }],
  ],
  
  // Configuración global de tests
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Timeouts
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Viewport estándar
    viewport: { width: 1920, height: 1080 },
    
    // Ignorar HTTPS errors en desarrollo
    ignoreHTTPSErrors: true,
  },
  
  // Proyectos de browser
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Tests para dispositivos móviles
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
    // Tablet para POS (importante para NovaVision)
    {
      name: 'tablet',
      use: { ...devices['iPad Pro 11'] },
    },
  ],
  
  // Timeouts globales
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  
  // Output
  outputDir: '../test_reports/playwright/artifacts',
  
  // No usar webServer automático en este entorno (ya está corriendo via supervisor)
  // webServer: {
  //   command: 'yarn start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
})
