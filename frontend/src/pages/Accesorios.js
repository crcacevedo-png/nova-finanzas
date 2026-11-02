// Gestión de Inventario de Accesorios - NovaVision
import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import {
  Plus,
  Pencil,
  Trash2,
  RefreshCw,
  Watch,
  Search,
  Package,
  AlertTriangle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
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
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { toast, Toaster } from 'sonner';
import { formatCurrency, margenInfo } from '../services/api';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

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

const EMPTY_FORM = { name: '', brand: '', description: '', cost_price: '', sale_price: '', stock: '' };

const Accesorios = () => {
  const { hasPermission } = useAuth();
  const [accesorios, setAccesorios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLowStock, setShowLowStock] = useState(false);
  const [formData, setFormData] = useState(EMPTY_FORM);

  const canManage = hasPermission('manage_optica_inventory');

  const fetchAccesorios = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/accessories`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      let data = response.data?.data || [];

      if (searchTerm) {
        const q = searchTerm.toLowerCase();
        data = data.filter(a =>
          a.name?.toLowerCase().includes(q) ||
          a.brand?.toLowerCase().includes(q) ||
          a.description?.toLowerCase().includes(q)
        );
      }
      if (showLowStock) {
        data = data.filter(a => a.stock <= 5);
      }
      setAccesorios(data);
    } catch (error) {
      console.error('Error fetching accessories:', error);
      toast.error('Error al cargar accesorios');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, showLowStock]);

  useEffect(() => {
    fetchAccesorios();
  }, [fetchAccesorios]);

  const handleOpenDialog = (item = null) => {
    if (item) {
      setEditing(item);
      setFormData({
        name: item.name || '',
        brand: item.brand || '',
        description: item.description || '',
        cost_price: item.cost_price?.toString() || '',
        sale_price: (item.sale_price || item.price)?.toString() || '',
        stock: item.stock?.toString() || ''
      });
    } else {
      setEditing(null);
      setFormData(EMPTY_FORM);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditing(null);
    setFormData(EMPTY_FORM);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('El nombre es obligatorio');
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
        name: formData.name.trim(),
        brand: formData.brand.trim(),
        description: formData.description.trim(),
        cost_price: parseFloat(formData.cost_price) || 0,
        sale_price: parseFloat(formData.sale_price),
        stock: parseInt(formData.stock) || 0
      };

      if (editing) {
        await axios.put(`${API_URL}/optica/accessories/${editing.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Accesorio actualizado');
      } else {
        await axios.post(`${API_URL}/optica/accessories`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Accesorio creado');
      }

      handleCloseDialog();
      fetchAccesorios();
    } catch (error) {
      console.error('Error saving accessory:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/optica/accessories/${selected.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Accesorio eliminado');
      setDeleteDialogOpen(false);
      setSelected(null);
      fetchAccesorios();
    } catch (error) {
      console.error('Error deleting accessory:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    } finally {
      setSubmitting(false);
    }
  };

  const totalItems = accesorios.length;
  const totalStock = accesorios.reduce((sum, a) => sum + (a.stock || 0), 0);
  const lowStockCount = accesorios.filter(a => a.stock <= 5).length;
  const totalValue = accesorios.reduce((sum, a) => sum + ((a.sale_price || a.price || 0) * (a.stock || 0)), 0);

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-6 space-y-6" data-testid="accesorios-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <Watch className="h-6 w-6 text-amber-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Accesorios
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Gestión de inventario de accesorios de óptica
              </p>
            </div>
          </div>
          {canManage && (
            <Button onClick={() => handleOpenDialog()} className="bg-amber-600 hover:bg-amber-700" data-testid="accesorio-nuevo-btn">
              <Plus className="h-4 w-4 mr-2" /> Nuevo Accesorio
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
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{totalItems}</p>
                </div>
                <Package className="h-8 w-8 text-amber-500" />
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
                <Watch className="h-8 w-8 text-blue-500" />
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
                <Package className="h-8 w-8 text-green-500" />
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
                  placeholder="Buscar por nombre, marca..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="accesorio-search-input"
                />
              </div>

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

              <Button variant="outline" onClick={fetchAccesorios}>
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
            ) : accesorios.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                <Watch className="h-12 w-12 mb-3 opacity-50" />
                <p>No hay accesorios registrados</p>
                {canManage && (
                  <Button className="mt-4" onClick={() => handleOpenDialog()}>
                    <Plus className="h-4 w-4 mr-2" /> Agregar Accesorio
                  </Button>
                )}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Marca</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Costo</TableHead>
                    <TableHead className="text-right">Precio Venta</TableHead>
                    <TableHead className="text-right">Margen</TableHead>
                    <TableHead className="text-center">Stock</TableHead>
                    {canManage && <TableHead className="text-right">Acciones</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {accesorios.map((item) => (
                    <TableRow key={item.id} data-testid={`accesorio-row-${item.id}`}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>{item.brand || '-'}</TableCell>
                      <TableCell className="text-sm text-slate-500 max-w-[200px] truncate">
                        {item.description || '-'}
                      </TableCell>
                      <TableCell className="text-right">{formatCurrency(item.cost_price || 0)}</TableCell>
                      <TableCell className="text-right font-medium text-green-600">
                        {formatCurrency(item.sale_price || item.price || 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {renderMargen(item.cost_price, item.sale_price || item.price)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant={item.stock > 5 ? 'default' : item.stock > 0 ? 'warning' : 'destructive'}>
                          {item.stock || 0}
                        </Badge>
                      </TableCell>
                      {canManage && (
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(item)} data-testid={`accesorio-editar-${item.id}`}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => { setSelected(item); setDeleteDialogOpen(true); }}
                              data-testid={`accesorio-eliminar-${item.id}`}
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
              <DialogTitle>{editing ? 'Editar Accesorio' : 'Nuevo Accesorio'}</DialogTitle>
              <DialogDescription>
                {editing ? 'Modifica los datos del accesorio' : 'Ingresa los datos del nuevo accesorio'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Nombre *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="Ej: Estuche, Paño, Cordón"
                      data-testid="accesorio-name-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="brand">Marca</Label>
                    <Input
                      id="brand"
                      value={formData.brand}
                      onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
                      placeholder="Opcional"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Descripción</Label>
                  <Input
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, cost_price: e.target.value })}
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
                      onChange={(e) => setFormData({ ...formData, sale_price: e.target.value })}
                      placeholder="0.00"
                      data-testid="accesorio-sale-price-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="stock">Stock Inicial</Label>
                    <Input
                      id="stock"
                      type="number"
                      min="0"
                      value={formData.stock}
                      onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                      placeholder="0"
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleCloseDialog}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting} className="bg-amber-600 hover:bg-amber-700" data-testid="accesorio-guardar-btn">
                  {submitting ? 'Guardando...' : (editing ? 'Actualizar' : 'Crear')}
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
                ¿Estás seguro de eliminar el accesorio &quot;{selected?.name}&quot;? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={submitting}>
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Accesorios;
