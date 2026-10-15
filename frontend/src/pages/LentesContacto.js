// Gestión de Inventario de Lentes de Contacto - NovaVision
import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  CircleDot,
  Search,
  Package,
  AlertTriangle
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { toast, Toaster } from 'sonner';
import { formatCurrency, margenInfo } from '../services/api';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Tipos de lentes de contacto
const TIPOS_LENTE_CONTACTO = [
  { value: 'esferico', label: 'Esférico' },
  { value: 'torico', label: 'Tórico (Astigmatismo)' },
  { value: 'multifocal', label: 'Multifocal' },
  { value: 'cosmetico', label: 'Cosmético' },
];

const renderMargen = (cost, sale) => {
  const m = margenInfo(cost, sale);
  if (!m) return <span className="text-slate-400">-</span>;
  const color = m.monto >= 0 ? '#0F6E56' : '#DC2626';
  return (
    <span className="font-medium" style={{ color }}>
      {formatCurrency(m.monto)} <span className="text-xs">({m.pct.toFixed(0)}%)</span>
    </span>
  );
};

const LentesContacto = () => {
  const { hasPermission } = useAuth();
  const [lenses, setLenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingLens, setEditingLens] = useState(null);
  const [selectedLens, setSelectedLens] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLowStock, setShowLowStock] = useState(false);
  const [filterType, setFilterType] = useState('all');
  
  const [formData, setFormData] = useState({
    lens_type: 'esferico',
    brand: '',
    name: '',
    description: '',
    cost_price: '',
    sale_price: '',
    stock: ''
  });

  const canManage = hasPermission('manage_optica_inventory');

  const fetchLenses = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/contact-lenses`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      let data = response.data?.data || [];
      
      // Filtrar por búsqueda
      if (searchTerm) {
        data = data.filter(lens => 
          lens.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          lens.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          lens.description?.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }
      
      // Filtrar por tipo
      if (filterType !== 'all') {
        data = data.filter(lens => lens.lens_type === filterType);
      }
      
      // Filtrar por stock bajo
      if (showLowStock) {
        data = data.filter(lens => lens.stock <= 5);
      }
      
      setLenses(data);
    } catch (error) {
      console.error('Error fetching contact lenses:', error);
      toast.error('Error al cargar lentes de contacto');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, showLowStock, filterType]);

  useEffect(() => {
    fetchLenses();
  }, [fetchLenses]);

  const handleOpenDialog = (lens = null) => {
    if (lens) {
      setEditingLens(lens);
      setFormData({
        lens_type: lens.lens_type || 'esferico',
        brand: lens.brand || '',
        name: lens.name || '',
        description: lens.description || '',
        cost_price: lens.cost_price?.toString() || '',
        sale_price: (lens.sale_price || lens.price)?.toString() || '',
        stock: lens.stock?.toString() || ''
      });
    } else {
      setEditingLens(null);
      setFormData({
        lens_type: 'esferico',
        brand: '',
        name: '',
        description: '',
        cost_price: '',
        sale_price: '',
        stock: ''
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingLens(null);
    setFormData({
      lens_type: 'esferico',
      brand: '',
      name: '',
      description: '',
      cost_price: '',
      sale_price: '',
      stock: ''
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.brand.trim() || !formData.name.trim()) {
      toast.error('Marca y nombre son obligatorios');
      return;
    }
    
    if (!formData.sale_price || parseFloat(formData.sale_price) < 0) {
      toast.error('Precio de venta debe ser un número válido');
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        lens_type: formData.lens_type,
        brand: formData.brand.trim(),
        name: formData.name.trim(),
        description: formData.description.trim(),
        cost_price: parseFloat(formData.cost_price) || 0,
        sale_price: parseFloat(formData.sale_price),
        stock: parseInt(formData.stock) || 0
      };

      if (editingLens) {
        await axios.put(`${API_URL}/optica/contact-lenses/${editingLens.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Lente de contacto actualizado');
      } else {
        await axios.post(`${API_URL}/optica/contact-lenses`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Lente de contacto creado');
      }
      
      handleCloseDialog();
      fetchLenses();
    } catch (error) {
      console.error('Error saving contact lens:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedLens) return;
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/optica/contact-lenses/${selectedLens.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Lente de contacto eliminado');
      setDeleteDialogOpen(false);
      setSelectedLens(null);
      fetchLenses();
    } catch (error) {
      console.error('Error deleting contact lens:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    } finally {
      setSubmitting(false);
    }
  };

  const getTipoLabel = (tipo) => {
    const found = TIPOS_LENTE_CONTACTO.find(t => t.value === tipo);
    return found ? found.label : tipo;
  };

  // Calcular resumen
  const totalLenses = lenses.length;
  const totalStock = lenses.reduce((sum, l) => sum + (l.stock || 0), 0);
  const lowStockCount = lenses.filter(l => l.stock <= 5).length;
  const totalValue = lenses.reduce((sum, l) => sum + ((l.sale_price || l.price || 0) * (l.stock || 0)), 0);

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-6 space-y-6" data-testid="lentes-contacto-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <CircleDot className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Lentes de Contacto
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Gestión de inventario de lentes de contacto
              </p>
            </div>
          </div>
          {canManage && (
            <Button onClick={() => handleOpenDialog()} className="bg-green-600 hover:bg-green-700">
              <Plus className="h-4 w-4 mr-2" /> Nuevo Lente
            </Button>
          )}
        </div>

        {/* Resumen */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Productos</p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{totalLenses}</p>
                </div>
                <Package className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Unidades en Stock</p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{totalStock}</p>
                </div>
                <CircleDot className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Stock Bajo</p>
                  <p className="text-2xl font-bold text-amber-500">{lowStockCount}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-amber-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Valor Inventario</p>
                  <p className="text-2xl font-bold text-green-500">{formatCurrency(totalValue)}</p>
                </div>
                <CircleDot className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filtros */}
        <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Buscar por marca, nombre..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Tipo de lente" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  {TIPOS_LENTE_CONTACTO.map(tipo => (
                    <SelectItem key={tipo.value} value={tipo.value}>{tipo.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <div className="flex items-center gap-2">
                <Checkbox 
                  id="lowStock" 
                  checked={showLowStock}
                  onCheckedChange={setShowLowStock}
                />
                <Label htmlFor="lowStock" className="text-sm cursor-pointer">
                  Solo stock bajo (≤5)
                </Label>
              </div>
              
              <Button variant="outline" onClick={fetchLenses}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla */}
        <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-4 space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : lenses.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                <CircleDot className="h-12 w-12 mb-3 opacity-50" />
                <p>No hay lentes de contacto registrados</p>
                {canManage && (
                  <Button className="mt-4" onClick={() => handleOpenDialog()}>
                    <Plus className="h-4 w-4 mr-2" /> Agregar Lente
                  </Button>
                )}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Marca</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Costo</TableHead>
                    <TableHead className="text-right">Precio Venta</TableHead>
                    <TableHead className="text-right">Margen</TableHead>
                    <TableHead className="text-center">Stock</TableHead>
                    {canManage && <TableHead className="text-right">Acciones</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lenses.map((lens) => (
                    <TableRow key={lens.id}>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {getTipoLabel(lens.lens_type)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{lens.brand}</TableCell>
                      <TableCell>{lens.name}</TableCell>
                      <TableCell className="text-sm text-slate-500 max-w-[200px] truncate">
                        {lens.description || '-'}
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(lens.cost_price || 0)}</TableCell>
                      <TableCell className="text-right font-medium text-green-600">
                        {formatCurrency(lens.sale_price || lens.price || 0)}
                      </TableCell>
                      <TableCell className="text-right" data-testid={`contact-lens-margen-${lens.id}`}>
                        {renderMargen(lens.cost_price, lens.sale_price || lens.price)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge 
                          variant={lens.stock > 5 ? 'default' : lens.stock > 0 ? 'warning' : 'destructive'}
                        >
                          {lens.stock || 0}
                        </Badge>
                      </TableCell>
                      {canManage && (
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(lens)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => {
                                setSelectedLens(lens);
                                setDeleteDialogOpen(true);
                              }}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Dialog Crear/Editar */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>
                {editingLens ? 'Editar Lente de Contacto' : 'Nuevo Lente de Contacto'}
              </DialogTitle>
              <DialogDescription>
                {editingLens ? 'Modifica los datos del lente' : 'Ingresa los datos del nuevo lente de contacto'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="lens_type">Tipo de Lente *</Label>
                    <Select 
                      value={formData.lens_type} 
                      onValueChange={(v) => setFormData({...formData, lens_type: v})}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar tipo" />
                      </SelectTrigger>
                      <SelectContent>
                        {TIPOS_LENTE_CONTACTO.map(tipo => (
                          <SelectItem key={tipo.value} value={tipo.value}>{tipo.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="brand">Marca *</Label>
                    <Input
                      id="brand"
                      value={formData.brand}
                      onChange={(e) => setFormData({...formData, brand: e.target.value})}
                      placeholder="Ej: Acuvue, Air Optix"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="name">Nombre del Producto *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="Ej: Oasys 1-Day, Dailies Total 1"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="description">Descripción</Label>
                  <Input
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="Descripción opcional"
                  />
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="cost_price">Precio Costo</Label>
                    <Input
                      id="cost_price"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.cost_price}
                      onChange={(e) => setFormData({...formData, cost_price: e.target.value})}
                      placeholder="0.00"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sale_price">Precio Venta *</Label>
                    <Input
                      id="sale_price"
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.sale_price}
                      onChange={(e) => setFormData({...formData, sale_price: e.target.value})}
                      placeholder="0.00"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stock">Stock Inicial</Label>
                    <Input
                      id="stock"
                      type="number"
                      min="0"
                      value={formData.stock}
                      onChange={(e) => setFormData({...formData, stock: e.target.value})}
                      placeholder="0"
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleCloseDialog}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting} className="bg-green-600 hover:bg-green-700">
                  {submitting ? 'Guardando...' : (editingLens ? 'Actualizar' : 'Crear')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Dialog Confirmar Eliminación */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar Eliminación</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de eliminar el lente &quot;{selectedLens?.brand} {selectedLens?.name}&quot;? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete}
                disabled={submitting}
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

export default LentesContacto;
