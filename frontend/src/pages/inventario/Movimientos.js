// /app/frontend/src/pages/inventario/Movimientos.js
// Kardex / Movimientos de Inventario

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  Search, Download, ChevronLeft, ChevronRight, ArrowUpCircle, ArrowDownCircle
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';

const Movimientos = () => {
  const [loading, setLoading] = useState(true);
  const [movimientos, setMovimientos] = useState([]);
  const [productos, setProductos] = useState([]);
  const [bodegas, setBodegas] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(30);
  
  // Filtros
  const [productoFilter, setProductoFilter] = useState('all');
  const [bodegaFilter, setBodegaFilter] = useState('all');
  const [tipoFilter, setTipoFilter] = useState('all');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      
      const [movRes, prodRes, bodRes] = await Promise.all([
        inventarioApi.getMovimientos({
          page,
          limit,
          producto_id: productoFilter !== 'all' ? productoFilter : undefined,
          bodega_id: bodegaFilter !== 'all' ? bodegaFilter : undefined,
          tipo: tipoFilter !== 'all' ? tipoFilter : undefined,
          fecha_desde: fechaDesde || undefined,
          fecha_hasta: fechaHasta || undefined
        }),
        inventarioApi.getProductos({ limit: 500 }),
        inventarioApi.getBodegas()
      ]);
      
      setMovimientos(movRes.data.data || []);
      setTotal(movRes.data.total || 0);
      setProductos(prodRes.data.data || []);
      setBodegas(bodRes.data.data || []);
    } catch (error) {
      console.error('Error cargando movimientos:', error);
    } finally {
      setLoading(false);
    }
  }, [page, limit, productoFilter, bodegaFilter, tipoFilter, fechaDesde, fechaHasta]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getTipoLabel = (tipo) => {
    const labels = {
      'entrada': 'Entrada',
      'salida': 'Salida',
      'venta': 'Venta',
      'devolucion': 'Devolución',
      'ajuste_positivo': 'Ajuste +',
      'ajuste_negativo': 'Ajuste -',
      'transferencia_entrada': 'Transf. Entrada',
      'transferencia_salida': 'Transf. Salida',
      'consumo': 'Consumo',
      'baja': 'Baja',
      'anulacion': 'Anulación'
    };
    return labels[tipo] || tipo;
  };

  const getTipoBadge = (tipo) => {
    const esEntrada = ['entrada', 'devolucion', 'ajuste_positivo', 'transferencia_entrada'].includes(tipo);
    const esSalida = ['salida', 'venta', 'ajuste_negativo', 'transferencia_salida', 'consumo', 'baja', 'anulacion'].includes(tipo);
    
    if (esEntrada) {
      return (
        <Badge className="bg-green-100 text-green-800 flex items-center gap-1">
          <ArrowUpCircle className="w-3 h-3" />
          {getTipoLabel(tipo)}
        </Badge>
      );
    } else if (esSalida) {
      return (
        <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
          <ArrowDownCircle className="w-3 h-3" />
          {getTipoLabel(tipo)}
        </Badge>
      );
    }
    return <Badge>{getTipoLabel(tipo)}</Badge>;
  };

  const tiposMovimiento = [
    { value: 'entrada', label: 'Entrada' },
    { value: 'salida', label: 'Salida' },
    { value: 'venta', label: 'Venta' },
    { value: 'ajuste_positivo', label: 'Ajuste +' },
    { value: 'ajuste_negativo', label: 'Ajuste -' },
    { value: 'transferencia_entrada', label: 'Transf. Entrada' },
    { value: 'transferencia_salida', label: 'Transf. Salida' },
    { value: 'baja', label: 'Baja' }
  ];

  const totalPages = Math.ceil(total / limit);

  return (
    <Layout>
      <div className="space-y-6" data-testid="movimientos-inventario">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Kardex / Movimientos</h1>
            <p className="text-gray-500">Historial de movimientos de inventario</p>
          </div>
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
        </div>

        {/* Filtros */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-end">
              <div className="w-[200px]">
                <label className="text-xs text-gray-500 mb-1 block">Producto</label>
                <Select value={productoFilter} onValueChange={(v) => { setProductoFilter(v); setPage(1); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los productos</SelectItem>
                    {productos.slice(0, 50).map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-[180px]">
                <label className="text-xs text-gray-500 mb-1 block">Bodega</label>
                <Select value={bodegaFilter} onValueChange={(v) => { setBodegaFilter(v); setPage(1); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Todas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las bodegas</SelectItem>
                    {bodegas.map(b => (
                      <SelectItem key={b.id} value={b.id}>{b.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-[180px]">
                <label className="text-xs text-gray-500 mb-1 block">Tipo</label>
                <Select value={tipoFilter} onValueChange={(v) => { setTipoFilter(v); setPage(1); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los tipos</SelectItem>
                    {tiposMovimiento.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="w-[150px]">
                <label className="text-xs text-gray-500 mb-1 block">Desde</label>
                <Input
                  type="date"
                  value={fechaDesde}
                  onChange={(e) => { setFechaDesde(e.target.value); setPage(1); }}
                />
              </div>
              
              <div className="w-[150px]">
                <label className="text-xs text-gray-500 mb-1 block">Hasta</label>
                <Input
                  type="date"
                  value={fechaHasta}
                  onChange={(e) => { setFechaHasta(e.target.value); setPage(1); }}
                />
              </div>
              
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  setProductoFilter('all');
                  setBodegaFilter('all');
                  setTipoFilter('all');
                  setFechaDesde('');
                  setFechaHasta('');
                  setPage(1);
                }}
              >
                Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla de movimientos */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : movimientos.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <p>No se encontraron movimientos</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bodega</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Anterior</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Nueva</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Unit.</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Total</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Referencia</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {movimientos.map((mov) => (
                      <tr key={mov.id} className="hover:bg-gray-50" data-testid={`mov-row-${mov.id}`}>
                        <td className="px-4 py-3 text-sm">
                          {new Date(mov.fecha).toLocaleString('es-GT', {
                            day: '2-digit',
                            month: '2-digit',
                            year: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </td>
                        <td className="px-4 py-3">{getTipoBadge(mov.tipo)}</td>
                        <td className="px-4 py-3 text-sm font-medium">{mov.producto_nombre}</td>
                        <td className="px-4 py-3 text-sm">{mov.bodega_nombre}</td>
                        <td className="px-4 py-3 text-right text-sm font-medium">{mov.cantidad}</td>
                        <td className="px-4 py-3 text-right text-sm text-gray-500">{mov.existencia_anterior}</td>
                        <td className="px-4 py-3 text-right text-sm font-medium">{mov.existencia_nueva}</td>
                        <td className="px-4 py-3 text-right text-sm">{formatCurrency(mov.costo_unitario)}</td>
                        <td className="px-4 py-3 text-right text-sm">{formatCurrency(mov.costo_total)}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {mov.referencia_tipo && (
                            <span className="text-xs">
                              {mov.referencia_tipo}
                              {mov.motivo && <span className="block text-gray-400">{mov.motivo.substring(0, 30)}...</span>}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Mostrando {((page - 1) * limit) + 1} - {Math.min(page * limit, total)} de {total}
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
                Página {page} de {totalPages}
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
      </div>
    </Layout>
  );
};

export default Movimientos;
