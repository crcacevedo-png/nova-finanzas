import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { FlaskConical, FileSpreadsheet, Loader2 } from 'lucide-react';
import { igssLibroApi } from '../../services/api';
import { descargarBlob } from '../../lib/igssLibro';

// Fase 4, paso (a): simulación de la migración al libro. SOLO LECTURA: no aplica nada.
const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');
const MAX_FILAS = 100;

const Dato = ({ label, valor, tono = 'text-slate-800', testId }) => (
  <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2" data-testid={testId}>
    <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
    <p className={`text-xl font-semibold ${tono}`}>{valor}</p>
  </div>
);

const Tabla = ({ titulos, filas, testId, vacio }) => (
  <div className="overflow-x-auto rounded-lg border border-slate-200">
    <table className="w-full text-left text-xs" data-testid={testId}>
      <thead className="bg-slate-50 uppercase text-slate-500">
        <tr>{titulos.map((t) => <th key={t} className="px-2 py-2 whitespace-nowrap">{t}</th>)}</tr>
      </thead>
      <tbody>
        {filas.length === 0 && <tr><td colSpan={titulos.length} className="p-4 text-center text-slate-400">{vacio}</td></tr>}
        {filas.map((f, i) => (
          <tr key={i} className="border-t border-slate-100">{f.map((v, j) => <td key={j} className="px-2 py-1.5">{v}</td>)}</tr>
        ))}
      </tbody>
    </table>
  </div>
);

const filasNog = (resumen) => resumen
  .filter((f) => f.migrar_atendidas || f.migrar_pendientes || f.pendientes_sps || f.libro_consumidos || f.libro_reservados)
  .map((f) => [f.unidad, f.nog, f.sin_tope ? 'Sin tope' : f.cantidad, f.consumidos, f.reservados,
    f.sin_tope ? '—' : f.disponibles,
    <span key="p" className={f.pendientes_sps ? 'font-semibold text-amber-700' : ''}>{f.pendientes_sps}</span>,
    f.sobrecupo ? <span key="s" className="font-semibold text-red-600">{f.sobrecupo}</span> : 0]);

const LISTAS = {
  manual: {
    label: 'Revisión manual', titulos: ['Etiqueta', 'Paciente', 'NOG', 'Fecha', 'Motivo', 'Orden probable'],
    filas: (s) => s.revision_manual.map((i) => [i.etiqueta, i.paciente_nombre || '—', i.nog || 'Sin NOG identificado', fmt(i.fecha), i.motivo, i.orden_probable || '—']),
  },
  ordenes: {
    label: 'Órdenes a migrar', titulos: ['No. SPS', 'Paciente', 'NOG', 'Estado', '1ª atención', 'Atenciones', 'Revisar fecha'],
    filas: (s) => s.ordenes.map((o) => [o.no_sps, o.paciente_nombre, o.nog, o.estado, fmt(o.fecha_primera_atencion), o.evaluaciones + o.cirugias, o.revisar_fecha ? 'Sí' : 'No']),
  },
  no_migrables: {
    label: 'No migrables', titulos: ['No. SPS', 'Paciente(s)', 'NOG(s)', 'Motivo'],
    filas: (s) => s.no_migrables.map((n) => [n.no_sps || '(vacío)', n.pacientes.join(', '), n.nogs.join(', ') || '—', n.motivo]),
  },
};

