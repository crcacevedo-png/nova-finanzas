import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { FlaskConical, FileSpreadsheet, Loader2, OctagonAlert, TriangleAlert, CheckCircle2 } from 'lucide-react';
import { igssLibroApi } from '../../services/api';
import { descargarBlob } from '../../lib/igssLibro';
import { AplicarMigracion, ComparacionLote, EstadoRespaldo, LotesMigracion } from './MigracionAcciones';

// Fase 4, paso (a): simulación de la migración al libro. SOLO LECTURA y solo superadmin.
// La pantalla es para decidir: totales y desgloses; el detalle caso por caso va en el Excel.
const TODAS = 'todas';
const n = (v) => Number(v || 0).toLocaleString('es-GT');
const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');

const Cifra = ({ label, valor, tono, testId }) => (
  <div className="rounded-xl border border-slate-200 bg-white px-5 py-4" data-testid={testId}>
    <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
    <p className={`text-4xl sm:text-5xl font-semibold tabular-nums mt-1 ${tono}`}>{n(valor)}</p>
  </div>
);

const Tabla = ({ titulo, cols, filas, testId }) => (
  <div className="rounded-xl border border-slate-200 bg-white overflow-hidden" data-testid={testId}>
    <p className="px-4 py-2 text-sm font-semibold text-slate-700 border-b border-slate-100">{titulo}</p>
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>{cols.map((c, i) => <th key={c} className={`px-3 py-2 whitespace-nowrap ${i ? 'text-right' : ''}`}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {filas.length === 0 && <tr><td colSpan={cols.length} className="p-4 text-center text-slate-400">Sin datos</td></tr>}
          {filas.map((f, i) => (
            <tr key={i} className="border-t border-slate-100">
              {f.map((v, j) => <td key={j} className={`px-3 py-1.5 ${j ? 'text-right tabular-nums' : ''}`}>{v}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const Bloqueos = ({ sim }) => {
  if (!sim.bloqueos.length) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" data-testid="mig-sin-bloqueos">
        <CheckCircle2 className="w-4 h-4" />
        {sim.aplicacion_permitida ? 'Sin bloqueos: la aplicación estaría permitida.'
          : `Sin bloqueos en esta unidad, pero hay ${sim.bloqueos_totales} en otras: la aplicación se negaría.`}
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-2" data-testid="mig-bloqueos">
      <p className="flex items-center gap-2 font-semibold text-red-700">
        <OctagonAlert className="w-5 h-5" /> Bloqueo: {sim.bloqueos.length} No. SPS vigente(s) en dos unidades duplicadas. La aplicación se negará.
      </p>
      <ul className="text-sm text-red-800 space-y-1 max-h-60 overflow-y-auto">
        {sim.bloqueos.map((b) => (
          <li key={b.no_sps} data-testid={`mig-bloqueo-${b.no_sps}`}>
            <b>{b.no_sps}</b> — {b.usos.map((u) => `${u.unidad} (${u.origen}: ${u.paciente_nombre || 'sin paciente'})`).join(' · ')}
          </li>
        ))}
      </ul>
    </div>
  );
};

const Advertencias = ({ lista }) => (lista.length > 0 && (
  <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-2" data-testid="mig-advertencias">
    <p className="flex items-center gap-2 font-semibold text-amber-800">
      <TriangleAlert className="w-5 h-5" /> Advertencia: {lista.length} nombre(s) de unidad repetido(s). No impide aplicar.
    </p>
    {lista.map((a) => (
      <p key={a.nombre} className="text-sm text-amber-900">
        <b>{a.nombre}</b>: {a.unidades.map((u) => `${u.unidad} (${u.is_active ? 'activa' : 'inactiva'}, creada ${fmt(u.creada)}, ${u.pacientes_activos} pacientes, ${u.nogs} NOG)`).join(' · ')}
      </p>
    ))}
  </div>
));

const Resultado = ({ sim }) => {
  const t = sim.totales;
  return (
    <div className="space-y-4" data-testid="migracion-resultado">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Cifra label="Órdenes a migrar" valor={t.ordenes_a_migrar} tono="text-slate-900" testId="mig-total-migrar" />
        <Cifra label="Consumidas" valor={t.consumidas} tono="text-teal-700" testId="mig-total-consumidas" />
        <Cifra label="Pendientes" valor={t.pendientes} tono="text-sky-700" testId="mig-total-pendientes" />
        <Cifra label="No se migra" valor={t.no_se_migra} tono="text-red-600" testId="mig-total-no-migra" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="mig-como-entra">
        <Cifra label="Entran vivas" valor={t.ordenes_vivas} tono="text-sky-700" testId="mig-total-vivas" />
        <Cifra label="Entran históricas" valor={t.ordenes_historicas} tono="text-violet-700" testId="mig-total-historicas" />
        <Cifra label="Constancias" valor={t.constancias_evaluaciones + t.constancias_cirugias} tono="text-slate-700" testId="mig-total-constancias" />
        <Cifra label="SPS por revisar" valor={t.sps_por_revisar} tono="text-amber-700" testId="mig-total-sps-revisar" />
      </div>
      <Bloqueos sim={sim} />
      <Advertencias lista={sim.advertencias} />
      {t.ordenes_reubicadas > 0 && (
        <p className="text-sm text-amber-900" data-testid="mig-reubicadas">
          {n(t.ordenes_reubicadas)} No. SPS del par de unidades duplicadas se reubican en la unidad activa. Detalle una por una en la hoja «Órdenes reubicadas» del Excel.
        </p>
      )}
      <div className="grid xl:grid-cols-2 gap-4">
        <Tabla titulo="Por unidad" testId="mig-por-unidad"
          cols={['Unidad', 'A migrar', 'Consumidas', 'Pendientes', 'No migrables', 'Pend. de SPS']}
          filas={sim.por_unidad.map((u) => [u.unidad, n(u.a_migrar), n(u.consumidas), n(u.pendientes), n(u.no_migrables), n(u.pendientes_sps)])} />
        <div className="space-y-4">
          <Tabla titulo="Por año de primera atención" testId="mig-por-anio" cols={['Año', 'Órdenes', 'Consumidas', 'Pendientes']}
            filas={sim.por_anio.map((a) => [a.anio, n(a.ordenes), n(a.consumidas), n(a.pendientes)])} />
          <Tabla titulo="No se migra, por motivo" testId="mig-por-motivo" cols={['Motivo', 'Casos']}
            filas={sim.por_motivo.map((m) => [`${m.motivo}${m.grupo === 'Pendiente de SPS' ? ' (pendiente de SPS)' : ''}`, n(m.casos)])} />
          <Tabla titulo="Formas de No. SPS (todas las unidades)" testId="mig-patrones" cols={['Forma (dígitos por bloque)', 'Órdenes', 'Ejemplo', 'Resultado']}
            filas={sim.patrones_sps.map((p) => [<span className="font-mono">{p.patron}</span>, n(p.ordenes), <span className="font-mono">{p.ejemplo}</span>,
              p.comun ? 'Formato válido' : <span className="font-semibold text-amber-700">Revisar SPS</span>])} />
        </div>
      </div>
      <p className="text-xs text-slate-500" data-testid="mig-historial">
        Historial ignorado (solo se cuenta): {n(t.evaluaciones_historicas_ignoradas)} evaluaciones ({n(t.evaluaciones_anteriores_al_contrato)} anteriores al contrato,
        {' '}{n(t.evaluaciones_sin_unidad_igss_en_la_fecha)} anteriores a la primera actividad IGSS del paciente o, si no tiene ninguna, a la creación de su expediente)
        {' '}y {n(t.cirugias_anteriores_al_contrato)} cirugías anteriores al contrato.
        {' '}{n(t.ordenes_ya_en_libro_con_atenciones_nuevas)} órdenes que ya están en el libro tienen atenciones sin registrar (la migración no las modifica) · {n(t.revisar_fecha)} para revisar fecha.
      </p>
    </div>
  );
};

export const MigracionSimulacion = ({ onCambio }) => {
  const [sim, setSim] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [versionLotes, setVersionLotes] = useState(0);
  const [unidad, setUnidad] = useState(TODAS);
  const [cargando, setCargando] = useState('');
  const params = (u) => (u === TODAS ? {} : { unidad_id: u });

  const simular = async (u = unidad) => {
    setCargando('json');
    try {
      setSim((await igssLibroApi.simularMigracion(params(u))).data);
      setResultado(null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo generar la simulación');
    } finally {
      setCargando('');
    }
  };

  const excel = async () => {
    setCargando('excel');
    try {
      const res = await igssLibroApi.simularMigracionExcel(params(unidad));
      const nombre = unidad === TODAS ? '' : `_${(sim?.unidad || '').replace(/[^A-Za-z0-9]+/g, '_')}`;
      const fecha = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Guatemala' });
      descargarBlob(res.data, `Simulacion_migracion_libro_IGSS${nombre}_${fecha}.xlsx`);
    } catch (e) {
      toast.error('No se pudo descargar el Excel');
    } finally {
      setCargando('');
    }
  };

  const cambiarUnidad = (u) => { setUnidad(u); simular(u); };

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5 space-y-4" data-testid="migracion-simulacion">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FlaskConical className="w-6 h-6 text-teal-700" />
          <div>
            <p className="font-semibold text-slate-800">
              Migración al libro — simulación <Badge className="bg-sky-100 text-sky-700 border-0 ml-1">Solo lectura</Badge>
            </p>
            <p className="text-xs text-slate-500 max-w-2xl mt-1">
              Calcula qué pasaría al migrar el historial al libro. Simular no crea, edita ni borra ningún dato;
              aplicar se hace aparte, con confirmación. El detalle caso por caso está en el Excel.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          {sim && (
            <Select value={unidad} onValueChange={cambiarUnidad} disabled={!!cargando}>
              <SelectTrigger className="w-64 bg-white" data-testid="mig-filtro-unidad"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={TODAS}>Todas las unidades</SelectItem>
                {sim.unidades.map((u) => (
                  <SelectItem key={u.id} value={u.id}>{u.name}{u.is_active ? '' : ' (inactiva)'}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button size="sm" onClick={() => simular()} disabled={!!cargando} className="bg-teal-600 hover:bg-teal-700" data-testid="mig-simular-btn">
            {cargando === 'json' ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FlaskConical className="w-4 h-4 mr-1" />} Simular
          </Button>
          <Button size="sm" variant="outline" onClick={excel} disabled={!!cargando} className="bg-white" data-testid="mig-excel-btn">
            {cargando === 'excel' ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-1" />} Descargar Excel
          </Button>
        </div>
      </div>
      {sim && <EstadoRespaldo respaldo={sim.respaldo} />}
      {sim && <AplicarMigracion sim={sim} onCaducada={() => setSim(null)}
        onAplicada={(r) => { setResultado(r); setSim(null); setVersionLotes((v) => v + 1); onCambio?.(); }} />}
      {resultado && <ComparacionLote resultado={resultado} />}
      {sim && <Resultado sim={sim} />}
      <LotesMigracion version={versionLotes} onDeshecho={() => { setResultado(null); setSim(null); onCambio?.(); }} />
    </div>
  );
};
