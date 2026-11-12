import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { ventasApi, formatCurrency, formatTime, formatDate, getGuatemalaDate } from '../services/api';
import { Receipt, ChevronRight, RefreshCw, ShoppingBag } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast, Toaster } from 'sonner';

const VentasDelDia = () => {
  const [ventas, setVentas] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);

  const [ventaDetalle, setVentaDetalle] = useState(null);
  const [detalleOpen, setDetalleOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resVentas, resResumen] = await Promise.all([
        ventasApi.getVentasHoy(),
        ventasApi.getResumenDia(),
      ]);
      setVentas(resVentas.data?.data || []);
      setResumen(resResumen.data);
    } catch (error) {
      toast.error('No se pudieron cargar las ventas del día');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const verDetalle = async (ventaId) => {
    try {
      const res = await ventasApi.getById(ventaId);
      setVentaDetalle(res.data);
      setDetalleOpen(true);
    } catch (error) {
      toast.error('No se pudo cargar el detalle de la venta');
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="ventas-del-dia-page">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Receipt className="w-6 h-6 text-[#0F6E56]" />
              Ventas del Día
            </h1>
            <p className="text-slate-500 text-sm">{getGuatemalaDate()}</p>
          </div>
          <Button variant="outline" onClick={fetchData} data-testid="btn-refrescar-ventas">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualizar
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card className="border-emerald-100">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Ventas registradas hoy</p>
                <p className="text-2xl font-bold text-slate-800" data-testid="resumen-total-ventas">{resumen?.total_ventas ?? 0}</p>
              </div>
              <ShoppingBag className="w-9 h-9 text-emerald-500" />
            </CardContent>
          </Card>
          <Card className="bg-[#0F6E56] border-none shadow-lg">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-100">Monto total del día</p>
                <p className="text-3xl font-extrabold text-white" data-testid="resumen-total-monto">{formatCurrency(resumen?.total_monto || 0)}</p>
              </div>
              <Receipt className="w-10 h-10 text-emerald-200" />
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Detalle de Ventas</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-slate-400 text-sm py-8 text-center">Cargando ventas...</p>
            ) : ventas.length === 0 ? (
              <div className="text-center py-12 text-slate-400" data-testid="ventas-empty-state">
                <Receipt className="w-12 h-12 mx-auto mb-2" />
                <p>No hay ventas registradas hoy</p>
              </div>
            ) : (
              <div className="space-y-2">
                {ventas.map((venta) => (
                  <div
                    key={venta.id}
                    className="p-3 bg-slate-50 rounded-lg flex items-center justify-between hover:bg-slate-100 cursor-pointer transition-colors"
                    onClick={() => verDetalle(venta.id)}
                    data-testid={`venta-row-${venta.id}`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-medium">{venta.numero_venta}</span>
                        <Badge variant={venta.estado === 'completada' ? 'outline' : 'destructive'}>
                          {venta.estado}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-500">
                        {venta.paciente_nombre || 'Cliente General'} • {venta.cantidad_items} items
                      </p>
                      <p className="text-xs text-slate-400">
                        {formatTime(venta.fecha)} • {venta.vendedor_nombre}
                      </p>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <p className="text-lg font-bold text-[#0F6E56]">{formatCurrency(venta.total)}</p>
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Dialog: Detalle de Venta */}
      <Dialog open={detalleOpen} onOpenChange={setDetalleOpen}>
        <DialogContent className="max-w-lg" data-testid="dialog-detalle-venta">
          <DialogHeader>
            <DialogTitle>Detalle de Venta</DialogTitle>
            <DialogDescription>
              {ventaDetalle?.numero_venta} • {ventaDetalle?.fecha && formatDate(ventaDetalle.fecha)}
            </DialogDescription>
          </DialogHeader>

          {ventaDetalle && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Cliente:</span>
                  <p className="font-medium">{ventaDetalle.paciente_nombre || 'Cliente General'}</p>
                </div>
                <div>
                  <span className="text-slate-500">Vendedor:</span>
                  <p className="font-medium">{ventaDetalle.vendedor_nombre}</p>
                </div>
              </div>

              <div className="border rounded-lg divide-y">
                {ventaDetalle.items?.map((item, idx) => (
                  <div key={idx} className="p-2 flex justify-between text-sm">
                    <div>
                      <p className="font-medium">{item.nombre}</p>
                      <p className="text-slate-500">{item.cantidad} x {formatCurrency(item.precio_unitario)}</p>
                    </div>
                    <span className="font-medium">{formatCurrency(item.subtotal)}</span>
                  </div>
                ))}
              </div>

              <div className="border-t pt-2 space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Subtotal</span>
                  <span>{formatCurrency(ventaDetalle.subtotal)}</span>
                </div>
                {ventaDetalle.descuento_total > 0 && (
                  <div className="flex justify-between text-sm text-red-600">
                    <span>Descuento{ventaDetalle.descuento_autoriza ? ` (aut. ${ventaDetalle.descuento_autoriza})` : ''}</span>
                    <span>- {formatCurrency(ventaDetalle.descuento_total)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg">
                  <span>Total</span>
                  <span className="text-[#0F6E56]">{formatCurrency(ventaDetalle.total)}</span>
                </div>
              </div>

              <div className="text-sm">
                <span className="text-slate-500">Forma de pago: </span>
                {ventaDetalle.formas_pago?.map((fp) => fp.metodo).join(', ')}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetalleOpen(false)} data-testid="btn-cerrar-detalle-venta">Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default VentasDelDia;
