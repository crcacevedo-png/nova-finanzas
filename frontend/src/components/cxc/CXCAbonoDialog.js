// Diálogo para registrar abono a cuenta por cobrar
import React from 'react';
import { DollarSign, RefreshCw } from 'lucide-react';
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
import { METODOS_PAGO } from './constants';

const CXCAbonoDialog = ({
  open,
  onOpenChange,
  cuenta,
  metodoPago,
  setMetodoPago,
  montoAbono,
  setMontoAbono,
  referenciaAbono,
  setReferenciaAbono,
  notasAbono,
  setNotasAbono,
  submitting,
  onRegistrar,
  onCancel
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Registrar Abono</DialogTitle>
          <DialogDescription>
            Cuenta: {cuenta?.numero_cuenta}
            <br />
            Saldo pendiente: <span className="font-bold text-orange-600">
              {formatCurrency(cuenta?.saldo_pendiente || 0)}
            </span>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Método de pago */}
          <div>
            <Label>Método de Pago</Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              {METODOS_PAGO.map(mp => {
                const Icon = mp.icon;
                return (
                  <button
                    key={mp.value}
                    onClick={() => setMetodoPago(mp.value)}
                    className={`
                      p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all
                      ${metodoPago === mp.value 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'}
                    `}
                  >
                    <Icon className={`h-5 w-5 ${metodoPago === mp.value ? 'text-blue-600' : 'text-slate-400'}`} />
                    <span className="text-xs">{mp.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          
          {/* Monto */}
          <div>
            <Label>Monto del Abono</Label>
            <div className="relative mt-2">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">Q</span>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                max={cuenta?.saldo_pendiente || 0}
                value={montoAbono}
                onChange={(e) => setMontoAbono(e.target.value)}
                className="pl-8 text-lg font-bold"
                placeholder="0.00"
              />
            </div>
            <div className="flex gap-2 mt-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setMontoAbono((cuenta?.saldo_pendiente || 0).toString())}
              >
                Pago total
              </Button>
              {[100, 200, 500].map(m => (
                <Button 
                  key={m}
                  variant="outline" 
                  size="sm"
                  onClick={() => setMontoAbono(m.toString())}
                >
                  Q{m}
                </Button>
              ))}
            </div>
          </div>
          
          {/* Referencia */}
          {metodoPago !== 'Efectivo' && (
            <div>
              <Label>Referencia (opcional)</Label>
              <Input
                value={referenciaAbono}
                onChange={(e) => setReferenciaAbono(e.target.value)}
                placeholder="No. autorización, boleta, etc."
                className="mt-2"
              />
            </div>
          )}
          
          {/* Notas */}
          <div>
            <Label>Notas (opcional)</Label>
            <Textarea
              value={notasAbono}
              onChange={(e) => setNotasAbono(e.target.value)}
              placeholder="Observaciones del pago..."
              rows={2}
              className="mt-2"
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
          <Button 
            className="bg-blue-600 hover:bg-blue-700"
            onClick={onRegistrar}
            disabled={submitting || !montoAbono || parseFloat(montoAbono) <= 0}
          >
            {submitting ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <DollarSign className="h-4 w-4 mr-2" />
                Registrar Abono
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CXCAbonoDialog;
