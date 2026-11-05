import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import {
  RefreshCw,
  ShoppingCart,
  Search,
  Eye,
  DollarSign,
  AlertCircle,
  X,
  TrendingUp,
  FileSpreadsheet,
  FileText,
  Download,
  Stethoscope,
  Package,
  Tags,
  BarChart3,
  CalendarDays,
  Ban,
  Receipt
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { FELButton } from '../components/FELButton';
import { toast, Toaster } from 'sonner';
import { ventasApi, formatCurrency, formatDate, getGuatemalaDate } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

const estadoLabels = { completada: 'Completada', anulada: 'Anulada' };

const VentasClinica = () => {
  const { user } = useAuth();
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Dashboard
  const [dashboardStats, setDashboardStats] = useState({
    ventas_mes: 0, ordenes_mes: 0, ticket_promedio: 0, ventas_hoy: 0, ordenes_hoy: 0, anuladas_mes: 0
  });
  const [monthlyChart, setMonthlyChart] = useState([]);
  const [topMedicos, setTopMedicos] = useState([]);
  const [topProductos, setTopProductos] = useState([]);
  const [topCategorias, setTopCategorias] = useState([]);
  const [loadingDashboard, setLoadingDashboard] = useState(true);

  // Anular
  const [anularDialogOpen, setAnularDialogOpen] = useState(false);
  const [anularMotivo, setAnularMotivo] = useState('');
  const [devolverInventario, setDevolverInventario] = useState(true);
  const [anulando, setAnulando] = useState(false);

  // Report
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [reportYear, setReportYear] = useState(parseInt(getGuatemalaDate().split('-')[0], 10));
  const [reportMonth, setReportMonth] = useState(parseInt(getGuatemalaDate().split('-')[1], 10));
  const [exportingReport, setExportingReport] = useState(false);

  const isAdminOrSuperAdmin = user?.role === 'admin' || user?.role === 'superadmin';

  const fetchSales = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter !== 'all') params.estado = statusFilter;
      if (searchTerm) params.search = searchTerm;
      if (dateFrom) params.fecha_desde = dateFrom;
      if (dateTo) params.fecha_hasta = dateTo;
      params.limit = 200;
      const response = await ventasApi.getAll(params);
      setSales(response.data.data || []);
    } catch (error) {
      console.error('Error fetching sales:', error);
      toast.error('Error al cargar las ventas');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm, dateFrom, dateTo]);

  const fetchDashboard = useCallback(async () => {
    try {
      setLoadingDashboard(true);
      const [statsRes, chartRes, medRes, prodRes, catRes] = await Promise.all([
        ventasApi.getDashboardStats(),
        ventasApi.getMonthlyChart(),
        ventasApi.getTopMedicos(5),
        ventasApi.getTopProductos(5),
        ventasApi.getTopCategorias(5)
      ]);
      setDashboardStats(statsRes.data);
      setMonthlyChart(chartRes.data);
      setTopMedicos(medRes.data);
      setTopProductos(prodRes.data);
      setTopCategorias(catRes.data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoadingDashboard(false);
    }
  }, []);

  useEffect(() => {
    fetchSales();
  }, [fetchSales]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const refreshAll = () => { fetchSales(); fetchDashboard(); };

  const openDetail = async (sale) => {
    try {
      const r = await ventasApi.getById(sale.id);
      setSelectedSale(r.data);
    } catch (e) {
      setSelectedSale(sale);
    }
    setDetailDialogOpen(true);
  };

  const refreshDetail = async () => {
    if (!selectedSale) return;
    try {
      const r = await ventasApi.getById(selectedSale.id);
      setSelectedSale(r.data);
    } catch (e) { /* noop */ }
  };

  const handleAnular = async () => {
    if (anularMotivo.trim().length < 5) {
      toast.error('El motivo debe tener al menos 5 caracteres');
      return;
    }
    setAnulando(true);
    try {
      await ventasApi.anular(selectedSale.id, {
        motivo: anularMotivo.trim(),
        devolver_inventario: devolverInventario
      });
      toast.success('Venta anulada correctamente');
      setAnularDialogOpen(false);
      setDetailDialogOpen(false);
      setAnularMotivo('');
      setDevolverInventario(true);
      refreshAll();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo anular la venta');
    } finally {
      setAnulando(false);
    }
  };

  const handleExportReport = async (format) => {
    setExportingReport(true);
    try {
      const response = await ventasApi.getMonthlyReport(reportYear, reportMonth, format);
      const blob = new Blob([response.data], {
        type: format === 'excel'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/pdf'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ventas_clinica_${reportYear}_${String(reportMonth).padStart(2, '0')}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success(`Informe ${format.toUpperCase()} descargado`);
      setReportDialogOpen(false);
    } catch (error) {
      toast.error('Error al exportar el informe');
    } finally {
      setExportingReport(false);
    }
  };

  const handlePrintTicket = (sale) => {
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    const rows = (sale.items || []).map(it =>
      `<tr><td>${esc(it.nombre)}</td><td style="text-align:center">${it.cantidad || 1}</td><td style="text-align:right">${formatCurrency(it.subtotal || 0)}</td></tr>`
    ).join('');
    const pagos = (sale.formas_pago || []).map(fp =>
      `<div style="text-align:right">${esc(fp.metodo)}: ${formatCurrency(fp.monto || 0)}</div>`
    ).join('');
    const win = window.open('', '_blank', 'width=400,height=600');
    if (!win) { toast.error('Permite las ventanas emergentes para imprimir'); return; }
    win.document.write(`
      <html><head><title>Ticket ${esc(sale.numero_venta)}</title>
      <style>body{font-family:monospace;font-size:12px;padding:12px;color:#111}h2{text-align:center;margin:4px 0}table{width:100%;border-collapse:collapse;margin-top:8px}td,th{padding:3px 0;border-bottom:1px dashed #ccc}.tot{font-weight:bold;font-size:14px}</style>
      </head><body>
      <h2>NovaVisión Clínica</h2>
      <div style="text-align:center">Comprobante de Venta</div>
      <hr/>
      <div>Orden: <b>${esc(sale.numero_venta)}</b></div>
      <div>Fecha: ${esc(formatDate(sale.fecha))}</div>
      <div>Cliente: ${esc(sale.paciente_nombre || 'Consumidor Final')}</div>
      ${sale.medico_nombre ? `<div>Médico: ${esc(sale.medico_nombre)}</div>` : ''}
      ${sale.estado === 'anulada' ? '<div style="color:#b91c1c;font-weight:bold">** ANULADA **</div>' : ''}
      <table><thead><tr><th style="text-align:left">Detalle</th><th>Cant</th><th style="text-align:right">Subtotal</th></tr></thead><tbody>${rows}</tbody></table>
      <hr/>
      <div class="tot" style="text-align:right">TOTAL: ${formatCurrency(sale.total || 0)}</div>
      ${pagos}
      <hr/><div style="text-align:center">¡Gracias por su compra!</div>
      <script>window.onload=function(){window.print();}</script>
      </body></html>`);
    win.document.close();
  };

  const getStatusBadgeClass = (estado) => {
    const classes = {
      completada: 'bg-green-100 text-green-700',
      anulada: 'bg-red-100 text-red-700'
    };
    return classes[estado] || 'bg-gray-100 text-gray-700';
  };

  const RankingRow = ({ i, name, value }) => (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
          i === 0 ? 'bg-yellow-100 text-yellow-700' :
          i === 1 ? 'bg-gray-100 text-gray-600' : 'bg-orange-100 text-orange-700'
        }`}>{i + 1}</span>
        <span className="text-sm truncate max-w-[130px]" style={{ color: 'var(--text-primary)' }}>{name}</span>
      </div>
      <span className="text-xs font-semibold" style={{ color: 'var(--primary-teal)' }}>{value}</span>
    </div>
  );

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="ventas-clinica-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Ventas de Clínica
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Revisión y análisis de las ventas del punto de venta
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setReportDialogOpen(true)} className="btn-outline" data-testid="export-report-button">
              <Download className="w-4 h-4 mr-2" />
              Exportar Informe
            </Button>
            <Button variant="outline" onClick={refreshAll} className="btn-outline" data-testid="refresh-button">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-blue-100"><TrendingUp className="w-5 h-5 text-blue-600" /></div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Ventas del Mes</p>
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }} data-testid="stat-ventas-mes">
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.ventas_mes)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-indigo-100"><ShoppingCart className="w-5 h-5 text-indigo-600" /></div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Órdenes Mes</p>
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }} data-testid="stat-ordenes-mes">
                  {loadingDashboard ? '...' : dashboardStats.ordenes_mes}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-emerald-100"><DollarSign className="w-5 h-5 text-emerald-600" /></div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Ticket Promedio</p>
                <p className="text-lg font-bold text-emerald-600" data-testid="stat-ticket-promedio">
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.ticket_promedio)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-teal-100"><Receipt className="w-5 h-5 text-teal-600" /></div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Ventas Hoy</p>
                <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }} data-testid="stat-ventas-hoy">
                  {loadingDashboard ? '...' : formatCurrency(dashboardStats.ventas_hoy)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-3 rounded-xl bg-red-100"><AlertCircle className="w-5 h-5 text-red-600" /></div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Anuladas Mes</p>
                <p className="text-lg font-bold text-red-600" data-testid="stat-anuladas-mes">
                  {loadingDashboard ? '...' : dashboardStats.anuladas_mes}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Chart + Rankings */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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
                    <YAxis tickFormatter={(v) => `Q${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} stroke="#6B7280" />
                    <Tooltip formatter={(value) => [formatCurrency(value), 'Ventas']} contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }} />
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

          {/* Rankings con pestañas */}
          <Card className="card-teal">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Rankings del Mes
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Tabs defaultValue="medicos">
                <TabsList className="grid grid-cols-3 w-full mb-2">
                  <TabsTrigger value="medicos" className="text-xs" data-testid="tab-top-medicos"><Stethoscope className="w-3.5 h-3.5 mr-1" />Médicos</TabsTrigger>
                  <TabsTrigger value="productos" className="text-xs" data-testid="tab-top-productos"><Package className="w-3.5 h-3.5 mr-1" />Productos</TabsTrigger>
                  <TabsTrigger value="categorias" className="text-xs" data-testid="tab-top-categorias"><Tags className="w-3.5 h-3.5 mr-1" />Categorías</TabsTrigger>
                </TabsList>
                <TabsContent value="medicos">
                  {loadingDashboard ? (
                    <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
                  ) : topMedicos.length > 0 ? (
                    <div className="space-y-1">{topMedicos.map((m, i) => <RankingRow key={i} i={i} name={m.medico_nombre} value={`${m.count} ventas`} />)}</div>
                  ) : <p className="text-sm text-center py-2" style={{ color: 'var(--text-hint)' }}>Sin datos</p>}
                </TabsContent>
                <TabsContent value="productos">
                  {loadingDashboard ? (
                    <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
                  ) : topProductos.length > 0 ? (
                    <div className="space-y-1">{topProductos.map((p, i) => <RankingRow key={i} i={i} name={p.nombre} value={`${p.cantidad} uds`} />)}</div>
                  ) : <p className="text-sm text-center py-2" style={{ color: 'var(--text-hint)' }}>Sin datos</p>}
                </TabsContent>
                <TabsContent value="categorias">
                  {loadingDashboard ? (
                    <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
                  ) : topCategorias.length > 0 ? (
                    <div className="space-y-1">{topCategorias.map((c, i) => <RankingRow key={i} i={i} name={c.categoria} value={formatCurrency(c.total_ventas)} />)}</div>
                  ) : <p className="text-sm text-center py-2" style={{ color: 'var(--text-hint)' }}>Sin datos</p>}
                </TabsContent>
              </Tabs>
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
                  placeholder="Buscar por cliente o número de orden..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                  data-testid="ventas-search"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px] input-teal" data-testid="ventas-estado-filter">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="completada">Completadas</SelectItem>
                  <SelectItem value="anulada">Anuladas</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2">
                <div>
                  <Label className="text-xs text-gray-500">Desde</Label>
                  <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input-teal" data-testid="ventas-date-from" />
                </div>
                <div>
                  <Label className="text-xs text-gray-500">Hasta</Label>
                  <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input-teal" data-testid="ventas-date-to" />
                </div>
                {(dateFrom || dateTo) && (
                  <Button variant="ghost" size="sm" className="self-end h-9" onClick={() => { setDateFrom(''); setDateTo(''); }} data-testid="ventas-date-clear">
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
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
              <div className="p-6 space-y-4">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
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
                      <TableHead className="table-header text-center">Estado</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sales.map((sale) => (
                      <TableRow key={sale.id} className="table-row-hover">
                        <TableCell>
                          <span className="font-mono text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{sale.numero_venta}</span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>{formatDate(sale.fecha)}</TableCell>
                        <TableCell>
                          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{sale.paciente_nombre || 'Consumidor Final'}</span>
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>{sale.medico_nombre || '-'}</TableCell>
                        <TableCell className="text-right font-semibold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(sale.total)}</TableCell>
                        <TableCell className="text-center">
                          <Badge className={getStatusBadgeClass(sale.estado)}>{estadoLabels[sale.estado] || sale.estado}</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openDetail(sale)} className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]" data-testid={`ventas-detalle-${sale.id}`}>
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handlePrintTicket(sale)} className="h-8 w-8 p-0 hover:bg-slate-100" title="Reimprimir ticket" data-testid={`ventas-print-${sale.id}`}>
                              <FileText className="w-4 h-4" />
                            </Button>
                            {isAdminOrSuperAdmin && sale.estado !== 'anulada' && (
                              <Button variant="ghost" size="sm" onClick={() => { setSelectedSale(sale); setAnularMotivo(''); setDevolverInventario(true); setAnularDialogOpen(true); }} className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600" title="Anular venta" data-testid={`ventas-anular-${sale.id}`}>
                                <Ban className="w-4 h-4" />
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
          <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Detalle de Venta</DialogTitle>
            </DialogHeader>
            {selectedSale && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-lg font-bold">{selectedSale.numero_venta}</span>
                  <Badge className={getStatusBadgeClass(selectedSale.estado)}>{estadoLabels[selectedSale.estado] || selectedSale.estado}</Badge>
                </div>

                <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <span className="text-sm font-medium text-slate-600">Factura electrónica (FEL)</span>
                  <FELButton
                    origen="clinica"
                    sale={selectedSale}
                    defaultNombre={selectedSale.paciente_nombre}
                    onUpdated={refreshDetail}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Cliente</p>
                    <p className="font-medium">{selectedSale.paciente_nombre || 'Consumidor Final'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Médico</p>
                    <p className="font-medium">{selectedSale.medico_nombre || '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Fecha</p>
                    <p>{formatDate(selectedSale.fecha)}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Vendedor</p>
                    <p>{selectedSale.vendedor_nombre || '-'}</p>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-2">
                  <p className="font-semibold">Productos</p>
                  {(selectedSale.items || []).map((item, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span>{item.nombre} x{item.cantidad || 1}</span>
                      <span>{formatCurrency(item.subtotal || 0)}</span>
                    </div>
                  ))}
                </div>

                <div className="border-t pt-4 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span>{formatCurrency(selectedSale.subtotal)}</span>
                  </div>
                  {selectedSale.descuento_total > 0 && (
                    <div className="flex justify-between text-red-600">
                      <span>Descuento:</span>
                      <span>-{formatCurrency(selectedSale.descuento_total)}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2">
                    <span>Total:</span>
                    <span>{formatCurrency(selectedSale.total)}</span>
                  </div>
                </div>

                {selectedSale.formas_pago?.length > 0 && (
                  <div className="border-t pt-4">
                    <p className="font-semibold mb-2">Formas de Pago</p>
                    {selectedSale.formas_pago.map((fp, i) => (
                      <div key={i} className="text-sm flex justify-between py-1 border-b last:border-0">
                        <span>{fp.metodo}{fp.referencia ? ` (${fp.referencia})` : ''}</span>
                        <span className="font-medium">{formatCurrency(fp.monto)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {selectedSale.estado === 'anulada' && selectedSale.motivo_anulacion && (
                  <div className="border-t pt-4 text-sm">
                    <p className="font-semibold text-red-600">Anulada</p>
                    <p style={{ color: 'var(--text-secondary)' }}>Motivo: {selectedSale.motivo_anulacion}</p>
                    {selectedSale.anulada_por_nombre && <p style={{ color: 'var(--text-hint)' }}>Por: {selectedSale.anulada_por_nombre}</p>}
                  </div>
                )}
              </div>
            )}
            <DialogFooter>
              {selectedSale && (
                <Button variant="outline" onClick={() => handlePrintTicket(selectedSale)} data-testid="ventas-detalle-print">
                  <FileText className="w-4 h-4 mr-2" />
                  Reimprimir
                </Button>
              )}
              {isAdminOrSuperAdmin && selectedSale && selectedSale.estado !== 'anulada' && (
                <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => { setAnularMotivo(''); setDevolverInventario(true); setAnularDialogOpen(true); }} data-testid="ventas-detalle-anular">
                  <Ban className="w-4 h-4 mr-2" />
                  Anular
                </Button>
              )}
              <Button variant="outline" onClick={() => setDetailDialogOpen(false)} className="btn-outline">Cerrar</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Anular Dialog */}
        <Dialog open={anularDialogOpen} onOpenChange={setAnularDialogOpen}>
          <DialogContent className="sm:max-w-[420px]">
            <DialogHeader>
              <DialogTitle className="text-red-600">Anular Venta</DialogTitle>
              <DialogDescription>
                Orden: {selectedSale?.numero_venta}. Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Motivo de anulación *</Label>
                <Textarea
                  value={anularMotivo}
                  onChange={(e) => setAnularMotivo(e.target.value)}
                  placeholder="Describe el motivo (mínimo 5 caracteres)..."
                  className="input-teal"
                  data-testid="anular-motivo-input"
                />
              </div>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox checked={devolverInventario} onCheckedChange={(v) => setDevolverInventario(!!v)} data-testid="anular-devolver-inventario" />
                Devolver productos al inventario
              </label>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAnularDialogOpen(false)} className="btn-outline">Cancelar</Button>
              <Button variant="destructive" onClick={handleAnular} disabled={anulando} data-testid="anular-confirm-btn">
                {anulando ? 'Anulando...' : 'Anular Venta'}
              </Button>
            </DialogFooter>
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
              <DialogDescription>Selecciona el mes y formato para exportar</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Año</Label>
                  <Select value={reportYear.toString()} onValueChange={(v) => setReportYear(parseInt(v))}>
                    <SelectTrigger className="input-teal"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {[2024, 2025, 2026].map(y => <SelectItem key={y} value={y.toString()}>{y}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Mes</Label>
                  <Select value={reportMonth.toString()} onValueChange={(v) => setReportMonth(parseInt(v))}>
                    <SelectTrigger className="input-teal"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'].map((m, i) => (
                        <SelectItem key={i + 1} value={(i + 1).toString()}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <Button onClick={() => handleExportReport('excel')} className="flex-1 bg-green-600 hover:bg-green-700 text-white" disabled={exportingReport} data-testid="export-excel-btn">
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  {exportingReport ? 'Exportando...' : 'Excel'}
                </Button>
                <Button onClick={() => handleExportReport('pdf')} className="flex-1 bg-red-600 hover:bg-red-700 text-white" disabled={exportingReport} data-testid="export-pdf-btn">
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

export default VentasClinica;
