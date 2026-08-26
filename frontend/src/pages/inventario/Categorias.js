// /app/frontend/src/pages/inventario/Categorias.js
// Gestión de Categorías de Inventario

import React, { useState, useEffect } from 'react';
import Layout from '../../components/Layout';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Switch } from '../../components/ui/switch';
import { 
  Plus, Edit, Trash2, Package, Tag, Pill, Stethoscope, 
  Eye, Glasses, Droplets, Syringe, Bandage, Heart,
  AlertTriangle, GripVertical
} from 'lucide-react';
import { inventarioApi } from '../../services/api';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';

// Iconos disponibles para categorías
const ICONOS_DISPONIBLES = [
  { value: 'package', label: 'Paquete', icon: Package },
  { value: 'tag', label: 'Etiqueta', icon: Tag },
  { value: 'pill', label: 'Píldora', icon: Pill },
  { value: 'stethoscope', label: 'Estetoscopio', icon: Stethoscope },
  { value: 'eye', label: 'Ojo', icon: Eye },
  { value: 'glasses', label: 'Lentes', icon: Glasses },
  { value: 'droplets', label: 'Gotas', icon: Droplets },
  { value: 'syringe', label: 'Jeringa', icon: Syringe },
  { value: 'bandage', label: 'Vendaje', icon: Bandage },
  { value: 'heart', label: 'Corazón', icon: Heart },
];

// Colores disponibles
const COLORES_DISPONIBLES = [
  { value: '#0F6E56', label: 'Verde Institucional' },
  { value: '#3B82F6', label: 'Azul' },
  { value: '#8B5CF6', label: 'Violeta' },
  { value: '#EC4899', label: 'Rosa' },
  { value: '#F97316', label: 'Naranja' },
  { value: '#EAB308', label: 'Amarillo' },
  { value: '#22C55E', label: 'Verde' },
  { value: '#06B6D4', label: 'Cyan' },
  { value: '#6366F1', label: 'Índigo' },
  { value: '#64748B', label: 'Gris' },
];

const getIconComponent = (iconName) => {
  const iconObj = ICONOS_DISPONIBLES.find(i => i.value === iconName);
  return iconObj ? iconObj.icon : Package;
};

