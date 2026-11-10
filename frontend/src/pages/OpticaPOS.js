// /app/frontend/src/pages/OpticaPOS.js
// Punto de Venta para Óptica - NovaVision
// Refactorizado con componentes modulares

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, doctorApi } from '../services/api';
import { agendaApi } from '../services/agendaApi';
import axios from 'axios';
import { 
  Search, 
  ShoppingCart,
  Package,
  Receipt,
  RefreshCw,
  Glasses,
  Eye,
  Watch
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';

// Componentes POS refactorizados
import {
  POSProductCard,
  POSCart,
  POSPatientDialog,
  POSPaymentDialog,
  POSRecetaDialog,
  POSSuccessDialog,
  POSSalesDialog,
  POSSaleDetailDialog
} from '../components/pos';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Categorías de productos óptica
const CATEGORIAS_OPTICA = [
  { value: 'armazones', label: 'Armazones', icon: Glasses, color: 'bg-blue-500' },
  { value: 'lentes', label: 'Lentes', icon: Eye, color: 'bg-purple-500' },
  { value: 'accesorios', label: 'Accesorios', icon: Watch, color: 'bg-amber-500' },
];

// Tipos de lentes para el filtro
const TIPOS_LENTE_FILTRO = [
  { value: 'todos', label: 'Todos los Lentes' },
  { value: 'contacto', label: 'Lentes de Contacto' },
  { value: 'oftalmico', label: 'Lentes Oftálmicos' },
];

const OpticaPOS = () => {
  const { user } = useAuth();
  const searchInputRef = useRef(null);
  
  // Estado del carrito
  const [carrito, setCarrito] = useState([]);
  const [paciente, setPaciente] = useState(null);
  const [medico, setMedico] = useState(null);
  const [medicoSearch, setMedicoSearch] = useState('');
  const [medicosResults, setMedicosResults] = useState([]);
  
  // Categoría activa
  const [categoriaActiva, setCategoriaActiva] = useState('armazones');
  
  // Productos por categoría
  const [armazones, setArmazones] = useState([]);
  const [lentesContacto, setLentesContacto] = useState([]);
  const [tiposLente, setTiposLente] = useState([]);
  const [accesorios, setAccesorios] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  
  // Búsqueda
  const [searchQuery, setSearchQuery] = useState('');
  
  // Filtros de armazones
  const [filtroMarca, setFiltroMarca] = useState('all');
  const [filtroMaterial, setFiltroMaterial] = useState('all');
  const [marcasDisponibles, setMarcasDisponibles] = useState([]);
  
  // Filtro de tipo de lente (contacto/oftálmico)
  const [filtroTipoLente, setFiltroTipoLente] = useState('todos');
  
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
  const [descuentoPorcentaje, setDescuentoPorcentaje] = useState('');
  const [descuentoAutoriza, setDescuentoAutoriza] = useState('');
  
  // Receta óptica
  const [recetaDialogOpen, setRecetaDialogOpen] = useState(false);
  const [receta, setReceta] = useState({
    od_esfera: '', od_cilindro: '', od_eje: '', od_add: '',
    oi_esfera: '', oi_cilindro: '', oi_eje: '', oi_add: '',
    dp: '', altura: '', observaciones: ''
  });
  
  // Ventas del día
  const [ventasHoy, setVentasHoy] = useState([]);
  const [resumenDia, setResumenDia] = useState({ total: 0, cobrado: 0, cantidad: 0, por_metodo: {} });
  const [ventasDialogOpen, setVentasDialogOpen] = useState(false);
  
  // Confirmación de venta exitosa
  const [ventaExitosa, setVentaExitosa] = useState(null);
  const [ventaExitosaDialogOpen, setVentaExitosaDialogOpen] = useState(false);

  // Detalle de venta (desde "Ver Ventas del Día")
  const [ventaDetalle, setVentaDetalle] = useState(null);
  const [ventaDetalleDialogOpen, setVentaDetalleDialogOpen] = useState(false);
  
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
  }, [categoriaActiva, searchQuery, filtroMarca, filtroMaterial, filtroTipoLente]);
  
  useEffect(() => {
    const delaySearch = setTimeout(() => {
      if (pacienteSearch.length >= 2) {
        buscarPacientes();
      } else {
        setPacientesResults([]);
      }
    }, 300);
    return () => clearTimeout(delaySearch);
  }, [pacienteSearch]);

  // Búsqueda de médicos con debounce (lista general de médicos)
  useEffect(() => {
    const t = setTimeout(async () => {
      if (medicoSearch && medicoSearch.length >= 2 && !medico) {
        try {
          const res = await doctorApi.search(medicoSearch, 10);
          setMedicosResults(res.data || []);
        } catch (e) {
          setMedicosResults([]);
        }
      } else {
        setMedicosResults([]);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [medicoSearch, medico]);

  // ==================== API CALLS ====================

  const fetchMarcas = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/frames/brands`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMarcasDisponibles(response.data || []);
    } catch (error) {
      console.error('Error fetching brands:', error);
    }
  };

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
      } else if (categoriaActiva === 'lentes') {
        const params = new URLSearchParams();
        if (searchQuery) params.append('search', searchQuery);
        params.append('is_active', 'true');
        
        if (filtroTipoLente === 'todos' || filtroTipoLente === 'contacto') {
          const responseContacto = await axios.get(`${API_URL}/optica/contact-lenses?${params}`, { headers });
          setLentesContacto(responseContacto.data?.data || responseContacto.data || []);
        } else {
          setLentesContacto([]);
        }
        
        if (filtroTipoLente === 'todos' || filtroTipoLente === 'oftalmico') {
          const responseTipos = await axios.get(`${API_URL}/optica/lens-types?${params}`, { headers });
          setTiposLente(responseTipos.data?.data || responseTipos.data || []);
        } else {
          setTiposLente([]);
        }
      } else if (categoriaActiva === 'accesorios') {
        const params = new URLSearchParams();
        if (searchQuery) params.append('search', searchQuery);
        const responseAcc = await axios.get(`${API_URL}/optica/accessories?${params}`, { headers });
        setAccesorios(responseAcc.data?.data || responseAcc.data || []);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
      toast.error('Error al cargar productos');
    } finally {
      setLoadingProductos(false);
    }
  };

  const fetchVentasHoy = async () => {
    try {
      const token = localStorage.getItem('token');
      const resumenRes = await axios.get(`${API_URL}/optica/sales/resumen-dia`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const r = resumenRes.data || {};
      setVentasHoy(r.sales || []);
      setResumenDia({
        total: r.total_vendido || 0,
        cobrado: r.total_cobrado || 0,
        cantidad: r.cantidad_ventas || 0,
        por_metodo: r.por_metodo || {}
      });
    } catch (error) {
      console.error('Error fetching sales:', error);
    }
  };

  // Refresca el estado de FEL de la venta en el diálogo de "Venta Exitosa"
  const refrescarVentaExitosa = async () => {
    if (!ventaExitosa) return;
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/optica/sales/${ventaExitosa.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVentaExitosa(res.data);
    } catch (error) {
      console.error('Error refreshing venta exitosa:', error);
    }
  };

  // Refresca el estado de FEL de la venta en el detalle de "Ver Ventas del Día"
  const refrescarVentaDetalle = async () => {
    if (!ventaDetalle) return;
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/optica/sales/${ventaDetalle.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVentaDetalle(res.data);
      setVentasHoy(prev => prev.map(v => (v.id === res.data.id ? res.data : v)));
    } catch (error) {
      console.error('Error refreshing venta detalle:', error);
    }
  };

  const abrirDetalleVenta = (venta) => {
    setVentaDetalle(venta);
    setVentaDetalleDialogOpen(true);
  };

  // ==================== IMPRESIÓN DE TICKETS TÉRMICOS ====================

  const imprimirTicket = async (ventaId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/optica/sales/${ventaId}/ticket`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const ticket = response.data;

      const ticketHTML = generarTicketHTMLOptica(ticket);

      const printWindow = window.open('', '_blank', 'width=350,height=600');
      if (!printWindow) {
        toast.error('El navegador bloqueó la ventana de impresión. Permite ventanas emergentes para este sitio.');
        return;
      }
      printWindow.document.write(ticketHTML);
      printWindow.document.close();

      printWindow.onload = () => {
        printWindow.focus();
        printWindow.print();
      };
    } catch (error) {
      console.error('Error al generar ticket:', error);
      toast.error('Error al generar ticket');
    }
  };

  const generarTicketHTMLOptica = (ticket) => {
    const formasPagoHTML = ticket.pago.formas.map(fp => `
      <div class="pago-line">
        <span>${fp.metodo}:</span>
        <span>Q${fp.monto.toFixed(2)}</span>
      </div>
    `).join('');

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

            .ticket { width: 100%; }

            .header {
              text-align: center;
              padding-bottom: 8px;
              border-bottom: 1px dashed #000;
              margin-bottom: 8px;
            }

            .logo-text { font-size: 16px; font-weight: bold; letter-spacing: 1px; }
            .empresa-info { font-size: 10px; margin-top: 4px; }
            .divider { border-bottom: 1px dashed #000; margin: 6px 0; }
            .info-section { margin-bottom: 8px; }
            .info-line { display: flex; justify-content: space-between; margin: 2px 0; }

            .ticket-numero {
              text-align: center;
              font-size: 14px;
              font-weight: bold;
              padding: 6px 0;
              background: #f0f0f0;
              margin: 6px 0;
            }

            .items { padding: 8px 0; border-top: 1px dashed #000; border-bottom: 1px dashed #000; }
            .item { margin-bottom: 6px; }
            .item-name { font-weight: bold; font-size: 10px; }
            .item-detail { display: flex; justify-content: space-between; font-size: 10px; padding-left: 8px; }

            .totales { padding: 8px 0; }
            .total-line { display: flex; justify-content: space-between; margin: 3px 0; }
            .total-final { font-size: 14px; font-weight: bold; border-top: 2px solid #000; padding-top: 6px; margin-top: 6px; }

            .pagos { padding: 6px 0; border-top: 1px dashed #000; }
            .pagos-title { font-weight: bold; margin-bottom: 4px; }
            .pago-line { display: flex; justify-content: space-between; font-size: 10px; }

            .footer { text-align: center; padding-top: 10px; border-top: 1px dashed #000; margin-top: 8px; }
            .footer-message { font-size: 11px; font-weight: bold; margin-bottom: 4px; }
            .footer-legal { font-size: 9px; color: #666; }

            @media print {
              @page { size: 80mm auto; margin: 0; }
              body { width: 72mm; padding: 2mm; }
            }
          </style>
        </head>
        <body>
          <div class="ticket">
            <div class="header">
              <div class="logo-text">NOVAVISIÓN</div>
              <div class="empresa-info">Óptica</div>
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
              <div class="total-line total-final">
                <span>TOTAL:</span>
                <span>Q${ticket.totales.total.toFixed(2)}</span>
              </div>
            </div>

            <div class="pagos">
              <div class="pagos-title">Forma de Pago:</div>
              ${formasPagoHTML}
            </div>

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
            window.onafterprint = function() {
              window.close();
            };
          </script>
        </body>
      </html>
    `;
  };

  const buscarPacientes = async () => {
    setSearchingPacientes(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/pacientes/buscar?q=${encodeURIComponent(pacienteSearch)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPacientesResults(response.data || []);
    } catch (error) {
      console.error('Error searching patients:', error);
      toast.error('Error al buscar pacientes');
    } finally {
      setSearchingPacientes(false);
    }
  };

  // ==================== FUNCIONES DEL CARRITO ====================

  const agregarAlCarrito = (producto, tipo) => {
    const precio = producto.sale_price || producto.price || producto.default_price || 0;
    const nombre = tipo === 'armazones' 
      ? `${producto.brand} ${producto.model}` 
      : tipo === 'lentes_contacto'
        ? `${producto.brand || ''} ${producto.name || ''}`.trim()
        : tipo === 'accesorios'
          ? `${producto.brand || ''} ${producto.name || ''}`.trim()
          : producto.name;
    
    const key = `${tipo}-${producto.id}`;
    const existente = carrito.find(item => item.key === key);
    
    if (existente) {
      setCarrito(carrito.map(item => 
        item.key === key 
          ? { ...item, cantidad: item.cantidad + 1 }
          : item
      ));
    } else {
      setCarrito([...carrito, {
        key,
        tipo,
        producto_id: producto.id,
        nombre,
        precio,
        cantidad: 1
      }]);
    }
    
    toast.success(`${nombre} agregado al carrito`);
  };

  const modificarCantidad = (key, delta) => {
    setCarrito(carrito.map(item => 
      item.key === key 
        ? { ...item, cantidad: Math.max(1, item.cantidad + delta) }
        : item
    ));
  };

  const eliminarDelCarrito = (key) => {
    setCarrito(carrito.filter(item => item.key !== key));
  };

  const limpiarCarrito = () => {
    setCarrito([]);
    setPaciente(null);
    setMedico(null);
    setMedicoSearch('');
    setMedicosResults([]);
    setFormasPago([]);
    setDescuentoPorcentaje('');
    setDescuentoAutoriza('');
    setReceta({
      od_esfera: '', od_cilindro: '', od_eje: '', od_add: '',
      oi_esfera: '', oi_cilindro: '', oi_eje: '', oi_add: '',
      dp: '', altura: '', observaciones: ''
    });
    setObservaciones('');
    toast.info('Carrito limpiado');
  };

  // ==================== CÁLCULOS ====================

  const calcularSubtotal = () => {
    return carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);
  };

  const calcularDescuento = () => {
    const pct = parseFloat(descuentoPorcentaje) || 0;
    if (pct <= 0) return 0;
    return Math.round(calcularSubtotal() * (pct / 100) * 100) / 100;
  };

  const calcularTotal = () => {
    return calcularSubtotal() - calcularDescuento();
  };

  const calcularTotalPagado = () => {
    return formasPago.reduce((sum, fp) => sum + fp.monto, 0);
  };

  const calcularPendiente = () => {
    return calcularTotal() - calcularTotalPagado();
  };

  // ==================== FUNCIONES DE PAGO ====================

  const agregarFormaPago = () => {
    const monto = parseFloat(montoPagoActual);
    if (!monto || monto <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    
    setFormasPago([...formasPago, {
      metodo: metodoPagoActual,
      monto,
      referencia: referenciaPagoActual || null,
      es_cxc: metodoPagoActual === 'Cuenta por Cobrar'
    }]);
    
    setMontoPagoActual('');
    setReferenciaPagoActual('');
  };

  const eliminarFormaPago = (index) => {
    setFormasPago(formasPago.filter((_, i) => i !== index));
  };

  const agregarCxCPendiente = () => {
    const pendiente = calcularPendiente();
    if (pendiente <= 0) return;
    
    setFormasPago([...formasPago, {
      metodo: 'Cuenta por Cobrar',
      monto: pendiente,
      referencia: null,
      es_cxc: true
    }]);
    
    toast.info(`Se agregará Q${pendiente.toFixed(2)} a Cuentas por Cobrar`);
  };

  // ==================== SELECCIONAR PACIENTE ====================

  const seleccionarPaciente = (p) => {
    setPaciente(p);
    setPacienteDialogOpen(false);
    setPacienteSearch('');
    setPacientesResults([]);
    toast.success(`Paciente: ${p.primer_nombre} ${p.primer_apellido}`);
    sugerirMedicoPorCita(p.id);
  };

  // Sugerir automáticamente el médico si el paciente tiene una cita hoy
  const sugerirMedicoPorCita = async (pacienteId) => {
    if (!pacienteId) return;
    try {
      const res = await agendaApi.getCitaHoyPaciente(pacienteId);
      const med = res.data?.medico;
      if (med && med.id) {
        setMedico({ id: med.id, name: med.name });
        setMedicoSearch('');
        setMedicosResults([]);
        toast.success(`Médico sugerido por cita de hoy: ${med.name}`);
      }
    } catch (e) {
      // Silencioso: la sugerencia es opcional
    }
  };

  // ==================== PROCESAR VENTA ====================

  const procesarVenta = async () => {
    // Validaciones
    if (carrito.length === 0) {
      toast.error('El carrito está vacío');
      return;
    }

    // Si el usuario escribió un monto en el campo "Monto" pero no presionó el botón "+",
    // se agrega automáticamente aquí para no bloquear la venta de forma poco intuitiva.
    let formasPagoFinal = formasPago;
    const montoStaged = parseFloat(montoPagoActual);
    if (montoStaged > 0) {
      formasPagoFinal = [...formasPago, {
        metodo: metodoPagoActual,
        monto: montoStaged,
        referencia: referenciaPagoActual || null,
        es_cxc: metodoPagoActual === 'Cuenta por Cobrar'
      }];
      setFormasPago(formasPagoFinal);
      setMontoPagoActual('');
      setReferenciaPagoActual('');
    }
    
    const tieneCxC = formasPagoFinal.some(fp => fp.es_cxc);
    if (tieneCxC && !paciente) {
      toast.error('Debe seleccionar un paciente para ventas con Cuenta por Cobrar');
      return;
    }
    
    const totalPagadoFinal = formasPagoFinal.reduce((sum, fp) => sum + fp.monto, 0);
    const pendiente = calcularTotal() - totalPagadoFinal;
    if (pendiente > 0.01 && !tieneCxC) {
      toast.error('El monto pagado es insuficiente');
      return;
    }
    
    // Si hay paciente seleccionado, el médico es obligatorio
    if (paciente && !medico) {
      toast.error('Seleccione el médico para esta venta');
      return;
    }

    // Si hay descuento, se debe indicar quién lo autoriza
    if ((parseFloat(descuentoPorcentaje) || 0) > 0 && !descuentoAutoriza.trim()) {
      toast.error('Indique quién autoriza el descuento');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // Separar pagos CxC de pagos normales
      const pagosCxC = formasPagoFinal.filter(fp => fp.es_cxc);
      const pagosNormales = formasPagoFinal.filter(fp => !fp.es_cxc);
      const montoCxC = pagosCxC.reduce((sum, fp) => sum + fp.monto, 0);
      
      // Preparar items para el nuevo formato V2
      const items = carrito.map(item => ({
        type: item.tipo === 'armazones' ? 'frame' : item.tipo === 'lentes_contacto' ? 'contact_lens' : item.tipo === 'accesorios' ? 'accessory' : 'lens_type',
        product_id: item.producto_id,
        quantity: item.cantidad,
        unit_price: item.precio,
        subtotal: item.precio * item.cantidad
      }));
      
      const ventaPayload = {
        patient_id: paciente?.id || null,
        patient_name: paciente ? `${paciente.primer_nombre} ${paciente.primer_apellido}` : 'Consumidor Final',
        doctor_id: medico?.id || null,
        doctor_name: medico?.name || null,
        items,
        subtotal: calcularSubtotal(),
        discount: calcularDescuento(),
        discount_percent: parseFloat(descuentoPorcentaje) || 0,
        discount_authorized_by: descuentoAutoriza.trim(),
        total: calcularTotal(),
        payments: pagosNormales.map(fp => ({
          method: fp.metodo,
          amount: fp.monto,
          reference: fp.referencia
        })),
        notes: observaciones,
        receta: Object.values(receta).some(v => v) ? receta : null,
        tiene_cxc: montoCxC > 0,
        monto_cxc: montoCxC
      };
      
      const response = await axios.post(`${API_URL}/optica/sales/v2`, ventaPayload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const ventaCreada = response.data;
      
      // Si hay CxC, crear la cuenta por cobrar
      if (montoCxC > 0 && paciente) {
        try {
          await axios.post(`${API_URL}/cuentas-cobrar/optica`, {
            paciente_id: paciente.id,
            paciente_nombre: `${paciente.primer_nombre} ${paciente.primer_apellido}`,
            concepto: carrito.map(i => i.nombre).join(', ') || `Venta Óptica #${ventaCreada.order_number || ventaCreada.id}`,
            descripcion: null,
            monto_total: montoCxC,
            fecha_vencimiento: null,
            venta_origen_id: ventaCreada.id,
            venta_origen_tipo: 'optica_sale'
          }, {
            headers: { Authorization: `Bearer ${token}` }
          });
        } catch (cxcError) {
          console.error('Error creating CxC:', cxcError);
          toast.error('Venta creada pero hubo error al registrar CxC');
        }
      }
      
      // Mostrar éxito
      setVentaExitosa(ventaCreada);
      setVentaExitosaDialogOpen(true);
      setPagoDialogOpen(false);
      
      // Limpiar estado
      setCarrito([]);
      setPaciente(null);
      setMedico(null);
      setMedicoSearch('');
      setMedicosResults([]);
      setFormasPago([]);
      setObservaciones('');
      setDescuentoPorcentaje('');
      setDescuentoAutoriza('');
      setReceta({
        od_esfera: '', od_cilindro: '', od_eje: '', od_add: '',
        oi_esfera: '', oi_cilindro: '', oi_eje: '', oi_add: '',
        dp: '', altura: '', observaciones: ''
      });
      
      // Refrescar ventas del día y stock de productos
      fetchVentasHoy();
      fetchProductos();
      
      toast.success('¡Venta registrada exitosamente!');
    } catch (error) {
      console.error('Error processing sale:', error);
      toast.error(error.response?.data?.detail || 'Error al procesar la venta');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== RENDER PRODUCTOS ====================

  const renderProductos = () => {
    let productos = [];
    
    if (categoriaActiva === 'armazones') {
      productos = armazones.map(p => ({ ...p, _tipoInterno: 'armazones' }));
    } else if (categoriaActiva === 'lentes') {
      const contactoConTipo = lentesContacto.map(p => ({ ...p, _tipoInterno: 'lentes_contacto' }));
      const oftalmicosConTipo = tiposLente.map(p => ({ ...p, _tipoInterno: 'tipos_lente' }));
      productos = [...contactoConTipo, ...oftalmicosConTipo];
    } else if (categoriaActiva === 'accesorios') {
      productos = accesorios.map(p => ({ ...p, _tipoInterno: 'accesorios' }));
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
          <POSProductCard
            key={producto.id}
            producto={producto}
            categoriaActiva={categoriaActiva}
            tipoProducto={producto._tipoInterno}
            onAgregar={agregarAlCarrito}
          />
        ))}
      </div>
    );
  };

  // ==================== RENDER PRINCIPAL ====================

  return (
    <Layout>
      <Toaster position="top-right" richColors />
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
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }} data-testid="pos-resumen-vendedor">
                    Mis ventas de hoy: {resumenDia.cantidad} | Cobrado: {formatCurrency(resumenDia.cobrado)}
                  </p>
                </div>
              </div>
              
              <Button
                variant="outline"
                data-testid="pos-ver-ventas-btn"
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
                      setFiltroTipoLente('todos');
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
              )}
              
              {categoriaActiva === 'lentes' && (
                <Select value={filtroTipoLente} onValueChange={setFiltroTipoLente}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Tipo de Lente" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_LENTE_FILTRO.map(tipo => (
                      <SelectItem key={tipo.value} value={tipo.value}>{tipo.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
        <POSCart
          carrito={carrito}
          paciente={paciente}
          receta={receta}
          medico={medico}
          medicoSearch={medicoSearch}
          onMedicoSearchChange={setMedicoSearch}
          medicosResults={medicosResults}
          onSeleccionarMedico={(m) => { setMedico(m); setMedicoSearch(''); setMedicosResults([]); }}
          onRemoverMedico={() => { setMedico(null); setMedicoSearch(''); setMedicosResults([]); }}
          calcularSubtotal={calcularSubtotal}
          calcularTotal={calcularTotal}
          calcularDescuento={calcularDescuento}
          descuentoPorcentaje={descuentoPorcentaje}
          onDescuentoPorcentajeChange={setDescuentoPorcentaje}
          descuentoAutoriza={descuentoAutoriza}
          onDescuentoAutorizaChange={setDescuentoAutoriza}
          onModificarCantidad={modificarCantidad}
          onEliminarItem={eliminarDelCarrito}
          onLimpiarCarrito={limpiarCarrito}
          onSeleccionarPaciente={() => setPacienteDialogOpen(true)}
          onRemoverPaciente={() => setPaciente(null)}
          onAbrirReceta={() => setRecetaDialogOpen(true)}
          onAbrirPago={() => setPagoDialogOpen(true)}
        />
      </div>
      
      {/* Diálogos */}
      <POSPatientDialog
        open={pacienteDialogOpen}
        onOpenChange={setPacienteDialogOpen}
        searchValue={pacienteSearch}
        onSearchChange={setPacienteSearch}
        searching={searchingPacientes}
        results={pacientesResults}
        onSelectPatient={seleccionarPaciente}
      />
      
      <POSPaymentDialog
        open={pagoDialogOpen}
        onOpenChange={setPagoDialogOpen}
        metodoPagoActual={metodoPagoActual}
        setMetodoPagoActual={setMetodoPagoActual}
        montoPagoActual={montoPagoActual}
        setMontoPagoActual={setMontoPagoActual}
        referenciaPagoActual={referenciaPagoActual}
        setReferenciaPagoActual={setReferenciaPagoActual}
        formasPago={formasPago}
        observaciones={observaciones}
        setObservaciones={setObservaciones}
        paciente={paciente}
        submitting={submitting}
        calcularTotal={calcularTotal}
        calcularTotalPagado={calcularTotalPagado}
        calcularPendiente={calcularPendiente}
        onAgregarFormaPago={agregarFormaPago}
        onEliminarFormaPago={eliminarFormaPago}
        onAgregarCxCPendiente={agregarCxCPendiente}
        onProcesarVenta={procesarVenta}
      />
      
      <POSRecetaDialog
        open={recetaDialogOpen}
        onOpenChange={setRecetaDialogOpen}
        receta={receta}
        setReceta={setReceta}
      />
      
      <POSSuccessDialog
        open={ventaExitosaDialogOpen}
        onOpenChange={setVentaExitosaDialogOpen}
        ventaExitosa={ventaExitosa}
        onImprimir={imprimirTicket}
        onFelUpdated={refrescarVentaExitosa}
      />
      
      <POSSalesDialog
        open={ventasDialogOpen}
        onOpenChange={setVentasDialogOpen}
        ventasHoy={ventasHoy}
        resumenDia={resumenDia}
        onSelectVenta={abrirDetalleVenta}
      />

      <POSSaleDetailDialog
        open={ventaDetalleDialogOpen}
        onOpenChange={setVentaDetalleDialogOpen}
        venta={ventaDetalle}
        onImprimir={imprimirTicket}
        onFelUpdated={refrescarVentaDetalle}
      />
    </Layout>
  );
};

export default OpticaPOS;
