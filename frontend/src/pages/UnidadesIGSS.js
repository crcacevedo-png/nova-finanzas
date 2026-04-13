import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Building,
  AlertCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
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
import { igssUnitApi } from '../services/api';

const UnidadesIGSS = () => {
  const { user } = useAuth();
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState(null);
  const [selectedUnit, setSelectedUnit] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    description: ''
  });

  const isSuperAdmin = user?.role === 'superadmin';

  const fetchUnits = useCallback(async () => {
    try {
      setLoading(true);
      const response = await igssUnitApi.getAll();
      setUnits(response.data.data || []);
    } catch (error) {
      console.error('Error fetching IGSS units:', error);
      toast.error('Error al cargar las unidades IGSS');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUnits();
  }, [fetchUnits]);

  const handleOpenDialog = (unit = null) => {
    if (unit) {
      setEditingUnit(unit);
      setFormData({
        name: unit.name,
        code: unit.code || '',
        description: unit.description || ''
      });
    } else {
      setEditingUnit(null);
      setFormData({
        name: '',
        code: '',
        description: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre de la unidad es obligatorio');
      return;
    }

    setSubmitting(true);
    try {
      if (editingUnit) {
        await igssUnitApi.update(editingUnit.id, formData);
        toast.success('Unidad IGSS actualizada exitosamente');
      } else {
        await igssUnitApi.create(formData);
        toast.success('Unidad IGSS creada exitosamente');
      }
      setDialogOpen(false);
      fetchUnits();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar la unidad IGSS';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedUnit) return;
    
    setSubmitting(true);
    try {
      await igssUnitApi.delete(selectedUnit.id);
      toast.success('Unidad IGSS eliminada exitosamente');
      setDeleteDialogOpen(false);
      setSelectedUnit(null);
      fetchUnits();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar la unidad IGSS';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUnits = units.filter(unit =>
    unit.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (unit.code && unit.code.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (!isSuperAdmin) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <AlertCircle className="w-12 h-12 text-amber-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">Acceso Restringido</h2>
          <p className="text-gray-500">Solo el SuperAdmin puede gestionar el catálogo de Unidades IGSS.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="unidades-igss-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Unidades IGSS
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Catálogo de unidades del Instituto Guatemalteco de Seguridad Social
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline"
              onClick={fetchUnits}
              className="btn-outline"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            <Button 
              onClick={() => handleOpenDialog()}
              className="btn-primary"
              data-testid="add-unit-button"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nueva Unidad
            </Button>
          </div>
        </div>

        {/* Summary Card */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-green-100">
              <Building className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Unidades IGSS</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {units.length}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <Input
              placeholder="Buscar por nombre o código..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-teal max-w-md"
              data-testid="search-unit"
            />
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Unidades IGSS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : filteredUnits.length === 0 ? (
              <div className="p-12 text-center">
                <Building className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {searchTerm ? 'No se encontraron unidades' : 'No hay unidades IGSS registradas'}
                </p>
                {!searchTerm && (
                  <Button 
                    onClick={() => handleOpenDialog()}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primera unidad
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Código</TableHead>
                      <TableHead className="table-header">Descripción</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUnits.map((unit) => (
                      <TableRow 
                        key={unit.id} 
                        className="table-row-hover"
                        data-testid={`unit-row-${unit.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-green-50">
                              <Building className="w-4 h-4 text-green-600" />
                            </div>
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {unit.name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {unit.code ? (
                            <span className="font-mono text-sm" style={{ color: 'var(--text-secondary)' }}>
                              {unit.code}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {unit.description || '-'}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(unit)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`edit-unit-${unit.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedUnit(unit);
                                setDeleteDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                              data-testid={`delete-unit-${unit.id}`}
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

        {/* Info Card */}
        <Card className="card-teal border-l-4 border-l-green-500">
          <CardContent className="p-4">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              <strong>Nota:</strong> Este catálogo permite administrar las unidades del IGSS que pueden ser asignadas 
              a pacientes cuando su institución referente es "IGSS". El catálogo inicia vacío y puede ser 
              completado según las necesidades de la clínica.
            </p>
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingUnit ? 'Editar Unidad IGSS' : 'Nueva Unidad IGSS'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingUnit 
                  ? 'Actualiza los datos de la unidad IGSS'
                  : 'Ingresa los datos de la nueva unidad IGSS'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre de la Unidad *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Hospital General de Enfermedades"
                  data-testid="unit-name-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="code">Código (opcional)</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: HGE-001"
                  data-testid="unit-code-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Descripción (opcional)</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input-teal"
                  placeholder="Descripción o ubicación de la unidad"
                  data-testid="unit-description-input"
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
                  data-testid="submit-unit-button"
                >
                  {submitting 
                    ? (editingUnit ? 'Guardando...' : 'Creando...') 
                    : (editingUnit ? 'Guardar cambios' : 'Crear unidad')}
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
                Eliminar Unidad IGSS
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar la unidad "{selectedUnit?.name}"? 
                Esta acción no se puede deshacer.
                <br /><br />
                <strong className="text-amber-600">Nota:</strong> No se podrá eliminar si hay pacientes usando esta unidad.
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

export default UnidadesIGSS;
