// Gestión de Bodegas - Módulo de Inventario - NovaVision
import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import axios from 'axios';
import { 
  Warehouse,
  Plus,
  Pencil,
  Trash2,
  Search,
  RefreshCw,
  Package,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Scale,
  ArrowLeftRight
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Switch } from '../../components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../components/ui/alert-dialog';
import { toast, Toaster } from 'sonner';
import { formatDate, inventarioApi } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form inicial
const FORM_INICIAL = {
  nombre: '',
  codigo: '',
  descripcion: '',
  responsable_id: null
};

const Bodegas = () => {
  const { user } = useAuth();
  const esAdmin = ['superadmin', 'admin'].includes(user?.role);

  // Estado principal
  const [bodegas, setBodegas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  
  // Diálogos
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [bodegaEliminar, setBodegaEliminar] = useState(null);
  
  // Formulario
  const [form, setForm] = useState(FORM_INICIAL);

  // Diálogo "Ver productos" por bodega
  const [productosDialogOpen, setProductosDialogOpen] = useState(false);
  const [bodegaSeleccionada, setBodegaSeleccionada] = useState(null);
  const [bodegaProductos, setBodegaProductos] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  const [buscarProducto, setBuscarProducto] = useState('');

  const handleVerProductos = async (bodega) => {
    setBodegaSeleccionada(bodega);
    setBuscarProducto('');
    setProductosDialogOpen(true);
    setLoadingProductos(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/inventario/existencias?bodega_id=${bodega.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = (response.data?.data || [])
        .filter(e => (e.cantidad || 0) !== 0)
        .sort((a, b) => (a.producto_nombre || '').localeCompare(b.producto_nombre || ''));
      setBodegaProductos(data);
    } catch (error) {
      console.error('Error fetching existencias:', error);
      toast.error('Error al cargar productos de la bodega');
      setBodegaProductos([]);
    } finally {
      setLoadingProductos(false);
    }
  };

  // Reconciliación de lotes (solo admin)
  const [reconcileOpen, setReconcileOpen] = useState(false);
  const [reconcileData, setReconcileData] = useState([]);
  const [reconcileLoading, setReconcileLoading] = useState(false);
  const [reconcileApplying, setReconcileApplying] = useState(false);

  const handleAbrirReconcile = async () => {
    setReconcileOpen(true);
    setReconcileLoading(true);
    try {
      const res = await inventarioApi.reconciliarLotesPreview();
      setReconcileData(res.data?.discrepancias || []);
    } catch (error) {
      console.error('Error preview reconciliación:', error);
      toast.error(error.response?.data?.detail || 'Error al detectar descuadres');
      setReconcileData([]);
    } finally {
      setReconcileLoading(false);
    }
  };

  const handleAplicarReconcile = async () => {
    setReconcileApplying(true);
    try {
      const res = await inventarioApi.reconciliarLotes();
      toast.success(res.data?.message || 'Reconciliación completada');
      // Confirmar que ya no quedan descuadres
      const prev = await inventarioApi.reconciliarLotesPreview();
      setReconcileData(prev.data?.discrepancias || []);
      fetchBodegas();
    } catch (error) {
      console.error('Error aplicando reconciliación:', error);
      toast.error(error.response?.data?.detail || 'Error al reconciliar');
    } finally {
      setReconcileApplying(false);
    }
  };

  // Traslado entre bodegas (solo admin)
  const [trasladoOpen, setTrasladoOpen] = useState(false);
  const [trasladoOrigen, setTrasladoOrigen] = useState('');
  const [trasladoDestino, setTrasladoDestino] = useState('');
  const [trasladoProductoId, setTrasladoProductoId] = useState('');
  const [trasladoCantidad, setTrasladoCantidad] = useState('');
  const [trasladoMotivo, setTrasladoMotivo] = useState('');
  const [productosOrigen, setProductosOrigen] = useState([]);
  const [loadingProductosOrigen, setLoadingProductosOrigen] = useState(false);
  const [trasladoSaving, setTrasladoSaving] = useState(false);

  const abrirTraslado = () => {
    setTrasladoOrigen('');
    setTrasladoDestino('');
    setTrasladoProductoId('');
    setTrasladoCantidad('');
    setTrasladoMotivo('');
    setProductosOrigen([]);
    setTrasladoOpen(true);
  };

  const handleOrigenChange = async (bodegaId) => {
    setTrasladoOrigen(bodegaId);
    setTrasladoProductoId('');
    setTrasladoCantidad('');
    if (trasladoDestino === bodegaId) setTrasladoDestino('');
    setLoadingProductosOrigen(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/inventario/existencias?bodega_id=${bodegaId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = (res.data?.data || [])
        .filter(e => (e.cantidad || 0) > 0)
        .sort((a, b) => (a.producto_nombre || '').localeCompare(b.producto_nombre || ''));
      setProductosOrigen(data);
    } catch (error) {
      console.error('Error fetching productos origen:', error);
      toast.error('Error al cargar productos de la bodega origen');
      setProductosOrigen([]);
    } finally {
      setLoadingProductosOrigen(false);
    }
  };

  const productoTrasladoSel = productosOrigen.find(p => p.producto_id === trasladoProductoId);
  const disponibleOrigen = productoTrasladoSel?.cantidad || 0;

  const handleGuardarTraslado = async () => {
    const cant = parseInt(trasladoCantidad, 10);
    if (!trasladoOrigen || !trasladoDestino || !trasladoProductoId) {
      toast.error('Completa origen, destino y producto');
      return;
    }
    if (trasladoOrigen === trasladoDestino) {
      toast.error('La bodega de origen y destino deben ser diferentes');
      return;
    }
    if (!cant || cant <= 0) {
      toast.error('Ingresa una cantidad válida');
      return;
    }
    if (cant > disponibleOrigen) {
      toast.error(`Solo hay ${disponibleOrigen} disponibles en la bodega de origen`);
      return;
    }
    try {
      setTrasladoSaving(true);
      const res = await inventarioApi.crearTraslado({
        producto_id: trasladoProductoId,
        bodega_origen_id: trasladoOrigen,
        bodega_destino_id: trasladoDestino,
        cantidad: cant,
        motivo: trasladoMotivo || null
      });
      toast.success(res.data?.message || 'Traslado realizado');
      setTrasladoOpen(false);
    } catch (error) {
      console.error('Error en traslado:', error);
      toast.error(error.response?.data?.detail || 'Error al realizar el traslado');
    } finally {
      setTrasladoSaving(false);
    }
  };

  // ==================== FETCH DATA ====================

  const fetchBodegas = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (!showInactive) params.append('activo', 'true');
      
      const response = await axios.get(`${API_URL}/inventario/bodegas?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      let data = response.data?.data || [];
      
      // Filtrar por búsqueda
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        data = data.filter(b => 
          b.nombre?.toLowerCase().includes(term) ||
          b.codigo?.toLowerCase().includes(term) ||
          b.descripcion?.toLowerCase().includes(term)
        );
      }
      
      setBodegas(data);
    } catch (error) {
      console.error('Error fetching bodegas:', error);
      toast.error('Error al cargar bodegas');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, showInactive]);

  useEffect(() => {
    fetchBodegas();
  }, [fetchBodegas]);

  // ==================== CRUD ====================

  const handleOpenDialog = (bodega = null) => {
    if (bodega) {
      setEditando(bodega);
      setForm({
        nombre: bodega.nombre || '',
        codigo: bodega.codigo || '',
        descripcion: bodega.descripcion || '',
        responsable_id: bodega.responsable_id || null
      });
    } else {
      setEditando(null);
      setForm(FORM_INICIAL);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditando(null);
    setForm(FORM_INICIAL);
  };

  const handleSubmit = async () => {
    // Validaciones
    if (!form.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (!form.codigo.trim()) {
      toast.error('El código es requerido');
      return;
    }
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        nombre: form.nombre.trim(),
        codigo: form.codigo.trim().toUpperCase(),
        descripcion: form.descripcion.trim() || null,
        responsable_id: form.responsable_id || null,
        es_punto_venta: false // Siempre false según requerimiento
      };
      
      if (editando) {
        await axios.put(`${API_URL}/inventario/bodegas/${editando.id}`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Bodega actualizada exitosamente');
      } else {
        await axios.post(`${API_URL}/inventario/bodegas`, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Bodega creada exitosamente');
      }
      
      handleCloseDialog();
      fetchBodegas();
    } catch (error) {
      console.error('Error guardando bodega:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar bodega');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActivo = async (bodega) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/inventario/bodegas/${bodega.id}`, {
        ...bodega,
        activo: !bodega.activo
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(bodega.activo ? 'Bodega desactivada' : 'Bodega activada');
      fetchBodegas();
    } catch (error) {
      console.error('Error toggling bodega:', error);
      toast.error('Error al cambiar estado de bodega');
    }
  };

  const handleDelete = async () => {
    if (!bodegaEliminar) return;
    
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/inventario/bodegas/${bodegaEliminar.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Bodega eliminada exitosamente');
      setDeleteDialogOpen(false);
      setBodegaEliminar(null);
      fetchBodegas();
    } catch (error) {
      console.error('Error eliminando bodega:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar bodega');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== RENDER ====================

  // Estadísticas
  const totalBodegas = bodegas.length;
  const bodegasActivas = bodegas.filter(b => b.activo).length;
  const bodegasInactivas = bodegas.filter(b => !b.activo).length;

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-6 space-y-6" data-testid="bodegas-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20">
              <Warehouse className="h-6 w-6 text-indigo-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Gestión de Bodegas
              </h1>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Administra las bodegas del sistema de inventario
              </p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            {esAdmin && (
              <Button
                variant="outline"
                onClick={abrirTraslado}
                data-testid="traslado-btn"
                title="Mover unidades de una bodega a otra"
              >
                <ArrowLeftRight className="h-4 w-4 mr-2" />
                Traslado
              </Button>
            )}
            {esAdmin && (
              <Button
                variant="outline"
                onClick={handleAbrirReconcile}
                data-testid="reconciliar-lotes-btn"
                title="Corrige productos cuya existencia no coincide con la suma de sus lotes"
              >
                <Scale className="h-4 w-4 mr-2" />
                Reconciliar lotes
              </Button>
            )}
            <Button 
              className="bg-indigo-600 hover:bg-indigo-700"
              onClick={() => handleOpenDialog()}
            >
              <Plus className="h-4 w-4 mr-2" />
              Nueva Bodega
            </Button>
          </div>
        </div>

        {/* Tarjetas de resumen */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Total Bodegas
                  </p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                    {totalBodegas}
                  </p>
                </div>
                <div className="p-3 rounded-full bg-indigo-100">
                  <Warehouse className="h-6 w-6 text-indigo-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Activas
                  </p>
                  <p className="text-2xl font-bold text-green-600">
                    {bodegasActivas}
                  </p>
                </div>
                <div className="p-3 rounded-full bg-green-100">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Inactivas
                  </p>
                  <p className="text-2xl font-bold text-slate-500">
                    {bodegasInactivas}
                  </p>
                </div>
                <div className="p-3 rounded-full bg-slate-100">
                  <XCircle className="h-6 w-6 text-slate-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filtros */}
        <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Buscar por nombre, código..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-bodegas"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <Switch
                  id="showInactive"
                  checked={showInactive}
                  onCheckedChange={setShowInactive}
                />
                <Label htmlFor="showInactive" className="text-sm cursor-pointer">
                  Mostrar inactivas
                </Label>
              </div>
              
              <Button variant="outline" onClick={fetchBodegas}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla de bodegas */}
        <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : bodegas.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                <Warehouse className="h-12 w-12 mb-3 opacity-50" />
                <p>No hay bodegas registradas</p>
                <Button 
                  className="mt-4 bg-indigo-600 hover:bg-indigo-700"
                  onClick={() => handleOpenDialog()}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Crear Primera Bodega
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código</TableHead>
                    <TableHead>Nombre</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha Creación</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bodegas.map((bodega) => (
                    <TableRow key={bodega.id} className={!bodega.activo ? 'opacity-60' : ''}>
                      <TableCell className="font-mono font-medium">
                        {bodega.codigo}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                            <Warehouse className="h-4 w-4 text-indigo-600" />
                          </div>
                          <span className="font-medium">{bodega.nombre}</span>
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-slate-500">
                        {bodega.descripcion || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge 
                          className={bodega.activo 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-slate-100 text-slate-700'
                          }
                        >
                          {bodega.activo ? 'Activa' : 'Inactiva'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm">
                        {formatDate(bodega.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleVerProductos(bodega)}
                            title="Ver productos"
                            data-testid={`ver-productos-${bodega.id}`}
                          >
                            <Package className="h-4 w-4 text-indigo-600" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenDialog(bodega)}
                            title="Editar"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActivo(bodega)}
                            title={bodega.activo ? 'Desactivar' : 'Activar'}
                          >
                            {bodega.activo ? (
                              <XCircle className="h-4 w-4 text-orange-500" />
                            ) : (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => {
                              setBodegaEliminar(bodega);
                              setDeleteDialogOpen(true);
                            }}
                            title="Eliminar"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Diálogo Crear/Editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editando ? 'Editar Bodega' : 'Nueva Bodega'}
            </DialogTitle>
            <DialogDescription>
              {editando 
                ? 'Modifica los datos de la bodega'
                : 'Crea una nueva bodega para el inventario'
              }
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="codigo">Código *</Label>
                <Input
                  id="codigo"
                  value={form.codigo}
                  onChange={(e) => setForm({...form, codigo: e.target.value.toUpperCase()})}
                  placeholder="BOD-001"
                  maxLength={20}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={form.nombre}
                  onChange={(e) => setForm({...form, nombre: e.target.value})}
                  placeholder="Bodega Principal"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="descripcion">Descripción</Label>
              <Textarea
                id="descripcion"
                value={form.descripcion}
                onChange={(e) => setForm({...form, descripcion: e.target.value})}
                placeholder="Descripción de la bodega..."
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={handleCloseDialog}>
              Cancelar
            </Button>
            <Button 
              className="bg-indigo-600 hover:bg-indigo-700"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {editando ? 'Actualizar' : 'Crear'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Ver Productos de la Bodega */}
      <Dialog open={productosDialogOpen} onOpenChange={setProductosDialogOpen}>
        <DialogContent className="sm:max-w-2xl" data-testid="bodega-productos-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-indigo-600" />
              Productos en {bodegaSeleccionada?.nombre}
            </DialogTitle>
            <DialogDescription>
              Existencias actuales de esta bodega. Solo se muestran productos con stock.
            </DialogDescription>
          </DialogHeader>

          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Buscar producto..."
              value={buscarProducto}
              onChange={(e) => setBuscarProducto(e.target.value)}
              className="pl-10"
              data-testid="buscar-producto-bodega"
            />
          </div>

          <div className="max-h-[50vh] overflow-auto">
            {loadingProductos ? (
              <div className="space-y-2 py-4">
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : (() => {
              const term = buscarProducto.trim().toLowerCase();
              const filtrados = term
                ? bodegaProductos.filter(p =>
                    (p.producto_nombre || '').toLowerCase().includes(term) ||
                    (p.producto_codigo || '').toLowerCase().includes(term))
                : bodegaProductos;
              if (filtrados.length === 0) {
                return (
                  <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                    <Package className="h-10 w-10 mb-2 opacity-50" />
                    <p>{bodegaProductos.length === 0 ? 'Esta bodega no tiene productos con stock' : 'Sin coincidencias'}</p>
                  </div>
                );
              }
              return (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Código</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead className="text-right">Cantidad</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtrados.map((p) => (
                      <TableRow key={`${p.producto_id}-${p.bodega_id}`} data-testid={`bodega-producto-row-${p.producto_id}`}>
                        <TableCell className="font-mono text-xs text-slate-500">{p.producto_codigo || '-'}</TableCell>
                        <TableCell className="font-medium">{p.producto_nombre}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant={p.cantidad > 5 ? 'outline' : 'destructive'} className="font-semibold">
                            {p.cantidad}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              );
            })()}
          </div>

          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              <span className="text-sm text-slate-500" data-testid="bodega-productos-total">
                {bodegaProductos.length} producto{bodegaProductos.length !== 1 ? 's' : ''} con stock
              </span>
              <Button variant="outline" onClick={() => setProductosDialogOpen(false)}>Cerrar</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Traslado entre Bodegas */}
      <Dialog open={trasladoOpen} onOpenChange={setTrasladoOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="traslado-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowLeftRight className="h-5 w-5 text-indigo-600" />
              Traslado entre bodegas
            </DialogTitle>
            <DialogDescription>
              Mueve unidades de un producto de una bodega a otra. Queda registrado en el kardex.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <Label>Bodega de origen *</Label>
              <Select value={trasladoOrigen} onValueChange={handleOrigenChange}>
                <SelectTrigger data-testid="traslado-origen-select">
                  <SelectValue placeholder="Selecciona la bodega de origen" />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.filter(b => b.activo).map((b) => (
                    <SelectItem key={b.id} value={b.id} data-testid={`traslado-origen-${b.id}`}>{b.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Producto *</Label>
              <Select
                value={trasladoProductoId}
                onValueChange={(v) => { setTrasladoProductoId(v); setTrasladoCantidad(''); }}
                disabled={!trasladoOrigen || loadingProductosOrigen}
              >
                <SelectTrigger data-testid="traslado-producto-select">
                  <SelectValue placeholder={
                    !trasladoOrigen ? 'Primero elige la bodega de origen'
                      : loadingProductosOrigen ? 'Cargando productos...'
                      : productosOrigen.length === 0 ? 'Esta bodega no tiene productos con stock'
                      : 'Selecciona un producto'
                  } />
                </SelectTrigger>
                <SelectContent>
                  {productosOrigen.map((p) => (
                    <SelectItem key={p.producto_id} value={p.producto_id} data-testid={`traslado-producto-${p.producto_id}`}>
                      {p.producto_nombre} ({p.cantidad} disp.)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Cantidad a trasladar *</Label>
              <Input
                type="number"
                min="1"
                max={disponibleOrigen}
                value={trasladoCantidad}
                onChange={(e) => setTrasladoCantidad(e.target.value)}
                placeholder="0"
                disabled={!trasladoProductoId}
                data-testid="traslado-cantidad-input"
              />
              {trasladoProductoId && (
                <p className="text-xs text-slate-500 mt-1">Disponible en origen: <span className="font-semibold">{disponibleOrigen}</span></p>
              )}
            </div>

            <div>
              <Label>Bodega de destino *</Label>
              <Select value={trasladoDestino} onValueChange={setTrasladoDestino}>
                <SelectTrigger data-testid="traslado-destino-select">
                  <SelectValue placeholder="Selecciona la bodega de destino" />
                </SelectTrigger>
                <SelectContent>
                  {bodegas.filter(b => b.activo && b.id !== trasladoOrigen).map((b) => (
                    <SelectItem key={b.id} value={b.id} data-testid={`traslado-destino-${b.id}`}>{b.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Motivo (opcional)</Label>
              <Textarea
                value={trasladoMotivo}
                onChange={(e) => setTrasladoMotivo(e.target.value)}
                placeholder="Ej. Reabastecer dispensario"
                rows={2}
                data-testid="traslado-motivo-input"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTrasladoOpen(false)}>Cancelar</Button>
            <Button
              className="bg-indigo-600 hover:bg-indigo-700"
              onClick={handleGuardarTraslado}
              disabled={trasladoSaving}
              data-testid="traslado-guardar-btn"
            >
              {trasladoSaving ? (
                <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Trasladando...</>
              ) : (
                <><ArrowLeftRight className="h-4 w-4 mr-2" />Realizar traslado</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Reconciliar Lotes */}
      <Dialog open={reconcileOpen} onOpenChange={setReconcileOpen}>
        <DialogContent className="sm:max-w-2xl" data-testid="reconciliar-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-indigo-600" />
              Reconciliar lotes
            </DialogTitle>
            <DialogDescription>
              Productos con control de lotes cuya existencia no coincide con la suma de sus lotes.
              Al reconciliar, la existencia se ajusta a la suma de los lotes y queda registrado en el kardex.
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[50vh] overflow-auto">
            {reconcileLoading ? (
              <div className="space-y-2 py-4">
                {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : reconcileData.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-green-600" data-testid="reconciliar-sin-descuadres">
                <CheckCircle className="h-10 w-10 mb-2" />
                <p className="font-medium">Todo cuadra</p>
                <p className="text-sm text-slate-500">No hay descuadres entre existencias y lotes.</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Bodega</TableHead>
                    <TableHead className="text-right">Existencia</TableHead>
                    <TableHead className="text-right">Lotes</TableHead>
                    <TableHead className="text-right">Ajuste</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reconcileData.map((d) => (
                    <TableRow key={`${d.producto_id}-${d.bodega_id}`} data-testid={`reconciliar-row-${d.producto_id}`}>
                      <TableCell className="font-medium">
                        {d.producto_nombre}
                        <span className="block text-xs font-mono text-slate-400">{d.producto_codigo}</span>
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">{d.bodega_nombre}</TableCell>
                      <TableCell className="text-right">{d.existencia_actual}</TableCell>
                      <TableCell className="text-right font-semibold">{d.suma_lotes}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant={d.diferencia < 0 ? 'destructive' : 'outline'}>
                          {d.diferencia > 0 ? '+' : ''}{d.diferencia}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              <span className="text-sm text-slate-500" data-testid="reconciliar-total">
                {reconcileData.length} descuadre{reconcileData.length !== 1 ? 's' : ''} detectado{reconcileData.length !== 1 ? 's' : ''}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setReconcileOpen(false)}>Cerrar</Button>
                <Button
                  className="bg-indigo-600 hover:bg-indigo-700"
                  onClick={handleAplicarReconcile}
                  disabled={reconcileApplying || reconcileLoading || reconcileData.length === 0}
                  data-testid="reconciliar-aplicar-btn"
                >
                  {reconcileApplying ? (
                    <><RefreshCw className="h-4 w-4 mr-2 animate-spin" />Reconciliando...</>
                  ) : (
                    <><Scale className="h-4 w-4 mr-2" />Reconciliar</>
                  )}
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Confirmar Eliminación */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Confirmar Eliminación
            </AlertDialogTitle>
            <AlertDialogDescription>
              ¿Estás seguro de eliminar la bodega <strong>{bodegaEliminar?.nombre}</strong>?
              <br /><br />
              Esta acción no se puede deshacer. Si la bodega tiene productos asociados, 
              es preferible desactivarla en lugar de eliminarla.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setBodegaEliminar(null)}>
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction 
              className="bg-red-600 hover:bg-red-700"
              onClick={handleDelete}
              disabled={submitting}
            >
              {submitting ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Bodegas;
