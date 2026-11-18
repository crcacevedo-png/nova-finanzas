import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { toast } from 'sonner';
import { Loader2, CheckCircle2, Users, ShieldCheck, ChevronDown, ChevronRight, RotateCcw } from 'lucide-react';
import { backupApi, formatDateTime } from '../../services/api';

const PALABRA = 'RESTAURAR';
const PASOS = [
  ['respaldo_previo', 'Respaldo previo del estado actual (obligatorio)'],
  ['lectura', 'Lectura del respaldo elegido'],
  ['preparacion', 'Preparación de la copia (todavía sin tocar los datos)'],
  ['reemplazo', 'Reemplazo de los datos'],
];
const n = (x) => Number(x || 0).toLocaleString('es-GT');
const slug = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, '-');
const detalle = (e, txt) => { const d = e?.response?.data?.detail; return typeof d === 'string' ? d : txt; };

const useSeguir = (tarea, setTarea) => {
  useEffect(() => {
    if (!tarea || tarea.estado !== 'en_curso') return undefined;
    const t = setTimeout(async () => {
      try { setTarea((await backupApi.tarea(tarea.id)).data); } catch { setTarea({ ...tarea }); }
    }, 2000);
    return () => clearTimeout(t);
  }, [tarea, setTarea]);
};

const Grupo = ({ g }) => (
  <div className="rounded-lg border border-slate-200 p-3" data-testid={`rest-grupo-${slug(g.nombre)}`}>
    <div className="text-xs font-semibold text-slate-800">{g.nombre}</div>
    <div className="mt-1 text-[11px] leading-5 text-slate-600">
      <div><b className="text-red-700" data-testid={`rest-creados-${slug(g.nombre)}`}>{n(g.creados)}</b> nuevos se borran</div>
      <div><b className="text-amber-700" data-testid={`rest-cambiados-${slug(g.nombre)}`}>{n(g.cambiados)}</b> cambiados vuelven atrás</div>
      <div><b className="text-sky-700" data-testid={`rest-borrados-${slug(g.nombre)}`}>{n(g.borrados)}</b> borrados reaparecen</div>
    </div>
  </div>
);

