// /app/frontend/src/pages/PuntoVenta.js
// Módulo de Punto de Venta (POS) táctil para NovaVision
// Optimizado para uso en tablets y pantallas táctiles

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { ventasApi, inventarioApi, formatCurrency, formatDate, formatTime } from '../services/api';
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
  DollarSign,
  Zap,
  Star,
  ChevronDown,
  ChevronUp
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
import { toast, Toaster } from 'sonner';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Métodos de pago disponibles
const METODOS_PAGO = [
  { value: 'Efectivo', label: 'Efectivo', icon: Banknote, color: 'bg-green-500' },
  { value: 'Tarjeta', label: 'Tarjeta', icon: CreditCard, color: 'bg-blue-500' },
  { value: 'Transferencia', label: 'Transferencia', icon: Building2, color: 'bg-purple-500' },
  { value: 'Cheque', label: 'Cheque', icon: FileText, color: 'bg-orange-500' },
  { value: 'Cuenta por Cobrar', label: 'Crédito (CxC)', icon: Clock, color: 'bg-yellow-500' },
];

const PuntoVenta = () => {
  const { user } = useAuth();
  const searchInputRef = useRef(null);
  
  // Estado de la bodega POS
  const [bodegaPOS, setBodegaPOS] = useState(null);
  const [loadingBodega, setLoadingBodega] = useState(true);
  
  // Estado del carrito
  const [carrito, setCarrito] = useState([]);
  const [paciente, setPaciente] = useState(null);
  
  // Búsqueda de productos
  const [searchQuery, setSearchQuery] = useState('');
  const [productos, setProductos] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  const [categorias, setCategorias] = useState([]);
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState('');
  
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
  
  // Para CxC
  const [pagadores, setPagadores] = useState([]);
  const [tipoPagadorId, setTipoPagadorId] = useState('');
  
  // Ventas del día
  const [ventasHoy, setVentasHoy] = useState([]);
  const [resumenDia, setResumenDia] = useState(null);
  const [ventasDialogOpen, setVentasDialogOpen] = useState(false);
  const [ventaDetalle, setVentaDetalle] = useState(null);
  const [ventaDetalleDialogOpen, setVentaDetalleDialogOpen] = useState(false);
  
  // Confirmación de venta exitosa
  const [ventaExitosa, setVentaExitosa] = useState(null);
  const [ventaExitosaDialogOpen, setVentaExitosaDialogOpen] = useState(false);
  
  // Productos Rápidos (más vendidos)
  const [productosRapidos, setProductosRapidos] = useState([]);
  const [loadingRapidos, setLoadingRapidos] = useState(false);
  const [mostrarRapidos, setMostrarRapidos] = useState(true);
  
  // Estado de la caja
  const [estadoCaja, setEstadoCaja] = useState(null);
  const [loadingCaja, setLoadingCaja] = useState(true);
  
  // UI state
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('venta');

  // ==================== EFECTOS ====================
  
  useEffect(() => {
    fetchBodegaPOS();
    fetchCategorias();
    fetchPagadores();
    fetchEstadoCaja();
  }, []);
  
  // Cargar productos rápidos cuando se obtiene la bodega
  useEffect(() => {
    if (bodegaPOS) {
      fetchProductos();
      fetchProductosRapidos();
    }
  }, [bodegaPOS, categoriaSeleccionada]);
  
  // Búsqueda de productos con debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (bodegaPOS) {
        fetchProductos();
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
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

  const fetchBodegaPOS = async () => {
    setLoadingBodega(true);
    try {
      const response = await ventasApi.getBodegaPOS();
      setBodegaPOS(response.data);
    } catch (error) {
      console.error('Error fetching bodega POS:', error);
      toast.error('Error al obtener bodega de punto de venta');
    } finally {
      setLoadingBodega(false);
    }
  };

  const fetchCategorias = async () => {
    try {
      const response = await inventarioApi.getCategorias({ activo: true });
      setCategorias(response.data?.data || []);
    } catch (error) {
      console.error('Error fetching categorías:', error);
    }
  };

  const fetchPagadores = async () => {
    try {
      const token = localStorage.getItem('token');
      // Usar los responsables del sistema de CxC
      const response = await axios.get(`${API_URL}/cuentas-cobrar/responsables`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPagadores(response.data?.data || []);
    } catch (error) {
      console.error('Error fetching pagadores/responsables:', error);
      setPagadores([]);
    }
  };

  const fetchEstadoCaja = async () => {
    setLoadingCaja(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/caja/estado`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // El backend devuelve 'caja_abierta', mapeamos a 'abierta' para consistencia
      setEstadoCaja({
        ...response.data,
        abierta: response.data.caja_abierta
      });
    } catch (error) {
      console.error('Error fetching estado caja:', error);
      setEstadoCaja({ abierta: false });
    } finally {
      setLoadingCaja(false);
    }
  };

  const fetchProductos = async () => {
    if (!bodegaPOS) return;
    
    setLoadingProductos(true);
    try {
      const params = {
        bodega_id: bodegaPOS.bodega_id,
        limit: 50
      };
      if (searchQuery) params.search = searchQuery;
      if (categoriaSeleccionada) params.categoria_id = categoriaSeleccionada;
      
      const response = await ventasApi.buscarProductos(params);
      setProductos(response.data || []);
    } catch (error) {
      console.error('Error fetching productos:', error);
    } finally {
      setLoadingProductos(false);
    }
  };

  const buscarPacientes = async (query) => {
    setSearchingPacientes(true);
    try {
      const response = await axios.get(`${API_URL}/pacientes/buscar?q=${encodeURIComponent(query)}`);
      setPacientesResults(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    } finally {
      setSearchingPacientes(false);
    }
  };

  const fetchVentasHoy = async () => {
    try {
      const [ventasRes, resumenRes] = await Promise.all([
        ventasApi.getVentasHoy(),
        ventasApi.getResumenDia()
      ]);
      setVentasHoy(ventasRes.data?.data || []);
      setResumenDia(resumenRes.data);
    } catch (error) {
      console.error('Error fetching ventas del día:', error);
    }
  };

  const fetchProductosRapidos = async () => {
    if (!bodegaPOS) return;
    
    setLoadingRapidos(true);
    try {
      const response = await ventasApi.getProductosRapidos({
        bodega_id: bodegaPOS.bodega_id,
        limit: 8
      });
      setProductosRapidos(response.data || []);
    } catch (error) {
      console.error('Error fetching productos rápidos:', error);
    } finally {
      setLoadingRapidos(false);
    }
  };

  // ==================== FUNCIONES DEL CARRITO ====================

  const agregarAlCarrito = (producto) => {
    setCarrito(prev => {
      const existente = prev.find(item => item.producto_id === producto.id);
      
      if (existente) {
        // Verificar stock disponible
        if (producto.existencia >= 0 && existente.cantidad >= producto.existencia) {
          toast.error(`Stock máximo: ${producto.existencia} unidades`);
          return prev;
        }
        
        return prev.map(item => 
          item.producto_id === producto.id 
            ? { ...item, cantidad: item.cantidad + 1, subtotal: (item.cantidad + 1) * item.precio_unitario }
            : item
        );
      } else {
        // Verificar stock disponible para productos con inventario
        if (producto.existencia === 0 && producto.existencia !== -1) {
          toast.error('Producto sin stock disponible');
          return prev;
        }
        
        return [...prev, {
          producto_id: producto.id,
          codigo: producto.codigo,
          nombre: producto.nombre,
          cantidad: 1,
          precio_unitario: producto.precio_venta,
          descuento: 0,
          subtotal: producto.precio_venta,
          afecto_iva: producto.afecto_iva,
          existencia: producto.existencia,
          controla_lotes: producto.controla_lotes
        }];
      }
    });
    
    // Focus en búsqueda
    if (searchInputRef.current) {
      searchInputRef.current.focus();
    }
  };

  const actualizarCantidad = (productoId, nuevaCantidad) => {
    if (nuevaCantidad < 1) {
      eliminarDelCarrito(productoId);
      return;
    }
    
    setCarrito(prev => {
      const item = prev.find(i => i.producto_id === productoId);
      if (item && item.existencia >= 0 && nuevaCantidad > item.existencia) {
        toast.error(`Stock máximo: ${item.existencia} unidades`);
        return prev;
      }
      
      return prev.map(item => 
        item.producto_id === productoId 
          ? { ...item, cantidad: nuevaCantidad, subtotal: nuevaCantidad * item.precio_unitario - item.descuento }
          : item
      );
    });
  };

  const eliminarDelCarrito = (productoId) => {
    setCarrito(prev => prev.filter(item => item.producto_id !== productoId));
  };

  const limpiarCarrito = () => {
    setCarrito([]);
    setPaciente(null);
    setObservaciones('');
    setFormasPago([]);
    setMetodoPagoActual('Efectivo');
    setMontoPagoActual('');
    setReferenciaPagoActual('');
    setTipoPagadorId('');
  };

  // ==================== CÁLCULOS ====================

  const calcularTotales = () => {
    const subtotal = carrito.reduce((sum, item) => sum + item.subtotal, 0);
    const descuento = carrito.reduce((sum, item) => sum + item.descuento, 0);
    const baseIva = carrito.filter(i => i.afecto_iva).reduce((sum, i) => sum + i.subtotal, 0);
    const iva = baseIva * 0.12;
    const total = subtotal + iva;
    const cantidadItems = carrito.reduce((sum, item) => sum + item.cantidad, 0);
    
    return { subtotal, descuento, iva, total, cantidadItems };
  };

  const { subtotal, descuento, iva, total, cantidadItems } = calcularTotales();

  // ==================== FUNCIONES DE PAGO ====================

  const abrirDialogoPago = () => {
    if (carrito.length === 0) {
      toast.error('Agregue productos al carrito');
      return;
    }
    
    // Resetear estado de pago
    setFormasPago([]);
    setMetodoPagoActual('Efectivo');
    setMontoPagoActual(total.toFixed(2));
    setReferenciaPagoActual('');
    setTipoPagadorId('');
    setPagoDialogOpen(true);
  };

  // Calcula el total ya pagado con las formas de pago agregadas
  const totalPagado = formasPago.reduce((acc, fp) => acc + fp.monto, 0);
  const pendientePorPagar = Math.max(0, total - totalPagado);
  
  // Calcula el cambio (solo si hay efectivo y se pagó de más)
  const cambioTotal = formasPago.reduce((acc, fp) => {
    if (fp.metodo === 'Efectivo' && fp.efectivo_recibido) {
      return acc + Math.max(0, fp.efectivo_recibido - fp.monto);
    }
    return acc;
  }, 0);

  const agregarFormaPago = () => {
    const monto = parseFloat(montoPagoActual) || 0;
    
    if (monto <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    
    if (metodoPagoActual === 'Cuenta por Cobrar' && !tipoPagadorId) {
      toast.error('Seleccione el tipo de pagador para Crédito');
      return;
    }
    
    const nuevaFormaPago = {
      id: Date.now(),
      metodo: metodoPagoActual,
      monto: monto,
      referencia: referenciaPagoActual || null,
      tipo_pagador_id: metodoPagoActual === 'Cuenta por Cobrar' ? tipoPagadorId : null,
      tipo_pagador_nombre: metodoPagoActual === 'Cuenta por Cobrar' ? 
        pagadores.find(p => p.id === tipoPagadorId)?.nombre : null,
      // Para efectivo, guardamos cuánto recibió el cliente
      efectivo_recibido: metodoPagoActual === 'Efectivo' ? monto : null
    };
    
    setFormasPago([...formasPago, nuevaFormaPago]);
    
    // Resetear para siguiente forma de pago
    const nuevoMontoPendiente = Math.max(0, pendientePorPagar - monto);
    setMontoPagoActual(nuevoMontoPendiente > 0 ? nuevoMontoPendiente.toFixed(2) : '');
    setReferenciaPagoActual('');
    setTipoPagadorId('');
    
    toast.success(`${metodoPagoActual} agregado: ${formatCurrency(monto)}`);
  };

  const eliminarFormaPago = (id) => {
    setFormasPago(formasPago.filter(fp => fp.id !== id));
  };

  const seleccionarMetodoPago = (metodo) => {
    setMetodoPagoActual(metodo);
    // Pre-llenar con el monto pendiente
    if (pendientePorPagar > 0) {
      setMontoPagoActual(pendientePorPagar.toFixed(2));
    }
  };

  const confirmarVenta = async () => {
    // Validaciones
    if (carrito.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }
    
    if (formasPago.length === 0) {
      toast.error('Agregue al menos una forma de pago');
      return;
    }
    
    const totalFormasPago = formasPago.reduce((acc, fp) => acc + fp.monto, 0);
    if (totalFormasPago < total) {
      toast.error(`Faltan ${formatCurrency(total - totalFormasPago)} por cubrir`);
      return;
    }
    
    setSubmitting(true);
    
    try {
      // Preparar datos - calcular efectivo total recibido y cambio
      const efectivoTotalRecibido = formasPago
        .filter(fp => fp.metodo === 'Efectivo')
        .reduce((acc, fp) => acc + (fp.efectivo_recibido || fp.monto), 0);
      
      const formasPagoData = formasPago.map(fp => ({
        metodo: fp.metodo,
        monto: fp.monto,
        referencia: fp.referencia || null,
        tipo_pagador_id: fp.tipo_pagador_id || null,
        tipo_pagador_nombre: fp.tipo_pagador_nombre || null
      }));
      
      const ventaData = {
        bodega_id: bodegaPOS.bodega_id,
        paciente_id: paciente?.id || null,
        paciente_nombre: paciente?.nombre || paciente?.nombre_completo || 
          (paciente ? `${paciente.first_name} ${paciente.last_name}` : null),
        items: carrito.map(item => ({
          producto_id: item.producto_id,
          codigo: item.codigo,
          nombre: item.nombre,
          cantidad: item.cantidad,
          precio_unitario: item.precio_unitario,
          descuento: item.descuento,
          subtotal: item.subtotal,
          afecto_iva: item.afecto_iva
        })),
        formas_pago: formasPagoData,
        efectivo_recibido: efectivoTotalRecibido > 0 ? efectivoTotalRecibido : null,
        observaciones: observaciones || null
      };
      
      const response = await ventasApi.crear(ventaData);
      
      // Éxito
      setVentaExitosa(response.data);
      setVentaExitosaDialogOpen(true);
      setPagoDialogOpen(false);
      
      // Limpiar carrito
      limpiarCarrito();
      
      toast.success('Venta registrada exitosamente');
      
      // Actualizar productos para reflejar nuevo stock (en background, sin bloquear)
      try {
        await Promise.all([fetchProductos(), fetchProductosRapidos()]);
      } catch (fetchError) {
        console.warn('Error actualizando lista de productos:', fetchError);
        // No mostrar error al usuario, la venta ya se completó
      }
      
    } catch (error) {
      console.error('Error al crear venta:', error);
      toast.error(error.response?.data?.detail || 'Error al registrar la venta');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== IMPRESIÓN DE TICKETS TÉRMICOS ====================
  
  const imprimirTicket = async (ventaId) => {
    try {
      const response = await ventasApi.getTicket(ventaId);
      const ticket = response.data;
      
      // Generar contenido HTML optimizado para impresoras térmicas (58mm/80mm)
      const ticketHTML = generarTicketHTML(ticket);
      
      const printWindow = window.open('', '_blank', 'width=350,height=600');
      printWindow.document.write(ticketHTML);
      printWindow.document.close();
      
      // Esperar a que cargue y luego imprimir
      printWindow.onload = () => {
        printWindow.focus();
        printWindow.print();
      };
    } catch (error) {
      console.error('Error al generar ticket:', error);
      toast.error('Error al generar ticket');
    }
  };

  const generarTicketHTML = (ticket) => {
    // Formatear formas de pago
    const formasPagoHTML = ticket.pago.formas.map(fp => `
      <div class="pago-line">
        <span>${fp.metodo}:</span>
        <span>Q${fp.monto.toFixed(2)}</span>
      </div>
    `).join('');

    // Calcular líneas de productos con truncado para papel térmico
    const itemsHTML = ticket.items.map(item => {
      const nombreCorto = item.nombre.length > 28 ? item.nombre.substring(0, 25) + '...' : item.nombre;
      return `
        <div class="item">
          <div class="item-name">${nombreCorto}</div>
          <div class="item-detail">
            <span>${item.cantidad} x Q${item.precio_unitario.toFixed(2)}</span>
            <span>Q${item.subtotal.toFixed(2)}</span>
          </div>
        </div>
      `;
    }).join('');

    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="UTF-8">
          <title>Ticket ${ticket.venta.numero}</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body { 
              font-family: 'Courier New', 'Lucida Console', Monaco, monospace;
              font-size: 11px;
              line-height: 1.3;
              width: 280px;
              padding: 8px;
              background: #fff;
              color: #000;
            }
            
            .ticket {
              width: 100%;
            }
            
            .header {
              text-align: center;
              padding-bottom: 8px;
              border-bottom: 1px dashed #000;
              margin-bottom: 8px;
            }
            
            .logo-text {
              font-size: 16px;
              font-weight: bold;
              letter-spacing: 1px;
            }
            
            .empresa-info {
              font-size: 10px;
              margin-top: 4px;
            }
            
            .divider {
              border-bottom: 1px dashed #000;
              margin: 6px 0;
            }
            
            .info-section {
              margin-bottom: 8px;
            }
            
            .info-line {
              display: flex;
              justify-content: space-between;
              margin: 2px 0;
            }
            
            .ticket-numero {
              text-align: center;
              font-size: 14px;
              font-weight: bold;
              padding: 6px 0;
              background: #f0f0f0;
              margin: 6px 0;
            }
            
            .items {
              padding: 8px 0;
              border-top: 1px dashed #000;
              border-bottom: 1px dashed #000;
            }
            
            .item {
              margin-bottom: 6px;
            }
            
            .item-name {
              font-weight: bold;
              font-size: 10px;
            }
            
            .item-detail {
              display: flex;
              justify-content: space-between;
              font-size: 10px;
              padding-left: 8px;
            }
            
            .totales {
              padding: 8px 0;
            }
            
            .total-line {
              display: flex;
              justify-content: space-between;
              margin: 3px 0;
            }
            
            .total-final {
              font-size: 14px;
              font-weight: bold;
              border-top: 2px solid #000;
              padding-top: 6px;
              margin-top: 6px;
            }
            
            .pagos {
              padding: 6px 0;
              border-top: 1px dashed #000;
            }
            
            .pagos-title {
              font-weight: bold;
              margin-bottom: 4px;
            }
            
            .pago-line {
              display: flex;
              justify-content: space-between;
              font-size: 10px;
            }
            
            .cambio-section {
              background: #f5f5f5;
              padding: 6px;
              margin: 6px 0;
              text-align: center;
            }
            
            .cambio-label {
              font-size: 10px;
            }
            
            .cambio-monto {
              font-size: 16px;
              font-weight: bold;
            }
            
            .footer {
              text-align: center;
              padding-top: 10px;
              border-top: 1px dashed #000;
              margin-top: 8px;
            }
            
            .footer-message {
              font-size: 11px;
              font-weight: bold;
              margin-bottom: 4px;
            }
            
            .footer-legal {
              font-size: 9px;
              color: #666;
            }
            
            .barcode {
              text-align: center;
              margin: 8px 0;
              font-family: 'Libre Barcode 39', monospace;
              font-size: 32px;
              letter-spacing: -2px;
            }
            
            @media print {
              @page {
                size: 80mm auto;
                margin: 0;
              }
              body {
                width: 72mm;
                padding: 2mm;
              }
            }
          </style>
        </head>
        <body>
          <div class="ticket">
            <div class="header">
              <div class="logo-text">NOVAVISION</div>
              <div class="empresa-info">Clínica Oftalmológica</div>
              ${ticket.empresa.direccion ? `<div class="empresa-info">${ticket.empresa.direccion}</div>` : ''}
              ${ticket.empresa.nit ? `<div class="empresa-info">NIT: ${ticket.empresa.nit}</div>` : ''}
              ${ticket.empresa.telefono ? `<div class="empresa-info">Tel: ${ticket.empresa.telefono}</div>` : ''}
            </div>
            
            <div class="ticket-numero">${ticket.venta.numero}</div>
            
            <div class="info-section">
              <div class="info-line">
                <span>Fecha:</span>
                <span>${ticket.venta.fecha}</span>
              </div>
              <div class="info-line">
                <span>Cliente:</span>
                <span>${ticket.cliente.nombre}</span>
              </div>
              ${ticket.venta.vendedor ? `
                <div class="info-line">
                  <span>Atendió:</span>
                  <span>${ticket.venta.vendedor}</span>
                </div>
              ` : ''}
            </div>
            
            <div class="items">
              ${itemsHTML}
            </div>
            
            <div class="totales">
              <div class="total-line">
                <span>Subtotal:</span>
                <span>Q${ticket.totales.subtotal.toFixed(2)}</span>
              </div>
              ${ticket.totales.descuento > 0 ? `
                <div class="total-line">
                  <span>Descuento:</span>
                  <span>-Q${ticket.totales.descuento.toFixed(2)}</span>
                </div>
              ` : ''}
              <div class="total-line">
                <span>IVA (12%):</span>
                <span>Q${ticket.totales.iva.toFixed(2)}</span>
              </div>
              <div class="total-line total-final">
                <span>TOTAL:</span>
                <span>Q${ticket.totales.total.toFixed(2)}</span>
              </div>
            </div>
            
            <div class="pagos">
              <div class="pagos-title">Forma de Pago:</div>
              ${formasPagoHTML}
            </div>
            
            ${ticket.pago.cambio > 0 ? `
              <div class="cambio-section">
                <div class="cambio-label">Efectivo recibido: Q${ticket.pago.efectivo_recibido.toFixed(2)}</div>
                <div class="cambio-monto">CAMBIO: Q${ticket.pago.cambio.toFixed(2)}</div>
              </div>
            ` : ''}
            
            ${ticket.observaciones ? `
              <div class="divider"></div>
              <div style="font-size: 9px; padding: 4px 0;">
                <strong>Obs:</strong> ${ticket.observaciones}
              </div>
            ` : ''}
            
            <div class="footer">
              <div class="footer-message">¡Gracias por su preferencia!</div>
              <div class="footer-legal">Documento no fiscal</div>
              <div class="footer-legal">Conserve este ticket para cualquier aclaración</div>
            </div>
          </div>
          
          <script>
            // Auto-imprimir cuando está listo
            window.onafterprint = function() {
              window.close();
            };
          </script>
        </body>
      </html>
    `;
  };

  // ==================== SELECCIÓN DE PACIENTE ====================

  const seleccionarPaciente = (pac) => {
    const nombre = pac.nombre || pac.nombre_completo || `${pac.first_name} ${pac.last_name}`;
    setPaciente({ ...pac, nombre });
    setPacienteDialogOpen(false);
    setPacienteSearch('');
    setPacientesResults([]);
  };

  // ==================== RENDER ====================

  if (loadingBodega) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-[80vh]">
          <div className="text-center">
            <RefreshCw className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-slate-500">Cargando punto de venta...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!bodegaPOS) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-[80vh]">
          <div className="text-center">
            <AlertCircle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-slate-800 mb-2">Sin Bodega Configurada</h2>
            <p className="text-slate-500 mb-4">No hay una bodega configurada para punto de venta.</p>
            <p className="text-sm text-slate-400">Configure una bodega en Inventario &gt; Configuración</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      <div className="h-[calc(100vh-120px)] flex flex-col">
        {/* Header compacto */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-800">Punto de Venta</h1>
              <p className="text-sm text-slate-500">Bodega: {bodegaPOS.bodega_nombre}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => {
                fetchVentasHoy();
                setVentasDialogOpen(true);
              }}
              data-testid="btn-ventas-hoy"
            >
              <Receipt className="w-4 h-4 mr-2" />
              Ventas del Día
            </Button>
          </div>
        </div>

        {/* Banner de caja cerrada */}
        {!loadingCaja && estadoCaja && !estadoCaja.abierta && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between" data-testid="banner-caja-cerrada">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-600" />
              <div>
                <p className="font-medium text-amber-800">La caja está cerrada</p>
                <p className="text-sm text-amber-600">Debe abrir la caja antes de realizar ventas. Las ventas no se registrarán en el corte del día.</p>
              </div>
            </div>
            <Button 
              variant="outline" 
              className="border-amber-400 text-amber-700 hover:bg-amber-100"
              onClick={() => window.location.href = '/caja'}
              data-testid="btn-ir-a-caja"
            >
              Ir a Caja
            </Button>
          </div>
        )}

        {/* Contenido principal - 2 columnas */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-hidden">
          
          {/* Columna izquierda: Productos */}
          <div className="lg:col-span-2 flex flex-col bg-white rounded-lg border overflow-hidden">
            {/* Barra de búsqueda */}
            <div className="p-4 border-b bg-slate-50">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
                  <Input
                    ref={searchInputRef}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar producto o escanear código..."
                    className="pl-10 h-12 text-lg"
                    data-testid="input-buscar-producto"
                    autoFocus
                  />
                </div>
                <Select value={categoriaSeleccionada || "all"} onValueChange={(v) => setCategoriaSeleccionada(v === "all" ? "" : v)}>
                  <SelectTrigger className="w-48 h-12">
                    <SelectValue placeholder="Categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las categorías</SelectItem>
                    {categorias.map(cat => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Lista de productos - Grid táctil */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* Sección de Productos Rápidos */}
              {mostrarRapidos && productosRapidos.length > 0 && !searchQuery && !categoriaSeleccionada && (
                <div className="mb-6">
                  <div 
                    className="flex items-center justify-between mb-3 cursor-pointer group"
                    onClick={() => setMostrarRapidos(!mostrarRapidos)}
                  >
                    <div className="flex items-center gap-2">
                      <Zap className="w-5 h-5 text-amber-500" />
                      <h3 className="font-semibold text-slate-700">Productos Rápidos</h3>
                      <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-700">
                        Más vendidos
                      </Badge>
                    </div>
                    <ChevronUp className="w-4 h-4 text-slate-400 group-hover:text-slate-600" />
                  </div>
                  
                  <div className="grid grid-cols-4 md:grid-cols-4 lg:grid-cols-8 gap-2">
                    {productosRapidos.map(producto => (
                      <button
                        key={`rapido-${producto.id}`}
                        onClick={() => agregarAlCarrito(producto)}
                        className={`
                          p-2 rounded-lg border-2 text-center transition-all
                          hover:border-amber-400 hover:shadow-md hover:bg-amber-50 active:scale-95
                          ${producto.existencia === 0 && producto.existencia !== -1 
                            ? 'bg-slate-100 border-slate-200 opacity-60' 
                            : 'bg-gradient-to-b from-amber-50 to-white border-amber-200'}
                        `}
                        disabled={producto.existencia === 0 && producto.existencia !== -1}
                        data-testid={`producto-rapido-${producto.id}`}
                      >
                        <p className="font-medium text-xs text-slate-700 line-clamp-2 mb-1 min-h-[2rem]">
                          {producto.nombre.length > 20 ? producto.nombre.substring(0, 18) + '...' : producto.nombre}
                        </p>
                        <p className="text-sm font-bold text-amber-600">
                          {formatCurrency(producto.precio_venta)}
                        </p>
                        {producto.existencia >= 0 && producto.existencia <= 5 && (
                          <Badge variant="destructive" className="text-[10px] mt-1 px-1">
                            {producto.existencia}
                          </Badge>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Mostrar botón para expandir productos rápidos si está colapsado */}
              {!mostrarRapidos && productosRapidos.length > 0 && !searchQuery && !categoriaSeleccionada && (
                <button
                  onClick={() => setMostrarRapidos(true)}
                  className="w-full mb-4 p-2 rounded-lg border border-dashed border-amber-300 bg-amber-50 text-amber-600 hover:bg-amber-100 transition-colors flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  <span className="text-sm font-medium">Mostrar productos rápidos</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
              )}

              {/* Grid de todos los productos */}
              {loadingProductos ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {[1,2,3,4,5,6,7,8].map(i => (
                    <Skeleton key={i} className="h-28" />
                  ))}
                </div>
              ) : productos.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <Package className="w-16 h-16 mb-4" />
                  <p>No se encontraron productos</p>
                </div>
              ) : (
                <>
                  {(searchQuery || categoriaSeleccionada) && (
                    <p className="text-sm text-slate-500 mb-3">
                      {productos.length} producto{productos.length !== 1 ? 's' : ''} encontrado{productos.length !== 1 ? 's' : ''}
                    </p>
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {productos.map(producto => (
                      <button
                        key={producto.id}
                        onClick={() => agregarAlCarrito(producto)}
                        className={`
                          p-3 rounded-lg border-2 text-left transition-all
                          hover:border-blue-500 hover:shadow-md active:scale-95
                          ${producto.existencia === 0 && producto.existencia !== -1 
                            ? 'bg-slate-100 border-slate-200 opacity-60' 
                            : 'bg-white border-slate-200'}
                        `}
                        disabled={producto.existencia === 0 && producto.existencia !== -1}
                        data-testid={`producto-${producto.id}`}
                      >
                        <div className="flex items-start justify-between mb-1">
                          <span className="text-xs font-mono text-slate-400">{producto.codigo}</span>
                          {producto.existencia >= 0 && (
                            <Badge variant={producto.existencia > 5 ? "outline" : "destructive"} className="text-xs">
                              {producto.existencia}
                            </Badge>
                          )}
                        </div>
                        <p className="font-medium text-sm text-slate-800 line-clamp-2 mb-1">
                          {producto.nombre}
                        </p>
                        {producto.categoria_nombre && (
                          <p className="text-xs text-slate-400 mb-1">{producto.categoria_nombre}</p>
                        )}
                        <p className="text-lg font-bold text-blue-600">
                          {formatCurrency(producto.precio_venta)}
                        </p>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Columna derecha: Carrito */}
          <div className="flex flex-col bg-white rounded-lg border overflow-hidden">
            {/* Header del carrito */}
            <div className="p-4 border-b bg-blue-600 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5" />
                  <span className="font-semibold">Carrito</span>
                  {cantidadItems > 0 && (
                    <Badge className="bg-white text-blue-600">{cantidadItems}</Badge>
                  )}
                </div>
                {carrito.length > 0 && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={limpiarCarrito}
                    className="text-white hover:bg-blue-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>

            {/* Paciente */}
            <div className="p-3 border-b bg-slate-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-600">
                    {paciente ? paciente.nombre : 'Cliente General'}
                  </span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setPacienteDialogOpen(true)}
                  data-testid="btn-seleccionar-paciente"
                >
                  {paciente ? 'Cambiar' : 'Seleccionar'}
                </Button>
              </div>
            </div>

            {/* Items del carrito */}
            <div className="flex-1 overflow-y-auto p-3">
              {carrito.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <ShoppingCart className="w-12 h-12 mb-2" />
                  <p className="text-sm">Carrito vacío</p>
                  <p className="text-xs">Agregue productos para vender</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {carrito.map(item => (
                    <div 
                      key={item.producto_id}
                      className="p-2 bg-slate-50 rounded-lg"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <div className="flex-1 pr-2">
                          <p className="text-sm font-medium text-slate-800 line-clamp-1">
                            {item.nombre}
                          </p>
                          <p className="text-xs text-slate-500">
                            {formatCurrency(item.precio_unitario)} c/u
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                          onClick={() => eliminarDelCarrito(item.producto_id)}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => actualizarCantidad(item.producto_id, item.cantidad - 1)}
                          >
                            <Minus className="w-4 h-4" />
                          </Button>
                          <span className="w-10 text-center font-medium">{item.cantidad}</span>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => actualizarCantidad(item.producto_id, item.cantidad + 1)}
                          >
                            <Plus className="w-4 h-4" />
                          </Button>
                        </div>
                        <span className="font-bold text-blue-600">
                          {formatCurrency(item.subtotal)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Totales */}
            <div className="border-t bg-slate-50 p-4">
              <div className="space-y-1 mb-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Subtotal</span>
                  <span>{formatCurrency(subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">IVA (12%)</span>
                  <span>{formatCurrency(iva)}</span>
                </div>
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>TOTAL</span>
                  <span className="text-blue-600">{formatCurrency(total)}</span>
                </div>
              </div>

              <Button
                className="w-full h-14 text-lg bg-blue-600 hover:bg-blue-700"
                onClick={abrirDialogoPago}
                disabled={carrito.length === 0}
                data-testid="btn-cobrar"
              >
                <DollarSign className="w-5 h-5 mr-2" />
                Cobrar {formatCurrency(total)}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== DIALOGS ==================== */}

      {/* Dialog: Seleccionar Paciente */}
      <Dialog open={pacienteDialogOpen} onOpenChange={setPacienteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Seleccionar Paciente</DialogTitle>
            <DialogDescription>Busque y seleccione un paciente</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                value={pacienteSearch}
                onChange={(e) => setPacienteSearch(e.target.value)}
                placeholder="Buscar por nombre o DPI..."
                className="pl-10"
                autoFocus
              />
            </div>
            
            <div className="max-h-60 overflow-y-auto">
              {searchingPacientes ? (
                <div className="flex items-center justify-center py-4">
                  <RefreshCw className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : pacientesResults.length === 0 ? (
                <div className="text-center py-4 text-slate-400">
                  {pacienteSearch.length >= 2 ? 'No se encontraron pacientes' : 'Escriba para buscar...'}
                </div>
              ) : (
                <div className="space-y-1">
                  {pacientesResults.map(pac => (
                    <button
                      key={pac.id}
                      onClick={() => seleccionarPaciente(pac)}
                      className="w-full p-3 text-left hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      <p className="font-medium text-slate-800">
                        {pac.nombre || pac.nombre_completo || `${pac.first_name} ${pac.last_name}`}
                      </p>
                      <p className="text-sm text-slate-500">
                        {pac.dpi ? `DPI: ${pac.dpi}` : ''} {pac.phone ? `| Tel: ${pac.phone}` : ''}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setPacienteDialogOpen(false);
              setPaciente(null);
            }}>
              Cliente General
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Pago Mixto */}
      <Dialog open={pagoDialogOpen} onOpenChange={setPagoDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl">Cobrar Venta</DialogTitle>
            <DialogDescription asChild>
              <div className="flex items-center justify-between">
                <span>Total a cobrar: <span className="text-2xl font-bold text-blue-600">{formatCurrency(total)}</span></span>
                {pendientePorPagar > 0 && formasPago.length > 0 && (
                  <span className="text-orange-600 font-medium">
                    Pendiente: {formatCurrency(pendientePorPagar)}
                  </span>
                )}
              </div>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Formas de pago agregadas */}
            {formasPago.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-3">
                <Label className="mb-2 block text-sm font-medium text-slate-700">
                  Formas de Pago Agregadas ({formasPago.length})
                </Label>
                <div className="space-y-2">
                  {formasPago.map((fp, index) => {
                    const metodoInfo = METODOS_PAGO.find(m => m.value === fp.metodo);
                    const Icon = metodoInfo?.icon || Banknote;
                    return (
                      <div 
                        key={fp.id} 
                        className="flex items-center justify-between bg-white p-3 rounded-lg border"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full ${metodoInfo?.color || 'bg-slate-500'} flex items-center justify-center`}>
                            <Icon className="w-4 h-4 text-white" />
                          </div>
                          <div>
                            <p className="font-medium text-sm">{fp.metodo}</p>
                            {fp.referencia && (
                              <p className="text-xs text-slate-500">Ref: {fp.referencia}</p>
                            )}
                            {fp.tipo_pagador_nombre && (
                              <p className="text-xs text-slate-500">{fp.tipo_pagador_nombre}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-blue-600">{formatCurrency(fp.monto)}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={() => eliminarFormaPago(fp.id)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Resumen de pago */}
                <div className="mt-3 pt-3 border-t border-slate-200 flex justify-between text-sm">
                  <span>Total pagado:</span>
                  <span className={`font-bold ${totalPagado >= total ? 'text-green-600' : 'text-orange-600'}`}>
                    {formatCurrency(totalPagado)}
                  </span>
                </div>
                
                {cambioTotal > 0 && (
                  <div className="mt-1 p-2 bg-yellow-50 rounded text-center">
                    <span className="text-yellow-700 text-sm">Cambio a devolver: </span>
                    <span className="font-bold text-yellow-700">{formatCurrency(cambioTotal)}</span>
                  </div>
                )}
              </div>
            )}
            
            {/* Agregar nueva forma de pago - solo mostrar si falta por pagar */}
            {(pendientePorPagar > 0 || formasPago.length === 0) && (
              <div className="border rounded-lg p-4 bg-white">
                <Label className="mb-3 block font-medium">
                  {formasPago.length === 0 ? 'Seleccionar Método de Pago' : 'Agregar Otro Método'}
                </Label>
                
                {/* Métodos de pago */}
                <div className="grid grid-cols-5 gap-2 mb-4">
                  {METODOS_PAGO.map(mp => {
                    const Icon = mp.icon;
                    return (
                      <button
                        key={mp.value}
                        onClick={() => seleccionarMetodoPago(mp.value)}
                        className={`
                          p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all
                          ${metodoPagoActual === mp.value 
                            ? 'border-blue-500 bg-blue-50' 
                            : 'border-slate-200 hover:border-slate-300'}
                        `}
                      >
                        <div className={`w-8 h-8 rounded-full ${mp.color} flex items-center justify-center`}>
                          <Icon className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-xs font-medium text-center">{mp.label}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Monto */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-sm">Monto</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={montoPagoActual}
                      onChange={(e) => setMontoPagoActual(e.target.value)}
                      className="h-12 text-lg font-bold text-center"
                      placeholder="0.00"
                      data-testid="input-monto-pago"
                    />
                  </div>
                  
                  {/* Referencia (para tarjeta, transferencia, cheque) */}
                  {['Tarjeta', 'Transferencia', 'Cheque'].includes(metodoPagoActual) && (
                    <div>
                      <Label className="text-sm">Referencia (opcional)</Label>
                      <Input
                        value={referenciaPagoActual}
                        onChange={(e) => setReferenciaPagoActual(e.target.value)}
                        className="h-12"
                        placeholder="No. autorización..."
                      />
                    </div>
                  )}
                  
                  {/* Pagador para CxC */}
                  {metodoPagoActual === 'Cuenta por Cobrar' && (
                    <div>
                      <Label className="text-sm">Responsable de Pago *</Label>
                      <Select value={tipoPagadorId || "select"} onValueChange={(v) => setTipoPagadorId(v === "select" ? "" : v)}>
                        <SelectTrigger className="h-12">
                          <SelectValue placeholder="Seleccione responsable..." />
                        </SelectTrigger>
                        <SelectContent>
                          {pagadores.length === 0 ? (
                            <SelectItem value="none" disabled>
                              No hay responsables. Créelos en CxC &gt; Responsables
                            </SelectItem>
                          ) : (
                            pagadores.map(pag => (
                              <SelectItem key={pag.id} value={pag.id}>
                                {pag.nombre} ({pag.tipo})
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>

                {/* Botones rápidos de monto */}
                <div className="grid grid-cols-5 gap-2 mt-3">
                  {[50, 100, 200, 500, pendientePorPagar > 0 ? Math.ceil(pendientePorPagar) : total].map((monto, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      size="sm"
                      onClick={() => setMontoPagoActual(monto.toString())}
                      className={idx === 4 ? 'bg-blue-50 border-blue-200 text-blue-700' : ''}
                    >
                      {idx === 4 ? 'Todo' : `Q${monto}`}
                    </Button>
                  ))}
                </div>

                {/* Botón agregar */}
                <Button
                  className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
                  onClick={agregarFormaPago}
                  disabled={!montoPagoActual || parseFloat(montoPagoActual) <= 0}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Agregar {metodoPagoActual} - {formatCurrency(parseFloat(montoPagoActual) || 0)}
                </Button>
              </div>
            )}

            {/* Observaciones */}
            <div>
              <Label className="text-sm">Observaciones (opcional)</Label>
              <Textarea
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                placeholder="Notas adicionales..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 mt-4">
            <Button variant="outline" onClick={() => setPagoDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={confirmarVenta}
              disabled={submitting || formasPago.length === 0 || totalPagado < total}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="btn-confirmar-venta"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  Procesando...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Confirmar Venta
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Venta Exitosa */}
      <Dialog open={ventaExitosaDialogOpen} onOpenChange={setVentaExitosaDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader className="sr-only">
            <DialogTitle>Venta Exitosa</DialogTitle>
          </DialogHeader>
          <div className="text-center py-4">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">¡Venta Exitosa!</h2>
            <p className="text-slate-500 mb-4">
              Ticket: <span className="font-mono font-bold">{ventaExitosa?.numero_venta}</span>
            </p>
            <p className="text-3xl font-bold text-blue-600 mb-6">
              {formatCurrency(ventaExitosa?.total || 0)}
            </p>
            
            {ventaExitosa?.cambio > 0 && (
              <div className="bg-yellow-50 p-3 rounded-lg mb-4">
                <span className="text-yellow-700">Cambio: </span>
                <span className="text-xl font-bold text-yellow-700">
                  {formatCurrency(ventaExitosa.cambio)}
                </span>
              </div>
            )}
          </div>
          
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                if (ventaExitosa) imprimirTicket(ventaExitosa.id);
              }}
            >
              <Printer className="w-4 h-4 mr-2" />
              Imprimir Ticket
            </Button>
            <Button 
              onClick={() => setVentaExitosaDialogOpen(false)}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Nueva Venta
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Ventas del Día */}
      <Dialog open={ventasDialogOpen} onOpenChange={setVentasDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Ventas del Día</DialogTitle>
            <DialogDescription asChild>
              <div>
                {resumenDia && (
                  <span className="flex gap-6 mt-2">
                    <span>Total: <strong>{resumenDia.total_ventas}</strong> ventas</span>
                    <span>Monto: <strong className="text-blue-600">{formatCurrency(resumenDia.total_monto)}</strong></span>
                  </span>
                )}
              </div>
            </DialogDescription>
          </DialogHeader>
          
          <div className="overflow-y-auto max-h-[50vh]">
            {ventasHoy.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <Receipt className="w-12 h-12 mx-auto mb-2" />
                <p>No hay ventas registradas hoy</p>
              </div>
            ) : (
              <div className="space-y-2">
                {ventasHoy.map(venta => (
                  <div 
                    key={venta.id}
                    className="p-3 bg-slate-50 rounded-lg flex items-center justify-between hover:bg-slate-100 cursor-pointer"
                    onClick={async () => {
                      try {
                        const res = await ventasApi.getById(venta.id);
                        setVentaDetalle(res.data);
                        setVentaDetalleDialogOpen(true);
                      } catch (e) {
                        toast.error('Error al cargar detalle');
                      }
                    }}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-medium">{venta.numero_venta}</span>
                        <Badge variant={venta.estado === 'completada' ? 'outline' : 'destructive'}>
                          {venta.estado}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-500">
                        {venta.paciente_nombre || 'Cliente General'} • {venta.cantidad_items} items
                      </p>
                      <p className="text-xs text-slate-400">
                        {formatTime(venta.fecha)} • {venta.vendedor_nombre}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-blue-600">{formatCurrency(venta.total)}</p>
                      <ChevronRight className="w-4 h-4 text-slate-400 inline" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setVentasDialogOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Detalle de Venta */}
      <Dialog open={ventaDetalleDialogOpen} onOpenChange={setVentaDetalleDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Detalle de Venta</DialogTitle>
            <DialogDescription>
              {ventaDetalle?.numero_venta} • {ventaDetalle?.fecha?.split('T')[0]}
            </DialogDescription>
          </DialogHeader>
          
          {ventaDetalle && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Cliente:</span>
                  <p className="font-medium">{ventaDetalle.paciente_nombre || 'Cliente General'}</p>
                </div>
                <div>
                  <span className="text-slate-500">Vendedor:</span>
                  <p className="font-medium">{ventaDetalle.vendedor_nombre}</p>
                </div>
              </div>
              
              <div className="border rounded-lg divide-y">
                {ventaDetalle.items?.map((item, idx) => (
                  <div key={idx} className="p-2 flex justify-between text-sm">
                    <div>
                      <p className="font-medium">{item.nombre}</p>
                      <p className="text-slate-500">{item.cantidad} x {formatCurrency(item.precio_unitario)}</p>
                    </div>
                    <span className="font-medium">{formatCurrency(item.subtotal)}</span>
                  </div>
                ))}
              </div>
              
              <div className="border-t pt-2 space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Subtotal</span>
                  <span>{formatCurrency(ventaDetalle.subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>IVA</span>
                  <span>{formatCurrency(ventaDetalle.iva)}</span>
                </div>
                <div className="flex justify-between font-bold text-lg">
                  <span>Total</span>
                  <span className="text-blue-600">{formatCurrency(ventaDetalle.total)}</span>
                </div>
              </div>
              
              <div className="text-sm">
                <span className="text-slate-500">Forma de pago: </span>
                {ventaDetalle.formas_pago?.map(fp => fp.metodo).join(', ')}
              </div>
            </div>
          )}
          
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => ventaDetalle && imprimirTicket(ventaDetalle.id)}
            >
              <Printer className="w-4 h-4 mr-2" />
              Imprimir
            </Button>
            <Button variant="outline" onClick={() => setVentaDetalleDialogOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default PuntoVenta;
