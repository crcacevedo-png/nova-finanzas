// /app/frontend/src/pages/CuentasCobrarFinanzas.js
// Cuentas por Cobrar - Módulo Clínica/Finanzas - NovaVision
// Refactorizado con componentes modulares

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import axios from 'axios';
import { 
  CreditCard,
  Search,
  RefreshCw,
  Filter
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast, Toaster } from 'sonner';

// Componentes refactorizados de CXC
import {
  ESTADOS_CXC,
  TIPOS_RESPONSABLE,
  CXCResumenCards,
  CXCResumenPorTipo,
  CXCTable,
  CXCDetalleDialog,
  CXCAbonoDialog,
  CXCResponsableDialog,
  CXCResponsablesGrid
} from '../components/cxc';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form inicial para responsables
const RESPONSABLE_FORM_INICIAL = {
  tipo: 'medico',
  nombre: '',
  nit: '',
  direccion: '',
  telefono: '',
  email: '',
  contacto: '',
  plazo_dias: 30,
  notas: ''
};

const CuentasCobrarFinanzas = () => {
  // Estado principal
  const [activeTab, setActiveTab] = useState('cuentas');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Cuentas por cobrar
  const [cuentas, setCuentas] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [resumen, setResumen] = useState(null);
  
  // Filtros
  const [filtroEstado, setFiltroEstado] = useState('all');
  const [filtroTipo, setFiltroTipo] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Cuenta seleccionada
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(null);
  const [detalleDialogOpen, setDetalleDialogOpen] = useState(false);
  
  // Abono
  const [abonoDialogOpen, setAbonoDialogOpen] = useState(false);
  const [metodoPago, setMetodoPago] = useState('Efectivo');
  const [montoAbono, setMontoAbono] = useState('');
  const [referenciaAbono, setReferenciaAbono] = useState('');
  const [notasAbono, setNotasAbono] = useState('');
  
  // Responsables
  const [responsables, setResponsables] = useState([]);
  const [responsableDialogOpen, setResponsableDialogOpen] = useState(false);
  const [responsableEditando, setResponsableEditando] = useState(null);
  const [responsableForm, setResponsableForm] = useState(RESPONSABLE_FORM_INICIAL);

  // ==================== EFECTOS ====================

  useEffect(() => {
    fetchCuentas();
    fetchResumen();
    fetchResponsables();
  }, []);

  useEffect(() => {
    fetchCuentas();
  }, [filtroEstado, filtroTipo, searchTerm, offset]);

  // ==================== API CALLS - CUENTAS ====================

  const fetchCuentas = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      params.append('limit', limit);
      params.append('offset', offset);
      if (filtroEstado && filtroEstado !== 'all') params.append('estado', filtroEstado);
      if (filtroTipo && filtroTipo !== 'all') params.append('tipo', filtroTipo);
      if (searchTerm) params.append('search', searchTerm);
      
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
  }, [filtroEstado, filtroTipo, searchTerm, offset, limit]);

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
      toast.error('Error al cargar detalle de la cuenta');
    }
  };

  // ==================== API CALLS - RESPONSABLES ====================

  const fetchResponsables = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/cuentas-cobrar/responsables`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResponsables(response.data?.data || []);
    } catch (error) {
      console.error('Error fetching responsables:', error);
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
      const payload = {
        tipo: responsableForm.tipo,
        nombre: responsableForm.nombre.trim(),
        nit: responsableForm.nit || null,
        direccion: responsableForm.direccion || null,
        telefono: responsableForm.telefono || null,
        email: responsableForm.email || null,
        contacto: responsableForm.contacto || null,
        plazo_dias: responsableForm.plazo_dias || 30,
        notas: responsableForm.notas || null
      };
      
      if (responsableEditando) {
        await axios.put(`${API_URL}/cuentas-cobrar/responsables/${responsableEditando.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Responsable actualizado');
      } else {
        await axios.post(`${API_URL}/cuentas-cobrar/responsables`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Responsable creado');
      }
      
      fetchResponsables();
      fetchResumen();
      setResponsableDialogOpen(false);
      resetResponsableForm();
    } catch (error) {
      console.error('Error guardando responsable:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar responsable');
    } finally {
      setSubmitting(false);
    }
  };

  const eliminarResponsable = async (id) => {
    if (!window.confirm('¿Está seguro de eliminar este responsable?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/cuentas-cobrar/responsables/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Responsable eliminado');
      fetchResponsables();
    } catch (error) {
      console.error('Error eliminando responsable:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar responsable');
    }
  };

  const resetResponsableForm = () => {
    setResponsableForm(RESPONSABLE_FORM_INICIAL);
    setResponsableEditando(null);
  };

  const abrirEditarResponsable = (resp) => {
    setResponsableEditando(resp);
    setResponsableForm({
      tipo: resp.tipo,
      nombre: resp.nombre,
      nit: resp.nit || '',
      direccion: resp.direccion || '',
      telefono: resp.telefono || '',
      email: resp.email || '',
      contacto: resp.contacto || '',
      plazo_dias: resp.plazo_dias || 30,
      notas: resp.notas || ''
    });
    setResponsableDialogOpen(true);
  };

  // ==================== ABONOS ====================

  const abrirAbonoDialog = () => {
    setDetalleDialogOpen(false);
    setMetodoPago('Efectivo');
    setMontoAbono('');
    setReferenciaAbono('');
    setNotasAbono('');
    setAbonoDialogOpen(true);
  };

  const registrarAbono = async () => {
    const monto = parseFloat(montoAbono);
    if (!monto || monto <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }
    
    if (monto > cuentaSeleccionada.saldo_pendiente) {
      toast.error('El monto no puede ser mayor al saldo pendiente');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/cuentas-cobrar/${cuentaSeleccionada.id}/abono`, {
        monto,
        metodo_pago: metodoPago,
        referencia: referenciaAbono || null,
        notas: notasAbono || null
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Abono registrado exitosamente');
      setAbonoDialogOpen(false);
      fetchCuentas();
      fetchResumen();
      
      // Recargar detalle
      if (cuentaSeleccionada) {
        await fetchCuentaDetalle(cuentaSeleccionada.id);
      }
    } catch (error) {
      console.error('Error registrando abono:', error);
      toast.error(error.response?.data?.detail || 'Error al registrar abono');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== RENDER ====================

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-6 space-y-6" data-testid="cxc-finanzas-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <CreditCard className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Cuentas por Cobrar
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Gestión de créditos y cobranza - Clínica
              </p>
            </div>
          </div>
          
          <Button 
            variant="outline" 
            onClick={() => { fetchCuentas(); fetchResumen(); fetchResponsables(); }}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>

        {/* Resumen Cards */}
        <CXCResumenCards resumen={resumen} />

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="cuentas">Cuentas por Cobrar</TabsTrigger>
            <TabsTrigger value="responsables">Responsables</TabsTrigger>
          </TabsList>
          
          {/* Tab: Cuentas */}
          <TabsContent value="cuentas" className="space-y-4">
            {/* Resumen por tipo */}
            <CXCResumenPorTipo resumen={resumen} />
            
            {/* Filtros */}
            <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
              <CardContent className="p-4">
                <div className="flex flex-wrap gap-4 items-center">
                  <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Buscar por número, responsable, concepto..."
                      value={searchTerm}
                      onChange={(e) => { setSearchTerm(e.target.value); setOffset(0); }}
                      className="pl-10"
                    />
                  </div>
                  
                  <Select value={filtroEstado} onValueChange={(v) => { setFiltroEstado(v); setOffset(0); }}>
                    <SelectTrigger className="w-40">
                      <Filter className="h-4 w-4 mr-2" />
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      {ESTADOS_CXC.map(e => (
                        <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <Select value={filtroTipo} onValueChange={(v) => { setFiltroTipo(v); setOffset(0); }}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {TIPOS_RESPONSABLE.map(t => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
            
            {/* Tabla */}
            <CXCTable
              cuentas={cuentas}
              loading={loading}
              total={total}
              offset={offset}
              limit={limit}
              onPageChange={setOffset}
              onSelectCuenta={fetchCuentaDetalle}
            />
          </TabsContent>
          
          {/* Tab: Responsables */}
          <TabsContent value="responsables">
            <CXCResponsablesGrid
              responsables={responsables}
              loading={loading}
              onNuevo={() => {
                resetResponsableForm();
                setResponsableDialogOpen(true);
              }}
              onEditar={abrirEditarResponsable}
              onEliminar={eliminarResponsable}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Diálogos */}
      <CXCDetalleDialog
        open={detalleDialogOpen}
        onOpenChange={setDetalleDialogOpen}
        cuenta={cuentaSeleccionada}
        onRegistrarAbono={abrirAbonoDialog}
      />
      
      <CXCAbonoDialog
        open={abonoDialogOpen}
        onOpenChange={setAbonoDialogOpen}
        cuenta={cuentaSeleccionada}
        metodoPago={metodoPago}
        setMetodoPago={setMetodoPago}
        montoAbono={montoAbono}
        setMontoAbono={setMontoAbono}
        referenciaAbono={referenciaAbono}
        setReferenciaAbono={setReferenciaAbono}
        notasAbono={notasAbono}
        setNotasAbono={setNotasAbono}
        submitting={submitting}
        onRegistrar={registrarAbono}
        onCancel={() => setAbonoDialogOpen(false)}
      />
      
      <CXCResponsableDialog
        open={responsableDialogOpen}
        onOpenChange={setResponsableDialogOpen}
        editando={responsableEditando}
        form={responsableForm}
        setForm={setResponsableForm}
        submitting={submitting}
        onGuardar={guardarResponsable}
        onCancel={() => {
          setResponsableDialogOpen(false);
          resetResponsableForm();
        }}
      />
    </Layout>
  );
};

export default CuentasCobrarFinanzas;