const TodasLasColecciones = ({ res }) => {
  const [abierto, setAbierto] = useState(false);
  return (
    <div className="rounded-lg border border-slate-200">
      <button type="button" onClick={() => setAbierto(!abierto)} className="w-full flex items-center gap-1 px-3 py-2 text-xs font-medium text-slate-700" data-testid="rest-todas-toggle">
        {abierto ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        Todos los módulos: {res.colecciones.length} con diferencias, {res.colecciones_sin_cambios} sin cambios
      </button>
      {abierto && (
        <table className="w-full text-xs" data-testid="rest-todas-tabla">
          <thead className="bg-slate-50 text-slate-500"><tr>
            <th className="px-3 py-1 text-left">Módulo</th><th className="px-2 py-1 text-right">Nuevos</th>
            <th className="px-2 py-1 text-right">Cambiados</th><th className="px-2 py-1 text-right">Borrados</th>
          </tr></thead>
          <tbody>
            {res.colecciones.map((c) => (
              <tr key={c.coleccion} className="border-t border-slate-100" data-testid={`rest-col-${c.coleccion}`}>
                <td className="px-3 py-1">{c.nombre}{c.nombre !== c.coleccion && <span className="text-slate-400"> · {c.coleccion}</span>}</td>
                <td className="px-2 py-1 text-right">{n(c.creados)}</td><td className="px-2 py-1 text-right">{n(c.cambiados)}</td>
                <td className="px-2 py-1 text-right">{n(c.borrados)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

const Sesiones = ({ sesiones }) => (sesiones.length === 0 ? (
  <p className="text-xs text-emerald-700 flex items-center gap-1" data-testid="rest-sin-sesiones">
    <ShieldCheck className="w-4 h-4" /> No hay otros usuarios con sesión abierta (actividad en los últimos 30 minutos).
  </p>
) : (
  <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900" data-testid="rest-sesiones">
    <div className="font-semibold flex items-center gap-1">
      <Users className="w-4 h-4" /> {sesiones.length} usuario(s) con sesión abierta (actividad en los últimos 30 minutos). Pídales que cierren sesión:
    </div>
    <ul className="mt-1 list-disc pl-5">
      {sesiones.map((s) => (
        <li key={s.user_id} data-testid={`rest-sesion-${s.usuario}`}>{s.nombre} ({s.rol}) · última actividad {formatDateTime(s.ultima_actividad)}</li>
      ))}
    </ul>
  </div>
));

const Revision = ({ res, palabra, setPalabra }) => (
  <div className="space-y-3" data-testid="rest-revision">
    <p className="text-sm font-medium text-slate-800">Lo que se pierde o vuelve atrás si restaura este respaldo:</p>
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{res.grupos.map((g) => <Grupo key={g.nombre} g={g} />)}</div>
    <p className="text-xs text-slate-600" data-testid="rest-total">
      En total: {n(res.total.creados)} registros nuevos se borran, {n(res.total.cambiados)} cambiados vuelven atrás y {n(res.total.borrados)} borrados reaparecen.
    </p>
    <TodasLasColecciones res={res} />
    <Sesiones sesiones={res.sesiones} />
    <ul className="text-xs text-slate-600 list-disc pl-5 space-y-0.5">
      <li>Antes de reemplazar nada se hace un respaldo automático del estado actual. Si ese respaldo falla, no se restaura nada.</li>
      <li>No se tocan: el registro de auditoría, la lista de respaldos y las sesiones ya cerradas.</li>
      <li>Esta revisión vale hasta las <b data-testid="rest-vence">{formatDateTime(res.vence)}</b>.</li>
    </ul>
    <div>
      <label className="text-xs text-slate-700" htmlFor="rest-palabra">Escriba <b>{PALABRA}</b> para confirmar</label>
      <Input id="rest-palabra" value={palabra} onChange={(e) => setPalabra(e.target.value)} className="mt-1 max-w-xs" autoComplete="off" data-testid="rest-palabra" />
    </div>
  </div>
);

const Progreso = ({ tarea }) => {
  const hechos = Object.fromEntries((tarea.pasos || []).map((p) => [p.paso, p]));
  return (
    <ol className="space-y-2" data-testid="rest-progreso">
      {PASOS.map(([k, label]) => {
        const p = hechos[k];
        return (
          <li key={k} className="flex items-center gap-2 text-sm" data-testid={`rest-paso-${k}`}>
            {p ? <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              : tarea.paso_actual === k ? <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
                : <span className="w-4 h-4 rounded-full border border-slate-300" />}
            <span className={p ? 'text-slate-800' : 'text-slate-500'}>{label}</span>
            {p && <span className="ml-auto text-xs text-slate-500" data-testid={`rest-paso-seg-${k}`}>{p.segundos} s</span>}
          </li>
        );
      })}
    </ol>
  );
};

const Resultado = ({ tarea }) => (tarea.estado === 'listo' ? (
  <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800" data-testid="rest-resultado-ok">
    Restauración terminada en {tarea.segundos} s. Los datos volvieron al {formatDateTime(tarea.respaldo?.created_at)}.
    Respaldo previo guardado: <b>{tarea.respaldo_previo_archivo}</b>.
  </div>
) : (
  <div className={`rounded-lg border p-3 text-sm ${tarea.parcial ? 'border-red-300 bg-red-50 text-red-800' : 'border-amber-300 bg-amber-50 text-amber-900'}`}
    data-testid={tarea.parcial ? 'rest-resultado-parcial' : 'rest-resultado-cancelada'}>
    {tarea.error}
  </div>
));

export const RestaurarRespaldoDialog = ({ respaldo, onClose, onTerminado }) => {
  const [rev, setRev] = useState(null);
  const [rest, setRest] = useState(null);
  const [palabra, setPalabra] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  useSeguir(rev, setRev);
  useSeguir(rest, setRest);

  useEffect(() => {
    setRev(null); setRest(null); setPalabra(''); setError('');
    if (!respaldo) return;
    backupApi.revisarRestauracion(respaldo.id).then((r) => setRev(r.data)).catch((e) => setError(detalle(e, 'No se pudo revisar el respaldo')));
  }, [respaldo]);

  const terminado = !!rest && rest.estado !== 'en_curso';
  useEffect(() => { if (terminado) onTerminado(); }, [terminado, onTerminado]);

  const restaurar = async () => {
    setEnviando(true);
    try {
      setRest((await backupApi.restaurar(rev.id, palabra)).data);
    } catch (e) {
      toast.error(detalle(e, 'No se pudo iniciar la restauración'));
    } finally {
      setEnviando(false);
    }
  };
  const enCurso = enviando || rest?.estado === 'en_curso';

  return (
    <Dialog open={!!respaldo} onOpenChange={(v) => !v && !enCurso && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="restaurar-dialog">
        <DialogHeader>
          <DialogTitle>Restaurar respaldo</DialogTitle>
          <DialogDescription>
            Respaldo del <b data-testid="rest-fecha">{formatDateTime(respaldo?.created_at)}</b> (hora de Guatemala) · {respaldo?.filename} · {n(respaldo?.documents_count)} documentos.
          </DialogDescription>
        </DialogHeader>
        {error && <p className="text-sm text-red-700" data-testid="rest-error">{error}</p>}
        {rest ? (
          <div className="space-y-3"><Progreso tarea={rest} />{terminado && <Resultado tarea={rest} />}</div>
        ) : rev?.estado === 'listo' ? (
          <Revision res={rev.resultado} palabra={palabra} setPalabra={setPalabra} />
        ) : rev?.estado === 'error' ? (
          <p className="text-sm text-red-700" data-testid="rest-error">{rev.error}</p>
        ) : !error && (
          <p className="text-sm text-slate-600 flex items-center gap-2" data-testid="rest-cargando">
            <Loader2 className="w-4 h-4 animate-spin" /> Leyendo el respaldo y comparándolo con los datos actuales…
          </p>
        )}
        <DialogFooter>
          {!rest && rev?.estado === 'listo' && (
            <Button variant="destructive" disabled={palabra !== PALABRA || enviando} onClick={restaurar} data-testid="rest-confirmar">
              {enviando ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-1" />} Restaurar
            </Button>
          )}
          <Button variant="outline" disabled={enCurso} onClick={onClose} data-testid="rest-cerrar">{terminado ? 'Cerrar' : 'Cancelar'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
