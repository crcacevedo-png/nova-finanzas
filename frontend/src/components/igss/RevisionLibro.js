import React from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { CheckCircle2, CircleSlash, Clock, Inbox, Scissors } from 'lucide-react';
import { estadoOrden } from './estadosLibro';

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');

const CIFRAS = [
  ['completas', 'Completas', 'se cobran', 'text-emerald-700'],
  ['en_curso', 'En curso', 'ocupan cupo', 'text-sky-700'],
  ['reservadas', 'Reservadas', 'ocupan cupo', 'text-amber-700'],
  ['historicas', 'Históricas', 'no se cobran', 'text-violet-700'],
  ['cerradas', 'Cerradas sin completar', 'no se cobran', 'text-orange-700'],
];

// Cifras del libro (todas las unidades): las históricas nunca se suman a las completas
export const ResumenLibro = ({ resumen }) => (
  <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="libro-resumen">
    {CIFRAS.map(([k, label, nota, color]) => (
      <div key={k} className="rounded-xl border border-slate-200 bg-white p-4" data-testid={`libro-resumen-${k}`}>
        <p className="text-xs text-slate-500">{label}</p>
        <p className={`text-2xl font-semibold ${color}`} data-testid={`libro-resumen-${k}-valor`}>{resumen?.[k] ?? 0}</p>
        <p className="text-[11px] text-slate-400">{nota}</p>
      </div>
    ))}
  </div>
);

const TARJETAS = [
  ['sin_orden', Inbox, 'Atenciones sin orden', 'Pendientes de asignar a una orden'],
  ['cirugias', Scissors, 'Cirugías sin marcar como realizadas', 'De órdenes reservadas o en curso: ya pasó su fecha y no se cobran hasta marcarlas'],
  ['detenidas', Clock, 'En curso sin movimiento', 'Sin dosis ni atención nueva en más de 90 días'],
];

export const TarjetasRevision = ({ vista, onVista, conteos }) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="libro-revision">
    {TARJETAS.map(([k, Icono, titulo, sub]) => (
      <button key={k} type="button" onClick={() => onVista(k)} data-testid={`libro-revision-${k}`}
        className={`text-left rounded-xl border p-4 bg-white transition-colors hover:bg-slate-50 ${vista === k ? 'border-teal-600 ring-1 ring-teal-600' : 'border-slate-200'}`}>
        <div className="flex items-center justify-between">
          <Icono className="w-5 h-5 text-teal-700" />
          <span className={`text-2xl font-semibold ${conteos[k] ? 'text-red-600' : 'text-slate-400'}`} data-testid={`libro-revision-${k}-total`}>{conteos[k] ?? 0}</span>
        </div>
        <p className="mt-2 text-sm font-semibold text-slate-800">{titulo}</p>
        <p className="text-xs text-slate-500">{sub}</p>
      </button>
    ))}
  </div>
);

const Vacio = ({ cols, texto, testId }) => (
  <tr><td colSpan={cols} className="p-6 text-center text-sm text-slate-400" data-testid={testId}>{texto}</td></tr>
);

const Th = ({ children }) => <th className="px-3 py-2">{children}</th>;

export const TablaCirugiasPorMarcar = ({ filas, onMarcar }) => (
  <table className="w-full text-left" data-testid="cirugias-por-marcar-tabla">
    <thead className="text-xs uppercase text-slate-500 bg-slate-50">
      <tr><Th>Fecha</Th><Th>Paciente</Th><Th>Procedimiento</Th><Th>Orden (No. SPS)</Th><Th>Atraso</Th><Th /></tr>
    </thead>
    <tbody>
      {filas.length === 0 && <Vacio cols={6} texto="No hay cirugías de órdenes reservadas o en curso pendientes de marcar." testId="cirugias-por-marcar-vacio" />}
      {filas.map((c) => (
        <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`cirugia-por-marcar-${c.id}`}>
          <td className="px-3 py-2 text-sm whitespace-nowrap">{fmt(c.fecha)} <span className="text-xs text-slate-400">{c.hora}</span></td>
          <td className="px-3 py-2 text-sm font-medium text-slate-800">{c.paciente_nombre || '—'}<div className="text-xs text-slate-400 font-normal">{c.unidad}</div></td>
          <td className="px-3 py-2 text-sm text-slate-600">{c.procedimiento} {c.ojo}<div className="text-xs text-slate-400">{c.cirujano}</div></td>
          <td className="px-3 py-2 text-xs">
            <span className="font-mono">{c.orden?.no_sps}</span>
            <div className="text-slate-400">{estadoOrden(c.orden?.estado)[1]}{c.orden?.inyectable ? ' · Inyectable' : ''}</div>
          </td>
          <td className="px-3 py-2 text-xs text-red-600 whitespace-nowrap">{c.dias_atraso} días</td>
          <td className="px-3 py-2 text-right">
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => onMarcar(c)} data-testid={`cirugia-marcar-${c.id}`}>
              <CheckCircle2 className="w-3 h-3 mr-1" /> Marcar realizada
            </Button>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);

export const TablaDetenidas = ({ filas, onCerrar }) => (
  <table className="w-full text-left" data-testid="detenidas-tabla">
    <thead className="text-xs uppercase text-slate-500 bg-slate-50">
      <tr><Th>No. SPS</Th><Th>Paciente</Th><Th>Procedimiento</Th><Th>Avance</Th><Th>Última actividad</Th><Th /></tr>
    </thead>
    <tbody>
      {filas.length === 0 && <Vacio cols={6} texto="No hay órdenes en curso detenidas." testId="detenidas-vacio" />}
      {filas.map((o) => (
        <tr key={o.id} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`detenida-${o.id}`}>
          <td className="px-3 py-2 text-xs font-mono">{o.no_sps}<div className="font-sans text-slate-400">{o.etiqueta_nog}</div></td>
          <td className="px-3 py-2 text-sm font-medium text-slate-800">{o.paciente_nombre}<div className="text-xs text-slate-400 font-normal">{o.paciente_expediente}</div></td>
          <td className="px-3 py-2 text-sm text-slate-600">{o.procedimiento || o.nombre_servicio || '—'}</td>
          <td className="px-3 py-2 text-xs whitespace-nowrap">
            <Badge variant="outline" className={estadoOrden(o.estado)[0]}>{estadoOrden(o.estado)[1]}</Badge>{' '}
            {o.dosis_aplicadas} de {o.dosis_autorizadas} dosis
          </td>
          <td className="px-3 py-2 text-xs whitespace-nowrap">{fmt(o.ultima_actividad)} · <span className="text-red-600">{o.dias_sin_movimiento} días</span></td>
          <td className="px-3 py-2 text-right">
            <Button size="sm" variant="ghost" className="h-7 text-xs text-orange-700" onClick={() => onCerrar(o)} data-testid={`detenida-cerrar-${o.id}`}>
              <CircleSlash className="w-3 h-3 mr-1" /> Cerrar sin completar
            </Button>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);
