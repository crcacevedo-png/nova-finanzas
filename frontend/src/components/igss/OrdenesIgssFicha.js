import React, { useEffect, useState } from 'react';
import { Badge } from '../ui/badge';
import { Loader2 } from 'lucide-react';
import { igssLibroApi } from '../../services/api';
import { estadoOrden } from './estadosLibro';

const fmt = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');

export const avanceDosis = (o) => (o.tipo === 'procedimiento' ? `Dosis ${o.dosis_aplicadas} de ${o.dosis_autorizadas}` : 'Consulta');

// Órdenes IGSS reservadas y en curso de la ficha, SOLO LECTURA para médico y recepción (sin No. SPS ni NOG)
export const OrdenesIgssFicha = ({ pacienteId }) => {
  const [ordenes, setOrdenes] = useState(null);
  useEffect(() => {
    if (!pacienteId) return undefined;
    let vivo = true;
    igssLibroApi.ficha(pacienteId).then(({ data }) => vivo && setOrdenes(data || [])).catch(() => vivo && setOrdenes([]));
    return () => { vivo = false; };
  }, [pacienteId]);

  return (
    <div className="space-y-2" data-testid="ordenes-igss-ficha">
      <span className="text-sm font-semibold text-blue-700">Órdenes IGSS</span>
      {ordenes === null && <p className="text-xs text-slate-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Cargando…</p>}
      {ordenes?.length === 0 && <p className="text-xs text-slate-500" data-testid="ordenes-igss-ficha-vacio">Sin órdenes IGSS reservadas ni en curso.</p>}
      {(ordenes || []).map((o) => {
        const [cls, label] = estadoOrden(o.estado);
        return (
          <div key={o.id} className="flex items-center justify-between gap-2 border border-slate-200 rounded-lg px-3 py-2 bg-white" data-testid={`ficha-orden-${o.id}`}>
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-800 flex items-baseline gap-2 min-w-0">
                <span className="truncate">{o.procedimiento}</span>
                <span className="shrink-0 whitespace-nowrap font-mono text-xs font-medium text-slate-600 bg-slate-100 rounded px-1.5" data-testid={`ficha-orden-numero-${o.id}`}>{o.numero_libro}</span>
              </div>
              <div className="text-xs text-slate-500">Ingreso {fmt(o.fecha_ingreso)}{o.inyectable ? ' · Inyectable' : ''}</div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-medium text-slate-700" data-testid={`ficha-orden-dosis-${o.id}`}>{avanceDosis(o)}</span>
              <Badge variant="outline" className={cls} data-testid={`ficha-orden-estado-${o.id}`}>{label}</Badge>
            </div>
          </div>
        );
      })}
    </div>
  );
};
