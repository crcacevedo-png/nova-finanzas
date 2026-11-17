import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus, Pencil, Trash2, Download, Users, ChevronDown, ChevronRight,
  AlertTriangle, XCircle, FileSpreadsheet,
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
import { toast } from 'sonner';
import { igssNogApi } from '../services/api';
import { descargarBlob, etiquetaCatalogo, nombreListado } from '../lib/igssLibro';

const TIPO_COMPRA_OPTIONS = [
  { value: 'compra_directa', label: 'Compra Directa' },
  { value: 'baja_cuantia', label: 'Baja Cuantía' },
  { value: 'contrato', label: 'Contrato' },
  { value: 'convenio', label: 'Convenio' },
];

const fmtQ = (n) => `Q ${Number(n || 0).toLocaleString('es-GT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtDia = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');

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

// Órdenes vigentes (atendidas y pendientes) de un NOG, leídas del libro IGSS
const ESTADO_ORDEN = {
  atendida: { cls: 'bg-emerald-100 text-emerald-700', label: 'Atendida' },
  pendiente: { cls: 'bg-amber-100 text-amber-700', label: 'Pendiente' },
};

const FilaOrden = ({ o }) => {
  const est = ESTADO_ORDEN[o.estado] || ESTADO_ORDEN.pendiente;
  return (
    <TableRow data-testid={`nog-orden-row-${o.orden_id}`}>
      <TableCell className="font-mono text-xs">{o.no_sps}</TableCell>
      <TableCell className="font-medium">
        {o.paciente_nombre}
        {!o.paciente_activo && <span className="ml-1 text-[10px] text-gray-400">(inactivo)</span>}
      </TableCell>
      <TableCell className="font-mono text-xs">{o.expediente || '—'}</TableCell>
      <TableCell><Badge className={est.cls} data-testid={`nog-orden-estado-${o.orden_id}`}>{est.label}</Badge></TableCell>
      <TableCell className="text-xs">{fmtDia(o.fecha_primera_atencion)}</TableCell>
      <TableCell className="text-xs text-center">{o.dosis_aplicadas} / {o.dosis_autorizadas}</TableCell>
      <TableCell className="text-xs text-right">{fmtQ(o.costo)}</TableCell>
    </TableRow>
  );
};

const OrdenesNog = ({ nogId }) => {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    igssNogApi.getPacientes(nogId)
      .then((res) => { if (vivo) setRows(res.data?.ordenes || []); })
      .catch(() => { if (vivo) toast.error('Error al cargar las órdenes del NOG'); })
      .finally(() => { if (vivo) setLoading(false); });
    return () => { vivo = false; };
  }, [nogId]);

  if (loading) return <div className="p-4"><Skeleton className="h-24 w-full" /></div>;

  return (
    <div className="p-3 bg-gray-50 rounded-lg" data-testid={`nog-ordenes-${nogId}`}>
      {rows.length === 0 ? (
        <div className="p-2 text-sm text-gray-500">No hay órdenes vigentes en este NOG.</div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="table-header">No. SPS</TableHead>
                <TableHead className="table-header">Paciente</TableHead>
                <TableHead className="table-header">Expediente</TableHead>
                <TableHead className="table-header">Estado</TableHead>
                <TableHead className="table-header">1ª atención</TableHead>
                <TableHead className="table-header text-center">Dosis</TableHead>
                <TableHead className="table-header text-right">Precio</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((o) => <FilaOrden key={o.orden_id} o={o} />)}
            </TableBody>
          </Table>
        </div>
      )}
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
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const rango = { desde: desde || undefined, hasta: hasta || undefined };

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

  const exportNog = async (nog) => {
    try {
      const res = await igssNogApi.exportExcel(nog.id, rango);
      descargarBlob(res.data, nombreListado(etiquetaCatalogo(nog), rango));
    } catch (e) {
      toast.error('Error al exportar el NOG');
    }
  };

  const exportUnidad = async () => {
    try {
      const res = await igssNogApi.exportUnidadExcel(unit.id, rango);
      descargarBlob(res.data, nombreListado(unit.name, rango));
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
            Contratos de servicios del IGSS. Cada orden (No. SPS) ocupa 1 cupo: reservada mientras está pendiente y consumida al atenderse. El NOG se bloquea al completarse.
          </DialogDescription>
        </DialogHeader>

        {/* Acciones */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-4 text-sm">
            <span style={{ color: 'var(--text-secondary)' }}>Contratados: <strong>{totales.servicios_contratados ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }} data-testid="nog-unidad-consumidos">Consumidos: <strong>{totales.consumidos ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }} data-testid="nog-unidad-reservados">Reservados: <strong>{totales.reservados ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }}>Disponibles: <strong>{totales.servicios_disponibles ?? 0}</strong></span>
            <span style={{ color: 'var(--text-secondary)' }}>Valor: <strong>{fmtQ(totales.valor_total)}</strong></span>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            {nogs.length > 0 && (
              <>
                <div>
                  <Label className="text-[11px] text-gray-500">Desde (1ª atención)</Label>
                  <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="input-teal h-8 w-36 text-xs" data-testid="nog-export-desde" />
                </div>
                <div>
                  <Label className="text-[11px] text-gray-500">Hasta</Label>
                  <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="input-teal h-8 w-36 text-xs" data-testid="nog-export-hasta" />
                </div>
                <Button variant="outline" size="sm" className="btn-outline" onClick={exportUnidad} data-testid="nog-export-unidad">
                  <FileSpreadsheet className="w-4 h-4 mr-2" />Listado oficial
                </Button>
              </>
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
                        <div className={`font-semibold ${n.numero ? '' : 'text-amber-700'}`}>{etiquetaCatalogo(n)}</div>
                        <div className="text-xs text-gray-500">{n.nombre_servicio || 'Sin nombre de servicio'}</div>
                      </TableCell>
                      <TableCell className="text-xs">{n.tipo_compra_label || '—'}</TableCell>
                      <TableCell className="min-w-[160px]" data-testid={`nog-avance-${n.id}`}>
                        {n.disponibles == null ? (
                          <div className="text-xs"><strong>{n.usados}</strong> órdenes · <span className="text-gray-400">sin tope</span></div>
                        ) : (
                          <>
                            <div className="flex items-center gap-1 text-xs mb-1">
                              <strong>{n.usados}</strong> / {n.cantidad}
                              {n.estado === 'por_completarse' && <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                              {n.estado === 'completado' && <XCircle className="w-3.5 h-3.5 text-red-500" />}
                            </div>
                            <Progress value={n.porcentaje || 0} className="h-2" data-testid={`nog-progress-${n.id}`} />
                          </>
                        )}
                        <div className="text-[11px] text-gray-400 mt-0.5">
                          {n.consumidos} atendidas · {n.reservados} reservadas{n.disponibles != null ? ` · ${n.disponibles} disp.` : ''}
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-xs">
                        {fmtQ(n.precio)}
                        <div className="text-[11px] text-gray-400">Total {fmtQ(n.valor_total)}</div>
                      </TableCell>
                      <TableCell><EstadoBadge estado={n.estado} /></TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Listado oficial del NOG"
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
                          <OrdenesNog nogId={n.id} />
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
                ¿Eliminar &quot;{deleteTarget ? etiquetaCatalogo(deleteTarget) : ''}&quot;? Solo es posible si no tiene órdenes en el libro (si las tiene, desactívelo). Esta acción no se puede deshacer.
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
