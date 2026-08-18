// /app/frontend/src/pages/CuentasCobrarFinanzas.js
// Cuentas por Cobrar - Módulo Finanzas/NovaVision Clínica
// Con soporte para responsables configurables (médico, institución, seguro, etc.)

import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, formatDate } from '../services/api';
import axios from 'axios';
import { 
  Search, 
  Plus, 
  DollarSign,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Filter,
  RefreshCw,
  User,
  FileText,
  Receipt,
  CreditCard,
  Banknote,
  Building2,
  Eye,
  X,
  ArrowDownCircle,
  Calendar,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  Stethoscope,
  Building,
  Shield,
  Briefcase,
  Users,
  Edit,
  Trash2
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
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import { toast } from 'sonner';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Métodos de pago para abonos
const METODOS_PAGO = [
  { value: 'Efectivo', label: 'Efectivo', icon: Banknote },
  { value: 'Tarjeta', label: 'Tarjeta', icon: CreditCard },
  { value: 'Transferencia', label: 'Transferencia', icon: Building2 },
  { value: 'Cheque', label: 'Cheque', icon: FileText },
];

// Estados de cuenta
const ESTADOS_CXC = [
  { value: '', label: 'Todos' },
  { value: 'Pendiente', label: 'Pendiente', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'Parcial', label: 'Parcial', color: 'bg-blue-100 text-blue-700' },
  { value: 'Pagado', label: 'Pagado', color: 'bg-green-100 text-green-700' },
  { value: 'Vencido', label: 'Vencido', color: 'bg-red-100 text-red-700' },
  { value: 'Anulado', label: 'Anulado', color: 'bg-slate-100 text-slate-700' },
];

// Tipos de responsable
const TIPOS_RESPONSABLE = [
  { value: 'medico', label: 'Médico', icon: Stethoscope, color: 'bg-blue-500' },
  { value: 'institucion', label: 'Institución', icon: Building, color: 'bg-purple-500' },
  { value: 'seguro', label: 'Seguro', icon: Shield, color: 'bg-green-500' },
  { value: 'convenio', label: 'Convenio', icon: Briefcase, color: 'bg-orange-500' },
  { value: 'igss', label: 'IGSS', icon: Users, color: 'bg-teal-500' },
  { value: 'otro', label: 'Otro', icon: User, color: 'bg-slate-500' },
];

const CuentasCobrarFinanzas = () => {
  const { user } = useAuth();
  
  // Tab activa
  const [activeTab, setActiveTab] = useState('cuentas');
  
  // Estado principal - Cuentas
  const [cuentas, setCuentas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resumen, setResumen] = useState(null);
  
  // Estado - Responsables
  const [responsables, setResponsables] = useState([]);
  const [loadingResponsables, setLoadingResponsables] = useState(false);
  
  // Filtros
  const [searchQuery, setSearchQuery] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipoResponsable, setFiltroTipoResponsable] = useState('');
  const [filtroResponsable, setFiltroResponsable] = useState('');
  
  // Paginación
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;
  
  // Dialogs
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(null);
  const [detalleDialogOpen, setDetalleDialogOpen] = useState(false);
  const [abonoDialogOpen, setAbonoDialogOpen] = useState(false);
  
  // Dialog de responsables
  const [responsableDialogOpen, setResponsableDialogOpen] = useState(false);
  const [responsableEditando, setResponsableEditando] = useState(null);
  const [responsableForm, setResponsableForm] = useState({
    nombre: '',
    tipo: 'medico',
    nit: '',
    direccion: '',
    telefono: '',
    email: '',
    contacto: '',
    notas: '',
    plazo_dias: 30
  });
  
  // Abono
  const [montoAbono, setMontoAbono] = useState('');
  const [metodoPago, setMetodoPago] = useState('Efectivo');
  const [referenciaAbono, setReferenciaAbono] = useState('');
  const [notasAbono, setNotasAbono] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // ==================== EFECTOS ====================
  
  useEffect(() => {
    fetchCuentas();
    fetchResumen();
    fetchResponsables();
  }, []);
  
  useEffect(() => {
    fetchCuentas();
  }, [filtroEstado, filtroTipoResponsable, filtroResponsable, offset]);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setOffset(0);
      fetchCuentas();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // ==================== API CALLS ====================

  const fetchCuentas = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (filtroEstado) params.append('estado', filtroEstado);
      if (filtroTipoResponsable) params.append('tipo_responsable', filtroTipoResponsable);
      if (filtroResponsable) params.append('responsable_id', filtroResponsable);
      params.append('limit', limit);
      params.append('offset', offset);
      
      const response = await axios.get(`${API_URL}/cuentas-cobrar/clinica?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setCuentas(response.data?.data || []);
      setTotal(response.data?.total || 0);
    } catch (error) {
      console.error('Error fetching cuentas:', error);
      toast.error('Error al cargar cuentas por cobrar');
    } finally {
      setLoading(false);
    }
  };

  const fetchResumen = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/cuentas-cobrar/clinica/resumen`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResumen(response.data);
    } catch (error) {
      console.error('Error fetching resumen:', error);
    }
  };

  const fetchResponsables = async () => {
    setLoadingResponsables(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/cuentas-cobrar/responsables`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResponsables(response.data?.data || []);
    } catch (error) {
      console.error('Error fetching responsables:', error);
    } finally {
      setLoadingResponsables(false);
    }
  };

  const fetchCuentaDetalle = async (cuentaId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/cuentas-cobrar/${cuentaId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCuentaSeleccionada(response.data);
      setDetalleDialogOpen(true);
    } catch (error) {
      console.error('Error fetching cuenta detalle:', error);
      toast.error('Error al cargar detalle de cuenta');
    }
  };

  const registrarAbono = async () => {
    if (!cuentaSeleccionada) return;
    
    const monto = parseFloat(montoAbono);
    if (isNaN(monto) || monto <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    
    if (monto > cuentaSeleccionada.saldo_pendiente) {
      toast.error('El abono excede el saldo pendiente');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_URL}/cuentas-cobrar/${cuentaSeleccionada.id}/abono`,
        {
          monto: monto,
          metodo_pago: metodoPago,
          referencia: referenciaAbono || null,
          notas: notasAbono || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Abono registrado exitosamente');
      setAbonoDialogOpen(false);
      resetAbonoForm();
      
      // Recargar datos
      await fetchCuentaDetalle(cuentaSeleccionada.id);
      fetchCuentas();
      fetchResumen();
      
    } catch (error) {
      console.error('Error registrando abono:', error);
      toast.error(error.response?.data?.detail || 'Error al registrar abono');
    } finally {
      setSubmitting(false);
    }
  };

  const guardarResponsable = async () => {
    if (!responsableForm.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      
      if (responsableEditando) {
        // Actualizar
        await axios.put(
          `${API_URL}/cuentas-cobrar/responsables/${responsableEditando.id}`,
          responsableForm,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Responsable actualizado');
      } else {
        // Crear
        await axios.post(
          `${API_URL}/cuentas-cobrar/responsables`,
          responsableForm,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success('Responsable creado');
      }
      
      setResponsableDialogOpen(false);
      resetResponsableForm();
      fetchResponsables();
      
    } catch (error) {
      console.error('Error guardando responsable:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar responsable');
    } finally {
      setSubmitting(false);
    }
  };

  const eliminarResponsable = async (responsableId) => {
    if (!confirm('¿Desactivar este responsable?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/cuentas-cobrar/responsables/${responsableId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Responsable desactivado');
      fetchResponsables();
    } catch (error) {
      console.error('Error eliminando responsable:', error);
      toast.error(error.response?.data?.detail || 'Error al desactivar responsable');
    }
  };

  const resetAbonoForm = () => {
    setMontoAbono('');
    setMetodoPago('Efectivo');
    setReferenciaAbono('');
    setNotasAbono('');
  };

  const resetResponsableForm = () => {
    setResponsableEditando(null);
    setResponsableForm({
      nombre: '',
      tipo: 'medico',
      nit: '',
      direccion: '',
      telefono: '',
      email: '',
      contacto: '',
      notas: '',
      plazo_dias: 30
    });
  };

  const editarResponsable = (resp) => {
    setResponsableEditando(resp);
    setResponsableForm({
      nombre: resp.nombre || '',
      tipo: resp.tipo || 'medico',
      nit: resp.nit || '',
      direccion: resp.direccion || '',
      telefono: resp.telefono || '',
      email: resp.email || '',
      contacto: resp.contacto || '',
      notas: resp.notas || '',
      plazo_dias: resp.plazo_dias || 30
    });
    setResponsableDialogOpen(true);
  };

  const getEstadoBadge = (estado) => {
    const config = ESTADOS_CXC.find(e => e.value === estado);
    return (
      <Badge className={config?.color || 'bg-slate-100 text-slate-700'}>
        {estado}
      </Badge>
    );
  };

  const getEstadoIcon = (estado) => {
    switch (estado) {
      case 'Pendiente': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'Parcial': return <ArrowDownCircle className="h-4 w-4 text-blue-500" />;
      case 'Pagado': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'Vencido': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'Anulado': return <XCircle className="h-4 w-4 text-slate-500" />;
      default: return null;
    }
  };

  const getTipoResponsableInfo = (tipo) => {
    return TIPOS_RESPONSABLE.find(t => t.value === tipo) || TIPOS_RESPONSABLE[5];
  };

  // ==================== RENDER ====================

  return (
    <Layout>
      <div className="space-y-6" data-testid="cxc-finanzas-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Cuentas por Cobrar - Clínica
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestión de créditos con responsables configurables
            </p>
          </div>
          
          <Button variant="outline" onClick={() => { fetchCuentas(); fetchResumen(); fetchResponsables(); }}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="cuentas" className="flex items-center gap-2">
              <Receipt className="h-4 w-4" />
              Cuentas por Cobrar
            </TabsTrigger>
            <TabsTrigger value="responsables" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Responsables
            </TabsTrigger>
          </TabsList>
          
          {/* TAB: Cuentas por Cobrar */}
          <TabsContent value="cuentas" className="space-y-6">
            {/* Resumen Cards */}
            {resumen && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Total Emitido
                        </p>
                        <p className="text-2xl font-bold text-blue-600">
                          {formatCurrency(resumen.total_emitido)}
                        </p>
                      </div>
                      <div className="p-3 rounded-full bg-blue-100">
                        <Receipt className="h-6 w-6 text-blue-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Total Cobrado
                        </p>
                        <p className="text-2xl font-bold text-green-600">
                          {formatCurrency(resumen.total_cobrado)}
                        </p>
                      </div>
                      <div className="p-3 rounded-full bg-green-100">
                        <TrendingUp className="h-6 w-6 text-green-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Saldo Pendiente
                        </p>
                        <p className="text-2xl font-bold text-orange-600">
                          {formatCurrency(resumen.saldo_pendiente)}
                        </p>
                      </div>
                      <div className="p-3 rounded-full bg-orange-100">
                        <Clock className="h-6 w-6 text-orange-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                          Cuentas Activas
                        </p>
                        <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                          {resumen.cantidad_cuentas}
                        </p>
                      </div>
                      <div className="p-3 rounded-full bg-slate-100">
                        <FileText className="h-6 w-6 text-slate-600" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Resumen por Tipo */}
            {resumen && resumen.por_tipo && Object.keys(resumen.por_tipo).length > 0 && (
              <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Saldos por Tipo de Responsable</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {Object.entries(resumen.por_tipo).map(([tipo, data]) => {
                      const tipoInfo = getTipoResponsableInfo(tipo);
                      const Icon = tipoInfo.icon;
                      return (
                        <div 
                          key={tipo}
                          className="p-3 rounded-lg border text-center"
                          style={{ borderColor: 'var(--border-color)' }}
                        >
                          <div className={`w-10 h-10 rounded-full ${tipoInfo.color} flex items-center justify-center mx-auto mb-2`}>
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                            {tipoInfo.label}
                          </p>
                          <p className="font-bold text-orange-600">
                            {formatCurrency(data.pendiente)}
                          </p>
                          <p className="text-xs text-slate-500">
                            {data.cantidad} cuentas
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Filtros */}
            <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-4">
                  <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Buscar por paciente, responsable, número..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                      data-testid="cxc-search-input"
                    />
                  </div>
                  
                  <Select value={filtroEstado || "all"} onValueChange={(v) => setFiltroEstado(v === "all" ? "" : v)}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {ESTADOS_CXC.filter(e => e.value).map(estado => (
                        <SelectItem key={estado.value} value={estado.value}>
                          {estado.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <Select value={filtroTipoResponsable || "all"} onValueChange={(v) => setFiltroTipoResponsable(v === "all" ? "" : v)}>
                    <SelectTrigger className="w-44">
                      <SelectValue placeholder="Tipo Responsable" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos los tipos</SelectItem>
                      {TIPOS_RESPONSABLE.map(tipo => (
                        <SelectItem key={tipo.value} value={tipo.value}>
                          {tipo.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <Select value={filtroResponsable || "all"} onValueChange={(v) => setFiltroResponsable(v === "all" ? "" : v)}>
                    <SelectTrigger className="w-52">
                      <SelectValue placeholder="Responsable" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos los responsables</SelectItem>
                      {responsables.map(resp => (
                        <SelectItem key={resp.id} value={resp.id}>
                          {resp.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Tabla de Cuentas */}
            <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-6 space-y-4">
                    {[...Array(5)].map((_, i) => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : cuentas.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                    <FileText className="h-12 w-12 mb-3 opacity-50" />
                    <p>No hay cuentas por cobrar</p>
                    <p className="text-sm">Las cuentas se crean desde el Punto de Venta</p>
                  </div>
                ) : (
                  <>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>No. Cuenta</TableHead>
                          <TableHead>Responsable</TableHead>
                          <TableHead>Paciente</TableHead>
                          <TableHead>Concepto</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                          <TableHead className="text-right">Saldo</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead>Fecha</TableHead>
                          <TableHead></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cuentas.map((cuenta) => {
                          const tipoInfo = getTipoResponsableInfo(cuenta.tipo_responsable);
                          const Icon = tipoInfo.icon;
                          return (
                            <TableRow 
                              key={cuenta.id} 
                              className="cursor-pointer hover:bg-slate-50"
                              onClick={() => fetchCuentaDetalle(cuenta.id)}
                            >
                              <TableCell className="font-mono font-medium">
                                {cuenta.numero_cuenta}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  <div className={`w-6 h-6 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                                    <Icon className="h-3 w-3 text-white" />
                                  </div>
                                  <div>
                                    <p className="font-medium text-sm">{cuenta.responsable_nombre}</p>
                                    <p className="text-xs text-slate-500">{tipoInfo.label}</p>
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell>
                                {cuenta.paciente_nombre || '-'}
                              </TableCell>
                              <TableCell className="max-w-[150px] truncate">
                                {cuenta.concepto}
                              </TableCell>
                              <TableCell className="text-right font-medium">
                                {formatCurrency(cuenta.monto_total)}
                              </TableCell>
                              <TableCell className="text-right font-bold text-orange-600">
                                {formatCurrency(cuenta.saldo_pendiente)}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  {getEstadoIcon(cuenta.estado)}
                                  {getEstadoBadge(cuenta.estado)}
                                </div>
                              </TableCell>
                              <TableCell className="text-slate-500 text-sm">
                                {formatDate(cuenta.fecha_emision)}
                              </TableCell>
                              <TableCell>
                                <ChevronRight className="h-4 w-4 text-slate-400" />
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                    
                    {/* Paginación */}
                    {total > limit && (
                      <div className="flex items-center justify-between px-6 py-4 border-t">
                        <span className="text-sm text-slate-500">
                          Mostrando {offset + 1} - {Math.min(offset + limit, total)} de {total}
                        </span>
                        <div className="flex gap-2">
                          <Button 
                            variant="outline" 
                            size="sm"
                            disabled={offset === 0}
                            onClick={() => setOffset(Math.max(0, offset - limit))}
                          >
                            Anterior
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            disabled={offset + limit >= total}
                            onClick={() => setOffset(offset + limit)}
                          >
                            Siguiente
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* TAB: Responsables */}
          <TabsContent value="responsables" className="space-y-6">
            <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Catálogo de Responsables</CardTitle>
                <Button 
                  className="bg-blue-600 hover:bg-blue-700"
                  onClick={() => {
                    resetResponsableForm();
                    setResponsableDialogOpen(true);
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Nuevo Responsable
                </Button>
              </CardHeader>
              <CardContent>
                {loadingResponsables ? (
                  <div className="space-y-3">
                    {[...Array(4)].map((_, i) => (
                      <Skeleton key={i} className="h-20 w-full" />
                    ))}
                  </div>
                ) : responsables.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No hay responsables registrados</p>
                    <p className="text-sm">Cree responsables para asignar a las cuentas por cobrar</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {responsables.map((resp) => {
                      const tipoInfo = getTipoResponsableInfo(resp.tipo);
                      const Icon = tipoInfo.icon;
                      return (
                        <div 
                          key={resp.id}
                          className="p-4 rounded-lg border hover:shadow-md transition-shadow"
                          style={{ borderColor: 'var(--border-color)' }}
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                                <Icon className="h-5 w-5 text-white" />
                              </div>
                              <div>
                                <p className="font-medium">{resp.nombre}</p>
                                <Badge variant="outline" className="text-xs">
                                  {tipoInfo.label}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex gap-1">
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => editarResponsable(resp)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                className="text-red-500 hover:text-red-700"
                                onClick={() => eliminarResponsable(resp.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                          
                          <div className="space-y-1 text-sm text-slate-500">
                            {resp.nit && <p>NIT: {resp.nit}</p>}
                            {resp.telefono && <p>Tel: {resp.telefono}</p>}
                            {resp.email && <p>{resp.email}</p>}
                            <p>Plazo: {resp.plazo_dias} días</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* ==================== DIALOGS ==================== */}

      {/* Dialog: Detalle de Cuenta */}
      <Dialog open={detalleDialogOpen} onOpenChange={setDetalleDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="h-5 w-5 text-blue-500" />
              {cuentaSeleccionada?.numero_cuenta}
            </DialogTitle>
            <DialogDescription>
              Detalle de cuenta por cobrar - Clínica
            </DialogDescription>
          </DialogHeader>
          
          {cuentaSeleccionada && (
            <div className="space-y-6">
              {/* Info principal */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Responsable</Label>
                  <div className="flex items-center gap-2 mt-1">
                    {(() => {
                      const tipoInfo = getTipoResponsableInfo(cuentaSeleccionada.tipo_responsable);
                      const Icon = tipoInfo.icon;
                      return (
                        <>
                          <div className={`w-8 h-8 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                            <Icon className="h-4 w-4 text-white" />
                          </div>
                          <div>
                            <p className="font-medium">{cuentaSeleccionada.responsable_nombre}</p>
                            <p className="text-xs text-slate-500">{tipoInfo.label}</p>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
                
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Estado</Label>
                  <div className="flex items-center gap-2 mt-1">
                    {getEstadoIcon(cuentaSeleccionada.estado)}
                    {getEstadoBadge(cuentaSeleccionada.estado)}
                  </div>
                </div>
                
                {cuentaSeleccionada.paciente_nombre && (
                  <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                    <Label className="text-sm text-slate-500">Paciente</Label>
                    <p className="font-medium flex items-center gap-2 mt-1">
                      <User className="h-4 w-4 text-slate-400" />
                      {cuentaSeleccionada.paciente_nombre}
                    </p>
                  </div>
                )}
                
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Fecha de Emisión</Label>
                  <p className="font-medium flex items-center gap-2 mt-1">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    {formatDate(cuentaSeleccionada.fecha_emision)}
                  </p>
                </div>
              </div>
              
              {/* Concepto */}
              <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border-color)' }}>
                <Label className="text-sm text-slate-500">Concepto</Label>
                <p className="font-medium mt-1">{cuentaSeleccionada.concepto}</p>
                {cuentaSeleccionada.notas && (
                  <p className="text-sm text-slate-500 mt-2">
                    Notas: {cuentaSeleccionada.notas}
                  </p>
                )}
              </div>
              
              {/* Montos */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-slate-100 text-center">
                  <Label className="text-sm text-slate-500">Total</Label>
                  <p className="text-xl font-bold text-slate-800">
                    {formatCurrency(cuentaSeleccionada.monto_total)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-green-100 text-center">
                  <Label className="text-sm text-green-600">Pagado</Label>
                  <p className="text-xl font-bold text-green-700">
                    {formatCurrency(cuentaSeleccionada.monto_pagado)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-orange-100 text-center">
                  <Label className="text-sm text-orange-600">Saldo</Label>
                  <p className="text-xl font-bold text-orange-700">
                    {formatCurrency(cuentaSeleccionada.saldo_pendiente)}
                  </p>
                </div>
              </div>
              
              {/* Historial de pagos */}
              {cuentaSeleccionada.pagos && cuentaSeleccionada.pagos.length > 0 && (
                <div>
                  <Label className="mb-2 block">Historial de Pagos</Label>
                  <div className="border rounded-lg divide-y" style={{ borderColor: 'var(--border-color)' }}>
                    {cuentaSeleccionada.pagos.map((pago, idx) => (
                      <div key={pago.id || idx} className="p-3 flex items-center justify-between">
                        <div>
                          <p className="font-medium">{pago.metodo_pago}</p>
                          <p className="text-sm text-slate-500">
                            {formatDate(pago.fecha)} • {pago.registrado_por_nombre}
                          </p>
                          {pago.referencia && (
                            <p className="text-xs text-slate-400">Ref: {pago.referencia}</p>
                          )}
                        </div>
                        <p className="font-bold text-green-600">
                          {formatCurrency(pago.monto)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetalleDialogOpen(false)}>
              Cerrar
            </Button>
            {cuentaSeleccionada && 
             cuentaSeleccionada.estado !== 'Pagado' && 
             cuentaSeleccionada.estado !== 'Anulado' && (
              <Button 
                className="bg-blue-600 hover:bg-blue-700"
                onClick={() => {
                  setMontoAbono(cuentaSeleccionada.saldo_pendiente.toString());
                  setAbonoDialogOpen(true);
                }}
              >
                <DollarSign className="h-4 w-4 mr-2" />
                Registrar Abono
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Registrar Abono */}
      <Dialog open={abonoDialogOpen} onOpenChange={setAbonoDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Registrar Abono</DialogTitle>
            <DialogDescription>
              Cuenta: {cuentaSeleccionada?.numero_cuenta}
              <br />
              Saldo pendiente: <span className="font-bold text-orange-600">
                {formatCurrency(cuentaSeleccionada?.saldo_pendiente || 0)}
              </span>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Método de pago */}
            <div>
              <Label>Método de Pago</Label>
              <div className="grid grid-cols-4 gap-2 mt-2">
                {METODOS_PAGO.map(mp => {
                  const Icon = mp.icon;
                  return (
                    <button
                      key={mp.value}
                      onClick={() => setMetodoPago(mp.value)}
                      className={`
                        p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all
                        ${metodoPago === mp.value 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-slate-200 hover:border-slate-300'}
                      `}
                    >
                      <Icon className={`h-5 w-5 ${metodoPago === mp.value ? 'text-blue-600' : 'text-slate-400'}`} />
                      <span className="text-xs">{mp.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            
            {/* Monto */}
            <div>
              <Label>Monto del Abono</Label>
              <div className="relative mt-2">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">Q</span>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={cuentaSeleccionada?.saldo_pendiente || 0}
                  value={montoAbono}
                  onChange={(e) => setMontoAbono(e.target.value)}
                  className="pl-8 text-lg font-bold"
                  placeholder="0.00"
                />
              </div>
              <div className="flex gap-2 mt-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setMontoAbono((cuentaSeleccionada?.saldo_pendiente || 0).toString())}
                >
                  Pago total
                </Button>
                {[100, 200, 500].map(m => (
                  <Button 
                    key={m}
                    variant="outline" 
                    size="sm"
                    onClick={() => setMontoAbono(m.toString())}
                  >
                    Q{m}
                  </Button>
                ))}
              </div>
            </div>
            
            {/* Referencia */}
            {metodoPago !== 'Efectivo' && (
              <div>
                <Label>Referencia (opcional)</Label>
                <Input
                  value={referenciaAbono}
                  onChange={(e) => setReferenciaAbono(e.target.value)}
                  placeholder="No. autorización, boleta, etc."
                  className="mt-2"
                />
              </div>
            )}
            
            {/* Notas */}
            <div>
              <Label>Notas (opcional)</Label>
              <Textarea
                value={notasAbono}
                onChange={(e) => setNotasAbono(e.target.value)}
                placeholder="Observaciones del pago..."
                rows={2}
                className="mt-2"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setAbonoDialogOpen(false);
                resetAbonoForm();
              }}
            >
              Cancelar
            </Button>
            <Button 
              className="bg-blue-600 hover:bg-blue-700"
              onClick={registrarAbono}
              disabled={submitting || !montoAbono || parseFloat(montoAbono) <= 0}
            >
              {submitting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <DollarSign className="h-4 w-4 mr-2" />
                  Registrar Abono
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Responsable */}
      <Dialog open={responsableDialogOpen} onOpenChange={setResponsableDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {responsableEditando ? 'Editar Responsable' : 'Nuevo Responsable'}
            </DialogTitle>
            <DialogDescription>
              Defina los datos del responsable de las cuentas por cobrar
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Tipo */}
            <div>
              <Label>Tipo de Responsable</Label>
              <div className="grid grid-cols-3 gap-2 mt-2">
                {TIPOS_RESPONSABLE.map(tipo => {
                  const Icon = tipo.icon;
                  return (
                    <button
                      key={tipo.value}
                      onClick={() => setResponsableForm({...responsableForm, tipo: tipo.value})}
                      className={`
                        p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all
                        ${responsableForm.tipo === tipo.value 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-slate-200 hover:border-slate-300'}
                      `}
                    >
                      <div className={`w-8 h-8 rounded-full ${tipo.color} flex items-center justify-center`}>
                        <Icon className="h-4 w-4 text-white" />
                      </div>
                      <span className="text-xs">{tipo.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            
            {/* Nombre */}
            <div>
              <Label>Nombre *</Label>
              <Input
                value={responsableForm.nombre}
                onChange={(e) => setResponsableForm({...responsableForm, nombre: e.target.value})}
                placeholder="Nombre del responsable"
                className="mt-2"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>NIT</Label>
                <Input
                  value={responsableForm.nit}
                  onChange={(e) => setResponsableForm({...responsableForm, nit: e.target.value})}
                  placeholder="NIT"
                  className="mt-2"
                />
              </div>
              <div>
                <Label>Teléfono</Label>
                <Input
                  value={responsableForm.telefono}
                  onChange={(e) => setResponsableForm({...responsableForm, telefono: e.target.value})}
                  placeholder="Teléfono"
                  className="mt-2"
                />
              </div>
            </div>
            
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={responsableForm.email}
                onChange={(e) => setResponsableForm({...responsableForm, email: e.target.value})}
                placeholder="correo@ejemplo.com"
                className="mt-2"
              />
            </div>
            
            <div>
              <Label>Dirección</Label>
              <Input
                value={responsableForm.direccion}
                onChange={(e) => setResponsableForm({...responsableForm, direccion: e.target.value})}
                placeholder="Dirección"
                className="mt-2"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Persona de Contacto</Label>
                <Input
                  value={responsableForm.contacto}
                  onChange={(e) => setResponsableForm({...responsableForm, contacto: e.target.value})}
                  placeholder="Nombre del contacto"
                  className="mt-2"
                />
              </div>
              <div>
                <Label>Plazo de Pago (días)</Label>
                <Input
                  type="number"
                  min="0"
                  max="365"
                  value={responsableForm.plazo_dias}
                  onChange={(e) => setResponsableForm({...responsableForm, plazo_dias: parseInt(e.target.value) || 30})}
                  className="mt-2"
                />
              </div>
            </div>
            
            <div>
              <Label>Notas</Label>
              <Textarea
                value={responsableForm.notas}
                onChange={(e) => setResponsableForm({...responsableForm, notas: e.target.value})}
                placeholder="Notas adicionales..."
                rows={2}
                className="mt-2"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setResponsableDialogOpen(false);
                resetResponsableForm();
              }}
            >
              Cancelar
            </Button>
            <Button 
              className="bg-blue-600 hover:bg-blue-700"
              onClick={guardarResponsable}
              disabled={submitting || !responsableForm.nombre.trim()}
            >
              {submitting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {responsableEditando ? 'Actualizar' : 'Crear'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default CuentasCobrarFinanzas;
