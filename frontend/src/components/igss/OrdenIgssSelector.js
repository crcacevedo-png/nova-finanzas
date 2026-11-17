import React, { useEffect, useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { igssLibroApi } from '../../services/api';

export const NINGUNA = 'ninguna';

const fmt = (f) => {
  if (!f) return '';
  const [y, m, d] = String(f).slice(0, 10).split('-');
  return d ? `${d}/${m}/${y}` : f;
};

// Órdenes abiertas del paciente (solo procedimiento y fecha de ingreso; nunca SPS/NOG/dosis)
export const useOrdenesAbiertas = (pacienteId, activo = true) => {
  const [estado, setEstado] = useState({ opciones: [], cargado: false });
  useEffect(() => {
    if (!pacienteId || !activo) { setEstado({ opciones: [], cargado: false }); return undefined; }
    let cancel = false;
    setEstado({ opciones: [], cargado: false });
    igssLibroApi.abiertas(pacienteId)
      .then(({ data }) => { if (!cancel) setEstado({ opciones: data || [], cargado: true }); })
      .catch(() => { if (!cancel) setEstado({ opciones: [], cargado: true }); });
    return () => { cancel = true; };
  }, [pacienteId, activo]);
  return estado;
};

// Elige qué orden usar sin intervención: la preferida (p. ej. de la cita) o la única abierta
export const ordenPreseleccionada = (opciones, preferidaId) =>
  (opciones.find((o) => o.id === preferidaId) || (opciones.length === 1 ? opciones[0] : null));

export const OrdenIgssSelector = ({ opciones, cargado, value, onChange, disabled, testIdPrefix = 'orden-igss' }) => {
  const legacy = value && value !== NINGUNA && !opciones.some((o) => o.id === value);
  return (
    <div className="space-y-1.5" data-testid={`${testIdPrefix}-selector`}>
      <Select value={value || ''} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="input-teal" data-testid={`${testIdPrefix}-select`}>
          <SelectValue placeholder={cargado ? 'Seleccionar orden' : 'Cargando órdenes…'} />
        </SelectTrigger>
        <SelectContent>
          {opciones.map((o) => (
            <SelectItem key={o.id} value={o.id} data-testid={`${testIdPrefix}-option-${o.id}`}>
              {o.procedimiento}{o.fecha_ingreso ? ` · Ingreso ${fmt(o.fecha_ingreso)}` : ''}
            </SelectItem>
          ))}
          {legacy && <SelectItem value={value}>Orden registrada anteriormente</SelectItem>}
          <SelectItem value={NINGUNA} data-testid={`${testIdPrefix}-ninguna`}>Ninguna de estas / no sé</SelectItem>
        </SelectContent>
      </Select>
      {cargado && opciones.length === 0 && (
        <p className="text-xs text-slate-500" data-testid={`${testIdPrefix}-sin-opciones`}>
          El paciente no tiene órdenes IGSS abiertas. Se guardará normal y Administración IGSS la asignará.
        </p>
      )}
      {value === NINGUNA && (
        <p className="text-xs text-slate-500">Se guardará normal y Administración IGSS asignará la orden.</p>
      )}
    </div>
  );
};
