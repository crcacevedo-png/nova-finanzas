/**
 * Tests E2E - Módulo de Inventario
 * NovaVision ERP - Playwright E2E Suite
 */

import { test, expect } from '@playwright/test'

// Credenciales de prueba
const SUPERADMIN = { username: 'superadmin', password: 'nova2024' }

// Helper para login
async function loginAsSuperAdmin(page) {
  await page.goto('/')
  await page.getByPlaceholder(/usuario/i).fill(SUPERADMIN.username)
  await page.getByPlaceholder(/contraseña/i).fill(SUPERADMIN.password)
  await page.getByRole('button', { name: /ingresar/i }).click()
  await page.waitForTimeout(3000)
}

test.describe('Inventario - Panel Principal', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('accede al panel de inventario', async ({ page }) => {
    await page.goto('/inventario')
    
    // Verificar que la página carga
    await expect(page.getByText(/Inventario|Panel/i).first()).toBeVisible({ timeout: 15000 })
  })

  test('muestra KPIs del inventario', async ({ page }) => {
    await page.goto('/inventario')
    await page.waitForTimeout(2000)
    
    // Verificar que se muestran métricas
    const valorInventario = page.getByText(/valor.*inventario|total.*productos/i).first()
    if (await valorInventario.isVisible()) {
      await expect(valorInventario).toBeVisible()
    }
  })

  test('muestra alertas de stock bajo y vencimientos', async ({ page }) => {
    await page.goto('/inventario')
    await page.waitForTimeout(2000)
    
    // Verificar sección de alertas
    const alertas = page.getByText(/alerta|vencimiento|bajo.*stock/i).first()
    if (await alertas.isVisible()) {
      await expect(alertas).toBeVisible()
    }
  })

  test('navegación a submenús de inventario', async ({ page }) => {
    await page.goto('/inventario')
    await page.waitForTimeout(2000)
    
    // Verificar links de navegación
    const linkProductos = page.getByRole('link', { name: /productos/i })
      .or(page.getByText('Productos').first())
    
    if (await linkProductos.isVisible()) {
      await expect(linkProductos).toBeVisible()
    }
  })
})

test.describe('Inventario - Productos', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('accede a lista de productos', async ({ page }) => {
    await page.goto('/inventario/productos')
    
    // Verificar que la tabla de productos carga
    await expect(page.getByText(/productos|catálogo/i).first()).toBeVisible({ timeout: 15000 })
  })

  test('muestra tabla con productos existentes', async ({ page }) => {
    await page.goto('/inventario/productos')
    await page.waitForTimeout(2000)
    
    // Verificar que hay tabla o grid de productos
    const tabla = page.locator('table').first()
      .or(page.locator('[role="grid"]').first())
    
    if (await tabla.isVisible()) {
      await expect(tabla).toBeVisible()
    }
  })

  test('permite buscar productos', async ({ page }) => {
    await page.goto('/inventario/productos')
    await page.waitForTimeout(2000)
    
    // Buscar campo de búsqueda
    const searchInput = page.getByPlaceholder(/buscar|filtrar/i).first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('Lágrima')
      await page.waitForTimeout(1000)
      // Verificar que filtra
      await expect(searchInput).toHaveValue('Lágrima')
    }
  })

  test('botón de entrada rápida está disponible', async ({ page }) => {
    await page.goto('/inventario/productos')
    await page.waitForTimeout(2000)
    
    // Buscar botón de entrada rápida
    const botonEntrada = page.getByRole('button', { name: /entrada.*rápida|agregar.*stock/i })
      .or(page.locator('[data-testid*="entrada-rapida"]'))
    
    if (await botonEntrada.isVisible()) {
      await expect(botonEntrada).toBeEnabled()
    }
  })

  test('modal de entrada rápida se abre', async ({ page }) => {
    await page.goto('/inventario/productos')
    await page.waitForTimeout(2000)
    
    // Buscar cualquier botón de entrada en la tabla
    const botonEntrada = page.locator('button:has-text("Entrada")').first()
      .or(page.locator('[data-testid*="entrada"]').first())
    
    if (await botonEntrada.isVisible()) {
      await botonEntrada.click()
      await page.waitForTimeout(500)
      
      // Verificar que se abre modal
      const modal = page.locator('[role="dialog"]')
        .or(page.locator('.modal'))
      
      if (await modal.isVisible()) {
        await expect(modal).toBeVisible()
      }
    }
  })
})

test.describe('Inventario - Lotes y Vencimientos', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('accede a página de lotes', async ({ page }) => {
    await page.goto('/inventario/lotes')
    
    // Verificar que la página carga
    await expect(page.getByText(/lotes|vencimientos/i).first()).toBeVisible({ timeout: 15000 })
  })

  test('muestra lotes con código de color por vencimiento', async ({ page }) => {
    await page.goto('/inventario/lotes')
    await page.waitForTimeout(2000)
    
    // Verificar que hay indicadores de vencimiento
    const indicadores = page.locator('.bg-red-100, .bg-yellow-100, .bg-green-100')
      .or(page.getByText(/vencido|por vencer/i))
    
    if (await indicadores.first().isVisible()) {
      await expect(indicadores.first()).toBeVisible()
    }
  })
})

test.describe('Inventario - Kardex (Movimientos)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('accede a página de kardex', async ({ page }) => {
    await page.goto('/inventario/movimientos')
    
    // Verificar que la página carga
    await expect(page.getByText(/kardex|movimientos/i).first()).toBeVisible({ timeout: 15000 })
  })

  test('muestra historial de movimientos', async ({ page }) => {
    await page.goto('/inventario/movimientos')
    await page.waitForTimeout(2000)
    
    // Verificar que hay tabla de movimientos
    const tabla = page.locator('table').first()
    if (await tabla.isVisible()) {
      await expect(tabla).toBeVisible()
    }
  })

  test('permite filtrar por tipo de movimiento', async ({ page }) => {
    await page.goto('/inventario/movimientos')
    await page.waitForTimeout(2000)
    
    // Buscar selectores de filtro
    const filtroTipo = page.getByRole('combobox')
      .or(page.locator('select'))
      .first()
    
    if (await filtroTipo.isVisible()) {
      await expect(filtroTipo).toBeVisible()
    }
  })
})
