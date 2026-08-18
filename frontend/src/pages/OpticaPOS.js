// /app/frontend/src/pages/OpticaPOS.js
// Punto de Venta para Óptica - NovaVision
// Interfaz táctil para venta de armazones, lentes de contacto y lentes oftálmicos

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, formatDate } from '../services/api';
import axios from 'axios';
import { 
  Search, 
  Plus, 
  Minus,
  Trash2,
  ShoppingCart,
  Package,
  User,
  CreditCard,
  Banknote,
  Building2,
  ArrowLeft,
  Check,
  X,
  Printer,
  AlertCircle,
  Receipt,
  Calculator,
  RefreshCw,
  ChevronRight,
  Tag,
  FileText,
  Clock,
  Glasses,
  Eye,
  CircleDot,
  Filter,
  Star
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import { toast } from 'sonner';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Métodos de pago disponibles
const METODOS_PAGO = [
  { value: 'Efectivo', label: 'Efectivo', icon: Banknote, color: 'bg-green-500' },
  { value: 'Tarjeta', label: 'Tarjeta', icon: CreditCard, color: 'bg-blue-500' },
  { value: 'Transferencia', label: 'Transferencia', icon: Building2, color: 'bg-purple-500' },
  { value: 'Cheque', label: 'Cheque', icon: FileText, color: 'bg-orange-500' },
  { value: 'Cuenta por Cobrar', label: 'Crédito (CxC)', icon: Clock, color: 'bg-yellow-500' },
];

// Categorías de productos óptica
const CATEGORIAS_OPTICA = [
  { value: 'armazones', label: 'Armazones', icon: Glasses, color: 'bg-blue-500' },
  { value: 'lentes_contacto', label: 'Lentes de Contacto', icon: CircleDot, color: 'bg-green-500' },
  { value: 'tipos_lente', label: 'Lentes Oftálmicos', icon: Eye, color: 'bg-purple-500' },
];

const OpticaPOS = () => {
  const { user } = useAuth();
  const searchInputRef = useRef(null);
  
  // Estado del carrito
  const [carrito, setCarrito] = useState([]);
  const [paciente, setPaciente] = useState(null);
  
  // Categoría activa
  const [categoriaActiva, setCategoriaActiva] = useState('armazones');
  
  // Productos por categoría
  const [armazones, setArmazones] = useState([]);
  const [lentesContacto, setLentesContacto] = useState([]);
  const [tiposLente, setTiposLente] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  
  // Búsqueda
  const [searchQuery, setSearchQuery] = useState('');
  
  // Filtros de armazones
  const [filtroMarca, setFiltroMarca] = useState('all');
  const [filtroMaterial, setFiltroMaterial] = useState('all');
  const [marcasDisponibles, setMarcasDisponibles] = useState([]);
  
  // Búsqueda de pacientes
  const [pacienteSearch, setPacienteSearch] = useState('');
  const [pacientesResults, setPacientesResults] = useState([]);
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const [pacienteDialogOpen, setPacienteDialogOpen] = useState(false);
  
  // Pago
  const [pagoDialogOpen, setPagoDialogOpen] = useState(false);
  const [metodoPagoActual, setMetodoPagoActual] = useState('Efectivo');
  const [montoPagoActual, setMontoPagoActual] = useState('');
  const [referenciaPagoActual, setReferenciaPagoActual] = useState('');
  const [formasPago, setFormasPago] = useState([]);
  const [observaciones, setObservaciones] = useState('');
  
  // Receta óptica
  const [recetaDialogOpen, setRecetaDialogOpen] = useState(false);
  const [receta, setReceta] = useState({
    od_esfera: '', od_cilindro: '', od_eje: '', od_add: '',
    oi_esfera: '', oi_cilindro: '', oi_eje: '', oi_add: '',
    dp: '', altura: '', observaciones: ''
  });
  
  // Ventas del día
  const [ventasHoy, setVentasHoy] = useState([]);
  const [resumenDia, setResumenDia] = useState({ total: 0, cantidad: 0 });
  const [ventasDialogOpen, setVentasDialogOpen] = useState(false);
  
  // Confirmación de venta exitosa
  const [ventaExitosa, setVentaExitosa] = useState(null);
  const [ventaExitosaDialogOpen, setVentaExitosaDialogOpen] = useState(false);
  
  // UI state
  const [submitting, setSubmitting] = useState(false);

  // ==================== EFECTOS ====================
  
  useEffect(() => {
    fetchProductos();
    fetchVentasHoy();
    fetchMarcas();
  }, []);
  
  useEffect(() => {
    fetchProductos();
  }, [categoriaActiva, searchQuery, filtroMarca, filtroMaterial]);
  
  // Búsqueda de pacientes con debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (pacienteSearch && pacienteSearch.length >= 2) {
        buscarPacientes(pacienteSearch);
      } else {
        setPacientesResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [pacienteSearch]);

  // ==================== API CALLS ====================

  const fetchProductos = async () => {
    setLoadingProductos(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      
      if (categoriaActiva === 'armazones') {
        const params = new URLSearchParams();
        if (searchQuery) params.append('search', searchQuery);
        if (filtroMarca && filtroMarca !== 'all') params.append('brand', filtroMarca);
        if (filtroMaterial && filtroMaterial !== 'all') params.append('material', filtroMaterial);
        params.append('is_active', 'true');
        
        const response = await axios.get(`${API_URL}/optica/frames?${params}`, { headers });
        setArmazones(response.data?.data || response.data || []);
      } else if (categoriaActiva === 'lentes_contacto') {
        const params = new URLSearchParams();
        if (searchQuery) params.append('search', searchQuery);
        params.append('is_active', 'true');
        
        const response = await axios.get(`${API_URL}/optica/contact-lenses?${params}`, { headers });
        setLentesContacto(response.data?.data || response.data || []);
      } else if (categoriaActiva === 'tipos_lente') {
        const params = new URLSearchParams();
        if (searchQuery) params.append('search', searchQuery);
        params.append('is_active', 'true');
        
        const response = await axios.get(`${API_URL}/optica/lens-types?${params}`, { headers });
        setTiposLente(response.data?.data || response.data || []);
      }
    } catch (error) {
      console.error('Error fetching productos:', error);
      toast.error('Error al cargar productos');
    } finally {
      setLoadingProductos(false);
    }
  };

  const fetchMarcas = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/frames`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const frames = response.data?.data || response.data || [];
      const marcas = [...new Set(frames.map(f => f.brand).filter(Boolean))];
      setMarcasDisponibles(marcas);
    } catch (error) {
      console.error('Error fetching marcas:', error);
    }
  };

  const buscarPacientes = async (query) => {
    setSearchingPacientes(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/pacientes/buscar?q=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPacientesResults(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    } finally {
      setSearchingPacientes(false);
    }
  };

  const fetchVentasHoy = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/sales?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const ventas = response.data?.data || response.data || [];
      setVentasHoy(ventas);
      
      // Calcular resumen
      const hoy = new Date().toISOString().split('T')[0];
      const ventasDeHoy = ventas.filter(v => v.created_at?.startsWith(hoy));
      setResumenDia({
        total: ventasDeHoy.reduce((sum, v) => sum + (v.total || 0), 0),
        cantidad: ventasDeHoy.length
      });
    } catch (error) {
      console.error('Error fetching ventas del día:', error);
    }
  };

  // ==================== FUNCIONES DEL CARRITO ====================

  const agregarAlCarrito = (producto, tipo) => {
    setCarrito(prev => {
      const key = `${tipo}-${producto.id}`;
      const existente = prev.find(item => item.key === key);
      
      if (existente) {
        // Verificar stock para armazones y lentes de contacto
        if (tipo !== 'tipos_lente') {
          const stockDisponible = producto.stock || 0;
          if (existente.cantidad >= stockDisponible) {
            toast.error('No hay más stock disponible');
            return prev;
          }
        }
        
        return prev.map(item => 
          item.key === key 
            ? { ...item, cantidad: item.cantidad + 1 }
            : item
        );
      }
      
      // Agregar nuevo item
      const nuevoItem = {
        key,
        tipo,
        producto_id: producto.id,
        codigo: producto.sku || producto.code || producto.id,
        nombre: tipo === 'armazones' 
          ? `${producto.brand} ${producto.model}` 
          : tipo === 'lentes_contacto'
            ? `${producto.brand} ${producto.name}`
            : producto.name,
        precio: producto.sale_price || producto.price || 0,
        cantidad: 1,
        stock: producto.stock,
        producto_original: producto
      };
      
      return [...prev, nuevoItem];
    });
    
    toast.success('Producto agregado');
  };

  const modificarCantidad = (key, delta) => {
    setCarrito(prev => prev.map(item => {
      if (item.key !== key) return item;
      
      const nuevaCantidad = item.cantidad + delta;
      if (nuevaCantidad < 1) return item;
      
      // Verificar stock
      if (item.tipo !== 'tipos_lente' && item.stock !== undefined) {
        if (nuevaCantidad > item.stock) {
          toast.error('Stock insuficiente');
          return item;
        }
      }
      
      return { ...item, cantidad: nuevaCantidad };
    }));
  };

  const eliminarDelCarrito = (key) => {
    setCarrito(prev => prev.filter(item => item.key !== key));
  };

  const limpiarCarrito = () => {
    setCarrito([]);
    setPaciente(null);
    setFormasPago([]);
    setObservaciones('');
    setReceta({
      od_esfera: '', od_cilindro: '', od_eje: '', od_add: '',
      oi_esfera: '', oi_cilindro: '', oi_eje: '', oi_add: '',
      dp: '', altura: '', observaciones: ''
    });
  };

  // ==================== CÁLCULOS ====================

  const calcularSubtotal = () => {
    return carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);
  };

  const calcularTotal = () => {
    return calcularSubtotal();
  };

  const calcularTotalPagado = () => {
    return formasPago.reduce((sum, fp) => sum + fp.monto, 0);
  };

  const calcularPendiente = () => {
    return calcularTotal() - calcularTotalPagado();
  };

  // ==================== FORMAS DE PAGO ====================

  const agregarFormaPago = () => {
    const monto = parseFloat(montoPagoActual) || 0;
    if (monto <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    
    const pendiente = calcularPendiente();
    const montoFinal = Math.min(monto, pendiente);
    
    if (montoFinal <= 0) {
      toast.error('El monto total ya está cubierto');
      return;
    }
    
    setFormasPago(prev => [...prev, {
      metodo: metodoPagoActual,
      monto: montoFinal,
      referencia: referenciaPagoActual || null,
      es_cxc: metodoPagoActual === 'Cuenta por Cobrar'
    }]);
    
    setMontoPagoActual('');
    setReferenciaPagoActual('');
  };

  // Agregar saldo pendiente a CxC (para Óptica, vinculado al paciente)
  const agregarCxCPendiente = () => {
    const pendiente = calcularPendiente();
    if (pendiente <= 0) {
      toast.error('No hay saldo pendiente');
      return;
    }
    
    if (!paciente) {
      toast.error('Debe seleccionar un paciente para crear Cuenta por Cobrar');
      return;
    }
    
    setFormasPago(prev => [...prev, {
      metodo: 'Cuenta por Cobrar',
      monto: pendiente,
      referencia: null,
      es_cxc: true
    }]);
    
    toast.success(`Saldo de ${formatCurrency(pendiente)} agregado a Cuenta por Cobrar`);
  };

  const eliminarFormaPago = (index) => {
    setFormasPago(prev => prev.filter((_, i) => i !== index));
  };

  // ==================== PROCESAR VENTA ====================

  const procesarVenta = async () => {
    if (carrito.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }
    
    const pendiente = calcularPendiente();
    
    // Verificar si hay CxC en las formas de pago
    const tieneCxC = formasPago.some(fp => fp.es_cxc);
    
    // Si hay pendiente y no hay CxC, no permitir
    if (pendiente > 0.01 && !tieneCxC) {
      toast.error(`Falta cubrir ${formatCurrency(pendiente)}. Agregue un pago o envíe a Cuenta por Cobrar.`);
      return;
    }
    
    // Si hay CxC pero no hay paciente seleccionado
    if (tieneCxC && !paciente) {
      toast.error('Debe seleccionar un paciente para ventas con Cuenta por Cobrar');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // Preparar items para la venta
      const items = carrito.map(item => ({
        type: item.tipo === 'armazones' ? 'frame' 
            : item.tipo === 'lentes_contacto' ? 'contact_lens' 
            : 'lens_type',
        product_id: item.producto_id,
        quantity: item.cantidad,
        unit_price: item.precio,
        subtotal: item.precio * item.cantidad
      }));
      
      // Verificar si hay lentes que requieren receta
      const tieneLentes = carrito.some(item => item.tipo === 'tipos_lente');
      
      // Separar pagos de CxC de pagos normales
      const pagosCxC = formasPago.filter(fp => fp.es_cxc);
      const pagosNormales = formasPago.filter(fp => !fp.es_cxc);
      const montoCxC = pagosCxC.reduce((sum, fp) => sum + fp.monto, 0);
      
      const ventaData = {
        patient_id: paciente?.id || null,
        patient_name: paciente 
          ? `${paciente.primer_nombre} ${paciente.primer_apellido}` 
          : 'Consumidor Final',
        items,
        subtotal: calcularSubtotal(),
        discount: 0,
        total: calcularTotal(),
        payments: pagosNormales.map(fp => ({
          method: fp.metodo,
          amount: fp.monto,
          reference: fp.referencia
        })),
        notes: observaciones || null,
        prescription: tieneLentes && Object.values(receta).some(v => v) ? receta : null,
        created_by: user?.id,
        created_by_name: user?.name || user?.username,
        // Indicar si tiene CxC
        tiene_cxc: montoCxC > 0,
        monto_cxc: montoCxC
      };
      
      const response = await axios.post(`${API_URL}/optica/sales/v2`, ventaData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Si tiene CxC, crear la cuenta por cobrar
      if (montoCxC > 0 && paciente) {
        try {
          const cxcData = {
            origen: 'optica',
            paciente_id: paciente.id,
            paciente_nombre: `${paciente.primer_nombre} ${paciente.primer_apellido}`,
            monto_total: montoCxC,
            concepto: `Venta Óptica #${response.data?.sale_number || 'N/A'} - ${items.map(i => i.type).join(', ')}`,
            venta_id: response.data?.id || null,
            notas: observaciones || null
          };
          
          await axios.post(`${API_URL}/cuentas-cobrar/optica`, cxcData, {
            headers: { 
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          toast.success(`Cuenta por Cobrar de ${formatCurrency(montoCxC)} creada para ${paciente.primer_nombre}`);
        } catch (cxcError) {
          console.error('Error creando CxC:', cxcError);
          toast.warning('Venta registrada, pero hubo un error creando la Cuenta por Cobrar');
        }
      }
      
      setVentaExitosa(response.data);
      setVentaExitosaDialogOpen(true);
      setPagoDialogOpen(false);
      
      // Limpiar y recargar
      limpiarCarrito();
      fetchProductos();
      fetchVentasHoy();
      
      toast.success('¡Venta registrada exitosamente!');
      
    } catch (error) {
      console.error('Error procesando venta:', error);
      toast.error(error.response?.data?.detail || 'Error al procesar la venta');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== SELECCIONAR PACIENTE ====================

  const seleccionarPaciente = (p) => {
    setPaciente(p);
    setPacienteDialogOpen(false);
    setPacienteSearch('');
    setPacientesResults([]);
    toast.success(`Paciente: ${p.primer_nombre} ${p.primer_apellido}`);
  };

  // ==================== RENDER PRODUCTOS ====================

  const renderProductos = () => {
    let productos = [];
    
    if (categoriaActiva === 'armazones') {
      productos = armazones;
    } else if (categoriaActiva === 'lentes_contacto') {
      productos = lentesContacto;
    } else {
      productos = tiposLente;
    }
    
    if (loadingProductos) {
      return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-lg" />
          ))}
        </div>
      );
    }
    
    if (productos.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-slate-500">
          <Package className="h-12 w-12 mb-3 opacity-50" />
          <p>No hay productos disponibles</p>
          <p className="text-sm">Intenta ajustar los filtros</p>
        </div>
      );
    }
    
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {productos.map((producto) => (
          <Card 
            key={producto.id}
            className="cursor-pointer hover:border-teal-500 transition-all hover:shadow-lg group"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
            onClick={() => agregarAlCarrito(producto, categoriaActiva)}
          >
            <CardContent className="p-3">
              {/* Imagen o ícono */}
              <div 
                className="h-20 rounded-md mb-2 flex items-center justify-center"
                style={{ background: 'var(--bg-hover)' }}
              >
                {categoriaActiva === 'armazones' ? (
                  <Glasses className="h-10 w-10 text-teal-500" />
                ) : categoriaActiva === 'lentes_contacto' ? (
                  <CircleDot className="h-10 w-10 text-green-500" />
                ) : (
                  <Eye className="h-10 w-10 text-purple-500" />
                )}
              </div>
              
              {/* Info del producto */}
              <div className="space-y-1">
                <p className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                  {categoriaActiva === 'armazones' 
                    ? `${producto.brand} ${producto.model}`
                    : categoriaActiva === 'lentes_contacto'
                      ? `${producto.brand} ${producto.name}`
                      : producto.name
                  }
                </p>
                
                {categoriaActiva === 'armazones' && producto.color && (
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    Color: {producto.color}
                  </p>
                )}
                
                <div className="flex items-center justify-between">
                  <p className="font-bold text-teal-500">
                    {formatCurrency(producto.sale_price || producto.price || 0)}
                  </p>
                  
                  {categoriaActiva !== 'tipos_lente' && (
                    <Badge 
                      variant={producto.stock > 5 ? 'default' : producto.stock > 0 ? 'warning' : 'destructive'}
                      className="text-xs"
                    >
                      {producto.stock || 0}
                    </Badge>
                  )}
                </div>
              </div>
              
              {/* Botón agregar (visible en hover) */}
              <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button 
                  size="sm" 
                  className="w-full bg-teal-600 hover:bg-teal-700"
                >
                  <Plus className="h-4 w-4 mr-1" /> Agregar
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  };

  // ==================== RENDER PRINCIPAL ====================

  return (
    <Layout>
      <div className="flex h-[calc(100vh-80px)]" data-testid="optica-pos-page">
        {/* Panel izquierdo - Productos */}
        <div className="flex-1 flex flex-col overflow-hidden p-4">
          {/* Header */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-teal-500/20">
                  <ShoppingCart className="h-6 w-6 text-teal-500" />
                </div>
                <div>
                  <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    Punto de Venta - Óptica
                  </h1>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    Ventas de {resumenDia.cantidad} | Total: {formatCurrency(resumenDia.total)}
                  </p>
                </div>
              </div>
              
              <Button
                variant="outline"
                onClick={() => { fetchVentasHoy(); setVentasDialogOpen(true); }}
              >
                <Receipt className="h-4 w-4 mr-2" />
                Ver Ventas
              </Button>
            </div>
            
            {/* Categorías */}
            <div className="flex gap-2 mb-4">
              {CATEGORIAS_OPTICA.map(cat => {
                const Icon = cat.icon;
                return (
                  <Button
                    key={cat.value}
                    variant={categoriaActiva === cat.value ? 'default' : 'outline'}
                    className={categoriaActiva === cat.value ? 'bg-teal-600 hover:bg-teal-700' : ''}
                    onClick={() => {
                      setCategoriaActiva(cat.value);
                      setSearchQuery('');
                    }}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {cat.label}
                  </Button>
                );
              })}
            </div>
            
            {/* Búsqueda y filtros */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  ref={searchInputRef}
                  placeholder="Buscar productos..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="pos-search-input"
                />
              </div>
              
              {categoriaActiva === 'armazones' && (
                <>
                  <Select value={filtroMarca} onValueChange={setFiltroMarca}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Marca" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas las marcas</SelectItem>
                      {marcasDisponibles.map(m => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </>
              )}
              
              <Button variant="outline" onClick={fetchProductos}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* Grid de productos */}
          <div className="flex-1 overflow-y-auto">
            {renderProductos()}
          </div>
        </div>
        
        {/* Panel derecho - Carrito */}
        <div 
          className="w-96 flex flex-col border-l"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
        >
          {/* Header carrito */}
          <div className="p-4 border-b" style={{ borderColor: 'var(--border-color)' }}>
            <div className="flex items-center justify-between">
              <h2 className="font-bold" style={{ color: 'var(--text-primary)' }}>
                Carrito ({carrito.length})
              </h2>
              {carrito.length > 0 && (
                <Button variant="ghost" size="sm" onClick={limpiarCarrito}>
                  <Trash2 className="h-4 w-4 mr-1" /> Limpiar
                </Button>
              )}
            </div>
            
            {/* Paciente */}
            <div className="mt-3">
              {paciente ? (
                <div 
                  className="flex items-center justify-between p-2 rounded-lg"
                  style={{ background: 'var(--bg-hover)' }}
                >
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-teal-500" />
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {paciente.primer_nombre} {paciente.primer_apellido}
                    </span>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setPaciente(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setPacienteDialogOpen(true)}
                >
                  <User className="h-4 w-4 mr-2" />
                  Seleccionar Paciente
                </Button>
              )}
            </div>
          </div>
          
          {/* Items del carrito */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {carrito.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <ShoppingCart className="h-12 w-12 mb-3 opacity-50" />
                <p>Carrito vacío</p>
                <p className="text-sm">Selecciona productos para agregar</p>
              </div>
            ) : (
              carrito.map((item) => (
                <div 
                  key={item.key}
                  className="p-3 rounded-lg"
                  style={{ background: 'var(--bg-hover)' }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                        {item.nombre}
                      </p>
                      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {formatCurrency(item.precio)} c/u
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => eliminarDelCarrito(item.key)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => modificarCantidad(item.key, -1)}
                        disabled={item.cantidad <= 1}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                      <span className="w-8 text-center font-medium" style={{ color: 'var(--text-primary)' }}>
                        {item.cantidad}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => modificarCantidad(item.key, 1)}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="font-bold text-teal-500">
                      {formatCurrency(item.precio * item.cantidad)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {/* Totales y botón de pago */}
          <div className="p-4 border-t" style={{ borderColor: 'var(--border-color)' }}>
            {/* Botón de receta si hay lentes */}
            {carrito.some(item => item.tipo === 'tipos_lente') && (
              <Button
                variant="outline"
                className="w-full mb-3"
                onClick={() => setRecetaDialogOpen(true)}
              >
                <FileText className="h-4 w-4 mr-2" />
                {Object.values(receta).some(v => v) ? 'Editar Receta' : 'Agregar Receta'}
              </Button>
            )}
            
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>Subtotal:</span>
                <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(calcularSubtotal())}</span>
              </div>
              <div className="flex justify-between text-lg font-bold">
                <span style={{ color: 'var(--text-primary)' }}>Total:</span>
                <span className="text-teal-500">{formatCurrency(calcularTotal())}</span>
              </div>
            </div>
            
            <Button
              className="w-full h-14 text-lg bg-teal-600 hover:bg-teal-700"
              disabled={carrito.length === 0}
              onClick={() => setPagoDialogOpen(true)}
              data-testid="pos-pagar-btn"
            >
              <CreditCard className="h-5 w-5 mr-2" />
              Cobrar {formatCurrency(calcularTotal())}
            </Button>
          </div>
        </div>
      </div>
      
      {/* ==================== DIALOGS ==================== */}
      
      {/* Dialog de búsqueda de pacientes */}
      <Dialog open={pacienteDialogOpen} onOpenChange={setPacienteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Seleccionar Paciente</DialogTitle>
            <DialogDescription>
              Busca un paciente por nombre, DPI o teléfono
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Buscar paciente..."
                value={pacienteSearch}
                onChange={(e) => setPacienteSearch(e.target.value)}
                className="pl-10"
                autoFocus
              />
            </div>
            
            <div className="max-h-60 overflow-y-auto space-y-2">
              {searchingPacientes ? (
                <div className="text-center py-4 text-slate-500">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Buscando...
                </div>
              ) : pacientesResults.length === 0 ? (
                <div className="text-center py-4 text-slate-500">
                  {pacienteSearch.length >= 2 ? 'No se encontraron pacientes' : 'Escribe al menos 2 caracteres'}
                </div>
              ) : (
                pacientesResults.map(p => (
                  <div
                    key={p.id}
                    className="p-3 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    onClick={() => seleccionarPaciente(p)}
                  >
                    <p className="font-medium">
                      {p.primer_nombre} {p.segundo_nombre} {p.primer_apellido} {p.segundo_apellido}
                    </p>
                    <p className="text-sm text-slate-500">
                      {p.dpi || 'Sin DPI'} • {p.telefono || 'Sin teléfono'}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setPacienteDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => { setPaciente(null); setPacienteDialogOpen(false); }}>
              Consumidor Final
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Dialog de pago */}
      <Dialog open={pagoDialogOpen} onOpenChange={setPagoDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Procesar Pago</DialogTitle>
            <DialogDescription>
              Total a cobrar: <span className="font-bold text-teal-500">{formatCurrency(calcularTotal())}</span>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Métodos de pago */}
            <div className="grid grid-cols-4 gap-2">
              {METODOS_PAGO.map(mp => {
                const Icon = mp.icon;
                return (
                  <Button
                    key={mp.value}
                    variant={metodoPagoActual === mp.value ? 'default' : 'outline'}
                    className={metodoPagoActual === mp.value ? 'bg-teal-600' : ''}
                    onClick={() => setMetodoPagoActual(mp.value)}
                  >
                    <Icon className="h-4 w-4" />
                  </Button>
                );
              })}
            </div>
            
            {/* Monto */}
            <div className="flex gap-2">
              <div className="flex-1">
                <Label>Monto</Label>
                <Input
                  type="number"
                  placeholder="0.00"
                  value={montoPagoActual}
                  onChange={(e) => setMontoPagoActual(e.target.value)}
                />
              </div>
              {metodoPagoActual !== 'Efectivo' && (
                <div className="flex-1">
                  <Label>Referencia</Label>
                  <Input
                    placeholder="No. autorización"
                    value={referenciaPagoActual}
                    onChange={(e) => setReferenciaPagoActual(e.target.value)}
                  />
                </div>
              )}
              <div className="flex items-end">
                <Button onClick={agregarFormaPago}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Botones rápidos */}
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setMontoPagoActual(calcularPendiente().toFixed(2))}
              >
                Monto exacto
              </Button>
              {[100, 200, 500].map(m => (
                <Button 
                  key={m}
                  variant="outline" 
                  size="sm"
                  onClick={() => setMontoPagoActual(m.toString())}
                >
                  Q{m}
                </Button>
              ))}
            </div>
            
            {/* Formas de pago agregadas */}
            {formasPago.length > 0 && (
              <div className="space-y-2">
                <Label>Pagos registrados:</Label>
                {formasPago.map((fp, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-slate-100 dark:bg-slate-800 rounded">
                    <span>{fp.metodo}: {formatCurrency(fp.monto)}</span>
                    <Button variant="ghost" size="sm" onClick={() => eliminarFormaPago(i)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            
            {/* Resumen */}
            <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-800 space-y-2">
              <div className="flex justify-between">
                <span>Total:</span>
                <span className="font-bold">{formatCurrency(calcularTotal())}</span>
              </div>
              <div className="flex justify-between">
                <span>Pagado:</span>
                <span className="text-green-500">{formatCurrency(calcularTotalPagado())}</span>
              </div>
              <div className="flex justify-between font-bold text-lg">
                <span>Pendiente:</span>
                <span className={calcularPendiente() > 0 ? 'text-red-500' : 'text-green-500'}>
                  {formatCurrency(calcularPendiente())}
                </span>
              </div>
            </div>
            
            {/* Botón para agregar saldo pendiente a CxC */}
            {calcularPendiente() > 0.01 && (
              <Button
                variant="outline"
                className="w-full border-yellow-500 text-yellow-700 hover:bg-yellow-50"
                onClick={agregarCxCPendiente}
              >
                <Clock className="h-4 w-4 mr-2" />
                Agregar saldo pendiente a Cuenta por Cobrar - {formatCurrency(calcularPendiente())}
              </Button>
            )}
            
            {/* Aviso si hay CxC pero no paciente */}
            {formasPago.some(fp => fp.es_cxc) && !paciente && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-2 text-yellow-800">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">Debe seleccionar un paciente para ventas con Cuenta por Cobrar</span>
              </div>
            )}
            
            {/* Observaciones */}
            <div>
              <Label>Observaciones</Label>
              <Textarea
                placeholder="Notas adicionales..."
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setPagoDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              className="bg-teal-600 hover:bg-teal-700"
              onClick={procesarVenta}
              disabled={submitting || (calcularPendiente() > 0.01 && !formasPago.some(fp => fp.es_cxc))}
            >
              {submitting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Confirmar Venta
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Dialog de receta */}
      <Dialog open={recetaDialogOpen} onOpenChange={setRecetaDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Receta Óptica</DialogTitle>
            <DialogDescription>
              Ingresa la graduación para los lentes
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* OD - Ojo Derecho */}
            <div>
              <Label className="font-bold">Ojo Derecho (OD)</Label>
              <div className="grid grid-cols-4 gap-2 mt-2">
                <div>
                  <Label className="text-xs">Esfera</Label>
                  <Input
                    placeholder="-0.00"
                    value={receta.od_esfera}
                    onChange={(e) => setReceta({...receta, od_esfera: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">Cilindro</Label>
                  <Input
                    placeholder="-0.00"
                    value={receta.od_cilindro}
                    onChange={(e) => setReceta({...receta, od_cilindro: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">Eje</Label>
                  <Input
                    placeholder="0°"
                    value={receta.od_eje}
                    onChange={(e) => setReceta({...receta, od_eje: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">ADD</Label>
                  <Input
                    placeholder="+0.00"
                    value={receta.od_add}
                    onChange={(e) => setReceta({...receta, od_add: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            {/* OI - Ojo Izquierdo */}
            <div>
              <Label className="font-bold">Ojo Izquierdo (OI)</Label>
              <div className="grid grid-cols-4 gap-2 mt-2">
                <div>
                  <Label className="text-xs">Esfera</Label>
                  <Input
                    placeholder="-0.00"
                    value={receta.oi_esfera}
                    onChange={(e) => setReceta({...receta, oi_esfera: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">Cilindro</Label>
                  <Input
                    placeholder="-0.00"
                    value={receta.oi_cilindro}
                    onChange={(e) => setReceta({...receta, oi_cilindro: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">Eje</Label>
                  <Input
                    placeholder="0°"
                    value={receta.oi_eje}
                    onChange={(e) => setReceta({...receta, oi_eje: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">ADD</Label>
                  <Input
                    placeholder="+0.00"
                    value={receta.oi_add}
                    onChange={(e) => setReceta({...receta, oi_add: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            {/* DP y Altura */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Distancia Pupilar (DP)</Label>
                <Input
                  placeholder="62mm"
                  value={receta.dp}
                  onChange={(e) => setReceta({...receta, dp: e.target.value})}
                />
              </div>
              <div>
                <Label>Altura</Label>
                <Input
                  placeholder="mm"
                  value={receta.altura}
                  onChange={(e) => setReceta({...receta, altura: e.target.value})}
                />
              </div>
            </div>
            
            <div>
              <Label>Observaciones</Label>
              <Textarea
                placeholder="Notas sobre la receta..."
                value={receta.observaciones}
                onChange={(e) => setReceta({...receta, observaciones: e.target.value})}
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setRecetaDialogOpen(false)}>
              Cancelar
            </Button>
            <Button className="bg-teal-600" onClick={() => setRecetaDialogOpen(false)}>
              Guardar Receta
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Dialog de venta exitosa */}
      <Dialog open={ventaExitosaDialogOpen} onOpenChange={setVentaExitosaDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <div className="text-center py-6">
            <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="h-8 w-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              ¡Venta Exitosa!
            </h2>
            <p className="text-slate-500 mb-4">
              Orden: {ventaExitosa?.order_number || ventaExitosa?.id}
            </p>
            <p className="text-3xl font-bold text-teal-500 mb-6">
              {formatCurrency(ventaExitosa?.total || 0)}
            </p>
            
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={() => setVentaExitosaDialogOpen(false)}>
                Cerrar
              </Button>
              <Button className="bg-teal-600 hover:bg-teal-700">
                <Printer className="h-4 w-4 mr-2" />
                Imprimir
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Dialog de ventas del día */}
      <Dialog open={ventasDialogOpen} onOpenChange={setVentasDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Ventas del Día</DialogTitle>
            <DialogDescription>
              Total: {formatCurrency(resumenDia.total)} ({resumenDia.cantidad} ventas)
            </DialogDescription>
          </DialogHeader>
          
          <div className="max-h-96 overflow-y-auto space-y-2">
            {ventasHoy.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No hay ventas registradas hoy
              </div>
            ) : (
              ventasHoy.map(venta => (
                <div 
                  key={venta.id}
                  className="p-3 rounded-lg border"
                  style={{ background: 'var(--bg-hover)', borderColor: 'var(--border-color)' }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {venta.order_number || venta.id}
                      </p>
                      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        {venta.patient_name || 'Consumidor Final'}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-teal-500">
                        {formatCurrency(venta.total)}
                      </p>
                      <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                        {formatDate(venta.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setVentasDialogOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default OpticaPOS;
