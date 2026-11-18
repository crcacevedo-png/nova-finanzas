import React, { useEffect, useState, useCallback } from 'react';
import { backupApi } from '../services/api';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { toast } from 'sonner';
import { DatabaseBackup, Download, Trash2, RefreshCw, Loader2, CheckCircle2, AlertCircle, Clock, HardDriveDownload, RotateCcw } from 'lucide-react';
import { RestaurarRespaldoDialog } from '../components/respaldos/RestaurarRespaldoDialog';

const fmtSize = (bytes) => {
  if (!bytes) return '—';
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(2)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
};

const fmtFecha = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('es-GT', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala',
    });
  } catch { return iso; }
};

const TIPOS = { automatico: 'Automático', manual: 'Manual', previo_restauracion: 'Previo a restaurar' };
const ESTADO_REST = { listo: ['Terminada', 'bg-green-100 text-green-700'], cancelada: ['Cancelada: no se tocó nada', 'bg-amber-100 text-amber-800'],
  error: ['Detenida a medias', 'bg-red-100 text-red-700'], en_curso: ['En curso', 'bg-sky-100 text-sky-700'] };

const Restauraciones = ({ filas }) => (filas.length === 0 ? null : (
  <Card className="p-4" data-testid="restauraciones-recientes">
    <h2 className="text-sm font-semibold mb-2">Restauraciones recientes</h2>
    <ul className="text-xs space-y-1">
      {filas.map((r) => {
        const [txt, cls] = ESTADO_REST[r.estado] || [r.estado, ''];
        return (
          <li key={r.id} className="flex flex-wrap items-center gap-2" data-testid={`restauracion-${r.id}`}>
            <span>{fmtFecha(r.created_at)}</span> · <span>respaldo del {fmtFecha(r.respaldo?.created_at)}</span> ·
            <span>{r.created_by_nombre}</span> <Badge className={cls}>{txt}</Badge>
            {r.segundos != null && <span className="text-muted-foreground">{r.segundos} s</span>}
            {r.error && <span className="text-muted-foreground">{r.error}</span>}
          </li>
        );
      })}
    </ul>
  </Card>
));

const EstadoBadge = ({ status }) => {
  if (status === 'completado') return <Badge className="bg-green-100 text-green-700 gap-1" data-testid="backup-estado-completado"><CheckCircle2 className="w-3 h-3" /> Completado</Badge>;
  if (status === 'error') return <Badge className="bg-red-100 text-red-700 gap-1"><AlertCircle className="w-3 h-3" /> Error</Badge>;
  return <Badge className="bg-amber-100 text-amber-700 gap-1"><Clock className="w-3 h-3" /> En progreso</Badge>;
};

