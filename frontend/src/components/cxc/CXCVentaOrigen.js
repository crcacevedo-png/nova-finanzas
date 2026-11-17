// Bloque "Venta de origen" para una cuenta por cobrar + vinculación manual.
// Solo cambia la referencia a la venta: no recalcula montos, saldos ni estado.
import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { ShoppingCart, Link2, Unlink, Search, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { formatCurrency, formatDate } from '../../services/api';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
const authHeaders = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

export const CXCVentaOrigen = ({ cuenta, puedeEditar = false, onChanged }) => {
  const venta = cuenta?.venta || null;
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [fecha, setFecha] = useState('');
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [pendiente, setPendiente] = useState(null); // { venta, mensaje } cuando requiere confirmación

  const buscar = useCallback(async () => {
    setBuscando(true);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.append('search', search.trim());
      if (fecha) params.append('fecha', fecha);
      params.append('origen', cuenta?.origen || 'clinica');
      const res = await axios.get(`${API_URL}/cuentas-cobrar/ventas/buscar?${params}`, authHeaders());
      setResultados(res.data?.data || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudieron buscar las ventas');
    } finally {
      setBuscando(false);
    }
  }, [search, fecha, cuenta?.origen]);

  const abrirBuscador = () => {
    setOpen(true);
    setPendiente(null);
    if (resultados.length === 0) buscar();
  };

  const vincular = async (v, confirmar = false) => {
    setGuardando(true);
    try {
      const res = await axios.put(
        `${API_URL}/cuentas-cobrar/${cuenta.id}/venta`,
        { venta_id: v.id, confirmar },
        authHeaders()
      );
      (res.data?.advertencias || []).forEach((a) => toast.warning(a));
      toast.success(res.data?.message || 'Venta vinculada');
      setOpen(false);
      setPendiente(null);
      if (onChanged) onChanged();
    } catch (e) {
      if (e.response?.status === 409) {
        setPendiente({ venta: v, mensaje: e.response?.data?.detail });
      } else {
        toast.error(e.response?.data?.detail || 'No se pudo vincular la venta');
      }
    } finally {
      setGuardando(false);
    }
  };

  const desvincular = async () => {
    setGuardando(true);
    try {
      await axios.delete(`${API_URL}/cuentas-cobrar/${cuenta.id}/venta`, authHeaders());
      toast.success('Venta desvinculada');
      if (onChanged) onChanged();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo desvincular la venta');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border-color)' }} data-testid="cxc-venta-origen">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShoppingCart className="h-4 w-4 text-slate-400" />
          <Label className="text-sm text-slate-500">Venta de origen</Label>
          {venta ? (
            <span className="font-mono text-sm font-medium text-slate-700" data-testid="cxc-venta-numero">
              {venta.numero_venta}
            </span>
          ) : (
            <span className="text-sm text-slate-400" data-testid="cxc-venta-sin-venta">Sin venta asociada</span>
          )}
          {venta?.estado === 'anulada' && (
            <Badge className="bg-slate-100 text-slate-600">Venta anulada</Badge>
          )}
        </div>
        {puedeEditar && (
          <div className="flex items-center gap-1 shrink-0">
            <Button variant="outline" size="sm" onClick={abrirBuscador} data-testid="cxc-vincular-venta-button">
              <Link2 className="h-4 w-4 mr-1" />
              {venta ? 'Cambiar venta' : 'Vincular venta'}
            </Button>
            {venta && (
              <Button
                variant="ghost" size="sm" disabled={guardando}
                onClick={desvincular} className="text-slate-500"
                data-testid="cxc-desvincular-venta-button"
              >
                <Unlink className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}
      </div>

      {venta && (
        <div className="mt-3 space-y-3" data-testid="cxc-venta-detalle">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-slate-500">Fecha</p>
              <p className="font-medium">{formatDate(venta.fecha)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Vendedor</p>
              <p className="font-medium">{venta.vendedor_nombre || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Médico</p>
              <p className="font-medium">{venta.medico_nombre || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Bodega</p>
              <p className="font-medium">{venta.bodega_nombre || '—'}</p>
            </div>
          </div>

          <div className="border rounded-lg divide-y" style={{ borderColor: 'var(--border-color)' }}>
            {venta.items.map((it, idx) => (
              <div key={`${it.codigo}-${idx}`} className="px-3 py-2 flex items-center justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate">{it.nombre}</p>
                  <p className="text-xs text-slate-500">
                    {it.cantidad} × {formatCurrency(it.precio_unitario)}
                    {it.descuento > 0 && ` • Desc. ${formatCurrency(it.descuento)}`}
                  </p>
                </div>
                <p className="font-medium shrink-0">{formatCurrency(it.subtotal)}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-xs text-slate-500">Total de la venta</p>
              <p className="font-semibold">{formatCurrency(venta.total)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Al crédito</p>
              <p className="font-semibold text-orange-600" data-testid="cxc-venta-credito">
                {formatCurrency(venta.monto_credito)}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Pagado en caja</p>
              <p className="font-semibold text-green-600">{formatCurrency(venta.monto_en_caja)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Buscador de ventas */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="w-[95vw] max-w-2xl max-h-[85vh] overflow-y-auto overflow-x-hidden grid-cols-[minmax(0,1fr)]"
          data-testid="cxc-buscar-venta-dialog"
        >
          <DialogHeader>
            <DialogTitle>Vincular venta</DialogTitle>
            <DialogDescription>
              Busca la venta por número de orden, paciente o fecha. Vincular no modifica montos ni saldos.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder={(cuenta?.origen === 'optica') ? 'ORD-2026... o nombre del paciente' : 'VTA-2026... o nombre del paciente'}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && buscar()}
                className="pl-9"
                data-testid="cxc-buscar-venta-input"
              />
            </div>
            <Input
              type="date" value={fecha} onChange={(e) => setFecha(e.target.value)}
              className="sm:w-44" data-testid="cxc-buscar-venta-fecha"
            />
            <Button onClick={buscar} disabled={buscando} data-testid="cxc-buscar-venta-submit">
              {buscando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Buscar'}
            </Button>
          </div>

          {pendiente && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm" data-testid="cxc-confirmar-vinculo">
              <p className="flex items-start gap-2 text-amber-800">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                {pendiente.mensaje}
              </p>
              <div className="flex gap-2 mt-2">
                <Button
                  size="sm" className="bg-amber-600 hover:bg-amber-700" disabled={guardando}
                  onClick={() => vincular(pendiente.venta, true)}
                  data-testid="cxc-confirmar-vinculo-button"
                >
                  Vincular de todas formas
                </Button>
                <Button size="sm" variant="outline" onClick={() => setPendiente(null)}>Cancelar</Button>
              </div>
            </div>
          )}

          <div className="border rounded-lg divide-y" style={{ borderColor: 'var(--border-color)' }}>
            {buscando ? (
              <div className="p-6 text-center text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin inline mr-2" />Buscando ventas...
              </div>
            ) : resultados.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-sm" data-testid="cxc-buscar-venta-vacio">
                No se encontraron ventas con esos datos.
              </div>
            ) : (
              resultados.map((v) => (
                <div key={v.id} className="p-3 flex items-center justify-between gap-3" data-testid={`cxc-venta-opcion-${v.id}`}>
                  <div className="min-w-0">
                    <p className="font-mono text-sm font-medium">{v.numero_venta}</p>
                    <p className="text-xs text-slate-500 truncate">
                      {formatDate(v.fecha)} • {v.paciente_nombre || 'Sin paciente'} • Total {formatCurrency(v.total)}
                      {v.monto_credito > 0 && ` • Crédito ${formatCurrency(v.monto_credito)}`}
                    </p>
                    {v.cuentas_vinculadas.length > 0 && (
                      <p className="text-xs text-amber-600 mt-0.5">
                        Ya vinculada a {v.cuentas_vinculadas.map((c) => c.numero_cuenta).join(', ')}
                      </p>
                    )}
                  </div>
                  <Button
                    size="sm" variant="outline" disabled={guardando || v.id === cuenta?.venta_id}
                    onClick={() => vincular(v)}
                    data-testid={`cxc-seleccionar-venta-${v.id}`}
                  >
                    {v.id === cuenta?.venta_id ? 'Vinculada' : 'Vincular'}
                  </Button>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CXCVentaOrigen;
