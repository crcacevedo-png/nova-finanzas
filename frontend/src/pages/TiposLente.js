import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Eye,
  Search
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import { lensTypeApi, formatCurrency } from '../services/api';

const TiposLente = () => {
  const { hasPermission } = useAuth();
  const [lensTypes, setLensTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingLensType, setEditingLensType] = useState(null);
  const [selectedLensType, setSelectedLensType] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    cost_price: '',
    default_price: ''
  });

  const canManage = hasPermission('manage_optica_inventory');

  const fetchLensTypes = useCallback(async () => {
    try {
      setLoading(true);
      const response = await lensTypeApi.getAll();
      let data = response.data.data || [];
      // Filtrar por búsqueda local
      if (searchTerm) {
        data = data.filter(lt => 
          lt.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (lt.description && lt.description.toLowerCase().includes(searchTerm.toLowerCase()))
        );
      }
      setLensTypes(data);
    } catch (error) {
      console.error('Error fetching lens types:', error);
      toast.error('Error al cargar tipos de lente');
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    fetchLensTypes();
  }, [fetchLensTypes]);

  const handleOpenDialog = (lensType = null) => {
    if (lensType) {
      setEditingLensType(lensType);
      setFormData({
        name: lensType.name,
        description: lensType.description || '',
        cost_price: lensType.cost_price?.toString() || '',
        default_price: lensType.default_price.toString()
      });
    } else {
      setEditingLensType(null);
      setFormData({
        name: '',
        description: '',
        cost_price: '',
        default_price: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (!formData.default_price) {
      toast.error('El precio de venta es obligatorio');
      return;
    }

    const payload = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      cost_price: formData.cost_price ? parseFloat(formData.cost_price) : null,
      default_price: parseFloat(formData.default_price)
    };

    setSubmitting(true);
    try {
      if (editingLensType) {
        await lensTypeApi.update(editingLensType.id, payload);
        toast.success('Tipo de lente actualizado exitosamente');
      } else {
        await lensTypeApi.create(payload);
        toast.success('Tipo de lente creado exitosamente');
      }
      setDialogOpen(false);
      fetchLensTypes();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedLensType) return;
    
    setSubmitting(true);
    try {
      await lensTypeApi.delete(selectedLensType.id);
      toast.success('Tipo de lente eliminado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedLensType(null);
      fetchLensTypes();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="tipos-lente-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Tipos de Lente
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Catálogo de tipos de lentes oftálmicos
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchLensTypes} className="btn-outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canManage && (
              <Button onClick={() => handleOpenDialog()} className="btn-primary" data-testid="add-lens-type-button">
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Tipo
              </Button>
            )}
          </div>
        </div>

        {/* Stats */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-indigo-100">
              <Eye className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Tipos de Lente</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{lensTypes.length}</p>
            </div>
          </CardContent>
        </Card>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por nombre..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-teal pl-10"
                data-testid="search-lens-type"
              />
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Catálogo de Tipos de Lente ({lensTypes.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : lensTypes.length === 0 ? (
              <div className="p-12 text-center">
                <Eye className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay tipos de lente registrados</p>
                {canManage && (
                  <Button onClick={() => handleOpenDialog()} className="btn-primary mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer tipo
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Descripción</TableHead>
                      <TableHead className="table-header text-right">Costo</TableHead>
                      <TableHead className="table-header text-right">Precio Venta</TableHead>
                      {canManage && <TableHead className="table-header text-right">Acciones</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lensTypes.map((lensType) => (
                      <TableRow key={lensType.id} className="table-row-hover" data-testid={`lens-type-row-${lensType.id}`}>
                        <TableCell>
                          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                            {lensType.name}
                          </span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {lensType.description || '-'}
                        </TableCell>
                        <TableCell className="text-right" style={{ color: 'var(--text-secondary)' }}>
                          {lensType.cost_price ? formatCurrency(lensType.cost_price) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-semibold" style={{ color: 'var(--primary-teal)' }}>
                          {formatCurrency(lensType.default_price)}
                        </TableCell>
                        {canManage && (
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenDialog(lensType)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                data-testid={`edit-lens-type-${lensType.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setSelectedLensType(lensType); setDeleteDialogOpen(true); }}
                                className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                                data-testid={`delete-lens-type-${lensType.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingLensType ? 'Editar Tipo de Lente' : 'Nuevo Tipo de Lente'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingLensType ? 'Actualiza los datos del tipo de lente' : 'Ingresa los datos del nuevo tipo'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Monofocal"
                  data-testid="lens-type-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Descripción</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input-teal"
                  placeholder="Descripción del tipo de lente"
                  data-testid="lens-type-description"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cost_price">Precio Costo</Label>
                  <Input
                    id="cost_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.cost_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, cost_price: e.target.value }))}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="lens-type-cost"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="default_price">Precio Venta *</Label>
                  <Input
                    id="default_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.default_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, default_price: e.target.value }))}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="lens-type-price"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="submit-lens-type">
                  {submitting ? 'Guardando...' : (editingLensType ? 'Guardar' : 'Crear')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Tipo de Lente</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar "{selectedLensType?.name}"?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={submitting} data-testid="confirm-delete-lens-type">
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default TiposLente;
