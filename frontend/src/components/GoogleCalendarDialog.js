import React, { useState, useEffect, useCallback } from 'react';
import { CalendarCheck, Link2, Unlink, RefreshCw, Check, History } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { googleCalendarApi } from '../services/api';

const fmtFecha = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('es-GT', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return '—';
  }
};

export const GoogleCalendarDialog = ({ open, onOpenChange }) => {
  const [loading, setLoading] = useState(true);
  const [medicos, setMedicos] = useState([]);
  const [busy, setBusy] = useState(null);
  const [cals, setCals] = useState({});
  const [selBusy, setSelBusy] = useState(null);
  const [resyncing, setResyncing] = useState(false);

  const loadCalendars = useCallback(async (list) => {
    const connected = (list || []).filter((m) => m.connected);
    const entries = await Promise.all(
      connected.map(async (m) => {
        try {
          const r = await googleCalendarApi.getCalendars(m.id);
          return [m.id, r.data.data || []];
        } catch {
          return [m.id, []];
        }
      })
    );
    setCals(Object.fromEntries(entries));
  }, []);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await googleCalendarApi.getStatus();
      const data = res.data.data || [];
      setMedicos(data);
      loadCalendars(data);
    } catch (e) {
      toast.error('No se pudo cargar el estado de Google Calendar');
    } finally {
      setLoading(false);
    }
  }, [loadCalendars]);

  useEffect(() => { if (open) fetchStatus(); }, [open, fetchStatus]);

  const resyncCompleto = async () => {
    setResyncing(true);
    try {
      const res = await googleCalendarApi.resyncFull();
      const d = res.data || {};
      toast.success(`Resincronización completa: ${d.importadas ?? 0} nuevas, ${d.actualizadas ?? 0} actualizadas, ${d.canceladas ?? 0} canceladas`);
      if ((d.errores || []).length > 0) {
        toast.error(`${d.errores.length} médico(s) con error de sincronización`);
      }
      fetchStatus();
    } catch (e) {
      toast.error('No se pudo resincronizar');
    } finally {
      setResyncing(false);
    }
  };

  const elegirCalendario = async (medico, calId) => {
    const cal = (cals[medico.id] || []).find((c) => c.id === calId);
    setSelBusy(medico.id);
    try {
      await googleCalendarApi.selectCalendar(medico.id, calId, cal ? cal.summary : '');
      toast.success(`Calendario actualizado para ${medico.name}. La próxima sincronización traerá todo desde hoy.`);
      setMedicos((prev) => prev.map((x) => (x.id === medico.id ? { ...x, calendar_id: calId, calendar_name: cal ? cal.summary : '' } : x)));
    } catch (e) {
      toast.error('No se pudo actualizar el calendario');
    } finally {
      setSelBusy(null);
    }
  };

  const conectar = async (medico) => {
    setBusy(medico.id);
    try {
      const res = await googleCalendarApi.getConnectUrl(medico.id);
      const url = res.data.authorization_url;
      if (url) {
        // Redirige a la pantalla de consentimiento de Google (vuelve a /agenda?gcal=connected)
        window.location.href = url;
      }
    } catch (e) {
      toast.error('No se pudo iniciar la conexión con Google');
      setBusy(null);
    }
  };

  const desconectar = async (medico) => {
    setBusy(medico.id);
    try {
      await googleCalendarApi.disconnect(medico.id);
      toast.success(`Cuenta de Google desconectada de ${medico.name}`);
      fetchStatus();
    } catch (e) {
      toast.error('No se pudo desconectar');
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl" data-testid="gcal-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarCheck className="w-5 h-5 text-blue-600" />
            Google Calendar por médico
          </DialogTitle>
          <DialogDescription>
            Conecta la cuenta de Google de cada médico y elige el calendario a sincronizar
            (propio o compartido, incluido el principal). Las citas se sincronizan en ambos sentidos.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {loading ? (
            <div className="py-8 text-center text-slate-500">Cargando...</div>
          ) : medicos.length === 0 ? (
            <div className="py-8 text-center text-slate-500">No hay médicos activos.</div>
          ) : (
            medicos.map((m) => (
              <div
                key={m.id}
                className="p-3 rounded-lg border border-slate-200 bg-white"
                data-testid={`gcal-medico-${m.id}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{m.name}</p>
                    <p className="text-xs text-slate-500 truncate">
                      {m.connected ? (
                        <>
                          <Check className="w-3 h-3 inline mr-1 text-green-600" />
                          {m.email || 'Conectado'} · última sync: {fmtFecha(m.last_sync)}
                        </>
                      ) : (
                        'Sin conectar'
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {m.connected ? (
                      <>
                        <Badge className="bg-green-100 text-green-700">Conectado</Badge>
                        <Button
                          variant="outline" size="sm"
                          disabled={busy === m.id}
                          onClick={() => desconectar(m)}
                          data-testid={`gcal-disconnect-${m.id}`}
                        >
                          <Unlink className="w-4 h-4 mr-1" />Desconectar
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        className="bg-blue-600 hover:bg-blue-700"
                        disabled={busy === m.id}
                        onClick={() => conectar(m)}
                        data-testid={`gcal-connect-${m.id}`}
                      >
                        {busy === m.id ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" /> : <Link2 className="w-4 h-4 mr-1" />}
                        Conectar
                      </Button>
                    )}
                  </div>
                </div>

                {m.connected && (
                  <div className="mt-3 flex items-center gap-2">
                    <label className="text-xs text-slate-500 shrink-0">Calendario:</label>
                    <select
                      className="flex-1 text-sm border border-slate-300 rounded-md px-2 py-1.5 bg-white disabled:opacity-60"
                      value={m.calendar_id || 'primary'}
                      disabled={selBusy === m.id}
                      onChange={(e) => elegirCalendario(m, e.target.value)}
                      data-testid={`gcal-calendar-select-${m.id}`}
                    >
                      {(cals[m.id] && cals[m.id].length > 0) ? (
                        cals[m.id].map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.summary}{c.primary ? ' (Principal)' : ''}
                          </option>
                        ))
                      ) : (
                        <option value={m.calendar_id || 'primary'}>
                          {m.calendar_name || 'Principal'}
                        </option>
                      )}
                    </select>
                    {selBusy === m.id && <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500 order-2 sm:order-1">
            ¿Faltan citas de Google? Usa la resincronización completa para recuperarlas.
          </p>
          <Button
            variant="outline"
            onClick={resyncCompleto}
            disabled={resyncing || loading}
            className="order-1 sm:order-2"
            data-testid="gcal-resync-full-button"
          >
            {resyncing ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <History className="w-4 h-4 mr-2" />}
            {resyncing ? 'Resincronizando...' : 'Resincronización completa'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default GoogleCalendarDialog;
