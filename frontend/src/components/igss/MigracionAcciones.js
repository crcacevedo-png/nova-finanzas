import React, { useCallback, useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { toast } from 'sonner';
import { CheckCircle2, DatabaseZap, Loader2, OctagonAlert, ShieldCheck, ShieldAlert, Undo2 } from 'lucide-react';
import { igssLibroApi, formatDateTime } from '../../services/api';

// Fase 4, paso (b): aplicar la migración revisada y deshacer un lote. Solo superadmin (también en el servidor).
const PALABRA_APLICAR = 'MIGRAR';
const PALABRA_DESHACER = 'DESHACER';
const n = (v) => Number(v || 0).toLocaleString('es-GT');
const mensaje = (e, fb) => {
  const d = e?.response?.data?.detail;
  return typeof d === 'string' ? d : d?.mensaje || fb;
};

const useRestanteMs = (vence) => {
  const calc = useCallback(() => (vence ? new Date(vence).getTime() - Date.now() : 0), [vence]);
  const [ms, setMs] = useState(calc);
  useEffect(() => {
    setMs(calc());
    const t = setInterval(() => setMs(calc()), 10000);
    return () => clearInterval(t);
  }, [calc]);
  return ms;
};

export const CifrasLote = ({ cifras, testId }) => (
  <div className="rounded-lg border border-slate-200 divide-y divide-slate-100 bg-white" data-testid={testId}>
    {cifras.map((c) => (
      <div key={c.clave} className="flex justify-between gap-3 px-3 py-1.5 text-sm" data-testid={`${testId}-${c.clave}`}>
        <span className={c.concepto.startsWith(' ') ? 'pl-4 text-slate-500' : 'text-slate-700'}>{c.concepto.trim()}</span>
        <span className="font-semibold tabular-nums">{n(c.valor)}</span>
      </div>
    ))}
  </div>
);

// Diálogo que exige escribir una palabra exacta; el botón se bloquea mientras corre (sin doble envío)
const PalabraDialog = ({ open, onOpenChange, titulo, descripcion, palabra, accion, onConfirmar, children, testId, peligro }) => {
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { if (open) setTexto(''); }, [open]);
  const confirmar = async () => {
    if (enviando) return;
    setEnviando(true);
    try { await onConfirmar(texto.trim()); } finally { setEnviando(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !enviando && onOpenChange(v)}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto" data-testid={testId}>
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>{descripcion}</DialogDescription>
        </DialogHeader>
        {children}
        {palabra && (
          <div className="space-y-1">
            <p className="text-sm text-slate-700">Escriba <b className="font-mono">{palabra}</b> para confirmar</p>
            <Input value={texto} onChange={(e) => setTexto(e.target.value)} autoComplete="off" className="font-mono" data-testid={`${testId}-palabra`} />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={enviando} data-testid={`${testId}-cancelar`}>
            {palabra ? 'Cancelar' : 'Cerrar'}
          </Button>
          {palabra && (
            <Button onClick={confirmar} disabled={texto.trim() !== palabra || enviando} data-testid={`${testId}-confirmar`}
              className={peligro ? 'bg-red-600 hover:bg-red-700' : 'bg-teal-600 hover:bg-teal-700'}>
              {enviando && <Loader2 className="w-4 h-4 mr-1 animate-spin" />} {accion}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const EstadoRespaldo = ({ respaldo }) => (
  <p className={`flex items-center gap-1.5 text-xs ${respaldo?.vigente ? 'text-emerald-700' : 'text-red-600'}`} data-testid="mig-respaldo">
    {respaldo?.vigente ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
    {respaldo?.completed_at
      ? `Último respaldo: ${formatDateTime(respaldo.completed_at)} (hace ${n(respaldo.horas)} h)${respaldo.vigente ? '' : ' — se necesita uno de menos de 24 h para aplicar'}`
      : 'No hay ningún respaldo completado: se necesita uno de menos de 24 h para aplicar'}
  </p>
);

export const AplicarMigracion = ({ sim, onAplicada, onCaducada }) => {
  const restante = useRestanteMs(sim?.vence);
  const [abierto, setAbierto] = useState(false);
  const razones = [];
  if (!sim?.token_aplicar) razones.push('Simule con «Todas las unidades» para poder aplicar.');
  else if (restante <= 0) razones.push('La simulación tiene más de 30 minutos: simule de nuevo.');
  if (!sim?.aplicacion_permitida) razones.push('Hay bloqueos: la aplicación se negaría.');
  if (!sim?.respaldo?.vigente) razones.push('Falta un respaldo de menos de 24 horas.');

  const aplicar = async (palabra) => {
    try {
      const { data } = await igssLibroApi.aplicarMigracion(sim.token_aplicar, palabra);
      setAbierto(false);
      toast.success(`Migración aplicada: ${n(data.ordenes)} órdenes y ${n(data.ajustes)} cupos sin SPS`);
      onAplicada(data);
    } catch (e) {
      toast.error(mensaje(e, 'No se pudo aplicar la migración'), { duration: 10000 });
      if (e?.response?.status === 409) { setAbierto(false); onCaducada(); }
    }
  };

  return (
    <div className="rounded-xl border border-teal-200 bg-white p-4 space-y-2" data-testid="mig-aplicar">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-800 flex items-center gap-2"><DatabaseZap className="w-5 h-5 text-teal-700" /> Aplicar la migración</p>
          <p className="text-xs text-slate-500 max-w-xl">Crea en el libro exactamente lo de esta simulación. Solo si se corrió hace menos de 30 minutos y nada cambió desde entonces.</p>
        </div>
        <Button onClick={() => setAbierto(true)} disabled={razones.length > 0} className="bg-teal-700 hover:bg-teal-800" data-testid="mig-aplicar-btn">
          <DatabaseZap className="w-4 h-4 mr-1" /> Aplicar migración
        </Button>
      </div>
      {sim?.token_aplicar && restante > 0 && (
        <p className="text-xs text-slate-500" data-testid="mig-vence">Esta simulación vale {Math.ceil(restante / 60000)} min más.</p>
      )}
      {razones.map((r) => <p key={r} className="text-xs text-red-600" data-testid="mig-aplicar-razon">{r}</p>)}
      <PalabraDialog
        open={abierto} onOpenChange={setAbierto} testId="mig-aplicar-dialog" palabra={PALABRA_APLICAR} accion="Aplicar migración"
        titulo="¿Aplicar la migración al libro?"
        descripcion="Estas son las cifras de la simulación que revisó. Se aplicarán exactamente ellas; si algún dato cambió, el sistema pedirá simular de nuevo."
        onConfirmar={aplicar}
      >
        <CifrasLote cifras={sim?.cifras_lote || []} testId="mig-confirmar" />
      </PalabraDialog>
    </div>
  );
};

export const ComparacionLote = ({ resultado }) => (
  <div className="rounded-xl border border-slate-200 bg-white overflow-hidden" data-testid="mig-comparacion">
    <div className={`px-4 py-3 text-sm font-semibold flex items-center gap-2 ${resultado.diferencias.length ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'}`}>
      {resultado.diferencias.length ? <OctagonAlert className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
      {resultado.diferencias.length
        ? `${resultado.diferencias.length} cifra(s) aplicada(s) distinta(s) a la simulación (en rojo)`
        : 'Las cifras aplicadas coinciden con la simulación'}
      <span className="ml-auto font-mono text-xs font-normal">lote {resultado.lote_id.slice(0, 8)}</span>
    </div>
    <table className="w-full text-sm">
      <thead className="bg-slate-50 text-xs uppercase text-slate-500">
        <tr><th className="px-3 py-2 text-left">Concepto</th><th className="px-3 py-2 text-right">Simulado</th><th className="px-3 py-2 text-right">Aplicado</th></tr>
      </thead>
      <tbody>
        {resultado.comparacion.map((c) => (
          <tr key={c.clave} className={`border-t border-slate-100 ${c.igual ? '' : 'bg-red-50 text-red-700 font-semibold'}`} data-testid={`mig-comp-${c.clave}`} data-igual={c.igual ? 'si' : 'no'}>
            <td className={`px-3 py-1.5 ${c.concepto.startsWith(' ') ? 'pl-7' : ''}`}>{c.concepto.trim()}</td>
            <td className="px-3 py-1.5 text-right tabular-nums">{n(c.simulado)}</td>
            <td className="px-3 py-1.5 text-right tabular-nums">{n(c.aplicado)}</td>
          </tr>
        ))}
      </tbody>
    </table>
    {resultado.omitidas?.length > 0 && (
      <div className="px-4 py-2 text-xs text-red-700 border-t border-red-100" data-testid="mig-omitidas">
        No se crearon: {resultado.omitidas.map((o) => `${o.no_sps} (${o.paciente_nombre}: ${o.motivo})`).join(' · ')}
      </div>
    )}
  </div>
);

const Cambios = ({ cambios }) => (
  <ul className="max-h-72 overflow-y-auto space-y-2 text-sm" data-testid="mig-deshacer-cambios">
    {cambios.map((c) => (
      <li key={c.id} className="rounded-lg border border-red-200 bg-red-50 p-2" data-testid={`mig-deshacer-cambio-${c.id}`}>
        <p className="font-medium text-red-800">
          <span className="font-mono whitespace-nowrap">{c.numero_libro || 'Cupo sin SPS'}</span> {c.no_sps && <span className="font-mono">· {c.no_sps}</span>} · {c.paciente_nombre || '—'} <span className="text-xs font-normal">({c.estado})</span>
        </p>
        <p className="text-xs text-red-700">Cambió: {c.que_cambio.join(', ')}</p>
        {c.registros.map((r, i) => (
          <p key={i} className="text-xs text-slate-600">{r.accion} · {r.quien} · {r.cuando ? formatDateTime(r.cuando) : '—'}</p>
        ))}
      </li>
    ))}
  </ul>
);

const ESTADO_LOTE = {
  aplicado: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  incompleto: 'bg-amber-50 text-amber-700 border-amber-200',
  deshecho: 'bg-slate-100 text-slate-500 border-slate-200',
  aplicando: 'bg-sky-50 text-sky-700 border-sky-200',
};

export const LotesMigracion = ({ version, onDeshecho }) => {
  const [lotes, setLotes] = useState([]);
  const [revision, setRevision] = useState(null);
  const [revisando, setRevisando] = useState('');

  const cargar = useCallback(async () => {
    try { setLotes((await igssLibroApi.lotesMigracion()).data?.data || []); } catch (e) { setLotes([]); }
  }, []);
  useEffect(() => { cargar(); }, [cargar, version]);

  const revisar = async (lote) => {
    setRevisando(lote.id);
    try { setRevision((await igssLibroApi.simularDeshacer(lote.id)).data); } catch (e) { toast.error(mensaje(e, 'No se pudo revisar el lote')); } finally { setRevisando(''); }
  };

  const deshacer = async (palabra) => {
    try {
      const { data } = await igssLibroApi.deshacerMigracion(revision.token_deshacer, palabra);
      toast.success(`Lote deshecho: ${n(data.ordenes_borradas)} órdenes y ${n(data.ajustes_borrados)} cupos sin SPS borrados`);
      setRevision(null);
      cargar();
      onDeshecho?.();
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(mensaje(e, 'No se pudo deshacer'), { duration: 10000 });
      if (d?.cambios?.length) setRevision((r) => ({ ...r, puede_deshacer: false, motivo: d.mensaje, cambios: d.cambios }));
      else setRevision(null);
    }
  };

  if (!lotes.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto" data-testid="mig-lotes">
      <p className="px-4 py-2 text-sm font-semibold text-slate-700 border-b border-slate-100">Lotes de migración aplicados</p>
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr><th className="px-3 py-2 text-left">Fecha</th><th className="px-3 py-2 text-left">Por</th><th className="px-3 py-2 text-left">Estado</th><th className="px-3 py-2 text-right">Órdenes</th><th className="px-3 py-2 text-right">Cupos sin SPS</th><th className="px-3 py-2" /></tr>
        </thead>
        <tbody>
          {lotes.map((l) => (
            <tr key={l.id} className="border-t border-slate-100" data-testid={`mig-lote-${l.id}`}>
              <td className="px-3 py-2 whitespace-nowrap">{formatDateTime(l.creado_en)}</td>
              <td className="px-3 py-2">{l.creado_por_nombre}</td>
              <td className="px-3 py-2"><Badge variant="outline" className={ESTADO_LOTE[l.estado] || ''} data-testid={`mig-lote-estado-${l.id}`}>{l.estado}</Badge></td>
              <td className="px-3 py-2 text-right tabular-nums">{n(l.ordenes)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{n(l.ajustes)}</td>
              <td className="px-3 py-2 text-right">
                {['aplicado', 'incompleto'].includes(l.estado) && (
                  <Button size="sm" variant="outline" className="h-7 text-xs text-red-700 border-red-200" onClick={() => revisar(l)} disabled={!!revisando} data-testid={`mig-deshacer-btn-${l.id}`}>
                    {revisando === l.id ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Undo2 className="w-3 h-3 mr-1" />} Deshacer…
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <PalabraDialog
        open={!!revision} onOpenChange={(v) => !v && setRevision(null)} testId="mig-deshacer-dialog" peligro
        palabra={revision?.puede_deshacer ? PALABRA_DESHACER : null} accion="Deshacer lote"
        titulo={revision?.puede_deshacer ? '¿Deshacer este lote de migración?' : 'Este lote no se puede deshacer'}
        descripcion={revision?.puede_deshacer
          ? `Se borrarán ${n(revision.ordenes)} órdenes y ${n(revision.ajustes)} cupos sin SPS creados por la migración, y sus cupos vuelven a quedar libres. No toca el sistema anterior.`
          : revision?.motivo}
        onConfirmar={deshacer}
      >
        {revision && !revision.puede_deshacer && revision.cambios?.length > 0 && <Cambios cambios={revision.cambios} />}
      </PalabraDialog>
    </div>
  );
};
