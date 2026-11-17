import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { FechaDMA } from './FechaDMA';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { FileSpreadsheet, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { igssNogApi } from '../../services/api';
import { descargarBlob, nombreListado } from '../../lib/igssLibro';

// Listado oficial IGSS por unidad: 1 fila por orden COMPLETA, filtrable por la fecha en que
// se completó. Resumen + una hoja por NOG + Baja Cuantía (+ "Históricas", solo de consulta).
export const ListadoOficialDialog = ({ open, onOpenChange, unidades, unidadInicial }) => {
  const [unidad, setUnidad] = useState('');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [descargando, setDescargando] = useState(false);

  useEffect(() => { if (open) setUnidad(unidadInicial && unidadInicial !== 'all' ? unidadInicial : ''); }, [open, unidadInicial]);

  const descargar = async () => {
    if (!unidad) { toast.error('Elija la unidad IGSS'); return; }
    if (desde === null || hasta === null) { toast.error('Corrija la fecha: use dd/mm/aaaa'); return; }
    if (desde && hasta && desde > hasta) { toast.error('La fecha "desde" no puede ser posterior a "hasta"'); return; }
    const rango = { desde: desde || undefined, hasta: hasta || undefined };
    setDescargando(true);
    try {
      const res = await igssNogApi.exportUnidadExcel(unidad, rango);
      descargarBlob(res.data, nombreListado((unidades.find((u) => u.id === unidad) || {}).name, rango));
      onOpenChange(false);
    } catch (e) {
      toast.error('No se pudo generar el listado oficial');
    } finally {
      setDescargando(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="listado-oficial-dialog">
        <DialogHeader>
          <DialogTitle>Listado oficial IGSS (Excel)</DialogTitle>
          <DialogDescription>
            Una fila por orden COMPLETA (No. SPS): solo esas se cobran. Excluye reservadas, en curso, cerradas sin completar y anuladas; incluye pacientes inactivos. Las históricas van en una hoja aparte, solo de consulta.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs">Unidad IGSS *</Label>
            <select
              value={unidad} onChange={(e) => setUnidad(e.target.value)}
              className="mt-1 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm"
              data-testid="listado-oficial-unidad"
            >
              <option value="">Seleccionar unidad...</option>
              {unidades.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Desde (fecha en que se completó)</Label>
              <div className="mt-1"><FechaDMA value={desde} onChange={setDesde} testId="listado-oficial-desde" /></div>
            </div>
            <div>
              <Label className="text-xs">Hasta</Label>
              <div className="mt-1"><FechaDMA value={hasta} onChange={setHasta} testId="listado-oficial-hasta" /></div>
            </div>
          </div>
          <p className="text-xs text-slate-400">Sin fechas se exporta todo el historial: el total de filas coincide con las órdenes completas.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={descargando}>Cancelar</Button>
          <Button onClick={descargar} disabled={descargando || desde === null || hasta === null} className="bg-teal-600 hover:bg-teal-700" data-testid="listado-oficial-descargar">
            {descargando ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
            Descargar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ListadoOficialDialog;