export default function Respaldos() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [restaurarTarget, setRestaurarTarget] = useState(null);
  const [restauraciones, setRestauraciones] = useState([]);

  const cargar = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [{ data }, rest] = await Promise.all([backupApi.getAll(), backupApi.restauraciones()]);
      setBackups(data.data || []);
      setRestauraciones(rest.data.data || []);
    } catch (e) {
      if (!silent) toast.error('No se pudieron cargar los respaldos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);
  const refrescar = useCallback(() => cargar(true), [cargar]);

  // Auto-refresco mientras haya alguno en progreso
  useEffect(() => {
    const hayEnProgreso = backups.some((b) => b.status === 'en_progreso');
    if (!hayEnProgreso) return;
    const t = setInterval(() => cargar(true), 4000);
    return () => clearInterval(t);
  }, [backups, cargar]);

  const crearAhora = async () => {
    setRunning(true);
    try {
      await backupApi.run();
      toast.success('Respaldo iniciado. Aparecerá en la lista en unos segundos.');
      await cargar(true);
    } catch (e) {
      toast.error('No se pudo iniciar el respaldo');
    } finally {
      setRunning(false);
    }
  };

  const descargar = async (b) => {
    setDownloadingId(b.id);
    try {
      const { data } = await backupApi.download(b.id);
      const url = window.URL.createObjectURL(new Blob([data], { type: 'application/gzip' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = b.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error('No se pudo descargar el respaldo');
    } finally {
      setDownloadingId(null);
    }
  };

  const confirmarEliminar = async () => {
    if (!deleteTarget) return;
    try {
      await backupApi.remove(deleteTarget.id);
      toast.success('Respaldo eliminado de la lista');
      setDeleteTarget(null);
      await cargar(true);
    } catch (e) {
      toast.error('No se pudo eliminar el respaldo');
    }
  };

  return (
    <div className="space-y-6" data-testid="respaldos-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <DatabaseBackup className="w-7 h-7" /> Respaldos
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Copia de seguridad de toda la base de datos. Se genera automáticamente cada semana (domingos). Descárgalos a una unidad externa y elimina los más antiguos cuando quieras.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => cargar()} data-testid="backup-refresh-btn">
            <RefreshCw className="w-4 h-4 mr-2" /> Actualizar
          </Button>
          <Button onClick={crearAhora} disabled={running} data-testid="backup-run-btn">
            {running ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <DatabaseBackup className="w-4 h-4 mr-2" />}
            Crear respaldo ahora
          </Button>
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left">
                <th className="px-4 py-3 font-semibold">Archivo</th>
                <th className="px-4 py-3 font-semibold">Tipo</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 font-semibold">Fecha</th>
                <th className="px-4 py-3 font-semibold">Documentos</th>
                <th className="px-4 py-3 font-semibold">Tamaño</th>
                <th className="px-4 py-3 font-semibold text-right">Acciones</th>
              </tr>
            </thead>
            <tbody data-testid="backup-list">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin inline mr-2" /> Cargando...
                </td></tr>
              ) : backups.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">
                  Aún no hay respaldos. El primero se generará automáticamente el próximo domingo, o puedes crear uno ahora.
                </td></tr>
              ) : backups.map((b) => (
                <tr key={b.id} className="border-b hover:bg-muted/20" data-testid={`backup-row-${b.id}`}>
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    <HardDriveDownload className="w-4 h-4 text-muted-foreground" /> {b.filename}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{TIPOS[b.tipo] || 'Manual'}</Badge>
                  </td>
                  <td className="px-4 py-3"><EstadoBadge status={b.status} /></td>
                  <td className="px-4 py-3 whitespace-nowrap">{fmtFecha(b.created_at)}</td>
                  <td className="px-4 py-3">{b.documents_count ? b.documents_count.toLocaleString('es-GT') : '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{fmtSize(b.size)}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm" variant="outline"
                        disabled={b.status !== 'completado' || downloadingId === b.id}
                        onClick={() => descargar(b)}
                        data-testid={`backup-download-${b.id}`}
                      >
                        {downloadingId === b.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                      </Button>
                      <Button
                        size="sm" variant="outline"
                        disabled={b.status !== 'completado'}
                        onClick={() => setRestaurarTarget(b)}
                        title="Restaurar este respaldo"
                        data-testid={`backup-restaurar-${b.id}`}
                      >
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm" variant="outline"
                        className="text-red-600 hover:text-red-700"
                        onClick={() => setDeleteTarget(b)}
                        data-testid={`backup-delete-${b.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Restauraciones filas={restauraciones} />

      <RestaurarRespaldoDialog respaldo={restaurarTarget} onClose={() => setRestaurarTarget(null)} onTerminado={refrescar} />

      <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent data-testid="backup-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar respaldo</AlertDialogTitle>
            <AlertDialogDescription>
              Se quitará <b>{deleteTarget?.filename}</b> de la lista. Asegúrate de haberlo descargado si quieres conservarlo. Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="backup-delete-cancel">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmarEliminar} className="bg-red-600 hover:bg-red-700" data-testid="backup-delete-confirm">
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
