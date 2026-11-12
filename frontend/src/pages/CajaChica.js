import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { cajaChicaApi, formatCurrency, formatDate, getGuatemalaDate } from '../services/api';
import {
  Plus,
  Pencil,
  Trash2,
  Wallet,
  ArrowUpCircle,
  ArrowDownCircle,
  FileDown,
  FileSpreadsheet,
  Calendar,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { toast, Toaster } from 'sonner';

const EMPTY_FORM = { tipo: 'ingreso', monto: '', fecha: getGuatemalaDate(), solicitante: '', motivo: '' };

const CajaChica = () => {
  const { user, hasPermission } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const puedeEliminar = hasPermission('delete_caja_chica');

  const [resumen, setResumen] = useState({ total_ingresos: 0, total_egresos: 0, saldo: 0 });
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroTipo, setFiltroTipo] = useState('todos');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const [informeOpen, setInformeOpen] = useState(false);
  const [informeMes, setInformeMes] = useState(getGuatemalaDate().slice(0, 7));
  const [informe, setInforme] = useState(null);
  const [cargandoInforme, setCargandoInforme] = useState(false);
  const [descargando, setDescargando] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resResumen, resMovs] = await Promise.all([
        cajaChicaApi.getResumen(),
        cajaChicaApi.getMovimientos(filtroTipo !== 'todos' ? { tipo: filtroTipo } : {}),
      ]);
      setResumen(resResumen.data);
      setMovimientos(resMovs.data.data || []);
    } catch (error) {
      toast.error('No se pudo cargar la información de Caja Chica');
    } finally {
      setLoading(false);
    }
  }, [filtroTipo]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const puedeEditar = (mov) => isSuperAdmin || mov.registrado_por_id === user?.id;

  const abrirNuevo = (tipo) => {
    setEditingId(null);
    setFormData({ ...EMPTY_FORM, tipo });
    setDialogOpen(true);
  };

  const abrirEdicion = (mov) => {
    setEditingId(mov.id);
    setFormData({
      tipo: mov.tipo,
      monto: String(mov.monto),
      fecha: mov.fecha,
      solicitante: mov.solicitante || '',
      motivo: mov.motivo || '',
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.monto || parseFloat(formData.monto) <= 0) {
      toast.error('Ingresa un monto válido');
      return;
    }
    if (!formData.fecha) {
      toast.error('Ingresa la fecha del movimiento');
      return;
    }
    if (formData.tipo === 'egreso' && (!formData.solicitante.trim() || !formData.motivo.trim())) {
      toast.error('Para un egreso, indica quién lo solicitó y el motivo');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        tipo: formData.tipo,
        monto: parseFloat(formData.monto),
        fecha: formData.fecha,
        ...(formData.tipo === 'egreso' ? { solicitante: formData.solicitante.trim(), motivo: formData.motivo.trim() } : {}),
      };
      if (editingId) {
        await cajaChicaApi.update(editingId, payload);
        toast.success('Movimiento actualizado');
      } else {
        await cajaChicaApi.create(payload);
        toast.success(formData.tipo === 'ingreso' ? 'Ingreso registrado' : 'Egreso registrado');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar el movimiento');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await cajaChicaApi.delete(deleteTarget.id);
      toast.success('Movimiento eliminado');
      setDeleteTarget(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo eliminar el movimiento');
    } finally {
      setDeleting(false);
    }
  };

  const abrirInforme = async () => {
    setInformeOpen(true);
    setCargandoInforme(true);
    try {
      const res = await cajaChicaApi.getInforme(informeMes);
      setInforme(res.data);
    } catch (error) {
      toast.error('No se pudo generar el informe');
    } finally {
      setCargandoInforme(false);
    }
  };

  const recargarInforme = async (mes) => {
    setInformeMes(mes);
    setCargandoInforme(true);
    try {
      const res = await cajaChicaApi.getInforme(mes);
      setInforme(res.data);
    } catch (error) {
      toast.error('No se pudo generar el informe');
    } finally {
      setCargandoInforme(false);
    }
  };

  const descargarExcel = async () => {
    setDescargando(true);
    try {
      const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
      const res = await axios.get(`${API_URL}/caja-chica/informe/excel?mes=${informeMes}`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `caja_chica_${informeMes}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Excel descargado');
    } catch (error) {
      toast.error('No se pudo descargar el Excel');
    } finally {
      setDescargando(false);
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="caja-chica-page">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Wallet className="w-6 h-6 text-[#0F6E56]" />
              Caja Chica — Óptica
            </h1>
            <p className="text-slate-500 text-sm">Control de ingresos y egresos de caja chica</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={abrirInforme} data-testid="btn-informe-mensual">
              <FileDown className="w-4 h-4 mr-2" /> Informe mensual
            </Button>
            <Button variant="outline" className="border-rose-200 text-rose-600 hover:bg-rose-50" onClick={() => abrirNuevo('egreso')} data-testid="btn-nuevo-egreso">
              <ArrowDownCircle className="w-4 h-4 mr-2" /> Registrar Egreso
            </Button>
            <Button className="btn-primary" onClick={() => abrirNuevo('ingreso')} data-testid="btn-nuevo-ingreso">
              <Plus className="w-4 h-4 mr-2" /> Registrar Ingreso
            </Button>
          </div>
        </div>

        {/* Saldo prominente */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="border-emerald-100">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total Ingresado</p>
                <p className="text-2xl font-bold text-emerald-600" data-testid="resumen-total-ingresos">{formatCurrency(resumen.total_ingresos)}</p>
              </div>
              <ArrowUpCircle className="w-9 h-9 text-emerald-500" />
            </CardContent>
          </Card>
          <Card className="border-rose-100">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total Egresos</p>
                <p className="text-2xl font-bold text-rose-600" data-testid="resumen-total-egresos">{formatCurrency(resumen.total_egresos)}</p>
              </div>
              <ArrowDownCircle className="w-9 h-9 text-rose-500" />
            </CardContent>
          </Card>
          <Card className="bg-[#0F6E56] border-none shadow-lg">
            <CardContent className="pt-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-100">Saldo Disponible</p>
                <p className="text-3xl font-extrabold text-white" data-testid="resumen-saldo">{formatCurrency(resumen.saldo)}</p>
              </div>
              <Wallet className="w-10 h-10 text-emerald-200" />
            </CardContent>
          </Card>
        </div>

        {/* Historial */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Historial de Movimientos</CardTitle>
            <Select value={filtroTipo} onValueChange={setFiltroTipo}>
              <SelectTrigger className="w-[160px]" data-testid="filtro-tipo-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="ingreso">Ingresos</SelectItem>
                <SelectItem value="egreso">Egresos</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-slate-400 text-sm py-8 text-center">Cargando movimientos...</p>
            ) : movimientos.length === 0 ? (
              <p className="text-slate-400 text-sm py-8 text-center" data-testid="caja-chica-empty-state">No hay movimientos registrados todavía.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Detalle</TableHead>
                    <TableHead>Registrado por</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movimientos.map((mov) => (
                    <TableRow key={mov.id} data-testid={`mov-row-${mov.id}`}>
                      <TableCell>{formatDate(mov.fecha)}</TableCell>
                      <TableCell>
                        {mov.tipo === 'ingreso' ? (
                          <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Ingreso</Badge>
                        ) : (
                          <Badge className="bg-rose-100 text-rose-700 hover:bg-rose-100">Egreso</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">
                        {mov.tipo === 'egreso' ? (
                          <span><strong>{mov.solicitante}</strong> — {mov.motivo}</span>
                        ) : (
                          <span className="text-slate-400">Ingreso a caja chica</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">{mov.registrado_por_nombre}</TableCell>
                      <TableCell className={`text-right font-semibold ${mov.tipo === 'egreso' ? 'text-rose-600' : 'text-emerald-600'}`}>
                        {mov.tipo === 'egreso' ? '-' : '+'}{formatCurrency(mov.monto)}
                      </TableCell>
                      <TableCell className="text-right space-x-1">
                        {puedeEditar(mov) && (
                          <Button variant="ghost" size="icon" onClick={() => abrirEdicion(mov)} data-testid={`btn-editar-${mov.id}`}>
                            <Pencil className="w-4 h-4 text-slate-500" />
                          </Button>
                        )}
                        {puedeEliminar && (
                          <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(mov)} data-testid={`btn-eliminar-${mov.id}`}>
                            <Trash2 className="w-4 h-4 text-rose-500" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Dialog Crear/Editar Movimiento */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="dialog-movimiento-caja-chica">
          <DialogHeader>
            <DialogTitle>
              {editingId ? 'Editar Movimiento' : formData.tipo === 'ingreso' ? 'Registrar Ingreso' : 'Registrar Egreso'}
            </DialogTitle>
            <DialogDescription>
              {formData.tipo === 'ingreso'
                ? 'Monto inicial de caja chica o un refuerzo recibido durante el mes.'
                : 'Dinero solicitado de caja chica.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {formData.tipo === 'egreso' && (
              <>
                <div>
                  <Label>Quién solicitó el dinero *</Label>
                  <Input
                    value={formData.solicitante}
                    onChange={(e) => setFormData({ ...formData, solicitante: e.target.value })}
                    placeholder="Nombre de la persona"
                    data-testid="input-solicitante"
                  />
                </div>
                <div>
                  <Label>Para qué lo solicitó *</Label>
                  <Input
                    value={formData.motivo}
                    onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                    placeholder="Ej. compra de papelería"
                    data-testid="input-motivo"
                  />
                </div>
              </>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Monto (Q) *</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={formData.monto}
                  onChange={(e) => setFormData({ ...formData, monto: e.target.value })}
                  data-testid="input-monto"
                />
              </div>
              <div>
                <Label>Fecha *</Label>
                <Input
                  type="date"
                  value={formData.fecha}
                  onChange={(e) => setFormData({ ...formData, fecha: e.target.value })}
                  data-testid="input-fecha"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} data-testid="btn-cancelar-movimiento">Cancelar</Button>
              <Button type="submit" className="btn-primary" disabled={submitting} data-testid="btn-guardar-movimiento">
                {submitting ? 'Guardando...' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* AlertDialog Eliminar */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent data-testid="dialog-confirmar-eliminar">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar este movimiento?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. El movimiento se eliminará permanentemente del historial de Caja Chica.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="btn-cancelar-eliminar">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleting} className="bg-rose-600 hover:bg-rose-700" data-testid="btn-confirmar-eliminar">
              {deleting ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog Informe Mensual */}
      <Dialog open={informeOpen} onOpenChange={setInformeOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="dialog-informe-mensual">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Calendar className="w-5 h-5" /> Informe de Fin de Mes</DialogTitle>
            <DialogDescription>Resumen de movimientos y saldo acumulado al cierre del mes elegido.</DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-3">
            <Label className="shrink-0">Mes</Label>
            <Input
              type="month"
              value={informeMes}
              onChange={(e) => recargarInforme(e.target.value)}
              className="w-44"
              data-testid="input-mes-informe"
            />
            <Button variant="outline" onClick={descargarExcel} disabled={descargando || !informe} className="ml-auto" data-testid="btn-descargar-excel">
              <FileSpreadsheet className="w-4 h-4 mr-2" /> {descargando ? 'Descargando...' : 'Descargar Excel'}
            </Button>
          </div>

          {cargandoInforme ? (
            <p className="text-slate-400 text-sm py-8 text-center">Generando informe...</p>
          ) : informe ? (
            <div className="space-y-4" data-testid="informe-contenido">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-emerald-50 rounded-lg p-3">
                  <p className="text-xs text-slate-500">Ingresos del mes</p>
                  <p className="text-lg font-bold text-emerald-600">{formatCurrency(informe.total_ingresos_mes)}</p>
                </div>
                <div className="bg-rose-50 rounded-lg p-3">
                  <p className="text-xs text-slate-500">Egresos del mes</p>
                  <p className="text-lg font-bold text-rose-600">{formatCurrency(informe.total_egresos_mes)}</p>
                </div>
                <div className="bg-[#0F6E56]/10 rounded-lg p-3">
                  <p className="text-xs text-slate-500">Saldo acumulado al cierre</p>
                  <p className="text-lg font-bold text-[#0F6E56]">{formatCurrency(informe.saldo_acumulado_fin_mes)}</p>
                </div>
              </div>
              {informe.movimientos.length === 0 ? (
                <p className="text-slate-400 text-sm py-4 text-center">Sin movimientos en este mes.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fecha</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Detalle</TableHead>
                      <TableHead className="text-right">Monto</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {informe.movimientos.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell>{formatDate(m.fecha)}</TableCell>
                        <TableCell>{m.tipo === 'ingreso' ? 'Ingreso' : 'Egreso'}</TableCell>
                        <TableCell className="text-sm text-slate-600">
                          {m.tipo === 'egreso' ? `${m.solicitante} — ${m.motivo}` : '—'}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${m.tipo === 'egreso' ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {m.tipo === 'egreso' ? '-' : '+'}{formatCurrency(m.monto)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default CajaChica;
