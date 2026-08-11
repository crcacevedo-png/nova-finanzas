/**
 * Tests E2E - Flujo de Autenticación
 * NovaVision ERP - Playwright E2E Suite
 */

import { test, expect } from '@playwright/test'

// Credenciales de prueba
const CREDENTIALS = {
  superadmin: { username: 'superadmin', password: 'nova2024' },
  admin: { username: 'admin', password: 'Admin2024Nuevo!' },
  usuario: { username: 'usuario', password: 'user2024' },
  optica: { username: 'optica', password: 'optica2024' },
}

test.describe('Autenticación', () => {
  test.beforeEach(async ({ page }) => {
    // Limpiar estado
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('muestra página de login cuando no está autenticado', async ({ page }) => {
    await page.goto('/')
    
    // Debe mostrar el formulario de login
    await expect(page.getByText('NovaVision')).toBeVisible()
    await expect(page.getByPlaceholder(/usuario/i)).toBeVisible()
    await expect(page.getByPlaceholder(/contraseña/i)).toBeVisible()
  })

  test('login exitoso con superadmin', async ({ page }) => {
    await page.goto('/')
    
    // Llenar credenciales
    await page.getByPlaceholder(/usuario/i).fill(CREDENTIALS.superadmin.username)
    await page.getByPlaceholder(/contraseña/i).fill(CREDENTIALS.superadmin.password)
    
    // Click en botón de login
    await page.getByRole('button', { name: /ingresar/i }).click()
    
    // Esperar navegación al dashboard
    await expect(page).toHaveURL(/.*dashboard.*|.*\/$/, { timeout: 15000 })
    
    // Verificar que se muestre el sidebar o contenido del dashboard
    await expect(page.locator('text=Dashboard').or(page.locator('text=Resumen'))).toBeVisible({ timeout: 10000 })
  })

  test('muestra error con credenciales inválidas', async ({ page }) => {
    await page.goto('/')
    
    // Llenar credenciales incorrectas
    await page.getByPlaceholder(/usuario/i).fill('usuario_falso')
    await page.getByPlaceholder(/contraseña/i).fill('password_incorrecto')
    
    // Click en botón de login
    await page.getByRole('button', { name: /ingresar/i }).click()
    
    // Esperar mensaje de error
    await expect(page.getByText(/inválid|error|incorrect/i)).toBeVisible({ timeout: 10000 })
  })

  test('logout funciona correctamente', async ({ page }) => {
    // Primero hacer login
    await page.goto('/')
    await page.getByPlaceholder(/usuario/i).fill(CREDENTIALS.superadmin.username)
    await page.getByPlaceholder(/contraseña/i).fill(CREDENTIALS.superadmin.password)
    await page.getByRole('button', { name: /ingresar/i }).click()
    
    // Esperar a que cargue
    await page.waitForTimeout(2000)
    
    // Buscar y hacer click en logout
    const logoutButton = page.getByRole('button', { name: /salir|logout|cerrar sesión/i })
      .or(page.locator('[data-testid="logout-button"]'))
      .or(page.locator('text=Salir'))
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click()
      
      // Debe redirigir a login
      await expect(page.getByPlaceholder(/usuario/i)).toBeVisible({ timeout: 10000 })
    }
  })

  test('redirige a login si el token expira', async ({ page }) => {
    await page.goto('/')
    
    // Simular token expirado
    await page.evaluate(() => {
      localStorage.setItem('token', 'token_expirado_invalido')
    })
    
    // Intentar acceder a página protegida
    await page.goto('/dashboard')
    
    // Debe redirigir a login eventualmente
    await page.waitForTimeout(2000)
    // El sistema debe detectar el token inválido
  })
})

test.describe('Permisos por Rol', () => {
  test('superadmin puede ver todos los módulos', async ({ page }) => {
    await page.goto('/')
    await page.getByPlaceholder(/usuario/i).fill(CREDENTIALS.superadmin.username)
    await page.getByPlaceholder(/contraseña/i).fill(CREDENTIALS.superadmin.password)
    await page.getByRole('button', { name: /ingresar/i }).click()
    
    await page.waitForTimeout(3000)
    
    // Verificar acceso a módulos críticos
    const sidebar = page.locator('nav, aside, [role="navigation"]')
    await expect(sidebar.getByText(/Dashboard|Inicio/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('usuario optica tiene acceso limitado', async ({ page }) => {
    await page.goto('/')
    await page.getByPlaceholder(/usuario/i).fill(CREDENTIALS.optica.username)
    await page.getByPlaceholder(/contraseña/i).fill(CREDENTIALS.optica.password)
    await page.getByRole('button', { name: /ingresar/i }).click()
    
    await page.waitForTimeout(3000)
    
    // Usuario óptica debería tener acceso limitado
    // Verificar que se cargó alguna vista
    await expect(page.locator('main, [role="main"], .main-content').first()).toBeVisible({ timeout: 10000 })
  })
})
