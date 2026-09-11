import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus, Pencil, Trash2, RefreshCw, Download, Users, ChevronDown, ChevronRight,
  AlertTriangle, XCircle, FileSpreadsheet, RotateCcw,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from './ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from './ui/select';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Skeleton } from './ui/skeleton';
import { Textarea } from './ui/textarea';
import { toast } from 'sonner';
import { igssNogApi } from '../services/api';

const TIPO_COMPRA_OPTIONS = [
  { value: 'compra_directa', label: 'Compra Directa' },
  { value: 'baja_cuantia', label: 'Baja Cuantía' },
  { value: 'contrato', label: 'Contrato' },
  { value: 'convenio', label: 'Convenio' },
];

const fmtQ = (n) => `Q ${Number(n || 0).toLocaleString('es-GT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtFecha = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' });
  } catch (e) {
    return iso.slice(0, 10);
  }
};

const descargarBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const EstadoBadge = ({ estado }) => {
  const map = {
    activo: { cls: 'bg-green-100 text-green-700', label: 'Activo' },
    por_completarse: { cls: 'bg-amber-100 text-amber-700', label: 'Por completarse' },
    completado: { cls: 'bg-red-100 text-red-700', label: 'Completado' },
    inactivo: { cls: 'bg-gray-100 text-gray-600', label: 'Inactivo' },
  };
  const s = map[estado] || map.activo;
  return <Badge className={s.cls} data-testid={`nog-estado-${estado}`}>{s.label}</Badge>;
};

// Formulario de creación / edición de NOG
const NogForm = ({ open, onOpenChange, unitId, editing, onSaved }) => {
  const empty = { numero: '', nombre_servicio: '', tipo_compra: '', cantidad: '', precio: '', is_active: true };
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(editing ? {
        numero: editing.numero || '',
        nombre_servicio: editing.nombre_servicio || '',
        tipo_compra: editing.tipo_compra || '',
        cantidad: String(editing.cantidad ?? ''),
        precio: String(editing.precio ?? ''),
        is_active: editing.is_active !== false,
      } : empty);
    }
  }, [open, editing]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.numero.trim()) { toast.error('El número de NOG es obligatorio'); return; }
    const cantidad = parseInt(form.cantidad, 10);
    if (!cantidad || cantidad < 1) { toast.error('La cantidad de servicios debe ser mayor a 0'); return; }
    const precio = parseFloat(form.precio) || 0;
    setSaving(true);
    try {
      if (editing) {
        await igssNogApi.update(editing.id, {
          numero: form.numero.trim(),
          nombre_servicio: form.nombre_servicio,
          tipo_compra: form.tipo_compra,
          cantidad,
          precio,
          is_active: form.is_active,
        });
        toast.success('NOG actualizado');
      } else {
        const res = await igssNogApi.create(unitId, {
          numero: form.numero.trim(),
          nombre_servicio: form.nombre_servicio,
          tipo_compra: form.tipo_compra,
          cantidad,
          precio,
        });
        const retro = res.data?.acreditaciones_retroactivas || 0;
        toast.success(retro > 0 ? `NOG creado. Se acreditaron ${retro} servicio(s) existentes.` : 'NOG creado');
      }
      onSaved();
      onOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar el NOG');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{editing ? 'Editar NOG' : 'Nuevo NOG'}</DialogTitle>
          <DialogDescription>
            {editing ? 'Actualiza los datos del contrato de servicios.' : 'Cada NOG es un contrato de servicios que se debe cumplir de forma exacta.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">Número de NOG *</Label>
              <Input value={form.numero} onChange={(e) => setForm((p) => ({ ...p, numero: e.target.value }))}
                className="input-teal" placeholder="Ej: NOG-2024-001" data-testid="nog-form-numero" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Tipo de compra</Label>
              <Select value={form.tipo_compra} onValueChange={(v) => setForm((p) => ({ ...p, tipo_compra: v }))}>
                <SelectTrigger className="input-teal" data-testid="nog-form-tipo-compra">
                  <SelectValue placeholder="Seleccionar" />
                </SelectTrigger>
                <SelectContent>
                  {TIPO_COMPRA_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Nombre del servicio</Label>
            <Input value={form.nombre_servicio} onChange={(e) => setForm((p) => ({ ...p, nombre_servicio: e.target.value }))}
              className="input-teal" placeholder="Ej: Consulta oftalmológica" data-testid="nog-form-servicio" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs">Cantidad de servicios *</Label>
              <Input type="number" min="1" value={form.cantidad} onChange={(e) => setForm((p) => ({ ...p, cantidad: e.target.value }))}
                className="input-teal" placeholder="Ej: 100" data-testid="nog-form-cantidad" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Precio unitario (Q)</Label>
              <Input type="number" min="0" step="0.01" value={form.precio} onChange={(e) => setForm((p) => ({ ...p, precio: e.target.value }))}
                className="input-teal" placeholder="Ej: 150.00" data-testid="nog-form-precio" />
            </div>
          </div>
          {form.cantidad && form.precio && (
            <p className="text-xs text-gray-500" data-testid="nog-form-valor-total">
              Valor total del contrato: <strong>{fmtQ((parseInt(form.cantidad, 10) || 0) * (parseFloat(form.precio) || 0))}</strong>
            </p>
          )}
          {editing && (
            <div className="flex items-center gap-2">
              <input type="checkbox" id="nog-activo" checked={form.is_active}
                onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))} data-testid="nog-form-activo" />
              <Label htmlFor="nog-activo" className="text-xs cursor-pointer">NOG activo (puede asignarse a pacientes)</Label>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" className="btn-outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" className="btn-primary" disabled={saving} data-testid="nog-form-submit">
              {saving ? 'Guardando...' : (editing ? 'Guardar cambios' : 'Crear NOG')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// Fila expandible de pacientes acreditados de un NOG
const PacientesNog = ({ nogId, onAnulada }) => {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [anularTarget, setAnularTarget] = useState(null);
  const [motivo, setMotivo] = useState('');
  const [anulando, setAnulando] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await igssNogApi.getPacientes(nogId);
      setRows(res.data?.acreditaciones || []);
    } catch (e) {
      toast.error('Error al cargar pacientes del NOG');
    } finally {
      setLoading(false);
    }
  }, [nogId]);

  useEffect(() => { fetch(); }, [fetch]);

  const confirmarAnular = async () => {
    if (!anularTarget) return;
    setAnulando(true);
    try {
      await igssNogApi.anularAcreditacion(nogId, anularTarget.acreditacion_id, motivo);
      toast.success('Acreditación anulada. El servicio quedó disponible.');
      setAnularTarget(null);
      setMotivo('');
      fetch();
      onAnulada && onAnulada();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al anular la acreditación');
    } finally {
      setAnulando(false);
    }
  };

  if (loading) return <div className="p-4"><Skeleton className="h-24 w-full" /></div>;
  if (rows.length === 0) return <div className="p-4 text-sm text-gray-500">No hay pacientes acreditados en este NOG.</div>;

  return (
    <div className="p-3 bg-gray-50 rounded-lg" data-testid={`nog-pacientes-${nogId}`}>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="table-header">Expediente</TableHead>
              <TableHead className="table-header">Paciente</TableHead>
              <TableHead className="table-header">DPI</TableHead>
              <TableHead className="table-header">Afiliación</TableHead>
              <TableHead className="table-header">Fecha acreditación</TableHead>
              <TableHead className="table-header text-right">Acción</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.acreditacion_id} data-testid={`nog-acred-row-${r.acreditacion_id}`}>
                <TableCell className="font-mono text-xs">{r.record_number || '—'}</TableCell>
                <TableCell className="font-medium">{r.full_name}</TableCell>
                <TableCell className="text-xs">{r.dpi || '—'}</TableCell>
                <TableCell className="text-xs">{r.igss_afiliacion || '—'}</TableCell>
                <TableCell className="text-xs">{fmtFecha(r.fecha_acreditacion)}</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" className="h-8 text-red-600 hover:bg-red-100"
                    onClick={() => setAnularTarget(r)} data-testid={`nog-anular-${r.acreditacion_id}`}>
                    <RotateCcw className="w-3.5 h-3.5 mr-1" />Anular
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={!!anularTarget} onOpenChange={(o) => { if (!o) { setAnularTarget(null); setMotivo(''); } }}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Anular acreditación</DialogTitle>
            <DialogDescription>
              Se liberará 1 servicio del NOG (volverá a quedar disponible). Esta acción corrige una acreditación hecha por error.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label className="text-xs">Motivo (opcional)</Label>
            <Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} className="input-teal"
              placeholder="Ej: registrado por error" data-testid="nog-anular-motivo" />
          </div>
          <DialogFooter>
            <Button variant="outline" className="btn-outline" onClick={() => { setAnularTarget(null); setMotivo(''); }}>Cancelar</Button>
            <Button variant="destructive" onClick={confirmarAnular} disabled={anulando} data-testid="nog-anular-confirm">
              {anulando ? 'Anulando...' : 'Anular'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Diálogo principal: gestión de NOG de una unidad IGSS
export const NogsUnidadDialog = ({ unit, open, onOpenChange, initialNogId = null, onChanged }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [busyNog, setBusyNog] = useState(null);

  const fetch = useCallback(async () => {
    if (!unit) return;
    setLoading(true);
    try {
      const res = await igssNogApi.getByUnit(unit.id);
      setData(res.data);
    } catch (e) {
      toast.error('Error al cargar los NOG de la unidad');
    } finally {
      setLoading(false);
    }
  }, [unit]);

  const refresh = useCallback(() => {
    fetch();
    if (onChanged) onChanged();
  }, [fetch, onChanged]);

  useEffect(() => { if (open) { fetch(); setExpanded(initialNogId || null); } }, [open, fetch, initialNogId]);

  const recalcular = async (nog) => {
    setBusyNog(nog.id);
    try {
      const res = await igssNogApi.recalcular(nog.id);
      const nuevas = res.data?.acreditaciones_nuevas || 0;
      toast.success(nuevas > 0 ? `Recalculado: ${nuevas} acreditación(es) nueva(s).` : 'Recalculado: sin cambios.');
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al recalcular');
    } finally {
      setBusyNog(null);
    }
  };

  const exportNog = async (nog) => {
    try {
      const res = await igssNogApi.exportExcel(nog.id);
      descargarBlob(res.data, `NOG_${nog.numero}.xlsx`);
    } catch (e) {
      toast.error('Error al exportar el NOG');
    }
  };

  const exportUnidad = async () => {
    try {
      const res = await igssNogApi.exportUnidadExcel(unit.id);
      descargarBlob(res.data, `Unidad_${unit.name}_NOGs.xlsx`);
    } catch (e) {
      toast.error('Error al exportar la unidad');
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await igssNogApi.delete(deleteTarget.id);
      toast.success('NOG eliminado');
      setDeleteTarget(null);
      refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al eliminar el NOG');
    } finally {
      setDeleting(false);
    }
  };

  const nogs = data?.nogs || [];
  const totales = data?.totales || {};
  const fuera = data?.pacientes_nog_no_catalogado || [];
  const sinNog = data?.pacientes_sin_nog || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="nogs-unidad-dialog">
        <DialogHeader>
          <DialogTitle>NOG — {unit?.name || data?.unidad?.name || ''}</DialogTitle>
          <DialogDescription>
            Contratos de servicios del IGSS. El sistema acredita 1 servicio por atención (evaluación) y bloquea el NOG al completarse.
          </DialogDescription>
        </DialogHeader>

        {/* Acciones */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-4 text-sm">
            <span style={{ color: 'var(--text-secondary)' }}>Contratados: <strong>{totales.servicios_contratados ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }}>Acreditados: <strong>{totales.servicios_acreditados ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }}>Disponibles: <strong>{totales.servicios_disponibles ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }}>Valor: <strong>{fmtQ(totales.valor_total)}</strong></span>
          </div>
          <div className="flex gap-2">
            {nogs.length > 0 && (
              <Button variant="outline" size="sm" className="btn-outline" onClick={exportUnidad} data-testid="nog-export-unidad">
                <FileSpreadsheet className="w-4 h-4 mr-2" />Exportar unidad
              </Button>
            )}
            <Button size="sm" className="btn-primary" onClick={() => { setEditing(null); setFormOpen(true); }} data-testid="nog-add-button">
              <Plus className="w-4 h-4 mr-2" />Nuevo NOG
            </Button>
          </div>
        </div>

        {/* Tabla de NOG */}
        {loading ? (
          <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
        ) : nogs.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            Esta unidad aún no tiene NOG registrados. Crea el primero con &quot;Nuevo NOG&quot;.
          </div>
        ) : (
          <div className="overflow-x-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                  <TableHead className="table-header w-8"></TableHead>
                  <TableHead className="table-header">NOG / Servicio</TableHead>
                  <TableHead className="table-header">Tipo compra</TableHead>
                  <TableHead className="table-header text-center">Avance</TableHead>
                  <TableHead className="table-header text-right">Precio</TableHead>
                  <TableHead className="table-header">Estado</TableHead>
                  <TableHead className="table-header text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nogs.map((n) => (
                  <React.Fragment key={n.id}>
                    <TableRow data-testid={`nog-row-${n.id}`}>
                      <TableCell>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0"
                          onClick={() => setExpanded(expanded === n.id ? null : n.id)}
                          data-testid={`nog-expand-${n.id}`}>
                          {expanded === n.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </Button>
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold">{n.numero}</div>
                        <div className="text-xs text-gray-500">{n.nombre_servicio || 'Sin nombre de servicio'}</div>
                      </TableCell>
                      <TableCell className="text-xs">{n.tipo_compra_label || '—'}</TableCell>
                      <TableCell className="min-w-[140px]">
                        <div className="flex items-center gap-1 text-xs mb-1">
                          <strong>{n.acreditados}</strong> / {n.cantidad}
                          {n.estado === 'por_completarse' && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                          {n.estado === 'completado' && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                        </div>
                        <Progress value={n.porcentaje} className="h-2" data-testid={`nog-progress-${n.id}`} />
                        <div className="text-[11px] text-gray-400 mt-0.5">{n.disponibles} disp.</div>
                      </TableCell>
                      <TableCell className="text-right text-xs">
                        {fmtQ(n.precio)}
                        <div className="text-[11px] text-gray-400">Total {fmtQ(n.valor_total)}</div>
                      </TableCell>
                      <TableCell><EstadoBadge estado={n.estado} /></TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Recalcular"
                            disabled={busyNog === n.id} onClick={() => recalcular(n)} data-testid={`nog-recalcular-${n.id}`}>
                            <RefreshCw className={`w-4 h-4 ${busyNog === n.id ? 'animate-spin' : ''}`} />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Exportar"
                            onClick={() => exportNog(n)} data-testid={`nog-export-${n.id}`}>
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Editar"
                            onClick={() => { setEditing(n); setFormOpen(true); }} data-testid={`nog-edit-${n.id}`}>
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-600 hover:bg-red-100" title="Eliminar"
                            onClick={() => setDeleteTarget(n)} data-testid={`nog-delete-${n.id}`}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {expanded === n.id && (
                      <TableRow>
                        <TableCell colSpan={7} className="p-0">
                          <PacientesNog nogId={n.id} onAnulada={refresh} />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Pacientes de la unidad fuera del catálogo / sin NOG */}
        {!loading && (fuera.length > 0 || sinNog.length > 0) && (
          <div className="space-y-4">
            {fuera.length > 0 && (
              <div data-testid="nog-fuera-catalogo">
                <div className="flex items-center gap-2 text-sm font-semibold text-amber-700 mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  Pacientes con NOG fuera del catálogo ({fuera.length})
                </div>
                <p className="text-xs text-gray-500 mb-2">Tienen un NOG escrito que aún no existe en el catálogo. Crea ese NOG para acreditarlos automáticamente.</p>
                <div className="overflow-x-auto border rounded-lg">
                  <Table>
                    <TableHeader><TableRow>
                      <TableHead className="table-header">Expediente</TableHead>
                      <TableHead className="table-header">Paciente</TableHead>
                      <TableHead className="table-header">NOG (texto)</TableHead>
                      <TableHead className="table-header">Teléfono</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {fuera.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell className="font-mono text-xs">{p.record_number || '—'}</TableCell>
                          <TableCell className="text-sm">{p.full_name}</TableCell>
                          <TableCell className="text-xs font-medium text-amber-700">{p.igss_nog}</TableCell>
                          <TableCell className="text-xs">{p.phone || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
            {sinNog.length > 0 && (
              <div data-testid="nog-sin-nog">
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-600 mb-2">
                  <Users className="w-4 h-4" />
                  Pacientes sin NOG asignado ({sinNog.length})
                </div>
                <div className="overflow-x-auto border rounded-lg">
                  <Table>
                    <TableHeader><TableRow>
                      <TableHead className="table-header">Expediente</TableHead>
                      <TableHead className="table-header">Paciente</TableHead>
                      <TableHead className="table-header">Teléfono</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {sinNog.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell className="font-mono text-xs">{p.record_number || '—'}</TableCell>
                          <TableCell className="text-sm">{p.full_name}</TableCell>
                          <TableCell className="text-xs">{p.phone || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}

        <NogForm open={formOpen} onOpenChange={setFormOpen} unitId={unit?.id} editing={editing} onSaved={refresh} />

        <Dialog open={!!deleteTarget} onOpenChange={(o) => { if (!o) setDeleteTarget(null); }}>
          <DialogContent className="sm:max-w-[420px]">
            <DialogHeader>
              <DialogTitle>Eliminar NOG</DialogTitle>
              <DialogDescription>
                ¿Eliminar el NOG &quot;{deleteTarget?.numero}&quot;? Se borrarán también sus {deleteTarget?.acreditados || 0} acreditación(es). Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" className="btn-outline" onClick={() => setDeleteTarget(null)}>Cancelar</Button>
              <Button variant="destructive" onClick={confirmDelete} disabled={deleting} data-testid="nog-delete-confirm">
                {deleting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </DialogContent>
    </Dialog>
  );
};

export default NogsUnidadDialog;
