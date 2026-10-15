import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Glasses,
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
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { toast, Toaster } from 'sonner';
import { frameApi, formatCurrency, margenInfo } from '../services/api';

const renderMargen = (cost, sale) => {
  const m = margenInfo(cost, sale);
  if (!m) return <span style={{ color: 'var(--text-secondary)' }}>-</span>;
  const color = m.monto >= 0 ? '#0F6E56' : '#DC2626';
  return (
    <span className="font-medium" style={{ color }}>
      {formatCurrency(m.monto)} <span className="text-xs">({m.pct.toFixed(0)}%)</span>
    </span>
  );
};

const OpticaInventario = () => {
  const { user, hasPermission } = useAuth();
  const [frames, setFrames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingFrame, setEditingFrame] = useState(null);
  const [selectedFrame, setSelectedFrame] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLowStock, setShowLowStock] = useState(false);
  
  const [formData, setFormData] = useState({
    brand: '',
    code: '',
    model: '',
    color: '',
    cost_price: '',
    sale_price: '',
    stock: ''
  });

  const canManage = hasPermission('manage_optica_inventory');

  const fetchFrames = useCallback(async () => {
    try {
      setLoading(true);
      const response = await frameApi.getAll({ search: searchTerm, low_stock: showLowStock });
      setFrames(response.data.data || []);
    } catch (error) {
      console.error('Error fetching frames:', error);
      toast.error('Error al cargar el inventario');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, showLowStock]);

  useEffect(() => {
    fetchFrames();
  }, [fetchFrames]);

  const handleOpenDialog = (frame = null) => {
    if (frame) {
      setEditingFrame(frame);
      setFormData({
        brand: frame.brand,
        code: frame.code,
        model: frame.model || '',
        color: frame.color || '',
        cost_price: frame.cost_price.toString(),
        sale_price: frame.sale_price.toString(),
        stock: frame.stock.toString()
      });
    } else {
      setEditingFrame(null);
      setFormData({
        brand: '',
        code: '',
        model: '',
        color: '',
        cost_price: '',
        sale_price: '',
        stock: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.brand.trim() || !formData.code.trim()) {
      toast.error('Marca y código son obligatorios');
      return;
    }
    if (!formData.cost_price || !formData.sale_price || !formData.stock) {
      toast.error('Precios y stock son obligatorios');
      return;
    }

    const payload = {
      brand: formData.brand,
      code: formData.code,
      model: formData.model,
      color: formData.color,
      cost_price: parseFloat(formData.cost_price),
      sale_price: parseFloat(formData.sale_price),
      stock: parseInt(formData.stock)
    };

    setSubmitting(true);
    try {
      if (editingFrame) {
        await frameApi.update(editingFrame.id, payload);
        toast.success('Aro actualizado exitosamente');
      } else {
        await frameApi.create(payload);
        toast.success('Aro creado exitosamente');
      }
      setDialogOpen(false);
      fetchFrames();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedFrame) return;
    
    setSubmitting(true);
    try {
      await frameApi.delete(selectedFrame.id);
      toast.success('Aro eliminado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedFrame(null);
      fetchFrames();
    } catch (error) {
      toast.error('Error al eliminar el aro');
    } finally {
      setSubmitting(false);
    }
  };

  const totalStock = frames.reduce((sum, f) => sum + f.stock, 0);
  const lowStockCount = frames.filter(f => f.stock <= 5).length;
  const totalValue = frames.reduce((sum, f) => sum + (f.sale_price * f.stock), 0);

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="optica-inventario-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Inventario de Aros
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestiona el inventario de armazones
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchFrames} className="btn-outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canManage && (
              <Button onClick={() => handleOpenDialog()} className="btn-primary" data-testid="add-frame-button">
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Aro
              </Button>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-100">
                <Package className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total en Stock</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{totalStock}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-amber-100">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Stock Bajo</p>
                <p className="text-2xl font-bold text-amber-600">{lowStockCount}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-emerald-100">
                <Glasses className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Valor Inventario</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(totalValue)}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filters */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por marca, código o modelo..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                  data-testid="search-frame"
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
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Aros ({frames.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : frames.length === 0 ? (
              <div className="p-12 text-center">
                <Glasses className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay aros en el inventario</p>
                {canManage && (
                  <Button onClick={() => handleOpenDialog()} className="btn-primary mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer aro
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Código</TableHead>
                      <TableHead className="table-header">Marca</TableHead>
                      <TableHead className="table-header">Modelo</TableHead>
                      <TableHead className="table-header">Color</TableHead>
                      <TableHead className="table-header text-right">Costo</TableHead>
                      <TableHead className="table-header text-right">Venta</TableHead>
                      <TableHead className="table-header text-right">Margen</TableHead>
                      <TableHead className="table-header text-center">Stock</TableHead>
                      {canManage && <TableHead className="table-header text-right">Acciones</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {frames.map((frame) => (
                      <TableRow key={frame.id} className="table-row-hover" data-testid={`frame-row-${frame.id}`}>
                        <TableCell>
                          <span className="font-mono text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                            {frame.code}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{frame.brand}</span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>{frame.model || '-'}</TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>{frame.color || '-'}</TableCell>
                        <TableCell className="text-right" style={{ color: 'var(--text-secondary)' }}>
                          {formatCurrency(frame.cost_price)}
                        </TableCell>
                        <TableCell className="text-right font-semibold" style={{ color: 'var(--primary-teal)' }}>
                          {formatCurrency(frame.sale_price)}
                        </TableCell>
                        <TableCell className="text-right" data-testid={`frame-margen-${frame.id}`}>
                          {renderMargen(frame.cost_price, frame.sale_price)}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className={frame.stock <= 5 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}>
                            {frame.stock}
                          </Badge>
                        </TableCell>
                        {canManage && (
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenDialog(frame)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setSelectedFrame(frame); setDeleteDialogOpen(true); }}
                                className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
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
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingFrame ? 'Editar Aro' : 'Nuevo Aro'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingFrame ? 'Actualiza los datos del aro' : 'Ingresa los datos del nuevo aro'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="brand">Marca *</Label>
                  <Input
                    id="brand"
                    value={formData.brand}
                    onChange={(e) => setFormData(prev => ({ ...prev, brand: e.target.value }))}
                    className="input-teal"
                    placeholder="Ej: Ray-Ban"
                    data-testid="frame-brand"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="code">Código *</Label>
                  <Input
                    id="code"
                    value={formData.code}
                    onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                    className="input-teal"
                    placeholder="Ej: RB-001"
                    data-testid="frame-code"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="model">Modelo</Label>
                  <Input
                    id="model"
                    value={formData.model}
                    onChange={(e) => setFormData(prev => ({ ...prev, model: e.target.value }))}
                    className="input-teal"
                    placeholder="Ej: Aviator"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="color">Color</Label>
                  <Input
                    id="color"
                    value={formData.color}
                    onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                    className="input-teal"
                    placeholder="Ej: Dorado"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cost_price">Precio Costo *</Label>
                  <Input
                    id="cost_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.cost_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, cost_price: e.target.value }))}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="frame-cost"
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
                    onChange={(e) => setFormData(prev => ({ ...prev, sale_price: e.target.value }))}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="frame-sale"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="stock">Stock *</Label>
                  <Input
                    id="stock"
                    type="number"
                    min="0"
                    value={formData.stock}
                    onChange={(e) => setFormData(prev => ({ ...prev, stock: e.target.value }))}
                    className="input-teal"
                    placeholder="0"
                    data-testid="frame-stock"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="submit-frame">
                  {submitting ? 'Guardando...' : (editingFrame ? 'Guardar' : 'Crear')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Aro</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar &quot;{selectedFrame?.brand} - {selectedFrame?.code}&quot;?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
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

export default OpticaInventario;
