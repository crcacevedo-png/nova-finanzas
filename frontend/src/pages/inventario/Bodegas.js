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
  AlertTriangle
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
import { formatDate } from '../../services/api';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form inicial
const FORM_INICIAL = {
  nombre: '',
  codigo: '',
  descripcion: '',
  responsable_id: null
};

const Bodegas = () => {
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
        <div className="flex items-center justify-between">
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
          
          <Button 
            className="bg-indigo-600 hover:bg-indigo-700"
            onClick={() => handleOpenDialog()}
          >
            <Plus className="h-4 w-4 mr-2" />
            Nueva Bodega
          </Button>
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
