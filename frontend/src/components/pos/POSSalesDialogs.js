// Diálogos de ventas y venta exitosa para POS
import React from 'react';
import { Check, Printer } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { formatCurrency, formatDate } from '../../services/api';

// Diálogo de venta exitosa
export const POSSuccessDialog = ({
  open,
  onOpenChange,
  ventaExitosa
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <div className="text-center py-6">
          <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
            ¡Venta Exitosa!
          </h2>
          <p className="text-slate-500 mb-4">
            Orden: {ventaExitosa?.order_number || ventaExitosa?.id}
          </p>
          <p className="text-3xl font-bold text-teal-500 mb-6">
            {formatCurrency(ventaExitosa?.total || 0)}
          </p>
          
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
            <Button className="bg-teal-600 hover:bg-teal-700">
              <Printer className="h-4 w-4 mr-2" />
              Imprimir
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Diálogo de ventas del día
export const POSSalesDialog = ({
  open,
  onOpenChange,
  ventasHoy,
  resumenDia
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Ventas del Día</DialogTitle>
          <DialogDescription>
            Total: {formatCurrency(resumenDia.total)} ({resumenDia.cantidad} ventas)
          </DialogDescription>
        </DialogHeader>
        
        <div className="max-h-96 overflow-y-auto space-y-2">
          {ventasHoy.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No hay ventas registradas hoy
            </div>
          ) : (
            ventasHoy.map(venta => (
              <div 
                key={venta.id}
                className="p-3 rounded-lg border"
                style={{ background: 'var(--bg-hover)', borderColor: 'var(--border-color)' }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {venta.order_number || venta.id}
                    </p>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {venta.patient_name || 'Consumidor Final'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-teal-500">
                      {formatCurrency(venta.total)}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                      {formatDate(venta.created_at)}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
