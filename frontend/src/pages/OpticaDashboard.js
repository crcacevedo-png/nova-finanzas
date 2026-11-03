// /app/frontend/src/pages/OpticaDashboard.js
// Dashboard completo de Óptica con Rentabilidad, Ventas del Día, Informes Mensuales y Por Origen

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Label } from '../components/ui/label';
import {
  TrendingUp, TrendingDown, DollarSign, ShoppingCart, Calendar,
  RefreshCw, Download, Eye, Package, Users, Building2, FileText,
  BarChart3, PieChart, Clock, CreditCard, Percent, ArrowUpRight, ArrowDownRight, Target, Pencil
} from 'lucide-react';
import { Input } from '../components/ui/input';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import { opticaSaleApi, formatCurrency, formatDate, getGuatemalaDate } from '../services/api';
import { toast } from 'sonner';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

const OpticaDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('resumen');
  
  // Estados de datos
  const [ventasDia, setVentasDia] = useState(null);
  const [rentabilidad, setRentabilidad] = useState(null);
  const [ventasOrigen, setVentasOrigen] = useState(null);
  const [informeMensual, setInformeMensual] = useState(null);
  const [historialMensual, setHistorialMensual] = useState(null);
  const [metas, setMetas] = useState(null);

  // Dialog de metas
  const [metasDialogOpen, setMetasDialogOpen] = useState(false);
  const [metaMensualInput, setMetaMensualInput] = useState('');
  const [savingMetas, setSavingMetas] = useState(false);
  
  // Filtros
  const [periodoRentabilidad, setPeriodoRentabilidad] = useState('mes');
  const [mesInforme, setMesInforme] = useState(parseInt(getGuatemalaDate().split('-')[1], 10));
  const [yearInforme, setYearInforme] = useState(parseInt(getGuatemalaDate().split('-')[0], 10));

  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      
      const [ventasDiaRes, rentabilidadRes, ventasOrigenRes, historialRes, metasRes] = await Promise.all([
        opticaSaleApi.getVentasDelDia(),
        opticaSaleApi.getRentabilidad(periodoRentabilidad),
        opticaSaleApi.getVentasPorOrigen(),
        opticaSaleApi.getHistorialMensual(12),
        opticaSaleApi.getMetas()
      ]);
      
      setVentasDia(ventasDiaRes.data);
      setRentabilidad(rentabilidadRes.data);
      setVentasOrigen(ventasOrigenRes.data);
      setHistorialMensual(historialRes.data);
      setMetas(metasRes.data);
      
    } catch (error) {
      console.error('Error cargando dashboard:', error);
      toast.error('Error al cargar datos del dashboard');
    } finally {
      setLoading(false);
    }
  }, [periodoRentabilidad]);

  const openMetasDialog = () => {
    setMetaMensualInput(metas?.meta_mensual ? String(metas.meta_mensual) : '');
    setMetasDialogOpen(true);
  };

  const handleSaveMetas = async () => {
    const mensual = parseFloat(metaMensualInput) || 0;
    if (mensual < 0) {
      toast.error('La meta no puede ser negativa');
      return;
    }
    try {
      setSavingMetas(true);
      await opticaSaleApi.setMetas({ meta_diaria: 0, meta_mensual: mensual });
      toast.success('Metas de ventas actualizadas');
      setMetasDialogOpen(false);
      await loadDashboardData();
    } catch (error) {
      console.error('Error guardando metas:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar las metas');
    } finally {
      setSavingMetas(false);
    }
  };

  const loadInformeMensual = useCallback(async () => {
    try {
      const res = await opticaSaleApi.getInformeMensual(yearInforme, mesInforme);
      setInformeMensual(res.data);
    } catch (error) {
      console.error('Error cargando informe:', error);
      toast.error('Error al cargar informe mensual');
    }
  }, [yearInforme, mesInforme]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    if (activeTab === 'informes') {
      loadInformeMensual();
    }
  }, [activeTab, loadInformeMensual]);

  const exportarInformeCSV = () => {
    if (!informeMensual) return;
    
    const lines = [
      `INFORME MENSUAL DE ÓPTICA - ${informeMensual.periodo}`,
      '',
      'VENTAS',
      `Total Ventas,${informeMensual.ventas.total}`,
      `Total Cobrado,${informeMensual.ventas.cobrado}`,
      `Pendiente por Cobrar,${informeMensual.ventas.pendiente}`,
      `Descuentos Aplicados,${informeMensual.ventas.descuentos}`,
      `Número de Órdenes,${informeMensual.ventas.num_ordenes}`,
      `Promedio por Orden,${informeMensual.ventas.promedio_orden}`,
      '',
      'COMPRAS',
      `Total Compras,${informeMensual.compras.total}`,
      `Número de Compras,${informeMensual.compras.num_compras}`,
      '',
      'BALANCE',
      `Ingresos (Cobrado),${informeMensual.balance.ingresos}`,
      `Egresos (Compras),${informeMensual.balance.egresos}`,
      `Resultado,${informeMensual.balance.resultado}`,
    ];
    
    const csvContent = lines.join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `informe_optica_${informeMensual.periodo.replace(' ', '_')}.csv`;
    link.click();
    toast.success('Informe exportado');
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' && entry.name !== 'Órdenes' 
                ? formatCurrency(entry.value) 
                : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </Layout>
    );
  }

  // Preparar datos para gráfica de orígenes
  const pieDataOrigen = ventasOrigen ? Object.entries(ventasOrigen.origenes)
    .filter(([key, val]) => val.total > 0)
    .map(([key, val], idx) => ({
      name: val.label,
      value: val.total,
      count: val.count,
      color: COLORS[idx % COLORS.length]
    })) : [];

  return (
    <Layout>
      <div className="space-y-6" data-testid="optica-dashboard">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Eye className="w-7 h-7 text-blue-600" />
              Dashboard de Óptica
            </h1>
            <p className="text-gray-500 mt-1">Análisis de ventas, rentabilidad e informes</p>
          </div>
          <Button variant="outline" onClick={loadDashboardData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>

        {/* Tarjetas de Resumen Principal */}
        {ventasDia && rentabilidad && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="optica-summary-cards">
            {/* Ventas del Día */}
            <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200" data-testid="card-ventas-hoy">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-600 font-medium">Ventas Hoy</p>
                    <p className="text-2xl font-bold text-blue-800 mt-1">
                      {formatCurrency(ventasDia.total_ventas)}
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      {ventasDia.num_ordenes} órdenes
                    </p>
                  </div>
                  <div className="p-3 bg-blue-200 rounded-full">
                    <ShoppingCart className="w-6 h-6 text-blue-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cobrado Hoy */}
            <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200" data-testid="card-cobrado-hoy">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-600 font-medium">Cobrado Hoy</p>
                    <p className="text-2xl font-bold text-green-800 mt-1">
                      {formatCurrency(ventasDia.total_cobrado)}
                    </p>
                    <p className="text-xs text-green-600 mt-1">
                      Pendiente hoy: {formatCurrency(ventasDia.saldo_pendiente)}
                    </p>
                  </div>
                  <div className="p-3 bg-green-200 rounded-full">
                    <DollarSign className="w-6 h-6 text-green-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cuentas por Cobrar */}
            <Card className="bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200" data-testid="card-cuentas-por-cobrar">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-amber-700 font-medium">Cuentas por Cobrar</p>
                    <p className="text-2xl font-bold text-amber-800 mt-1">
                      {formatCurrency(ventasDia.cuentas_por_cobrar)}
                    </p>
                    <p className="text-xs text-amber-600 mt-1">
                      {ventasDia.cuentas_por_cobrar_count} órdenes pendientes
                    </p>
                  </div>
                  <div className="p-3 bg-amber-200 rounded-full">
                    <CreditCard className="w-6 h-6 text-amber-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Rentabilidad / Margen del Mes */}
            <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200" data-testid="card-rentabilidad-mes">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-purple-600 font-medium">Rentabilidad ({periodoRentabilidad})</p>
                    <p className={`text-2xl font-bold mt-1 ${
                      rentabilidad.margen_porcentaje >= 30 ? 'text-green-600' : 
                      rentabilidad.margen_porcentaje >= 20 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {rentabilidad.margen_porcentaje.toFixed(1)}%
                    </p>
                    <p className="text-xs text-purple-600 mt-1">
                      Ganancia: {formatCurrency(rentabilidad.ganancia_bruta)}
                    </p>
                  </div>
                  <div className="p-3 bg-purple-200 rounded-full">
                    <Percent className="w-6 h-6 text-purple-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pagos de Óptica (compras/egresos) */}
            <Card className="bg-gradient-to-br from-rose-50 to-rose-100 border-rose-200" data-testid="card-pagos-optica">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-rose-600 font-medium">Pagos de Óptica ({periodoRentabilidad})</p>
                    <p className="text-2xl font-bold text-rose-800 mt-1">
                      {formatCurrency(rentabilidad.total_compras)}
                    </p>
                    <p className="text-xs text-rose-600 mt-1">
                      {rentabilidad.num_compras} compras
                    </p>
                  </div>
                  <div className="p-3 bg-rose-200 rounded-full">
                    <ArrowDownRight className="w-6 h-6 text-rose-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Ingresos del Mes */}
            <Card className="bg-gradient-to-br from-cyan-50 to-cyan-100 border-cyan-200" data-testid="card-ingresos-mes">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-cyan-700 font-medium">Ingresos ({periodoRentabilidad})</p>
                    <p className="text-2xl font-bold text-cyan-800 mt-1">
                      {formatCurrency(rentabilidad.total_ingresos)}
                    </p>
                    <p className="text-xs text-cyan-600 mt-1">
                      {rentabilidad.num_ventas} ventas
                    </p>
                  </div>
                  <div className="p-3 bg-cyan-200 rounded-full">
                    <TrendingUp className="w-6 h-6 text-cyan-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Utilidad del Mes */}
            <Card className={`bg-gradient-to-br border ${
              rentabilidad.utilidad >= 0 ? 'from-emerald-50 to-emerald-100 border-emerald-200' : 'from-red-50 to-red-100 border-red-200'
            }`} data-testid="card-utilidad-mes">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${rentabilidad.utilidad >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                      Utilidad ({periodoRentabilidad})
                    </p>
                    <p className={`text-2xl font-bold mt-1 ${rentabilidad.utilidad >= 0 ? 'text-emerald-800' : 'text-red-700'}`}>
                      {rentabilidad.utilidad >= 0 ? '' : '-'}{formatCurrency(Math.abs(rentabilidad.utilidad))}
                    </p>
                    <p className={`text-xs mt-1 ${rentabilidad.utilidad >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      Ingresos − Pagos
                    </p>
                  </div>
                  <div className={`p-3 rounded-full ${rentabilidad.utilidad >= 0 ? 'bg-emerald-200' : 'bg-red-200'}`}>
                    {rentabilidad.utilidad >= 0
                      ? <ArrowUpRight className="w-6 h-6 text-emerald-700" />
                      : <ArrowDownRight className="w-6 h-6 text-red-700" />}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Meta de Ventas */}
        {metas && (
          <Card className="border-slate-200" data-testid="metas-ventas-card">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Target className="w-5 h-5 text-indigo-600" />
                  Meta de Ventas
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openMetasDialog}
                  data-testid="edit-metas-btn"
                >
                  <Pencil className="w-4 h-4 mr-1.5" />
                  Definir metas
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {metas.meta_mensual > 0 ? (
                <div>
                  {/* Meta del mes */}
                  <div data-testid="meta-mes-progress">
                    <div className="flex items-baseline justify-between mb-1.5">
                      <span className="text-sm font-medium text-slate-700">Meta del Mes</span>
                      <span className="text-sm font-semibold text-amber-600">{metas.progreso_mes}%</span>
                    </div>
                    <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${metas.progreso_mes >= 100 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                        style={{ width: `${Math.min(metas.progreso_mes, 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between mt-1.5 text-xs">
                      <span className="text-slate-600">{formatCurrency(metas.ventas_mes)} / {formatCurrency(metas.meta_mensual)}</span>
                      {metas.progreso_mes >= 100
                        ? <span className="text-emerald-600 font-medium">¡Meta alcanzada!</span>
                        : <span className="text-slate-500">Faltan {formatCurrency(metas.falta_mes)}</span>}
                    </div>
                    {metas.proyeccion_mes != null && (
                      <div
                        className={`mt-2 flex items-center gap-1.5 text-xs rounded-md px-2.5 py-1.5 ${metas.proyeccion_mes >= metas.meta_mensual ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}
                        data-testid="meta-mes-proyeccion"
                      >
                        <TrendingUp className="w-3.5 h-3.5 shrink-0" />
                        <span>
                          A este ritmo cerrarás el mes en <span className="font-semibold">{formatCurrency(metas.proyeccion_mes)}</span>
                          {metas.proyeccion_mes >= metas.meta_mensual ? ' — ¡superarás la meta!' : ' — por debajo de la meta'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-6 text-center" data-testid="metas-empty-state">
                  <Target className="w-8 h-8 text-slate-300 mb-2" />
                  <p className="text-sm text-slate-500">Aún no has definido metas de ventas.</p>
                  <Button variant="link" className="text-indigo-600" onClick={openMetasDialog} data-testid="metas-empty-define-btn">
                    Definir metas ahora
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Dialog Definir Metas */}
        <Dialog open={metasDialogOpen} onOpenChange={setMetasDialogOpen}>
          <DialogContent data-testid="metas-dialog">
            <DialogHeader>
              <DialogTitle>Definir metas de ventas</DialogTitle>
              <DialogDescription>
                Establece el objetivo de ventas del mes (en Quetzales).
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label htmlFor="meta-mensual">Meta mensual (Q)</Label>
                <Input
                  id="meta-mensual"
                  type="number"
                  min="0"
                  step="any"
                  value={metaMensualInput}
                  onChange={(e) => setMetaMensualInput(e.target.value)}
                  placeholder="Ej. 40000"
                  data-testid="meta-mensual-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setMetasDialogOpen(false)} data-testid="metas-cancel-btn">
                Cancelar
              </Button>
              <Button onClick={handleSaveMetas} disabled={savingMetas} data-testid="metas-save-btn">
                {savingMetas ? 'Guardando...' : 'Guardar metas'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Tabs de Contenido */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full max-w-2xl grid-cols-4">
            <TabsTrigger value="resumen" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Resumen
            </TabsTrigger>
            <TabsTrigger value="rentabilidad" className="flex items-center gap-2">
              <Percent className="w-4 h-4" />
              Rentabilidad
            </TabsTrigger>
            <TabsTrigger value="origen" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Por Origen
            </TabsTrigger>
            <TabsTrigger value="informes" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Informes
            </TabsTrigger>
          </TabsList>

          {/* Tab: Resumen */}
          <TabsContent value="resumen" className="space-y-4">
            {/* Ventas del Día */}
            {ventasDia && ventasDia.ventas && ventasDia.ventas.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Clock className="w-5 h-5 text-blue-600" />
                    Ventas del Día ({ventasDia.ventas.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-64">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left">Orden</th>
                          <th className="px-3 py-2 text-left">Paciente</th>
                          <th className="px-3 py-2 text-right">Total</th>
                          <th className="px-3 py-2 text-right">Pagado</th>
                          <th className="px-3 py-2 text-center">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {ventasDia.ventas.map((venta) => (
                          <tr key={venta.id} className="hover:bg-gray-50">
                            <td className="px-3 py-2 font-mono text-xs">{venta.order_number}</td>
                            <td className="px-3 py-2">{venta.patient_name}</td>
                            <td className="px-3 py-2 text-right font-medium">{formatCurrency(venta.total)}</td>
                            <td className="px-3 py-2 text-right text-green-600">{formatCurrency(venta.total_paid)}</td>
                            <td className="px-3 py-2 text-center">
                              <Badge variant={venta.status === 'pagado' ? 'success' : 'warning'}>
                                {venta.status}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Gráfica Historial Mensual */}
            {activeTab === 'resumen' && historialMensual && historialMensual.historial.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Historial de Ventas y Compras</CardTitle>
                  <CardDescription>Últimos 12 meses</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={historialMensual.historial}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                        <YAxis tickFormatter={(v) => `Q${(v/1000).toFixed(0)}k`} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar dataKey="ventas" name="Ventas" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="compras" name="Compras" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                        <Line type="monotone" dataKey="ganancia" name="Ganancia" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Tab: Rentabilidad */}
          <TabsContent value="rentabilidad" className="space-y-4">
            <div className="flex items-center gap-4 mb-4">
              <Label>Período:</Label>
              <Select value={periodoRentabilidad} onValueChange={setPeriodoRentabilidad}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dia">Hoy</SelectItem>
                  <SelectItem value="semana">Última Semana</SelectItem>
                  <SelectItem value="mes">Este Mes</SelectItem>
                  <SelectItem value="año">Este Año</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {rentabilidad && (
              <>
                {/* Resumen de Rentabilidad */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="p-5">
                      <p className="text-sm text-gray-500">Ingresos por Ventas</p>
                      <p className="text-2xl font-bold text-gray-800">{formatCurrency(rentabilidad.total_ingresos)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-5">
                      <p className="text-sm text-gray-500">Costo de Productos</p>
                      <p className="text-2xl font-bold text-gray-800">{formatCurrency(rentabilidad.total_costos)}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-green-50">
                    <CardContent className="p-5">
                      <p className="text-sm text-green-600">Ganancia Bruta</p>
                      <p className="text-2xl font-bold text-green-700">{formatCurrency(rentabilidad.ganancia_bruta)}</p>
                      <p className="text-sm text-green-600 mt-1">Margen: {rentabilidad.margen_porcentaje.toFixed(1)}%</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Desglose por Categoría */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Rentabilidad por Categoría</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-y">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ingresos</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costos</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ganancia</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Margen</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {Object.entries(rentabilidad.desglose_categorias)
                            .filter(([_, cat]) => cat.cantidad > 0 || cat.ingresos > 0)
                            .map(([key, cat]) => (
                            <tr key={key} className="hover:bg-gray-50">
                              <td className="px-4 py-3 font-medium">
                                {{
                                  aros: 'Aros/Monturas',
                                  lentes_contacto: 'Lentes de Contacto',
                                  tipos_lente: 'Tipos de Lente',
                                  accesorios: 'Accesorios',
                                  otros: 'Otros'
                                }[key] || key}
                              </td>
                              <td className="px-4 py-3 text-center">{cat.cantidad}</td>
                              <td className="px-4 py-3 text-right">{formatCurrency(cat.ingresos)}</td>
                              <td className="px-4 py-3 text-right text-gray-600">{formatCurrency(cat.costos)}</td>
                              <td className="px-4 py-3 text-right font-medium text-green-600">
                                {formatCurrency(cat.ganancia)}
                              </td>
                              <td className="px-4 py-3 text-center">
                                <Badge variant={cat.margen >= 30 ? 'success' : cat.margen >= 20 ? 'warning' : 'destructive'}>
                                  {cat.margen.toFixed(1)}%
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>

          {/* Tab: Por Origen */}
          <TabsContent value="origen" className="space-y-4">
            {ventasOrigen && (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Gráfica de Pastel */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Distribución por Origen</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-72">
                        <ResponsiveContainer width="100%" height="100%">
                          <RechartsPie>
                            <Pie
                              data={pieDataOrigen}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={100}
                              paddingAngle={2}
                              dataKey="value"
                              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                              labelLine={false}
                            >
                              {pieDataOrigen.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => formatCurrency(value)} />
                          </RechartsPie>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Tabla de Orígenes */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Detalle por Origen</CardTitle>
                      <CardDescription>Total: {formatCurrency(ventasOrigen.total_general)}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(ventasOrigen.origenes)
                          .filter(([_, v]) => v.total > 0)
                          .sort((a, b) => b[1].total - a[1].total)
                          .map(([key, origen], idx) => (
                          <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                              <div>
                                <p className="font-medium">{origen.label}</p>
                                <p className="text-xs text-gray-500">{origen.count} órdenes</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="font-bold">{formatCurrency(origen.total)}</p>
                              <p className="text-xs text-gray-500">{origen.porcentaje}%</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Desglose IGSS */}
                {ventasOrigen.origenes.igss && Object.keys(ventasOrigen.origenes.igss.unidades || {}).length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Building2 className="w-5 h-5" />
                        Desglose IGSS por Unidad
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {Object.entries(ventasOrigen.origenes.igss.unidades)
                          .sort((a, b) => b[1].total - a[1].total)
                          .map(([unidad, datos]) => (
                          <div key={unidad} className="p-3 border rounded-lg">
                            <p className="font-medium text-sm">{unidad}</p>
                            <p className="text-lg font-bold text-blue-600">{formatCurrency(datos.total)}</p>
                            <p className="text-xs text-gray-500">{datos.count} órdenes</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Desglose Otras Instituciones */}
                {ventasOrigen.origenes.otra && Object.keys(ventasOrigen.origenes.otra.instituciones || {}).length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Building2 className="w-5 h-5" />
                        Otras Instituciones
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {Object.entries(ventasOrigen.origenes.otra.instituciones)
                          .sort((a, b) => b[1].total - a[1].total)
                          .map(([inst, datos]) => (
                          <div key={inst} className="p-3 border rounded-lg">
                            <p className="font-medium text-sm">{inst}</p>
                            <p className="text-lg font-bold text-purple-600">{formatCurrency(datos.total)}</p>
                            <p className="text-xs text-gray-500">{datos.count} órdenes</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </TabsContent>

          {/* Tab: Informes */}
          <TabsContent value="informes" className="space-y-4">
            <div className="flex items-center gap-4">
              <Label>Mes:</Label>
              <Select value={mesInforme.toString()} onValueChange={(v) => setMesInforme(parseInt(v))}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
                    .map((m, i) => (
                    <SelectItem key={i+1} value={(i+1).toString()}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={yearInforme.toString()} onValueChange={(v) => setYearInforme(parseInt(v))}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 4 }, (_, i) => new Date().getFullYear() - 2 + i).map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={loadInformeMensual} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                Generar
              </Button>
              <Button onClick={exportarInformeCSV} disabled={!informeMensual}>
                <Download className="w-4 h-4 mr-2" />
                Exportar CSV
              </Button>
            </div>

            {informeMensual && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Ventas */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg text-blue-600">Ventas</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Vendido:</span>
                        <span className="font-bold">{formatCurrency(informeMensual.ventas.total)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Cobrado:</span>
                        <span className="font-bold text-green-600">{formatCurrency(informeMensual.ventas.cobrado)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Pendiente:</span>
                        <span className="font-bold text-amber-600">{formatCurrency(informeMensual.ventas.pendiente)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Descuentos:</span>
                        <span className="text-red-600">{formatCurrency(informeMensual.ventas.descuentos)}</span>
                      </div>
                      <hr />
                      <div className="flex justify-between">
                        <span className="text-gray-600">Órdenes:</span>
                        <span>{informeMensual.ventas.num_ordenes}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Promedio/Orden:</span>
                        <span>{formatCurrency(informeMensual.ventas.promedio_orden)}</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Compras */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg text-amber-600">Compras</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Compras:</span>
                        <span className="font-bold">{formatCurrency(informeMensual.compras.total)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Núm. Compras:</span>
                        <span>{informeMensual.compras.num_compras}</span>
                      </div>
                      <hr />
                      <p className="text-sm font-medium text-gray-700 mt-2">Por Categoría:</p>
                      {Object.entries(informeMensual.compras.por_categoria || {}).map(([cat, datos]) => (
                        <div key={cat} className="flex justify-between text-sm">
                          <span className="text-gray-600 capitalize">{cat}:</span>
                          <span>{formatCurrency(datos.total)}</span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {/* Balance */}
                  <Card className={informeMensual.balance.resultado >= 0 ? 'bg-green-50' : 'bg-red-50'}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">Balance del Mes</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Ingresos:</span>
                        <span className="font-bold text-green-600">{formatCurrency(informeMensual.balance.ingresos)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Egresos:</span>
                        <span className="font-bold text-red-600">{formatCurrency(informeMensual.balance.egresos)}</span>
                      </div>
                      <hr />
                      <div className="flex justify-between items-center pt-2">
                        <span className="font-medium">Resultado:</span>
                        <span className={`text-2xl font-bold ${informeMensual.balance.resultado >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {informeMensual.balance.resultado >= 0 ? '+' : ''}{formatCurrency(informeMensual.balance.resultado)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Top Productos */}
                {informeMensual.top_productos && informeMensual.top_productos.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Top 10 Productos Vendidos</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-2 text-left">#</th>
                              <th className="px-4 py-2 text-left">Producto</th>
                              <th className="px-4 py-2 text-center">Cantidad</th>
                              <th className="px-4 py-2 text-right">Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {informeMensual.top_productos.map((prod, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-2 font-medium">{idx + 1}</td>
                                <td className="px-4 py-2">{prod.nombre}</td>
                                <td className="px-4 py-2 text-center">{prod.cantidad}</td>
                                <td className="px-4 py-2 text-right font-medium">{formatCurrency(prod.total)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default OpticaDashboard;