const Categorias = () => {
  const { user } = useAuth();
  const canManage = user?.role === 'superadmin' || user?.role === 'admin';
  
  const [loading, setLoading] = useState(true);
  const [categorias, setCategorias] = useState([]);
  
  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCategoria, setEditingCategoria] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Modal eliminar
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [categoriaToDelete, setCategoriaToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  
  // Formulario
  const [formData, setFormData] = useState({
    nombre: '',
    icono: 'package',
    color: '#0F6E56',
    orden: 0,
    activo: true
  });

  useEffect(() => {
    loadCategorias();
  }, []);

  const loadCategorias = async () => {
    try {
      setLoading(true);
      const response = await inventarioApi.getCategorias();
      setCategorias(response.data.data || []);
    } catch (error) {
      console.error('Error cargando categorías:', error);
      toast.error('Error al cargar categorías');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (categoria = null) => {
    if (categoria) {
      setEditingCategoria(categoria);
      setFormData({
        nombre: categoria.nombre || '',
        icono: categoria.icono || 'package',
        color: categoria.color || '#0F6E56',
        orden: categoria.orden || 0,
        activo: categoria.activo !== false
      });
    } else {
      setEditingCategoria(null);
      setFormData({
        nombre: '',
        icono: 'package',
        color: '#0F6E56',
        orden: categorias.length,
        activo: true
      });
    }
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    setSaving(true);
    try {
      if (editingCategoria) {
        await inventarioApi.updateCategoria(editingCategoria.id, formData);
        toast.success('Categoría actualizada');
      } else {
        await inventarioApi.createCategoria(formData);
        toast.success('Categoría creada');
      }
      setModalOpen(false);
      loadCategorias();
    } catch (error) {
      console.error('Error guardando categoría:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar categoría');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (categoria) => {
    setCategoriaToDelete(categoria);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!categoriaToDelete) return;
    
    setDeleting(true);
    try {
      await inventarioApi.deleteCategoria(categoriaToDelete.id);
      toast.success(`Categoría "${categoriaToDelete.nombre}" eliminada`);
      setDeleteModalOpen(false);
      setCategoriaToDelete(null);
      loadCategorias();
    } catch (error) {
      console.error('Error eliminando categoría:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar categoría');
    } finally {
      setDeleting(false);
    }
  };

  if (!canManage) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
            <h2 className="text-xl font-semibold text-gray-800">Acceso Restringido</h2>
            <p className="text-gray-500">Solo administradores pueden gestionar categorías.</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="categorias-inventario">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Categorías de Inventario</h1>
            <p className="text-gray-500">{categorias.length} categorías configuradas</p>
          </div>
          <Button onClick={() => handleOpenModal()} data-testid="btn-nueva-categoria">
            <Plus className="w-4 h-4 mr-2" />
            Nueva Categoría
          </Button>
        </div>

        {/* Lista de Categorías */}
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Cargando categorías...</div>
          ) : categorias.length === 0 ? (
            <div className="p-8 text-center">
              <Tag className="w-12 h-12 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">No hay categorías configuradas</p>
              <Button onClick={() => handleOpenModal()} className="mt-4">
                Crear primera categoría
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {categorias.map((cat, index) => {
                const IconComponent = getIconComponent(cat.icono);
                return (
                  <div 
                    key={cat.id}
                    className={`flex items-center justify-between p-4 hover:bg-gray-50 transition-colors ${!cat.activo ? 'opacity-50 bg-gray-50' : ''}`}
                    data-testid={`categoria-row-${cat.id}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="text-gray-400 cursor-move">
                        <GripVertical className="w-4 h-4" />
                      </div>
                      <div 
                        className="w-10 h-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: `${cat.color}20`, color: cat.color }}
                      >
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{cat.nombre}</p>
                        <p className="text-xs text-gray-500">
                          Orden: {cat.orden} {!cat.activo && '• Inactiva'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-6 h-6 rounded-full border-2 border-white shadow-sm"
                        style={{ backgroundColor: cat.color }}
                        title={cat.color}
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenModal(cat)}
                        data-testid={`btn-edit-${cat.id}`}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(cat)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        data-testid={`btn-delete-${cat.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Crear/Editar */}
        <Dialog open={modalOpen} onOpenChange={setModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>
                {editingCategoria ? 'Editar Categoría' : 'Nueva Categoría'}
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Nombre */}
              <div>
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ej: Medicamentos"
                  data-testid="input-nombre-categoria"
                />
              </div>

              {/* Icono */}
              <div>
                <Label>Icono</Label>
                <div className="grid grid-cols-5 gap-2 mt-2">
                  {ICONOS_DISPONIBLES.map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFormData({ ...formData, icono: value })}
                      className={`p-3 rounded-lg border-2 transition-all ${
                        formData.icono === value 
                          ? 'border-primary bg-primary/10' 
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      title={label}
                    >
                      <Icon className="w-5 h-5 mx-auto" style={{ color: formData.color }} />
                    </button>
                  ))}
                </div>
              </div>

              {/* Color */}
              <div>
                <Label>Color</Label>
                <div className="grid grid-cols-5 gap-2 mt-2">
                  {COLORES_DISPONIBLES.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setFormData({ ...formData, color: value })}
                      className={`w-full h-10 rounded-lg border-2 transition-all ${
                        formData.color === value 
                          ? 'border-gray-800 scale-110' 
                          : 'border-transparent hover:scale-105'
                      }`}
                      style={{ backgroundColor: value }}
                      title={label}
                    />
                  ))}
                </div>
              </div>

              {/* Orden y Activo */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="orden">Orden</Label>
                  <Input
                    id="orden"
                    type="number"
                    value={formData.orden}
                    onChange={(e) => setFormData({ ...formData, orden: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                </div>
                <div className="flex items-center justify-between pt-6">
                  <Label htmlFor="activo">Activa</Label>
                  <Switch
                    id="activo"
                    checked={formData.activo}
                    onCheckedChange={(checked) => setFormData({ ...formData, activo: checked })}
                  />
                </div>
              </div>

              {/* Preview */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 mb-2">Vista previa:</p>
                <div className="flex items-center gap-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${formData.color}20`, color: formData.color }}
                  >
                    {React.createElement(getIconComponent(formData.icono), { className: 'w-5 h-5' })}
                  </div>
                  <span className="font-medium">{formData.nombre || 'Nombre de categoría'}</span>
                </div>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setModalOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={saving} data-testid="btn-guardar-categoria">
                {saving ? 'Guardando...' : (editingCategoria ? 'Actualizar' : 'Crear')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal Eliminar */}
        <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Eliminar Categoría
              </DialogTitle>
              <DialogDescription>
                Esta acción eliminará la categoría permanentemente.
              </DialogDescription>
            </DialogHeader>
            
            {categoriaToDelete && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${categoriaToDelete.color}20`, color: categoriaToDelete.color }}
                  >
                    {React.createElement(getIconComponent(categoriaToDelete.icono), { className: 'w-5 h-5' })}
                  </div>
                  <p className="font-medium text-red-800">{categoriaToDelete.nombre}</p>
                </div>
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteModalOpen(false)}>
                Cancelar
              </Button>
              <Button 
                variant="destructive"
                onClick={handleDeleteConfirm}
                disabled={deleting}
                data-testid="btn-confirmar-eliminar-categoria"
              >
                {deleting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Categorias;
