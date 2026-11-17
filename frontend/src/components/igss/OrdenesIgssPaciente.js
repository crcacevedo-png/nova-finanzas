import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Plus, Pencil, Ban, ChevronDown, ChevronRight, Shuffle, Loader2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi } from '../../services/api';
import { OrdenLibroDialog } from './OrdenLibroDialog';
import { MotivoDialog, ElegirOrdenDialog } from './OrdenDialogs';

const ESTADO = {
  pendiente: ['bg-amber-50 text-amber-700 border-amber-200', 'Pendiente'],
  atendida: ['bg-emerald-50 text-emerald-700 border-emerald-200', 'Atendida'],
  anulada: ['bg-slate-100 text-slate-500 border-slate-200', 'Anulada'],
};

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');

const Atenciones = ({ orden, onReasignar }) => (
  <div className="mt-2 border-t border-slate-100 pt-2 space-y-1" data-testid={`orden-atenciones-${orden.id}`}>
    {(orden.atenciones || []).length === 0 && <p className="text-xs text-slate-400">Sin atenciones registradas.</p>}
    {(orden.atenciones || []).map((a) => (
      <div key={`${a.tipo}-${a.ref_id}`} className="flex items-center justify-between gap-2 text-xs text-slate-600">
        <span>
          {a.tipo === 'cirugia' ? `Cirugía · dosis ${a.numero_dosis}` : 'Evaluación'} · {fmt(a.fecha)}{a.medico ? ` · ${a.medico}` : ''}
          {a.excede_dosis && <span className="ml-1 text-red-600 font-medium">(excede dosis)</span>}
        </span>
        {orden.estado !== 'anulada' && (
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => onReasignar(orden, a)} data-testid={`reasignar-${a.ref_id}`}>
            <Shuffle className="w-3 h-3 mr-1" /> Reasignar
          </Button>
        )}
      </div>
    ))}
  </div>
);

const FilaOrden = ({ o, abierta, onToggle, onEditar, onAnular, onReasignar }) => {
  const [cls, label] = ESTADO[o.estado] || ESTADO.pendiente;
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-white" data-testid={`orden-libro-${o.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <button type="button" onClick={onToggle} className="flex items-start gap-2 text-left">
          {abierta ? <ChevronDown className="w-4 h-4 mt-0.5 text-slate-400" /> : <ChevronRight className="w-4 h-4 mt-0.5 text-slate-400" />}
          <div>
            <div className="text-sm font-semibold text-slate-800">
              <span className="font-mono" data-testid={`orden-sps-${o.id}`}>{o.no_sps}</span>
              <span className="text-slate-400 font-normal"> · </span>{o.etiqueta_nog}
            </div>
            <div className="text-xs text-slate-500">
              {o.modalidad || 'Sin modalidad'} · {o.tipo === 'procedimiento' ? 'Procedimiento' : 'Consulta'}
              {o.procedimiento ? ` · ${o.procedimiento}` : ''} · Ingreso {fmt(o.fecha_ingreso)}
            </div>
          </div>
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-700" data-testid={`orden-dosis-${o.id}`}>
            {o.tipo === 'procedimiento' ? `Dosis aplicadas ${o.dosis_aplicadas} de ${o.dosis_autorizadas}` : `${o.total_atenciones} atención(es)`}
          </span>
          <Badge variant="outline" className={cls} data-testid={`orden-estado-${o.id}`}>{label}</Badge>
          {o.estado !== 'anulada' && (
            <>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={onEditar} title="Editar" data-testid={`orden-editar-${o.id}`}><Pencil className="w-3.5 h-3.5" /></Button>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500" onClick={onAnular} title="Anular" data-testid={`orden-anular-${o.id}`}><Ban className="w-3.5 h-3.5" /></Button>
            </>
          )}
        </div>
      </div>
      {o.estado === 'anulada' && <p className="text-xs text-slate-500 mt-1">Anulada: {o.motivo_anulacion}</p>}
      {abierta && <Atenciones orden={o} onReasignar={onReasignar} />}
    </div>
  );
};

// Sección de órdenes IGSS de la ficha del paciente (solo LIBRO_IGSS_ROLES)
export const OrdenesIgssPaciente = ({ pacienteId, unidadId }) => {
  const [ordenes, setOrdenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [abiertas, setAbiertas] = useState({});
  const [editar, setEditar] = useState({ open: false, orden: null });
  const [anular, setAnular] = useState(null);
  const [reasignar, setReasignar] = useState(null);

  const cargar = useCallback(async () => {
    if (!pacienteId) return;
    setCargando(true);
    try {
      const { data } = await igssLibroApi.listar({ paciente_id: pacienteId, limit: 200 });
      setOrdenes(data?.data || []);
    } catch (e) {
      setOrdenes([]);
    } finally {
      setCargando(false);
    }
  }, [pacienteId]);

  useEffect(() => { cargar(); }, [cargar]);

  const confirmarReasignar = async (destino) => {
    await igssLibroApi.reasignar({ tipo: reasignar.atencion.tipo, ref_id: reasignar.atencion.ref_id, orden_destino_id: destino });
    toast.success(destino ? 'Atención reasignada' : 'Atención enviada a "atenciones sin orden"');
    cargar();
  };

  return (
    <div className="space-y-2" data-testid="ordenes-igss-libro">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-blue-700">Órdenes IGSS (libro)</span>
        <Button type="button" variant="outline" size="sm" onClick={() => setEditar({ open: true, orden: null })} className="h-7 text-xs text-emerald-700 border-emerald-200" data-testid="orden-libro-nueva">
          <Plus className="w-3 h-3 mr-1" /> Nueva orden
        </Button>
      </div>
      {cargando && <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Cargando…</p>}
      {!cargando && ordenes.length === 0 && (
        <p className="text-xs text-slate-500 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Sin órdenes en el libro.</p>
      )}
      {ordenes.map((o) => (
        <FilaOrden
          key={o.id} o={o} abierta={!!abiertas[o.id]}
          onToggle={() => setAbiertas((a) => ({ ...a, [o.id]: !a[o.id] }))}
          onEditar={() => setEditar({ open: true, orden: o })}
          onAnular={() => setAnular(o)}
          onReasignar={(orden, atencion) => setReasignar({ orden, atencion })}
        />
      ))}
      <OrdenLibroDialog
        open={editar.open} onOpenChange={(v) => setEditar((s) => ({ ...s, open: v }))}
        pacienteId={pacienteId} unidadId={unidadId} orden={editar.orden} onSaved={cargar}
      />
      <MotivoDialog
        open={!!anular} onOpenChange={(v) => !v && setAnular(null)} testId="anular-orden-dialog"
        titulo={`Anular orden ${anular?.no_sps || ''}`} descripcion="La orden no se borra: queda anulada con su motivo y libera el cupo."
        accion="Anular" onConfirm={async (motivo) => { await igssLibroApi.anular(anular.id, motivo); toast.success('Orden anulada'); cargar(); }}
      />
      <ElegirOrdenDialog
        open={!!reasignar} onOpenChange={(v) => !v && setReasignar(null)} pacienteId={pacienteId}
        excluirId={reasignar?.orden?.id} permitirSinOrden titulo="Reasignar atención" onConfirm={confirmarReasignar}
      />
    </div>
  );
};
