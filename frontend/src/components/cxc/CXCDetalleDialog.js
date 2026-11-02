// Diálogo de detalle de cuenta por cobrar
import React from 'react';
import { Receipt, User, Calendar, DollarSign } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Label } from '../ui/label';
import { formatCurrency, formatDate } from '../../services/api';
import { getTipoResponsableInfo, getEstadoIcon, getEstadoConfig } from './constants';

const CXCDetalleDialog = ({
  open,
  onOpenChange,
  cuenta,
  onRegistrarAbono
}) => {
  const getEstadoBadge = (estado) => {
    const config = getEstadoConfig(estado);
    return (
      <Badge className={config?.color || 'bg-slate-100 text-slate-700'}>
        {estado}
      </Badge>
    );
  };

  const renderEstadoIcon = (estado) => {
    const IconComponent = getEstadoIcon(estado);
    if (!IconComponent) return null;
    
    const colorMap = {
      'Pendiente': 'text-yellow-500',
      'Parcial': 'text-blue-500',
      'Pagado': 'text-green-500',
      'Vencido': 'text-red-500',
      'Anulado': 'text-slate-500'
    };
    
    return <IconComponent className={`h-4 w-4 ${colorMap[estado] || ''}`} />;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5 text-blue-500" />
            {cuenta?.numero_cuenta}
          </DialogTitle>
          <DialogDescription>
            Detalle de cuenta por cobrar - Clínica
          </DialogDescription>
        </DialogHeader>
        
        {cuenta && (
          <div className="space-y-6">
            {/* Info principal */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <Label className="text-sm text-slate-500">Responsable</Label>
                <div className="flex items-center gap-2 mt-1">
                  {(() => {
                    const tipoInfo = getTipoResponsableInfo(cuenta.tipo_responsable);
                    const Icon = tipoInfo.icon;
                    return (
                      <>
                        <div className={`w-8 h-8 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                          <Icon className="h-4 w-4 text-white" />
                        </div>
                        <div>
                          <p className="font-medium">{cuenta.responsable_nombre}</p>
                          <p className="text-xs text-slate-500">{tipoInfo.label}</p>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
              
              <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <Label className="text-sm text-slate-500">Estado</Label>
                <div className="flex items-center gap-2 mt-1">
                  {renderEstadoIcon(cuenta.estado)}
                  {getEstadoBadge(cuenta.estado)}
                </div>
              </div>
              
              {cuenta.paciente_nombre && (
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Paciente</Label>
                  <p className="font-medium flex items-center gap-2 mt-1">
                    <User className="h-4 w-4 text-slate-400" />
                    {cuenta.paciente_nombre}
                  </p>
                </div>
              )}
              
              <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <Label className="text-sm text-slate-500">Fecha de Emisión</Label>
                <p className="font-medium flex items-center gap-2 mt-1">
                  <Calendar className="h-4 w-4 text-slate-400" />
                  {formatDate(cuenta.fecha_emision)}
                </p>
              </div>
            </div>
            
            {/* Concepto */}
            <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border-color)' }}>
              <Label className="text-sm text-slate-500">Concepto</Label>
              <p className="font-medium mt-1">{cuenta.concepto}</p>
              {cuenta.descripcion && (
                <p className="text-sm text-slate-600 mt-2" data-testid="cxc-detalle-descripcion">
                  Servicio: {cuenta.descripcion}
                </p>
              )}
              {cuenta.notas && (
                <p className="text-sm text-slate-500 mt-2">
                  Notas: {cuenta.notas}
                </p>
              )}
            </div>
            
            {/* Montos */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-slate-100 text-center">
                <Label className="text-sm text-slate-500">Total</Label>
                <p className="text-xl font-bold text-slate-800">
                  {formatCurrency(cuenta.monto_total)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-green-100 text-center">
                <Label className="text-sm text-green-600">Pagado</Label>
                <p className="text-xl font-bold text-green-700">
                  {formatCurrency(cuenta.monto_pagado)}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-orange-100 text-center">
                <Label className="text-sm text-orange-600">Saldo</Label>
                <p className="text-xl font-bold text-orange-700">
                  {formatCurrency(cuenta.saldo_pendiente)}
                </p>
              </div>
            </div>
            
            {/* Historial de pagos */}
            {cuenta.pagos && cuenta.pagos.length > 0 && (
              <div>
                <Label className="mb-2 block">Historial de Pagos</Label>
                <div className="border rounded-lg divide-y" style={{ borderColor: 'var(--border-color)' }}>
                  {cuenta.pagos.map((pago, idx) => (
                    <div key={pago.id || idx} className="p-3 flex items-center justify-between">
                      <div>
                        <p className="font-medium">{pago.metodo_pago}</p>
                        <p className="text-sm text-slate-500">
                          {formatDate(pago.fecha)} • {pago.registrado_por_nombre}
                        </p>
                        {pago.referencia && (
                          <p className="text-xs text-slate-400">Ref: {pago.referencia}</p>
                        )}
                      </div>
                      <p className="font-bold text-green-600">
                        {formatCurrency(pago.monto)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
          {cuenta && 
           cuenta.estado !== 'Pagado' && 
           cuenta.estado !== 'Anulado' && (
            <Button 
              className="bg-blue-600 hover:bg-blue-700"
              onClick={onRegistrarAbono}
            >
              <DollarSign className="h-4 w-4 mr-2" />
              Registrar Abono
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CXCDetalleDialog;
