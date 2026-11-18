// Estados de una orden del libro IGSS (etiqueta y color) y desglose de cupo de un NOG
export const ESTADO_ORDEN = {
  reservada: ['bg-amber-50 text-amber-700 border-amber-200', 'Reservada'],
  en_curso: ['bg-sky-50 text-sky-700 border-sky-200', 'En curso'],
  completa: ['bg-emerald-50 text-emerald-700 border-emerald-200', 'Completa'],
  historica: ['bg-violet-50 text-violet-700 border-violet-200', 'Histórica'],
  cerrada: ['bg-orange-50 text-orange-700 border-orange-200', 'Cerrada sin completar'],
  anulada: ['bg-slate-100 text-slate-500 border-slate-200', 'Anulada'],
};

export const ESTADOS_ACTIVOS = ['reservada', 'en_curso', 'completa'];

export const estadoOrden = (e) => ESTADO_ORDEN[e] || ESTADO_ORDEN.reservada;

// "2 completas · 1 en curso · 3 reservadas · 5 históricas" (las históricas solo si hay)
export const desgloseCupo = (n) => [
  `${n?.completas ?? 0} completas`,
  `${n?.en_curso ?? 0} en curso`,
  `${n?.reservadas ?? 0} reservadas`,
  n?.historicas ? `${n.historicas} históricas` : null,
  n?.sin_sps ? `${n.sin_sps} sin SPS` : null,
].filter(Boolean).join(' · ');