const Resultado = ({ sim }) => {
  const [lista, setLista] = useState('manual');
  const t = sim.totales;
  const filas = LISTAS[lista].filas(sim);
  return (
    <div className="space-y-5" data-testid="migracion-resultado">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Dato label="Órdenes a migrar" valor={t.ordenes_a_migrar} testId="mig-ordenes" />
        <Dato label="Atendidas / pendientes" valor={`${t.atendidas} / ${t.pendientes}`} testId="mig-atendidas" />
        <Dato label="Revisión manual" valor={t.revision_manual} tono="text-amber-700" testId="mig-manual" />
        <Dato label="No migrables" valor={t.no_migrables} tono="text-red-600" testId="mig-no-migrables" />
      </div>
      <div className="text-sm text-slate-600 space-y-1" data-testid="mig-historial">
        <p><b>{t.evaluaciones_historicas_ignoradas} evaluaciones históricas ignoradas</b> ({t.evaluaciones_anteriores_al_contrato} anteriores al contrato · {t.evaluaciones_sin_unidad_igss_en_la_fecha} sin unidad IGSS en esa fecha) · {t.cirugias_anteriores_al_contrato} cirugías anteriores al contrato.</p>
        <p>{t.revision_manual_cupo_sin_sps} cupos descontados sin SPS ({t.cupo_sin_sps_con_orden_probable} con una orden probable) · {t.revisar_fecha} órdenes para revisar fecha · {t.nogs_con_sobrecupo} entradas sobre su cupo.</p>
      </div>
      <div className="grid md:grid-cols-[220px_1fr] gap-4">
        <Tabla testId="mig-por-anio" titulos={['Año 1ª atención', 'Órdenes']} vacio="Sin órdenes"
          filas={sim.por_anio.map((a) => [a.anio, a.ordenes])} />
        <Tabla testId="mig-por-nog" vacio="Sin movimiento"
          titulos={['Unidad', 'NOG / Entrada', 'Cupos', 'Consumidos', 'Reservados', 'Disponibles', 'Pendientes de SPS', 'Sobrecupo']}
          filas={filasNog(sim.resumen_nog)} />
      </div>
      <div className="space-y-2">
        <div className="flex gap-1">
          {Object.entries(LISTAS).map(([k, v]) => (
            <Button key={k} size="sm" variant={lista === k ? 'default' : 'ghost'} onClick={() => setLista(k)}
              className={lista === k ? 'bg-teal-600 hover:bg-teal-700' : ''} data-testid={`mig-tab-${k}`}>{v.label}</Button>
          ))}
        </div>
        <Tabla testId={`mig-lista-${lista}`} titulos={LISTAS[lista].titulos} filas={filas.slice(0, MAX_FILAS)} vacio="Sin casos" />
        {filas.length > MAX_FILAS && <p className="text-xs text-slate-400">Se muestran {MAX_FILAS} de {filas.length}. Descargue el Excel para verlos todos.</p>}
      </div>
    </div>
  );
};

export const MigracionSimulacion = () => {
  const [sim, setSim] = useState(null);
  const [cargando, setCargando] = useState('');

  const ejecutar = async (modo) => {
    setCargando(modo);
    try {
      if (modo === 'excel') {
        const res = await igssLibroApi.simularMigracionExcel();
        descargarBlob(res.data, `simulacion_migracion_libro_igss_${new Date().toISOString().slice(0, 10)}.xlsx`);
      } else {
        setSim((await igssLibroApi.simularMigracion()).data);
      }
    } catch (e) {
      toast.error('No se pudo generar la simulación');
    } finally {
      setCargando('');
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4" data-testid="migracion-simulacion">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <FlaskConical className="w-6 h-6 text-teal-700" />
          <div>
            <p className="font-semibold text-slate-800">
              Migración al libro — simulación <Badge className="bg-sky-100 text-sky-700 border-0 ml-1">Solo lectura</Badge>
            </p>
            <p className="text-xs text-slate-500 max-w-2xl mt-1">
              Muestra qué órdenes pasarían al libro, qué casos quedarían para revisión manual y cuánto historial se ignora.
              No crea, edita ni borra ningún dato.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => ejecutar('json')} disabled={!!cargando} className="bg-teal-600 hover:bg-teal-700" data-testid="mig-simular-btn">
            {cargando === 'json' ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FlaskConical className="w-4 h-4 mr-1" />} Simular
          </Button>
          <Button size="sm" variant="outline" onClick={() => ejecutar('excel')} disabled={!!cargando} data-testid="mig-excel-btn">
            {cargando === 'excel' ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-1" />} Excel
          </Button>
        </div>
      </div>
      {sim && <Resultado sim={sim} />}
    </div>
  );
};
