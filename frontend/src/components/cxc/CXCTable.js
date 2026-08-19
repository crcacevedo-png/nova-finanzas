// Tabla de cuentas por cobrar
import React from 'react';
import { ChevronRight, FileText } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { formatCurrency, formatDate } from '../../services/api';
import { getTipoResponsableInfo, getEstadoIcon, getEstadoConfig } from './constants';

const CXCTable = ({
  cuentas,
  loading,
  total,
  offset,
  limit,
  onPageChange,
  onSelectCuenta
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

  if (loading) {
    return (
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="p-6 space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (cuentas.length === 0) {
    return (
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="p-0">
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <FileText className="h-12 w-12 mb-3 opacity-50" />
            <p>No hay cuentas por cobrar</p>
            <p className="text-sm">Las cuentas se crean desde el Punto de Venta</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>No. Cuenta</TableHead>
              <TableHead>Responsable</TableHead>
              <TableHead>Paciente</TableHead>
              <TableHead>Concepto</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right">Saldo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cuentas.map((cuenta) => {
              const tipoInfo = getTipoResponsableInfo(cuenta.tipo_responsable);
              const Icon = tipoInfo.icon;
              return (
                <TableRow 
                  key={cuenta.id} 
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => onSelectCuenta(cuenta.id)}
                >
                  <TableCell className="font-mono font-medium">
                    {cuenta.numero_cuenta}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                        <Icon className="h-3 w-3 text-white" />
                      </div>
                      <div>
                        <p className="font-medium text-sm">{cuenta.responsable_nombre}</p>
                        <p className="text-xs text-slate-500">{tipoInfo.label}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {cuenta.paciente_nombre || '-'}
                  </TableCell>
                  <TableCell className="max-w-[150px] truncate">
                    {cuenta.concepto}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(cuenta.monto_total)}
                  </TableCell>
                  <TableCell className="text-right font-bold text-orange-600">
                    {formatCurrency(cuenta.saldo_pendiente)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {renderEstadoIcon(cuenta.estado)}
                      {getEstadoBadge(cuenta.estado)}
                    </div>
                  </TableCell>
                  <TableCell className="text-slate-500 text-sm">
                    {formatDate(cuenta.fecha_emision)}
                  </TableCell>
                  <TableCell>
                    <ChevronRight className="h-4 w-4 text-slate-400" />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        
        {/* Paginación */}
        {total > limit && (
          <div className="flex items-center justify-between px-6 py-4 border-t">
            <span className="text-sm text-slate-500">
              Mostrando {offset + 1} - {Math.min(offset + limit, total)} de {total}
            </span>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm"
                disabled={offset === 0}
                onClick={() => onPageChange(Math.max(0, offset - limit))}
              >
                Anterior
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                disabled={offset + limit >= total}
                onClick={() => onPageChange(offset + limit)}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CXCTable;
