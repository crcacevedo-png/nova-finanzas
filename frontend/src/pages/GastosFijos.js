import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  CalendarClock,
  DollarSign,
  Calendar,
  Truck,
  Play
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
import { fixedExpenseApi, supplierApi, formatCurrency } from '../services/api';

const GastosFijos = () => {
  const { user } = useAuth();
  const [fixedExpenses, setFixedExpenses] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    supplier_id: '',
    expense_name: '',
    amount: '',
    day_of_month: ''
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [expensesRes, suppliersRes] = await Promise.all([
        fixedExpenseApi.getAll(),
        supplierApi.getAll()
      ]);
      setFixedExpenses(expensesRes.data.data || []);
      setSuppliers(suppliersRes.data.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenDialog = (expense = null) => {
    if (expense) {
      setEditingExpense(expense);
      setFormData({
        supplier_id: expense.supplier_id,
        expense_name: expense.expense_name,
        amount: expense.amount.toString(),
        day_of_month: expense.day_of_month.toString()
      });
    } else {
      setEditingExpense(null);
      setFormData({
        supplier_id: '',
        expense_name: '',
        amount: '',
        day_of_month: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.supplier_id) {
      toast.error('Debe seleccionar un proveedor');
      return;
    }
    if (!formData.expense_name.trim()) {
      toast.error('El nombre del gasto es obligatorio');
      return;
    }
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      toast.error('El monto debe ser mayor a 0');
      return;
    }
    if (!formData.day_of_month || parseInt(formData.day_of_month) < 1 || parseInt(formData.day_of_month) > 31) {
      toast.error('El día del mes debe ser entre 1 y 31');
      return;
    }

    const payload = {
      supplier_id: formData.supplier_id,
      expense_name: formData.expense_name,
      amount: parseFloat(formData.amount),
      day_of_month: parseInt(formData.day_of_month)
    };

    setSubmitting(true);
    try {
      if (editingExpense) {
        await fixedExpenseApi.update(editingExpense.id, payload);
        toast.success('Gasto fijo actualizado exitosamente');
      } else {
        await fixedExpenseApi.create(payload);
        toast.success('Gasto fijo creado exitosamente');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar el gasto fijo';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedExpense) return;
    
    setSubmitting(true);
    try {
      await fixedExpenseApi.delete(selectedExpense.id);
      toast.success('Gasto fijo eliminado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedExpense(null);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar el gasto fijo';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerateNow = async () => {
    setSubmitting(true);
    try {
      const response = await fixedExpenseApi.generateNow();
      toast.success(`Se generaron ${response.data.count} gastos fijos`);
      setGenerateDialogOpen(false);
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al generar gastos fijos';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredExpenses = fixedExpenses.filter(expense =>
    expense.expense_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    expense.supplier_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalMonthly = fixedExpenses.reduce((sum, e) => sum + e.amount, 0);

  const getDayLabel = (day) => {
    if (day === 1) return '1ro';
    if (day === 2) return '2do';
    if (day === 3) return '3ro';
    return `${day}`;
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="gastos-fijos-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Gastos Fijos
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Configura los gastos recurrentes mensuales
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button 
              variant="outline"
              onClick={fetchData}
              className="btn-outline"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {user?.role === 'superadmin' && (
              <Button 
                variant="outline"
                onClick={() => setGenerateDialogOpen(true)}
                className="btn-outline border-amber-500 text-amber-600 hover:bg-amber-50"
                data-testid="generate-now-button"
              >
                <Play className="w-4 h-4 mr-2" />
                Generar Ahora
              </Button>
            )}
            <Button 
              onClick={() => handleOpenDialog()}
              className="btn-primary"
              data-testid="add-fixed-expense-button"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Gasto Fijo
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-teal-100">
                <CalendarClock className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Gastos Fijos</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {fixedExpenses.length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-emerald-100">
                <DollarSign className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Mensual</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {formatCurrency(totalMonthly)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <Input
              placeholder="Buscar por nombre de gasto o proveedor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-teal max-w-md"
              data-testid="search-fixed-expense"
            />
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Gastos Fijos Recurrentes
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : filteredExpenses.length === 0 ? (
              <div className="p-12 text-center">
                <CalendarClock className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {searchTerm ? 'No se encontraron gastos fijos' : 'No hay gastos fijos registrados'}
                </p>
                {!searchTerm && (
                  <Button 
                    onClick={() => handleOpenDialog()}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer gasto fijo
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Proveedor</TableHead>
                      <TableHead className="table-header">Nombre del Gasto</TableHead>
                      <TableHead className="table-header text-right">Monto</TableHead>
                      <TableHead className="table-header text-center">Día del Mes</TableHead>
                      <TableHead className="table-header text-center">Última Generación</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredExpenses.map((expense) => (
                      <TableRow 
                        key={expense.id} 
                        className="table-row-hover"
                        data-testid={`fixed-expense-row-${expense.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-teal-50">
                              <Truck className="w-4 h-4 text-teal-600" />
                            </div>
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {expense.supplier_name || 'Sin proveedor'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {expense.expense_name}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {formatCurrency(expense.amount)}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className="badge-fijo">
                            <Calendar className="w-3 h-3 mr-1" />
                            Día {getDayLabel(expense.day_of_month)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          {expense.last_generated ? (
                            <span style={{ color: 'var(--text-secondary)' }}>
                              {expense.last_generated}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>Nunca</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(expense)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`edit-fixed-expense-${expense.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedExpense(expense);
                                setDeleteDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                              data-testid={`delete-fixed-expense-${expense.id}`}
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
        <Card className="card-teal border-l-4 border-l-teal-500">
          <CardContent className="p-4">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              <strong>Nota:</strong> Los gastos fijos se generan automáticamente cada día a las 00:05 horas. 
              Cuando el día configurado coincide con el día actual del mes, se crea un nuevo gasto pendiente 
              con vencimiento a +30 días.
            </p>
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingExpense ? 'Editar Gasto Fijo' : 'Nuevo Gasto Fijo'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingExpense 
                  ? 'Actualiza los datos del gasto fijo recurrente'
                  : 'Configura un nuevo gasto fijo que se generará automáticamente cada mes'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="supplier_id">Proveedor *</Label>
                <Select
                  value={formData.supplier_id}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, supplier_id: value }))}
                >
                  <SelectTrigger className="input-teal" data-testid="supplier-select">
                    <SelectValue placeholder="Selecciona un proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliers.map((supplier) => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {suppliers.length === 0 && (
                  <p className="text-xs text-amber-600">
                    No hay proveedores registrados. Crea uno primero en Configuración → Proveedores.
                  </p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="expense_name">Nombre del gasto *</Label>
                <Input
                  id="expense_name"
                  value={formData.expense_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, expense_name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Alquiler de local, Planilla, Luz"
                  data-testid="expense-name-input"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="amount">Monto (GTQ) *</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData(prev => ({ ...prev, amount: e.target.value }))}
                    className="input-teal"
                    placeholder="0.00"
                    data-testid="amount-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="day_of_month">Día del mes *</Label>
                  <Input
                    id="day_of_month"
                    type="number"
                    min="1"
                    max="31"
                    value={formData.day_of_month}
                    onChange={(e) => setFormData(prev => ({ ...prev, day_of_month: e.target.value }))}
                    className="input-teal"
                    placeholder="1-31"
                    data-testid="day-of-month-input"
                  />
                  <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                    Día en que se genera el gasto cada mes
                  </p>
                </div>
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
                  disabled={submitting || suppliers.length === 0}
                  data-testid="submit-fixed-expense-button"
                >
                  {submitting 
                    ? (editingExpense ? 'Guardando...' : 'Creando...') 
                    : (editingExpense ? 'Guardar cambios' : 'Crear gasto fijo')}
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
                Eliminar Gasto Fijo
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar el gasto fijo "{selectedExpense?.expense_name}"? 
                Los gastos ya generados no serán eliminados, pero no se generarán nuevos.
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

        {/* Generate Now Confirmation Dialog */}
        <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Generar Gastos Fijos Ahora
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                Esta acción generará inmediatamente todos los gastos fijos configurados para el día de hoy ({new Date().getDate()}). 
                Solo se generarán aquellos que no hayan sido generados este mes.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => setGenerateDialogOpen(false)} 
                className="btn-outline"
              >
                Cancelar
              </Button>
              <Button 
                onClick={handleGenerateNow}
                disabled={submitting}
                className="bg-amber-500 hover:bg-amber-600 text-white"
                data-testid="confirm-generate-button"
              >
                {submitting ? 'Generando...' : 'Generar Ahora'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default GastosFijos;
