import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  CheckCircle,
  XCircle,
  Clock,
  Building2,
  FileCheck,
  AlertCircle,
  Eye,
  Trash2,
  RefreshCw,
  CreditCard,
  Calendar,
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
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import { toast, Toaster } from 'sonner';
import { paymentAuthorizationApi, bankAccountApi, formatCurrency, formatDate } from '../services/api';

const statusConfig = {
  pendiente: { label: 'Pendiente', color: 'bg-amber-100 text-amber-700', icon: Clock },
  ejecutado: { label: 'Ejecutado', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  cancelado: { label: 'Cancelado', color: 'bg-red-100 text-red-700', icon: XCircle }
};

const AutorizacionPagos = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdmin = user?.role === 'admin';
  
  const [authorizations, setAuthorizations] = useState([]);
  const [pendingExpenses, setPendingExpenses] = useState([]);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  const [selectedAuth, setSelectedAuth] = useState(null);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    expense_id: '',
    bank_account_id: '',
    amount_to_pay: '',
    notes: ''
  });

  // Summary counts
  const [summary, setSummary] = useState({ pending: 0, executed: 0, total: 0 });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Obtener autorizaciones
      const statusParam = statusFilter !== 'all' ? statusFilter : null;
      const authResponse = await paymentAuthorizationApi.getAll(statusParam);
      setAuthorizations(authResponse.data.data || []);
      setSummary({
        pending: authResponse.data.pending_count || 0,
        executed: authResponse.data.executed_count || 0,
        total: authResponse.data.total || 0
      });
      
      // Solo SuperAdmin puede crear autorizaciones
      if (isSuperAdmin) {
        const [expensesRes, accountsRes] = await Promise.all([
          paymentAuthorizationApi.getExpensesPendingAuth(),
          bankAccountApi.getAll()
        ]);
        setPendingExpenses(expensesRes.data.data || []);
        setBankAccounts(accountsRes.data.data || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, isSuperAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenCreateDialog = () => {
    setFormData({
      expense_id: '',
      bank_account_id: '',
      amount_to_pay: '',
      notes: ''
    });
    setSelectedExpense(null);
    setCreateDialogOpen(true);
  };

  const handleExpenseSelect = (expenseId) => {
    const expense = pendingExpenses.find(e => e.id === expenseId);
    setSelectedExpense(expense);
    setFormData(prev => ({
      ...prev,
      expense_id: expenseId,
      amount_to_pay: expense ? expense.remaining_amount.toString() : ''
    }));
  };

  const handleCreateAuthorization = async (e) => {
    e.preventDefault();
    
    if (!formData.expense_id || !formData.bank_account_id || !formData.amount_to_pay) {
      toast.error('Por favor completa los campos obligatorios');
      return;
    }

    setSubmitting(true);
    try {
      await paymentAuthorizationApi.create({
        expense_id: formData.expense_id,
        bank_account_id: formData.bank_account_id,
        amount_to_pay: parseFloat(formData.amount_to_pay),
        notes: formData.notes
      });
      toast.success('Autorización creada exitosamente');
      setCreateDialogOpen(false);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al crear la autorización';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedAuth) return;
    
    setSubmitting(true);
    try {
      await paymentAuthorizationApi.execute(selectedAuth.id);
      toast.success('Pago ejecutado exitosamente');
      setExecuteDialogOpen(false);
      setSelectedAuth(null);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al ejecutar el pago';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedAuth) return;
    
    setSubmitting(true);
    try {
      await paymentAuthorizationApi.cancel(selectedAuth.id);
      toast.success('Autorización cancelada');
      setCancelDialogOpen(false);
      setSelectedAuth(null);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al cancelar la autorización';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedAuth) return;
    
    setSubmitting(true);
    try {
      await paymentAuthorizationApi.delete(selectedAuth.id);
      toast.success('Autorización eliminada');
      setDeleteDialogOpen(false);
      setSelectedAuth(null);
      fetchData();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar la autorización';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const StatusBadge = ({ status }) => {
    const config = statusConfig[status] || statusConfig.pendiente;
    const Icon = config.icon;
    return (
      <Badge className={`${config.color} flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    );
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="autorizacion-pagos-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Autorización de Pagos
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {isSuperAdmin 
                ? 'Autoriza pagos y asigna cuentas bancarias'
                : 'Ejecuta los pagos autorizados'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline"
              onClick={fetchData}
              className="btn-outline"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {isSuperAdmin && (
              <Button 
                onClick={handleOpenCreateDialog}
                className="btn-primary"
                disabled={pendingExpenses.length === 0}
                data-testid="create-authorization-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nueva Autorización
              </Button>
            )}
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-amber-100">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Pendientes</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {summary.pending}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-emerald-100">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Ejecutados</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {summary.executed}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-100">
                <FileCheck className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Autorizaciones</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {summary.total}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <Label>Estado:</Label>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[180px] input-teal" data-testid="status-filter">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="pendiente">Pendiente</SelectItem>
                    <SelectItem value="ejecutado">Ejecutado</SelectItem>
                    <SelectItem value="cancelado">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Autorizaciones
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : authorizations.length === 0 ? (
              <div className="p-12 text-center">
                <FileCheck className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {statusFilter !== 'all' 
                    ? `No hay autorizaciones con estado "${statusConfig[statusFilter]?.label || statusFilter}"`
                    : 'No hay autorizaciones de pago'}
                </p>
                {isSuperAdmin && pendingExpenses.length > 0 && (
                  <Button 
                    onClick={handleOpenCreateDialog}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Crear primera autorización
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Gasto</TableHead>
                      <TableHead className="table-header">Proveedor</TableHead>
                      <TableHead className="table-header">Monto Autorizado</TableHead>
                      <TableHead className="table-header">Cuenta Bancaria</TableHead>
                      <TableHead className="table-header">Estado</TableHead>
                      <TableHead className="table-header">Autorizado por</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {authorizations.map((auth) => (
                      <TableRow 
                        key={auth.id} 
                        className="table-row-hover"
                        data-testid={`auth-row-${auth.id}`}
                      >
                        <TableCell>
                          <div>
                            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {auth.expense_name}
                            </p>
                            <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                              Vence: {formatDate(auth.expense_due_date)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {auth.expense_provider || '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-semibold" style={{ color: 'var(--primary-teal)' }}>
                            {formatCurrency(auth.amount_to_pay)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Building2 className="w-4 h-4" style={{ color: 'var(--text-hint)' }} />
                            <div>
                              <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
                                {auth.bank_account_alias}
                              </p>
                              <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                                {auth.bank_name}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={auth.status} />
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4" style={{ color: 'var(--text-hint)' }} />
                            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                              {auth.authorized_by_name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedAuth(auth);
                                setDetailDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`view-auth-${auth.id}`}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            
                            {/* Admin puede ejecutar pagos pendientes */}
                            {isAdmin && auth.status === 'pendiente' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedAuth(auth);
                                  setExecuteDialogOpen(true);
                                }}
                                className="h-8 w-8 p-0 hover:bg-emerald-100 hover:text-emerald-600"
                                data-testid={`execute-auth-${auth.id}`}
                              >
                                <CheckCircle className="w-4 h-4" />
                              </Button>
                            )}
                            
                            {/* SuperAdmin puede cancelar y eliminar */}
                            {isSuperAdmin && auth.status === 'pendiente' && (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setSelectedAuth(auth);
                                    setCancelDialogOpen(true);
                                  }}
                                  className="h-8 w-8 p-0 hover:bg-amber-100 hover:text-amber-600"
                                  data-testid={`cancel-auth-${auth.id}`}
                                >
                                  <XCircle className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setSelectedAuth(auth);
                                    setDeleteDialogOpen(true);
                                  }}
                                  className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                                  data-testid={`delete-auth-${auth.id}`}
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

        {/* Create Authorization Dialog (SuperAdmin only) */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="sm:max-w-[550px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Nueva Autorización de Pago
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                Selecciona un gasto pendiente y asigna la cuenta bancaria para el pago
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateAuthorization} className="space-y-4">
              {/* Selección de gasto */}
              <div className="space-y-2">
                <Label>Gasto a pagar *</Label>
                <Select 
                  value={formData.expense_id} 
                  onValueChange={handleExpenseSelect}
                >
                  <SelectTrigger className="input-teal" data-testid="expense-select">
                    <SelectValue placeholder="Selecciona un gasto" />
                  </SelectTrigger>
                  <SelectContent>
                    {pendingExpenses.map((expense) => (
                      <SelectItem key={expense.id} value={expense.id}>
                        <div className="flex justify-between items-center gap-4">
                          <span>{expense.name}</span>
                          <span className="text-xs text-muted-foreground">
                            Pendiente: {formatCurrency(expense.remaining_amount)}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Info del gasto seleccionado */}
              {selectedExpense && (
                <Card className="bg-[#E1F5EE]/50 border-[#0F6E56]/20">
                  <CardContent className="p-4 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Proveedor:</span>
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {selectedExpense.provider || 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Monto total:</span>
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {formatCurrency(selectedExpense.amount)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Monto pendiente:</span>
                      <span className="font-semibold" style={{ color: 'var(--primary-teal)' }}>
                        {formatCurrency(selectedExpense.remaining_amount)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Fecha vencimiento:</span>
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {formatDate(selectedExpense.due_date)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Selección de cuenta bancaria */}
              <div className="space-y-2">
                <Label>Cuenta bancaria *</Label>
                <Select 
                  value={formData.bank_account_id} 
                  onValueChange={(value) => setFormData(prev => ({ ...prev, bank_account_id: value }))}
                >
                  <SelectTrigger className="input-teal" data-testid="bank-account-select">
                    <SelectValue placeholder="Selecciona una cuenta" />
                  </SelectTrigger>
                  <SelectContent>
                    {bankAccounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-muted-foreground" />
                          <span>{account.account_alias}</span>
                          <span className="text-xs text-muted-foreground">({account.bank_name})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Monto a pagar */}
              <div className="space-y-2">
                <Label>Monto a autorizar *</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">Q</span>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={selectedExpense?.remaining_amount || 999999}
                    value={formData.amount_to_pay}
                    onChange={(e) => setFormData(prev => ({ ...prev, amount_to_pay: e.target.value }))}
                    className="input-teal pl-8"
                    placeholder="0.00"
                    data-testid="amount-input"
                  />
                </div>
              </div>

              {/* Notas */}
              <div className="space-y-2">
                <Label>Notas (opcional)</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  className="input-teal resize-none"
                  placeholder="Instrucciones adicionales para el pago..."
                  rows={3}
                  data-testid="notes-input"
                />
              </div>

              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setCreateDialogOpen(false)} 
                  className="btn-outline"
                >
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={submitting}
                  data-testid="submit-authorization-button"
                >
                  {submitting ? 'Creando...' : 'Crear Autorización'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Detalle de Autorización
              </DialogTitle>
            </DialogHeader>
            {selectedAuth && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Estado:</span>
                  <StatusBadge status={selectedAuth.status} />
                </div>
                
                <div className="border-t pt-4 space-y-3" style={{ borderColor: 'var(--border-card)' }}>
                  <h4 className="font-medium" style={{ color: 'var(--text-primary)' }}>Información del Gasto</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <span style={{ color: 'var(--text-secondary)' }}>Nombre:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{selectedAuth.expense_name}</span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Proveedor:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{selectedAuth.expense_provider || '-'}</span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Monto Total:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(selectedAuth.expense_amount)}</span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Pendiente:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(selectedAuth.expense_remaining)}</span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Vencimiento:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{formatDate(selectedAuth.expense_due_date)}</span>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-3" style={{ borderColor: 'var(--border-card)' }}>
                  <h4 className="font-medium" style={{ color: 'var(--text-primary)' }}>Autorización</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <span style={{ color: 'var(--text-secondary)' }}>Monto Autorizado:</span>
                    <span className="font-semibold" style={{ color: 'var(--primary-teal)' }}>
                      {formatCurrency(selectedAuth.amount_to_pay)}
                    </span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Cuenta:</span>
                    <span style={{ color: 'var(--text-primary)' }}>
                      {selectedAuth.bank_account_alias} ({selectedAuth.bank_name})
                    </span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Autorizado por:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{selectedAuth.authorized_by_name}</span>
                    
                    <span style={{ color: 'var(--text-secondary)' }}>Fecha autorización:</span>
                    <span style={{ color: 'var(--text-primary)' }}>{formatDate(selectedAuth.authorized_at)}</span>
                    
                    {selectedAuth.executed_by_name && (
                      <>
                        <span style={{ color: 'var(--text-secondary)' }}>Ejecutado por:</span>
                        <span style={{ color: 'var(--text-primary)' }}>{selectedAuth.executed_by_name}</span>
                        
                        <span style={{ color: 'var(--text-secondary)' }}>Fecha ejecución:</span>
                        <span style={{ color: 'var(--text-primary)' }}>{formatDate(selectedAuth.executed_at)}</span>
                      </>
                    )}
                  </div>
                  
                  {selectedAuth.notes && (
                    <div className="mt-3">
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Notas:</span>
                      <p className="mt-1 text-sm p-2 bg-slate-50 rounded" style={{ color: 'var(--text-primary)' }}>
                        {selectedAuth.notes}
                      </p>
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

        {/* Execute Confirmation Dialog */}
        <Dialog open={executeDialogOpen} onOpenChange={setExecuteDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                Ejecutar Pago
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Confirmas que deseas ejecutar este pago autorizado?
              </DialogDescription>
            </DialogHeader>
            {selectedAuth && (
              <Card className="bg-emerald-50 border-emerald-200">
                <CardContent className="p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-emerald-700">Gasto:</span>
                    <span className="font-medium text-emerald-900">{selectedAuth.expense_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-emerald-700">Monto a pagar:</span>
                    <span className="font-bold text-emerald-900">{formatCurrency(selectedAuth.amount_to_pay)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-emerald-700">Desde cuenta:</span>
                    <span className="font-medium text-emerald-900">{selectedAuth.bank_account_alias}</span>
                  </div>
                </CardContent>
              </Card>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setExecuteDialogOpen(false)} className="btn-outline">
                Cancelar
              </Button>
              <Button 
                onClick={handleExecute}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="confirm-execute-button"
              >
                {submitting ? 'Procesando...' : 'Confirmar Pago'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Cancel Confirmation Dialog */}
        <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <XCircle className="w-5 h-5 text-amber-600" />
                Cancelar Autorización
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de cancelar la autorización para "{selectedAuth?.expense_name}"?
                El gasto quedará disponible para una nueva autorización.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCancelDialogOpen(false)} className="btn-outline">
                No, mantener
              </Button>
              <Button 
                onClick={handleCancel}
                disabled={submitting}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="confirm-cancel-button"
              >
                {submitting ? 'Cancelando...' : 'Sí, cancelar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Autorización</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar esta autorización? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
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

export default AutorizacionPagos;
