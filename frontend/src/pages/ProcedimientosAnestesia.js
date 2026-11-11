import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import axios from 'axios';
import { toast, Toaster } from 'sonner';
import { formatCurrency } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import { Plus, Pencil, Power, Syringe, Lock, CheckCircle, FileSpreadsheet, FileText, Check, RotateCcw, Filter, X } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const ALL_VALUE = '__all__';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Formatea una fecha "YYYY-MM-DD" (sin componente de hora) sin aplicar conversión de
// zona horaria, para evitar que se muestre el día anterior (mismo criterio que SalaOperaciones.js).
const formatDateOnly = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr + 'T00:00:00');
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear().toString().slice(-2);
  return `${day}/${month}/${year}`;
};

const TiposTab = ({ canManage }) => {
  const [tipos, setTipos] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ name: '', value: '' });

  const fetchTipos = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/quirofano/anesthesia/types`);
      setTipos(res.data.data || []);
    } catch (e) { toast.error('Error al cargar tipos'); }
  }, []);
  useEffect(() => { fetchTipos(); }, [fetchTipos]);

  const openNew = () => { setEditItem(null); setForm({ name: '', value: '' }); setDialogOpen(true); };
  const openEdit = (t) => { setEditItem(t); setForm({ name: t.name, value: String(t.value) }); setDialogOpen(true); };

  const save = async () => {
    if (!form.name.trim()) { toast.error('El nombre es obligatorio'); return; }
    try {
      const payload = { name: form.name, value: parseFloat(form.value) || 0 };
      if (editItem) { await axios.put(`${API_URL}/quirofano/anesthesia/types/${editItem.id}`, payload); toast.success('Tipo actualizado'); }
      else { await axios.post(`${API_URL}/quirofano/anesthesia/types`, payload); toast.success('Tipo agregado'); }
      setDialogOpen(false); fetchTipos();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo guardar'); }
  };

  const toggleActive = async (t) => {
    try {
      if (t.active) await axios.delete(`${API_URL}/quirofano/anesthesia/types/${t.id}`);
      else await axios.put(`${API_URL}/quirofano/anesthesia/types/${t.id}`, { active: true });
      fetchTipos();
    } catch (e) { toast.error('No se pudo cambiar el estado'); }
  };

  return (
    <div data-testid="anesthesia-types-tab">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">Honorario fijo por tipo (igual para todos los anestesiólogos)</p>
        {canManage && (
          <Button onClick={openNew} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="anesthesia-type-add"><Plus className="w-4 h-4 mr-2" />Agregar tipo</Button>
        )}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500">
            <tr><th className="px-4 py-3">Tipo de anestesia</th><th className="px-4 py-3 text-right">Honorario</th><th className="px-4 py-3 text-center">Estado</th>{canManage && <th className="px-4 py-3 text-right">Acciones</th>}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tipos.map((t) => (
              <tr key={t.id} className={t.active ? '' : 'opacity-50'} data-testid={`anesthesia-type-row-${t.id}`}>
                <td className="px-4 py-3 font-medium text-gray-900">{t.name}</td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(t.value)}</td>
                <td className="px-4 py-3 text-center"><Badge className={t.active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'}>{t.active ? 'Activo' : 'Inactivo'}</Badge></td>
                {canManage && (
                  <td className="px-4 py-3 text-right space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(t)} data-testid={`anesthesia-type-edit-${t.id}`}><Pencil className="w-4 h-4" /></Button>
                    <Button variant="ghost" size="sm" onClick={() => toggleActive(t)}><Power className="w-4 h-4" /></Button>
                  </td>
                )}
              </tr>
            ))}
            {tipos.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Sin tipos. Agrega el primero (ej. Tópica, General).</td></tr>}
          </tbody>
        </table>
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="anesthesia-type-dialog">
          <DialogHeader><DialogTitle>{editItem ? 'Editar' : 'Agregar'} tipo de anestesia</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Nombre *</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej: Tópica" data-testid="anesthesia-type-name" /></div>
            <div><Label>Honorario (Q)</Label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="0.00" data-testid="anesthesia-type-value" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="anesthesia-type-save">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const CierreTab = ({ canClose }) => {
  const now = new Date();
  const [month, setMonth] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [medico, setMedico] = useState(ALL_VALUE);
  const [institucion, setInstitucion] = useState(ALL_VALUE);
  const [filtros, setFiltros] = useState({ medicos: [], instituciones: [] });

  const fetchFiltros = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/quirofano/anesthesia/closure/filtros?month=${month}`);
      setFiltros(res.data || { medicos: [], instituciones: [] });
    } catch (e) { /* silencioso: no bloquea la vista principal */ }
  }, [month]);
  useEffect(() => { fetchFiltros(); }, [fetchFiltros]);

  const fetchClosure = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ month });
      if (medico !== ALL_VALUE) params.set('medico', medico);
      if (institucion !== ALL_VALUE) params.set('institucion', institucion);
      const res = await axios.get(`${API_URL}/quirofano/anesthesia/closure?${params.toString()}`);
      setData(res.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al cargar el cierre'); }
    finally { setLoading(false); }
  }, [month, medico, institucion]);
  useEffect(() => { fetchClosure(); }, [fetchClosure]);

  // Al cambiar de mes, los filtros de médico/institución de un mes anterior pueden ya
  // no existir en el mes nuevo; se reinician para evitar un filtro "fantasma".
  useEffect(() => { setMedico(ALL_VALUE); setInstitucion(ALL_VALUE); }, [month]);

  const filtrosActivos = medico !== ALL_VALUE || institucion !== ALL_VALUE;
  const limpiarFiltros = () => { setMedico(ALL_VALUE); setInstitucion(ALL_VALUE); };

  const cerrarMes = async () => {
    if (!window.confirm(`¿Cerrar el mes ${month} y marcar los honorarios como pagados? Esta acción deja el mes de solo lectura.`)) return;
    try {
      await axios.post(`${API_URL}/quirofano/anesthesia/closure/close`, { month });
      toast.success('Mes cerrado y honorarios marcados como pagados');
      fetchClosure();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo cerrar el mes'); }
  };

  const [payingId, setPayingId] = useState(null);
  const marcarPago = async (recordId, paid) => {
    setPayingId(recordId);
    try {
      await axios.post(`${API_URL}/quirofano/anesthesia/records/${recordId}/pagar`, { paid });
      toast.success(paid ? 'Procedimiento marcado como pagado' : 'Pago revertido a pendiente');
      fetchClosure();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo actualizar el pago');
    } finally { setPayingId(null); }
  };

  const [exporting, setExporting] = useState(false);
  const exportar = async (format) => {
    setExporting(true);
    try {
      toast.info(`Generando ${format.toUpperCase()}...`);
      const params = new URLSearchParams({ month, format });
      if (medico !== ALL_VALUE) params.set('medico', medico);
      if (institucion !== ALL_VALUE) params.set('institucion', institucion);
      const res = await axios.get(`${API_URL}/quirofano/anesthesia/closure/export?${params.toString()}`, { responseType: 'blob' });
      const blob = new Blob([res.data], {
        type: format === 'xlsx'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/pdf',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `anestesia_${month}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} descargado`);
    } catch (e) {
      toast.error('No se pudo exportar el cierre');
    } finally { setExporting(false); }
  };

  return (
    <div data-testid="anesthesia-closure-tab">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <Label className="text-sm">Mes:</Label>
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-56 min-w-[14rem]" data-testid="anesthesia-closure-month" />
        </div>
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <Button variant="outline" size="sm" onClick={() => exportar('xlsx')} disabled={exporting || !data?.num_registros} data-testid="anesthesia-export-xlsx">
            <FileSpreadsheet className="w-4 h-4 mr-2 text-emerald-600" />Excel
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportar('pdf')} disabled={exporting || !data?.num_registros} data-testid="anesthesia-export-pdf">
            <FileText className="w-4 h-4 mr-2 text-red-600" />PDF
          </Button>
          {data?.closed ? (
            <Badge variant="outline" className="border-red-300 bg-red-50 text-red-700 py-1.5 px-3" data-testid="anesthesia-month-closed"><Lock className="w-3.5 h-3.5 mr-1" />Mes cerrado (pagado)</Badge>
          ) : canClose ? (
            <Button onClick={cerrarMes} disabled={loading || !data?.num_registros} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="anesthesia-close-month-btn">
              <CheckCircle className="w-4 h-4 mr-2" />Cerrar mes y marcar pagado
            </Button>
          ) : (
            <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-700 py-1.5 px-3">Mes abierto (pendiente de pago)</Badge>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-4 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5">
        <Filter className="w-4 h-4 text-gray-400 shrink-0" />
        <Label className="text-sm text-gray-500 mr-1">Filtrar por:</Label>
        <Select value={medico} onValueChange={setMedico}>
          <SelectTrigger className="w-[220px] bg-white" data-testid="anesthesia-filter-medico">
            <SelectValue placeholder="Médico responsable" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>Todos los médicos</SelectItem>
            {filtros.medicos.map((m) => (<SelectItem key={m} value={m}>{m}</SelectItem>))}
          </SelectContent>
        </Select>
        <Select value={institucion} onValueChange={setInstitucion}>
          <SelectTrigger className="w-[220px] bg-white" data-testid="anesthesia-filter-institucion">
            <SelectValue placeholder="Institución" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>Todas las instituciones</SelectItem>
            {filtros.instituciones.map((inst) => (<SelectItem key={inst} value={inst}>{inst}</SelectItem>))}
          </SelectContent>
        </Select>
        {filtrosActivos && (
          <Button variant="ghost" size="sm" onClick={limpiarFiltros} className="h-8 px-2 text-xs text-gray-500 hover:text-red-600" data-testid="anesthesia-filter-clear">
            <X className="w-3.5 h-3.5 mr-1" />Limpiar filtros
          </Button>
        )}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-gray-500">{filtrosActivos ? 'Total a pagar (filtrado)' : 'Total a pagar del mes'} ({data?.num_pendientes ?? 0} de {data?.num_registros || 0} procedimientos pendientes)</span>
        <div className="flex items-center gap-4">
          {(data?.total_pagado_general || 0) > 0 && (
            <span className="text-sm text-gray-400">Pagado: <span className="font-semibold text-emerald-600">{formatCurrency(data.total_pagado_general)}</span></span>
          )}
          <span className="text-2xl font-bold text-indigo-700" data-testid="anesthesia-total-general">{formatCurrency(data?.total_general || 0)}</span>
        </div>
      </div>
      <div className="space-y-3">
        {(data?.por_anestesiologo || []).map((g, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 overflow-x-auto" data-testid={`anesthesia-anest-${i}`}>
            <div className="flex items-center justify-between mb-2 min-w-[840px]">
              <span className="font-bold text-gray-900">{g.anesthesiologist}</span>
              <span className="font-bold text-emerald-700">{formatCurrency(g.total)} <span className="text-xs font-normal text-gray-400">({g.count - g.count_pagado} de {g.count} pendientes)</span></span>
            </div>
            <table className="w-full text-sm min-w-[840px]">
              <thead>
                <tr className="text-xs text-gray-400 border-b border-gray-100">
                  <th className="py-1.5 text-left font-medium">Fecha</th>
                  <th className="py-1.5 text-left font-medium">Paciente</th>
                  <th className="py-1.5 text-left font-medium">Procedimiento</th>
                  <th className="py-1.5 text-left font-medium">Médico responsable</th>
                  <th className="py-1.5 text-left font-medium">Institución</th>
                  <th className="py-1.5 text-left font-medium">Tipo de anestesia</th>
                  <th className="py-1.5 text-right font-medium">Honorario</th>
                  <th className="py-1.5 text-center font-medium">Pago</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {g.detalle.map((d, j) => (
                  <tr key={j} className={d.paid ? 'opacity-50' : ''} data-testid={`anesthesia-detail-row-${i}-${j}`}>
                    <td className="py-1.5 text-gray-500 whitespace-nowrap">{formatDateOnly(d.date)}</td>
                    <td className="py-1.5 text-gray-900 font-medium">{d.patient_name || '—'}</td>
                    <td className="py-1.5 text-gray-600">{d.procedure || '—'}</td>
                    <td className="py-1.5 text-gray-600">{d.surgeon || '—'}</td>
                    <td className="py-1.5 text-gray-600">{d.institution || '—'}</td>
                    <td className="py-1.5 text-gray-500">{d.tipo}</td>
                    <td className="py-1.5 text-right font-medium">{formatCurrency(d.value)}</td>
                    <td className="py-1.5 text-center">
                      {canClose && !data?.closed ? (
                        d.paid ? (
                          <Button variant="ghost" size="sm" disabled={payingId === d.id} onClick={() => marcarPago(d.id, false)} className="h-7 px-2 text-xs text-gray-500 hover:text-amber-600" data-testid={`unpay-record-${d.id}`}>
                            <RotateCcw className="w-3.5 h-3.5 mr-1" />Pagado
                          </Button>
                        ) : (
                          <Button variant="outline" size="sm" disabled={payingId === d.id} onClick={() => marcarPago(d.id, true)} className="h-7 px-2 text-xs border-emerald-200 text-emerald-700 hover:bg-emerald-50" data-testid={`pay-record-${d.id}`}>
                            <Check className="w-3.5 h-3.5 mr-1" />Marcar pagado
                          </Button>
                        )
                      ) : (
                        <Badge variant="outline" className={d.paid ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}>
                          {d.paid ? 'Pagado' : 'Pendiente'}
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {(data?.por_anestesiologo || []).length === 0 && !loading && (
          <div className="text-center text-gray-400 py-10">
            {filtrosActivos ? 'Sin registros de anestesia con los filtros seleccionados.' : 'Sin registros de anestesia este mes.'}
          </div>
        )}
      </div>
    </div>
  );
};

export default function ProcedimientosAnestesia() {
  const { user } = useAuth();
  const canSeeCierre = ['admin', 'superadmin', 'anestesia'].includes(user?.role);
  const canCloseMonth = ['admin', 'superadmin'].includes(user?.role);
  const canManageTipos = ['admin', 'superadmin', 'usuario'].includes(user?.role);

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-4 sm:p-6 max-w-6xl mx-auto" data-testid="anestesia-page">
        <h1 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2"><Syringe className="w-6 h-6 text-indigo-600" />Procedimientos de Anestesia</h1>
        <p className="text-sm text-gray-500 mb-6">Tipos de anestesia con honorario y cierre mensual de pago por anestesiólogo.</p>
        <Tabs defaultValue={canSeeCierre ? 'cierre' : 'tipos'}>
          <TabsList>
            {canSeeCierre && <TabsTrigger value="cierre" data-testid="tab-cierre">Cierre mensual</TabsTrigger>}
            <TabsTrigger value="tipos" data-testid="tab-tipos">Tipos de anestesia</TabsTrigger>
          </TabsList>
          {canSeeCierre && <TabsContent value="cierre" className="mt-4"><CierreTab canClose={canCloseMonth} /></TabsContent>}
          <TabsContent value="tipos" className="mt-4"><TiposTab canManage={canManageTipos} /></TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
