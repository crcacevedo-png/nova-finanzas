import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Plus, Pencil, Ban, ChevronDown, ChevronRight, Shuffle, Loader2, AlertTriangle, CircleSlash, ClipboardCheck } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi } from '../../services/api';
import { OrdenLibroDialog } from './OrdenLibroDialog';
import { MotivoDialog, ElegirOrdenDialog } from './OrdenDialogs';
import { ESTADOS_ACTIVOS, estadoOrden } from './estadosLibro';
import { ConfirmarDosisDialog } from './ConfirmarDosisDialog';

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
        {ESTADOS_ACTIVOS.includes(orden.estado) && (
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" type="button" onClick={() => onReasignar(orden, a)} data-testid={`reasignar-${a.ref_id}`}>
            <Shuffle className="w-3 h-3 mr-1" /> Reasignar
          </Button>
        )}
      </div>
    ))}
    {(orden.cirugias_programadas || []).map((p) => (
      <div key={`prog-${p.ref_id}`} className="text-xs text-sky-700" data-testid={`orden-programada-${p.ref_id}`}>
        Cirugía programada · {fmt(p.fecha)} (aún no realizada)
      </div>
    ))}
  </div>
);

const FilaOrden = ({ o, abierta, onToggle, onEditar, onAnular, onCerrar, onConfirmar, onReasignar }) => {
  const [cls, label] = estadoOrden(o.estado);
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-white" data-testid={`orden-libro-${o.id}`}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
        <button type="button" onClick={onToggle} className="flex items-start gap-2 text-left min-w-0 sm:flex-1">
          {abierta ? <ChevronDown className="w-4 h-4 mt-0.5 text-slate-400" /> : <ChevronRight className="w-4 h-4 mt-0.5 text-slate-400" />}
          <div>
            <div className="text-sm font-semibold text-slate-800">
              <span className="font-mono" data-testid={`orden-sps-${o.id}`}>{o.no_sps}</span>
              <span className="text-slate-400 font-normal"> · </span>{o.etiqueta_nog}
              <span className="ml-2 font-mono text-[11px] font-normal text-slate-400" data-testid={`orden-numero-${o.id}`}>{o.numero_libro}</span>
            </div>
            <div className="text-xs text-slate-500">
              {o.modalidad || 'Sin modalidad'} · {o.tipo === 'procedimiento' ? 'Procedimiento' : 'Consulta'}
              {o.inyectable && <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px] bg-sky-50 text-sky-700 border-sky-200" data-testid={`orden-inyectable-${o.id}`}>Inyectable</Badge>}
              {o.procedimiento ? ` · ${o.procedimiento}` : ''} · Ingreso {fmt(o.fecha_ingreso)}
            </div>
          </div>
        </button>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-medium text-slate-700 whitespace-nowrap" data-testid={`orden-dosis-${o.id}`}>
            {o.tipo === 'procedimiento' ? `Dosis aplicadas ${o.dosis_aplicadas} de ${o.dosis_autorizadas}` : `${o.total_atenciones} atención(es)`}
          </span>
          <Badge variant="outline" className={cls} data-testid={`orden-estado-${o.id}`}>{label}</Badge>
          {o.dosis_por_confirmar && ESTADOS_ACTIVOS.includes(o.estado) && (
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs text-amber-700 border-amber-300" type="button" onClick={onConfirmar} data-testid={`orden-confirmar-dosis-${o.id}`}>
              <ClipboardCheck className="w-3.5 h-3.5 mr-1" /> Confirmar dosis
            </Button>
          )}
          {o.estado !== 'anulada' && (
            <>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" type="button" onClick={onEditar} title="Editar" data-testid={`orden-editar-${o.id}`}><Pencil className="w-3.5 h-3.5" /></Button>
              {o.estado === 'en_curso' && (
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-orange-600" type="button" onClick={onCerrar} title="Cerrar sin completar" data-testid={`orden-cerrar-${o.id}`}><CircleSlash className="w-3.5 h-3.5" /></Button>
              )}
              {o.estado !== 'cerrada' && (
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500" type="button" onClick={onAnular} title="Anular" data-testid={`orden-anular-${o.id}`}><Ban className="w-3.5 h-3.5" /></Button>
              )}
            </>
          )}
        </div>
      </div>
      {o.estado === 'anulada' && <p className="text-xs text-slate-500 mt-1">Anulada: {o.motivo_anulacion}</p>}
      {o.dosis_por_confirmar && ESTADOS_ACTIVOS.includes(o.estado) && (
        <p className="text-xs text-amber-700 mt-1" data-testid={`orden-falta-confirmar-${o.id}`}>Falta confirmar las dosis con la hoja: no llega a completa ni se cobra hasta confirmarlas.</p>
      )}
      {o.estado === 'cerrada' && <p className="text-xs text-orange-700 mt-1" data-testid={`orden-cerrada-motivo-${o.id}`}>Cerrada sin completar (no se cobra): {o.motivo_cierre}</p>}
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
  const [cerrar, setCerrar] = useState(null);
  const [confirmar, setConfirmar] = useState(null);
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
          onCerrar={() => setCerrar(o)}
          onConfirmar={() => setConfirmar(o)}
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
      <MotivoDialog
        open={!!cerrar} onOpenChange={(v) => !v && setCerrar(null)} testId="cerrar-orden-dialog"
        titulo={`Cerrar sin completar ${cerrar?.no_sps || ''}`}
        descripcion="Para tratamientos suspendidos (el paciente mejora, no regresa o fallece). La orden deja de admitir dosis, libera su cupo y NO se cobra. Queda en auditoría."
        accion="Cerrar sin completar" onConfirm={async (motivo) => { await igssLibroApi.cerrar(cerrar.id, motivo); toast.success('Orden cerrada sin completar'); cargar(); }}
      />
      <ConfirmarDosisDialog orden={confirmar} onOpenChange={(v) => !v && setConfirmar(null)} onSaved={cargar} />
      <ElegirOrdenDialog
        open={!!reasignar} onOpenChange={(v) => !v && setReasignar(null)} pacienteId={pacienteId}
        excluirId={reasignar?.orden?.id} permitirSinOrden titulo="Reasignar atención" onConfirm={confirmarReasignar}
      />
    </div>
  );
};
