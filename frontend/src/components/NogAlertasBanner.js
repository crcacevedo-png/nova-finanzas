import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, XCircle, Eye } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { igssNogApi } from '../services/api';

// Banner reutilizable de alertas de contratos NOG (90%+ y completados).
// Se autoabastece del endpoint /igss-units/nogs/alertas. Si no hay alertas
// (o no hay permiso), no renderiza nada. `onVer(alerta)` decide la acción.
export const NogAlertasBanner = ({ onVer, reloadSignal = 0 }) => {
  const [data, setData] = useState(null);

  const fetchAlertas = useCallback(async () => {
    try {
      const res = await igssNogApi.getAlertas();
      setData(res.data);
    } catch (e) {
      setData(null); // silencioso (informativo)
    }
  }, []);

  useEffect(() => {
    fetchAlertas();
  }, [fetchAlertas, reloadSignal]);

  if (!data || data.total === 0) return null;

  return (
    <Card className="border-l-4 border-l-amber-500 bg-amber-50/50" data-testid="nog-alertas-banner">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2 text-amber-800">
          <AlertTriangle className="w-5 h-5 text-amber-600" />
          Alertas de contratos NOG
          <Badge className="bg-amber-200 text-amber-900" data-testid="nog-alertas-count">{data.total}</Badge>
        </CardTitle>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          {data.completados > 0 && (
            <span className="text-red-700 font-medium">{data.completados} completado(s)</span>
          )}
          {data.completados > 0 && data.por_completarse > 0 && ' · '}
          {data.por_completarse > 0 && (
            <span className="text-amber-700 font-medium">{data.por_completarse} por completarse (≥{data.umbral_aviso}%)</span>
          )}
          {' '}— renueva el contrato a tiempo.
        </p>
      </CardHeader>
      <CardContent className="pt-0 space-y-2">
        {data.alertas.map((a) => {
          const completado = a.estado === 'completado';
          return (
            <div
              key={a.nog_id}
              className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border ${completado ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-white'}`}
              data-testid={`nog-alerta-${a.nog_id}`}
            >
              <div className="flex items-center gap-3">
                {completado
                  ? <XCircle className="w-5 h-5 text-red-500 shrink-0" />
                  : <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />}
                <div>
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {a.numero}
                    {a.nombre_servicio ? <span className="font-normal text-gray-500"> — {a.nombre_servicio}</span> : null}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {a.unidad_nombre} · {a.acreditados}/{a.cantidad} servicios ({a.porcentaje}%) · {a.disponibles} disponibles
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 sm:justify-end">
                <Badge className={completado ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>
                  {completado ? 'Completado' : 'Por completarse'}
                </Badge>
                {onVer && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="btn-outline"
                    onClick={() => onVer(a)}
                    data-testid={`nog-alerta-ver-${a.nog_id}`}
                  >
                    <Eye className="w-4 h-4 mr-1" />Ver
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default NogAlertasBanner;
