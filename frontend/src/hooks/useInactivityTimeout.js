// /app/frontend/src/hooks/useInactivityTimeout.js
// Hook para manejar el timeout de inactividad de sesión
// SEC-007: Timeout de 30 minutos en todas las estaciones

import { useState, useEffect, useCallback, useRef } from 'react';

// Configuración por defecto (en milisegundos)
const DEFAULT_TIMEOUT = 30 * 60 * 1000; // 30 minutos
const WARNING_BEFORE = 5 * 60 * 1000;   // Avisar 5 minutos antes

/**
 * Hook para manejar el timeout de inactividad
 * @param {Object} options - Opciones de configuración
 * @param {number} options.timeout - Tiempo de inactividad en ms (default: 30 min)
 * @param {number} options.warningTime - Tiempo antes del timeout para mostrar advertencia (default: 5 min)
 * @param {Function} options.onTimeout - Callback cuando expira el timeout
 * @param {Function} options.onWarning - Callback cuando se muestra la advertencia
 * @param {Function} options.onActivity - Callback cuando hay actividad (opcional)
 * @param {boolean} options.enabled - Si el timeout está habilitado (default: true)
 */
export function useInactivityTimeout({
  timeout = DEFAULT_TIMEOUT,
  warningTime = WARNING_BEFORE,
  onTimeout,
  onWarning,
  onActivity,
  enabled = true
} = {}) {
  const [showWarning, setShowWarning] = useState(false);
  const [remainingTime, setRemainingTime] = useState(null);
  const [isActive, setIsActive] = useState(true);
  
  const timeoutRef = useRef(null);
  const warningRef = useRef(null);
  const countdownRef = useRef(null);
  const lastActivityRef = useRef(Date.now());
  
  // Limpiar todos los timers
  const clearAllTimers = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningRef.current) {
      clearTimeout(warningRef.current);
      warningRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, []);
  
  // Resetear los timers (cuando hay actividad)
  const resetTimers = useCallback(() => {
    if (!enabled) return;
    
    clearAllTimers();
    lastActivityRef.current = Date.now();
    setShowWarning(false);
    setRemainingTime(null);
    setIsActive(true);
    
    // Timer para mostrar advertencia
    warningRef.current = setTimeout(() => {
      setShowWarning(true);
      setRemainingTime(Math.ceil(warningTime / 1000));
      
      if (onWarning) {
        onWarning();
      }
      
      // Iniciar countdown
      countdownRef.current = setInterval(() => {
        setRemainingTime(prev => {
          if (prev <= 1) {
            clearInterval(countdownRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
    }, timeout - warningTime);
    
    // Timer para cerrar sesión
    timeoutRef.current = setTimeout(() => {
      setIsActive(false);
      setShowWarning(false);
      
      if (onTimeout) {
        onTimeout();
      }
    }, timeout);
    
  }, [enabled, timeout, warningTime, onTimeout, onWarning, clearAllTimers]);
  
  // Manejar actividad del usuario
  const handleActivity = useCallback(() => {
    if (!enabled) return;
    
    // Solo resetear si no estamos en el período de gracia post-warning
    // O si el usuario explícitamente continúa
    if (!showWarning) {
      resetTimers();
      
      if (onActivity) {
        onActivity();
      }
    }
  }, [enabled, showWarning, resetTimers, onActivity]);
  
  // Extender sesión (cuando el usuario hace clic en "Continuar")
  const extendSession = useCallback(() => {
    resetTimers();
  }, [resetTimers]);
  
  // Efecto para configurar los event listeners
  useEffect(() => {
    if (!enabled) {
      clearAllTimers();
      return;
    }
    
    // Eventos que indican actividad del usuario
    const events = [
      'mousedown',
      'mousemove',
      'keydown',
      'scroll',
      'touchstart',
      'click',
      'wheel'
    ];
    
    // Throttle para no procesar demasiados eventos
    let lastEventTime = 0;
    const throttleMs = 1000; // Solo procesar un evento por segundo
    
    const throttledHandler = () => {
      const now = Date.now();
      if (now - lastEventTime > throttleMs) {
        lastEventTime = now;
        handleActivity();
      }
    };
    
    // Agregar listeners
    events.forEach(event => {
      window.addEventListener(event, throttledHandler, { passive: true });
    });
    
    // Iniciar timers
    resetTimers();
    
    // Cleanup
    return () => {
      events.forEach(event => {
        window.removeEventListener(event, throttledHandler);
      });
      clearAllTimers();
    };
  }, [enabled, handleActivity, resetTimers, clearAllTimers]);
  
  // Formatear tiempo restante para mostrar
  const formatRemainingTime = useCallback(() => {
    if (remainingTime === null) return '';
    
    const minutes = Math.floor(remainingTime / 60);
    const seconds = remainingTime % 60;
    
    if (minutes > 0) {
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${seconds} segundos`;
  }, [remainingTime]);
  
  return {
    showWarning,
    remainingTime,
    remainingTimeFormatted: formatRemainingTime(),
    isActive,
    extendSession,
    resetTimers
  };
}

export default useInactivityTimeout;
