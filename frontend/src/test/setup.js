/**
 * Configuración global de Vitest para testing de React
 * NovaVision ERP - Suite de Testing
 */

import '@testing-library/jest-dom'
import { vi, afterEach } from 'vitest'

// Mock de variables de entorno
vi.stubEnv('REACT_APP_BACKEND_URL', 'http://localhost:8001')

// Mock de window.matchMedia para componentes responsivos
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock de ResizeObserver para componentes que lo usan
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock

// Mock de IntersectionObserver
class IntersectionObserverMock {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.IntersectionObserver = IntersectionObserverMock

// Mock de scrollTo
window.scrollTo = vi.fn()

// Mock de localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Suprimir warnings de console en tests (opcional, descomentar si es necesario)
// vi.spyOn(console, 'warn').mockImplementation(() => {})
// vi.spyOn(console, 'error').mockImplementation(() => {})

// Cleanup después de cada test
afterEach(() => {
  vi.clearAllMocks()
})
