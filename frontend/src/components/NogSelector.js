import React, { useState, useEffect, useCallback } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Input } from './ui/input';
import { igssNogApi } from '../services/api';

const LIBRE = '__libre__';

// Selector de NOG para la ficha del paciente: elige un NOG del catálogo de la
// unidad o escribe uno libre (compatibilidad). Los NOG completados no se pueden
// elegir para pacientes nuevos, salvo que ya sea el valor actual del paciente.
export const NogSelector = ({ unitId, value, onChange, idSuffix = '' }) => {
  const [nogs, setNogs] = useState([]);
  const [libre, setLibre] = useState(false);

  const fetchNogs = useCallback(async () => {
    if (!unitId) {
      setNogs([]);
      return;
    }
    try {
      const res = await igssNogApi.getActivos(unitId);
      // Excluir NOGs sin número: un <SelectItem value=""> hace que Radix Select
      // lance una excepción y rompa la página (ErrorBoundary).
      setNogs((res.data || []).filter((n) => (n.numero || '').toString().trim() !== ''));
    } catch (e) {
      setNogs([]);
    }
  }, [unitId]);

  useEffect(() => {
    fetchNogs();
  }, [fetchNogs]);

  // Ajusta el modo (catálogo/libre) según el valor actual y los NOG disponibles
  useEffect(() => {
    if (!value) {
      setLibre(false);
      return;
    }
    const enCatalogo = nogs.some((n) => n.numero === value);
    setLibre(!enCatalogo);
  }, [value, nogs]);

  const handleSelect = (val) => {
    // Radix Select v2 puede emitir onValueChange('') al montar con un valor
    // preseleccionado (modo edición). Ignorar ese evento espurio para no borrar
    // el NOG ya asignado. El borrado explícito se hace con la opción LIBRE o el
    // input de texto libre.
    if (!val) return;
    if (val === LIBRE) {
      setLibre(true);
      onChange('');
    } else {
      setLibre(false);
      onChange(val);
    }
  };

  // Sin catálogo: solo texto libre (comportamiento anterior)
  if (nogs.length === 0) {
    return (
      <Input
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="input-teal"
        placeholder="No. Orden Gestión"
        data-testid={`patient-igss-nog${idSuffix}`}
      />
    );
  }

  const selectValue = libre ? LIBRE : (value || '');

  return (
    <div className="space-y-2">
      <Select value={selectValue} onValueChange={handleSelect}>
        <SelectTrigger className="input-teal" data-testid={`patient-igss-nog-select${idSuffix}`}>
          <SelectValue placeholder="Seleccionar NOG" />
        </SelectTrigger>
        <SelectContent>
          {nogs.map((n) => {
            const completado = n.estado === 'completado';
            const esValorActual = n.numero === value;
            return (
              <SelectItem
                key={n.id}
                value={n.numero}
                disabled={completado && !esValorActual}
                data-testid={`patient-nog-option-${n.id}`}
              >
                {n.numero}{n.nombre_servicio ? ` — ${n.nombre_servicio}` : ''}
                {completado ? ' (completado)' : ` (${n.disponibles} disp.)`}
              </SelectItem>
            );
          })}
          <SelectItem value={LIBRE} data-testid="patient-nog-option-libre">
            Otro (escribir NOG)
          </SelectItem>
        </SelectContent>
      </Select>
      {libre && (
        <Input
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="input-teal"
          placeholder="No. Orden Gestión (texto libre)"
          data-testid={`patient-igss-nog${idSuffix}`}
        />
      )}
    </div>
  );
};

export default NogSelector;
