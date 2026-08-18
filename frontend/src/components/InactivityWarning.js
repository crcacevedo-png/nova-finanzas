// /app/frontend/src/components/InactivityWarning.js
// Componente de advertencia de inactividad
// SEC-007: Modal que avisa al usuario antes de cerrar sesión por inactividad

import React from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { Clock, LogOut } from 'lucide-react';

/**
 * Modal de advertencia de inactividad
 * @param {Object} props
 * @param {boolean} props.open - Si el modal está abierto
 * @param {string} props.remainingTime - Tiempo restante formateado
 * @param {Function} props.onContinue - Callback al hacer clic en "Continuar trabajando"
 * @param {Function} props.onLogout - Callback al hacer clic en "Cerrar sesión"
 */
export function InactivityWarning({ open, remainingTime, onContinue, onLogout }) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-amber-100 rounded-full">
              <Clock className="h-6 w-6 text-amber-600" />
            </div>
            <AlertDialogTitle className="text-lg">
              Sesión por expirar
            </AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-base">
            Por su seguridad, su sesión se cerrará automáticamente por inactividad.
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center justify-center gap-2">
                <span className="text-amber-700 font-medium">Tiempo restante:</span>
                <span className="text-2xl font-bold text-amber-600">
                  {remainingTime}
                </span>
              </div>
            </div>
            <p className="mt-3 text-sm text-gray-500">
              Haga clic en &ldquo;Continuar trabajando&rdquo; para mantener su sesión activa.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col sm:flex-row gap-2">
          <button
            onClick={onLogout}
            className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Cerrar sesión ahora
          </button>
          <AlertDialogAction
            onClick={onContinue}
            className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          >
            Continuar trabajando
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default InactivityWarning;
