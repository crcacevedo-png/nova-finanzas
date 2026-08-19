// Tarjetas de resumen para Cuentas por Cobrar
import React from 'react';
import { Receipt, TrendingUp, Clock, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { formatCurrency } from '../../services/api';
import { getTipoResponsableInfo } from './constants';

// Tarjetas principales de resumen
export const CXCResumenCards = ({ resumen }) => {
  if (!resumen) return null;
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Total Emitido
              </p>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(resumen.total_emitido)}
              </p>
            </div>
            <div className="p-3 rounded-full bg-blue-100">
              <Receipt className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Total Cobrado
              </p>
              <p className="text-2xl font-bold text-green-600">
                {formatCurrency(resumen.total_cobrado)}
              </p>
            </div>
            <div className="p-3 rounded-full bg-green-100">
              <TrendingUp className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Saldo Pendiente
              </p>
              <p className="text-2xl font-bold text-orange-600">
                {formatCurrency(resumen.saldo_pendiente)}
              </p>
            </div>
            <div className="p-3 rounded-full bg-orange-100">
              <Clock className="h-6 w-6 text-orange-600" />
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Cuentas Activas
              </p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {resumen.cantidad_cuentas}
              </p>
            </div>
            <div className="p-3 rounded-full bg-slate-100">
              <FileText className="h-6 w-6 text-slate-600" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Resumen por tipo de responsable
export const CXCResumenPorTipo = ({ resumen }) => {
  if (!resumen || !resumen.por_tipo || Object.keys(resumen.por_tipo).length === 0) {
    return null;
  }
  
  return (
    <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Saldos por Tipo de Responsable</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {Object.entries(resumen.por_tipo).map(([tipo, data]) => {
            const tipoInfo = getTipoResponsableInfo(tipo);
            const Icon = tipoInfo.icon;
            return (
              <div 
                key={tipo}
                className="p-3 rounded-lg border text-center"
                style={{ borderColor: 'var(--border-color)' }}
              >
                <div className={`w-10 h-10 rounded-full ${tipoInfo.color} flex items-center justify-center mx-auto mb-2`}>
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  {tipoInfo.label}
                </p>
                <p className="font-bold text-orange-600">
                  {formatCurrency(data.pendiente)}
                </p>
                <p className="text-xs text-slate-500">
                  {data.cantidad} cuentas
                </p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
