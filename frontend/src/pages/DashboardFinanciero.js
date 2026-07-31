// /app/frontend/src/pages/DashboardFinanciero.js
// Dashboard Financiero - Solo SuperAdmin
// Muestra ingresos de Caja y gastos de la empresa

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast, Toaster } from 'sonner';
import { 
  TrendingUp, TrendingDown, DollarSign, CreditCard, 
  Download, FileSpreadsheet, FileText, Calendar,
  ArrowUpRight, ArrowDownRight, Wallet, Receipt
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import api, { formatCurrency, formatDate } from '../services/api';

const DashboardFinanciero = () => {
  const [loading, setLoading] = useState(true);
  const [datos, setDatos] = useState(null);
  const [periodo, setPeriodo] = useState('mes_actual');
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [exportando, setExportando] = useState(false);

  // Colores para gráficos
  const COLORS = ['#0D7377', '#14919B', '#0AD1C8', '#45E3D6', '#7FF0E6', '#B3F7F0'];
  const COLORS_GASTOS = ['#DC2626', '#F97316', '#EAB308', '#84CC16'];

  const cargarDatos = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ periodo });
      if (periodo === 'personalizado' && fechaInicio && fechaFin) {
        params.append('fecha_inicio', fechaInicio);
        params.append('fecha_fin', fechaFin);
      }
      
      const response = await api.get(`/dashboard/financiero?${params}`);
      setDatos(response.data);
    } catch (error) {
      console.error('Error cargando dashboard:', error);
      if (error.response?.status === 403) {
        toast.error('No tiene permisos para acceder al Dashboard Financiero');
      } else {
        toast.error('Error al cargar datos del dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, [periodo, fechaInicio, fechaFin]);

  useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);

  const handleExportar = async (formato) => {
    setExportando(true);
    try {
      const params = new URLSearchParams({ formato, periodo });
      if (periodo === 'personalizado' && fechaInicio && fechaFin) {
        params.append('fecha_inicio', fechaInicio);
        params.append('fecha_fin', fechaFin);
      }
      
      const response = await api.get(`/dashboard/financiero/exportar?${params}`, {
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `reporte_financiero.${formato === 'excel' ? 'xlsx' : 'pdf'}`;
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Reporte exportado exitosamente a ${formato.toUpperCase()}`);
    } catch (error) {
      console.error('Error exportando:', error);
      toast.error('Error al exportar el reporte');
    } finally {
      setExportando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2" style={{ borderColor: 'var(--accent-primary)' }}></div>
      </div>
    );
  }

  if (!datos) {
    return (
      <div className="p-6" style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
        <p>No se pudieron cargar los datos del dashboard.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: 'var(--bg-primary)', minHeight: '100vh' }}>
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Dashboard Financiero
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            {datos.periodo.nombre}
          </p>
        </div>
        
        {/* Filtros y Exportar */}
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label className="text-xs" style={{ color: 'var(--text-hint)' }}>Período</Label>
            <Select value={periodo} onValueChange={setPeriodo}>
              <SelectTrigger className="w-40" style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}>
                <SelectItem value="mes_actual">Mes actual</SelectItem>
                <SelectItem value="semestre">Últimos 6 meses</SelectItem>
                <SelectItem value="anual">Año actual</SelectItem>
                <SelectItem value="personalizado">Personalizado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {periodo === 'personalizado' && (
            <>
              <div className="space-y-1">
                <Label className="text-xs" style={{ color: 'var(--text-hint)' }}>Desde</Label>
                <Input
                  type="date"
                  value={fechaInicio}
                  onChange={(e) => setFechaInicio(e.target.value)}
                  className="w-36"
                  style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs" style={{ color: 'var(--text-hint)' }}>Hasta</Label>
                <Input
                  type="date"
                  value={fechaFin}
                  onChange={(e) => setFechaFin(e.target.value)}
                  className="w-36"
                  style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
                />
              </div>
              <Button 
                onClick={cargarDatos}
                style={{ backgroundColor: 'var(--accent-primary)', color: 'white' }}
              >
                Aplicar
              </Button>
            </>
          )}
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportar('excel')}
              disabled={exportando}
              style={{ borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
              data-testid="export-excel-btn"
            >
              <FileSpreadsheet className="w-4 h-4 mr-1" />
              Excel
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExportar('pdf')}
              disabled={exportando}
              style={{ borderColor: 'var(--border-primary)', color: 'var(--text-primary)' }}
              data-testid="export-pdf-btn"
            >
              <FileText className="w-4 h-4 mr-1" />
              PDF
            </Button>
          </div>
        </div>
      </div>

      {/* KPIs Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Ingresos Cobrados */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }} data-testid="kpi-ingresos">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-hint)' }}>Ingresos Cobrados</p>
                <p className="text-2xl font-bold" style={{ color: '#10B981' }}>
                  {formatCurrency(datos.ingresos.total_cobrado)}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Caja: {formatCurrency(datos.ingresos.de_caja_directa)} | CxC: {formatCurrency(datos.ingresos.de_abonos_cxc)}
                </p>
              </div>
              <div className="p-3 rounded-full" style={{ backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>
                <TrendingUp className="w-6 h-6" style={{ color: '#10B981' }} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gastos Pagados */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }} data-testid="kpi-gastos">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-hint)' }}>Gastos Pagados</p>
                <p className="text-2xl font-bold" style={{ color: '#EF4444' }}>
                  {formatCurrency(datos.gastos.pagado)}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Pendiente: {formatCurrency(datos.gastos.pendiente)}
                </p>
              </div>
              <div className="p-3 rounded-full" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)' }}>
                <TrendingDown className="w-6 h-6" style={{ color: '#EF4444' }} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Balance Neto */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }} data-testid="kpi-balance">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-hint)' }}>Balance Neto</p>
                <p className="text-2xl font-bold" style={{ color: datos.balance.positivo ? '#10B981' : '#EF4444' }}>
                  {formatCurrency(datos.balance.neto)}
                </p>
                <p className="text-xs mt-1 flex items-center gap-1" style={{ color: datos.balance.positivo ? '#10B981' : '#EF4444' }}>
                  {datos.balance.positivo ? (
                    <><ArrowUpRight className="w-3 h-3" /> Ganancia</>
                  ) : (
                    <><ArrowDownRight className="w-3 h-3" /> Pérdida</>
                  )}
                </p>
              </div>
              <div className="p-3 rounded-full" style={{ backgroundColor: datos.balance.positivo ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }}>
                <Wallet className="w-6 h-6" style={{ color: datos.balance.positivo ? '#10B981' : '#EF4444' }} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CxC Pendientes */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }} data-testid="kpi-cxc">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-hint)' }}>CxC Pendientes</p>
                <p className="text-2xl font-bold" style={{ color: '#F59E0B' }}>
                  {formatCurrency(datos.cuentas_por_cobrar.total_pendiente)}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Por cobrar a clientes
                </p>
              </div>
              <div className="p-3 rounded-full" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)' }}>
                <Receipt className="w-6 h-6" style={{ color: '#F59E0B' }} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de Barras - Ingresos vs Gastos mensual */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }}>
          <CardHeader>
            <CardTitle style={{ color: 'var(--text-primary)' }}>Ingresos vs Gastos Mensual</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={datos.evolucion_mensual}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                <XAxis dataKey="mes_nombre" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} tickFormatter={(v) => `Q${(v/1000).toFixed(0)}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: '8px' }}
                  labelStyle={{ color: 'var(--text-primary)' }}
                  formatter={(value) => [`Q ${value.toLocaleString('es-GT', { minimumFractionDigits: 2 })}`, '']}
                />
                <Legend />
                <Bar dataKey="ingresos" name="Ingresos" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="gastos" name="Gastos" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Gráfico de Línea - Balance acumulado */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }}>
          <CardHeader>
            <CardTitle style={{ color: 'var(--text-primary)' }}>Balance Mensual</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={datos.evolucion_mensual}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
                <XAxis dataKey="mes_nombre" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} tickFormatter={(v) => `Q${(v/1000).toFixed(0)}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: '8px' }}
                  labelStyle={{ color: 'var(--text-primary)' }}
                  formatter={(value) => [`Q ${value.toLocaleString('es-GT', { minimumFractionDigits: 2 })}`, 'Balance']}
                />
                <Line 
                  type="monotone" 
                  dataKey="balance" 
                  stroke="#0D7377" 
                  strokeWidth={3}
                  dot={{ fill: '#0D7377', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#0D7377' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Desglose por categorías */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ingresos por Pagador */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }}>
          <CardHeader>
            <CardTitle style={{ color: 'var(--text-primary)' }}>Ingresos por Tipo de Pagador</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={datos.ingresos_por_pagador}
                    dataKey="monto"
                    nameKey="tipo"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={false}
                  >
                    {datos.ingresos_por_pagador.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: '8px' }}
                    formatter={(value) => [`Q ${value.toLocaleString('es-GT', { minimumFractionDigits: 2 })}`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {datos.ingresos_por_pagador.slice(0, 5).map((item, index) => (
                  <div key={item.tipo} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.tipo}</span>
                    </div>
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {formatCurrency(item.monto)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gastos por Categoría */}
        <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }}>
          <CardHeader>
            <CardTitle style={{ color: 'var(--text-primary)' }}>Gastos por Categoría</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={datos.gastos_por_categoria}
                    dataKey="monto"
                    nameKey="categoria"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={false}
                  >
                    {datos.gastos_por_categoria.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS_GASTOS[index % COLORS_GASTOS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: '8px' }}
                    formatter={(value) => [`Q ${value.toLocaleString('es-GT', { minimumFractionDigits: 2 })}`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {datos.gastos_por_categoria.map((item, index) => (
                  <div key={item.categoria} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS_GASTOS[index % COLORS_GASTOS.length] }}></div>
                      <span className="text-sm capitalize" style={{ color: 'var(--text-secondary)' }}>{item.categoria}</span>
                    </div>
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {formatCurrency(item.monto)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Desglose Ingresos por Método */}
      <Card style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-primary)' }}>
        <CardHeader>
          <CardTitle style={{ color: 'var(--text-primary)' }}>Ingresos por Método de Pago</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5" style={{ color: '#10B981' }} />
                <span className="text-sm" style={{ color: 'var(--text-hint)' }}>Efectivo</span>
              </div>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {formatCurrency(datos.ingresos.efectivo)}
              </p>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div className="flex items-center gap-2 mb-2">
                <CreditCard className="w-5 h-5" style={{ color: '#3B82F6' }} />
                <span className="text-sm" style={{ color: 'var(--text-hint)' }}>Tarjeta</span>
              </div>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {formatCurrency(datos.ingresos.tarjeta)}
              </p>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div className="flex items-center gap-2 mb-2">
                <ArrowUpRight className="w-5 h-5" style={{ color: '#8B5CF6' }} />
                <span className="text-sm" style={{ color: 'var(--text-hint)' }}>Transferencia</span>
              </div>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {formatCurrency(datos.ingresos.transferencia)}
              </p>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-5 h-5" style={{ color: '#F59E0B' }} />
                <span className="text-sm" style={{ color: 'var(--text-hint)' }}>Cheque</span>
              </div>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {formatCurrency(datos.ingresos.cheque)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DashboardFinanciero;
