import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { igssNogApi } from '../services/api';
import {
  ClipboardList, Plus, Search, Pencil, Power, PowerOff, Loader2, AlertTriangle, XCircle, CheckCircle2,
} from 'lucide-react';

const TIPO_COMPRA_OPTIONS = [
  { value: 'compra_directa', label: 'Compra Directa' },
  { value: 'baja_cuantia', label: 'Baja Cuantía' },
  { value: 'contrato', label: 'Contrato' },
  { value: 'convenio', label: 'Convenio' },
];

const ESTADO_OPTIONS = [
  { value: 'activo', label: 'Activo' },
  { value: 'por_completarse', label: 'Por completarse (90%)' },
  { value: 'completado', label: 'Completado (100%)' },
  { value: 'inactivo', label: 'Inactivo' },
];

const fmtQ = (n) => `Q ${Number(n || 0).toLocaleString('es-GT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtFecha = (f) => {
  if (!f) return '—';
  try {
    return new Date(`${f}T12:00:00`).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' });
  } catch (e) {
    return (f || '').slice(0, 10) || '—';
  }
};

const EstadoBadge = ({ estado }) => {
  const map = {
    activo: { cls: 'bg-green-100 text-green-700', label: 'Activo', icon: CheckCircle2 },
    por_completarse: { cls: 'bg-amber-100 text-amber-700', label: 'Por completarse', icon: AlertTriangle },
    completado: { cls: 'bg-red-100 text-red-700', label: 'Completado', icon: XCircle },
    inactivo: { cls: 'bg-gray-100 text-gray-600', label: 'Inactivo', icon: PowerOff },
  };
  const s = map[estado] || map.activo;
  const Icon = s.icon;
  return (
    <Badge className={`${s.cls} gap-1`} data-testid={`nog-estado-${estado}`}>
      <Icon className="w-3 h-3" />{s.label}
    </Badge>
  );
};

const emptyForm = {
  id: null, numero: '', nombre_servicio: '', tipo_compra: '', cantidad: '',
  precio: '', unidad_id: '', fecha_asignacion: '', is_active: true,
};

const GestionNOG = () => {
  const [loading, setLoading] = useState(true);
  const [nogs, setNogs] = useState([]);
  const [unidades, setUnidades] = useState([]);
  const [search, setSearch] = useState('');
  const [filtroUnidad, setFiltroUnidad] = useState('all');
  const [filtroEstado, setFiltroEstado] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [togglingId, setTogglingId] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await igssNogApi.getAll();
      setNogs(res.data.data || []);
      setUnidades(res.data.unidades || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudieron cargar los NOG');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return nogs.filter((n) => {
      if (filtroUnidad !== 'all' && n.unidad_id !== filtroUnidad) return false;
      if (filtroEstado !== 'all' && n.estado !== filtroEstado) return false;
      if (q) {
        const hay = `${n.numero} ${n.nombre_servicio}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [nogs, search, filtroUnidad, filtroEstado]);

  const abrirNuevo = () => {
    setForm({ ...emptyForm, unidad_id: filtroUnidad !== 'all' ? filtroUnidad : '' });
    setDialogOpen(true);
  };

  const abrirEditar = (n) => {
    setForm({
      id: n.id, numero: n.numero || '', nombre_servicio: n.nombre_servicio || '',
      tipo_compra: n.tipo_compra || '', cantidad: String(n.cantidad ?? ''),
      precio: String(n.precio ?? ''), unidad_id: n.unidad_id || '',
      fecha_asignacion: (n.fecha_asignacion || '').slice(0, 10), is_active: n.is_active,
    });
    setDialogOpen(true);
  };

  const guardar = async () => {
    if (!form.numero.trim()) { toast.error('El número de NOG es obligatorio'); return; }
    if (!form.unidad_id) { toast.error('La unidad es obligatoria'); return; }
    const cant = parseInt(form.cantidad, 10);
    if (!cant || cant < 1) { toast.error('La cantidad de cupos debe ser al menos 1'); return; }
    const payload = {
      numero: form.numero.trim(),
      nombre_servicio: form.nombre_servicio.trim(),
      tipo_compra: form.tipo_compra || '',
      cantidad: cant,
      precio: parseFloat(form.precio) || 0,
      fecha_asignacion: form.fecha_asignacion || '',
    };
    setSaving(true);
    try {
      if (form.id) {
        await igssNogApi.update(form.id, payload);
        toast.success('NOG actualizado');
      } else {
        await igssNogApi.create(form.unidad_id, payload);
        toast.success('NOG creado y disponible para asignar a pacientes');
      }
      setDialogOpen(false);
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar el NOG');
    } finally {
      setSaving(false);
    }
  };

  const toggleActivo = async (n) => {
    setTogglingId(n.id);
    try {
      await igssNogApi.update(n.id, { is_active: !n.is_active });
      toast.success(n.is_active ? 'NOG desactivado' : 'NOG activado');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo cambiar el estado');
    } finally {
      setTogglingId(null);
    }
  };

  const nombreUnidad = (id) => (unidades.find((u) => u.id === id) || {}).name || '';

  const totales = useMemo(() => ({
    total: filtered.length,
    cupos: filtered.reduce((a, n) => a + (n.cantidad || 0), 0),
    usados: filtered.reduce((a, n) => a + (n.acreditados || 0), 0),
    disponibles: filtered.reduce((a, n) => a + (n.is_active ? (n.disponibles || 0) : 0), 0),
  }), [filtered]);

  return (
    <Layout>
      <div className="space-y-6" data-testid="gestion-nog-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-teal-600 flex items-center justify-center shrink-0">
              <ClipboardList className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">NOG</h1>
              <p className="text-sm text-slate-500">Ingreso y gestión central de todos los NOG del IGSS</p>
            </div>
          </div>
          <Button onClick={abrirNuevo} className="bg-teal-600 hover:bg-teal-700" data-testid="nuevo-nog-button">
            <Plus className="w-4 h-4 mr-2" /> Nuevo NOG
          </Button>
        </div>

        {/* Totales */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'NOG (filtrados)', value: totales.total },
            { label: 'Cupos totales', value: totales.cupos },
            { label: 'Cupos usados', value: totales.usados },
            { label: 'Disponibles', value: totales.disponibles },
          ].map((c) => (
            <div key={c.label} className="rounded-xl border bg-white p-4">
              <p className="text-xs text-slate-500">{c.label}</p>
              <p className="text-2xl font-bold text-slate-800">{c.value}</p>
            </div>
          ))}
        </div>

        {/* Filtros */}
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Buscar por número o servicio..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
              data-testid="nog-search-input"
            />
          </div>
          <select
            value={filtroUnidad}
            onChange={(e) => setFiltroUnidad(e.target.value)}
            className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm md:w-56"
            data-testid="nog-filtro-unidad"
          >
            <option value="all">Todas las unidades</option>
            {unidades.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm md:w-48"
            data-testid="nog-filtro-estado"
          >
            <option value="all">Todos los estados</option>
            {ESTADO_OPTIONS.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
          </select>
        </div>

        {/* Tabla */}
        <div className="rounded-xl border bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="nog-table">
              <thead className="bg-slate-50 text-slate-600 text-left">
                <tr>
                  <th className="px-4 py-3 font-semibold">NOG</th>
                  <th className="px-4 py-3 font-semibold">Servicio</th>
                  <th className="px-4 py-3 font-semibold">Unidad</th>
                  <th className="px-4 py-3 font-semibold">Tipo compra</th>
                  <th className="px-4 py-3 font-semibold">Fecha asignación</th>
                  <th className="px-4 py-3 font-semibold text-center">Cupos</th>
                  <th className="px-4 py-3 font-semibold text-center">Disp.</th>
                  <th className="px-4 py-3 font-semibold text-right">Precio</th>
                  <th className="px-4 py-3 font-semibold">Estado</th>
                  <th className="px-4 py-3 font-semibold text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={10} className="px-4 py-10 text-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin inline mr-2" />Cargando...
                  </td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={10} className="px-4 py-10 text-center text-slate-400" data-testid="nog-empty">
                    No hay NOG que coincidan con los filtros.
                  </td></tr>
                ) : (
                  filtered.map((n) => (
                    <tr key={n.id} className="border-t hover:bg-slate-50" data-testid={`nog-row-${n.id}`}>
                      <td className="px-4 py-3 font-semibold text-slate-800">{n.numero}</td>
                      <td className="px-4 py-3 text-slate-600 max-w-[200px] truncate">{n.nombre_servicio || '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{n.unidad_nombre || '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{n.tipo_compra_label || '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{fmtFecha(n.fecha_asignacion)}</td>
                      <td className="px-4 py-3 text-center text-slate-600">{n.acreditados} / {n.cantidad}</td>
                      <td className="px-4 py-3 text-center font-medium text-slate-700">{n.disponibles}</td>
                      <td className="px-4 py-3 text-right text-slate-600">{fmtQ(n.precio)}</td>
                      <td className="px-4 py-3"><EstadoBadge estado={n.estado} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => abrirEditar(n)} data-testid={`nog-editar-${n.id}`}>
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost" size="sm"
                            disabled={togglingId === n.id}
                            onClick={() => toggleActivo(n)}
                            className={n.is_active ? 'text-red-600' : 'text-green-600'}
                            data-testid={`nog-toggle-${n.id}`}
                          >
                            {togglingId === n.id ? <Loader2 className="w-4 h-4 animate-spin" /> : (n.is_active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />)}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Dialog crear/editar */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg" data-testid="nog-dialog">
            <DialogHeader>
              <DialogTitle>{form.id ? 'Editar NOG' : 'Nuevo NOG'}</DialogTitle>
              <DialogDescription>
                {form.id ? 'Modifica los datos del NOG.' : 'Registra un NOG y asígnalo a una unidad IGSS. Quedará disponible de inmediato.'}
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Unidad IGSS *</Label>
                <select
                  value={form.unidad_id}
                  onChange={(e) => setForm((f) => ({ ...f, unidad_id: e.target.value }))}
                  disabled={!!form.id}
                  className="mt-1 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm disabled:bg-slate-100 disabled:opacity-70"
                  data-testid="nog-form-unidad"
                >
                  <option value="">Seleccionar unidad...</option>
                  {unidades.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </select>
                {form.id && <p className="text-xs text-slate-400 mt-1">La unidad no se puede cambiar al editar.</p>}
              </div>

              <div>
                <Label>Número de NOG *</Label>
                <Input
                  value={form.numero}
                  onChange={(e) => setForm((f) => ({ ...f, numero: e.target.value }))}
                  className="mt-1" data-testid="nog-form-numero"
                />
              </div>
              <div>
                <Label>Tipo de compra</Label>
                <select
                  value={form.tipo_compra}
                  onChange={(e) => setForm((f) => ({ ...f, tipo_compra: e.target.value }))}
                  className="mt-1 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm"
                  data-testid="nog-form-tipo-compra"
                >
                  <option value="">—</option>
                  {TIPO_COMPRA_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>

              <div className="col-span-2">
                <Label>Servicio</Label>
                <Input
                  value={form.nombre_servicio}
                  onChange={(e) => setForm((f) => ({ ...f, nombre_servicio: e.target.value }))}
                  placeholder="Nombre del servicio del NOG"
                  className="mt-1" data-testid="nog-form-servicio"
                />
              </div>

              <div>
                <Label>Cantidad de cupos *</Label>
                <Input
                  type="number" min="1"
                  value={form.cantidad}
                  onChange={(e) => setForm((f) => ({ ...f, cantidad: e.target.value }))}
                  className="mt-1" data-testid="nog-form-cantidad"
                />
              </div>
              <div>
                <Label>Precio por cupo (Q)</Label>
                <Input
                  type="number" min="0" step="0.01"
                  value={form.precio}
                  onChange={(e) => setForm((f) => ({ ...f, precio: e.target.value }))}
                  className="mt-1" data-testid="nog-form-precio"
                />
              </div>

              <div className="col-span-2">
                <Label>Fecha de asignación</Label>
                <Input
                  type="date"
                  value={form.fecha_asignacion}
                  onChange={(e) => setForm((f) => ({ ...f, fecha_asignacion: e.target.value }))}
                  className="mt-1" data-testid="nog-form-fecha-asignacion"
                />
                <p className="text-xs text-slate-400 mt-1">Fecha en que el IGSS asignó/autorizó el NOG.</p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving} data-testid="nog-form-cancelar">Cancelar</Button>
              <Button onClick={guardar} disabled={saving} className="bg-teal-600 hover:bg-teal-700" data-testid="nog-form-guardar">
                {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {form.id ? 'Guardar cambios' : 'Crear NOG'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default GestionNOG;
