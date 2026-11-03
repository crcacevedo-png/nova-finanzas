import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import axios from 'axios';
import { toast, Toaster } from 'sonner';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger
} from '../components/ui/dialog';
import { Plus, Pencil, Power, Package, Wrench } from 'lucide-react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CatalogSection = ({ tipo, icon: Icon, titulo }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ name: '', note: '' });

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/quirofano/catalog?tipo=${tipo}`);
      setItems(res.data.data || []);
    } catch (e) {
      toast.error('Error al cargar el catálogo');
    } finally {
      setLoading(false);
    }
  }, [tipo]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const openNew = () => { setEditItem(null); setForm({ name: '', note: '' }); setDialogOpen(true); };
  const openEdit = (it) => { setEditItem(it); setForm({ name: it.name, note: it.note || '' }); setDialogOpen(true); };

  const save = async () => {
    if (!form.name.trim()) { toast.error('El nombre es obligatorio'); return; }
    try {
      if (editItem) {
        await axios.put(`${API_URL}/quirofano/catalog/${editItem.id}`, form);
        toast.success('Elemento actualizado');
      } else {
        await axios.post(`${API_URL}/quirofano/catalog`, { tipo, ...form });
        toast.success('Elemento agregado');
      }
      setDialogOpen(false);
      fetchItems();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar');
    }
  };

  const toggleActive = async (it) => {
    try {
      if (it.active) {
        await axios.delete(`${API_URL}/quirofano/catalog/${it.id}`);
      } else {
        await axios.put(`${API_URL}/quirofano/catalog/${it.id}`, { active: true });
      }
      fetchItems();
    } catch (e) {
      toast.error('No se pudo cambiar el estado');
    }
  };

  return (
    <div data-testid={`catalog-section-${tipo}`}>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">Catálogo de {titulo.toLowerCase()} (sin precio)</p>
        <Button onClick={openNew} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid={`catalog-add-${tipo}`}>
          <Plus className="w-4 h-4 mr-2" /> Agregar
        </Button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Nota / Categoría</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((it) => (
              <tr key={it.id} className={it.active ? '' : 'opacity-50'} data-testid={`catalog-row-${it.id}`}>
                <td className="px-4 py-3 font-medium text-gray-900 flex items-center gap-2"><Icon className="w-4 h-4 text-teal-600" />{it.name}</td>
                <td className="px-4 py-3 text-gray-600">{it.note || '—'}</td>
                <td className="px-4 py-3 text-center">
                  <Badge className={it.active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'}>
                    {it.active ? 'Activo' : 'Inactivo'}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right space-x-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(it)} data-testid={`catalog-edit-${it.id}`}><Pencil className="w-4 h-4" /></Button>
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(it)} data-testid={`catalog-toggle-${it.id}`}><Power className="w-4 h-4" /></Button>
                </td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Sin elementos. Agrega el primero.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid={`catalog-dialog-${tipo}`}>
          <DialogHeader><DialogTitle>{editItem ? 'Editar' : 'Agregar'} {titulo.slice(0, -1).toLowerCase()}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Nombre *</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="catalog-name-input" />
            </div>
            <div>
              <Label>Nota / Categoría (opcional)</Label>
              <Input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="catalog-note-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="catalog-save-btn">Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default function InsumosEquiposQuirurgicos() {
  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-4 sm:p-6 max-w-5xl mx-auto" data-testid="insumos-equipos-page">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Insumos y Equipos Quirúrgicos</h1>
        <p className="text-sm text-gray-500 mb-6">Administra las listas que alimentan el registro de cada cirugía.</p>
        <Tabs defaultValue="insumo">
          <TabsList>
            <TabsTrigger value="insumo" data-testid="tab-insumos"><Package className="w-4 h-4 mr-2" />Insumos</TabsTrigger>
            <TabsTrigger value="equipo" data-testid="tab-equipos"><Wrench className="w-4 h-4 mr-2" />Equipos</TabsTrigger>
          </TabsList>
          <TabsContent value="insumo" className="mt-4"><CatalogSection tipo="insumo" icon={Package} titulo="Insumos" /></TabsContent>
          <TabsContent value="equipo" className="mt-4"><CatalogSection tipo="equipo" icon={Wrench} titulo="Equipos" /></TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
