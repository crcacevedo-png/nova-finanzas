import React, { useState } from 'react';
import { Button } from './ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from './ui/dialog';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { igssNogApi } from '../services/api';
import { Loader2, Scale as ScaleIcon, FileSpreadsheet, RefreshCw } from 'lucide-react';

const LEYENDA = {
  D01: 'Contador del NOG distinto de las acreditaciones vigentes',
  D02: 'Cupo consumido sin atención registrada',
  D03: 'Atención registrada que no descontó cupo',
  D04: 'Acreditación vigente sin No. SPS',
  D05: 'Acreditaciones duplicadas para la misma autorización',
  D06: 'Mismo No. SPS en varios pacientes o NOG',
  D07: 'Acreditación de paciente inactivo o inexistente',
  D08: 'Acreditación con evaluación inexistente',
  D09: 'Cirugía IGSS sin acreditación vigente',
  D10: 'Paciente IGSS sin unidad asignada',
  D11: 'NOG usado que no está en el catálogo de su unidad',
  D12: 'Posibles pacientes duplicados',
  D13: 'Producción con evaluación inexistente',
  D14: 'Evaluación real sin No. SPS',
  D15: 'Orden de paciente sin No. SPS',
};

export const ConciliacionNOG = ({ unidades = [] }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [unidad, setUnidad] = useState('all');
  const [data, setData] = useState(null);

  const params = () => (unidad !== 'all' ? { unidad_id: unidad } : {});

  const cargar = async () => {
    setLoading(true);
    try {
      const res = await igssNogApi.getConciliacion(params());
      setData(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo generar la conciliación');
    } finally {
      setLoading(false);
    }
  };

  const abrir = () => {
    setOpen(true);
    if (!data) cargar();
  };

  const descargar = async () => {
    setDownloading(true);
    try {
      const res = await igssNogApi.conciliacionExcel(params());
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `conciliacion_igss_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error('No se pudo descargar el Excel');
    } finally {
      setDownloading(false);
    }
  };

  const t = data?.totales_globales || {};

  return (
    <>
      <Button variant="outline" onClick={abrir} data-testid="conciliacion-abrir-button">
        <ScaleIcon className="w-4 h-4 mr-2" /> Conciliación
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="w-[95vw] max-w-6xl max-h-[90vh] overflow-y-auto overflow-x-hidden grid-cols-[minmax(0,1fr)]" data-testid="conciliacion-dialog">
          <DialogHeader>
            <DialogTitle>Conciliación IGSS / NOG</DialogTitle>
            <DialogDescription>
              Reporte de solo lectura para cotejar contra las hojas SPS físicas. No modifica ningún dato.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={unidad}
              onChange={(e) => setUnidad(e.target.value)}
              className="h-10 w-full sm:w-64 rounded-md border border-slate-300 bg-white px-3 text-sm"
              data-testid="conciliacion-filtro-unidad"
            >
              <option value="all">Todas las unidades</option>
              {unidades.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
            <Button variant="outline" onClick={cargar} disabled={loading} data-testid="conciliacion-recargar-button">
              {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Actualizar
            </Button>
            <Button
              onClick={descargar}
              disabled={downloading || loading}
              className="bg-teal-600 hover:bg-teal-700"
              data-testid="conciliacion-excel-button"
            >
              {downloading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
              Descargar Excel
            </Button>
          </div>

          {loading && !data ? (
            <div className="py-12 text-center text-slate-400" data-testid="conciliacion-loading">
              <Loader2 className="w-5 h-5 animate-spin inline mr-2" />Analizando todas las fuentes...
            </div>
          ) : !data ? null : (
            <div className="space-y-5 min-w-0" data-testid="conciliacion-contenido">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: 'NOG analizados', value: t.nogs },
                  { label: 'Contador guardado', value: t.contador_guardado },
                  { label: 'Acreditaciones vigentes', value: t.acreditaciones_vigentes },
                  { label: 'Con atención real', value: t.autorizaciones_con_evaluacion_real },
                  { label: 'Discrepancias', value: t.discrepancias },
                ].map((c) => (
                  <div key={c.label} className="rounded-xl border bg-white p-3">
                    <p className="text-xs text-slate-500">{c.label}</p>
                    <p className="text-xl font-bold text-slate-800">{c.value ?? 0}</p>
                  </div>
                ))}
              </div>

              <div>
                <h3 className="text-base font-semibold text-slate-700 mb-2">Discrepancias por tipo</h3>
                <div className="flex flex-wrap gap-2" data-testid="conciliacion-conteo-tipos">
                  {Object.entries(data.conteo_por_tipo || {}).map(([k, v]) => (
                    <Badge
                      key={k}
                      className={v > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-500'}
                      title={LEYENDA[k]}
                      data-testid={`conciliacion-tipo-${k}`}
                    >
                      {k}: {v} — {LEYENDA[k]}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-slate-700 mb-2">Resumen por NOG</h3>
                <div className="rounded-xl border overflow-x-auto min-w-0">
                  <table className="w-full text-sm" data-testid="conciliacion-resumen-table">
                    <thead className="bg-slate-50 text-slate-600 text-left">
                      <tr>
                        <th className="px-3 py-2 font-semibold">Unidad</th>
                        <th className="px-3 py-2 font-semibold">NOG</th>
                        <th className="px-3 py-2 font-semibold text-center">Cupos</th>
                        <th className="px-3 py-2 font-semibold text-center">Contador</th>
                        <th className="px-3 py-2 font-semibold text-center">Vigentes</th>
                        <th className="px-3 py-2 font-semibold text-center">Con atención</th>
                        <th className="px-3 py-2 font-semibold text-center">Órdenes</th>
                        <th className="px-3 py-2 font-semibold text-center">Cirugías</th>
                        <th className="px-3 py-2 font-semibold text-center">Producción</th>
                        <th className="px-3 py-2 font-semibold text-center">Dif. contador</th>
                        <th className="px-3 py-2 font-semibold text-center">Dif. atendidos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.resumen_por_nog || []).map((r) => (
                        <tr key={r.nog_id} className="border-t" data-testid={`conciliacion-row-${r.nog_id}`}>
                          <td className="px-3 py-2 text-slate-600">{r.unidad || '—'}</td>
                          <td className="px-3 py-2 font-semibold text-slate-800">{r.numero}</td>
                          <td className="px-3 py-2 text-center">{r.cantidad}</td>
                          <td className="px-3 py-2 text-center">{r.contador_guardado}</td>
                          <td className="px-3 py-2 text-center">{r.acreditaciones_vigentes}</td>
                          <td className="px-3 py-2 text-center">{r.autorizaciones_con_evaluacion_real}</td>
                          <td className="px-3 py-2 text-center">{r.autorizaciones_en_ordenes}</td>
                          <td className="px-3 py-2 text-center">{r.cirugias_igss}</td>
                          <td className="px-3 py-2 text-center">{r.filas_produccion}</td>
                          <td className={`px-3 py-2 text-center font-semibold ${r.diferencia_contador !== 0 ? 'text-red-600' : 'text-slate-500'}`}>
                            {r.diferencia_contador}
                          </td>
                          <td className={`px-3 py-2 text-center font-semibold ${r.diferencia_atendidos !== 0 ? 'text-amber-600' : 'text-slate-500'}`}>
                            {r.diferencia_atendidos}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ConciliacionNOG;
