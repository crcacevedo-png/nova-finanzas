import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { paymentAuthorizationApi, bankAccountApi, formatCurrency, formatDate } from '../services/api';
import { 
  Clock,
  CheckCircle,
  XCircle,
  Eye,
  Building2,
  Receipt,
  AlertTriangle,
  CreditCard,
  Banknote,
  FileText,
  Wallet
} from 'lucide-react';
import { Button } from '../components/ui/button';
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
import { Skeleton } from '../components/ui/skeleton';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast, Toaster } from 'sonner';

// Métodos de pago disponibles
const PAYMENT_METHODS = [
  { value: 'transferencia', label: 'Transferencia Bancaria', icon: Building2 },
  { value: 'efectivo', label: 'Efectivo', icon: Banknote },
  { value: 'cheque', label: 'Cheque', icon: FileText },
  { value: 'tarjeta', label: 'Tarjeta de Crédito/Débito', icon: CreditCard },
  { value: 'otro', label: 'Otro', icon: Wallet },
];

const AutorizacionesPendientes = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdmin = user?.role === 'admin';
  
  const [authorizations, setAuthorizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bankAccounts, setBankAccounts] = useState([]);
  const [statusFilter, setStatusFilter] = useState('pendiente');
  
  // Dialogs
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [payDialogOpen, setPayDialogOpen] = useState(false);
  
  // Selected
  const [selectedAuth, setSelectedAuth] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Payment form
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('transferencia');
  const [paymentReference, setPaymentReference] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');

  useEffect(() => {
    fetchAuthorizations();
    if (isSuperAdmin) {
      fetchBankAccounts();
    }
  }, [statusFilter]);

  const fetchAuthorizations = async () => {
    try {
      setLoading(true);
      const response = await paymentAuthorizationApi.getAll({ status: statusFilter !== 'all' ? statusFilter : undefined });
      setAuthorizations(response.data.data || response.data || []);
    } catch (error) {
      console.error('Error fetching authorizations:', error);
      toast.error('Error al cargar las autorizaciones');
    } finally {
      setLoading(false);
    }
  };

  const fetchBankAccounts = async () => {
    try {
      const response = await bankAccountApi.getAll();
      setBankAccounts(response.data.data || []);
    } catch (error) {
      console.error('Error fetching bank accounts:', error);
    }
  };

  const handleViewDetails = (auth) => {
    setSelectedAuth(auth);
    setDetailDialogOpen(true);
  };

  const handleOpenExecute = (auth) => {
    setSelectedAuth(auth);
    setExecuteDialogOpen(true);
  };

  const handleOpenCancel = (auth) => {
    setSelectedAuth(auth);
    setCancelDialogOpen(true);
  };

  const handleOpenPay = (auth) => {
    setSelectedAuth(auth);
    setSelectedPaymentMethod('transferencia');
    setPaymentReference('');
    setPaymentNotes('');
    setPayDialogOpen(true);
  };

  const handlePay = async () => {
    if (!selectedAuth) return;
    
    setSubmitting(true);
    try {
      await paymentAuthorizationApi.execute(selectedAuth.id, {
        payment_method: selectedPaymentMethod,
        reference: paymentReference,
        notes: paymentNotes
      });
      toast.success('Pago registrado correctamente');
      setPayDialogOpen(false);
      setSelectedAuth(null);
      fetchAuthorizations();
    } catch (error) {
      console.error('Error processing payment:', error);
      toast.error(error.response?.data?.detail || 'Error al procesar el pago');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedAuth) return;
    
    setSubmitting(true);
    try {
      await paymentAuthorizationApi.execute(selectedAuth.id);
      toast.success('Pago ejecutado correctamente');
      setExecuteDialogOpen(false);
      setSelectedAuth(null);
      fetchAuthorizations();
    } catch (error) {
      console.error('Error executing payment:', error);
      toast.error(error.response?.data?.detail || 'Error al ejecutar el pago');
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
      fetchAuthorizations();
    } catch (error) {
      console.error('Error canceling authorization:', error);
      toast.error(error.response?.data?.detail || 'Error al cancelar la autorización');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      pendiente: 'bg-amber-100 text-amber-700 border-0',
      ejecutado: 'bg-emerald-100 text-emerald-700 border-0',
      cancelado: 'bg-red-100 text-red-700 border-0'
    };
    const labels = {
      pendiente: 'Pendiente',
      ejecutado: 'Ejecutado',
      cancelado: 'Cancelado'
    };
    return <Badge className={colors[status]}>{labels[status]}</Badge>;
  };

  const getBankName = (bankAccountId) => {
    const bank = bankAccounts.find(b => b.id === bankAccountId);
    return bank ? bank.account_alias : bankAccountId;
  };

  // Contar pendientes
  const pendingCount = authorizations.filter(a => a.status === 'pendiente').length;

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="autorizaciones-pendientes-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Autorizaciones de Pago</h1>
            <p className="text-slate-500 text-sm">
              {isAdmin ? 'Ejecuta los pagos autorizados por el SuperAdmin' : 'Gestiona las autorizaciones de pago'}
            </p>
          </div>
          {pendingCount > 0 && statusFilter === 'pendiente' && (
            <Badge className="bg-amber-100 text-amber-700 text-base px-4 py-2">
              <Clock className="w-4 h-4 mr-2" />
              {pendingCount} pendiente{pendingCount > 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        {/* Filter */}
        <Card className="border border-slate-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-600">Filtrar por estado:</span>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[200px]" data-testid="status-filter">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pendiente">Pendientes</SelectItem>
                  <SelectItem value="ejecutado">Ejecutados</SelectItem>
                  <SelectItem value="cancelado">Cancelados</SelectItem>
                  <SelectItem value="all">Todos</SelectItem>
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
            ) : authorizations.length === 0 ? (
              <div className="p-12 text-center">
                <Receipt className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No hay autorizaciones {statusFilter !== 'all' ? `con estado "${statusFilter}"` : ''}</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">No. Gasto</TableHead>
                      <TableHead className="table-header">Gasto</TableHead>
                      <TableHead className="table-header">Monto a Pagar</TableHead>
                      <TableHead className="table-header">Cuenta Bancaria</TableHead>
                      <TableHead className="table-header">Estado</TableHead>
                      <TableHead className="table-header">Autorizado Por</TableHead>
                      <TableHead className="table-header">Fecha</TableHead>
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
                          <span className="font-mono text-sm font-semibold" style={{ color: 'var(--primary-teal)' }}>
                            {auth.expense_number || '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium text-slate-900">{auth.expense_name || 'N/A'}</p>
                            <p className="text-xs text-slate-500">{auth.expense_provider || 'Sin proveedor'}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <p className="font-semibold text-emerald-600">{formatCurrency(auth.amount_to_pay)}</p>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-slate-400" />
                            <div className="flex flex-col">
                              <span className="text-sm">{auth.bank_account_alias || 'N/A'}</span>
                              {auth.bank_name && <span className="text-xs text-slate-400">{auth.bank_name}</span>}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(auth.status)}</TableCell>
                        <TableCell>
                          <span className="text-sm text-slate-600">{auth.authorized_by_name || 'N/A'}</span>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-slate-500">{formatDate(auth.authorized_at)}</span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewDetails(auth)}
                              className="h-8 w-8 p-0 hover:bg-slate-100"
                              title="Ver detalles"
                              data-testid={`view-auth-${auth.id}`}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            
                            {/* Botón Pagar - Solo Admin y autorizaciones pendientes */}
                            {isAdmin && auth.status === 'pendiente' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenPay(auth)}
                                className="h-8 px-3 bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                                title="Pagar"
                                data-testid={`pay-auth-${auth.id}`}
                              >
                                <Wallet className="w-4 h-4 mr-1" />
                                Pagar
                              </Button>
                            )}
                            
                            {/* Botón Cancelar - Solo SuperAdmin y autorizaciones pendientes */}
                            {isSuperAdmin && auth.status === 'pendiente' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenCancel(auth)}
                                className="h-8 px-3 bg-red-100 text-red-700 hover:bg-red-200"
                                title="Cancelar autorización"
                                data-testid={`cancel-auth-${auth.id}`}
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Cancelar
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
        </Card>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Detalle de Autorización</DialogTitle>
            </DialogHeader>
            {selectedAuth && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-500">No. Gasto</p>
                    <p className="font-mono font-semibold" style={{ color: 'var(--primary-teal)' }}>
                      {selectedAuth.expense_number || '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Estado</p>
                    {getStatusBadge(selectedAuth.status)}
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Gasto</p>
                    <p className="font-medium">{selectedAuth.expense_name || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Proveedor</p>
                    <p className="font-medium">{selectedAuth.expense_provider || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Monto a Pagar</p>
                    <p className="font-semibold text-lg text-emerald-600">{formatCurrency(selectedAuth.amount_to_pay)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Cuenta Bancaria</p>
                    <p className="font-medium">{selectedAuth.bank_account_alias || 'N/A'}</p>
                    {selectedAuth.bank_name && <p className="text-xs text-slate-400">{selectedAuth.bank_name}</p>}
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Autorizado Por</p>
                    <p className="font-medium">{selectedAuth.authorized_by_name || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Fecha Autorización</p>
                    <p className="font-medium">{formatDate(selectedAuth.authorized_at)}</p>
                  </div>
                  {selectedAuth.executed_at && (
                    <>
                      <div>
                        <p className="text-sm text-slate-500">Ejecutado Por</p>
                        <p className="font-medium">{selectedAuth.executed_by_name || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-sm text-slate-500">Fecha Ejecución</p>
                        <p className="font-medium">{formatDate(selectedAuth.executed_at)}</p>
                      </div>
                    </>
                  )}
                </div>
                {selectedAuth.notes && (
                  <div>
                    <p className="text-sm text-slate-500">Notas</p>
                    <p className="text-sm bg-slate-50 p-3 rounded-lg">{selectedAuth.notes}</p>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Execute Dialog (legacy - mantener por compatibilidad) */}
        <Dialog open={executeDialogOpen} onOpenChange={setExecuteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
                Ejecutar Pago
              </DialogTitle>
              <DialogDescription>
                ¿Confirmas la ejecución de este pago? Esta acción registrará el pago en el sistema.
              </DialogDescription>
            </DialogHeader>
            {selectedAuth && (
              <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                <p className="font-medium text-emerald-900">{selectedAuth.expense_name}</p>
                <p className="text-2xl font-bold text-emerald-600 mt-1">{formatCurrency(selectedAuth.amount_to_pay)}</p>
                <p className="text-sm text-emerald-700 mt-2">
                  Cuenta: {selectedAuth.bank_account_alias}
                </p>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setExecuteDialogOpen(false)} disabled={submitting}>
                Cancelar
              </Button>
              <Button 
                onClick={handleExecute}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="confirm-execute-button"
              >
                {submitting ? 'Ejecutando...' : 'Confirmar Ejecución'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Pay Dialog - Nuevo diálogo con opciones de pago */}
        <Dialog open={payDialogOpen} onOpenChange={setPayDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <Wallet className="w-5 h-5 text-emerald-600" />
                Registrar Pago
              </DialogTitle>
              <DialogDescription>
                Selecciona el método de pago y completa los datos para registrar el pago.
              </DialogDescription>
            </DialogHeader>
            {selectedAuth && (
              <div className="space-y-4">
                {/* Resumen del pago */}
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                  <p className="font-medium text-emerald-900">{selectedAuth.expense_name}</p>
                  <p className="text-2xl font-bold text-emerald-600 mt-1">{formatCurrency(selectedAuth.amount_to_pay)}</p>
                  <p className="text-sm text-emerald-700 mt-2">
                    Cuenta destino: {selectedAuth.bank_account_alias}
                  </p>
                </div>

                {/* Método de pago */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Método de Pago</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {PAYMENT_METHODS.map((method) => {
                      const Icon = method.icon;
                      return (
                        <button
                          key={method.value}
                          type="button"
                          onClick={() => setSelectedPaymentMethod(method.value)}
                          className={`flex items-center gap-2 p-3 rounded-lg border transition-all ${
                            selectedPaymentMethod === method.value
                              ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                              : 'border-slate-200 hover:border-slate-300 text-slate-600'
                          }`}
                          data-testid={`payment-method-${method.value}`}
                        >
                          <Icon className="w-4 h-4" />
                          <span className="text-sm font-medium">{method.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Número de referencia */}
                <div className="space-y-2">
                  <Label htmlFor="reference" className="text-sm font-medium">
                    Número de Referencia / Comprobante
                  </Label>
                  <Input
                    id="reference"
                    placeholder={
                      selectedPaymentMethod === 'transferencia' ? 'Ej: TRF-123456' :
                      selectedPaymentMethod === 'cheque' ? 'Ej: CHQ-001234' :
                      selectedPaymentMethod === 'tarjeta' ? 'Últimos 4 dígitos' :
                      'Número de referencia'
                    }
                    value={paymentReference}
                    onChange={(e) => setPaymentReference(e.target.value)}
                    data-testid="payment-reference-input"
                  />
                </div>

                {/* Notas */}
                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-medium">
                    Notas adicionales (opcional)
                  </Label>
                  <Input
                    id="notes"
                    placeholder="Observaciones del pago..."
                    value={paymentNotes}
                    onChange={(e) => setPaymentNotes(e.target.value)}
                    data-testid="payment-notes-input"
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setPayDialogOpen(false)} disabled={submitting}>
                Cancelar
              </Button>
              <Button 
                onClick={handlePay}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="confirm-pay-button"
              >
                {submitting ? 'Procesando...' : 'Confirmar Pago'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Cancel Dialog */}
        <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                Cancelar Autorización
              </DialogTitle>
              <DialogDescription>
                ¿Estás seguro de cancelar esta autorización? El pago no será ejecutado.
              </DialogDescription>
            </DialogHeader>
            {selectedAuth && (
              <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                <p className="font-medium text-red-900">{selectedAuth.expense_name}</p>
                <p className="text-xl font-bold text-red-600 mt-1">{formatCurrency(selectedAuth.amount_to_pay)}</p>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setCancelDialogOpen(false)} disabled={submitting}>
                Volver
              </Button>
              <Button 
                variant="destructive"
                onClick={handleCancel}
                disabled={submitting}
                data-testid="confirm-cancel-button"
              >
                {submitting ? 'Cancelando...' : 'Cancelar Autorización'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AutorizacionesPendientes;
