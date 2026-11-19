import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Loader2, ExternalLink, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi, surgeryApi, formatDateTime } from '../../services/api';

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');
const ESTADO_CX = { activo: 'Programada', realizado: 'Realizada', cancelado: 'Cancelada', reagendado: 'Reagendada' };

const Dato = ({ label, valor }) => (valor ? (
  <div className="flex gap-2 text-sm"><span className="w-32 shrink-0 text-slate-500">{label}</span><span className="text-slate-800">{valor}</span></div>
) : null);

// Datos originales de una cirugía, solo lectura
const CirugiaOriginalDialog = ({ cirugia, onClose }) => (
  <Dialog open={!!cirugia} onOpenChange={(v) => !v && onClose()}>
    <DialogContent className="max-w-lg" data-testid="constancia-cirugia-dialog">
      <DialogHeader>
        <DialogTitle>Cirugía original (solo lectura)</DialogTitle>
        <DialogDescription>Registro de Sala de Operaciones vinculado a la orden como constancia.</DialogDescription>
      </DialogHeader>
      {cirugia && (
        <div className="space-y-1.5" data-testid="constancia-cirugia-datos">
          <Dato label="Fecha" valor={`${fmt(cirugia.date)}${cirugia.time ? ` · ${cirugia.time}` : ''}`} />
          <Dato label="Paciente" valor={cirugia.patient_name} />
          <Dato label="Procedimiento" valor={cirugia.procedure} />
          <Dato label="Ojo" valor={cirugia.eye} />
          <Dato label="LIO" valor={cirugia.lio} />
          <Dato label="Cirujano" valor={cirugia.surgeon} />
          <Dato label="Ayudante" valor={cirugia.assistant_surgeon} />
          <Dato label="Anestesia" valor={[cirugia.anesthesia_type, cirugia.anesthesiologist].filter(Boolean).join(' · ')} />
          <Dato label="Estado" valor={ESTADO_CX[cirugia.status] || cirugia.status} />
          <Dato label="Realizada" valor={cirugia.realizada_en ? `${cirugia.realizada_por_nombre || '—'} · ${formatDateTime(cirugia.realizada_en)}` : ''} />
          <Dato label="Motivo de cancelación" valor={cirugia.cancellation_reason} />
          <Dato label="Observaciones" valor={cirugia.observations} />
        </div>
      )}
    </DialogContent>
  </Dialog>
);

// Constancias: servicios anteriores al libro vinculados a la orden por la migración (no cuentan como atenciones)
export const ConstanciasOrden = ({ orden }) => {
  const [cirugia, setCirugia] = useState(null);
  const [abriendo, setAbriendo] = useState('');
  const lista = orden.constancias || [];
  if (!lista.length) return null;

  const ver = async (c) => {
    setAbriendo(c.ref_id);
    try {
      if (c.tipo === 'cirugia') {
        setCirugia((await surgeryApi.getById(c.ref_id)).data);
      } else {
        const { data } = await igssLibroApi.pdfEvaluacion(c.ref_id);
        window.open(window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' })), '_blank');
      }
    } catch (e) {
      toast.error(e?.response?.status === 404 ? 'El registro original ya no existe' : 'No se pudo abrir el registro original');
    } finally {
      setAbriendo('');
    }
  };

  return (
    <div className="mt-2 border-t border-dashed border-slate-200 pt-2 space-y-1" data-testid={`orden-constancias-${orden.id}`}>
      <p className="text-xs font-medium text-slate-600">Constancias (servicios anteriores al libro) · solo lectura</p>
      {lista.map((c) => (
        <div key={`${c.tipo}-${c.ref_id}`} className="flex items-center justify-between gap-2 text-xs text-slate-600" data-testid={`constancia-${c.ref_id}`}>
          <span className="min-w-0">
            {c.tipo === 'cirugia' ? 'Cirugía' : 'Evaluación'} · {fmt(c.fecha)}
            {c.procedimiento ? ` · ${c.procedimiento}` : ''}{c.medico ? ` · ${c.medico}` : ''}
          </span>
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs shrink-0" type="button" disabled={abriendo === c.ref_id}
            onClick={() => ver(c)} data-testid={`constancia-ver-${c.ref_id}`}>
            {abriendo === c.ref_id ? <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              : c.tipo === 'cirugia' ? <ExternalLink className="w-3 h-3 mr-1" /> : <FileText className="w-3 h-3 mr-1" />}
            Ver original
          </Button>
        </div>
      ))}
      <CirugiaOriginalDialog cirugia={cirugia} onClose={() => setCirugia(null)} />
    </div>
  );
};
