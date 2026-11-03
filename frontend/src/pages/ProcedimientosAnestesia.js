import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import axios from 'axios';
import { toast, Toaster } from 'sonner';
import { formatCurrency } from '../services/api';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import { Plus, Pencil, Power, Syringe, Lock, CheckCircle } from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TiposTab = () => {
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
        <Button onClick={openNew} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="anesthesia-type-add"><Plus className="w-4 h-4 mr-2" />Agregar tipo</Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500">
            <tr><th className="px-4 py-3">Tipo de anestesia</th><th className="px-4 py-3 text-right">Honorario</th><th className="px-4 py-3 text-center">Estado</th><th className="px-4 py-3 text-right">Acciones</th></tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tipos.map((t) => (
              <tr key={t.id} className={t.active ? '' : 'opacity-50'} data-testid={`anesthesia-type-row-${t.id}`}>
                <td className="px-4 py-3 font-medium text-gray-900">{t.name}</td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(t.value)}</td>
                <td className="px-4 py-3 text-center"><Badge className={t.active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'}>{t.active ? 'Activo' : 'Inactivo'}</Badge></td>
                <td className="px-4 py-3 text-right space-x-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(t)} data-testid={`anesthesia-type-edit-${t.id}`}><Pencil className="w-4 h-4" /></Button>
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(t)}><Power className="w-4 h-4" /></Button>
                </td>
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

const CierreTab = () => {
  const now = new Date();
  const [month, setMonth] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchClosure = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/quirofano/anesthesia/closure?month=${month}`);
      setData(res.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al cargar el cierre'); }
    finally { setLoading(false); }
  }, [month]);
  useEffect(() => { fetchClosure(); }, [fetchClosure]);

  const cerrarMes = async () => {
    if (!window.confirm(`¿Cerrar el mes ${month} y marcar los honorarios como pagados? Esta acción deja el mes de solo lectura.`)) return;
    try {
      await axios.post(`${API_URL}/quirofano/anesthesia/closure/close`, { month });
      toast.success('Mes cerrado y honorarios marcados como pagados');
      fetchClosure();
    } catch (e) { toast.error(e.response?.data?.detail || 'No se pudo cerrar el mes'); }
  };

  return (
    <div data-testid="anesthesia-closure-tab">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Label className="text-sm">Mes:</Label>
          <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" data-testid="anesthesia-closure-month" />
        </div>
        <div className="flex items-center gap-2">
          {data?.closed ? (
            <Badge variant="outline" className="border-red-300 bg-red-50 text-red-700 py-1.5 px-3" data-testid="anesthesia-month-closed"><Lock className="w-3.5 h-3.5 mr-1" />Mes cerrado (pagado)</Badge>
          ) : (
            <Button onClick={cerrarMes} disabled={loading || !data?.num_registros} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="anesthesia-close-month-btn">
              <CheckCircle className="w-4 h-4 mr-2" />Cerrar mes y marcar pagado
            </Button>
          )}
        </div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center justify-between">
        <span className="text-sm text-gray-500">Total a pagar del mes ({data?.num_registros || 0} procedimientos)</span>
        <span className="text-2xl font-bold text-indigo-700" data-testid="anesthesia-total-general">{formatCurrency(data?.total_general || 0)}</span>
      </div>
      <div className="space-y-3">
        {(data?.por_anestesiologo || []).map((g, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 p-4" data-testid={`anesthesia-anest-${i}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-gray-900">{g.anesthesiologist}</span>
              <span className="font-bold text-emerald-700">{formatCurrency(g.total)} <span className="text-xs font-normal text-gray-400">({g.count} proc.)</span></span>
            </div>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-50">
                {g.tipos.map((t, j) => (
                  <tr key={j}>
                    <td className="py-1.5 text-gray-600">{t.tipo}</td>
                    <td className="py-1.5 text-center text-gray-500">{t.count} × {formatCurrency(t.value)}</td>
                    <td className="py-1.5 text-right font-medium">{formatCurrency(t.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {(data?.por_anestesiologo || []).length === 0 && !loading && (
          <div className="text-center text-gray-400 py-10">Sin registros de anestesia este mes.</div>
        )}
      </div>
    </div>
  );
};

export default function ProcedimientosAnestesia() {
  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-4 sm:p-6 max-w-5xl mx-auto" data-testid="anestesia-page">
        <h1 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2"><Syringe className="w-6 h-6 text-indigo-600" />Procedimientos de Anestesia</h1>
        <p className="text-sm text-gray-500 mb-6">Tipos de anestesia con honorario y cierre mensual de pago por anestesiólogo.</p>
        <Tabs defaultValue="cierre">
          <TabsList>
            <TabsTrigger value="cierre" data-testid="tab-cierre">Cierre mensual</TabsTrigger>
            <TabsTrigger value="tipos" data-testid="tab-tipos">Tipos de anestesia</TabsTrigger>
          </TabsList>
          <TabsContent value="cierre" className="mt-4"><CierreTab /></TabsContent>
          <TabsContent value="tipos" className="mt-4"><TiposTab /></TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
