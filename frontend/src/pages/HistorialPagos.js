import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { paymentApi, formatCurrency, formatDate, paymentMethodLabels } from '../services/api';
import { 
  Search, 
  Trash2,
  Calendar,
  CreditCard,
  FileText,
  ChevronLeft,
  ChevronRight,
  Filter
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
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
import { toast, Toaster } from 'sonner';
import { useAuth } from '../context/AuthContext';

const HistorialPagos = () => {
  const { canDeletePayments } = useAuth();
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [paymentToDelete, setPaymentToDelete] = useState(null);
  
  // Filters
  const [filters, setFilters] = useState({
    search: '',
    method: '',
    dateFrom: '',
    dateTo: ''
  });
  
  // Pagination
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0
  });

  useEffect(() => {
    fetchPayments();
  }, [pagination.page, filters.method]);

  const fetchPayments = async () => {
    try {
      const response = await paymentApi.getAll();
      let data = response.data;
      
      // Handle paginated response
      if (data.data) {
        setPayments(data.data);
        setPagination(prev => ({
          ...prev,
          total: data.total || data.data.length,
          totalPages: data.total_pages || Math.ceil(data.data.length / prev.limit)
        }));
      } else {
        setPayments(data);
        setPagination(prev => ({
          ...prev,
          total: data.length,
          totalPages: Math.ceil(data.length / prev.limit)
        }));
      }
    } catch (error) {
      console.error('Error fetching payments:', error);
      toast.error('Error al cargar el historial de pagos');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPagination(prev => ({ ...prev, page: 1 }));
    fetchPayments();
  };

  const handleDeleteClick = (payment) => {
    setPaymentToDelete(payment);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!paymentToDelete) return;

    try {
      await paymentApi.delete(paymentToDelete.id);
      toast.success('Pago eliminado correctamente');
      fetchPayments();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar el pago';
      toast.error(message);
    } finally {
      setDeleteDialogOpen(false);
      setPaymentToDelete(null);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      setPagination(prev => ({ ...prev, page: newPage }));
    }
  };

  const getMethodBadge = (method) => {
    const colors = {
      'Efectivo': 'bg-[#E1F5EE] text-[#0F6E56] border-0',
      'Transferencia bancaria': 'bg-[#E6F0FA] text-[#2B5EA7] border-0',
      'Tarjeta de crédito': 'bg-[#E1F5EE] text-[#085041] border-0',
      'Tarjeta de débito': 'bg-[#E6F0FA] text-[#2B5EA7] border-0',
      'Cheque': 'bg-[#FEF4E0] text-[#8B6914] border-0'
    };
    return <Badge className={colors[method] || 'bg-slate-50 text-slate-700'}>{method}</Badge>;
  };

  // Filter payments locally
  const filteredPayments = payments.filter(payment => {
    let matches = true;
    
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      matches = matches && (
        payment.expense_name?.toLowerCase().includes(searchLower) ||
        payment.reference?.toLowerCase().includes(searchLower)
      );
    }
    
    if (filters.method) {
      matches = matches && payment.method === filters.method;
    }
    
    if (filters.dateFrom) {
      matches = matches && new Date(payment.date) >= new Date(filters.dateFrom);
    }
    
    if (filters.dateTo) {
      matches = matches && new Date(payment.date) <= new Date(filters.dateTo);
    }
    
    return matches;
  });

  // Paginate filtered results
  const paginatedPayments = filteredPayments.slice(
    (pagination.page - 1) * pagination.limit,
    pagination.page * pagination.limit
  );

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="historial-pagos-page">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Historial de Pagos</h1>
          <p className="text-slate-500 text-sm">Consulta todos los pagos realizados</p>
        </div>

        {/* Filters */}
        <Card className="border border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Buscar por gasto o referencia..."
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10"
                  data-testid="search-payment-input"
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
                  value={filters.method || "all"}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, method: value === "all" ? "" : value }))}
                >
                  <SelectTrigger className="w-[180px]" data-testid="method-filter">
                    <SelectValue placeholder="Método de pago" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los métodos</SelectItem>
                    {paymentMethodLabels.map(method => (
                      <SelectItem key={method} value={method}>{method}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={handleSearch} className="px-6">
                  <Filter className="w-4 h-4 mr-2" />
                  Filtrar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#E1F5EE]">
                <CreditCard className="w-5 h-5 text-[#0F6E56]" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Pagos</p>
                <p className="text-lg font-bold text-slate-900">{filteredPayments.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#E1F5EE]">
                <FileText className="w-5 h-5 text-[#085041]" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Monto Total</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(filteredPayments.reduce((sum, p) => sum + p.amount, 0))}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#FEF4E0]">
                <Calendar className="w-5 h-5 text-[#8B6914]" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Último Pago</p>
                <p className="text-lg font-bold text-slate-900">
                  {filteredPayments.length > 0 
                    ? formatDate(filteredPayments[0]?.date)
                    : '-'
                  }
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Table */}
        <Card className="border border-slate-200">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : paginatedPayments.length === 0 ? (
              <div className="p-12 text-center">
                <CreditCard className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No se encontraron pagos</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead className="font-semibold text-slate-600">Fecha</TableHead>
                      <TableHead className="font-semibold text-slate-600">Gasto</TableHead>
                      <TableHead className="font-semibold text-slate-600">Monto</TableHead>
                      <TableHead className="font-semibold text-slate-600">Método</TableHead>
                      <TableHead className="font-semibold text-slate-600">Referencia</TableHead>
                      <TableHead className="font-semibold text-slate-600">Registrado por</TableHead>
                      {canDeletePayments() && (
                        <TableHead className="font-semibold text-slate-600 text-right">Acciones</TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedPayments.map((payment) => (
                      <TableRow 
                        key={payment.id} 
                        className="table-row-hover"
                        data-testid={`payment-row-${payment.id}`}
                      >
                        <TableCell className="text-slate-600">
                          {formatDate(payment.date)}
                        </TableCell>
                        <TableCell>
                          <p className="font-medium text-slate-900">{payment.expense_name || 'N/A'}</p>
                        </TableCell>
                        <TableCell>
                          <p className="font-semibold text-[#0F6E56]">{formatCurrency(payment.amount)}</p>
                        </TableCell>
                        <TableCell>{getMethodBadge(payment.method)}</TableCell>
                        <TableCell className="text-slate-600">
                          {payment.reference || '-'}
                        </TableCell>
                        <TableCell className="text-slate-600 text-sm">
                          {payment.created_by_name || '-'}
                        </TableCell>
                        {canDeletePayments() && (
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(payment)}
                              className="h-8 w-8 p-0 hover:bg-rose-50 hover:text-rose-700"
                              data-testid={`delete-payment-${payment.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
          
          {/* Pagination */}
          {filteredPayments.length > pagination.limit && (
            <div className="p-4 border-t border-slate-200 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                Mostrando {((pagination.page - 1) * pagination.limit) + 1} - {Math.min(pagination.page * pagination.limit, filteredPayments.length)} de {filteredPayments.length} pagos
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
                  Página {pagination.page} de {Math.ceil(filteredPayments.length / pagination.limit)}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page >= Math.ceil(filteredPayments.length / pagination.limit)}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </Card>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Pago</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar este pago de {paymentToDelete && formatCurrency(paymentToDelete.amount)}? 
                Esta acción no se puede deshacer y actualizará el saldo del gasto asociado.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleConfirmDelete} data-testid="confirm-delete-payment-button">
                Eliminar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default HistorialPagos;
