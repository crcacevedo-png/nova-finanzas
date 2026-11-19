import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Plus, Pencil, Ban, ChevronDown, ChevronRight, Shuffle, Loader2, AlertTriangle, CircleSlash, ClipboardCheck, FileCheck2 } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi, formatDateTime } from '../../services/api';
import { OrdenLibroDialog } from './OrdenLibroDialog';
import { MotivoDialog, ElegirOrdenDialog } from './OrdenDialogs';
import { ESTADOS_ACTIVOS, estadoOrden } from './estadosLibro';
import { ConfirmarDosisDialog } from './ConfirmarDosisDialog';
import { ConfirmarSpsDialog } from './ConfirmarSpsDialog';
import { ConstanciasOrden } from './ConstanciasOrden';
import { useAuth } from '../../context/AuthContext';
import { puedeVerLibroIgss } from '../../lib/igssLibro';

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');
const fmtHora = (f) => (f ? formatDateTime(f) : '—');

const Atenciones = ({ orden, onReasignar }) => (
  <div className="mt-2 border-t border-slate-100 pt-2 space-y-1" data-testid={`orden-atenciones-${orden.id}`}>
    {(orden.atenciones || []).length === 0 && <p className="text-xs text-slate-400">Sin atenciones registradas.</p>}
    {(orden.atenciones || []).map((a) => (
      <div key={`${a.tipo}-${a.ref_id}`} className="flex items-center justify-between gap-2 text-xs text-slate-600">
        <span>
          {a.tipo === 'cirugia' ? `Cirugía · dosis ${a.numero_dosis}` : 'Evaluación'} · {fmt(a.fecha)}{a.medico ? ` · ${a.medico}` : ''}
          {a.excede_dosis && <span className="ml-1 text-red-600 font-medium">(excede dosis)</span>}
        </span>
        {onReasignar && ESTADOS_ACTIVOS.includes(orden.estado) && (
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

// Acciones de administración (solo roles del libro)
const AccionesLibro = ({ o, onEditar, onAnular, onCerrar, onConfirmar, onConfirmarSps }) => (
  <>
    {o.sps_por_revisar && o.estado !== 'anulada' && (
      <Button variant="outline" size="sm" className="h-7 px-2 text-xs text-amber-700 border-amber-300" type="button" onClick={onConfirmarSps} data-testid={`orden-confirmar-sps-${o.id}`}>
        <FileCheck2 className="w-3.5 h-3.5 mr-1" /> Confirmar SPS
      </Button>
    )}
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
  </>
);

const FilaOrden = ({ o, esLibro, abierta, onToggle, onEditar, onAnular, onCerrar, onConfirmar, onConfirmarSps, onReasignar }) => {
  const [cls, label] = estadoOrden(o.estado);
  return (
    <div className="border border-slate-200 rounded-lg p-3 bg-white" data-testid={`orden-libro-${o.id}`}>
      <div className="flex flex-col gap-2">
        <button type="button" onClick={onToggle} className="flex items-start gap-2 text-left min-w-0">
          {abierta ? <ChevronDown className="w-4 h-4 mt-0.5 text-slate-400" /> : <ChevronRight className="w-4 h-4 mt-0.5 text-slate-400" />}
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-800 flex flex-wrap items-baseline gap-x-2">
              <span className="font-mono break-all" data-testid={`orden-sps-${o.id}`}>{o.no_sps}</span>
              <span className="text-slate-600 font-normal">{o.etiqueta_nog}</span>
              <span className="whitespace-nowrap font-mono text-xs font-medium text-slate-600 bg-slate-100 rounded px-1.5" data-testid={`orden-numero-${o.id}`}>{o.numero_libro}</span>
              {o.sps_por_revisar && <Badge variant="outline" className="h-5 px-1.5 text-[10px] bg-amber-50 text-amber-700 border-amber-300 whitespace-nowrap" data-testid={`orden-revisar-sps-${o.id}`}>Revisar SPS</Badge>}
            </div>
            <div className="text-xs text-slate-500">
              {o.modalidad || 'Sin modalidad'} · {o.tipo === 'procedimiento' ? 'Procedimiento' : 'Consulta'}
              {o.inyectable && <Badge variant="outline" className="ml-1 h-4 px-1 text-[10px] bg-sky-50 text-sky-700 border-sky-200" data-testid={`orden-inyectable-${o.id}`}>Inyectable</Badge>}
              {o.procedimiento ? ` · ${o.procedimiento}` : ''} · Ingreso {fmt(o.fecha_ingreso)}
            </div>
            <div className="text-[11px] text-slate-400" data-testid={`orden-ingresada-por-${o.id}`}>
              Ingresada por {o.created_by_nombre || '—'} · {fmtHora(o.created_at)}
              {o.sps_confirmado_en && (
                <span className="text-emerald-700" data-testid={`orden-sps-confirmado-${o.id}`}>
                  {' '}· No. SPS confirmado por {o.sps_confirmado_por_nombre || '—'} · {fmtHora(o.sps_confirmado_en)}
                </span>
              )}
            </div>
          </div>
        </button>
        <div className="flex flex-wrap items-center gap-2 pl-6">
          <span className="text-xs font-medium text-slate-700 whitespace-nowrap" data-testid={`orden-dosis-${o.id}`}>
            {o.tipo === 'procedimiento' ? `Dosis aplicadas ${o.dosis_aplicadas} de ${o.dosis_autorizadas}` : `${o.total_atenciones} atención(es)`}
            {(o.constancias || []).length > 0 && <span className="font-normal text-slate-500"> · {o.constancias.length} constancia(s)</span>}
          </span>
          <Badge variant="outline" className={cls} data-testid={`orden-estado-${o.id}`}>{label}</Badge>
          {esLibro
            ? <AccionesLibro o={o} onEditar={onEditar} onAnular={onAnular} onCerrar={onCerrar} onConfirmar={onConfirmar} onConfirmarSps={onConfirmarSps} />
            : o.puede_corregir && (
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" type="button" onClick={onEditar} title="Corregir" data-testid={`orden-editar-${o.id}`}><Pencil className="w-3.5 h-3.5" /></Button>
            )}
        </div>
      </div>
      {o.estado === 'anulada' && <p className="text-xs text-slate-500 mt-1">Anulada: {o.motivo_anulacion}</p>}
      {o.dosis_por_confirmar && ESTADOS_ACTIVOS.includes(o.estado) && (
        <p className="text-xs text-amber-700 mt-1" data-testid={`orden-falta-confirmar-${o.id}`}>Falta confirmar las dosis con la hoja: no llega a completa ni se cobra hasta confirmarlas.</p>
      )}
      {o.sps_por_revisar && o.estado !== 'anulada' && (
        <p className="text-xs text-amber-700 mt-1" data-testid={`orden-falta-confirmar-sps-${o.id}`}>
          {o.estado === 'historica'
            ? 'No. SPS con forma poco común: confirmarlo con la hoja es solo informativo (orden histórica).'
            : 'No. SPS con forma poco común: no se puede marcar facturada hasta que un rol del libro lo confirme con la hoja.'}
        </p>
      )}
      {o.estado === 'cerrada' && <p className="text-xs text-orange-700 mt-1" data-testid={`orden-cerrada-motivo-${o.id}`}>Cerrada sin completar (no se cobra): {o.motivo_cierre}</p>}
      {abierta && <Atenciones orden={o} onReasignar={esLibro ? onReasignar : null} />}
      {abierta && <ConstanciasOrden orden={o} />}
    </div>
  );
};

// Sección de órdenes IGSS de la ficha del paciente (roles que ingresan órdenes; administración solo en el libro)
export const OrdenesIgssPaciente = ({ pacienteId, unidadId }) => {
  const { user } = useAuth();
  const esLibro = puedeVerLibroIgss(user);
  const [ordenes, setOrdenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [abiertas, setAbiertas] = useState({});
  const [editar, setEditar] = useState({ open: false, orden: null });
  const [anular, setAnular] = useState(null);
  const [cerrar, setCerrar] = useState(null);
  const [confirmar, setConfirmar] = useState(null);
  const [confirmarSps, setConfirmarSps] = useState(null);
  const [reasignar, setReasignar] = useState(null);

  const cargar = useCallback(async () => {
    if (!pacienteId) return;
    setCargando(true);
    try {
      const { data } = await igssLibroApi.delPaciente(pacienteId);
      setOrdenes(data || []);
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
          key={o.id} o={o} esLibro={esLibro} abierta={!!abiertas[o.id]}
          onToggle={() => setAbiertas((a) => ({ ...a, [o.id]: !a[o.id] }))}
          onEditar={() => setEditar({ open: true, orden: o })}
          onAnular={() => setAnular(o)}
          onCerrar={() => setCerrar(o)}
          onConfirmar={() => setConfirmar(o)}
          onConfirmarSps={() => setConfirmarSps(o)}
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
      {esLibro && <ConfirmarSpsDialog orden={confirmarSps} onClose={() => setConfirmarSps(null)} onSaved={cargar} />}
      <ElegirOrdenDialog
        open={!!reasignar} onOpenChange={(v) => !v && setReasignar(null)} pacienteId={pacienteId}
        excluirId={reasignar?.orden?.id} permitirSinOrden titulo="Reasignar atención" onConfirm={confirmarReasignar}
      />
    </div>
  );
};
