// /app/frontend/src/pages/inventario/PanelInventario.js
// Panel/Dashboard del módulo de Inventario

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Package, AlertTriangle, Clock, TrendingUp, ArrowRight,
  DollarSign, Box, AlertCircle, Activity
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const PanelInventario = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [panelData, setPanelData] = useState(null);
  const [alertas, setAlertas] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [panelRes, alertasRes] = await Promise.all([
        inventarioApi.getPanel(),
        inventarioApi.getAlertas()
      ]);
      setPanelData(panelRes.data);
      setAlertas(alertasRes.data);
    } catch (error) {
      console.error('Error cargando panel:', error);
    } finally {
      setLoading(false);
    }
  };

  const kpis = panelData ? [
    {
      title: 'Valor Total Inventario',
      value: formatCurrency(panelData.valor_total_inventario),
      icon: DollarSign,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10'
    },
    {
      title: 'Productos Activos',
      value: panelData.total_productos_activos,
      icon: Package,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
      onClick: () => navigate('/inventario/productos')
    },
    {
      title: 'Bajo Mínimo',
      value: panelData.productos_bajo_minimo,
      icon: AlertTriangle,
      color: panelData.productos_bajo_minimo > 0 ? 'text-red-500' : 'text-gray-500',
      bgColor: panelData.productos_bajo_minimo > 0 ? 'bg-red-500/10' : 'bg-gray-500/10',
      badge: panelData.productos_bajo_minimo > 0 ? 'danger' : null,
      onClick: () => navigate('/inventario/productos?bajo_minimo=true')
    },
    {
      title: 'Por Vencer (90 días)',
      value: panelData.lotes_por_vencer_90,
      icon: Clock,
      color: panelData.lotes_por_vencer_90 > 0 ? 'text-amber-500' : 'text-gray-500',
      bgColor: panelData.lotes_por_vencer_90 > 0 ? 'bg-amber-500/10' : 'bg-gray-500/10',
      badge: panelData.lotes_por_vencer_90 > 0 ? 'warning' : null,
      onClick: () => navigate('/inventario/lotes')
    },
    {
      title: 'Lotes Vencidos',
      value: panelData.lotes_vencidos,
      icon: AlertCircle,
      color: panelData.lotes_vencidos > 0 ? 'text-red-600' : 'text-gray-500',
      bgColor: panelData.lotes_vencidos > 0 ? 'bg-red-600/10' : 'bg-gray-500/10',
      badge: panelData.lotes_vencidos > 0 ? 'danger' : null,
      onClick: () => navigate('/inventario/lotes?estado=vencido')
    },
    {
      title: 'Movimientos Hoy',
      value: panelData.movimientos_hoy,
      icon: Activity,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
      onClick: () => navigate('/inventario/movimientos')
    }
  ] : [];

  const getBadgeVariant = (type) => {
    switch (type) {
      case 'danger': return 'destructive';
      case 'warning': return 'warning';
      default: return 'secondary';
    }
  };

  const getTipoMovimientoLabel = (tipo) => {
    const labels = {
      'entrada': 'Entrada',
      'salida': 'Salida',
      'venta': 'Venta',
      'ajuste_positivo': 'Ajuste +',
      'ajuste_negativo': 'Ajuste -',
      'transferencia_entrada': 'Transfer. In',
      'transferencia_salida': 'Transfer. Out'
    };
    return labels[tipo] || tipo;
  };

  const getTipoColor = (tipo) => {
    if (['entrada', 'devolucion', 'ajuste_positivo', 'transferencia_entrada'].includes(tipo)) {
      return 'bg-green-100 text-green-800';
    }
    if (['salida', 'venta', 'ajuste_negativo', 'transferencia_salida', 'consumo', 'baja'].includes(tipo)) {
      return 'bg-red-100 text-red-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="panel-inventario">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Panel de Inventario</h1>
            <p className="text-gray-500">Resumen y métricas del inventario</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/inventario/productos')}>
              <Package className="w-4 h-4 mr-2" />
              Productos
            </Button>
            <Button onClick={() => navigate('/inventario/ordenes')}>
              <Box className="w-4 h-4 mr-2" />
              Nueva Orden
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {kpis.map((kpi, index) => (
            <Card 
              key={index}
              className={`cursor-pointer hover:shadow-md transition-shadow ${kpi.onClick ? 'hover:border-teal-300' : ''}`}
              onClick={kpi.onClick}
              data-testid={`kpi-${index}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className={`p-2 rounded-lg ${kpi.bgColor}`}>
                    <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
                  </div>
                  {kpi.badge && (
                    <Badge variant={getBadgeVariant(kpi.badge)} className="h-5">
                      !
                    </Badge>
                  )}
                </div>
                <p className="text-2xl font-bold mt-3">{kpi.value}</p>
                <p className="text-xs text-gray-500 mt-1">{kpi.title}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Alertas activas */}
        {alertas && alertas.total > 0 && (
          <Card className="border-amber-200 bg-amber-50/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Alertas Activas ({alertas.total})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {alertas.alertas.slice(0, 5).map((alerta, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border">
                    <div className="flex items-center gap-2">
                      <Badge variant={alerta.severidad === 'alta' ? 'destructive' : 'warning'}>
                        {alerta.tipo}
                      </Badge>
                      <span className="text-sm">{alerta.producto_nombre}</span>
                    </div>
                    <span className="text-xs text-gray-500">{alerta.mensaje}</span>
                  </div>
                ))}
              </div>
              {alertas.total > 5 && (
                <Button 
                  variant="link" 
                  className="mt-2 p-0 h-auto"
                  onClick={() => navigate('/inventario/lotes')}
                >
                  Ver todas las alertas <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfica de valor por categoría */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Valor por Categoría</CardTitle>
            </CardHeader>
            <CardContent>
              {panelData?.valor_por_categoria?.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={panelData.valor_por_categoria} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={(v) => `Q${(v/1000).toFixed(0)}k`} />
                    <YAxis dataKey="categoria_nombre" type="category" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip 
                      formatter={(value) => [formatCurrency(value), 'Valor']}
                      labelFormatter={(label) => label}
                    />
                    <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
                      {panelData.valor_por_categoria.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color || '#0F6E56'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[250px] flex items-center justify-center text-gray-400">
                  Sin datos de categorías
                </div>
              )}
            </CardContent>
          </Card>

          {/* Productos con mayor rotación */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-teal-500" />
                Mayor Rotación del Mes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {panelData?.productos_mayor_rotacion?.length > 0 ? (
                <div className="space-y-3">
                  {panelData.productos_mayor_rotacion.slice(0, 5).map((prod, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-gray-400 w-6">{idx + 1}</span>
                        <div>
                          <p className="text-sm font-medium">{prod.producto_nombre}</p>
                          <p className="text-xs text-gray-500">{prod.producto_codigo}</p>
                        </div>
                      </div>
                      <Badge variant="secondary">{prod.total_salidas} und</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-[200px] flex items-center justify-center text-gray-400">
                  Sin movimientos este mes
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Últimos movimientos */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Últimos Movimientos</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/inventario/movimientos')}>
              Ver todos <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            {panelData?.ultimos_movimientos?.length > 0 ? (
              <div className="space-y-2">
                {panelData.ultimos_movimientos.map((mov, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center gap-3">
                      <Badge className={getTipoColor(mov.tipo)}>
                        {getTipoMovimientoLabel(mov.tipo)}
                      </Badge>
                      <span className="text-sm font-medium">{mov.producto_nombre}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm">{mov.cantidad} und</span>
                      <span className="text-xs text-gray-500">
                        {new Date(mov.fecha).toLocaleString('es-GT', { 
                          day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-400 py-8">
                No hay movimientos recientes
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default PanelInventario;
