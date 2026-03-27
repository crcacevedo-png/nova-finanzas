import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { expenseApi, formatCurrency, formatDate, categoryLabels, statusLabels } from '../services/api';
import { 
  Plus, 
  Search, 
  Filter,
  Pencil,
  Trash2,
  X,
  Calendar
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';

const initialFormState = {
  concepto: '',
  monto: '',
  fecha: new Date().toISOString().split('T')[0],
  categoria: 'gastos_fijos',
  estado: 'pendiente',
  fecha_vencimiento: '',
  proveedor: '',
  notas: ''
};

const Gastos = () => {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [expenseToDelete, setExpenseToDelete] = useState(null);
  const [formData, setFormData] = useState(initialFormState);
  const [submitting, setSubmitting] = useState(false);
  const [filters, setFilters] = useState({ categoria: '', estado: '', search: '' });

  useEffect(() => {
    fetchExpenses();
  }, [filters.categoria, filters.estado]);

  const fetchExpenses = async () => {
    try {
      const response = await expenseApi.getAll({
        categoria: filters.categoria || undefined,
        estado: filters.estado || undefined
      });
      setExpenses(response.data);
    } catch (error) {
      console.error('Error fetching expenses:', error);
      toast.error('Error al cargar los gastos');
    } finally {
      setLoading(false);
    }
  };

  const filteredExpenses = expenses.filter(expense => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return expense.concepto.toLowerCase().includes(searchLower) ||
             expense.proveedor?.toLowerCase().includes(searchLower);
    }
    return true;
  });

  const handleOpenDialog = (expense = null) => {
    if (expense) {
      setEditingExpense(expense);
      setFormData({
        concepto: expense.concepto,
        monto: expense.monto.toString(),
        fecha: expense.fecha.split('T')[0],
        categoria: expense.categoria,
        estado: expense.estado,
        fecha_vencimiento: expense.fecha_vencimiento?.split('T')[0] || '',
        proveedor: expense.proveedor || '',
        notas: expense.notas || ''
      });
    } else {
      setEditingExpense(null);
      setFormData(initialFormState);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingExpense(null);
    setFormData(initialFormState);
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.concepto || !formData.monto || !formData.fecha) {
      toast.error('Por favor completa los campos requeridos');
      return;
    }

    setSubmitting(true);
    try {
      const data = {
        ...formData,
        monto: parseFloat(formData.monto),
        fecha_vencimiento: formData.fecha_vencimiento || null
      };

      if (editingExpense) {
        await expenseApi.update(editingExpense.id, data);
        toast.success('Gasto actualizado correctamente');
      } else {
        await expenseApi.create(data);
        toast.success('Gasto registrado correctamente');
      }

      handleCloseDialog();
      fetchExpenses();
    } catch (error) {
      console.error('Error saving expense:', error);
      toast.error('Error al guardar el gasto');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteClick = (expense) => {
    setExpenseToDelete(expense);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!expenseToDelete) return;

    try {
      await expenseApi.delete(expenseToDelete.id);
      toast.success('Gasto eliminado correctamente');
      fetchExpenses();
    } catch (error) {
      console.error('Error deleting expense:', error);
      toast.error('Error al eliminar el gasto');
    } finally {
      setDeleteDialogOpen(false);
      setExpenseToDelete(null);
    }
  };

  const getStatusBadge = (estado) => {
    if (estado === 'pagado') {
      return <Badge className="badge-success">{statusLabels[estado]}</Badge>;
    }
    return <Badge className="badge-warning">{statusLabels[estado]}</Badge>;
  };

  const getCategoryBadge = (categoria) => {
    const colors = {
      gastos_fijos: 'badge-info',
      pagos_proveedores: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
      gastos_variables: 'bg-amber-50 text-amber-700 border border-amber-200'
    };
    return <Badge className={colors[categoria]}>{categoryLabels[categoria]}</Badge>;
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="gastos-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Gastos</h1>
            <p className="text-slate-500 text-sm">Administra los gastos de la clínica</p>
          </div>
          <Button 
            onClick={() => handleOpenDialog()}
            className="bg-teal-800 hover:bg-teal-900 text-white"
            data-testid="add-expense-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Gasto
          </Button>
        </div>

        {/* Filters */}
        <Card className="border border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Buscar por concepto o proveedor..."
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <Select
                value={filters.categoria}
                onValueChange={(value) => setFilters(prev => ({ ...prev, categoria: value }))}
              >
                <SelectTrigger className="w-full md:w-[200px]" data-testid="category-filter">
                  <SelectValue placeholder="Categoría" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todas las categorías</SelectItem>
                  <SelectItem value="gastos_fijos">Gastos Fijos</SelectItem>
                  <SelectItem value="pagos_proveedores">Pagos Proveedores</SelectItem>
                  <SelectItem value="gastos_variables">Gastos Variables</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={filters.estado}
                onValueChange={(value) => setFilters(prev => ({ ...prev, estado: value }))}
              >
                <SelectTrigger className="w-full md:w-[180px]" data-testid="status-filter">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos los estados</SelectItem>
                  <SelectItem value="pendiente">Pendiente</SelectItem>
                  <SelectItem value="pagado">Pagado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="border border-slate-200">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : filteredExpenses.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-slate-500">No se encontraron gastos</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead className="font-semibold text-slate-600">Concepto</TableHead>
                      <TableHead className="font-semibold text-slate-600">Monto</TableHead>
                      <TableHead className="font-semibold text-slate-600">Fecha</TableHead>
                      <TableHead className="font-semibold text-slate-600">Categoría</TableHead>
                      <TableHead className="font-semibold text-slate-600">Estado</TableHead>
                      <TableHead className="font-semibold text-slate-600">Vencimiento</TableHead>
                      <TableHead className="font-semibold text-slate-600 text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredExpenses.map((expense) => (
                      <TableRow 
                        key={expense.id} 
                        className="table-row-hover"
                        data-testid={`expense-row-${expense.id}`}
                      >
                        <TableCell>
                          <div>
                            <p className="font-medium text-slate-900">{expense.concepto}</p>
                            {expense.proveedor && (
                              <p className="text-xs text-slate-500">{expense.proveedor}</p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="font-semibold text-slate-900">
                          {formatCurrency(expense.monto)}
                        </TableCell>
                        <TableCell className="text-slate-600">
                          {formatDate(expense.fecha)}
                        </TableCell>
                        <TableCell>{getCategoryBadge(expense.categoria)}</TableCell>
                        <TableCell>{getStatusBadge(expense.estado)}</TableCell>
                        <TableCell className="text-slate-600">
                          {expense.fecha_vencimiento ? formatDate(expense.fecha_vencimiento) : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(expense)}
                              className="h-8 w-8 p-0 hover:bg-teal-50 hover:text-teal-700"
                              data-testid={`edit-expense-${expense.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(expense)}
                              className="h-8 w-8 p-0 hover:bg-rose-50 hover:text-rose-700"
                              data-testid={`delete-expense-${expense.id}`}
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
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">
                {editingExpense ? 'Editar Gasto' : 'Nuevo Gasto'}
              </DialogTitle>
              <DialogDescription>
                {editingExpense 
                  ? 'Modifica los datos del gasto' 
                  : 'Completa los datos para registrar un nuevo gasto'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="concepto">Concepto *</Label>
                <Input
                  id="concepto"
                  value={formData.concepto}
                  onChange={(e) => handleInputChange('concepto', e.target.value)}
                  placeholder="Descripción del gasto"
                  data-testid="expense-concepto-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="monto">Monto (GTQ) *</Label>
                  <Input
                    id="monto"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.monto}
                    onChange={(e) => handleInputChange('monto', e.target.value)}
                    placeholder="0.00"
                    data-testid="expense-monto-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fecha">Fecha *</Label>
                  <Input
                    id="fecha"
                    type="date"
                    value={formData.fecha}
                    onChange={(e) => handleInputChange('fecha', e.target.value)}
                    data-testid="expense-fecha-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="categoria">Categoría *</Label>
                  <Select
                    value={formData.categoria}
                    onValueChange={(value) => handleInputChange('categoria', value)}
                  >
                    <SelectTrigger data-testid="expense-categoria-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gastos_fijos">Gastos Fijos</SelectItem>
                      <SelectItem value="pagos_proveedores">Pagos Proveedores</SelectItem>
                      <SelectItem value="gastos_variables">Gastos Variables</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="estado">Estado *</Label>
                  <Select
                    value={formData.estado}
                    onValueChange={(value) => handleInputChange('estado', value)}
                  >
                    <SelectTrigger data-testid="expense-estado-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pendiente">Pendiente</SelectItem>
                      <SelectItem value="pagado">Pagado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fecha_vencimiento">Fecha Vencimiento</Label>
                  <Input
                    id="fecha_vencimiento"
                    type="date"
                    value={formData.fecha_vencimiento}
                    onChange={(e) => handleInputChange('fecha_vencimiento', e.target.value)}
                    data-testid="expense-vencimiento-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="proveedor">Proveedor</Label>
                  <Input
                    id="proveedor"
                    value={formData.proveedor}
                    onChange={(e) => handleInputChange('proveedor', e.target.value)}
                    placeholder="Nombre del proveedor"
                    data-testid="expense-proveedor-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="notas">Notas</Label>
                <Textarea
                  id="notas"
                  value={formData.notas}
                  onChange={(e) => handleInputChange('notas', e.target.value)}
                  placeholder="Notas adicionales..."
                  rows={3}
                  data-testid="expense-notas-input"
                />
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseDialog}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="bg-teal-800 hover:bg-teal-900 text-white"
                  disabled={submitting}
                  data-testid="expense-submit-button"
                >
                  {submitting ? 'Guardando...' : editingExpense ? 'Actualizar' : 'Registrar'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Gasto</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar el gasto "{expenseToDelete?.concepto}"? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDelete}
                data-testid="confirm-delete-button"
              >
                Eliminar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Gastos;
