// /app/frontend/src/pages/AgendaBloqueos.js
// Componente para gestionar Bloqueos de Agenda (franjas, días, feriados y vacaciones).
// Permite crear y eliminar bloqueos por médico o de clínica, y muestra los bloqueos
// vigentes del día seleccionado. El enforcement (impedir citas) es del backend.

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Ban, Lock, Trash2, CalendarOff, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import agendaApi from '../services/agendaApi';

const nombreMedico = (m) => m?.name || m?.nombre || m?.full_name || 'Médico';

export const BloqueosAgenda = ({ medicos = [], fecha, onBloqueosChange }) => {
  const [bloqueosDia, setBloqueosDia] = useState([]);
  const [listaBloqueos, setListaBloqueos] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [conflictos, setConflictos] = useState([]);
  const [form, setForm] = useState({
    tipo: 'medico',
    medico_id: '',
    fecha_inicio: fecha,
    fecha_fin: '',
    dia_completo: true,
    hora_inicio: '09:00',
    hora_fin: '12:00',
    motivo: ''
  });

  const cargarBloqueosDia = useCallback(async () => {
    if (!fecha) return;
    try {
      const res = await agendaApi.getBloqueos({ fecha });
      setBloqueosDia(res.data.data || []);
    } catch (e) {
      // silencioso
    }
  }, [fecha]);

  useEffect(() => { cargarBloqueosDia(); }, [cargarBloqueosDia]);

  // Refresco periódico para reflejar bloqueos creados por otros usuarios
  useEffect(() => {
    const i = setInterval(() => { if (!document.hidden) cargarBloqueosDia(); }, 15000);
    return () => clearInterval(i);
  }, [cargarBloqueosDia]);

  const abrirCrear = () => {
    setForm({
      tipo: 'medico',
      medico_id: medicos[0]?.id || '',
      fecha_inicio: fecha,
      fecha_fin: '',
      dia_completo: true,
      hora_inicio: '09:00',
      hora_fin: '12:00',
      motivo: ''
    });
    setConflictos([]);
    setCreateOpen(true);
  };

  const abrirGestion = async () => {
    try {
      const hoy = new Date().toISOString().split('T')[0];
      const res = await agendaApi.getBloqueos({ desde: hoy });
      setListaBloqueos(res.data.data || []);
    } catch (e) {
      setListaBloqueos([]);
    }
    setManageOpen(true);
  };

  const guardar = async () => {
    if (form.tipo === 'medico' && !form.medico_id) { toast.error('Seleccione un médico'); return; }
    if (!form.fecha_inicio) { toast.error('Seleccione la fecha'); return; }
    if (form.fecha_fin && form.fecha_fin < form.fecha_inicio) { toast.error('La fecha fin no puede ser anterior'); return; }
    if (form.tipo === 'medico' && !form.dia_completo) {
      if (!form.hora_inicio || !form.hora_fin) { toast.error('Ingrese la franja de horas'); return; }
      if (form.hora_fin <= form.hora_inicio) { toast.error('La hora fin debe ser mayor a la hora inicio'); return; }
    }
    setSaving(true);
    try {
      const medico = medicos.find(m => m.id === form.medico_id);
      const payload = {
        tipo: form.tipo,
        medico_id: form.tipo === 'medico' ? form.medico_id : null,
        medico_nombre: form.tipo === 'medico' ? nombreMedico(medico) : null,
        fecha_inicio: form.fecha_inicio,
        fecha_fin: form.fecha_fin || form.fecha_inicio,
        dia_completo: form.tipo === 'clinica' ? true : form.dia_completo,
        hora_inicio: (form.tipo === 'medico' && !form.dia_completo) ? form.hora_inicio : null,
        hora_fin: (form.tipo === 'medico' && !form.dia_completo) ? form.hora_fin : null,
        motivo: form.motivo || null
      };
      const res = await agendaApi.crearBloqueo(payload);
      const conf = res.data.citas_en_conflicto || [];
      setConflictos(conf);
      if (conf.length > 0) {
        toast.warning(`Bloqueo creado. ${conf.length} cita(s) en conflicto para reprogramar.`);
      } else {
        toast.success('Bloqueo creado correctamente');
        setCreateOpen(false);
      }
      cargarBloqueosDia();
      if (onBloqueosChange) onBloqueosChange();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al crear el bloqueo');
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (id) => {
    try {
      await agendaApi.eliminarBloqueo(id);
      toast.success('Bloqueo eliminado');
      setListaBloqueos(prev => prev.filter(b => b.id !== id));
      cargarBloqueosDia();
      if (onBloqueosChange) onBloqueosChange();
    } catch (e) {
      toast.error('No se pudo eliminar el bloqueo');
    }
  };

  const etiquetaBloqueo = (b) => {
    if (b.tipo === 'clinica') {
      const rango = b.fecha_fin && b.fecha_fin !== b.fecha_inicio ? `${b.fecha_inicio} a ${b.fecha_fin}` : b.fecha_inicio;
      return `Clínica · ${rango}`;
    }
    const horario = b.dia_completo ? 'Día completo' : `${b.hora_inicio}–${b.hora_fin}`;
    return `${b.medico_nombre || 'Médico'} · ${horario}`;
  };

  return (
    <div className="space-y-2" data-testid="bloqueos-agenda">
      <div className="flex items-center gap-2 flex-wrap">
        <Button onClick={abrirCrear} variant="outline" size="sm" className="border-amber-300 text-amber-700 hover:bg-amber-50" data-testid="btn-abrir-bloqueo">
          <Ban className="w-4 h-4 mr-1" />
          Bloquear agenda
        </Button>
        <Button onClick={abrirGestion} variant="outline" size="sm" data-testid="btn-ver-bloqueos">
          <Lock className="w-4 h-4 mr-1" />
          Ver bloqueos
        </Button>
      </div>

      {/* Banner de bloqueos vigentes del día seleccionado */}
      {bloqueosDia.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap rounded-lg border border-amber-200 bg-amber-50 px-3 py-2" data-testid="bloqueos-dia-banner">
          <CalendarOff className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="text-xs font-medium text-amber-800">Bloqueos del día:</span>
          {bloqueosDia.map((b) => (
            <Badge
              key={b.id}
              variant="outline"
              className={`gap-1 ${b.tipo === 'clinica' ? 'border-red-300 bg-red-100 text-red-700' : 'border-amber-300 bg-amber-100 text-amber-800'}`}
              data-testid={`bloqueo-badge-${b.id}`}
            >
              {etiquetaBloqueo(b)}{b.motivo ? ` · ${b.motivo}` : ''}
              <button
                type="button"
                onClick={() => eliminar(b.id)}
                className="ml-1 hover:text-red-600"
                title="Eliminar bloqueo"
                data-testid={`btn-eliminar-bloqueo-${b.id}`}
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Dialog: crear bloqueo */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Ban className="w-5 h-5 text-amber-600" />
              Bloquear agenda
            </DialogTitle>
            <DialogDescription>
              Reserva espacios para que no se puedan agendar citas. Las citas existentes no se cancelan; se listan para reprogramar.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Tipo */}
            <div className="space-y-2">
              <Label>Tipo de bloqueo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                <SelectTrigger data-testid="bloqueo-tipo"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="medico">Por médico</SelectItem>
                  <SelectItem value="clinica">Clínica completa (feriado/vacaciones)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Médico */}
            {form.tipo === 'medico' && (
              <div className="space-y-2">
                <Label>Médico</Label>
                <Select value={form.medico_id} onValueChange={(v) => setForm({ ...form, medico_id: v })}>
                  <SelectTrigger data-testid="bloqueo-medico"><SelectValue placeholder="Seleccione médico" /></SelectTrigger>
                  <SelectContent>
                    {medicos.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{nombreMedico(m)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Fechas */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{form.tipo === 'clinica' ? 'Fecha inicio' : 'Fecha'}</Label>
                <Input
                  type="date"
                  value={form.fecha_inicio}
                  onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
                  data-testid="bloqueo-fecha-inicio"
                />
              </div>
              {form.tipo === 'clinica' && (
                <div className="space-y-2">
                  <Label>Fecha fin (opcional)</Label>
                  <Input
                    type="date"
                    value={form.fecha_fin}
                    min={form.fecha_inicio}
                    onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
                    data-testid="bloqueo-fecha-fin"
                  />
                </div>
              )}
            </div>

            {/* Día completo / franja (solo médico) */}
            {form.tipo === 'medico' && (
              <>
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <Label className="cursor-pointer">Día completo</Label>
                    <p className="text-xs text-slate-500">Desactiva para bloquear una franja de horas</p>
                  </div>
                  <Switch
                    checked={form.dia_completo}
                    onCheckedChange={(v) => setForm({ ...form, dia_completo: v })}
                    data-testid="bloqueo-dia-completo"
                  />
                </div>

                {!form.dia_completo && (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Hora inicio</Label>
                      <Input type="time" value={form.hora_inicio} onChange={(e) => setForm({ ...form, hora_inicio: e.target.value })} data-testid="bloqueo-hora-inicio" />
                    </div>
                    <div className="space-y-2">
                      <Label>Hora fin</Label>
                      <Input type="time" value={form.hora_fin} onChange={(e) => setForm({ ...form, hora_fin: e.target.value })} data-testid="bloqueo-hora-fin" />
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Motivo */}
            <div className="space-y-2">
              <Label>Motivo (opcional)</Label>
              <Textarea
                value={form.motivo}
                onChange={(e) => setForm({ ...form, motivo: e.target.value })}
                placeholder="Ej: Vacaciones, Congreso, Almuerzo, Feriado..."
                rows={2}
                data-testid="bloqueo-motivo"
              />
            </div>

            {/* Citas en conflicto */}
            {conflictos.length > 0 && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 p-3" data-testid="bloqueo-conflictos">
                <div className="flex items-center gap-2 text-amber-800 font-medium text-sm mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  {conflictos.length} cita(s) en conflicto (reprograme manualmente)
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {conflictos.map((c) => (
                    <div key={c.id} className="text-xs text-slate-700 flex justify-between border-b border-amber-200 py-1">
                      <span>{c.paciente_nombre} · {c.medico_nombre}</span>
                      <span className="font-medium">{c.fecha} {c.hora_inicio}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              {conflictos.length > 0 ? 'Cerrar' : 'Cancelar'}
            </Button>
            {conflictos.length === 0 && (
              <Button onClick={guardar} disabled={saving} className="bg-amber-600 hover:bg-amber-700" data-testid="btn-guardar-bloqueo">
                {saving ? 'Guardando...' : 'Crear bloqueo'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: gestionar bloqueos */}
      <Dialog open={manageOpen} onOpenChange={setManageOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-slate-600" />
              Bloqueos vigentes
            </DialogTitle>
            <DialogDescription>Bloqueos de hoy en adelante. Cualquier usuario puede eliminarlos.</DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-2" data-testid="lista-bloqueos">
            {listaBloqueos.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">No hay bloqueos vigentes</p>
            ) : (
              listaBloqueos.map((b) => (
                <div key={b.id} className="flex items-center justify-between rounded-lg border p-3" data-testid={`lista-bloqueo-${b.id}`}>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={b.tipo === 'clinica' ? 'border-red-300 bg-red-100 text-red-700' : 'border-amber-300 bg-amber-100 text-amber-800'}>
                      {b.tipo === 'clinica' ? 'Clínica' : 'Médico'}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium text-slate-800">{etiquetaBloqueo(b)}</p>
                      {b.motivo && <p className="text-xs text-slate-500">{b.motivo}</p>}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => eliminar(b.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    data-testid={`btn-eliminar-lista-${b.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
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

export default BloqueosAgenda;
