import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { useCajaWebSocket } from '../hooks/useWebSocket';
import axios from 'axios';
import { formatCurrency, formatDate, formatTime } from '../services/api';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
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
  Wallet,
  ArrowUpCircle,
  ArrowDownCircle,
  Lock,
  Unlock,
  Calendar,
  FileText,
  Users,
  CreditCard,
  Banknote,
  Building2,
  RefreshCw,
  Clock,
  CheckCircle,
  AlertCircle,
  Printer,
  Calculator
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import { toast, Toaster } from 'sonner';

// Categorías predefinidas para movimientos de caja (solo ingresos)
const CATEGORIAS_INGRESO = [
  'Consulta',
  'Cirugía',
  'Procedimiento',
  'Medicamentos'
];

const METODOS_PAGO = ['Efectivo', 'Tarjeta', 'Transferencia', 'Cheque', 'Cuenta por Cobrar'];

// Formularios iniciales
const initialMovimientoForm = {
  categoria: '',
  concepto: '',
  monto: '',
  metodo_pago: 'Efectivo',
  referencia: '',
  paciente_id: '',
  paciente_nombre: '',
  // Campos adicionales para Cuenta por Cobrar
  tipo_pagador_id: '',
  tipo_pagador_nombre: '',
  pagador_nombre: '',
  es_aseguradora: false,
  monto_deducible: '',
  metodo_pago_deducible: 'Efectivo'
};

const initialCxCForm = {
  paciente_id: '',
  paciente_nombre: '',
  tipo_pagador_id: '',
  tipo_pagador_nombre: '',
  pagador_nombre: '',
  concepto: '',
  referencia: '',
  monto_total: '',
  fecha_vencimiento: '',
  notas: ''
};

const initialAbonoForm = {
  monto: '',
  metodo_pago: 'Efectivo',
  referencia: '',
  registrar_en_caja: true
};

const initialCierreFinancieroForm = {
  tipo: 'Mensual',
  mes: new Date().getMonth() + 1,
  semestre: 1,
  anio: new Date().getFullYear(),
  observaciones: ''
};

