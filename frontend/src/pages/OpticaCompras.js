import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  RefreshCw,
  Search,
  Eye,
  Pencil,
  Trash2,
  Receipt,
  TrendingUp,
  Package,
  Calendar
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
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
import { toast, Toaster } from 'sonner';
import { 
  opticaPurchaseApi,
  supplierApi,
  formatCurrency, 
  formatDate,
  getGuatemalaDate
} from '../services/api';

const categoryLabels = {
  aros: 'Aros',
  lentes_contacto: 'Lentes de Contacto',
  cristales: 'Cristales',
  accesorios: 'Accesorios',
  insumos: 'Insumos',
  otros: 'Otros'
};

const OpticaCompras = () => {
  const { hasPermission } = useAuth();
  const [purchases, setPurchases] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState(null);
  const [selectedPurchase, setSelectedPurchase] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  
  const [formData, setFormData] = useState({
    supplier_id: '',
    category: 'aros',
    description: '',
    quantity: 1,
    unit_price: '',
    total: '',
    invoice_number: '',
    purchase_date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  const canManage = hasPermission('manage_optica_inventory');

  // Stats
  const totalCompras = purchases.reduce((sum, p) => sum + (p.total || 0), 0);
  const totalMes = purchases.filter(p => {
    const purchaseDate = new Date(p.purchase_date);
    const [gy, gm] = getGuatemalaDate().split('-').map(Number);
    return purchaseDate.getMonth() === (gm - 1) && purchaseDate.getFullYear() === gy;
  }).reduce((sum, p) => sum + (p.total || 0), 0);

  const fetchPurchases = useCallback(async () => {
    try {
      setLoading(true);
      const response = await opticaPurchaseApi.getAll({
        search: searchTerm,
        category: categoryFilter === 'all' ? undefined : categoryFilter
      });
      setPurchases(response.data.data || []);
    } catch (error) {
      console.error('Error fetching purchases:', error);
      toast.error('Error al cargar las compras');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, categoryFilter]);

  const fetchSuppliers = useCallback(async () => {
    try {
      const response = await supplierApi.getAll();
      setSuppliers(response.data.data || []);
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    }
  }, []);

  useEffect(() => {
    fetchPurchases();
    fetchSuppliers();
  }, [fetchPurchases, fetchSuppliers]);

  const resetForm = () => {
    setFormData({
      supplier_id: '',
      category: 'aros',
      description: '',
      quantity: 1,
      unit_price: '',
      total: '',
      invoice_number: '',
      purchase_date: getGuatemalaDate(),
      notes: ''
    });
    setEditingPurchase(null);
  };

  const handleOpenDialog = (purchase = null) => {
    if (purchase) {
      setEditingPurchase(purchase);
      setFormData({
        supplier_id: purchase.supplier_id || '',
        category: purchase.category,
        description: purchase.description,
        quantity: purchase.quantity,
        unit_price: purchase.unit_price.toString(),
        total: purchase.total.toString(),
        invoice_number: purchase.invoice_number || '',
        purchase_date: purchase.purchase_date.split('T')[0],
        notes: purchase.notes || ''
      });
    } else {
      resetForm();
    }
    setDialogOpen(true);
  };

  const handleViewDetail = (purchase) => {
    setSelectedPurchase(purchase);
    setDetailDialogOpen(true);
  };

  const calculateTotal = (quantity, unitPrice) => {
    const qty = parseFloat(quantity) || 0;
    const price = parseFloat(unitPrice) || 0;
    return (qty * price).toFixed(2);
  };

  const handleQuantityChange = (value) => {
    const newTotal = calculateTotal(value, formData.unit_price);
    setFormData(prev => ({ ...prev, quantity: value, total: newTotal }));
  };

  const handleUnitPriceChange = (value) => {
    const newTotal = calculateTotal(formData.quantity, value);
    setFormData(prev => ({ ...prev, unit_price: value, total: newTotal }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.description.trim()) {
      toast.error('La descripción es obligatoria');
      return;
    }
    if (!formData.total || parseFloat(formData.total) <= 0) {
      toast.error('El total debe ser mayor a 0');
      return;
    }

    const payload = {
      supplier_id: formData.supplier_id || null,
      category: formData.category,
      description: formData.description.trim(),
      quantity: parseInt(formData.quantity) || 1,
      unit_price: parseFloat(formData.unit_price) || 0,
      total: parseFloat(formData.total),
      invoice_number: formData.invoice_number.trim() || null,
      purchase_date: formData.purchase_date,
      notes: formData.notes.trim()
    };

    setSubmitting(true);
    try {
      if (editingPurchase) {
        await opticaPurchaseApi.update(editingPurchase.id, payload);
        toast.success('Compra actualizada exitosamente');
      } else {
        await opticaPurchaseApi.create(payload);
        toast.success('Compra registrada exitosamente');
      }
      setDialogOpen(false);
      resetForm();
      fetchPurchases();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedPurchase) return;
    
    setSubmitting(true);
    try {
      await opticaPurchaseApi.delete(selectedPurchase.id);
      toast.success('Compra eliminada exitosamente');
      setDeleteDialogOpen(false);
      setSelectedPurchase(null);
      fetchPurchases();
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
      <div className="space-y-6 animate-fade-in" data-testid="optica-compras-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Compras de Óptica
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Registro de compras e insumos de óptica
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchPurchases} className="btn-outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canManage && (
              <Button onClick={() => handleOpenDialog()} className="btn-primary" data-testid="new-purchase-button">
                <Plus className="w-4 h-4 mr-2" />
                Nueva Compra
              </Button>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-100">
                <Receipt className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Compras</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(totalCompras)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-100">
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Compras del Mes</p>
                <p className="text-2xl font-bold text-blue-600">{formatCurrency(totalMes)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-purple-100">
                <Package className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Registros</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{purchases.length}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por descripción o factura..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                  data-testid="search-purchase"
                />
              </div>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-[180px] input-teal">
                  <SelectValue placeholder="Categoría" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {Object.entries(categoryLabels).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Compras ({purchases.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : purchases.length === 0 ? (
              <div className="p-12 text-center">
                <Receipt className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay compras registradas</p>
                {canManage && (
                  <Button onClick={() => handleOpenDialog()} className="btn-primary mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Registrar primera compra
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Fecha</TableHead>
                      <TableHead className="table-header">Categoría</TableHead>
                      <TableHead className="table-header">Descripción</TableHead>
                      <TableHead className="table-header">Proveedor</TableHead>
                      <TableHead className="table-header text-right">Cantidad</TableHead>
                      <TableHead className="table-header text-right">Total</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {purchases.map((purchase) => (
                      <TableRow key={purchase.id} className="table-row-hover" data-testid={`purchase-row-${purchase.id}`}>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {formatDate(purchase.purchase_date)}
                        </TableCell>
                        <TableCell>
                          <Badge className="bg-indigo-100 text-indigo-700">
                            {categoryLabels[purchase.category] || purchase.category}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                            {purchase.description}
                          </span>
                          {purchase.invoice_number && (
                            <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                              Factura: {purchase.invoice_number}
                            </p>
                          )}
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {purchase.supplier_name || '-'}
                        </TableCell>
                        <TableCell className="text-right" style={{ color: 'var(--text-secondary)' }}>
                          {purchase.quantity}
                        </TableCell>
                        <TableCell className="text-right font-semibold" style={{ color: 'var(--primary-teal)' }}>
                          {formatCurrency(purchase.total)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetail(purchase)}
                              className="h-8 w-8 p-0 hover:bg-blue-100 hover:text-blue-600"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {canManage && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleOpenDialog(purchase)}
                                  className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                >
                                  <Pencil className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => { setSelectedPurchase(purchase); setDeleteDialogOpen(true); }}
                                  className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </>
                            )}
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
          <DialogContent className="sm:max-w-[550px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingPurchase ? 'Editar Compra' : 'Nueva Compra'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingPurchase ? 'Actualiza los datos de la compra' : 'Registra una nueva compra de óptica'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Fecha *</Label>
                  <Input
                    type="date"
                    value={formData.purchase_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, purchase_date: e.target.value }))}
                    className="input-teal"
                    data-testid="purchase-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Categoría *</Label>
                  <Select value={formData.category} onValueChange={(v) => setFormData(prev => ({ ...prev, category: v }))}>
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(categoryLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Descripción *</Label>
                <Input
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Aros Ray-Ban modelo RB5154"
                  data-testid="purchase-description"
                />
              </div>
              <div className="space-y-2">
                <Label>Proveedor</Label>
                <Select value={formData.supplier_id || "none"} onValueChange={(v) => setFormData(prev => ({ ...prev, supplier_id: v === "none" ? "" : v }))}>
                  <SelectTrigger className="input-teal">
                    <SelectValue placeholder="Seleccionar proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin proveedor</SelectItem>
                    {suppliers.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Cantidad</Label>
                  <Input
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => handleQuantityChange(e.target.value)}
                    className="input-teal"
                    data-testid="purchase-quantity"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Precio Unitario</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.unit_price}
                    onChange={(e) => handleUnitPriceChange(e.target.value)}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="purchase-unit-price"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Total *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={formData.total}
                    onChange={(e) => setFormData(prev => ({ ...prev, total: e.target.value }))}
                    className="input-teal font-semibold"
                    placeholder="0.00"
                    data-testid="purchase-total"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>No. Factura</Label>
                <Input
                  value={formData.invoice_number}
                  onChange={(e) => setFormData(prev => ({ ...prev, invoice_number: e.target.value }))}
                  className="input-teal"
                  placeholder="Opcional"
                  data-testid="purchase-invoice"
                />
              </div>
              <div className="space-y-2">
                <Label>Notas</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  className="input-teal"
                  placeholder="Observaciones adicionales"
                  rows={2}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="submit-purchase">
                  {submitting ? 'Guardando...' : (editingPurchase ? 'Guardar' : 'Registrar')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Detalle de Compra</DialogTitle>
            </DialogHeader>
            {selectedPurchase && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Fecha</p>
                    <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {formatDate(selectedPurchase.purchase_date)}
                    </p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Categoría</p>
                    <Badge className="bg-indigo-100 text-indigo-700">
                      {categoryLabels[selectedPurchase.category]}
                    </Badge>
                  </div>
                  <div className="col-span-2">
                    <p style={{ color: 'var(--text-hint)' }}>Descripción</p>
                    <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {selectedPurchase.description}
                    </p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Proveedor</p>
                    <p style={{ color: 'var(--text-primary)' }}>
                      {selectedPurchase.supplier_name || '-'}
                    </p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>No. Factura</p>
                    <p style={{ color: 'var(--text-primary)' }}>
                      {selectedPurchase.invoice_number || '-'}
                    </p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Cantidad</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPurchase.quantity}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Precio Unitario</p>
                    <p style={{ color: 'var(--text-primary)' }}>{formatCurrency(selectedPurchase.unit_price)}</p>
                  </div>
                  <div className="col-span-2">
                    <p style={{ color: 'var(--text-hint)' }}>Total</p>
                    <p className="text-xl font-bold" style={{ color: 'var(--primary-teal)' }}>
                      {formatCurrency(selectedPurchase.total)}
                    </p>
                  </div>
                  {selectedPurchase.notes && (
                    <div className="col-span-2">
                      <p style={{ color: 'var(--text-hint)' }}>Notas</p>
                      <p style={{ color: 'var(--text-secondary)' }}>{selectedPurchase.notes}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setDetailDialogOpen(false)} className="btn-outline">
                Cerrar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Compra</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar esta compra? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={submitting} data-testid="confirm-delete-purchase">
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default OpticaCompras;
