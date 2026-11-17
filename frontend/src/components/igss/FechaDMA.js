import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { CalendarDays } from 'lucide-react';
import { Input } from '../ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Calendar } from '../ui/calendar';

const aTexto = (iso) => (iso ? iso.split('-').reverse().join('/') : '');

export const aIso = (txt) => {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(txt || '');
  if (!m) return null;
  const [, d, mo, y] = m;
  const f = new Date(Number(y), Number(mo) - 1, Number(d));
  if (f.getFullYear() !== Number(y) || f.getMonth() !== Number(mo) - 1 || f.getDate() !== Number(d)) return null;
  return `${y}-${mo}-${d}`;
};

const enmascarar = (v) => {
  const dig = v.replace(/\D/g, '').slice(0, 8);
  return [dig.slice(0, 2), dig.slice(2, 4), dig.slice(4)].filter(Boolean).join('/');
};

// Fecha en el formato de la app (dd/mm/aaaa), escrita o elegida en el calendario.
// value/onChange en ISO (aaaa-mm-dd): '' = vacía, null = fecha incompleta o inválida.
export const FechaDMA = ({ value, onChange, testId, inputClassName = '' }) => {
  const [texto, setTexto] = useState(aTexto(value));
  const [abierto, setAbierto] = useState(false);
  useEffect(() => { if (value || value === '') setTexto(aTexto(value)); }, [value]);

  const escribir = (e) => {
    const t = enmascarar(e.target.value);
    setTexto(t);
    onChange(t === '' ? '' : aIso(t));
  };
  const elegir = (d) => {
    if (!d) return;
    const iso = format(d, 'yyyy-MM-dd');
    setTexto(aTexto(iso));
    onChange(iso);
    setAbierto(false);
  };
  const invalida = texto !== '' && !aIso(texto);
  const elegido = value ? new Date(`${value}T12:00:00`) : undefined;

  return (
    <div>
      <div className="relative">
        <Input value={texto} onChange={escribir} placeholder="dd/mm/aaaa" inputMode="numeric" aria-invalid={invalida}
          className={`pr-8 ${inputClassName} ${invalida ? 'border-red-500' : ''}`} data-testid={testId} />
        <Popover open={abierto} onOpenChange={setAbierto}>
          <PopoverTrigger asChild>
            <button type="button" aria-label="Abrir calendario" data-testid={`${testId}-calendario`}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-teal-700">
              <CalendarDays className="w-4 h-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="end">
            <Calendar mode="single" locale={es} weekStartsOn={1} selected={elegido} defaultMonth={elegido} onSelect={elegir} initialFocus />
          </PopoverContent>
        </Popover>
      </div>
      {invalida && <p className="text-[11px] text-red-600 mt-0.5" data-testid={`${testId}-error`}>Fecha inválida: use dd/mm/aaaa</p>}
    </div>
  );
};