const Caja = () => {
  const { user, hasPermission } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';
  
  // Estado de la caja
  const [cajaEstado, setCajaEstado] = useState(null);
  const [loadingEstado, setLoadingEstado] = useState(true);
  
  // WebSocket para actualizaciones en tiempo real
  const { isConnected: wsConnected, lastMessage: wsMessage } = useCajaWebSocket({
    onMessage: (message) => {
      console.log('📩 WebSocket Caja:', message.type);
      
      switch (message.type) {
        case 'caja_abierta':
          toast.success(`Caja abierta por ${message.data.usuario}`);
          fetchCajaEstado();
          break;
          
        case 'caja_cerrada':
          toast.info(`Caja cerrada por ${message.data.usuario}`);
          fetchCajaEstado();
          break;
          
        case 'nuevo_movimiento':
          toast.info(`Nuevo ${message.data.tipo}: ${formatCurrency(message.data.monto)}`);
          fetchMovimientos();
          break;
          
        case 'caja_estado_inicial':
          // Estado inicial recibido al conectar
          break;
          
        default:
          break;
      }
    },
    enabled: true
  });
  
  // Tab actual
  const [activeTab, setActiveTab] = useState('caja-diaria');
  
  // === CAJA DIARIA ===
  const [movimientos, setMovimientos] = useState([]);
  const [loadingMovimientos, setLoadingMovimientos] = useState(false);
  const [movimientoDialogOpen, setMovimientoDialogOpen] = useState(false);
  const [movimientoForm, setMovimientoForm] = useState(initialMovimientoForm);
  const [editingMovimiento, setEditingMovimiento] = useState(null);
  const [deleteMovimientoDialog, setDeleteMovimientoDialog] = useState(false);
  const [movimientoToDelete, setMovimientoToDelete] = useState(null);
  
  // Apertura/Cierre dialogs
  const [aperturaDialogOpen, setAperturaDialogOpen] = useState(false);
  const [cierreDialogOpen, setCierreDialogOpen] = useState(false);
  const [montoApertura, setMontoApertura] = useState('');
  const [cierreForm, setCierreForm] = useState({ efectivo_contado: '', observaciones: '' });
  
  // Historial de cierres
  const [historialCierres, setHistorialCierres] = useState([]);
  const [historialDialogOpen, setHistorialDialogOpen] = useState(false);
  const [cierreDetalleDialog, setCierreDetalleDialog] = useState(false);
  const [cierreDetalle, setCierreDetalle] = useState(null);
  
  // Búsqueda de pacientes
  const [pacienteSearch, setPacienteSearch] = useState('');
  const [pacientesResults, setPacientesResults] = useState([]);
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  
  // === CUENTAS POR COBRAR ===
  const [cuentasCobrar, setCuentasCobrar] = useState([]);
  const [loadingCxC, setLoadingCxC] = useState(false);
  const [cxcDialogOpen, setCxcDialogOpen] = useState(false);
  const [cxcForm, setCxcForm] = useState(initialCxCForm);
  const [editingCxC, setEditingCxC] = useState(null);
  const [cxcDetalleDialog, setCxcDetalleDialog] = useState(false);
  const [cxcDetalle, setCxcDetalle] = useState(null);
  const [abonoDialogOpen, setAbonoDialogOpen] = useState(false);
  const [abonoForm, setAbonoForm] = useState(initialAbonoForm);
  const [resumenCxC, setResumenCxC] = useState(null);
  
  // Catálogo de pagadores
  const [pagadores, setPagadores] = useState([]);
  const [pagadorDialogOpen, setPagadorDialogOpen] = useState(false);
  const [pagadorForm, setPagadorForm] = useState({ nombre: '' });
  const [editingPagador, setEditingPagador] = useState(null);
  
  // Filtros CxC
  const [cxcFilters, setCxcFilters] = useState({ tipo_pagador: '', estado: '', search: '' });
  
  // === CIERRES FINANCIEROS ===
  const [cierresFinancieros, setCierresFinancieros] = useState([]);
  const [loadingCierresF, setLoadingCierresF] = useState(false);
  const [cierreFinancieroDialogOpen, setCierreFinancieroDialogOpen] = useState(false);
  const [cierreFinancieroForm, setCierreFinancieroForm] = useState(initialCierreFinancieroForm);
  const [cierreFinancieroDetalle, setCierreFinancieroDetalle] = useState(null);
  const [cierreFinancieroDetalleDialog, setCierreFinancieroDetalleDialog] = useState(false);
  
  const [submitting, setSubmitting] = useState(false);

  // ==================== EFECTOS ====================
  
  useEffect(() => {
    fetchCajaEstado();
    fetchPagadores();
  }, []);
  
  useEffect(() => {
    if (activeTab === 'caja-diaria') {
      fetchMovimientos();
    } else if (activeTab === 'cuentas-cobrar') {
      fetchCuentasCobrar();
      fetchResumenCxC();
    } else if (activeTab === 'cierres-financieros') {
      fetchCierresFinancieros();
    }
  }, [activeTab, cxcFilters]);

  // ==================== API CALLS ====================

  const fetchCajaEstado = async () => {
    setLoadingEstado(true);
    try {
      const response = await axios.get(`${API_URL}/caja/estado`);
      setCajaEstado(response.data);
    } catch (error) {
      console.error('Error fetching caja estado:', error);
      toast.error('Error al obtener estado de caja');
    } finally {
      setLoadingEstado(false);
    }
  };

  const fetchMovimientos = async () => {
    setLoadingMovimientos(true);
    try {
      const response = await axios.get(`${API_URL}/caja/movimientos`);
      setMovimientos(response.data.data || []);
    } catch (error) {
      console.error('Error fetching movimientos:', error);
    } finally {
      setLoadingMovimientos(false);
    }
  };

  const fetchPagadores = async () => {
    try {
      const response = await axios.get(`${API_URL}/catalogos/pagadores`);
      setPagadores(response.data || []);
    } catch (error) {
      console.error('Error fetching pagadores:', error);
    }
  };

  const fetchCuentasCobrar = async () => {
    setLoadingCxC(true);
    try {
      const params = new URLSearchParams();
      if (cxcFilters.tipo_pagador) params.append('tipo_pagador', cxcFilters.tipo_pagador);
      if (cxcFilters.estado) params.append('estado', cxcFilters.estado);
      if (cxcFilters.search) params.append('search', cxcFilters.search);
      
      const response = await axios.get(`${API_URL}/cxc?${params.toString()}`);
      setCuentasCobrar(response.data.data || []);
    } catch (error) {
      console.error('Error fetching CxC:', error);
    } finally {
      setLoadingCxC(false);
    }
  };

  const fetchResumenCxC = async () => {
    try {
      const response = await axios.get(`${API_URL}/cxc/resumen`);
      setResumenCxC(response.data);
    } catch (error) {
      console.error('Error fetching resumen CxC:', error);
    }
  };

  const fetchCierresFinancieros = async () => {
    setLoadingCierresF(true);
    try {
      const response = await axios.get(`${API_URL}/cierres-financieros`);
      setCierresFinancieros(response.data.data || []);
    } catch (error) {
      console.error('Error fetching cierres financieros:', error);
    } finally {
      setLoadingCierresF(false);
    }
  };

  const fetchHistorialCierres = async () => {
    try {
      const response = await axios.get(`${API_URL}/caja/cierres?limit=30`);
      setHistorialCierres(response.data?.data || response.data || []);
    } catch (error) {
      console.error('Error fetching historial cierres:', error);
    }
  };

  // Búsqueda de pacientes con debounce
  const searchPacientes = useCallback(async (query) => {
    if (!query || query.length < 2) {
      setPacientesResults([]);
      return;
    }
    setSearchingPacientes(true);
    try {
      const response = await axios.get(`${API_URL}/pacientes/buscar?q=${encodeURIComponent(query)}`);
      setPacientesResults(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    } finally {
      setSearchingPacientes(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      // Solo buscar si no hay un paciente ya seleccionado (en movimiento o cxc)
      const pacienteYaSeleccionado = movimientoForm.paciente_id || cxcForm.paciente_id;
      if (pacienteSearch && !pacienteYaSeleccionado) {
        searchPacientes(pacienteSearch);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [pacienteSearch, searchPacientes, movimientoForm.paciente_id, cxcForm.paciente_id]);

  // ==================== APERTURA / CIERRE ====================

  const handleAperturaCaja = async () => {
    if (!montoApertura || parseFloat(montoApertura) < 0) {
      toast.error('Ingrese un monto de apertura válido');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/caja/apertura`, { monto_apertura: parseFloat(montoApertura) });
      toast.success('Caja abierta exitosamente');
      setAperturaDialogOpen(false);
      setMontoApertura('');
      fetchCajaEstado();
      fetchMovimientos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al abrir caja');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCierreCaja = async () => {
    if (!cierreForm.efectivo_contado || parseFloat(cierreForm.efectivo_contado) < 0) {
      toast.error('Ingrese el efectivo contado');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/caja/cierre`, {
        efectivo_contado: parseFloat(cierreForm.efectivo_contado),
        observaciones: cierreForm.observaciones
      });
      toast.success('Caja cerrada exitosamente');
      setCierreDialogOpen(false);
      setCierreForm({ efectivo_contado: '', observaciones: '' });
      fetchCajaEstado();
      fetchMovimientos();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cerrar caja');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReabrirCaja = async (cierreId) => {
    if (!isSuperAdmin) {
      toast.error('Solo SuperAdmin puede reabrir cajas');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/caja/cierres/${cierreId}/reabrir`);
      toast.success('Caja reabierta exitosamente');
      fetchCajaEstado();
      fetchHistorialCierres();
      if (cierreDetalleDialog) {
        setCierreDetalleDialog(false);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al reabrir caja');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== MOVIMIENTOS ====================

  const handleSaveMovimiento = async () => {
    if (!movimientoForm.paciente_id || !movimientoForm.paciente_nombre) {
      toast.error('Debe seleccionar un paciente');
      return;
    }
    if (!movimientoForm.categoria || !movimientoForm.concepto || !movimientoForm.monto) {
      toast.error('Complete los campos obligatorios');
      return;
    }
    
    // Validaciones para Cuenta por Cobrar
    if (movimientoForm.metodo_pago === 'Cuenta por Cobrar') {
      if (!movimientoForm.tipo_pagador_id) {
        toast.error('Debe seleccionar el tipo de pagador');
        return;
      }
      // Si es aseguradora y tiene deducible, validar
      if (movimientoForm.es_aseguradora && movimientoForm.monto_deducible) {
        const deducible = parseFloat(movimientoForm.monto_deducible);
        const montoTotal = parseFloat(movimientoForm.monto);
        if (deducible >= montoTotal) {
          toast.error('El deducible debe ser menor al monto total');
          return;
        }
      }
    }
    
    setSubmitting(true);
    try {
      const montoTotal = parseFloat(movimientoForm.monto);
      
      // Caso especial: Cuenta por Cobrar
      if (movimientoForm.metodo_pago === 'Cuenta por Cobrar' && !editingMovimiento) {
        const deducible = movimientoForm.es_aseguradora && movimientoForm.monto_deducible 
          ? parseFloat(movimientoForm.monto_deducible) 
          : 0;
        const montoCxC = montoTotal - deducible;
        
        // 1. Si hay deducible, registrar el pago del deducible en caja
        if (deducible > 0) {
          await axios.post(`${API_URL}/caja/movimientos`, {
            tipo: 'Ingreso',
            categoria: movimientoForm.categoria,
            concepto: `${movimientoForm.concepto} (Deducible)`,
            monto: deducible,
            metodo_pago: movimientoForm.metodo_pago_deducible,
            referencia: movimientoForm.referencia,
            paciente_id: movimientoForm.paciente_id,
            paciente_nombre: movimientoForm.paciente_nombre
          });
        }
        
        // 2. Crear la cuenta por cobrar con el monto restante (o total si no hay deducible)
        await axios.post(`${API_URL}/cxc`, {
          paciente_id: movimientoForm.paciente_id,
          paciente_nombre: movimientoForm.paciente_nombre,
          tipo_pagador_id: movimientoForm.tipo_pagador_id,
          tipo_pagador_nombre: movimientoForm.tipo_pagador_nombre,
          pagador_nombre: movimientoForm.pagador_nombre || '',
          concepto: movimientoForm.concepto,
          referencia: movimientoForm.referencia,
          monto_total: montoCxC
        });
        
        toast.success(deducible > 0 
          ? `Deducible Q${deducible.toFixed(2)} registrado en caja y Q${montoCxC.toFixed(2)} agregado a Cuentas por Cobrar`
          : 'Cuenta por Cobrar creada exitosamente'
        );
      } else {
        // Caso normal: movimiento de ingreso regular
        const data = {
          tipo: 'Ingreso', // Siempre es ingreso
          categoria: movimientoForm.categoria,
          concepto: movimientoForm.concepto,
          monto: montoTotal,
          metodo_pago: movimientoForm.metodo_pago,
          referencia: movimientoForm.referencia,
          paciente_id: movimientoForm.paciente_id,
          paciente_nombre: movimientoForm.paciente_nombre
        };
        
        if (editingMovimiento) {
          await axios.put(`${API_URL}/caja/movimientos/${editingMovimiento.id}`, data);
          toast.success('Movimiento actualizado');
        } else {
          await axios.post(`${API_URL}/caja/movimientos`, data);
          toast.success('Movimiento registrado');
        }
      }
      
      setMovimientoDialogOpen(false);
      setMovimientoForm(initialMovimientoForm);
      setEditingMovimiento(null);
      setPacienteSearch('');
      setPacientesResults([]);
      fetchMovimientos();
      fetchCajaEstado();
      // También actualizar CxC si se creó una
      if (movimientoForm.metodo_pago === 'Cuenta por Cobrar') {
        fetchCuentasCobrar();
        fetchResumenCxC();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar movimiento');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteMovimiento = async () => {
    if (!movimientoToDelete) return;
    setSubmitting(true);
    try {
      await axios.delete(`${API_URL}/caja/movimientos/${movimientoToDelete.id}`);
      toast.success('Movimiento eliminado');
      setDeleteMovimientoDialog(false);
      setMovimientoToDelete(null);
      fetchMovimientos();
      fetchCajaEstado();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar movimiento');
    } finally {
      setSubmitting(false);
    }
  };

  const openEditMovimiento = (mov) => {
    setEditingMovimiento(mov);
    setMovimientoForm({
      categoria: mov.categoria,
      concepto: mov.concepto,
      monto: mov.monto.toString(),
      metodo_pago: mov.metodo_pago,
      referencia: mov.referencia || '',
      paciente_id: mov.paciente_id || '',
      paciente_nombre: mov.paciente_nombre || '',
      tipo_pagador_id: '',
      tipo_pagador_nombre: '',
      pagador_nombre: '',
      es_aseguradora: false,
      monto_deducible: '',
      metodo_pago_deducible: 'Efectivo'
    });
    setPacienteSearch(mov.paciente_nombre || '');
    setMovimientoDialogOpen(true);
  };

  // ==================== PAGADORES ====================

  const handleSavePagador = async () => {
    if (!pagadorForm.nombre.trim()) {
      toast.error('Ingrese el nombre del pagador');
      return;
    }
    setSubmitting(true);
    try {
      if (editingPagador) {
        await axios.put(`${API_URL}/catalogos/pagadores/${editingPagador.id}`, pagadorForm);
        toast.success('Pagador actualizado');
      } else {
        await axios.post(`${API_URL}/catalogos/pagadores`, pagadorForm);
        toast.success('Pagador creado');
      }
      setPagadorDialogOpen(false);
      setPagadorForm({ nombre: '' });
      setEditingPagador(null);
      fetchPagadores();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar pagador');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeletePagador = async (pagadorId) => {
    if (!confirm('¿Eliminar este tipo de pagador?')) return;
    try {
      await axios.delete(`${API_URL}/catalogos/pagadores/${pagadorId}`);
      toast.success('Pagador eliminado');
      fetchPagadores();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar pagador');
    }
  };

  const handleTogglePagador = async (pagador) => {
    try {
      await axios.put(`${API_URL}/catalogos/pagadores/${pagador.id}`, { activo: !pagador.activo });
      toast.success(pagador.activo ? 'Pagador desactivado' : 'Pagador activado');
      fetchPagadores();
    } catch (error) {
      toast.error('Error al actualizar pagador');
    }
  };

  // ==================== CUENTAS POR COBRAR ====================

  const handleSaveCxC = async () => {
    if (!cxcForm.paciente_nombre || !cxcForm.tipo_pagador_id || !cxcForm.concepto || !cxcForm.monto_total) {
      toast.error('Complete los campos obligatorios');
      return;
    }
    setSubmitting(true);
    try {
      const data = {
        ...cxcForm,
        monto_total: parseFloat(cxcForm.monto_total)
      };
      
      if (editingCxC) {
        await axios.put(`${API_URL}/cxc/${editingCxC.id}`, data);
        toast.success('Cuenta actualizada');
      } else {
        await axios.post(`${API_URL}/cxc`, data);
        toast.success('Cuenta por cobrar creada');
      }
      
      setCxcDialogOpen(false);
      setCxcForm(initialCxCForm);
      setEditingCxC(null);
      setPacienteSearch('');
      setPacientesResults([]);
      fetchCuentasCobrar();
      fetchResumenCxC();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al guardar cuenta');
    } finally {
      setSubmitting(false);
    }
  };

  const openCxCDetalle = async (cuenta) => {
    try {
      const response = await axios.get(`${API_URL}/cxc/${cuenta.id}`);
      setCxcDetalle(response.data);
      setCxcDetalleDialog(true);
    } catch (error) {
      toast.error('Error al cargar detalle');
    }
  };

  const handleSaveAbono = async () => {
    if (!abonoForm.monto || parseFloat(abonoForm.monto) <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    if (parseFloat(abonoForm.monto) > cxcDetalle.saldo_pendiente) {
      toast.error('El abono no puede ser mayor al saldo pendiente');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/cxc/${cxcDetalle.id}/abono`, {
        monto: parseFloat(abonoForm.monto),
        metodo_pago: abonoForm.metodo_pago,
        referencia: abonoForm.referencia,
        registrar_en_caja: abonoForm.registrar_en_caja
      });
      toast.success('Abono registrado');
      setAbonoDialogOpen(false);
      setAbonoForm(initialAbonoForm);
      
      // Recargar detalle
      const response = await axios.get(`${API_URL}/cxc/${cxcDetalle.id}`);
      setCxcDetalle(response.data);
      fetchCuentasCobrar();
      fetchResumenCxC();
      if (abonoForm.registrar_en_caja) {
        fetchCajaEstado();
        fetchMovimientos();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al registrar abono');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== CIERRES FINANCIEROS ====================

  const handleCreateCierreFinanciero = async () => {
    setSubmitting(true);
    try {
      const data = {
        tipo: cierreFinancieroForm.tipo,
        anio: cierreFinancieroForm.anio,
        observaciones: cierreFinancieroForm.observaciones
      };
      
      if (cierreFinancieroForm.tipo === 'Mensual') {
        data.mes = cierreFinancieroForm.mes;
      } else {
        data.semestre = cierreFinancieroForm.semestre;
      }
      
      await axios.post(`${API_URL}/cierres-financieros`, data);
      toast.success('Cierre financiero generado');
      setCierreFinancieroDialogOpen(false);
      setCierreFinancieroForm(initialCierreFinancieroForm);
      fetchCierresFinancieros();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al generar cierre');
    } finally {
      setSubmitting(false);
    }
  };

  const openCierreFinancieroDetalle = async (cierre) => {
    try {
      const response = await axios.get(`${API_URL}/cierres-financieros/${cierre.id}`);
      setCierreFinancieroDetalle(response.data);
      setCierreFinancieroDetalleDialog(true);
    } catch (error) {
      toast.error('Error al cargar detalle');
    }
  };

  const handleRecalcularCierreFinanciero = async (cierreId) => {
    setSubmitting(true);
    try {
      const response = await axios.post(`${API_URL}/cierres-financieros/${cierreId}/recalcular`);
      toast.success('Cierre recalculado');
      setCierreFinancieroDetalle(response.data);
      fetchCierresFinancieros();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al recalcular');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCierreFinanciero = async (cierreId) => {
    if (!confirm('¿Eliminar este cierre financiero?')) return;
    try {
      await axios.delete(`${API_URL}/cierres-financieros/${cierreId}`);
      toast.success('Cierre eliminado');
      setCierreFinancieroDetalleDialog(false);
      fetchCierresFinancieros();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  // ==================== IMPRESIÓN ====================

  const handlePrintCierreDiario = (cierre) => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Cierre de Caja - ${cierre.fecha}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1 { color: #0F6E56; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f4f4f4; }
            .totales { margin-top: 20px; }
            .diferencia { color: ${cierre.diferencia >= 0 ? '#16a34a' : '#dc2626'}; font-weight: bold; }
          </style>
        </head>
        <body>
          <h1>Cierre de Caja</h1>
          <p><strong>Fecha:</strong> ${formatDate(cierre.fecha)}</p>
          <p><strong>Abierto por:</strong> ${cierre.abierto_por_nombre}</p>
          <p><strong>Cerrado por:</strong> ${cierre.cerrado_por_nombre || '-'}</p>
          
          <table>
            <tr><th>Concepto</th><th>Monto</th></tr>
            <tr><td>Monto de Apertura</td><td>${formatCurrency(cierre.monto_apertura)}</td></tr>
            <tr><td>Total Ingresos</td><td>${formatCurrency(cierre.total_ingresos)}</td></tr>
            <tr><td>Total Egresos</td><td>${formatCurrency(cierre.total_egresos)}</td></tr>
            <tr><td><strong>Saldo Esperado (Efectivo)</strong></td><td><strong>${formatCurrency(cierre.saldo_esperado_efectivo)}</strong></td></tr>
            <tr><td>Efectivo Contado</td><td>${formatCurrency(cierre.efectivo_contado)}</td></tr>
            <tr><td>Diferencia</td><td class="diferencia">${formatCurrency(cierre.diferencia)}</td></tr>
          </table>
          
          ${cierre.observaciones ? `<p><strong>Observaciones:</strong> ${cierre.observaciones}</p>` : ''}
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  const handlePrintCierreFinanciero = (cierre) => {
    const printWindow = window.open('', '_blank');
    const periodoLabel = cierre.tipo === 'Mensual' 
      ? `${['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'][cierre.periodo.mes - 1]} ${cierre.periodo.anio}`
      : `${cierre.periodo.semestre === 1 ? 'Primer' : 'Segundo'} Semestre ${cierre.periodo.anio}`;
    
    printWindow.document.write(`
      <html>
        <head>
          <title>Cierre Financiero - ${periodoLabel}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1, h2 { color: #0F6E56; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f4f4f4; }
            .section { margin-top: 30px; }
          </style>
        </head>
        <body>
          <h1>Cierre Financiero ${cierre.tipo}</h1>
          <p><strong>Período:</strong> ${periodoLabel}</p>
          <p><strong>Estado:</strong> ${cierre.estado}</p>
          
          <div class="section">
            <h2>Resumen de Caja</h2>
            <table>
              <tr><th>Concepto</th><th>Monto</th></tr>
              <tr><td>Ingresos</td><td>${formatCurrency(cierre.ingresos_caja)}</td></tr>
              <tr><td>Egresos</td><td>${formatCurrency(cierre.egresos_caja)}</td></tr>
              <tr><td>Costo de Ventas</td><td>${formatCurrency(cierre.costo_ventas)}</td></tr>
              <tr><td>Gastos Pagados</td><td>${formatCurrency(cierre.gastos_pagados)}</td></tr>
              <tr><td>Utilidad Bruta</td><td>${formatCurrency(cierre.utilidad_bruta)}</td></tr>
              <tr><td><strong>Resultado Neto</strong></td><td><strong>${formatCurrency(cierre.resultado_neto)}</strong></td></tr>
            </table>
          </div>
          
          <div class="section">
            <h2>Cuentas por Cobrar</h2>
            <table>
              <tr><th>Tipo</th><th>Emitido</th><th>Cobrado</th><th>Pendiente</th></tr>
              ${cierre.cxc_por_tipo.map(t => `
                <tr>
                  <td>${t.tipo_pagador_nombre}</td>
                  <td>${formatCurrency(t.emitido)}</td>
                  <td>${formatCurrency(t.cobrado)}</td>
                  <td>${formatCurrency(t.pendiente)}</td>
                </tr>
              `).join('')}
              <tr style="font-weight: bold;">
                <td>TOTAL</td>
                <td>${formatCurrency(cierre.cxc_total_emitido)}</td>
                <td>${formatCurrency(cierre.cxc_total_cobrado)}</td>
                <td>${formatCurrency(cierre.cxc_saldo_pendiente)}</td>
              </tr>
            </table>
          </div>
          
          ${cierre.observaciones ? `<p><strong>Observaciones:</strong> ${cierre.observaciones}</p>` : ''}
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  // ==================== HELPERS ====================

  const getEstadoBadge = (estado) => {
    const colors = {
      'Pendiente': 'bg-yellow-100 text-yellow-800',
      'Parcial': 'bg-blue-100 text-blue-800',
      'Pagado': 'bg-green-100 text-green-800',
      'Vencido': 'bg-red-100 text-red-800',
      'Abierto': 'bg-green-100 text-green-800',
      'Cerrado': 'bg-gray-100 text-gray-800',
      'Borrador': 'bg-yellow-100 text-yellow-800',
      'Finalizado': 'bg-green-100 text-green-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  const selectPaciente = (paciente, formType) => {
    const nombrePaciente = paciente.nombre || paciente.nombre_completo || `${paciente.first_name} ${paciente.last_name}`;
    if (formType === 'movimiento') {
      setMovimientoForm(prev => ({
        ...prev,
        paciente_id: paciente.id,
        paciente_nombre: nombrePaciente
      }));
    } else if (formType === 'cxc') {
      setCxcForm(prev => ({
        ...prev,
        paciente_id: paciente.id,
        paciente_nombre: nombrePaciente
      }));
    }
    setPacienteSearch(nombrePaciente);
    setPacientesResults([]);
  };

  // ==================== RENDER ====================

  if (loadingEstado) {
    return (
      <Layout>
        <div className="space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <Skeleton key={i} className="h-32" />)}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Caja</h1>
            <p className="text-slate-500 text-sm">Control financiero del área clínica</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="caja-diaria" className="flex items-center gap-2" data-testid="tab-caja-diaria">
              <Wallet className="w-4 h-4" />
              <span className="hidden sm:inline">Caja Diaria</span>
            </TabsTrigger>
            <TabsTrigger value="cuentas-cobrar" className="flex items-center gap-2" data-testid="tab-cxc">
              <Users className="w-4 h-4" />
              <span className="hidden sm:inline">Cuentas por Cobrar</span>
            </TabsTrigger>
            <TabsTrigger value="cierres-financieros" className="flex items-center gap-2" data-testid="tab-cierres">
              <Calendar className="w-4 h-4" />
              <span className="hidden sm:inline">Cierres Financieros</span>
            </TabsTrigger>
          </TabsList>

          {/* ==================== TAB: CAJA DIARIA ==================== */}
          <TabsContent value="caja-diaria" className="space-y-6">
            {/* Estado de Caja */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className={`${cajaEstado?.caja_abierta ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Estado</p>
                      <p className="text-xl font-bold">{cajaEstado?.caja_abierta ? 'Abierta' : 'Cerrada'}</p>
                    </div>
                    {cajaEstado?.caja_abierta ? (
                      <Unlock className="w-8 h-8 text-green-600" />
                    ) : (
                      <Lock className="w-8 h-8 text-gray-400" />
                    )}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Ingresos Hoy</p>
                      <p className="text-xl font-bold text-green-600">
                        {formatCurrency(cajaEstado?.totales_dia?.total_ingresos || 0)}
                      </p>
                    </div>
                    <ArrowUpCircle className="w-8 h-8 text-green-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Egresos Hoy</p>
                      <p className="text-xl font-bold text-red-600">
                        {formatCurrency(cajaEstado?.totales_dia?.total_egresos || 0)}
                      </p>
                    </div>
                    <ArrowDownCircle className="w-8 h-8 text-red-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Saldo Efectivo</p>
                      <p className="text-xl font-bold text-blue-700">
                        {formatCurrency(cajaEstado?.saldo_efectivo_vivo || 0)}
                      </p>
                    </div>
                    <Banknote className="w-8 h-8 text-blue-600" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Acciones de Caja */}
            <div className="flex flex-wrap gap-2">
              {!cajaEstado?.caja_abierta ? (
                // Caja cerrada o no existe
                cajaEstado?.cierre?.estado === 'Cerrado' ? (
                  // Hay cierre del día pero está cerrado - mostrar Reabrir (solo SuperAdmin)
                  isSuperAdmin && (
                    <Button 
                      onClick={() => handleReabrirCaja(cajaEstado.cierre.id)}
                      disabled={submitting}
                      className="bg-yellow-600 hover:bg-yellow-700"
                      data-testid="btn-reabrir-caja"
                    >
                      <Unlock className="w-4 h-4 mr-2" />
                      {submitting ? 'Reabriendo...' : 'Reabrir Caja del Día'}
                    </Button>
                  )
                ) : (
                  // No hay cierre del día - mostrar Abrir
                  <Button 
                    onClick={() => setAperturaDialogOpen(true)}
                    className="bg-green-600 hover:bg-green-700"
                    data-testid="btn-abrir-caja"
                  >
                    <Unlock className="w-4 h-4 mr-2" />
                    Abrir Caja
                  </Button>
                )
              ) : (
                <>
                  <Button 
                    onClick={() => {
                      setMovimientoForm(initialMovimientoForm);
                      setEditingMovimiento(null);
                      setMovimientoDialogOpen(true);
                    }}
                    className="bg-blue-600 hover:bg-blue-700"
                    data-testid="btn-nuevo-movimiento"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Nuevo Movimiento
                  </Button>
                  <Button 
                    variant="outline"
                    onClick={() => {
                      setCierreForm({ 
                        efectivo_contado: cajaEstado?.saldo_efectivo_vivo?.toString() || '', 
                        observaciones: '' 
                      });
                      setCierreDialogOpen(true);
                    }}
                    className="border-red-200 text-red-600 hover:bg-red-50"
                    data-testid="btn-cerrar-caja"
                  >
                    <Lock className="w-4 h-4 mr-2" />
                    Cerrar Caja
                  </Button>
                </>
              )}
              <Button 
                variant="outline"
                onClick={() => {
                  fetchHistorialCierres();
                  setHistorialDialogOpen(true);
                }}
                data-testid="btn-historial-cierres"
              >
                <Clock className="w-4 h-4 mr-2" />
                Historial de Cierres
              </Button>
            </div>

            {/* Tabla de Movimientos */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Movimientos del Día</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingMovimientos ? (
                  <div className="space-y-2">
                    {[1,2,3].map(i => <Skeleton key={i} className="h-12" />)}
                  </div>
                ) : movimientos.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <Wallet className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No hay movimientos registrados hoy</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Hora</TableHead>
                          <TableHead>Categoría</TableHead>
                          <TableHead>Concepto</TableHead>
                          <TableHead>Paciente</TableHead>
                          <TableHead>Método</TableHead>
                          <TableHead className="text-right">Monto</TableHead>
                          <TableHead className="text-center">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {movimientos.map((mov) => (
                          <TableRow key={mov.id}>
                            <TableCell className="text-sm">
                              {formatTime(mov.fecha)}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{mov.categoria}</Badge>
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">{mov.concepto}</TableCell>
                            <TableCell className="text-sm">{mov.paciente_nombre || '-'}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{mov.metodo_pago}</Badge>
                            </TableCell>
                            <TableCell className="text-right font-medium text-green-600">
                              +{formatCurrency(mov.monto)}
                            </TableCell>
                            <TableCell className="text-center">
                              {!mov.bloqueado && cajaEstado?.caja_abierta && (
                                <div className="flex justify-center gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => openEditMovimiento(mov)}
                                  >
                                    <Pencil className="w-4 h-4" />
                                  </Button>
                                  {isSuperAdmin && (
                                    <Button 
                                      variant="ghost" 
                                      size="sm"
                                      className="text-red-600"
                                      onClick={() => {
                                        setMovimientoToDelete(mov);
                                        setDeleteMovimientoDialog(true);
                                      }}
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  )}
                                </div>
                              )}
                              {mov.bloqueado && (
                                <Lock className="w-4 h-4 text-gray-400 mx-auto" />
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ==================== TAB: CUENTAS POR COBRAR ==================== */}
          <TabsContent value="cuentas-cobrar" className="space-y-6">
            {/* Resumen CxC */}
            {resumenCxC && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-sm text-slate-500">Total Emitido</p>
                    <p className="text-xl font-bold">{formatCurrency(resumenCxC.total_emitido)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-sm text-slate-500">Total Cobrado</p>
                    <p className="text-xl font-bold text-green-600">{formatCurrency(resumenCxC.total_cobrado)}</p>
                  </CardContent>
                </Card>
                <Card className="border-yellow-200 bg-yellow-50">
                  <CardContent className="pt-4">
                    <p className="text-sm text-slate-500">Saldo Pendiente</p>
                    <p className="text-xl font-bold text-yellow-700">{formatCurrency(resumenCxC.saldo_pendiente)}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-sm text-slate-500">Cuentas Activas</p>
                    <p className="text-xl font-bold">{resumenCxC.cantidad_cuentas}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Filtros y Acciones */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 flex flex-wrap gap-2">
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                  <Input
                    placeholder="Buscar..."
                    value={cxcFilters.search}
                    onChange={(e) => setCxcFilters(prev => ({ ...prev, search: e.target.value }))}
                    className="pl-9"
                  />
                </div>
                <Select 
                  value={cxcFilters.tipo_pagador || "all"} 
                  onValueChange={(v) => setCxcFilters(prev => ({ ...prev, tipo_pagador: v === "all" ? "" : v }))}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Tipo de Pagador" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {pagadores.filter(p => p.activo).map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select 
                  value={cxcFilters.estado || "all"} 
                  onValueChange={(v) => setCxcFilters(prev => ({ ...prev, estado: v === "all" ? "" : v }))}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="Pendiente">Pendiente</SelectItem>
                    <SelectItem value="Parcial">Parcial</SelectItem>
                    <SelectItem value="Pagado">Pagado</SelectItem>
                    <SelectItem value="Vencido">Vencido</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={() => {
                    setCxcForm(initialCxCForm);
                    setEditingCxC(null);
                    setPacienteSearch('');
                    setCxcDialogOpen(true);
                  }}
                  className="bg-blue-600 hover:bg-blue-700"
                  data-testid="btn-nueva-cxc"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Nueva Cuenta
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setPagadorDialogOpen(true)}
                  data-testid="btn-gestionar-pagadores"
                >
                  <Users className="w-4 h-4 mr-2" />
                  Pagadores
                </Button>
              </div>
            </div>

            {/* Tabla CxC */}
            <Card>
              <CardContent className="pt-6">
                {loadingCxC ? (
                  <div className="space-y-2">
                    {[1,2,3].map(i => <Skeleton key={i} className="h-12" />)}
                  </div>
                ) : cuentasCobrar.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No hay cuentas por cobrar</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Fecha</TableHead>
                          <TableHead>Paciente</TableHead>
                          <TableHead>Tipo Pagador</TableHead>
                          <TableHead>Concepto</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                          <TableHead className="text-right">Pagado</TableHead>
                          <TableHead className="text-right">Pendiente</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead className="text-center">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cuentasCobrar.map((cuenta) => (
                          <TableRow key={cuenta.id}>
                            <TableCell className="text-sm">{formatDate(cuenta.fecha_emision)}</TableCell>
                            <TableCell>{cuenta.paciente_nombre}</TableCell>
                            <TableCell>{cuenta.tipo_pagador_nombre}</TableCell>
                            <TableCell className="max-w-[200px] truncate">{cuenta.concepto}</TableCell>
                            <TableCell className="text-right">{formatCurrency(cuenta.monto_total)}</TableCell>
                            <TableCell className="text-right text-green-600">{formatCurrency(cuenta.monto_pagado)}</TableCell>
                            <TableCell className="text-right font-medium text-yellow-600">{formatCurrency(cuenta.saldo_pendiente)}</TableCell>
                            <TableCell>
                              <Badge className={getEstadoBadge(cuenta.estado)}>{cuenta.estado}</Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => openCxCDetalle(cuenta)}
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ==================== TAB: CIERRES FINANCIEROS ==================== */}
          <TabsContent value="cierres-financieros" className="space-y-6">
            {/* Acciones */}
            <div className="flex justify-end">
              <Button 
                onClick={() => {
                  setCierreFinancieroForm(initialCierreFinancieroForm);
                  setCierreFinancieroDialogOpen(true);
                }}
                className="bg-blue-600 hover:bg-blue-700"
                data-testid="btn-nuevo-cierre-financiero"
              >
                <Plus className="w-4 h-4 mr-2" />
                Generar Cierre
              </Button>
            </div>

            {/* Lista de Cierres */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Cierres Financieros</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingCierresF ? (
                  <div className="space-y-2">
                    {[1,2,3].map(i => <Skeleton key={i} className="h-12" />)}
                  </div>
                ) : cierresFinancieros.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <Calendar className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No hay cierres financieros</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Período</TableHead>
                          <TableHead className="text-right">Ingresos</TableHead>
                          <TableHead className="text-right">Egresos</TableHead>
                          <TableHead className="text-right">Costo Ventas</TableHead>
                          <TableHead className="text-right">Utilidad Bruta</TableHead>
                          <TableHead className="text-right">Resultado Neto</TableHead>
                          <TableHead className="text-right">CxC Pendiente</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead className="text-center">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cierresFinancieros.map((cierre) => {
                          const periodoLabel = cierre.tipo === 'Mensual'
                            ? `${['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][cierre.periodo.mes - 1]} ${cierre.periodo.anio}`
                            : `S${cierre.periodo.semestre} ${cierre.periodo.anio}`;
                          return (
                            <TableRow key={cierre.id}>
                              <TableCell>
                                <Badge variant="outline">{cierre.tipo}</Badge>
                              </TableCell>
                              <TableCell className="font-medium">{periodoLabel}</TableCell>
                              <TableCell className="text-right text-green-600">{formatCurrency(cierre.ingresos_caja)}</TableCell>
                              <TableCell className="text-right text-red-600">{formatCurrency(cierre.egresos_caja)}</TableCell>
                              <TableCell className="text-right text-red-600">{formatCurrency(cierre.costo_ventas)}</TableCell>
                              <TableCell className="text-right text-blue-600">{formatCurrency(cierre.utilidad_bruta)}</TableCell>
                              <TableCell className={`text-right font-medium ${cierre.resultado_neto >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(cierre.resultado_neto)}
                              </TableCell>
                              <TableCell className="text-right text-yellow-600">{formatCurrency(cierre.cxc_saldo_pendiente)}</TableCell>
                              <TableCell>
                                <Badge className={getEstadoBadge(cierre.estado)}>{cierre.estado}</Badge>
                              </TableCell>
                              <TableCell className="text-center">
                                <div className="flex justify-center gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => openCierreFinancieroDetalle(cierre)}
                                  >
                                    <Eye className="w-4 h-4" />
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => handlePrintCierreFinanciero(cierre)}
                                  >
                                    <Printer className="w-4 h-4" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* ==================== DIALOGS ==================== */}

      {/* Dialog: Apertura de Caja */}
      <Dialog open={aperturaDialogOpen} onOpenChange={setAperturaDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Abrir Caja</DialogTitle>
            <DialogDescription>Ingrese el monto inicial de efectivo en caja</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Monto de Apertura (GTQ)</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={montoApertura}
                onChange={(e) => setMontoApertura(e.target.value)}
                placeholder="0.00"
                data-testid="input-monto-apertura"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAperturaDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleAperturaCaja} disabled={submitting} className="bg-green-600 hover:bg-green-700">
              {submitting ? 'Abriendo...' : 'Abrir Caja'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Cierre de Caja */}
      <Dialog open={cierreDialogOpen} onOpenChange={setCierreDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cerrar Caja</DialogTitle>
            <DialogDescription>
              Saldo esperado en efectivo: <strong>{formatCurrency(cajaEstado?.saldo_efectivo_vivo || 0)}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Efectivo Contado (GTQ) *</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={cierreForm.efectivo_contado}
                onChange={(e) => setCierreForm(prev => ({ ...prev, efectivo_contado: e.target.value }))}
                placeholder="0.00"
                data-testid="input-efectivo-contado"
              />
            </div>
            <div>
              <Label>Observaciones</Label>
              <Textarea
                value={cierreForm.observaciones}
                onChange={(e) => setCierreForm(prev => ({ ...prev, observaciones: e.target.value }))}
                placeholder="Notas sobre el cierre..."
              />
            </div>
            {cierreForm.efectivo_contado && (
              <div className={`p-3 rounded-lg ${parseFloat(cierreForm.efectivo_contado) - (cajaEstado?.saldo_efectivo_vivo || 0) === 0 ? 'bg-green-50' : 'bg-yellow-50'}`}>
                <p className="text-sm">
                  Diferencia: <strong className={parseFloat(cierreForm.efectivo_contado) - (cajaEstado?.saldo_efectivo_vivo || 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {formatCurrency(parseFloat(cierreForm.efectivo_contado) - (cajaEstado?.saldo_efectivo_vivo || 0))}
                  </strong>
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCierreDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleCierreCaja} disabled={submitting} className="bg-red-600 hover:bg-red-700">
              {submitting ? 'Cerrando...' : 'Cerrar Caja'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Nuevo/Editar Movimiento */}
      <Dialog open={movimientoDialogOpen} onOpenChange={setMovimientoDialogOpen}>
        <DialogContent className="max-w-xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>{editingMovimiento ? 'Editar Movimiento' : 'Nuevo Movimiento'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 overflow-y-auto pr-2">
            {/* 1. PACIENTE - Siempre primero */}
            <div>
              <Label>Paciente *</Label>
              <div className="relative">
                <Input
                  value={pacienteSearch}
                  onChange={(e) => {
                    setPacienteSearch(e.target.value);
                    setMovimientoForm(prev => ({ ...prev, paciente_id: '', paciente_nombre: '' }));
                  }}
                  placeholder="Buscar paciente..."
                  className={movimientoForm.paciente_id ? 'border-green-500' : ''}
                />
                {movimientoForm.paciente_id && (
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-green-500 text-sm">✓</span>
                )}
                {pacientesResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-40 overflow-y-auto">
                    {pacientesResults.map(p => (
                      <div
                        key={p.id}
                        className="px-3 py-2 hover:bg-slate-100 cursor-pointer text-sm"
                        onClick={() => selectPaciente(p, 'movimiento')}
                      >
                        {p.nombre || p.nombre_completo || `${p.first_name} ${p.last_name}`}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 2. CATEGORÍA Y CONCEPTO - En fila */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Categoría *</Label>
                <Select 
                  value={movimientoForm.categoria} 
                  onValueChange={(v) => setMovimientoForm(prev => ({ ...prev, categoria: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIAS_INGRESO.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Concepto *</Label>
                <Input
                  value={movimientoForm.concepto}
                  onChange={(e) => setMovimientoForm(prev => ({ ...prev, concepto: e.target.value }))}
                  placeholder="Descripción del servicio"
                />
              </div>
            </div>

            {/* 3. MONTO TOTAL */}
            <div>
              <Label>Monto Total (GTQ) *</Label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={movimientoForm.monto}
                onChange={(e) => setMovimientoForm(prev => ({ ...prev, monto: e.target.value }))}
                placeholder="0.00"
                className="text-lg font-medium"
              />
            </div>

            {/* 4. MÉTODO DE PAGO Y REFERENCIA - En fila */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Método de Pago *</Label>
                <Select 
                  value={movimientoForm.metodo_pago} 
                  onValueChange={(v) => setMovimientoForm(prev => ({ 
                    ...prev, 
                    metodo_pago: v,
                    // Si no es CxC, limpiar los campos relacionados
                    ...(v !== 'Cuenta por Cobrar' ? { 
                      tipo_pagador_id: '', 
                      tipo_pagador_nombre: '',
                      es_aseguradora: false,
                      monto_deducible: ''
                    } : {})
                  }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {METODOS_PAGO.map(m => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Referencia</Label>
                <Input
                  value={movimientoForm.referencia}
                  onChange={(e) => setMovimientoForm(prev => ({ ...prev, referencia: e.target.value }))}
                  placeholder="No. recibo, factura, etc."
                />
              </div>
            </div>

            {/* CAMPOS ADICIONALES PARA CUENTA POR COBRAR */}
            {movimientoForm.metodo_pago === 'Cuenta por Cobrar' && (
              <div className="border-t pt-4 space-y-4">
                <p className="text-sm font-medium text-slate-700 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Información de Cuenta por Cobrar
                </p>
                
                {/* Tipo de Pagador y Nombre en fila */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Adjudicar a *</Label>
                    <Select 
                      value={movimientoForm.tipo_pagador_id || "select"} 
                      onValueChange={(v) => {
                        if (v === "select") return;
                        const pag = pagadores.find(p => p.id === v);
                        const esAseguradora = pag?.nombre?.toLowerCase().includes('asegura') || 
                                             pag?.nombre?.toLowerCase().includes('seguro');
                        setMovimientoForm(prev => ({ 
                          ...prev, 
                          tipo_pagador_id: v,
                          tipo_pagador_nombre: pag?.nombre || '',
                          es_aseguradora: esAseguradora,
                          monto_deducible: esAseguradora ? prev.monto_deducible : ''
                        }));
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccione..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="select" disabled>Seleccione...</SelectItem>
                        {pagadores.filter(p => p.activo).map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Nombre del Pagador</Label>
                    <Input
                      value={movimientoForm.pagador_nombre}
                      onChange={(e) => setMovimientoForm(prev => ({ ...prev, pagador_nombre: e.target.value }))}
                      placeholder="Ej: Seguros G&T, IGSS Zona 1"
                    />
                  </div>
                </div>

                {/* Si es Aseguradora, mostrar campo de deducible */}
                {movimientoForm.es_aseguradora && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
                    <p className="text-sm font-medium text-blue-800 flex items-center gap-2">
                      <CreditCard className="w-4 h-4" />
                      Pago con Seguro
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-blue-700">Monto Deducible</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={movimientoForm.monto_deducible}
                          onChange={(e) => setMovimientoForm(prev => ({ ...prev, monto_deducible: e.target.value }))}
                          placeholder="0.00"
                          className="bg-white"
                        />
                        <p className="text-xs text-blue-600 mt-1">Se registra en caja del día</p>
                      </div>
                      {movimientoForm.monto_deducible && parseFloat(movimientoForm.monto_deducible) > 0 && (
                        <div>
                          <Label className="text-blue-700">Método de Pago</Label>
                          <Select 
                            value={movimientoForm.metodo_pago_deducible} 
                            onValueChange={(v) => setMovimientoForm(prev => ({ ...prev, metodo_pago_deducible: v }))}
                          >
                            <SelectTrigger className="bg-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Efectivo">Efectivo</SelectItem>
                              <SelectItem value="Tarjeta">Tarjeta</SelectItem>
                              <SelectItem value="Transferencia">Transferencia</SelectItem>
                              <SelectItem value="Cheque">Cheque</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    </div>
                    {movimientoForm.monto_deducible && parseFloat(movimientoForm.monto_deducible) > 0 && (
                      <div className="text-sm bg-white p-3 rounded border grid grid-cols-3 gap-2">
                        <div className="text-center">
                          <p className="text-slate-500 text-xs">Monto Total</p>
                          <p className="font-bold">{formatCurrency(parseFloat(movimientoForm.monto) || 0)}</p>
                        </div>
                        <div className="text-center border-x">
                          <p className="text-green-600 text-xs">Deducible (Caja)</p>
                          <p className="font-bold text-green-600">{formatCurrency(parseFloat(movimientoForm.monto_deducible) || 0)}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-yellow-600 text-xs">A CxC</p>
                          <p className="font-bold text-yellow-600">
                            {formatCurrency((parseFloat(movimientoForm.monto) || 0) - (parseFloat(movimientoForm.monto_deducible) || 0))}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setMovimientoDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveMovimiento} disabled={submitting} className="bg-blue-600 hover:bg-blue-700">
              {submitting ? 'Guardando...' : (movimientoForm.metodo_pago === 'Cuenta por Cobrar' ? 'Crear CxC' : 'Guardar')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Eliminar Movimiento */}
      <Dialog open={deleteMovimientoDialog} onOpenChange={setDeleteMovimientoDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar Movimiento</DialogTitle>
            <DialogDescription>
              ¿Está seguro de eliminar este movimiento? Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteMovimientoDialog(false)}>Cancelar</Button>
            <Button onClick={handleDeleteMovimiento} disabled={submitting} className="bg-red-600 hover:bg-red-700">
              {submitting ? 'Eliminando...' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Historial de Cierres */}
      <Dialog open={historialDialogOpen} onOpenChange={setHistorialDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Historial de Cierres</DialogTitle>
          </DialogHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Apertura</TableHead>
                <TableHead className="text-right">Ingresos</TableHead>
                <TableHead className="text-right">Egresos</TableHead>
                <TableHead className="text-right">Diferencia</TableHead>
                <TableHead className="text-center">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {historialCierres.map(cierre => (
                <TableRow key={cierre.id}>
                  <TableCell>{formatDate(cierre.fecha)}</TableCell>
                  <TableCell>
                    <Badge className={getEstadoBadge(cierre.estado)}>{cierre.estado}</Badge>
                  </TableCell>
                  <TableCell className="text-right">{formatCurrency(cierre.monto_apertura)}</TableCell>
                  <TableCell className="text-right text-green-600">{formatCurrency(cierre.total_ingresos)}</TableCell>
                  <TableCell className="text-right text-red-600">{formatCurrency(cierre.total_egresos)}</TableCell>
                  <TableCell className={`text-right ${(cierre.diferencia || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {cierre.diferencia !== null ? formatCurrency(cierre.diferencia) : '-'}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex justify-center gap-1">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={async () => {
                          const response = await axios.get(`${API_URL}/caja/cierres/${cierre.id}`);
                          setCierreDetalle(response.data);
                          setCierreDetalleDialog(true);
                        }}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handlePrintCierreDiario(cierre)}
                      >
                        <Printer className="w-4 h-4" />
                      </Button>
                      {isSuperAdmin && cierre.estado === 'Cerrado' && (
                        <Button 
                          variant="ghost" 
                          size="sm"
                          className="text-yellow-600"
                          onClick={() => handleReabrirCaja(cierre.id)}
                        >
                          <Unlock className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>

      {/* Dialog: Detalle de Cierre Diario */}
      <Dialog open={cierreDetalleDialog} onOpenChange={setCierreDetalleDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Detalle de Cierre - {cierreDetalle && formatDate(cierreDetalle.fecha)}</DialogTitle>
          </DialogHeader>
          {cierreDetalle && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">Estado</p>
                  <Badge className={getEstadoBadge(cierreDetalle.estado)}>{cierreDetalle.estado}</Badge>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Abierto por</p>
                  <p className="font-medium">{cierreDetalle.abierto_por_nombre}</p>
                </div>
              </div>
              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between">
                  <span>Monto Apertura</span>
                  <span className="font-medium">{formatCurrency(cierreDetalle.monto_apertura)}</span>
                </div>
                <div className="flex justify-between text-green-600">
                  <span>Total Ingresos</span>
                  <span className="font-medium">+{formatCurrency(cierreDetalle.total_ingresos)}</span>
                </div>
                <div className="flex justify-between text-red-600">
                  <span>Total Egresos</span>
                  <span className="font-medium">-{formatCurrency(cierreDetalle.total_egresos)}</span>
                </div>
                <div className="border-t pt-2 flex justify-between font-bold">
                  <span>Saldo Esperado (Efectivo)</span>
                  <span>{formatCurrency(cierreDetalle.saldo_esperado_efectivo)}</span>
                </div>
                {cierreDetalle.estado === 'Cerrado' && (
                  <>
                    <div className="flex justify-between">
                      <span>Efectivo Contado</span>
                      <span className="font-medium">{formatCurrency(cierreDetalle.efectivo_contado)}</span>
                    </div>
                    <div className={`flex justify-between font-bold ${cierreDetalle.diferencia >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      <span>Diferencia</span>
                      <span>{formatCurrency(cierreDetalle.diferencia)}</span>
                    </div>
                  </>
                )}
              </div>
              {cierreDetalle.observaciones && (
                <div className="border-t pt-4">
                  <p className="text-sm text-slate-500">Observaciones</p>
                  <p>{cierreDetalle.observaciones}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCierreDetalleDialog(false)}>Cerrar</Button>
            {cierreDetalle && (
              <Button variant="outline" onClick={() => handlePrintCierreDiario(cierreDetalle)}>
                <Printer className="w-4 h-4 mr-2" />
                Imprimir
              </Button>
            )}
            {isSuperAdmin && cierreDetalle?.estado === 'Cerrado' && (
              <Button 
                onClick={() => handleReabrirCaja(cierreDetalle.id)} 
                disabled={submitting}
                className="bg-yellow-600 hover:bg-yellow-700"
              >
                <Unlock className="w-4 h-4 mr-2" />
                Reabrir
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Gestionar Pagadores */}
      <Dialog open={pagadorDialogOpen} onOpenChange={setPagadorDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Tipos de Pagador</DialogTitle>
            <DialogDescription>Administre los tipos de pagador para cuentas por cobrar</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={pagadorForm.nombre}
                onChange={(e) => setPagadorForm({ nombre: e.target.value })}
                placeholder="Nombre del pagador"
              />
              <Button onClick={handleSavePagador} disabled={submitting}>
                {editingPagador ? 'Actualizar' : 'Agregar'}
              </Button>
            </div>
            <div className="border rounded-lg max-h-60 overflow-y-auto">
              {pagadores.map(p => (
                <div key={p.id} className={`flex items-center justify-between px-3 py-2 border-b last:border-b-0 ${!p.activo ? 'opacity-50' : ''}`}>
                  <span>{p.nombre}</span>
                  <div className="flex gap-1">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => {
                        setEditingPagador(p);
                        setPagadorForm({ nombre: p.nombre });
                      }}
                    >
                      <Pencil className="w-3 h-3" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleTogglePagador(p)}
                    >
                      {p.activo ? <X className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setPagadorDialogOpen(false);
              setEditingPagador(null);
              setPagadorForm({ nombre: '' });
            }}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Nueva/Editar Cuenta por Cobrar */}
      <Dialog open={cxcDialogOpen} onOpenChange={setCxcDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingCxC ? 'Editar Cuenta' : 'Nueva Cuenta por Cobrar'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
            <div>
              <Label>Paciente *</Label>
              <div className="relative">
                <Input
                  value={pacienteSearch}
                  onChange={(e) => {
                    setPacienteSearch(e.target.value);
                    setCxcForm(prev => ({ ...prev, paciente_id: '', paciente_nombre: '' }));
                  }}
                  placeholder="Buscar paciente..."
                />
                {pacientesResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-40 overflow-y-auto">
                    {pacientesResults.map(p => (
                      <div
                        key={p.id}
                        className="px-3 py-2 hover:bg-slate-100 cursor-pointer text-sm"
                        onClick={() => selectPaciente(p, 'cxc')}
                      >
                        {p.nombre || p.nombre_completo || `${p.first_name} ${p.last_name}`}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div>
              <Label>Tipo de Pagador *</Label>
              <Select 
                value={cxcForm.tipo_pagador_id} 
                onValueChange={(v) => {
                  const pag = pagadores.find(p => p.id === v);
                  setCxcForm(prev => ({ 
                    ...prev, 
                    tipo_pagador_id: v,
                    tipo_pagador_nombre: pag?.nombre || ''
                  }));
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccione..." />
                </SelectTrigger>
                <SelectContent>
                  {pagadores.filter(p => p.activo).map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Nombre del Pagador / Aseguradora</Label>
              <Input
                value={cxcForm.pagador_nombre}
                onChange={(e) => setCxcForm(prev => ({ ...prev, pagador_nombre: e.target.value }))}
                placeholder="Ej: Aseguradora XYZ, No. afiliación IGSS"
              />
            </div>
            <div>
              <Label>Concepto *</Label>
              <Input
                value={cxcForm.concepto}
                onChange={(e) => setCxcForm(prev => ({ ...prev, concepto: e.target.value }))}
                placeholder="Descripción del servicio"
              />
            </div>
            <div>
              <Label>Referencia</Label>
              <Input
                value={cxcForm.referencia}
                onChange={(e) => setCxcForm(prev => ({ ...prev, referencia: e.target.value }))}
                placeholder="No. factura, autorización, etc."
              />
            </div>
            <div>
              <Label>Monto Total (GTQ) *</Label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={cxcForm.monto_total}
                onChange={(e) => setCxcForm(prev => ({ ...prev, monto_total: e.target.value }))}
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Fecha de Vencimiento</Label>
              <Input
                type="date"
                value={cxcForm.fecha_vencimiento}
                onChange={(e) => setCxcForm(prev => ({ ...prev, fecha_vencimiento: e.target.value }))}
              />
            </div>
            <div>
              <Label>Notas</Label>
              <Textarea
                value={cxcForm.notas}
                onChange={(e) => setCxcForm(prev => ({ ...prev, notas: e.target.value }))}
                placeholder="Observaciones adicionales..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCxcDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveCxC} disabled={submitting} className="bg-blue-600 hover:bg-blue-700">
              {submitting ? 'Guardando...' : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Detalle de Cuenta por Cobrar */}
      <Dialog open={cxcDetalleDialog} onOpenChange={setCxcDetalleDialog}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Detalle de Cuenta por Cobrar</DialogTitle>
          </DialogHeader>
          {cxcDetalle && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">Paciente</p>
                  <p className="font-medium">{cxcDetalle.paciente_nombre}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Estado</p>
                  <Badge className={getEstadoBadge(cxcDetalle.estado)}>{cxcDetalle.estado}</Badge>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Tipo de Pagador</p>
                  <p className="font-medium">{cxcDetalle.tipo_pagador_nombre}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Pagador</p>
                  <p className="font-medium">{cxcDetalle.pagador_nombre || '-'}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-slate-500">Concepto</p>
                <p>{cxcDetalle.concepto}</p>
              </div>
              <div className="border-t pt-4 grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-sm text-slate-500">Total</p>
                  <p className="text-lg font-bold">{formatCurrency(cxcDetalle.monto_total)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Pagado</p>
                  <p className="text-lg font-bold text-green-600">{formatCurrency(cxcDetalle.monto_pagado)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Pendiente</p>
                  <p className="text-lg font-bold text-yellow-600">{formatCurrency(cxcDetalle.saldo_pendiente)}</p>
                </div>
              </div>
              
              {/* Historial de Abonos */}
              {cxcDetalle.abonos && cxcDetalle.abonos.length > 0 && (
                <div className="border-t pt-4">
                  <p className="font-medium mb-2">Historial de Abonos</p>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {cxcDetalle.abonos.map((abono, idx) => (
                      <div key={idx} className="flex justify-between items-center text-sm bg-slate-50 p-2 rounded">
                        <div>
                          <p>{formatDate(abono.fecha)}</p>
                          <p className="text-slate-500">{abono.metodo_pago}</p>
                        </div>
                        <p className="font-medium text-green-600">+{formatCurrency(abono.monto)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={() => setCxcDetalleDialog(false)}>Cerrar</Button>
            {cxcDetalle && cxcDetalle.saldo_pendiente > 0 && (
              <Button 
                onClick={() => setAbonoDialogOpen(true)}
                className="bg-green-600 hover:bg-green-700"
              >
                <DollarSign className="w-4 h-4 mr-2" />
                Registrar Abono
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Registrar Abono */}
      <Dialog open={abonoDialogOpen} onOpenChange={setAbonoDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Abono</DialogTitle>
            <DialogDescription>
              Saldo pendiente: <strong>{cxcDetalle && formatCurrency(cxcDetalle.saldo_pendiente)}</strong>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Monto (GTQ) *</Label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                max={cxcDetalle?.saldo_pendiente}
                value={abonoForm.monto}
                onChange={(e) => setAbonoForm(prev => ({ ...prev, monto: e.target.value }))}
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Método de Pago *</Label>
              <Select 
                value={abonoForm.metodo_pago} 
                onValueChange={(v) => setAbonoForm(prev => ({ ...prev, metodo_pago: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METODOS_PAGO.map(m => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Referencia</Label>
              <Input
                value={abonoForm.referencia}
                onChange={(e) => setAbonoForm(prev => ({ ...prev, referencia: e.target.value }))}
                placeholder="No. recibo, comprobante, etc."
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="registrar-caja"
                checked={abonoForm.registrar_en_caja}
                onChange={(e) => setAbonoForm(prev => ({ ...prev, registrar_en_caja: e.target.checked }))}
                className="rounded"
              />
              <Label htmlFor="registrar-caja" className="cursor-pointer">
                Registrar como ingreso en caja diaria
              </Label>
            </div>
            {abonoForm.registrar_en_caja && !cajaEstado?.caja_abierta && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                La caja del día no está abierta. El abono se registrará pero no se sumará a la caja diaria.
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAbonoDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveAbono} disabled={submitting} className="bg-green-600 hover:bg-green-700">
              {submitting ? 'Guardando...' : 'Registrar Abono'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Generar Cierre Financiero */}
      <Dialog open={cierreFinancieroDialogOpen} onOpenChange={setCierreFinancieroDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generar Cierre Financiero</DialogTitle>
            <DialogDescription>
              Genere un resumen financiero del período seleccionado
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Tipo de Cierre</Label>
              <Select 
                value={cierreFinancieroForm.tipo} 
                onValueChange={(v) => setCierreFinancieroForm(prev => ({ ...prev, tipo: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Mensual">Mensual</SelectItem>
                  <SelectItem value="Semestral">Semestral</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {cierreFinancieroForm.tipo === 'Mensual' ? (
              <div>
                <Label>Mes</Label>
                <Select 
                  value={cierreFinancieroForm.mes.toString()} 
                  onValueChange={(v) => setCierreFinancieroForm(prev => ({ ...prev, mes: parseInt(v) }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'].map((m, i) => (
                      <SelectItem key={i+1} value={(i+1).toString()}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div>
                <Label>Semestre</Label>
                <Select 
                  value={cierreFinancieroForm.semestre.toString()} 
                  onValueChange={(v) => setCierreFinancieroForm(prev => ({ ...prev, semestre: parseInt(v) }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Primer Semestre (Ene-Jun)</SelectItem>
                    <SelectItem value="2">Segundo Semestre (Jul-Dic)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div>
              <Label>Año</Label>
              <Select 
                value={cierreFinancieroForm.anio.toString()} 
                onValueChange={(v) => setCierreFinancieroForm(prev => ({ ...prev, anio: parseInt(v) }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[2024, 2025, 2026, 2027].map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Observaciones</Label>
              <Textarea
                value={cierreFinancieroForm.observaciones}
                onChange={(e) => setCierreFinancieroForm(prev => ({ ...prev, observaciones: e.target.value }))}
                placeholder="Notas del cierre..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCierreFinancieroDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleCreateCierreFinanciero} disabled={submitting} className="bg-blue-600 hover:bg-blue-700">
              {submitting ? 'Generando...' : 'Generar Cierre'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Detalle de Cierre Financiero */}
      <Dialog open={cierreFinancieroDetalleDialog} onOpenChange={setCierreFinancieroDetalleDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Cierre Financiero {cierreFinancieroDetalle?.tipo} - {
                cierreFinancieroDetalle?.tipo === 'Mensual'
                  ? `${['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'][cierreFinancieroDetalle?.periodo?.mes - 1]} ${cierreFinancieroDetalle?.periodo?.anio}`
                  : `${cierreFinancieroDetalle?.periodo?.semestre === 1 ? 'Primer' : 'Segundo'} Semestre ${cierreFinancieroDetalle?.periodo?.anio}`
              }
            </DialogTitle>
          </DialogHeader>
          {cierreFinancieroDetalle && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <Badge className={getEstadoBadge(cierreFinancieroDetalle.estado)}>
                  {cierreFinancieroDetalle.estado}
                </Badge>
                <p className="text-sm text-slate-500">
                  Generado: {formatDate(cierreFinancieroDetalle.fecha_generacion)}
                </p>
              </div>
              
              {/* Resumen de Caja */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Flujo de Caja (cobrado/pagado en efectivo/banco)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-sm text-slate-500">Ingresos</p>
                      <p className="text-lg font-bold text-green-600">{formatCurrency(cierreFinancieroDetalle.ingresos_caja)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Egresos (caja)</p>
                      <p className="text-lg font-bold text-red-600">{formatCurrency(cierreFinancieroDetalle.egresos_caja)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Saldo de caja</p>
                      <p className={`text-lg font-bold ${(cierreFinancieroDetalle.ingresos_caja - cierreFinancieroDetalle.egresos_caja) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(cierreFinancieroDetalle.ingresos_caja - cierreFinancieroDetalle.egresos_caja)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Utilidad Real */}
              <Card data-testid="cierre-utilidad-real-card">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Utilidad Real (resta costo de ventas y gastos pagados)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-center mb-4">
                    <div>
                      <p className="text-sm text-slate-500">Costo de ventas</p>
                      <p className="text-lg font-bold text-red-600">{formatCurrency(cierreFinancieroDetalle.costo_ventas)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Gastos pagados</p>
                      <p className="text-lg font-bold text-red-600">{formatCurrency(cierreFinancieroDetalle.gastos_pagados)}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-center border-t pt-4">
                    <div>
                      <p className="text-sm text-slate-500">Utilidad Bruta</p>
                      <p className="text-lg font-bold text-blue-600">{formatCurrency(cierreFinancieroDetalle.utilidad_bruta)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Resultado Neto</p>
                      <p className={`text-lg font-bold ${cierreFinancieroDetalle.resultado_neto >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(cierreFinancieroDetalle.resultado_neto)}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 mt-3">
                    Utilidad Bruta = Ingresos de caja − Costo de ventas. Resultado Neto = Utilidad Bruta − Gastos pagados − Egresos de caja.
                    No incluye servicios clínicos sin costo definido ni ajuste de IVA (ver auditoría P26).
                  </p>
                </CardContent>
              </Card>
              
              {/* Resumen CxC */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Cuentas por Cobrar</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tipo</TableHead>
                        <TableHead className="text-right">Emitido</TableHead>
                        <TableHead className="text-right">Cobrado</TableHead>
                        <TableHead className="text-right">Pendiente</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cierreFinancieroDetalle.cxc_por_tipo.map((t, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{t.tipo_pagador_nombre}</TableCell>
                          <TableCell className="text-right">{formatCurrency(t.emitido)}</TableCell>
                          <TableCell className="text-right text-green-600">{formatCurrency(t.cobrado)}</TableCell>
                          <TableCell className="text-right text-yellow-600">{formatCurrency(t.pendiente)}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="font-bold">
                        <TableCell>TOTAL</TableCell>
                        <TableCell className="text-right">{formatCurrency(cierreFinancieroDetalle.cxc_total_emitido)}</TableCell>
                        <TableCell className="text-right text-green-600">{formatCurrency(cierreFinancieroDetalle.cxc_total_cobrado)}</TableCell>
                        <TableCell className="text-right text-yellow-600">{formatCurrency(cierreFinancieroDetalle.cxc_saldo_pendiente)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
              
              {cierreFinancieroDetalle.observaciones && (
                <div>
                  <p className="text-sm text-slate-500">Observaciones</p>
                  <p>{cierreFinancieroDetalle.observaciones}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button variant="outline" onClick={() => setCierreFinancieroDetalleDialog(false)}>Cerrar</Button>
            {cierreFinancieroDetalle && (
              <>
                <Button 
                  variant="outline"
                  onClick={() => handleRecalcularCierreFinanciero(cierreFinancieroDetalle.id)}
                  disabled={submitting}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Recalcular
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => handlePrintCierreFinanciero(cierreFinancieroDetalle)}
                >
                  <Printer className="w-4 h-4 mr-2" />
                  Imprimir
                </Button>
                {isSuperAdmin && (
                  <Button 
                    variant="destructive"
                    onClick={() => handleDeleteCierreFinanciero(cierreFinancieroDetalle.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Eliminar
                  </Button>
                )}
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Caja;
