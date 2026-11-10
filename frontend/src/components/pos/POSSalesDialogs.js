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
import { FELButton } from '../FELButton';
import { formatCurrency, formatDate, saleStatusLabels } from '../../services/api';
import { Badge } from '../ui/badge';

const estadoBadgeClass = {
  pagado: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
  pendiente: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
  cancelado: 'bg-red-100 text-red-700 hover:bg-red-100',
};

// Diálogo de venta exitosa
export const POSSuccessDialog = ({
  open,
  onOpenChange,
  ventaExitosa,
  onImprimir,
  onFelUpdated
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="pos-venta-exitosa-dialog">
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

          {ventaExitosa && (
            <div className="flex flex-col items-center justify-center gap-1.5 mb-6" data-testid="pos-exitosa-fel-row">
              <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Factura electrónica (FEL)</span>
              <FELButton
                origen="optica"
                sale={ventaExitosa}
                defaultNombre={ventaExitosa.patient_name}
                onUpdated={onFelUpdated}
              />
            </div>
          )}

          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
            <Button
              className="bg-teal-600 hover:bg-teal-700"
              onClick={() => ventaExitosa && onImprimir(ventaExitosa.id)}
              data-testid="pos-exitosa-imprimir-btn"
            >
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
  resumenDia,
  onSelectVenta
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl" data-testid="pos-ventas-dialog">
        <DialogHeader>
          <DialogTitle>Mis Ventas del Día</DialogTitle>
          <DialogDescription>
            {resumenDia.cantidad} ventas | Vendido: {formatCurrency(resumenDia.total)} | Cobrado: {formatCurrency(resumenDia.cobrado)}
          </DialogDescription>
        </DialogHeader>

        {resumenDia.por_metodo && Object.keys(resumenDia.por_metodo).length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="pos-ventas-por-metodo">
            {Object.entries(resumenDia.por_metodo).map(([metodo, monto]) => (
              <div key={metodo} className="p-2 rounded-lg border text-center" style={{ borderColor: 'var(--border-color)' }}>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{metodo}</p>
                <p className="font-bold text-teal-500">{formatCurrency(monto)}</p>
              </div>
            ))}
          </div>
        )}
        
        <div className="max-h-96 overflow-y-auto space-y-2">
          {ventasHoy.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No hay ventas registradas hoy
            </div>
          ) : (
            ventasHoy.map(venta => (
              <div 
                key={venta.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectVenta(venta)}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#14b8a6'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-color)'; }}
                className="p-3 rounded-lg border cursor-pointer transition-colors"
                style={{ background: 'var(--bg-hover)', borderColor: 'var(--border-color)' }}
                data-testid={`pos-venta-row-${venta.id}`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {venta.order_number || venta.id}
                      </p>
                      {venta.status && venta.status !== 'pagado' && (
                        <Badge className={`text-[10px] px-1.5 py-0 ${estadoBadgeClass[venta.status] || ''}`}>
                          {saleStatusLabels[venta.status] || venta.status}
                        </Badge>
                      )}
                    </div>
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
