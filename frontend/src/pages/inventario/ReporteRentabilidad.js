// /app/frontend/src/pages/inventario/ReporteRentabilidad.js
// Reporte de Rentabilidad por Categoría de Productos con Gráfica Histórica

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  TrendingUp, TrendingDown, DollarSign, Package, BarChart3, 
  RefreshCw, Download, PieChart, Calendar, ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { toast } from 'sonner';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart
} from 'recharts';

const ReporteRentabilidad = () => {
  const [loading, setLoading] = useState(true);
  const [loadingHistorico, setLoadingHistorico] = useState(true);
  const [data, setData] = useState(null);
  const [dataHistorico, setDataHistorico] = useState(null);
  const [soloConStock, setSoloConStock] = useState(false);
  const [mesesHistorico, setMesesHistorico] = useState(12);
  const [activeTab, setActiveTab] = useState('categorias');

  const loadReporte = useCallback(async () => {
    try {
      setLoading(true);
      const res = await inventarioApi.getReporteRentabilidadCategorias({ solo_con_stock: soloConStock });
      setData(res.data);
    } catch (error) {
      console.error('Error cargando reporte:', error);
      toast.error('Error al cargar el reporte de rentabilidad');
    } finally {
      setLoading(false);
    }
  }, [soloConStock]);

  const loadHistorico = useCallback(async () => {
    try {
      setLoadingHistorico(true);
      const res = await inventarioApi.getReporteRentabilidadHistorico({ meses: mesesHistorico });
      setDataHistorico(res.data);
    } catch (error) {
      console.error('Error cargando histórico:', error);
      // No mostrar error si simplemente no hay datos
    } finally {
      setLoadingHistorico(false);
    }
  }, [mesesHistorico]);

  useEffect(() => {
    loadReporte();
    loadHistorico();
  }, [loadReporte, loadHistorico]);

  const getMargenColor = (margen) => {
    if (margen >= 40) return 'text-green-600';
    if (margen >= 30) return 'text-emerald-600';
    if (margen >= 20) return 'text-amber-600';
    if (margen >= 10) return 'text-orange-600';
    return 'text-red-600';
  };

  const getMargenBadge = (margen) => {
    if (margen >= 40) return <Badge className="bg-green-100 text-green-800">Excelente</Badge>;
    if (margen >= 30) return <Badge className="bg-emerald-100 text-emerald-800">Bueno</Badge>;
    if (margen >= 20) return <Badge className="bg-amber-100 text-amber-800">Regular</Badge>;
    if (margen >= 10) return <Badge className="bg-orange-100 text-orange-800">Bajo</Badge>;
    return <Badge className="bg-red-100 text-red-800">Crítico</Badge>;
  };

  const getProgressColor = (margen) => {
    if (margen >= 40) return 'bg-green-500';
    if (margen >= 30) return 'bg-emerald-500';
    if (margen >= 20) return 'bg-amber-500';
    if (margen >= 10) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getTendenciaIcon = (tendencia) => {
    if (tendencia === 'creciente') return <ArrowUpRight className="w-5 h-5 text-green-600" />;
    if (tendencia === 'decreciente') return <ArrowDownRight className="w-5 h-5 text-red-600" />;
    return <Minus className="w-5 h-5 text-gray-500" />;
  };

  const getTendenciaColor = (tendencia) => {
    if (tendencia === 'creciente') return 'text-green-600';
    if (tendencia === 'decreciente') return 'text-red-600';
    return 'text-gray-600';
  };

  const exportarCSV = () => {
    if (!data) return;
    
    const headers = ['Categoría', 'Productos', 'Margen Promedio %', 'Margen Mín %', 'Margen Máx %', 
                     'Ganancia Promedio', 'Valor Costo', 'Valor Venta', 'Ganancia Potencial'];
    
    const rows = data.categorias.map(cat => [
      cat.categoria_nombre,
      cat.total_productos,
      cat.margen_promedio.toFixed(2),
      cat.margen_minimo.toFixed(2),
      cat.margen_maximo.toFixed(2),
      cat.ganancia_promedio.toFixed(2),
      cat.valor_inventario_costo.toFixed(2),
      cat.valor_inventario_venta.toFixed(2),
      cat.ganancia_potencial.toFixed(2)
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `reporte_rentabilidad_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    toast.success('Reporte exportado correctamente');
  };

  const exportarHistoricoCSV = () => {
    if (!dataHistorico || !dataHistorico.datos_mensuales.length) return;
    
    const headers = ['Mes', 'Total Ventas', 'Productos Vendidos', 'Ingresos Brutos', 
                     'Costo Total', 'Ganancia Neta', 'Margen Promedio %'];
    
    const rows = dataHistorico.datos_mensuales.map(m => [
      m.mes_nombre,
      m.total_ventas,
      m.productos_vendidos,
      m.ingresos_brutos.toFixed(2),
      m.costo_total.toFixed(2),
      m.ganancia_neta.toFixed(2),
      m.margen_promedio.toFixed(2)
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `rentabilidad_historico_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    toast.success('Histórico exportado correctamente');
  };

  // Custom tooltip para las gráficas
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.name.includes('Margen') ? `${entry.value.toFixed(1)}%` : formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading && loadingHistorico) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="reporte-rentabilidad">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <PieChart className="w-7 h-7 text-blue-600" />
              Reporte de Rentabilidad
            </h1>
            <p className="text-gray-500 mt-1">Análisis de márgenes de ganancia por categoría y evolución histórica</p>
          </div>
          <div className="flex gap-3 items-center">
            <Button variant="outline" onClick={() => { loadReporte(); loadHistorico(); }} disabled={loading || loadingHistorico}>
              <RefreshCw className={`w-4 h-4 mr-2 ${(loading || loadingHistorico) ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>
        </div>

        {/* Resumen General */}
        {data && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-600 font-medium">Margen Promedio General</p>
                    <p className={`text-3xl font-bold mt-1 ${getMargenColor(data.resumen.margen_promedio_general)}`}>
                      {data.resumen.margen_promedio_general.toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-3 bg-blue-200 rounded-full">
                    <TrendingUp className="w-6 h-6 text-blue-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-emerald-600 font-medium">Ganancia Potencial Total</p>
                    <p className="text-2xl font-bold mt-1 text-emerald-700">
                      {formatCurrency(data.resumen.ganancia_potencial_total)}
                    </p>
                  </div>
                  <div className="p-3 bg-emerald-200 rounded-full">
                    <DollarSign className="w-6 h-6 text-emerald-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-purple-600 font-medium">Valor Inventario (Venta)</p>
                    <p className="text-2xl font-bold mt-1 text-purple-700">
                      {formatCurrency(data.resumen.valor_total_venta)}
                    </p>
                  </div>
                  <div className="p-3 bg-purple-200 rounded-full">
                    <BarChart3 className="w-6 h-6 text-purple-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-slate-50 to-slate-100 border-slate-200">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-600 font-medium">Productos Analizados</p>
                    <p className="text-3xl font-bold mt-1 text-slate-700">
                      {data.resumen.total_productos}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">en {data.resumen.total_categorias} categorías</p>
                  </div>
                  <div className="p-3 bg-slate-200 rounded-full">
                    <Package className="w-6 h-6 text-slate-700" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tabs de Contenido */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="categorias" className="flex items-center gap-2">
              <PieChart className="w-4 h-4" />
              Por Categoría
            </TabsTrigger>
            <TabsTrigger value="historico" className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Evolución Mensual
            </TabsTrigger>
          </TabsList>

          {/* Tab: Por Categoría */}
          <TabsContent value="categorias" className="space-y-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <Switch 
                  id="solo-stock" 
                  checked={soloConStock} 
                  onCheckedChange={setSoloConStock}
                />
                <Label htmlFor="solo-stock" className="text-sm text-gray-600">Solo productos con stock</Label>
              </div>
              <Button onClick={exportarCSV} disabled={!data} variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Exportar CSV
              </Button>
            </div>

            {/* Tabla de Categorías */}
            {data && data.categorias.length > 0 ? (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Rentabilidad por Categoría</CardTitle>
                  <CardDescription>
                    Ordenado por margen promedio descendente
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-y">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Productos</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Margen Promedio</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Rango</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ganancia/Unidad</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor Costo</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor Venta</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ganancia Potencial</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.categorias.map((cat, idx) => (
                          <tr key={cat.categoria_id || idx} className="hover:bg-gray-50" data-testid={`cat-row-${idx}`}>
                            <td className="px-4 py-4">
                              <div className="flex items-center gap-2">
                                <div className={`w-3 h-3 rounded-full ${getProgressColor(cat.margen_promedio)}`} />
                                <span className="font-medium text-gray-900">{cat.categoria_nombre}</span>
                              </div>
                            </td>
                            <td className="px-4 py-4 text-center">
                              <span className="text-gray-700">{cat.total_productos}</span>
                              {cat.productos_con_precio < cat.total_productos && (
                                <span className="text-xs text-gray-400 ml-1">
                                  ({cat.productos_con_precio} con precio)
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-4">
                              <div className="flex flex-col items-center gap-1">
                                <span className={`text-xl font-bold ${getMargenColor(cat.margen_promedio)}`}>
                                  {cat.margen_promedio.toFixed(1)}%
                                </span>
                                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div 
                                    className={`h-full ${getProgressColor(cat.margen_promedio)} transition-all`}
                                    style={{ width: `${Math.min(cat.margen_promedio, 100)}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-4 text-center">
                              <div className="text-xs text-gray-500">
                                <span className="text-red-500">{cat.margen_minimo.toFixed(1)}%</span>
                                <span className="mx-1">-</span>
                                <span className="text-green-500">{cat.margen_maximo.toFixed(1)}%</span>
                              </div>
                            </td>
                            <td className="px-4 py-4 text-right">
                              <span className="font-medium text-gray-700">
                                {formatCurrency(cat.ganancia_promedio)}
                              </span>
                            </td>
                            <td className="px-4 py-4 text-right text-sm text-gray-600">
                              {formatCurrency(cat.valor_inventario_costo)}
                            </td>
                            <td className="px-4 py-4 text-right text-sm font-medium text-gray-700">
                              {formatCurrency(cat.valor_inventario_venta)}
                            </td>
                            <td className="px-4 py-4 text-right">
                              <span className={`font-bold ${cat.ganancia_potencial >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(cat.ganancia_potencial)}
                              </span>
                            </td>
                            <td className="px-4 py-4 text-center">
                              {getMargenBadge(cat.margen_promedio)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      {/* Footer con totales */}
                      <tfoot className="bg-gray-100 border-t-2 border-gray-300">
                        <tr className="font-semibold">
                          <td className="px-4 py-3 text-gray-700">TOTAL</td>
                          <td className="px-4 py-3 text-center text-gray-700">{data.resumen.total_productos}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-lg font-bold ${getMargenColor(data.resumen.margen_promedio_general)}`}>
                              {data.resumen.margen_promedio_general.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-3"></td>
                          <td className="px-4 py-3"></td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {formatCurrency(data.resumen.valor_total_costo)}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">
                            {formatCurrency(data.resumen.valor_total_venta)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-lg font-bold text-green-600">
                              {formatCurrency(data.resumen.ganancia_potencial_total)}
                            </span>
                          </td>
                          <td className="px-4 py-3"></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-gray-500">
                  <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No hay datos de rentabilidad disponibles</p>
                  <p className="text-sm mt-1">Asegúrese de tener productos con precios de compra y venta configurados</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Tab: Evolución Histórica */}
          <TabsContent value="historico" className="space-y-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <Label className="text-sm text-gray-600">Período:</Label>
                <Select value={mesesHistorico.toString()} onValueChange={(v) => setMesesHistorico(parseInt(v))}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="6">Últimos 6 meses</SelectItem>
                    <SelectItem value="12">Últimos 12 meses</SelectItem>
                    <SelectItem value="18">Últimos 18 meses</SelectItem>
                    <SelectItem value="24">Últimos 24 meses</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={exportarHistoricoCSV} disabled={!dataHistorico?.datos_mensuales?.length} variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Exportar CSV
              </Button>
            </div>

            {/* Indicadores de Tendencia */}
            {dataHistorico && dataHistorico.datos_mensuales.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Tendencia</p>
                        <p className={`text-lg font-bold capitalize ${getTendenciaColor(dataHistorico.tendencia)}`}>
                          {dataHistorico.tendencia}
                        </p>
                      </div>
                      {getTendenciaIcon(dataHistorico.tendencia)}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Variación Último Mes</p>
                        <p className={`text-lg font-bold ${dataHistorico.variacion_ultimo_mes >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {dataHistorico.variacion_ultimo_mes >= 0 ? '+' : ''}{dataHistorico.variacion_ultimo_mes.toFixed(1)}%
                        </p>
                      </div>
                      {dataHistorico.variacion_ultimo_mes >= 0 ? 
                        <TrendingUp className="w-5 h-5 text-green-600" /> : 
                        <TrendingDown className="w-5 h-5 text-red-600" />
                      }
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Meses Analizados</p>
                        <p className="text-lg font-bold text-gray-700">
                          {dataHistorico.datos_mensuales.length} meses
                        </p>
                      </div>
                      <Calendar className="w-5 h-5 text-gray-500" />
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Gráfica Principal: Margen y Ganancia */}
            {activeTab === 'historico' && dataHistorico && dataHistorico.datos_mensuales.length > 0 ? (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-blue-600" />
                      Evolución del Margen de Rentabilidad
                    </CardTitle>
                    <CardDescription>
                      Margen promedio mensual basado en ventas realizadas
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={dataHistorico.datos_mensuales}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="mes_nombre" 
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => value.split(' ')[0].substring(0, 3)}
                          />
                          <YAxis 
                            yAxisId="left"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `${value}%`}
                            domain={[0, 'auto']}
                          />
                          <YAxis 
                            yAxisId="right"
                            orientation="right"
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `Q${(value/1000).toFixed(0)}k`}
                          />
                          <Tooltip content={<CustomTooltip />} />
                          <Legend />
                          <Area
                            yAxisId="right"
                            type="monotone"
                            dataKey="ganancia_neta"
                            name="Ganancia Neta"
                            fill="#10b981"
                            fillOpacity={0.2}
                            stroke="#10b981"
                            strokeWidth={2}
                          />
                          <Line
                            yAxisId="left"
                            type="monotone"
                            dataKey="margen_promedio"
                            name="Margen %"
                            stroke="#3b82f6"
                            strokeWidth={3}
                            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 5 }}
                            activeDot={{ r: 7 }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Gráfica de Ingresos vs Costos */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-purple-600" />
                      Ingresos vs Costos Mensuales
                    </CardTitle>
                    <CardDescription>
                      Comparativa de ingresos brutos contra costos de productos vendidos
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={dataHistorico.datos_mensuales}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis 
                            dataKey="mes_nombre" 
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => value.split(' ')[0].substring(0, 3)}
                          />
                          <YAxis 
                            tick={{ fontSize: 12 }}
                            tickFormatter={(value) => `Q${(value/1000).toFixed(0)}k`}
                          />
                          <Tooltip content={<CustomTooltip />} />
                          <Legend />
                          <Bar dataKey="ingresos_brutos" name="Ingresos" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="costo_total" name="Costos" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Tabla de datos mensuales */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Detalle Mensual</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-y">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mes</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ventas</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Productos</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ingresos</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costos</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ganancia</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Margen</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {dataHistorico.datos_mensuales.slice().reverse().map((mes, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-4 py-3 font-medium text-gray-900">{mes.mes_nombre}</td>
                              <td className="px-4 py-3 text-center text-gray-700">{mes.total_ventas}</td>
                              <td className="px-4 py-3 text-center text-gray-700">{mes.productos_vendidos}</td>
                              <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(mes.ingresos_brutos)}</td>
                              <td className="px-4 py-3 text-right text-gray-600">{formatCurrency(mes.costo_total)}</td>
                              <td className="px-4 py-3 text-right">
                                <span className={`font-medium ${mes.ganancia_neta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {formatCurrency(mes.ganancia_neta)}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className={`font-bold ${getMargenColor(mes.margen_promedio)}`}>
                                  {mes.margen_promedio.toFixed(1)}%
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-gray-500">
                  <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="font-medium">No hay datos históricos disponibles</p>
                  <p className="text-sm mt-1">Los datos de evolución se generan a partir de las ventas registradas en el sistema</p>
                  <p className="text-xs mt-3 text-gray-400">
                    Realice ventas en el Punto de Venta para comenzar a ver la evolución de rentabilidad
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>

        {/* Leyenda */}
        <Card className="bg-gray-50">
          <CardContent className="py-4">
            <div className="flex flex-wrap items-center justify-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-gray-600">Excelente (≥40%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-gray-600">Bueno (30-39%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-gray-600">Regular (20-29%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-orange-500" />
                <span className="text-gray-600">Bajo (10-19%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-gray-600">Crítico (&lt;10%)</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default ReporteRentabilidad;
