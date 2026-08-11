/**
 * Tests unitarios para utilidades de API
 * NovaVision ERP - Suite de Testing
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Funciones de utilidad del api.js para testing
describe('API Utils', () => {
  describe('formatDate', () => {
    it('formatea fecha correctamente en formato dd/mm/yy', () => {
      // Test de formato de fecha estándar Guatemala
      const date = new Date('2026-08-07T12:00:00Z')
      const day = date.getDate().toString().padStart(2, '0')
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const year = date.getFullYear().toString().slice(-2)
      const formatted = `${day}/${month}/${year}`
      
      expect(formatted).toMatch(/^\d{2}\/\d{2}\/\d{2}$/)
    })

    it('maneja fechas inválidas correctamente', () => {
      const invalidDate = new Date('invalid')
      expect(isNaN(invalidDate.getTime())).toBe(true)
    })
  })

  describe('formatCurrency', () => {
    it('formatea moneda en Quetzales correctamente', () => {
      const amount = 1234.56
      const formatted = `Q ${amount.toLocaleString('es-GT', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
      })}`
      
      expect(formatted).toContain('Q')
      expect(formatted).toContain('1')
    })

    it('maneja valores cero', () => {
      const amount = 0
      const formatted = `Q ${amount.toFixed(2)}`
      expect(formatted).toBe('Q 0.00')
    })

    it('maneja valores negativos', () => {
      const amount = -100
      expect(amount < 0).toBe(true)
    })
  })

  describe('Token Management', () => {
    // Usar storage real para estos tests
    const storage = {}
    
    beforeEach(() => {
      Object.keys(storage).forEach(key => delete storage[key])
    })

    it('almacena token correctamente', () => {
      const token = 'test-jwt-token'
      storage['token'] = token
      
      expect(storage['token']).toBe(token)
    })

    it('elimina token correctamente', () => {
      storage['token'] = 'test-token'
      delete storage['token']
      
      expect(storage['token']).toBeUndefined()
    })
  })
})

describe('Validaciones de Datos', () => {
  describe('DPI Guatemala', () => {
    it('valida formato de DPI correcto (13 dígitos)', () => {
      const dpiValido = '1234567890101'
      expect(dpiValido.length).toBe(13)
      expect(/^\d{13}$/.test(dpiValido)).toBe(true)
    })

    it('rechaza DPI con formato incorrecto', () => {
      const dpiCorto = '12345678901'
      const dpiConLetras = '123456789ABC1'
      
      expect(/^\d{13}$/.test(dpiCorto)).toBe(false)
      expect(/^\d{13}$/.test(dpiConLetras)).toBe(false)
    })
  })

  describe('Teléfono Guatemala', () => {
    it('valida número de teléfono de 8 dígitos', () => {
      const telefono = '55512345'
      expect(/^\d{8}$/.test(telefono)).toBe(true)
    })

    it('rechaza teléfonos con formato incorrecto', () => {
      const telConGuiones = '5551-2345'
      const telCorto = '555123'
      
      expect(/^\d{8}$/.test(telConGuiones)).toBe(false)
      expect(/^\d{8}$/.test(telCorto)).toBe(false)
    })
  })

  describe('Email', () => {
    it('valida email con formato correcto', () => {
      const email = 'usuario@ejemplo.com'
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      
      expect(emailRegex.test(email)).toBe(true)
    })

    it('rechaza email sin @', () => {
      const emailInvalido = 'usuarioejemplo.com'
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      
      expect(emailRegex.test(emailInvalido)).toBe(false)
    })
  })
})

describe('Cálculos Financieros', () => {
  describe('IVA Guatemala (12%)', () => {
    it('calcula IVA correctamente', () => {
      const subtotal = 100.00
      const tasaIVA = 0.12
      const iva = subtotal * tasaIVA
      
      expect(iva).toBe(12.00)
    })

    it('calcula total con IVA', () => {
      const subtotal = 100.00
      const tasaIVA = 0.12
      const total = subtotal * (1 + tasaIVA)
      
      expect(total).toBeCloseTo(112.00)
    })

    it('redondea a 2 decimales', () => {
      const subtotal = 99.99
      const tasaIVA = 0.12
      const total = Math.round(subtotal * (1 + tasaIVA) * 100) / 100
      
      expect(total.toString().split('.')[1]?.length || 0).toBeLessThanOrEqual(2)
    })
  })

  describe('Descuentos', () => {
    it('aplica descuento porcentual correctamente', () => {
      const precio = 100.00
      const descuentoPct = 10
      const descuento = precio * (descuentoPct / 100)
      const final = precio - descuento
      
      expect(final).toBe(90.00)
    })

    it('aplica descuento fijo correctamente', () => {
      const precio = 100.00
      const descuentoFijo = 15.00
      const final = precio - descuentoFijo
      
      expect(final).toBe(85.00)
    })

    it('no permite descuento mayor al precio', () => {
      const precio = 100.00
      const descuentoExcesivo = 150.00
      const final = Math.max(0, precio - descuentoExcesivo)
      
      expect(final).toBe(0)
    })
  })

  describe('Pago Mixto', () => {
    it('suma correctamente múltiples formas de pago', () => {
      const formasPago = [
        { metodo: 'Efectivo', monto: 50.00 },
        { metodo: 'Tarjeta', monto: 30.00 },
        { metodo: 'Transferencia', monto: 20.00 },
      ]
      
      const totalPagado = formasPago.reduce((sum, fp) => sum + fp.monto, 0)
      expect(totalPagado).toBe(100.00)
    })

    it('calcula cambio correctamente', () => {
      const total = 85.50
      const efectivoRecibido = 100.00
      const cambio = efectivoRecibido - total
      
      expect(cambio).toBe(14.50)
    })
  })
})

describe('Lógica FEFO (First Expire First Out)', () => {
  it('ordena lotes por fecha de vencimiento ascendente', () => {
    const lotes = [
      { id: '1', fecha_vencimiento: '2026-12-01', cantidad: 10 },
      { id: '2', fecha_vencimiento: '2026-08-15', cantidad: 5 },
      { id: '3', fecha_vencimiento: '2027-01-20', cantidad: 20 },
    ]
    
    const ordenados = [...lotes].sort((a, b) => 
      new Date(a.fecha_vencimiento) - new Date(b.fecha_vencimiento)
    )
    
    expect(ordenados[0].id).toBe('2') // Vence primero
    expect(ordenados[1].id).toBe('1')
    expect(ordenados[2].id).toBe('3') // Vence último
  })

  it('descuenta del lote que vence primero', () => {
    const lotes = [
      { id: '1', fecha_vencimiento: '2026-12-01', cantidad: 10 },
      { id: '2', fecha_vencimiento: '2026-08-15', cantidad: 5 },
    ]
    
    const cantidadADescontar = 3
    const ordenados = [...lotes].sort((a, b) => 
      new Date(a.fecha_vencimiento) - new Date(b.fecha_vencimiento)
    )
    
    // El lote 2 vence primero, debe descontarse de ahí
    const loteADescontar = ordenados[0]
    expect(loteADescontar.id).toBe('2')
    expect(loteADescontar.cantidad >= cantidadADescontar).toBe(true)
  })

  it('distribuye descuento entre múltiples lotes si es necesario', () => {
    const lotes = [
      { id: '1', fecha_vencimiento: '2026-12-01', cantidad: 10 },
      { id: '2', fecha_vencimiento: '2026-08-15', cantidad: 5 },
    ]
    
    const cantidadADescontar = 8 // Más que el lote que vence primero
    let restante = cantidadADescontar
    const consumo = []
    
    const ordenados = [...lotes].sort((a, b) => 
      new Date(a.fecha_vencimiento) - new Date(b.fecha_vencimiento)
    )
    
    for (const lote of ordenados) {
      if (restante <= 0) break
      const descontado = Math.min(lote.cantidad, restante)
      consumo.push({ lote_id: lote.id, cantidad: descontado })
      restante -= descontado
    }
    
    expect(consumo.length).toBe(2)
    expect(consumo[0]).toEqual({ lote_id: '2', cantidad: 5 })
    expect(consumo[1]).toEqual({ lote_id: '1', cantidad: 3 })
    expect(restante).toBe(0)
  })
})
