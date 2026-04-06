import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { expenseApi, paymentApi, formatCurrency, formatDate, typeLabels, statusLabels, paymentMethodLabels } from '../services/api';
import { 
  Plus, 
  Search, 
  Pencil,
  Trash2,
  DollarSign,
  Eye,
  X,
  Download,
  ChevronLeft,
  ChevronRight,
  FileText
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
import { Progress } from '../components/ui/progress';
import { toast, Toaster } from 'sonner';

const initialExpenseForm = {
  provider: '',
  name: '',
  type: 'fijo',
  amount: '',
  date: new Date().toISOString().split('T')[0],
  due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // +30 días
  invoice_number: '',
  notes: ''
};

// Función para calcular fecha de vencimiento (+30 días)
const calculateDueDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  date.setDate(date.getDate() + 30);
  return date.toISOString().split('T')[0];
};

const initialPaymentForm = {
  amount: '',
  date: new Date().toISOString().split('T')[0],
  method: 'Efectivo',
  reference: '',
  notes: ''
};

const Gastos = () => {
  const { canCreateExpenses, canEditExpenses, canDeleteExpenses, canRegisterPayments, canDeletePayments, canExportReports } = useAuth();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Pagination
  const [pagination, setPagination] = useState({ page: 1, limit: 20, total: 0, totalPages: 0 });
  
  // Dialogs
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  
  // Selected items
  const [editingExpense, setEditingExpense] = useState(null);
  const [expenseToDelete, setExpenseToDelete] = useState(null);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [expensePayments, setExpensePayments] = useState([]);
  
  // Forms
  const [expenseForm, setExpenseForm] = useState(initialExpenseForm);
  const [paymentForm, setPaymentForm] = useState(initialPaymentForm);
  
  // Filters
  const [filters, setFilters] = useState({ type: '', status: '', search: '', dateFrom: '', dateTo: '' });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchExpenses();
  }, [filters.type, filters.status, pagination.page]);

  const fetchExpenses = async () => {
    try {
      const response = await expenseApi.getAll({
        type: filters.type || undefined,
        status: filters.status || undefined,
        search: filters.search || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        page: pagination.page,
        limit: pagination.limit,
        sortBy: 'date',
        sortOrder: 'desc'
      });
      
      // Handle new paginated response structure
      if (response.data.data) {
        setExpenses(response.data.data);
        setPagination(prev => ({
          ...prev,
          total: response.data.total,
          totalPages: response.data.total_pages
        }));
      } else {
        setExpenses(response.data);
      }
    } catch (error) {
      console.error('Error fetching expenses:', error);
      toast.error('Error al cargar los gastos');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPagination(prev => ({ ...prev, page: 1 }));
    fetchExpenses();
  };

  const handleExport = (format) => {
    const token = localStorage.getItem('token');
    const url = expenseApi.exportReport({
      format,
      type: filters.type || undefined,
      status: filters.status || undefined,
      dateFrom: filters.dateFrom || undefined,
      dateTo: filters.dateTo || undefined
    });
    
    // Open download in new window with auth
    window.open(url, '_blank');
  };

  const filteredExpenses = expenses.filter(expense => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return expense.name.toLowerCase().includes(searchLower) ||
             expense.invoice_number?.toLowerCase().includes(searchLower);
    }
    return true;
  });

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination(prev => ({ ...prev, page: newPage }));
    }
  };

  // Expense handlers
  const handleOpenExpenseDialog = (expense = null) => {
    if (expense) {
      setEditingExpense(expense);
      const expenseDate = expense.date.split('T')[0];
      setExpenseForm({
        provider: expense.provider || '',
        name: expense.name,
        type: expense.type,
        amount: expense.amount.toString(),
        date: expenseDate,
        due_date: expense.due_date?.split('T')[0] || calculateDueDate(expenseDate),
        invoice_number: expense.invoice_number || '',
        notes: expense.notes || ''
      });
    } else {
      setEditingExpense(null);
      setExpenseForm(initialExpenseForm);
    }
    setExpenseDialogOpen(true);
  };

  const handleCloseExpenseDialog = () => {
    setExpenseDialogOpen(false);
    setEditingExpense(null);
    setExpenseForm(initialExpenseForm);
  };

  const handleExpenseSubmit = async (e) => {
    e.preventDefault();
    
    if (!expenseForm.provider || !expenseForm.name || !expenseForm.amount || !expenseForm.date) {
      toast.error('Por favor completa los campos requeridos');
      return;
    }

    setSubmitting(true);
    try {
      const data = {
        ...expenseForm,
        amount: parseFloat(expenseForm.amount),
        due_date: expenseForm.due_date || null,
        invoice_number: expenseForm.invoice_number || null,
        provider: expenseForm.provider || null
      };

      if (editingExpense) {
        await expenseApi.update(editingExpense.id, data);
        toast.success('Gasto actualizado correctamente');
      } else {
        await expenseApi.create(data);
        toast.success('Gasto registrado correctamente');
      }

      handleCloseExpenseDialog();
      fetchExpenses();
    } catch (error) {
      console.error('Error saving expense:', error);
      const message = error.response?.data?.detail || 'Error al guardar el gasto';
      toast.error(message);
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
      const message = error.response?.data?.detail || 'Error al eliminar el gasto';
      toast.error(message);
    } finally {
      setDeleteDialogOpen(false);
      setExpenseToDelete(null);
    }
  };

  // Payment handlers
  const handleOpenPaymentDialog = (expense) => {
    setSelectedExpense(expense);
    setPaymentForm({
      ...initialPaymentForm,
      amount: expense.remaining_amount.toString()
    });
    setPaymentDialogOpen(true);
  };

  const handleClosePaymentDialog = () => {
    setPaymentDialogOpen(false);
    setSelectedExpense(null);
    setPaymentForm(initialPaymentForm);
  };

  const handlePaymentSubmit = async (e) => {
    e.preventDefault();
    
    if (!paymentForm.amount || !paymentForm.date || !paymentForm.method) {
      toast.error('Por favor completa los campos requeridos');
      return;
    }

    const amount = parseFloat(paymentForm.amount);
    if (amount > selectedExpense.remaining_amount) {
      toast.error(`El monto no puede exceder Q${selectedExpense.remaining_amount.toFixed(2)}`);
      return;
    }

    setSubmitting(true);
    try {
      await paymentApi.create({
        expense_id: selectedExpense.id,
        amount: amount,
        date: paymentForm.date,
        method: paymentForm.method,
        reference: paymentForm.reference || null,
        notes: paymentForm.notes || ''
      });
      
      toast.success('Pago registrado correctamente');
      handleClosePaymentDialog();
      fetchExpenses();
    } catch (error) {
      console.error('Error creating payment:', error);
      const message = error.response?.data?.detail || 'Error al registrar el pago';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  // Detail view handlers
  const handleViewDetails = async (expense) => {
    setSelectedExpense(expense);
    try {
      const response = await expenseApi.getPayments(expense.id);
      setExpensePayments(response.data);
    } catch (error) {
      console.error('Error fetching payments:', error);
      setExpensePayments([]);
    }
    setDetailDialogOpen(true);
  };

  const handleDeletePayment = async (paymentId) => {
    try {
      await paymentApi.delete(paymentId);
      toast.success('Pago eliminado');
      // Refresh payments and expenses
      const response = await expenseApi.getPayments(selectedExpense.id);
      setExpensePayments(response.data);
      fetchExpenses();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar el pago';
      toast.error(message);
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      pendiente: 'badge-pending border-0',
      parcial: 'badge-partial border-0',
      pagado: 'badge-paid border-0',
      vencido: 'badge-overdue border-0'
    };
    return <Badge className={colors[status]}>{statusLabels[status]}</Badge>;
  };

  const getTypeBadge = (type) => {
    const colors = {
      fijo: 'badge-fixed border-0',
      proveedor: 'badge-provider border-0',
      variable: 'badge-variable border-0'
    };
    return <Badge className={colors[type]}>{typeLabels[type]}</Badge>;
  };

  const getPaymentProgress = (expense) => {
    const progress = (expense.paid_amount / expense.amount) * 100;
    return Math.min(progress, 100);
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
          <div className="flex items-center gap-2">
            {canExportReports() && (
              <>
                <Button 
                  variant="outline"
                  onClick={() => handleExport('xlsx')}
                  className="btn-outline"
                  data-testid="export-excel-button"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Excel
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handleExport('pdf')}
                  className="btn-outline"
                  data-testid="export-pdf-button"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  PDF
                </Button>
              </>
            )}
            {canCreateExpenses() && (
              <Button 
                onClick={() => handleOpenExpenseDialog()}
                className="btn-primary"
                data-testid="add-expense-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Gasto
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <Card className="border border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Buscar por nombre o factura..."
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Input
                  type="date"
                  placeholder="Desde"
                  value={filters.dateFrom}
                  onChange={(e) => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                  className="w-36"
                  data-testid="date-from-input"
                />
                <Input
                  type="date"
                  placeholder="Hasta"
                  value={filters.dateTo}
                  onChange={(e) => setFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                  className="w-36"
                  data-testid="date-to-input"
                />
                <Select
                  value={filters.type || "all"}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, type: value === "all" ? "" : value }))}
                >
                  <SelectTrigger className="w-[150px]" data-testid="type-filter">
                    <SelectValue placeholder="Tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los tipos</SelectItem>
                    <SelectItem value="fijo">Gasto Fijo</SelectItem>
                    <SelectItem value="proveedor">Pago Proveedor</SelectItem>
                    <SelectItem value="variable">Gasto Variable</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={filters.status || "all"}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, status: value === "all" ? "" : value }))}
                >
                  <SelectTrigger className="w-[150px]" data-testid="status-filter">
                    <SelectValue placeholder="Estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="pendiente">Pendiente</SelectItem>
                    <SelectItem value="parcial">Parcial</SelectItem>
                    <SelectItem value="pagado">Pagado</SelectItem>
                    <SelectItem value="vencido">Vencido</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={handleSearch} className="px-6">
                  Buscar
                </Button>
              </div>
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
                      <TableHead className="font-semibold text-slate-600">Nombre</TableHead>
                      <TableHead className="font-semibold text-slate-600">Monto</TableHead>
                      <TableHead className="font-semibold text-slate-600">Progreso</TableHead>
                      <TableHead className="font-semibold text-slate-600">Tipo</TableHead>
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
                            <p className="font-medium text-slate-900">{expense.name}</p>
                            {expense.invoice_number && (
                              <p className="text-xs text-slate-500">Factura: {expense.invoice_number}</p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-semibold text-slate-900">{formatCurrency(expense.amount)}</p>
                            {expense.paid_amount > 0 && (
                              <p className="text-xs text-slate-500">
                                Pagado: {formatCurrency(expense.paid_amount)}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="w-24">
                            <Progress value={getPaymentProgress(expense)} className="h-2" />
                            <p className="text-xs text-slate-500 mt-1">
                              {Math.round(getPaymentProgress(expense))}%
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>{getTypeBadge(expense.type)}</TableCell>
                        <TableCell>{getStatusBadge(expense.status)}</TableCell>
                        <TableCell className="text-slate-600">
                          {expense.due_date ? formatDate(expense.due_date) : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetails(expense)}
                              className="h-8 w-8 p-0 hover:bg-slate-100"
                              title="Ver detalles"
                              data-testid={`view-expense-${expense.id}`}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {canRegisterPayments() && expense.status !== 'pagado' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenPaymentDialog(expense)}
                                className="h-8 w-8 p-0 hover:bg-emerald-50 hover:text-emerald-700"
                                title="Registrar pago"
                                data-testid={`pay-expense-${expense.id}`}
                              >
                                <DollarSign className="w-4 h-4" />
                              </Button>
                            )}
                            {canEditExpenses() && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenExpenseDialog(expense)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                data-testid={`edit-expense-${expense.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                            )}
                            {canDeleteExpenses() && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteClick(expense)}
                                className="h-8 w-8 p-0 hover:bg-rose-50 hover:text-rose-700"
                                data-testid={`delete-expense-${expense.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
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
          
          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="p-4 border-t border-slate-200 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                Mostrando {((pagination.page - 1) * pagination.limit) + 1} - {Math.min(pagination.page * pagination.limit, pagination.total)} de {pagination.total} gastos
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-slate-600 px-2">
                  Página {pagination.page} de {pagination.totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page === pagination.totalPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* Create/Edit Expense Dialog */}
        <Dialog open={expenseDialogOpen} onOpenChange={setExpenseDialogOpen}>
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
            <form onSubmit={handleExpenseSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="provider">Proveedor *</Label>
                <Input
                  id="provider"
                  value={expenseForm.provider}
                  onChange={(e) => setExpenseForm(prev => ({ ...prev, provider: e.target.value }))}
                  placeholder="Ej: Óptica GT, Laboratorios ABC..."
                  data-testid="expense-provider-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Nombre del Gasto *</Label>
                <Input
                  id="name"
                  value={expenseForm.name}
                  onChange={(e) => setExpenseForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Ej: Alquiler oficina, Lentes oftálmicos..."
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
                    min="0"
                    value={expenseForm.amount}
                    onChange={(e) => setExpenseForm(prev => ({ ...prev, amount: e.target.value }))}
                    placeholder="0.00"
                    data-testid="expense-amount-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Tipo *</Label>
                  <Select
                    value={expenseForm.type}
                    onValueChange={(value) => setExpenseForm(prev => ({ ...prev, type: value }))}
                  >
                    <SelectTrigger data-testid="expense-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fijo">Gasto Fijo</SelectItem>
                      <SelectItem value="proveedor">Pago Proveedor</SelectItem>
                      <SelectItem value="variable">Gasto Variable</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date">Fecha Registro *</Label>
                  <Input
                    id="date"
                    type="date"
                    value={expenseForm.date}
                    onChange={(e) => {
                      const newDate = e.target.value;
                      setExpenseForm(prev => ({ 
                        ...prev, 
                        date: newDate,
                        due_date: calculateDueDate(newDate)
                      }));
                    }}
                    data-testid="expense-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="due_date">Fecha Vencimiento (auto +30 días)</Label>
                  <Input
                    id="due_date"
                    type="date"
                    value={expenseForm.due_date}
                    onChange={(e) => setExpenseForm(prev => ({ ...prev, due_date: e.target.value }))}
                    data-testid="expense-duedate-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="invoice_number">Número de Factura</Label>
                <Input
                  id="invoice_number"
                  value={expenseForm.invoice_number}
                  onChange={(e) => setExpenseForm(prev => ({ ...prev, invoice_number: e.target.value }))}
                  placeholder="Ej: FAC-001234"
                  data-testid="expense-invoice-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notas</Label>
                <Textarea
                  id="notes"
                  value={expenseForm.notes}
                  onChange={(e) => setExpenseForm(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Notas adicionales..."
                  rows={3}
                  data-testid="expense-notes-input"
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleCloseExpenseDialog} disabled={submitting}>
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="expense-submit-button">
                  {submitting ? 'Guardando...' : editingExpense ? 'Actualizar' : 'Registrar'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Payment Dialog */}
        <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Registrar Pago</DialogTitle>
              <DialogDescription>
                {selectedExpense && (
                  <div className="mt-2 p-3 bg-slate-50 rounded-lg">
                    <p className="font-medium text-slate-900">{selectedExpense.name}</p>
                    <p className="text-sm">Total: {formatCurrency(selectedExpense.amount)}</p>
                    <p className="text-sm text-emerald-600">Pagado: {formatCurrency(selectedExpense.paid_amount)}</p>
                    <p className="text-sm text-amber-600 font-medium">Pendiente: {formatCurrency(selectedExpense.remaining_amount)}</p>
                  </div>
                )}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handlePaymentSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="payment_amount">Monto a Pagar *</Label>
                  <Input
                    id="payment_amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={selectedExpense?.remaining_amount}
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
                    data-testid="payment-amount-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="payment_date">Fecha *</Label>
                  <Input
                    id="payment_date"
                    type="date"
                    value={paymentForm.date}
                    onChange={(e) => setPaymentForm(prev => ({ ...prev, date: e.target.value }))}
                    data-testid="payment-date-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment_method">Método de Pago *</Label>
                <Select
                  value={paymentForm.method}
                  onValueChange={(value) => setPaymentForm(prev => ({ ...prev, method: value }))}
                >
                  <SelectTrigger data-testid="payment-method-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {paymentMethodLabels.map(method => (
                      <SelectItem key={method} value={method}>{method}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment_reference">Referencia / Comprobante</Label>
                <Input
                  id="payment_reference"
                  value={paymentForm.reference}
                  onChange={(e) => setPaymentForm(prev => ({ ...prev, reference: e.target.value }))}
                  placeholder="Número de transacción, cheque, etc."
                  data-testid="payment-reference-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment_notes">Notas</Label>
                <Textarea
                  id="payment_notes"
                  value={paymentForm.notes}
                  onChange={(e) => setPaymentForm(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Notas adicionales..."
                  rows={2}
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClosePaymentDialog} disabled={submitting}>
                  Cancelar
                </Button>
                <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white" disabled={submitting} data-testid="payment-submit-button">
                  {submitting ? 'Registrando...' : 'Registrar Pago'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Detalle del Gasto</DialogTitle>
            </DialogHeader>
            {selectedExpense && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">Nombre</p>
                    <p className="font-medium">{selectedExpense.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Tipo</p>
                    {getTypeBadge(selectedExpense.type)}
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Monto Total</p>
                    <p className="font-semibold text-lg">{formatCurrency(selectedExpense.amount)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Estado</p>
                    {getStatusBadge(selectedExpense.status)}
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Pagado</p>
                    <p className="font-medium text-emerald-600">{formatCurrency(selectedExpense.paid_amount)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Pendiente</p>
                    <p className="font-medium text-amber-600">{formatCurrency(selectedExpense.remaining_amount)}</p>
                  </div>
                  {selectedExpense.invoice_number && (
                    <div>
                      <p className="text-sm text-slate-500">Factura</p>
                      <p className="font-medium">{selectedExpense.invoice_number}</p>
                    </div>
                  )}
                  {selectedExpense.due_date && (
                    <div>
                      <p className="text-sm text-slate-500">Vencimiento</p>
                      <p className="font-medium">{formatDate(selectedExpense.due_date)}</p>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t">
                  <h4 className="font-semibold mb-3">Historial de Pagos</h4>
                  {expensePayments.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No hay pagos registrados</p>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {expensePayments.map((payment) => (
                        <div key={payment.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div>
                            <p className="font-medium">{formatCurrency(payment.amount)}</p>
                            <p className="text-xs text-slate-500">
                              {formatDate(payment.date)} • {payment.method}
                              {payment.reference && ` • Ref: ${payment.reference}`}
                            </p>
                          </div>
                          {canDeletePayments() && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeletePayment(payment.id)}
                              className="h-8 w-8 p-0 hover:bg-rose-50 hover:text-rose-700"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Gasto</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar el gasto "{expenseToDelete?.name}"? 
                Esta acción eliminará también todos los pagos asociados y no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleConfirmDelete} data-testid="confirm-delete-button">
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
