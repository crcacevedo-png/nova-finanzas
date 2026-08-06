// /app/frontend/src/pages/PuntoVenta.js
// Módulo de Punto de Venta (POS) táctil para NovaVision
// Optimizado para uso en tablets y pantallas táctiles

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { ventasApi, inventarioApi, formatCurrency, formatDate } from '../services/api';
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
  DollarSign
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
  const [metodoPago, setMetodoPago] = useState('Efectivo');
  const [efectivoRecibido, setEfectivoRecibido] = useState('');
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
  
  // UI state
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('venta');

  // ==================== EFECTOS ====================
  
  useEffect(() => {
    fetchBodegaPOS();
    fetchCategorias();
    fetchPagadores();
  }, []);
  
  useEffect(() => {
    if (bodegaPOS) {
      fetchProductos();
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
      const response = await axios.get(`${API_URL}/catalogos/pagadores`);
      setPagadores(response.data || []);
    } catch (error) {
      console.error('Error fetching pagadores:', error);
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
    setMetodoPago('Efectivo');
    setEfectivoRecibido('');
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
  const cambio = metodoPago === 'Efectivo' ? Math.max(0, (parseFloat(efectivoRecibido) || 0) - total) : 0;

  // ==================== FUNCIONES DE PAGO ====================

  const abrirDialogoPago = () => {
    if (carrito.length === 0) {
      toast.error('Agregue productos al carrito');
      return;
    }
    
    setFormasPago([{ metodo: 'Efectivo', monto: total, referencia: '' }]);
    setEfectivoRecibido(total.toFixed(2));
    setPagoDialogOpen(true);
  };

  const seleccionarMetodoPago = (metodo) => {
    setMetodoPago(metodo);
    setFormasPago([{ metodo, monto: total, referencia: '', tipo_pagador_id: '', tipo_pagador_nombre: '' }]);
    if (metodo === 'Efectivo') {
      setEfectivoRecibido(total.toFixed(2));
    } else {
      setEfectivoRecibido('');
    }
  };

  const confirmarVenta = async () => {
    // Validaciones
    if (carrito.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }
    
    if (formasPago[0].metodo === 'Efectivo' && parseFloat(efectivoRecibido) < total) {
      toast.error('El efectivo recibido es menor al total');
      return;
    }
    
    if (formasPago[0].metodo === 'Cuenta por Cobrar' && !tipoPagadorId) {
      toast.error('Seleccione el tipo de pagador para Cuenta por Cobrar');
      return;
    }
    
    setSubmitting(true);
    
    try {
      // Preparar datos
      const formasPagoData = formasPago.map(fp => ({
        metodo: fp.metodo,
        monto: fp.metodo === 'Efectivo' ? parseFloat(efectivoRecibido) : total,
        referencia: fp.referencia || null,
        tipo_pagador_id: fp.metodo === 'Cuenta por Cobrar' ? tipoPagadorId : null,
        tipo_pagador_nombre: fp.metodo === 'Cuenta por Cobrar' ? 
          pagadores.find(p => p.id === tipoPagadorId)?.nombre : null
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
        observaciones: observaciones || null
      };
      
      const response = await ventasApi.crear(ventaData);
      
      // Éxito
      setVentaExitosa(response.data);
      setVentaExitosaDialogOpen(true);
      setPagoDialogOpen(false);
      
      // Limpiar carrito
      limpiarCarrito();
      
      // Actualizar productos para reflejar nuevo stock
      fetchProductos();
      
      toast.success('Venta registrada exitosamente');
      
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
            <RefreshCw className="w-12 h-12 animate-spin text-teal-600 mx-auto mb-4" />
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
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {productos.map(producto => (
                    <button
                      key={producto.id}
                      onClick={() => agregarAlCarrito(producto)}
                      className={`
                        p-3 rounded-lg border-2 text-left transition-all
                        hover:border-teal-500 hover:shadow-md active:scale-95
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
                      <p className="text-lg font-bold text-teal-600">
                        {formatCurrency(producto.precio_venta)}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Columna derecha: Carrito */}
          <div className="flex flex-col bg-white rounded-lg border overflow-hidden">
            {/* Header del carrito */}
            <div className="p-4 border-b bg-teal-600 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5" />
                  <span className="font-semibold">Carrito</span>
                  {cantidadItems > 0 && (
                    <Badge className="bg-white text-teal-600">{cantidadItems}</Badge>
                  )}
                </div>
                {carrito.length > 0 && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={limpiarCarrito}
                    className="text-white hover:bg-teal-700"
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
                        <span className="font-bold text-teal-600">
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
                  <span className="text-teal-600">{formatCurrency(total)}</span>
                </div>
              </div>

              <Button
                className="w-full h-14 text-lg bg-teal-600 hover:bg-teal-700"
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

      {/* Dialog: Pago */}
      <Dialog open={pagoDialogOpen} onOpenChange={setPagoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl">Cobrar Venta</DialogTitle>
            <DialogDescription>
              Total a cobrar: <span className="text-2xl font-bold text-teal-600">{formatCurrency(total)}</span>
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Métodos de pago */}
            <div>
              <Label className="mb-2 block">Método de Pago</Label>
              <div className="grid grid-cols-2 gap-2">
                {METODOS_PAGO.map(mp => {
                  const Icon = mp.icon;
                  return (
                    <button
                      key={mp.value}
                      onClick={() => seleccionarMetodoPago(mp.value)}
                      className={`
                        p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all
                        ${metodoPago === mp.value 
                          ? 'border-teal-500 bg-teal-50' 
                          : 'border-slate-200 hover:border-slate-300'}
                      `}
                    >
                      <div className={`w-10 h-10 rounded-full ${mp.color} flex items-center justify-center`}>
                        <Icon className="w-5 h-5 text-white" />
                      </div>
                      <span className="text-sm font-medium">{mp.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Efectivo recibido (solo para efectivo) */}
            {metodoPago === 'Efectivo' && (
              <div>
                <Label>Efectivo Recibido</Label>
                <Input
                  type="number"
                  step="0.01"
                  min={total}
                  value={efectivoRecibido}
                  onChange={(e) => setEfectivoRecibido(e.target.value)}
                  className="text-xl h-14 font-bold text-center"
                  data-testid="input-efectivo-recibido"
                />
                {cambio > 0 && (
                  <div className="mt-2 p-3 bg-green-50 rounded-lg text-center">
                    <span className="text-sm text-green-600">Cambio:</span>
                    <span className="text-2xl font-bold text-green-600 ml-2">{formatCurrency(cambio)}</span>
                  </div>
                )}
                
                {/* Botones rápidos de efectivo */}
                <div className="grid grid-cols-4 gap-2 mt-2">
                  {[50, 100, 200, 500].map(monto => (
                    <Button
                      key={monto}
                      variant="outline"
                      size="sm"
                      onClick={() => setEfectivoRecibido(monto.toString())}
                    >
                      Q{monto}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Para Cuenta por Cobrar */}
            {metodoPago === 'Cuenta por Cobrar' && (
              <div>
                <Label>Tipo de Pagador *</Label>
                <Select value={tipoPagadorId || "select"} onValueChange={(v) => setTipoPagadorId(v === "select" ? "" : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccione..." />
                  </SelectTrigger>
                  <SelectContent>
                    {pagadores.filter(p => p.activo).map(pag => (
                      <SelectItem key={pag.id} value={pag.id}>{pag.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Observaciones */}
            <div>
              <Label>Observaciones (opcional)</Label>
              <Textarea
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                placeholder="Notas adicionales..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setPagoDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={confirmarVenta}
              disabled={submitting || (metodoPago === 'Efectivo' && parseFloat(efectivoRecibido) < total)}
              className="bg-teal-600 hover:bg-teal-700"
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
            <p className="text-3xl font-bold text-teal-600 mb-6">
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
              className="bg-teal-600 hover:bg-teal-700"
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
                    <span>Monto: <strong className="text-teal-600">{formatCurrency(resumenDia.total_monto)}</strong></span>
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
                        {venta.fecha?.split('T')[1]?.substring(0, 5)} • {venta.vendedor_nombre}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-teal-600">{formatCurrency(venta.total)}</p>
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
                  <span className="text-teal-600">{formatCurrency(ventaDetalle.total)}</span>
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
