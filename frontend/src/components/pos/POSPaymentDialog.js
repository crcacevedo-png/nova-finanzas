// Diálogo de pago para POS de Óptica
import React from 'react';
import { 
  Plus, 
  X, 
  Check, 
  RefreshCw, 
  Clock, 
  AlertCircle,
  Banknote,
  CreditCard,
  Building2,
  FileText
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { formatCurrency } from '../../services/api';

// Métodos de pago disponibles
const METODOS_PAGO = [
  { value: 'Efectivo', label: 'Efectivo', icon: Banknote, color: 'bg-green-500' },
  { value: 'Tarjeta', label: 'Tarjeta', icon: CreditCard, color: 'bg-blue-500' },
  { value: 'Transferencia', label: 'Transferencia', icon: Building2, color: 'bg-purple-500' },
  { value: 'Cheque', label: 'Cheque', icon: FileText, color: 'bg-orange-500' },
  { value: 'Cuenta por Cobrar', label: 'Crédito (CxC)', icon: Clock, color: 'bg-yellow-500' },
];

const POSPaymentDialog = ({
  open,
  onOpenChange,
  metodoPagoActual,
  setMetodoPagoActual,
  montoPagoActual,
  setMontoPagoActual,
  referenciaPagoActual,
  setReferenciaPagoActual,
  formasPago,
  observaciones,
  setObservaciones,
  paciente,
  submitting,
  calcularTotal,
  calcularTotalPagado,
  calcularPendiente,
  onAgregarFormaPago,
  onEliminarFormaPago,
  onAgregarCxCPendiente,
  onProcesarVenta
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Procesar Pago</DialogTitle>
          <DialogDescription>
            Total a cobrar: <span className="font-bold text-teal-500">{formatCurrency(calcularTotal())}</span>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Métodos de pago */}
          <div className="grid grid-cols-4 gap-2">
            {METODOS_PAGO.map(mp => {
              const Icon = mp.icon;
              return (
                <Button
                  key={mp.value}
                  variant={metodoPagoActual === mp.value ? 'default' : 'outline'}
                  className={`flex flex-col h-auto py-2 gap-1 ${metodoPagoActual === mp.value ? 'bg-teal-600' : ''}`}
                  onClick={() => setMetodoPagoActual(mp.value)}
                  data-testid={`pos-metodo-${mp.value}`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-[11px] leading-tight text-center whitespace-normal">{mp.label}</span>
                </Button>
              );
            })}
          </div>
          
          {/* Monto */}
          <div className="flex gap-2">
            <div className="flex-1">
              <Label>Monto</Label>
              <Input
                type="number"
                placeholder="0.00"
                value={montoPagoActual}
                onChange={(e) => setMontoPagoActual(e.target.value)}
              />
            </div>
            {metodoPagoActual !== 'Efectivo' && (
              <div className="flex-1">
                <Label>Referencia</Label>
                <Input
                  placeholder="No. autorización"
                  value={referenciaPagoActual}
                  onChange={(e) => setReferenciaPagoActual(e.target.value)}
                />
              </div>
            )}
            <div className="flex items-end">
              <Button onClick={onAgregarFormaPago}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* Botones rápidos */}
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setMontoPagoActual(calcularPendiente().toFixed(2))}
            >
              Monto exacto
            </Button>
            {[100, 200, 500].map(m => (
              <Button 
                key={m}
                variant="outline" 
                size="sm"
                onClick={() => setMontoPagoActual(m.toString())}
              >
                Q{m}
              </Button>
            ))}
          </div>
          
          {/* Formas de pago agregadas */}
          {formasPago.length > 0 && (
            <div className="space-y-2">
              <Label>Pagos registrados:</Label>
              {formasPago.map((fp, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-slate-100 dark:bg-slate-800 rounded">
                  <span>{fp.metodo}: {formatCurrency(fp.monto)}</span>
                  <Button variant="ghost" size="sm" onClick={() => onEliminarFormaPago(i)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
          
          {/* Resumen */}
          <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 space-y-2">
            <div className="flex justify-between">
              <span>Total:</span>
              <span className="font-bold">{formatCurrency(calcularTotal())}</span>
            </div>
            <div className="flex justify-between">
              <span>Pagado:</span>
              <span className="text-green-500">{formatCurrency(calcularTotalPagado())}</span>
            </div>
            <div className="flex justify-between font-bold text-lg">
              <span>Pendiente:</span>
              <span className={calcularPendiente() > 0 ? 'text-red-500' : 'text-green-500'}>
                {formatCurrency(calcularPendiente())}
              </span>
            </div>
          </div>
          
          {/* Botón para agregar saldo pendiente a CxC */}
          {calcularPendiente() > 0.01 && (
            <Button
              variant="outline"
              className="w-full border-yellow-500 text-yellow-700 hover:bg-yellow-50"
              onClick={onAgregarCxCPendiente}
            >
              <Clock className="h-4 w-4 mr-2" />
              Agregar saldo pendiente a Cuenta por Cobrar - {formatCurrency(calcularPendiente())}
            </Button>
          )}
          
          {/* Aviso si hay CxC pero no paciente */}
          {formasPago.some(fp => fp.es_cxc) && !paciente && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-2 text-yellow-800">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm">Debe seleccionar un paciente para ventas con Cuenta por Cobrar</span>
            </div>
          )}
          
          {/* Observaciones */}
          <div>
            <Label>Observaciones</Label>
            <Textarea
              placeholder="Notas adicionales..."
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              rows={2}
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button 
            className="bg-teal-600 hover:bg-teal-700"
            onClick={onProcesarVenta}
            disabled={submitting || (calcularPendiente() > 0.01 && !formasPago.some(fp => fp.es_cxc))}
          >
            {submitting ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Confirmar Venta
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default POSPaymentDialog;
