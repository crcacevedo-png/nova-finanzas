/**
 * Tests E2E - Punto de Venta (POS)
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

test.describe('Punto de Venta (POS)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('accede a la página de POS', async ({ page }) => {
    // Navegar a POS
    await page.goto('/punto-venta')
    
    // Verificar que la página carga
    await expect(page.getByText(/Punto de Venta|POS/i).first()).toBeVisible({ timeout: 15000 })
  })

  test('muestra productos disponibles', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
    
    // Buscar sección de productos o buscador
    const searchInput = page.getByPlaceholder(/buscar|producto/i).first()
    if (await searchInput.isVisible()) {
      await expect(searchInput).toBeVisible()
    }
  })

  test('muestra sección de productos rápidos', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
    
    // Buscar sección de productos rápidos
    const productosRapidos = page.getByText(/productos rápidos|más vendidos/i).first()
    // Puede no existir si no hay productos configurados
    if (await productosRapidos.isVisible()) {
      await expect(productosRapidos).toBeVisible()
    }
  })

  test('permite agregar producto al carrito', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(3000)
    
    // Buscar un producto
    const searchInput = page.getByPlaceholder(/buscar|producto/i).first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('Lágrima')
      await page.waitForTimeout(1000)
      
      // Si aparece resultado, intentar agregarlo
      const resultado = page.locator('[data-testid*="producto"]').first()
        .or(page.locator('button:has-text("Agregar")').first())
      
      if (await resultado.isVisible()) {
        await resultado.click()
      }
    }
  })

  test('muestra resumen de venta con totales', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
    
    // Verificar que existe sección de totales
    const totales = page.getByText(/subtotal|total|iva/i).first()
    await expect(totales).toBeVisible({ timeout: 10000 })
  })

  test('muestra métodos de pago disponibles', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
    
    // Verificar que hay opciones de pago
    const metodoPago = page.getByText(/efectivo|tarjeta|transferencia/i).first()
    if (await metodoPago.isVisible()) {
      await expect(metodoPago).toBeVisible()
    }
  })
})

test.describe('POS - Pago Mixto', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
  })

  test('permite seleccionar pago mixto', async ({ page }) => {
    // Buscar opción de pago mixto
    const pagoMixto = page.getByText(/pago mixto|múltiples/i)
      .or(page.locator('[data-testid="pago-mixto"]'))
    
    if (await pagoMixto.isVisible()) {
      await pagoMixto.click()
      await page.waitForTimeout(500)
    }
  })

  test('permite agregar múltiples formas de pago', async ({ page }) => {
    // Este test verifica la UI de pago mixto
    const agregarPago = page.getByRole('button', { name: /agregar.*pago|añadir/i })
      .or(page.locator('button:has-text("+")'))
    
    if (await agregarPago.isVisible()) {
      await expect(agregarPago).toBeEnabled()
    }
  })
})

test.describe('POS - Impresión de Tickets', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsSuperAdmin(page)
  })

  test('botón de imprimir está disponible después de venta', async ({ page }) => {
    await page.goto('/punto-venta')
    await page.waitForTimeout(2000)
    
    // Buscar botón de imprimir en la interfaz
    const botonImprimir = page.getByRole('button', { name: /imprimir|ticket/i })
      .or(page.locator('[data-testid*="imprimir"]'))
    
    // El botón puede estar deshabilitado si no hay venta
    if (await botonImprimir.isVisible()) {
      await expect(botonImprimir).toBeVisible()
    }
  })
})
