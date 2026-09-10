/**
 * Utilidades de Testing para NovaVision
 * Incluye helpers para mocks, renderizado y datos de prueba
 */

import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../../context/AuthContext'
import { vi } from 'vitest'

/**
 * Renderiza un componente con todos los providers necesarios
 * @param {React.ReactElement} ui - Componente a renderizar
 * @param {Object} options - Opciones adicionales de render
 */
export function renderWithProviders(ui, options = {}) {
  const Wrapper = ({ children }) => (
    <BrowserRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </BrowserRouter>
  )
  
  return render(ui, { wrapper: Wrapper, ...options })
}

/**
 * Datos de prueba para usuarios
 */
export const mockUsers = {
  superadmin: {
    id: 'user-superadmin-001',
    username: 'superadmin',
    nombre: 'Super Administrador',
    rol: 'superadmin',
    email: 'superadmin@novavision.com',
    permisos: ['all'],
  },
  admin: {
    id: 'user-admin-001',
    username: 'admin',
    nombre: 'Administrador',
    rol: 'admin',
    email: 'admin@novavision.com',
    permisos: ['view_expenses', 'create_expenses', 'view_patients'],
  },
  usuario: {
    id: 'user-usuario-001',
    username: 'usuario',
    nombre: 'Usuario Regular',
    rol: 'usuario',
    email: 'usuario@novavision.com',
    permisos: ['view_expenses', 'view_patients'],
  },
  optica: {
    id: 'user-optica-001',
    username: 'optica',
    nombre: 'Usuario Óptica',
    rol: 'optica',
    email: 'optica@novavision.com',
    permisos: ['view_optica', 'create_optica'],
  },
}

/**
 * Datos de prueba para pacientes
 */
export const mockPacientes = [
  {
    id: 'paciente-001',
    nombre: 'Juan',
    apellido: 'García López',
    dpi: '1234567890101',
    telefono: '55512345',
    email: 'juan.garcia@email.com',
    fecha_nacimiento: '1985-06-15',
    direccion: 'Ciudad de Guatemala',
  },
  {
    id: 'paciente-002',
    nombre: 'María',
    apellido: 'Rodríguez Pérez',
    dpi: '9876543210101',
    telefono: '55567890',
    email: 'maria.rodriguez@email.com',
    fecha_nacimiento: '1990-03-22',
    direccion: 'Mixco, Guatemala',
  },
]

/**
 * Datos de prueba para productos de inventario
 */
export const mockProductos = [
  {
    id: 'prod-001',
    codigo: 'MED-001',
    nombre: 'Lágrimas Artificiales 15ml',
    categoria_id: 'cat-001',
    categoria_nombre: 'Medicamentos',
    tipo: 'producto',
    precio_venta: 85.00,
    costo_promedio: 55.00,
    existencia_total: 150,
    requiere_receta: false,
    activo: true,
  },
  {
    id: 'prod-002',
    codigo: 'MED-002',
    nombre: 'Timolol 0.5% Gotas 5ml',
    categoria_id: 'cat-001',
    categoria_nombre: 'Medicamentos',
    tipo: 'producto',
    precio_venta: 120.00,
    costo_promedio: 75.00,
    existencia_total: 80,
    requiere_receta: true,
    activo: true,
  },
]

/**
 * Datos de prueba para ventas POS
 */
export const mockVenta = {
  id: 'venta-001',
  numero_venta: 'VTA-20260807-0001',
  origen: 'clinica',
  paciente_nombre: 'Cliente General',
  items: [
    {
      producto_id: 'prod-001',
      nombre: 'Lágrimas Artificiales 15ml',
      cantidad: 2,
      precio_unitario: 85.00,
      descuento: 0,
      subtotal: 170.00,
    },
  ],
  subtotal: 170.00,
  iva: 20.40,
  total: 190.40,
  formas_pago: [{ metodo: 'Efectivo', monto: 190.40 }],
  estado: 'completada',
  fecha: new Date().toISOString(),
}

/**
 * Mock de respuestas de API
 */
export const mockApiResponses = {
  loginSuccess: {
    token: 'mock-jwt-token-12345',
    user: mockUsers.superadmin,
  },
  loginError: {
    detail: 'Credenciales inválidas',
  },
  pacientesLista: {
    items: mockPacientes,
    total: 2,
    page: 1,
    pages: 1,
  },
  productosLista: {
    items: mockProductos,
    total: 2,
  },
}

/**
 * Helper para crear mocks de axios
 * @param {Object} responses - Objeto con respuestas por endpoint
 */
export function createAxiosMock(responses = {}) {
  return {
    get: vi.fn((url) => {
      const response = responses[url]
      if (response) {
        return Promise.resolve({ data: response })
      }
      return Promise.reject(new Error(`No mock for GET ${url}`))
    }),
    post: vi.fn((url, data) => {
      const response = responses[url]
      if (response) {
        return Promise.resolve({ data: response })
      }
      return Promise.reject(new Error(`No mock for POST ${url}`))
    }),
    put: vi.fn((url, data) => {
      const response = responses[url]
      if (response) {
        return Promise.resolve({ data: response })
      }
      return Promise.reject(new Error(`No mock for PUT ${url}`))
    }),
    delete: vi.fn((url) => {
      const response = responses[url] || { success: true }
      return Promise.resolve({ data: response })
    }),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    defaults: {
      headers: {
        common: {},
      },
    },
  }
}

/**
 * Espera un tiempo determinado (útil para tests async)
 * @param {number} ms - Milisegundos a esperar
 */
export function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Formatea fecha como dd/mm/yy (estándar Guatemala)
 * @param {string|Date} date - Fecha a formatear
 */
export function formatDateGT(date) {
  const d = new Date(date)
  const day = d.getDate().toString().padStart(2, '0')
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const year = d.getFullYear().toString().slice(-2)
  return `${day}/${month}/${year}`
}

/**
 * Formatea moneda en Quetzales
 * @param {number} amount - Monto a formatear
 */
export function formatCurrencyGTQ(amount) {
  return `Q ${amount.toLocaleString('es-GT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
