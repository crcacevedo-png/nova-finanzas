// /app/frontend/src/pages/inventario/Sociedades.js
// Módulo de gestión de consumos de productos para sociedades médicas

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import {
  Users, Package, Calendar, TrendingDown, Search, Download, Filter,
  ChevronLeft, ChevronRight, DollarSign, BarChart3, RefreshCw, FileSpreadsheet, FileText
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Sociedades = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('consumos');
  
  // Consumos
  const [consumos, setConsumos] = useState([]);
  const [totalConsumos, setTotalConsumos] = useState(0);
  const [resumenConsumos, setResumenConsumos] = useState({});
  const [page, setPage] = useState(1);
  const [limit] = useState(30);
  
  // Filtros
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [productoFilter, setProductoFilter] = useState('all');
  
  // Productos sociedad
  const [productosSociedad, setProductosSociedad] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  
  // Resumen mensual
  const [resumenMensual, setResumenMensual] = useState(null);
  const [mesSeleccionado, setMesSeleccionado] = useState(new Date().getMonth() + 1);
  const [anioSeleccionado, setAnioSeleccionado] = useState(new Date().getFullYear());

  const fetchConsumos = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (productoFilter !== 'all') params.append('producto_id', productoFilter);
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/consumos?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Error al cargar consumos');
      
      const data = await response.json();
      setConsumos(data.data || []);
      setTotalConsumos(data.total || 0);
      setResumenConsumos(data.resumen || {});
    } catch (error) {
      console.error('Error fetching consumos:', error);
      toast.error('Error al cargar consumos de sociedades');
    } finally {
      setLoading(false);
    }
  }, [page, limit, fechaInicio, fechaFin, productoFilter]);

  const fetchProductosSociedad = useCallback(async () => {
    try {
      setLoadingProductos(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/inventario/sociedades/productos`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Error al cargar productos');
      
      const data = await response.json();
      setProductosSociedad(data || []);
    } catch (error) {
      console.error('Error fetching productos sociedad:', error);
    } finally {
      setLoadingProductos(false);
    }
  }, []);

  const fetchResumenMensual = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${API_URL}/api/inventario/sociedades/resumen?mes=${mesSeleccionado}&anio=${anioSeleccionado}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Error al cargar resumen');
      
      const data = await response.json();
      setResumenMensual(data);
    } catch (error) {
      console.error('Error fetching resumen:', error);
    }
  }, [mesSeleccionado, anioSeleccionado]);

  useEffect(() => {
    fetchConsumos();
    fetchProductosSociedad();
  }, [fetchConsumos, fetchProductosSociedad]);

  useEffect(() => {
    if (activeTab === 'resumen') {
      fetchResumenMensual();
    }
  }, [activeTab, fetchResumenMensual]);

  const totalPages = Math.ceil(totalConsumos / limit);

  const exportarExcel = async () => {
    try {
      toast.info('Generando Excel...');
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (!fechaInicio && !fechaFin) {
        params.append('mes', mesSeleccionado.toString());
        params.append('anio', anioSeleccionado.toString());
      }
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/exportar/excel?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al exportar');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sociedades_consumos.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('Excel descargado correctamente');
    } catch (error) {
      console.error('Error exporting Excel:', error);
      toast.error(error.message || 'Error al exportar Excel');
    }
  };

  const exportarPDF = async () => {
    try {
      toast.info('Generando PDF...');
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (!fechaInicio && !fechaFin) {
        params.append('mes', mesSeleccionado.toString());
        params.append('anio', anioSeleccionado.toString());
      }
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/exportar/pdf?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al exportar');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sociedades_consumos.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('PDF descargado correctamente');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error(error.message || 'Error al exportar PDF');
    }
  };

  const tipoLabels = {
    salida: 'Salida',
    venta: 'Venta',
    consumo: 'Consumo',
    ajuste_negativo: 'Ajuste -',
    baja: 'Baja'
  };

  const meses = [
    { value: 1, label: 'Enero' },
    { value: 2, label: 'Febrero' },
    { value: 3, label: 'Marzo' },
    { value: 4, label: 'Abril' },
    { value: 5, label: 'Mayo' },
    { value: 6, label: 'Junio' },
    { value: 7, label: 'Julio' },
    { value: 8, label: 'Agosto' },
    { value: 9, label: 'Septiembre' },
    { value: 10, label: 'Octubre' },
    { value: 11, label: 'Noviembre' },
    { value: 12, label: 'Diciembre' }
  ];

  return (
    <Layout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 font-['Outfit'] flex items-center gap-2">
              <Users className="w-7 h-7 text-purple-600" />
              Sociedades
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Control de consumos de productos para sociedades médicas
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={exportarExcel} variant="outline" data-testid="export-excel-btn">
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Excel
            </Button>
            <Button onClick={exportarPDF} variant="outline" data-testid="export-pdf-btn">
              <FileText className="w-4 h-4 mr-2" />
              PDF
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Package className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Productos Sociedad</p>
                  <p className="text-xl font-bold">{productosSociedad.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Consumos</p>
                  <p className="text-xl font-bold">{resumenConsumos.total_cantidad || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <DollarSign className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Costo Total</p>
                  <p className="text-xl font-bold">{formatCurrency(resumenConsumos.total_costo || 0)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Productos Distintos</p>
                  <p className="text-xl font-bold">{resumenConsumos.productos_distintos || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="consumos" className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              Consumos
            </TabsTrigger>
            <TabsTrigger value="productos" className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              Productos
            </TabsTrigger>
            <TabsTrigger value="resumen" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Resumen
            </TabsTrigger>
          </TabsList>

          {/* Tab: Consumos */}
          <TabsContent value="consumos" className="space-y-4">
            {/* Filtros */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex flex-wrap gap-4 items-end">
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Fecha inicio</label>
                    <Input
                      type="date"
                      value={fechaInicio}
                      onChange={(e) => setFechaInicio(e.target.value)}
                      className="w-40"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Fecha fin</label>
                    <Input
                      type="date"
                      value={fechaFin}
                      onChange={(e) => setFechaFin(e.target.value)}
                      className="w-40"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Producto</label>
                    <Select value={productoFilter} onValueChange={setProductoFilter}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Todos los productos" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos los productos</SelectItem>
                        {productosSociedad.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={fetchConsumos} variant="outline">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Filtrar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Tabla de consumos */}
            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
                  </div>
                ) : consumos.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No se encontraron consumos de sociedades</p>
                    <p className="text-sm mt-1">Marca productos como &quot;Sociedad&quot; en el catálogo para verlos aquí</p>
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bodega</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Unit.</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Total</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Motivo</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {consumos.map((consumo) => (
                            <tr key={consumo.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm">
                                {new Date(consumo.fecha).toLocaleDateString('es-GT')}
                              </td>
                              <td className="px-4 py-3">
                                <div>
                                  <p className="text-sm font-medium">{consumo.producto_nombre}</p>
                                  <p className="text-xs text-gray-500">{consumo.producto_codigo}</p>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-sm">{consumo.bodega_nombre}</td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="text-xs">
                                  {tipoLabels[consumo.tipo] || consumo.tipo}
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-sm text-right font-medium text-red-600">
                                -{consumo.cantidad}
                              </td>
                              <td className="px-4 py-3 text-sm text-right">
                                {formatCurrency(consumo.costo_unitario)}
                              </td>
                              <td className="px-4 py-3 text-sm text-right font-medium">
                                {formatCurrency(consumo.costo_total)}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">
                                {consumo.motivo || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Paginación */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between px-4 py-3 border-t">
                        <p className="text-sm text-gray-500">
                          Mostrando {((page - 1) * limit) + 1} - {Math.min(page * limit, totalConsumos)} de {totalConsumos}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </Button>
                          <span className="px-3 py-1 text-sm">
                            {page} / {totalPages}
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Productos */}
          <TabsContent value="productos" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Productos Marcados como Sociedad</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {loadingProductos ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
                  </div>
                ) : productosSociedad.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No hay productos marcados como sociedad</p>
                    <p className="text-sm mt-1">Ve al Catálogo de Productos y activa el switch &quot;Sociedad&quot;</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Existencia</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Compra</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Venta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {productosSociedad.map((producto) => (
                          <tr key={producto.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-mono">{producto.codigo}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                                  👥
                                </Badge>
                                <span className="text-sm font-medium">{producto.nombre}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm">{producto.categoria_nombre || '-'}</td>
                            <td className="px-4 py-3 text-sm text-right">
                              {producto.controla_inventario ? (
                                <Badge variant={producto.existencia_total > 10 ? "outline" : "destructive"}>
                                  {producto.existencia_total}
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="bg-blue-50 text-blue-600">∞</Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-right">{formatCurrency(producto.precio_compra)}</td>
                            <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(producto.precio_venta)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Resumen */}
          <TabsContent value="resumen" className="space-y-4">
            {/* Selector de mes/año */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-4">
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Mes</label>
                    <Select value={mesSeleccionado.toString()} onValueChange={(v) => setMesSeleccionado(parseInt(v))}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {meses.map(m => (
                          <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Año</label>
                    <Select value={anioSeleccionado.toString()} onValueChange={(v) => setAnioSeleccionado(parseInt(v))}>
                      <SelectTrigger className="w-[100px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[2024, 2025, 2026].map(a => (
                          <SelectItem key={a} value={a.toString()}>{a}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={fetchResumenMensual} variant="outline" className="mt-5">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Actualizar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {resumenMensual && (
              <>
                {/* Totales del mes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-gradient-to-br from-purple-50 to-white">
                    <CardContent className="pt-6">
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Total Consumos del Mes</p>
                        <p className="text-3xl font-bold text-purple-700">{resumenMensual.total_consumos}</p>
                        <p className="text-sm text-gray-400 mt-1">unidades</p>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className="bg-gradient-to-br from-amber-50 to-white">
                    <CardContent className="pt-6">
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Costo Total del Mes</p>
                        <p className="text-3xl font-bold text-amber-700">{formatCurrency(resumenMensual.total_costo)}</p>
                        <p className="text-sm text-gray-400 mt-1">en productos sociedad</p>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Desglose por producto */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Consumo por Producto</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {resumenMensual.por_producto?.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead className="bg-gray-50 border-b">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Total</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">% del Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {resumenMensual.por_producto.map((item, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3">
                                  <div>
                                    <p className="text-sm font-medium">{item.producto_nombre}</p>
                                    <p className="text-xs text-gray-500">{item.producto_codigo}</p>
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-sm text-right font-medium">
                                  {item.cantidad}
                                </td>
                                <td className="px-4 py-3 text-sm text-right">
                                  {formatCurrency(item.costo_total)}
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <Badge variant="outline">
                                    {resumenMensual.total_costo > 0 
                                      ? ((item.costo_total / resumenMensual.total_costo) * 100).toFixed(1) 
                                      : 0}%
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        No hay consumos registrados para este período
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default Sociedades;
