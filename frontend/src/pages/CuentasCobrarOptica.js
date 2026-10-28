// /app/frontend/src/pages/CuentasCobrarOptica.js
// Cuentas por Cobrar - Módulo Óptica
// Vinculadas directamente al cliente/paciente de la orden

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
  ChevronRight
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

const CuentasCobrarOptica = () => {
  const { user } = useAuth();
  
  // Estado principal
  const [cuentas, setCuentas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resumen, setResumen] = useState(null);
  
  // Filtros
  const [searchQuery, setSearchQuery] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  
  // Paginación
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;
  
  // Dialogs
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(null);
  const [detalleDialogOpen, setDetalleDialogOpen] = useState(false);
  const [abonoDialogOpen, setAbonoDialogOpen] = useState(false);
  
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
  }, [filtroEstado, offset]);
  
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
      params.append('limit', limit);
      params.append('offset', offset);
      
      const response = await axios.get(`${API_URL}/cuentas-cobrar/optica?${params}`, {
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
      const response = await axios.get(`${API_URL}/cuentas-cobrar/optica/resumen`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResumen(response.data);
    } catch (error) {
      console.error('Error fetching resumen:', error);
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

  const resetAbonoForm = () => {
    setMontoAbono('');
    setMetodoPago('Efectivo');
    setReferenciaAbono('');
    setNotasAbono('');
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

  // ==================== RENDER ====================

  return (
    <Layout>
      <div className="space-y-6" data-testid="cxc-optica-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Cuentas por Cobrar - Óptica
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestión de créditos y cobros del área de óptica
            </p>
          </div>
          
          <Button variant="outline" onClick={() => { fetchCuentas(); fetchResumen(); }}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>

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
                    <p className="text-2xl font-bold text-teal-600">
                      {formatCurrency(resumen.total_emitido)}
                    </p>
                  </div>
                  <div className="p-3 rounded-full bg-teal-100">
                    <Receipt className="h-6 w-6 text-teal-600" />
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

        {/* Filtros */}
        <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <CardContent className="pt-6">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Buscar por paciente, número de cuenta..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="cxc-search-input"
                />
              </div>
              
              <Select value={filtroEstado || "all"} onValueChange={(v) => setFiltroEstado(v === "all" ? "" : v)}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  {ESTADOS_CXC.filter(e => e.value).map(estado => (
                    <SelectItem key={estado.value} value={estado.value}>
                      {estado.label}
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
                      <TableHead>Paciente</TableHead>
                      <TableHead>Concepto</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Pagado</TableHead>
                      <TableHead className="text-right">Saldo</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cuentas.map((cuenta) => (
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
                            <User className="h-4 w-4 text-slate-400" />
                            {cuenta.paciente_nombre || 'Sin paciente'}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {cuenta.concepto}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(cuenta.monto_total)}
                        </TableCell>
                        <TableCell className="text-right text-green-600">
                          {formatCurrency(cuenta.monto_pagado)}
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
                    ))}
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
      </div>

      {/* ==================== DIALOGS ==================== */}

      {/* Dialog: Detalle de Cuenta */}
      <Dialog open={detalleDialogOpen} onOpenChange={setDetalleDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="h-5 w-5 text-teal-500" />
              {cuentaSeleccionada?.numero_cuenta}
            </DialogTitle>
            <DialogDescription>
              Detalle de cuenta por cobrar
            </DialogDescription>
          </DialogHeader>
          
          {cuentaSeleccionada && (
            <div className="space-y-6">
              {/* Info principal */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Paciente</Label>
                  <p className="font-medium flex items-center gap-2 mt-1">
                    <User className="h-4 w-4 text-teal-500" />
                    {cuentaSeleccionada.paciente_nombre || 'Sin paciente'}
                  </p>
                </div>
                
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Estado</Label>
                  <div className="flex items-center gap-2 mt-1">
                    {getEstadoIcon(cuentaSeleccionada.estado)}
                    {getEstadoBadge(cuentaSeleccionada.estado)}
                  </div>
                </div>
                
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Fecha de Emisión</Label>
                  <p className="font-medium flex items-center gap-2 mt-1">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    {formatDate(cuentaSeleccionada.fecha_emision)}
                  </p>
                </div>
                
                <div className="p-4 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                  <Label className="text-sm text-slate-500">Vencimiento</Label>
                  <p className="font-medium flex items-center gap-2 mt-1">
                    <Clock className="h-4 w-4 text-slate-400" />
                    {cuentaSeleccionada.fecha_vencimiento 
                      ? formatDate(cuentaSeleccionada.fecha_vencimiento)
                      : 'Sin vencimiento'}
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
                className="bg-teal-600 hover:bg-teal-700"
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
                          ? 'border-teal-500 bg-teal-50' 
                          : 'border-slate-200 hover:border-slate-300'}
                      `}
                    >
                      <Icon className={`h-5 w-5 ${metodoPago === mp.value ? 'text-teal-600' : 'text-slate-400'}`} />
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
                  type="text"
                  inputMode="decimal"
                  value={montoAbono}
                  onChange={(e) => {
                    const v = e.target.value.replace(',', '.');
                    if (v === '' || /^\d*\.?\d{0,2}$/.test(v)) setMontoAbono(v);
                  }}
                  className="pl-8 text-lg font-bold"
                  placeholder="0.00"
                  data-testid="abono-monto-input"
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
              className="bg-teal-600 hover:bg-teal-700"
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
    </Layout>
  );
};

export default CuentasCobrarOptica;
