// Detalle de una venta de Óptica (desde "Ver Ventas del Día"): items, totales, FEL e impresión
import React from 'react';
import { Printer } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { FELButton } from '../FELButton';
import { formatCurrency, formatDate, saleStatusLabels, opticaPaymentMethodLabels } from '../../services/api';

const estadoBadgeClass = {
  pagado: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
  pendiente: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
  cancelado: 'bg-red-100 text-red-700 hover:bg-red-100',
};

const POSSaleDetailDialog = ({ open, onOpenChange, venta, onImprimir, onFelUpdated }) => {
  if (!venta) return null;
  const items = venta.items_v2 || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" data-testid="pos-venta-detalle-dialog">
        <DialogHeader>
          <DialogTitle style={{ color: 'var(--text-primary)' }}>
            Venta {venta.order_number || venta.id}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                {venta.patient_name || 'Consumidor Final'}
              </p>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {formatDate(venta.created_at)}
              </p>
            </div>
            <Badge className={estadoBadgeClass[venta.status] || ''} data-testid="pos-venta-detalle-estado">
              {saleStatusLabels[venta.status] || venta.status}
            </Badge>
          </div>

          <div className="rounded-lg border divide-y" style={{ borderColor: 'var(--border-color)' }}>
            {items.map((it, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2">
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{it.name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {it.quantity} x {formatCurrency(it.unit_price)}
                  </p>
                </div>
                <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                  {formatCurrency(it.subtotal)}
                </p>
              </div>
            ))}
          </div>

          <div className="space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{formatCurrency(venta.subtotal)}</span>
            </div>
            {venta.discount_amount > 0 && (
              <div className="flex justify-between">
                <span>Descuento</span>
                <span>-{formatCurrency(venta.discount_amount)}</span>
              </div>
            )}
            <div className="flex justify-between text-base font-bold" style={{ color: 'var(--text-primary)' }}>
              <span>Total</span>
              <span className="text-teal-500">{formatCurrency(venta.total)}</span>
            </div>
          </div>

          {Array.isArray(venta.payments) && venta.payments.length > 0 && (
            <div className="text-xs space-y-1" style={{ color: 'var(--text-secondary)' }}>
              {venta.payments.map((p, idx) => (
                <div key={idx} className="flex justify-between">
                  <span>{opticaPaymentMethodLabels[p.payment_method] || p.payment_method}</span>
                  <span>{formatCurrency(p.amount)}</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between gap-2 pt-1">
            <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Factura electrónica (FEL):</span>
            <FELButton
              origen="optica"
              sale={venta}
              defaultNombre={venta.patient_name}
              onUpdated={onFelUpdated}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
          <Button
            className="bg-teal-600 hover:bg-teal-700"
            onClick={() => onImprimir(venta.id)}
            data-testid="pos-detalle-imprimir-btn"
          >
            <Printer className="h-4 w-4 mr-2" />
            Imprimir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default POSSaleDetailDialog;
