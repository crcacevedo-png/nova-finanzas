import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  RefreshCw,
  ShoppingCart,
  Search,
  Eye,
  DollarSign,
  CreditCard,
  AlertCircle,
  X,
  Check,
  TrendingUp,
  FileSpreadsheet,
  FileText,
  Download,
  Stethoscope,
  Award,
  BarChart3,
  CalendarDays
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
  opticaSaleApi, 
  patientApi, 
  doctorApi, 
  frameApi, 
  contactLensApi,
  lensTypeApi,
  formatCurrency, 
  formatDate,
  opticaPaymentMethodLabels,
  saleStatusLabels
} from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

const OpticaVentas = () => {
  const { user, hasPermission } = useAuth();
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Data for dropdowns
  const [patients, setPatients] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [frames, setFrames] = useState([]);
  const [contactLenses, setContactLenses] = useState([]);
  const [lensTypes, setLensTypes] = useState([]);
  
  // Search states
  const [patientSearch, setPatientSearch] = useState('');
  const [doctorSearch, setDoctorSearch] = useState('');
  const [frameSearch, setFrameSearch] = useState('');
  
  // Form data
  const [formData, setFormData] = useState({
    patient_id: '',
    patient_name: '',
    doctor_id: '',
    doctor_name: '',
    frame_id: '',
    frame_info: '',
    frame_price: 0,
    contact_lens_id: '',
    contact_lens_info: '',
    contact_lens_price: 0,
    lens_items: [],
    payment_method: 'efectivo',
    discount_percent: 0,
    initial_payment: 0,
    notes: ''
  });
  
  // Payment form
  const [paymentData, setPaymentData] = useState({
    amount: '',
    payment_method: 'efectivo',
    reference: '',
    notes: ''
  });

  // Dashboard states
  const [dashboardStats, setDashboardStats] = useState({
    ventas_mes: 0,
    cobrado_mes: 0,
    ordenes_mes: 0,
    saldo_pendiente: 0,
    ordenes_pendientes: 0
  });
  const [monthlyChart, setMonthlyChart] = useState([]);
  const [topDoctors, setTopDoctors] = useState([]);
  const [topBrands, setTopBrands] = useState([]);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  
  // Report states
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportYear, setReportYear] = useState(new Date().getFullYear());
  const [reportMonth, setReportMonth] = useState(new Date().getMonth() + 1);
  const [exportingReport, setExportingReport] = useState(false);

  const canManage = hasPermission('manage_optica_sales');

  const fetchSales = useCallback(async () => {
    try {
      setLoading(true);
      const response = await opticaSaleApi.getAll({ 
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchTerm 
      });
      setSales(response.data.data || []);
    } catch (error) {
      console.error('Error fetching sales:', error);
      toast.error('Error al cargar las ventas');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  const fetchLensTypes = useCallback(async () => {
    try {
      const response = await lensTypeApi.getAll();
      setLensTypes(response.data.data || []);
    } catch (error) {
      console.error('Error fetching lens types:', error);
    }
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      setLoadingDashboard(true);
      const [statsRes, chartRes, doctorsRes, brandsRes] = await Promise.all([
        opticaSaleApi.getDashboardStats(),
        opticaSaleApi.getMonthlyChart(),
        opticaSaleApi.getTopDoctors(5),
        opticaSaleApi.getTopBrands(5)
      ]);
      setDashboardStats(statsRes.data);
      setMonthlyChart(chartRes.data);
      setTopDoctors(doctorsRes.data);
      setTopBrands(brandsRes.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  useEffect(() => {
    fetchSales();
    fetchLensTypes();
    fetchDashboard();
  }, [fetchSales, fetchLensTypes, fetchDashboard]);

  const handleExportReport = async (format) => {
    setExportingReport(true);
    try {
      const response = await opticaSaleApi.getMonthlyReport(reportYear, reportMonth, format);
      
      const blob = new Blob([response.data], { 
        type: format === 'excel' 
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/pdf'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ventas_optica_${reportYear}_${String(reportMonth).padStart(2, '0')}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Informe ${format.toUpperCase()} descargado exitosamente`);
      setReportDialogOpen(false);
    } catch (error) {
      console.error('Error exporting report:', error);
      toast.error('Error al exportar el informe');
    } finally {
      setExportingReport(false);
    }
  };

  // Search handlers
  const searchPatients = async (query) => {
    if (query.length < 2) return;
    try {
      const response = await patientApi.search(query, 10);
      setPatients(response.data || []);
    } catch (error) {
      console.error('Error searching patients:', error);
    }
  };

  const searchDoctors = async (query) => {
    if (query.length < 2) return;
    try {
      const response = await doctorApi.search(query, 10);
      setDoctors(response.data || []);
    } catch (error) {
      console.error('Error searching doctors:', error);
    }
  };

  const searchFrames = async (query) => {
    if (query.length < 1) return;
    try {
      const response = await frameApi.search(query, 10);
      setFrames(response.data || []);
    } catch (error) {
      console.error('Error searching frames:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      patient_id: '',
      patient_name: '',
      doctor_id: '',
      doctor_name: '',
      frame_id: '',
      frame_info: '',
      frame_price: 0,
      contact_lens_id: '',
      contact_lens_info: '',
      contact_lens_price: 0,
      lens_items: [],
      payment_method: 'efectivo',
      discount_percent: 0,
      initial_payment: 0,
      notes: ''
    });
    setPatientSearch('');
    setDoctorSearch('');
    setFrameSearch('');
    setPatients([]);
    setDoctors([]);
    setFrames([]);
  };

  const handleOpenDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  // Calculate totals
  const calculateTotals = () => {
    const frameTotal = formData.frame_price || 0;
    const contactLensTotal = formData.contact_lens_price || 0;
    const lensTotal = formData.lens_items.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    const subtotal = frameTotal + contactLensTotal + lensTotal;
    const discountAmount = subtotal * (formData.discount_percent / 100);
    const total = subtotal - discountAmount;
    return { subtotal, discountAmount, total, lensTotal };
  };

  const addLensItem = (lensType) => {
    const existing = formData.lens_items.find(item => item.lens_type_id === lensType.id);
    if (existing) {
      toast.error('Este tipo de lente ya está agregado');
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      lens_items: [...prev.lens_items, {
        lens_type_id: lensType.id,
        lens_type_name: lensType.name,
        quantity: 1,
        unit_price: lensType.default_price,
        subtotal: lensType.default_price
      }]
    }));
  };

  const updateLensItem = (index, field, value) => {
    setFormData(prev => {
      const items = [...prev.lens_items];
      items[index][field] = value;
      items[index].subtotal = items[index].unit_price * items[index].quantity;
      return { ...prev, lens_items: items };
    });
  };

  const removeLensItem = (index) => {
    setFormData(prev => ({
      ...prev,
      lens_items: prev.lens_items.filter((_, i) => i !== index)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.patient_id) {
      toast.error('Debe seleccionar un paciente');
      return;
    }
    
    if (!formData.frame_id && !formData.contact_lens_id && formData.lens_items.length === 0) {
      toast.error('Debe agregar al menos un producto');
      return;
    }

    const { total } = calculateTotals();
    if (formData.initial_payment > total) {
      toast.error('El pago inicial no puede ser mayor al total');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        patient_id: formData.patient_id,
        doctor_id: formData.doctor_id || null,
        frame_id: formData.frame_id || null,
        contact_lens_id: formData.contact_lens_id || null,
        lens_items: formData.lens_items.map(item => ({
          lens_type_id: item.lens_type_id,
          quantity: item.quantity,
          unit_price: item.unit_price,
          subtotal: item.subtotal
        })),
        payment_method: formData.payment_method,
        discount_percent: formData.discount_percent,
        initial_payment: formData.initial_payment || 0,
        notes: formData.notes
      };

      await opticaSaleApi.create(payload);
      toast.success('Venta creada exitosamente');
      setDialogOpen(false);
      fetchSales();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al crear la venta';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddPayment = async (e) => {
    e.preventDefault();
    
    if (!paymentData.amount || parseFloat(paymentData.amount) <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }

    setSubmitting(true);
    try {
      await opticaSaleApi.addPayment(selectedSale.id, {
        amount: parseFloat(paymentData.amount),
        payment_method: paymentData.payment_method,
        reference: paymentData.reference,
        notes: paymentData.notes
      });
      toast.success('Abono registrado exitosamente');
      setPaymentDialogOpen(false);
      setPaymentData({ amount: '', payment_method: 'efectivo', reference: '', notes: '' });
      fetchSales();
      
      // Refresh detail if open
      if (detailDialogOpen) {
        const response = await opticaSaleApi.getById(selectedSale.id);
        setSelectedSale(response.data);
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al registrar el abono';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    const classes = {
      pendiente: 'bg-amber-100 text-amber-700',
      pagado: 'bg-green-100 text-green-700',
      cancelado: 'bg-red-100 text-red-700'
    };
    return classes[status] || 'bg-gray-100 text-gray-700';
  };

  const { subtotal, discountAmount, total, lensTotal } = calculateTotals();

  const totalSales = sales.filter(s => s.status !== 'cancelado').reduce((sum, s) => sum + s.total, 0);
  const pendingBalance = sales.filter(s => s.status === 'pendiente').reduce((sum, s) => sum + s.balance_due, 0);

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="optica-ventas-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Ventas de Óptica
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestiona las ventas y órdenes de óptica
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setReportDialogOpen(true)} className="btn-outline" data-testid="export-report-button">
              <Download className="w-4 h-4 mr-2" />
              Exportar Informe
            </Button>
            <Button variant="outline" onClick={() => { fetchSales(); fetchDashboard(); }} className="btn-outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canManage && (
              <Button onClick={handleOpenDialog} className="btn-primary" data-testid="new-sale-button">
                <Plus className="w-4 h-4 mr-2" />
                Nueva Venta
              </Button>
            )}
          </div>
        </div>

        {/* Dashboard Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-teal-100">
                <TrendingUp className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Ventas del Mes</p>
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.ventas_mes)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-emerald-100">
                <DollarSign className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Cobrado Mes</p>
                <p className="text-lg font-bold text-emerald-600">
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.cobrado_mes)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-amber-100">
                <AlertCircle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Saldo Pendiente</p>
                <p className="text-lg font-bold text-amber-600">
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.saldo_pendiente)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-blue-100">
                <ShoppingCart className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Órdenes Mes</p>
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                  {loadingDashboard ? '...' : dashboardStats.ordenes_mes}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-orange-100">
                <CreditCard className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Pendientes</p>
                <p className="text-lg font-bold text-orange-600">
                  {loadingDashboard ? '...' : dashboardStats.ordenes_pendientes}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts and Rankings */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Monthly Chart */}
          <Card className="card-teal lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <BarChart3 className="w-4 h-4" />
                Ventas Últimos 6 Meses
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingDashboard ? (
                <Skeleton className="h-[200px] w-full" />
              ) : monthlyChart.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={monthlyChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="mes" tick={{ fontSize: 11 }} stroke="#6B7280" />
                    <YAxis tickFormatter={(v) => `Q${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} stroke="#6B7280" />
                    <Tooltip 
                      formatter={(value) => [formatCurrency(value), 'Ventas']}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }}
                    />
                    <Bar dataKey="ventas" fill="#0F6E56" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[200px] flex items-center justify-center">
                  <p style={{ color: 'var(--text-hint)' }}>Sin datos de ventas</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top Doctors & Brands */}
          <div className="space-y-4">
            {/* Top Doctors */}
            <Card className="card-teal">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Stethoscope className="w-4 h-4" />
                  Top Médicos
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                {loadingDashboard ? (
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                  </div>
                ) : topDoctors.length > 0 ? (
                  <div className="space-y-2">
                    {topDoctors.slice(0, 3).map((doc, i) => (
                      <div key={doc.doctor_id} className="flex items-center justify-between py-1">
                        <div className="flex items-center gap-2">
                          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                            i === 0 ? 'bg-yellow-100 text-yellow-700' : 
                            i === 1 ? 'bg-gray-100 text-gray-600' : 'bg-orange-100 text-orange-700'
                          }`}>
                            {i + 1}
                          </span>
                          <span className="text-sm truncate max-w-[120px]" style={{ color: 'var(--text-primary)' }}>
                            {doc.doctor_name}
                          </span>
                        </div>
                        <span className="text-xs font-semibold" style={{ color: 'var(--primary-teal)' }}>
                          {doc.count} ventas
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-center py-2" style={{ color: 'var(--text-hint)' }}>Sin datos</p>
                )}
              </CardContent>
            </Card>

            {/* Top Brands */}
            <Card className="card-teal">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Award className="w-4 h-4" />
                  Top Marcas Aros
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                {loadingDashboard ? (
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
                  </div>
                ) : topBrands.length > 0 ? (
                  <div className="space-y-2">
                    {topBrands.slice(0, 3).map((brand, i) => (
                      <div key={brand.brand} className="flex items-center justify-between py-1">
                        <div className="flex items-center gap-2">
                          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                            i === 0 ? 'bg-yellow-100 text-yellow-700' : 
                            i === 1 ? 'bg-gray-100 text-gray-600' : 'bg-orange-100 text-orange-700'
                          }`}>
                            {i + 1}
                          </span>
                          <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                            {brand.brand}
                          </span>
                        </div>
                        <span className="text-xs font-semibold" style={{ color: 'var(--primary-teal)' }}>
                          {brand.count} ventas
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-center py-2" style={{ color: 'var(--text-hint)' }}>Sin datos</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Filters */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por cliente, orden o médico..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px] input-teal">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pendiente">Pendientes</SelectItem>
                  <SelectItem value="pagado">Pagados</SelectItem>
                  <SelectItem value="cancelado">Cancelados</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Ventas ({sales.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : sales.length === 0 ? (
              <div className="p-12 text-center">
                <ShoppingCart className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay ventas registradas</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Orden</TableHead>
                      <TableHead className="table-header">Fecha</TableHead>
                      <TableHead className="table-header">Cliente</TableHead>
                      <TableHead className="table-header">Médico</TableHead>
                      <TableHead className="table-header text-right">Total</TableHead>
                      <TableHead className="table-header text-right">Saldo</TableHead>
                      <TableHead className="table-header text-center">Estado</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sales.map((sale) => (
                      <TableRow key={sale.id} className="table-row-hover">
                        <TableCell>
                          <span className="font-mono text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                            {sale.order_number}
                          </span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {formatDate(sale.created_at)}
                        </TableCell>
                        <TableCell>
                          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                            {sale.patient_name}
                          </span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {sale.doctor_name || '-'}
                        </TableCell>
                        <TableCell className="text-right font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {formatCurrency(sale.total)}
                        </TableCell>
                        <TableCell className="text-right">
                          {sale.balance_due > 0 ? (
                            <span className="text-amber-600 font-semibold">{formatCurrency(sale.balance_due)}</span>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className={getStatusBadgeClass(sale.status)}>
                            {saleStatusLabels[sale.status] || sale.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => { setSelectedSale(sale); setDetailDialogOpen(true); }}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {canManage && sale.status === 'pendiente' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { 
                                  setSelectedSale(sale); 
                                  setPaymentData({ amount: sale.balance_due.toString(), payment_method: 'efectivo', reference: '', notes: '' });
                                  setPaymentDialogOpen(true); 
                                }}
                                className="h-8 w-8 p-0 hover:bg-green-100 hover:text-green-600"
                              >
                                <CreditCard className="w-4 h-4" />
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

        {/* New Sale Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Nueva Venta</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                Completa los datos de la venta
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Patient Selection */}
              <div className="space-y-2">
                <Label>Cliente *</Label>
                <div className="relative">
                  <Input
                    value={patientSearch}
                    onChange={(e) => { setPatientSearch(e.target.value); searchPatients(e.target.value); }}
                    placeholder="Buscar paciente por nombre o DPI..."
                    className="input-teal"
                    data-testid="patient-search"
                  />
                  {patients.length > 0 && patientSearch.length >= 2 && !formData.patient_id && (
                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                      {patients.map((p) => (
                        <div
                          key={p.id}
                          className="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, patient_id: p.id, patient_name: p.full_name }));
                            setPatientSearch(p.full_name);
                            setPatients([]);
                          }}
                        >
                          <p className="font-medium">{p.full_name}</p>
                          <p className="text-xs text-gray-500">{p.record_number} - {p.phone}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {formData.patient_id && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <Check className="w-4 h-4" />
                    <span>Cliente seleccionado: {formData.patient_name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => { setFormData(prev => ({ ...prev, patient_id: '', patient_name: '' })); setPatientSearch(''); }}
                      className="h-6 px-2"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>

              {/* Doctor Selection */}
              <div className="space-y-2">
                <Label>Médico Referente</Label>
                <div className="relative">
                  <Input
                    value={doctorSearch}
                    onChange={(e) => { setDoctorSearch(e.target.value); searchDoctors(e.target.value); }}
                    placeholder="Buscar médico..."
                    className="input-teal"
                  />
                  {doctors.length > 0 && doctorSearch.length >= 2 && !formData.doctor_id && (
                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                      {doctors.map((d) => (
                        <div
                          key={d.id}
                          className="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, doctor_id: d.id, doctor_name: d.name }));
                            setDoctorSearch(d.name);
                            setDoctors([]);
                          }}
                        >
                          <p className="font-medium">{d.name}</p>
                          <p className="text-xs text-gray-500">{d.specialty}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {formData.doctor_id && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <Check className="w-4 h-4" />
                    <span>{formData.doctor_name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => { setFormData(prev => ({ ...prev, doctor_id: '', doctor_name: '' })); setDoctorSearch(''); }}
                      className="h-6 px-2"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>

              {/* Frame Selection */}
              <div className="space-y-2">
                <Label>Aro</Label>
                <div className="relative">
                  <Input
                    value={frameSearch}
                    onChange={(e) => { setFrameSearch(e.target.value); searchFrames(e.target.value); }}
                    placeholder="Buscar aro por código o marca..."
                    className="input-teal"
                  />
                  {frames.length > 0 && frameSearch.length >= 1 && !formData.frame_id && (
                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                      {frames.map((f) => (
                        <div
                          key={f.id}
                          className="px-3 py-2 hover:bg-gray-100 cursor-pointer flex justify-between items-center"
                          onClick={() => {
                            setFormData(prev => ({ 
                              ...prev, 
                              frame_id: f.id, 
                              frame_info: f.label, 
                              frame_price: f.sale_price 
                            }));
                            setFrameSearch(f.label);
                            setFrames([]);
                          }}
                        >
                          <div>
                            <p className="font-medium">{f.label}</p>
                            <p className="text-xs text-gray-500">Stock: {f.stock}</p>
                          </div>
                          <span className="font-semibold text-teal-600">{formatCurrency(f.sale_price)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {formData.frame_id && (
                  <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <Check className="w-4 h-4" />
                      <span>{formData.frame_info}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{formatCurrency(formData.frame_price)}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => { setFormData(prev => ({ ...prev, frame_id: '', frame_info: '', frame_price: 0 })); setFrameSearch(''); }}
                        className="h-6 px-2"
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Lens Types */}
              <div className="space-y-2">
                <Label>Tipos de Lente</Label>
                <Select onValueChange={(value) => {
                  const lensType = lensTypes.find(lt => lt.id === value);
                  if (lensType) addLensItem(lensType);
                }}>
                  <SelectTrigger className="input-teal">
                    <SelectValue placeholder="Agregar tipo de lente..." />
                  </SelectTrigger>
                  <SelectContent>
                    {lensTypes.map((lt) => (
                      <SelectItem key={lt.id} value={lt.id}>
                        {lt.name} - {formatCurrency(lt.default_price)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                {formData.lens_items.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {formData.lens_items.map((item, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                        <span className="flex-1 text-sm">{item.lens_type_name}</span>
                        <Input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) => updateLensItem(index, 'quantity', parseInt(e.target.value) || 1)}
                          className="w-16 h-8 text-center"
                        />
                        <span className="text-xs">x</span>
                        <Input
                          type="number"
                          step="0.01"
                          value={item.unit_price}
                          onChange={(e) => updateLensItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                          className="w-24 h-8"
                        />
                        <span className="font-semibold text-sm w-24 text-right">{formatCurrency(item.subtotal)}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeLensItem(index)}
                          className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Totals and Payment */}
              <div className="border-t pt-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span>Aro:</span>
                  <span>{formatCurrency(formData.frame_price)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Lentes:</span>
                  <span>{formatCurrency(lensTotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Subtotal:</span>
                  <span className="font-semibold">{formatCurrency(subtotal)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Descuento (%):</span>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      value={formData.discount_percent}
                      onChange={(e) => setFormData(prev => ({ ...prev, discount_percent: parseFloat(e.target.value) || 0 }))}
                      className="w-20 h-8 text-center"
                    />
                    <span className="text-red-600">-{formatCurrency(discountAmount)}</span>
                  </div>
                </div>
                <div className="flex justify-between text-lg font-bold border-t pt-2">
                  <span>TOTAL:</span>
                  <span style={{ color: 'var(--primary-teal)' }}>{formatCurrency(total)}</span>
                </div>
              </div>

              {/* Payment Method and Initial Payment */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Método de Pago</Label>
                  <Select
                    value={formData.payment_method}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, payment_method: value }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(opticaPaymentMethodLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Pago Inicial</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max={total}
                    value={formData.initial_payment}
                    onChange={(e) => setFormData(prev => ({ ...prev, initial_payment: parseFloat(e.target.value) || 0 }))}
                    className="input-teal"
                    placeholder="0.00"
                  />
                </div>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label>Notas</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  className="input-teal"
                  placeholder="Observaciones..."
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="submit-sale">
                  {submitting ? 'Guardando...' : 'Crear Venta'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Sale Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Detalle de Venta
              </DialogTitle>
            </DialogHeader>
            {selectedSale && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-lg font-bold">{selectedSale.order_number}</span>
                  <Badge className={getStatusBadgeClass(selectedSale.status)}>
                    {saleStatusLabels[selectedSale.status]}
                  </Badge>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Cliente</p>
                    <p className="font-medium">{selectedSale.patient_name}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Médico</p>
                    <p className="font-medium">{selectedSale.doctor_name || '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Fecha</p>
                    <p>{formatDate(selectedSale.created_at)}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Método de Pago</p>
                    <p>{opticaPaymentMethodLabels[selectedSale.payment_method]}</p>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-2">
                  <p className="font-semibold">Productos</p>
                  {selectedSale.frame_info && (
                    <div className="flex justify-between text-sm">
                      <span>Aro: {selectedSale.frame_info}</span>
                      <span>{formatCurrency(selectedSale.frame_price)}</span>
                    </div>
                  )}
                  {selectedSale.lens_items?.map((item, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span>{item.lens_type_name} x{item.quantity}</span>
                      <span>{formatCurrency(item.subtotal)}</span>
                    </div>
                  ))}
                </div>

                <div className="border-t pt-4 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span>{formatCurrency(selectedSale.subtotal)}</span>
                  </div>
                  {selectedSale.discount_amount > 0 && (
                    <div className="flex justify-between text-red-600">
                      <span>Descuento ({selectedSale.discount_percent}%):</span>
                      <span>-{formatCurrency(selectedSale.discount_amount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2">
                    <span>Total:</span>
                    <span>{formatCurrency(selectedSale.total)}</span>
                  </div>
                  <div className="flex justify-between text-green-600">
                    <span>Pagado:</span>
                    <span>{formatCurrency(selectedSale.total_paid)}</span>
                  </div>
                  {selectedSale.balance_due > 0 && (
                    <div className="flex justify-between text-amber-600 font-semibold">
                      <span>Saldo Pendiente:</span>
                      <span>{formatCurrency(selectedSale.balance_due)}</span>
                    </div>
                  )}
                </div>

                {selectedSale.payments?.length > 0 && (
                  <div className="border-t pt-4">
                    <p className="font-semibold mb-2">Historial de Pagos</p>
                    {selectedSale.payments.map((payment, i) => (
                      <div key={i} className="text-sm flex justify-between py-1 border-b last:border-0">
                        <div>
                          <span>{formatDate(payment.created_at)}</span>
                          <span className="text-gray-500 ml-2">({opticaPaymentMethodLabels[payment.payment_method]})</span>
                        </div>
                        <span className="font-medium text-green-600">{formatCurrency(payment.amount)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <DialogFooter>
              {canManage && selectedSale?.status === 'pendiente' && (
                <Button
                  onClick={() => {
                    setPaymentData({ amount: selectedSale.balance_due.toString(), payment_method: 'efectivo', reference: '', notes: '' });
                    setPaymentDialogOpen(true);
                  }}
                  className="btn-primary"
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  Registrar Abono
                </Button>
              )}
              <Button variant="outline" onClick={() => setDetailDialogOpen(false)} className="btn-outline">
                Cerrar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Payment Dialog */}
        <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle>Registrar Abono</DialogTitle>
              <DialogDescription>
                Orden: {selectedSale?.order_number} - Saldo: {selectedSale && formatCurrency(selectedSale.balance_due)}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddPayment} className="space-y-4">
              <div className="space-y-2">
                <Label>Monto *</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={selectedSale?.balance_due}
                  value={paymentData.amount}
                  onChange={(e) => setPaymentData(prev => ({ ...prev, amount: e.target.value }))}
                  className="input-teal"
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Método de Pago</Label>
                <Select
                  value={paymentData.payment_method}
                  onValueChange={(value) => setPaymentData(prev => ({ ...prev, payment_method: value }))}
                >
                  <SelectTrigger className="input-teal">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="tarjeta">Tarjeta</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="cheque">Cheque</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Referencia</Label>
                <Input
                  value={paymentData.reference}
                  onChange={(e) => setPaymentData(prev => ({ ...prev, reference: e.target.value }))}
                  className="input-teal"
                  placeholder="Número de transacción, cheque, etc."
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setPaymentDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Guardando...' : 'Registrar Abono'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Export Report Dialog */}
        <Dialog open={reportDialogOpen} onOpenChange={setReportDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CalendarDays className="w-5 h-5" />
                Exportar Informe Mensual
              </DialogTitle>
              <DialogDescription>
                Selecciona el mes y formato para exportar
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Año</Label>
                  <Select value={reportYear.toString()} onValueChange={(v) => setReportYear(parseInt(v))}>
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[2024, 2025, 2026].map(y => (
                        <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Mes</Label>
                  <Select value={reportMonth.toString()} onValueChange={(v) => setReportMonth(parseInt(v))}>
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'].map((m, i) => (
                        <SelectItem key={i + 1} value={(i + 1).toString()}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <Button 
                  onClick={() => handleExportReport('excel')} 
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                  disabled={exportingReport}
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  {exportingReport ? 'Exportando...' : 'Excel'}
                </Button>
                <Button 
                  onClick={() => handleExportReport('pdf')} 
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                  disabled={exportingReport}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  {exportingReport ? 'Exportando...' : 'PDF'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default OpticaVentas;
