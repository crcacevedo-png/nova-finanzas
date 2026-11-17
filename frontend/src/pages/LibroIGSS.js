import React, { useCallback, useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { toast, Toaster } from 'sonner';
import { BookOpen, ShieldCheck, ShieldOff, Search, Link2, XCircle, Loader2, Lock, Unlock } from 'lucide-react';
import { igssLibroApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { MotivoDialog, ElegirOrdenDialog } from '../components/igss/OrdenDialogs';

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');
const fmtHora = (f) => (f ? new Date(f).toLocaleString('es-GT') : '—');
const ESTADOS = [['pendiente', 'Pendientes'], ['resuelta', 'Resueltas'], ['descartada', 'Descartadas']];

const INTERRUPTORES = {
  exigir_orden: {
    testId: 'libro-interruptor', titulo: 'Exigir orden del libro', iconos: [ShieldCheck, ShieldOff],
    quien: 'actualizado_por_nombre', cuando: 'actualizado_en', confirmarTitulo: '¿Encender la exigencia de orden?',
    texto: 'Encendido: una cirugía IGSS nueva exige paciente y un No. SPS del libro, y se rechaza la dosis de más. Apagado: se guarda igual y queda en "atenciones sin orden". En ambos casos una orden con sus dosis completas no admite otra.',
    confirmar: (c) => <>Hay <b data-testid="libro-interruptor-pendientes">{c?.atenciones_sin_orden_pendientes ?? 0}</b> atenciones sin orden pendientes. Las cirugías IGSS nuevas sin una orden del libro ya no se podrán guardar.</>,
  },
  usar_solo_libro: {
    testId: 'libro-solo-libro', titulo: 'Usar solo el libro', iconos: [Lock, Unlock],
    quien: 'solo_libro_actualizado_por_nombre', cuando: 'solo_libro_actualizado_en', confirmarTitulo: '¿Usar solo el libro?',
    texto: 'Encendido: guardar, desactivar o eliminar pacientes y evaluaciones, eliminar un NOG y limpiar borradores dejan de escribir en el sistema anterior (acreditaciones, contador "acreditados" y producción antigua), y sus recálculos quedan deshabilitados. El libro se sigue actualizando igual. Apagado por defecto.',
    confirmar: () => 'Los botones y funciones antiguas de recalcular, reconciliar, aplicar y anular acreditación quedarán deshabilitados. Los datos antiguos no se borran.',
  },
};

const Interruptor = ({ campo, config, esSuperadmin, onCambiar }) => {
  const d = INTERRUPTORES[campo];
  const [confirmar, setConfirmar] = useState(false);
  const encendido = !!config?.[campo];
  const [IconoOn, IconoOff] = d.iconos;
  const pedirCambio = (v) => (v ? setConfirmar(true) : onCambiar(campo, false));
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 flex flex-wrap items-center justify-between gap-4" data-testid={d.testId}>
      <div className="flex items-start gap-3">
        {encendido ? <IconoOn className="w-6 h-6 text-emerald-600" /> : <IconoOff className="w-6 h-6 text-slate-400" />}
        <div>
          <p className="font-semibold text-slate-800">
            {d.titulo}{' '}
            <Badge className={encendido ? 'bg-emerald-100 text-emerald-700 border-0' : 'bg-slate-100 text-slate-600 border-0'} data-testid={`${d.testId}-estado`}>
              {encendido ? 'Encendido' : 'Apagado'}
            </Badge>
          </p>
          <p className="text-xs text-slate-500 max-w-xl mt-1">{d.texto}</p>
          {config?.[d.cuando] && (
            <p className="text-xs text-slate-400 mt-1">Último cambio: {config[d.quien]} · {fmtHora(config[d.cuando])}</p>
          )}
        </div>
      </div>
      {esSuperadmin ? (
        <Switch checked={encendido} onCheckedChange={pedirCambio} data-testid={`${d.testId}-switch`} />
      ) : (
        <span className="text-xs text-slate-400">Solo superadmin puede cambiarlo</span>
      )}
      <AlertDialog open={confirmar} onOpenChange={setConfirmar}>
        <AlertDialogContent data-testid={`${d.testId}-confirmar`}>
          <AlertDialogHeader>
            <AlertDialogTitle>{d.confirmarTitulo}</AlertDialogTitle>
            <AlertDialogDescription>{d.confirmar(config)}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => onCambiar(campo, true)} data-testid={`${d.testId}-confirmar-btn`}>Encender</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

const FilaSinOrden = ({ e, onAsignar, onDescartar }) => (
  <tr className="border-b border-slate-100 hover:bg-slate-50" data-testid={`sin-orden-row-${e.id}`}>
    <td className="px-3 py-2 text-sm">{fmt(e.fecha)}</td>
    <td className="px-3 py-2 text-sm">{e.tipo === 'cirugia' ? 'Cirugía' : 'Evaluación'}</td>
    <td className="px-3 py-2 text-sm">
      <div className="font-medium text-slate-800">{e.paciente_nombre || '—'}</div>
      <div className="text-xs text-slate-400">{e.paciente_expediente}</div>
    </td>
    <td className="px-3 py-2 text-sm text-slate-600">{e.procedimiento || '—'}{e.medico ? <div className="text-xs text-slate-400">{e.medico}</div> : null}</td>
    <td className="px-3 py-2 text-xs text-slate-600 max-w-xs">{e.estado === 'pendiente' ? e.motivo : (e.motivo_cierre || e.motivo)}</td>
    <td className="px-3 py-2 text-right whitespace-nowrap">
      {e.estado === 'pendiente' && (
        <>
          <Button size="sm" variant="outline" className="h-7 text-xs mr-1" onClick={() => onAsignar(e)} disabled={!e.paciente_id} data-testid={`sin-orden-asignar-${e.id}`}>
            <Link2 className="w-3 h-3 mr-1" /> Asignar
          </Button>
          <Button size="sm" variant="ghost" className="h-7 text-xs text-red-600" onClick={() => onDescartar(e)} data-testid={`sin-orden-descartar-${e.id}`}>
            <XCircle className="w-3 h-3 mr-1" /> Descartar
          </Button>
        </>
      )}
    </td>
  </tr>
);

export default function LibroIGSS() {
  const { user } = useAuth();
  const [config, setConfig] = useState(null);
  const [estado, setEstado] = useState('pendiente');
  const [q, setQ] = useState('');
  const [lista, setLista] = useState({ data: [], total: 0, pendientes: 0 });
  const [cargando, setCargando] = useState(true);
  const [asignar, setAsignar] = useState(null);
  const [descartar, setDescartar] = useState(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [c, l] = await Promise.all([igssLibroApi.config(), igssLibroApi.sinOrden({ estado, q: q || undefined, limit: 200 })]);
      setConfig(c.data);
      setLista(l.data);
    } catch (e) {
      toast.error('No se pudo cargar el libro IGSS');
    } finally {
      setCargando(false);
    }
  }, [estado, q]);

  useEffect(() => { cargar(); }, [cargar]);

  const cambiarInterruptor = async (campo, v) => {
    try {
      await igssLibroApi.cambiarConfig({ [campo]: v });
      toast.success(`${INTERRUPTORES[campo].titulo}: ${v ? 'encendido' : 'apagado'}`);
      cargar();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo cambiar');
    }
  };

  return (
    <Layout>
      <div className="p-6 space-y-6" data-testid="libro-igss-page">
        <div className="flex items-center gap-3">
          <BookOpen className="w-7 h-7 text-teal-700" />
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Libro de órdenes IGSS</h1>
            <p className="text-sm text-slate-500">Atenciones que no pudieron vincularse a una orden (No. SPS).</p>
          </div>
        </div>
        {['exigir_orden', 'usar_solo_libro'].map((campo) => (
          <Interruptor key={campo} campo={campo} config={config} esSuperadmin={user?.role === 'superadmin'} onCambiar={cambiarInterruptor} />
        ))}
        <div className="rounded-xl border border-slate-200 bg-white">
          <div className="p-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100">
            <div className="flex gap-1">
              {ESTADOS.map(([v, l]) => (
                <Button key={v} size="sm" variant={estado === v ? 'default' : 'ghost'} onClick={() => setEstado(v)}
                  className={estado === v ? 'bg-teal-600 hover:bg-teal-700' : ''} data-testid={`sin-orden-tab-${v}`}>
                  {l}{v === 'pendiente' ? ` (${lista.pendientes})` : ''}
                </Button>
              ))}
            </div>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Paciente, expediente o SPS" className="pl-8 w-64" data-testid="sin-orden-buscar" />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="sin-orden-tabla">
              <thead className="text-xs uppercase text-slate-500 bg-slate-50">
                <tr>
                  <th className="px-3 py-2">Fecha</th><th className="px-3 py-2">Tipo</th><th className="px-3 py-2">Paciente</th>
                  <th className="px-3 py-2">Procedimiento</th><th className="px-3 py-2">Motivo</th><th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {cargando && <tr><td colSpan={6} className="p-6 text-center text-slate-400"><Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>}
                {!cargando && lista.data.length === 0 && (
                  <tr><td colSpan={6} className="p-6 text-center text-sm text-slate-400" data-testid="sin-orden-vacio">No hay atenciones en esta lista.</td></tr>
                )}
                {!cargando && lista.data.map((e) => (
                  <FilaSinOrden key={e.id} e={e} onAsignar={setAsignar} onDescartar={setDescartar} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <ElegirOrdenDialog
        open={!!asignar} onOpenChange={(v) => !v && setAsignar(null)} pacienteId={asignar?.paciente_id}
        titulo={`Asignar ${asignar?.tipo === 'cirugia' ? 'cirugía' : 'evaluación'} a una orden`}
        onConfirm={async (ordenId) => { await igssLibroApi.asignar(asignar.id, ordenId); toast.success('Atención asignada'); cargar(); }}
      />
      <MotivoDialog
        open={!!descartar} onOpenChange={(v) => !v && setDescartar(null)} testId="descartar-sin-orden-dialog"
        titulo="Descartar atención" descripcion="Úselo cuando la atención no corresponde a una orden IGSS."
        accion="Descartar" onConfirm={async (motivo) => { await igssLibroApi.descartar(descartar.id, motivo); toast.success('Atención descartada'); cargar(); }}
      />
      <Toaster position="top-right" richColors />
    </Layout>
  );
}
