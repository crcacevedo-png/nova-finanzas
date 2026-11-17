import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi, igssUnitApi } from '../../services/api';

const errorDe = (e, fb) => {
  const d = e?.response?.data?.detail;
  return typeof d === 'string' ? d : fb;
};

const VACIO = { unidad_id: '', nog_id: '', no_sps: '', tipo: 'consulta', dosis_autorizadas: 1, codigo: '', procedimiento: '', inyectable: false };

const cupoTexto = (c) => {
  if (c.sin_tope) return 'sin tope';
  const casiLleno = c.cantidad > 0 && c.ocupados >= c.cantidad * 0.9;
  return `${c.disponibles} disponibles${casiLleno && c.disponibles > 0 ? ' · ≥ 90 %' : ''}`;
};

// Crear o editar una orden del libro (No. SPS, entrada del catálogo, tipo y dosis)
export const OrdenLibroDialog = ({ open, onOpenChange, pacienteId, unidadId, orden, onSaved }) => {
  const [form, setForm] = useState(VACIO);
  const [unidades, setUnidades] = useState([]);
  const [catalogo, setCatalogo] = useState([]);
  const [guardando, setGuardando] = useState(false);
  const editando = !!orden;

  useEffect(() => {
    if (!open) return;
    setForm(orden ? { ...VACIO, ...orden, dosis_autorizadas: orden.dosis_autorizadas || 1 } : { ...VACIO, unidad_id: unidadId || '' });
    if (!orden) igssUnitApi.getAll().then(({ data }) => setUnidades((data?.data || data || []).filter((u) => u.is_active !== false))).catch(() => setUnidades([]));
  }, [open, orden, unidadId]);

  useEffect(() => {
    if (!open || editando || !form.unidad_id) { setCatalogo([]); return; }
    igssLibroApi.catalogo(form.unidad_id).then(({ data }) => setCatalogo(data || [])).catch(() => setCatalogo([]));
  }, [open, editando, form.unidad_id]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const onTipo = (v) => setForm((f) => ({ ...f, tipo: v, dosis_autorizadas: v === 'consulta' ? 1 : f.dosis_autorizadas, inyectable: v === 'consulta' ? false : f.inyectable }));

  const guardar = async () => {
    if (!form.no_sps.trim()) { toast.error('El No. SPS es obligatorio'); return; }
    if (!editando && !form.nog_id) { toast.error('Elija la entrada del catálogo (NOG o Baja Cuantía)'); return; }
    const payload = {
      no_sps: form.no_sps, tipo: form.tipo, dosis_autorizadas: Number(form.dosis_autorizadas) || 1,
      codigo: form.codigo || '', procedimiento: form.procedimiento || '',
      inyectable: form.tipo === 'procedimiento' && !!form.inyectable,
    };
    setGuardando(true);
    try {
      if (editando) await igssLibroApi.editar(orden.id, payload);
      else {
        const { data } = await igssLibroApi.crear({ ...payload, nog_id: form.nog_id, paciente_id: pacienteId });
        if (data?.aviso_cupo) toast.warning(data.aviso_cupo, { duration: 8000 });
      }
      toast.success(editando ? 'Orden actualizada' : 'Orden registrada en el libro');
      onOpenChange(false);
      onSaved?.();
    } catch (e) {
      toast.error(errorDe(e, 'No se pudo guardar la orden'));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="orden-libro-dialog">
        <DialogHeader>
          <DialogTitle>{editando ? 'Editar orden IGSS' : 'Nueva orden IGSS'}</DialogTitle>
          <DialogDescription>Una orden = una hoja de autorización (No. SPS).</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {editando ? (
            <div className="sm:col-span-2 text-sm text-slate-600">
              Entrada: <span className="font-medium text-slate-800">{orden.etiqueta_nog}</span>
            </div>
          ) : (
            <>
              <div>
                <Label className="text-xs">Unidad *</Label>
                <Select value={form.unidad_id} onValueChange={(v) => setForm((f) => ({ ...f, unidad_id: v, nog_id: '' }))}>
                  <SelectTrigger className="mt-1" data-testid="orden-form-unidad"><SelectValue placeholder="Unidad" /></SelectTrigger>
                  <SelectContent>{unidades.map((u) => <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">NOG / Baja Cuantía *</Label>
                <Select value={form.nog_id} onValueChange={(v) => set('nog_id', v)} disabled={!form.unidad_id}>
                  <SelectTrigger className="mt-1" data-testid="orden-form-nog"><SelectValue placeholder="Entrada del catálogo" /></SelectTrigger>
                  <SelectContent>
                    {catalogo.map((c) => (
                      <SelectItem key={c.id} value={c.id} disabled={!c.sin_tope && c.disponibles <= 0} data-testid={`orden-form-nog-${c.id}`}>
                        {c.etiqueta} · {cupoTexto(c)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
          <div>
            <Label className="text-xs">No. SPS *</Label>
            <Input value={form.no_sps} onChange={(e) => set('no_sps', e.target.value)} className="mt-1 font-mono uppercase" data-testid="orden-form-sps" />
          </div>
          <div>
            <Label className="text-xs">Tipo</Label>
            <Select value={form.tipo} onValueChange={onTipo}>
              <SelectTrigger className="mt-1" data-testid="orden-form-tipo"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="consulta">Consulta</SelectItem>
                <SelectItem value="procedimiento">Procedimiento</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Dosis autorizadas</Label>
            <Select value={String(form.dosis_autorizadas)} onValueChange={(v) => set('dosis_autorizadas', Number(v))} disabled={form.tipo === 'consulta'}>
              <SelectTrigger className="mt-1" data-testid="orden-form-dosis"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 dosis</SelectItem>
                <SelectItem value="3">3 dosis</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Código</Label>
            <Input value={form.codigo} onChange={(e) => set('codigo', e.target.value)} className="mt-1" data-testid="orden-form-codigo" />
          </div>
          {form.tipo === 'procedimiento' && (
            <label className="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700 cursor-pointer" data-testid="orden-form-inyectable-label">
              <Checkbox checked={!!form.inyectable} onCheckedChange={(v) => set('inyectable', v === true)} data-testid="orden-form-inyectable" />
              Inyectable <span className="text-xs text-slate-400">(tratamiento por dosis, p. ej. anti-VEGF)</span>
            </label>
          )}
          <div className="sm:col-span-2">
            <Label className="text-xs">Procedimiento / Estudio</Label>
            <Input value={form.procedimiento} onChange={(e) => set('procedimiento', e.target.value)} placeholder="Ej: Avastin OD" className="mt-1" data-testid="orden-form-procedimiento" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={guardar} disabled={guardando} className="bg-teal-600 hover:bg-teal-700" data-testid="orden-form-guardar">
            {guardando && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
