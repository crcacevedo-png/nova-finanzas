import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Users,
  Phone,
  User
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
import { supplierApi } from '../services/api';

const Proveedores = () => {
  const { user } = useAuth();
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    contact_name: '',
    phone: ''
  });

  const fetchSuppliers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await supplierApi.getAll();
      setSuppliers(response.data.data || []);
    } catch (error) {
      console.error('Error fetching suppliers:', error);
      toast.error('Error al cargar los proveedores');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  const handleOpenDialog = (supplier = null) => {
    if (supplier) {
      setEditingSupplier(supplier);
      setFormData({
        name: supplier.name,
        contact_name: supplier.contact_name || '',
        phone: supplier.phone || ''
      });
    } else {
      setEditingSupplier(null);
      setFormData({
        name: '',
        contact_name: '',
        phone: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre del proveedor es obligatorio');
      return;
    }

    setSubmitting(true);
    try {
      if (editingSupplier) {
        await supplierApi.update(editingSupplier.id, formData);
        toast.success('Proveedor actualizado exitosamente');
      } else {
        await supplierApi.create(formData);
        toast.success('Proveedor creado exitosamente');
      }
      setDialogOpen(false);
      fetchSuppliers();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar el proveedor';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedSupplier) return;
    
    setSubmitting(true);
    try {
      await supplierApi.delete(selectedSupplier.id);
      toast.success('Proveedor eliminado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedSupplier(null);
      fetchSuppliers();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar el proveedor';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredSuppliers = suppliers.filter(supplier =>
    supplier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (supplier.contact_name && supplier.contact_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="proveedores-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Proveedores
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestiona los proveedores de la clínica
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline"
              onClick={fetchSuppliers}
              className="btn-outline"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            <Button 
              onClick={() => handleOpenDialog()}
              className="btn-primary"
              data-testid="add-supplier-button"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Proveedor
            </Button>
          </div>
        </div>

        {/* Summary Card */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-teal-100">
              <Users className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Proveedores</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {suppliers.length}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <Input
              placeholder="Buscar por nombre o contacto..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-teal max-w-md"
              data-testid="search-supplier"
            />
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Proveedores
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : filteredSuppliers.length === 0 ? (
              <div className="p-12 text-center">
                <Users className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {searchTerm ? 'No se encontraron proveedores' : 'No hay proveedores registrados'}
                </p>
                {!searchTerm && (
                  <Button 
                    onClick={() => handleOpenDialog()}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer proveedor
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Contacto</TableHead>
                      <TableHead className="table-header">Teléfono</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSuppliers.map((supplier) => (
                      <TableRow 
                        key={supplier.id} 
                        className="table-row-hover"
                        data-testid={`supplier-row-${supplier.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-teal-50">
                              <Users className="w-4 h-4 text-teal-600" />
                            </div>
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {supplier.name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {supplier.contact_name ? (
                            <div className="flex items-center gap-2">
                              <User className="w-4 h-4" style={{ color: 'var(--text-hint)' }} />
                              <span style={{ color: 'var(--text-secondary)' }}>
                                {supplier.contact_name}
                              </span>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {supplier.phone ? (
                            <div className="flex items-center gap-2">
                              <Phone className="w-4 h-4" style={{ color: 'var(--text-hint)' }} />
                              <span style={{ color: 'var(--text-secondary)' }}>
                                {supplier.phone}
                              </span>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(supplier)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`edit-supplier-${supplier.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedSupplier(supplier);
                                setDeleteDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                              data-testid={`delete-supplier-${supplier.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
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
                {editingSupplier ? 'Editar Proveedor' : 'Nuevo Proveedor'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingSupplier 
                  ? 'Actualiza los datos del proveedor'
                  : 'Ingresa los datos del nuevo proveedor'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre del proveedor *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Laboratorios Visión S.A."
                  data-testid="supplier-name-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="contact_name">Nombre del contacto</Label>
                <Input
                  id="contact_name"
                  value={formData.contact_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, contact_name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Juan Pérez"
                  data-testid="supplier-contact-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="phone">Número de teléfono</Label>
                <Input
                  id="phone"
                  value={formData.phone}
                  onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: 5555-1234"
                  data-testid="supplier-phone-input"
                />
              </div>

              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setDialogOpen(false)} 
                  className="btn-outline"
                >
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={submitting}
                  data-testid="submit-supplier-button"
                >
                  {submitting 
                    ? (editingSupplier ? 'Guardando...' : 'Creando...') 
                    : (editingSupplier ? 'Guardar cambios' : 'Crear proveedor')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Eliminar Proveedor
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar al proveedor "{selectedSupplier?.name}"? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => setDeleteDialogOpen(false)} 
                className="btn-outline"
              >
                Cancelar
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete}
                disabled={submitting}
                data-testid="confirm-delete-button"
              >
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Proveedores;
