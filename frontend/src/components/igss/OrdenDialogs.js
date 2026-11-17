import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi } from '../../services/api';
import { ESTADOS_ACTIVOS, estadoOrden } from './estadosLibro';

const errorDe = (e, fb) => (typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : fb);
const SIN_ORDEN = '__sin_orden__';

export const etiquetaOrden = (o) => `${o.no_sps} · ${o.etiqueta_nog}${o.procedimiento ? ` · ${o.procedimiento}` : ''}`;

// Pide un motivo (anular una orden o descartar una atención sin orden)
export const MotivoDialog = ({ open, onOpenChange, titulo, descripcion, accion, onConfirm, testId }) => {
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { if (open) setMotivo(''); }, [open]);
  const confirmar = async () => {
    if (motivo.trim().length < 3) { toast.error('Indique el motivo'); return; }
    setEnviando(true);
    try { await onConfirm(motivo.trim()); onOpenChange(false); } catch (e) { toast.error(errorDe(e, 'No se pudo completar')); } finally { setEnviando(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid={testId}>
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          {descripcion && <DialogDescription>{descripcion}</DialogDescription>}
        </DialogHeader>
        <Label className="text-xs">Motivo *</Label>
        <Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} data-testid={`${testId}-motivo`} />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={confirmar} disabled={enviando} className="bg-red-600 hover:bg-red-700" data-testid={`${testId}-confirmar`}>
            {enviando && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} {accion}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Elige una orden vigente del paciente (para asignar o reasignar una atención)
export const ElegirOrdenDialog = ({ open, onOpenChange, pacienteId, excluirId, permitirSinOrden, titulo, onConfirm }) => {
  const [ordenes, setOrdenes] = useState([]);
  const [sel, setSel] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => {
    if (!open || !pacienteId) return;
    setSel('');
    igssLibroApi.listar({ paciente_id: pacienteId, limit: 200 })
      .then(({ data }) => setOrdenes((data?.data || []).filter((o) => ESTADOS_ACTIVOS.includes(o.estado) && o.id !== excluirId)))
      .catch(() => setOrdenes([]));
  }, [open, pacienteId, excluirId]);
  const confirmar = async () => {
    if (!sel) { toast.error('Elija una orden'); return; }
    setEnviando(true);
    try { await onConfirm(sel === SIN_ORDEN ? null : sel); onOpenChange(false); } catch (e) { toast.error(errorDe(e, 'No se pudo asignar')); } finally { setEnviando(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="elegir-orden-dialog">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>Solo órdenes vigentes del mismo paciente. El cambio queda en auditoría.</DialogDescription>
        </DialogHeader>
        <Select value={sel} onValueChange={setSel}>
          <SelectTrigger data-testid="elegir-orden-select"><SelectValue placeholder={ordenes.length ? 'Seleccionar orden' : 'El paciente no tiene otras órdenes vigentes'} /></SelectTrigger>
          <SelectContent>
            {ordenes.map((o) => (
              <SelectItem key={o.id} value={o.id} data-testid={`elegir-orden-option-${o.id}`}>
                {etiquetaOrden(o)} · {o.tipo === 'procedimiento' ? `${o.dosis_aplicadas}/${o.dosis_autorizadas} dosis` : estadoOrden(o.estado)[1]}
              </SelectItem>
            ))}
            {permitirSinOrden && <SelectItem value={SIN_ORDEN} data-testid="elegir-orden-sin-orden">Dejar sin orden</SelectItem>}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={confirmar} disabled={enviando} className="bg-teal-600 hover:bg-teal-700" data-testid="elegir-orden-confirmar">
            {enviando && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Confirmar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
