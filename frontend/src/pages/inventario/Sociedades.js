// /app/frontend/src/pages/inventario/Sociedades.js
// Módulo de gestión de sociedades médicas y sus consumos

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import {
  Users, Package, TrendingDown, Plus, Pencil, Trash2,
  ChevronLeft, ChevronRight, DollarSign, BarChart3, RefreshCw, 
  FileSpreadsheet, FileText, Building2, Mail, Phone, MapPin, Save
} from 'lucide-react';
import { inventarioApi, formatCurrency, getGuatemalaDate } from '../../services/api';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Colores disponibles para sociedades
const COLORES_SOCIEDAD = [
  { id: 'purple', label: 'Morado', class: 'bg-purple-100 text-purple-800 border-purple-200' },
  { id: 'blue', label: 'Azul', class: 'bg-blue-100 text-blue-800 border-blue-200' },
  { id: 'green', label: 'Verde', class: 'bg-green-100 text-green-800 border-green-200' },
  { id: 'red', label: 'Rojo', class: 'bg-red-100 text-red-800 border-red-200' },
  { id: 'orange', label: 'Naranja', class: 'bg-orange-100 text-orange-800 border-orange-200' },
  { id: 'teal', label: 'Turquesa', class: 'bg-teal-100 text-teal-800 border-teal-200' },
  { id: 'pink', label: 'Rosa', class: 'bg-pink-100 text-pink-800 border-pink-200' },
];

const getColorClass = (colorId) => {
  const found = COLORES_SOCIEDAD.find(c => c.id === colorId);
  return found ? found.class : 'bg-purple-100 text-purple-800 border-purple-200';
};

const Sociedades = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('sociedades');
  
  // Sociedades
  const [sociedades, setSociedades] = useState([]);
  const [loadingSociedades, setLoadingSociedades] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSociedad, setEditingSociedad] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sociedadToDelete, setSociedadToDelete] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    nit: '',
    direccion: '',
    telefono: '',
    email: '',
    contacto: '',
    color: 'purple'
  });
  const [savingSociedad, setSavingSociedad] = useState(false);
  
  // Filtro por sociedad
  const [sociedadFilter, setSociedadFilter] = useState('all');
  
  // Consumos
  const [consumos, setConsumos] = useState([]);
  const [totalConsumos, setTotalConsumos] = useState(0);
  const [resumenConsumos, setResumenConsumos] = useState({});
  const [page, setPage] = useState(1);
  const [limit] = useState(30);
  
  // Filtros
  const [fechaInicio, setFechaInicio] = useState('');
  const [fechaFin, setFechaFin] = useState('');
  const [productoFilter, setProductoFilter] = useState('all');
  
  // Productos sociedad
  const [productosSociedad, setProductosSociedad] = useState([]);
  const [loadingProductos, setLoadingProductos] = useState(false);
  
  // Resumen mensual
  const [resumenMensual, setResumenMensual] = useState(null);
  const [mesSeleccionado, setMesSeleccionado] = useState(parseInt(getGuatemalaDate().split('-')[1], 10));
  const [anioSeleccionado, setAnioSeleccionado] = useState(parseInt(getGuatemalaDate().split('-')[0], 10));

  // Fetch sociedades
  const fetchSociedades = useCallback(async () => {
    try {
      setLoadingSociedades(true);
      const response = await inventarioApi.getSociedades();
      setSociedades(response.data || []);
    } catch (error) {
      console.error('Error fetching sociedades:', error);
      toast.error('Error al cargar sociedades');
    } finally {
      setLoadingSociedades(false);
    }
  }, []);

  const fetchConsumos = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (productoFilter !== 'all') params.append('producto_id', productoFilter);
      if (sociedadFilter !== 'all') params.append('sociedad_id', sociedadFilter);
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/consumos?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Error al cargar consumos');
      
      const data = await response.json();
      setConsumos(data.data || []);
      setTotalConsumos(data.total || 0);
      setResumenConsumos(data.resumen || {});
    } catch (error) {
      console.error('Error fetching consumos:', error);
      toast.error('Error al cargar consumos de sociedades');
    } finally {
      setLoading(false);
    }
  }, [page, limit, fechaInicio, fechaFin, productoFilter, sociedadFilter]);

  const fetchProductosSociedad = useCallback(async () => {
    try {
      setLoadingProductos(true);
      const token = localStorage.getItem('token');
      const params = sociedadFilter !== 'all' ? `?sociedad_id=${sociedadFilter}` : '';
      const response = await fetch(`${API_URL}/api/inventario/sociedades/productos${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Error al cargar productos');
      
      const data = await response.json();
      setProductosSociedad(data || []);
    } catch (error) {
      console.error('Error fetching productos sociedad:', error);
    } finally {
      setLoadingProductos(false);
    }
  }, [sociedadFilter]);

  const fetchResumenMensual = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        mes: mesSeleccionado.toString(),
        anio: anioSeleccionado.toString()
      });
      if (sociedadFilter !== 'all') params.append('sociedad_id', sociedadFilter);
      
      const response = await fetch(
        `${API_URL}/api/inventario/sociedades/resumen?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Error al cargar resumen');
      
      const data = await response.json();
      setResumenMensual(data);
    } catch (error) {
      console.error('Error fetching resumen:', error);
    }
  }, [mesSeleccionado, anioSeleccionado, sociedadFilter]);

  useEffect(() => {
    fetchSociedades();
  }, [fetchSociedades]);

  useEffect(() => {
    if (activeTab === 'consumos') {
      fetchConsumos();
      fetchProductosSociedad();
    } else if (activeTab === 'productos') {
      fetchProductosSociedad();
    } else if (activeTab === 'resumen') {
      fetchResumenMensual();
    }
  }, [activeTab, fetchConsumos, fetchProductosSociedad, fetchResumenMensual]);

  // CRUD Sociedades
  const handleNewSociedad = () => {
    setEditingSociedad(null);
    setFormData({
      nombre: '',
      descripcion: '',
      nit: '',
      direccion: '',
      telefono: '',
      email: '',
      contacto: '',
      color: 'purple'
    });
    setDialogOpen(true);
  };

  const handleEditSociedad = (sociedad) => {
    setEditingSociedad(sociedad);
    setFormData({
      nombre: sociedad.nombre || '',
      descripcion: sociedad.descripcion || '',
      nit: sociedad.nit || '',
      direccion: sociedad.direccion || '',
      telefono: sociedad.telefono || '',
      email: sociedad.email || '',
      contacto: sociedad.contacto || '',
      color: sociedad.color || 'purple'
    });
    setDialogOpen(true);
  };

  const handleDeleteClick = (sociedad) => {
    setSociedadToDelete(sociedad);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!sociedadToDelete) return;
    
    try {
      await inventarioApi.deleteSociedad(sociedadToDelete.id);
      toast.success(`Sociedad "${sociedadToDelete.nombre}" eliminada`);
      setDeleteDialogOpen(false);
      setSociedadToDelete(null);
      fetchSociedades();
    } catch (error) {
      console.error('Error deleting sociedad:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar sociedad');
    }
  };

  const handleSaveSociedad = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es requerido');
      return;
    }

    try {
      setSavingSociedad(true);
      
      if (editingSociedad) {
        await inventarioApi.updateSociedad(editingSociedad.id, formData);
        toast.success(`Sociedad "${formData.nombre}" actualizada`);
      } else {
        await inventarioApi.createSociedad(formData);
        toast.success(`Sociedad "${formData.nombre}" creada`);
      }
      
      setDialogOpen(false);
      fetchSociedades();
    } catch (error) {
      console.error('Error saving sociedad:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar sociedad');
    } finally {
      setSavingSociedad(false);
    }
  };

  const totalPages = Math.ceil(totalConsumos / limit);

  const exportarExcel = async () => {
    try {
      toast.info('Generando Excel...');
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (!fechaInicio && !fechaFin) {
        params.append('mes', mesSeleccionado.toString());
        params.append('anio', anioSeleccionado.toString());
      }
      if (sociedadFilter !== 'all') params.append('sociedad_id', sociedadFilter);
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/exportar/excel?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al exportar');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sociedades_consumos.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('Excel descargado correctamente');
    } catch (error) {
      console.error('Error exporting Excel:', error);
      toast.error(error.message || 'Error al exportar Excel');
    }
  };

  const exportarPDF = async () => {
    try {
      toast.info('Generando PDF...');
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      
      if (fechaInicio) params.append('fecha_inicio', fechaInicio);
      if (fechaFin) params.append('fecha_fin', fechaFin);
      if (!fechaInicio && !fechaFin) {
        params.append('mes', mesSeleccionado.toString());
        params.append('anio', anioSeleccionado.toString());
      }
      if (sociedadFilter !== 'all') params.append('sociedad_id', sociedadFilter);
      
      const response = await fetch(`${API_URL}/api/inventario/sociedades/exportar/pdf?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al exportar');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sociedades_consumos.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('PDF descargado correctamente');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error(error.message || 'Error al exportar PDF');
    }
  };

  const tipoLabels = {
    salida: 'Salida',
    venta: 'Venta',
    consumo: 'Consumo',
    ajuste_negativo: 'Ajuste -',
    baja: 'Baja'
  };

  const meses = [
    { value: 1, label: 'Enero' }, { value: 2, label: 'Febrero' },
    { value: 3, label: 'Marzo' }, { value: 4, label: 'Abril' },
    { value: 5, label: 'Mayo' }, { value: 6, label: 'Junio' },
    { value: 7, label: 'Julio' }, { value: 8, label: 'Agosto' },
    { value: 9, label: 'Septiembre' }, { value: 10, label: 'Octubre' },
    { value: 11, label: 'Noviembre' }, { value: 12, label: 'Diciembre' }
  ];

  return (
    <Layout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 font-['Outfit'] flex items-center gap-2">
              <Building2 className="w-7 h-7 text-purple-600" />
              Sociedades Médicas
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Gestión de sociedades y control de consumos de productos
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={exportarExcel} variant="outline" data-testid="export-excel-btn">
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Excel
            </Button>
            <Button onClick={exportarPDF} variant="outline" data-testid="export-pdf-btn">
              <FileText className="w-4 h-4 mr-2" />
              PDF
            </Button>
          </div>
        </div>

        {/* Filtro global por sociedad */}
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-4">
              <Label className="text-sm font-medium">Filtrar por Sociedad:</Label>
              <Select value={sociedadFilter} onValueChange={setSociedadFilter}>
                <SelectTrigger className="w-[280px]">
                  <SelectValue placeholder="Todas las sociedades" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las sociedades</SelectItem>
                  {sociedades.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      <div className="flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${getColorClass(s.color).split(' ')[0]}`} />
                        {s.nombre}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {sociedadFilter !== 'all' && (
                <Button variant="ghost" size="sm" onClick={() => setSociedadFilter('all')}>
                  Limpiar filtro
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Building2 className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Sociedades</p>
                  <p className="text-xl font-bold">{sociedades.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Package className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Productos Asignados</p>
                  <p className="text-xl font-bold">{productosSociedad.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Total Consumos</p>
                  <p className="text-xl font-bold">{resumenConsumos.total_cantidad || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <DollarSign className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Monto Vendido</p>
                  <p className="text-xl font-bold">{formatCurrency(resumenConsumos.total_costo || 0)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full max-w-lg grid-cols-4">
            <TabsTrigger value="sociedades" className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Sociedades
            </TabsTrigger>
            <TabsTrigger value="consumos" className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              Consumos
            </TabsTrigger>
            <TabsTrigger value="productos" className="flex items-center gap-2">
              <Package className="w-4 h-4" />
              Productos
            </TabsTrigger>
            <TabsTrigger value="resumen" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Resumen
            </TabsTrigger>
          </TabsList>

          {/* Tab: Sociedades */}
          <TabsContent value="sociedades" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-500">
                Administra las sociedades médicas y asigna productos desde el catálogo
              </p>
              <Button onClick={handleNewSociedad} data-testid="create-sociedad-btn">
                <Plus className="w-4 h-4 mr-2" />
                Nueva Sociedad
              </Button>
            </div>

            {loadingSociedades ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
              </div>
            ) : sociedades.length === 0 ? (
              <Card className="p-8 text-center">
                <Building2 className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500">No hay sociedades creadas</p>
                <Button className="mt-4" onClick={handleNewSociedad}>
                  <Plus className="w-4 h-4 mr-2" />
                  Crear primera sociedad
                </Button>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sociedades.map((sociedad) => (
                  <Card key={sociedad.id} className="overflow-hidden" data-testid={`sociedad-card-${sociedad.id}`}>
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <Badge className={`${getColorClass(sociedad.color)} text-sm`}>
                            <Building2 className="w-3 h-3 mr-1" />
                            {sociedad.nombre}
                          </Badge>
                        </div>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleEditSociedad(sociedad)}>
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => handleDeleteClick(sociedad)}
                            disabled={sociedad.productos_count > 0}
                            title={sociedad.productos_count > 0 ? 'Tiene productos asignados' : 'Eliminar'}
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                      {sociedad.descripcion && (
                        <CardDescription className="mt-2 text-sm">{sociedad.descripcion}</CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="pt-0 space-y-2 text-sm">
                      {sociedad.nit && (
                        <div className="text-gray-600">NIT: {sociedad.nit}</div>
                      )}
                      {sociedad.contacto && (
                        <div className="flex items-center gap-2 text-gray-600">
                          <Users className="w-4 h-4" />
                          {sociedad.contacto}
                        </div>
                      )}
                      {sociedad.telefono && (
                        <div className="flex items-center gap-2 text-gray-600">
                          <Phone className="w-4 h-4" />
                          {sociedad.telefono}
                        </div>
                      )}
                      {sociedad.email && (
                        <div className="flex items-center gap-2 text-gray-600">
                          <Mail className="w-4 h-4" />
                          {sociedad.email}
                        </div>
                      )}
                      {sociedad.direccion && (
                        <div className="flex items-center gap-2 text-gray-600">
                          <MapPin className="w-4 h-4" />
                          {sociedad.direccion}
                        </div>
                      )}
                      <div className="pt-2 border-t mt-2">
                        <Badge variant="outline">
                          {sociedad.productos_count} producto{sociedad.productos_count !== 1 ? 's' : ''} asignado{sociedad.productos_count !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Tab: Consumos */}
          <TabsContent value="consumos" className="space-y-4">
            {/* Filtros */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex flex-wrap gap-4 items-end">
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Fecha inicio</label>
                    <Input
                      type="date"
                      value={fechaInicio}
                      onChange={(e) => setFechaInicio(e.target.value)}
                      className="w-40"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Fecha fin</label>
                    <Input
                      type="date"
                      value={fechaFin}
                      onChange={(e) => setFechaFin(e.target.value)}
                      className="w-40"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Producto</label>
                    <Select value={productoFilter} onValueChange={setProductoFilter}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Todos los productos" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos los productos</SelectItem>
                        {productosSociedad.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={fetchConsumos} variant="outline">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Filtrar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Tabla de consumos */}
            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
                  </div>
                ) : consumos.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No se encontraron consumos</p>
                    <p className="text-sm mt-1">Asigna productos a sociedades para ver sus consumos aquí</p>
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sociedad</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Monto</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {consumos.map((consumo) => (
                            <tr key={consumo.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm">
                                {new Date(consumo.fecha).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' })}
                              </td>
                              <td className="px-4 py-3">
                                <div>
                                  <p className="text-sm font-medium">{consumo.producto_nombre}</p>
                                  <p className="text-xs text-gray-500">{consumo.producto_codigo}</p>
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 text-xs">
                                  <Building2 className="w-3 h-3 mr-1" />
                                  {consumo.sociedad_nombre || 'Sin asignar'}
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-sm text-right font-medium">
                                {consumo.cantidad}
                              </td>
                              <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">
                                {formatCurrency(consumo.costo_total)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Paginación */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between px-4 py-3 border-t">
                        <p className="text-sm text-gray-500">
                          Mostrando {((page - 1) * limit) + 1} - {Math.min(page * limit, totalConsumos)} de {totalConsumos}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </Button>
                          <span className="px-3 py-1 text-sm">
                            {page} / {totalPages}
                          </span>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Productos */}
          <TabsContent value="productos" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Productos Asignados a Sociedades</CardTitle>
                <CardDescription>
                  Para asignar productos a sociedades, ve a Inventario {'>'} Productos y edita cada producto
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {loadingProductos ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
                  </div>
                ) : productosSociedad.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No hay productos asignados a sociedades</p>
                    <p className="text-sm mt-1">Ve a Productos y activa &quot;Sociedad&quot; + selecciona la sociedad</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sociedad</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Existencia</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Compra</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Venta</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {productosSociedad.map((producto) => (
                          <tr key={producto.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-mono">{producto.codigo}</td>
                            <td className="px-4 py-3">
                              <span className="text-sm font-medium">{producto.nombre}</span>
                            </td>
                            <td className="px-4 py-3">
                              {producto.sociedad_nombre ? (
                                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                                  <Building2 className="w-3 h-3 mr-1" />
                                  {producto.sociedad_nombre}
                                </Badge>
                              ) : (
                                <span className="text-gray-400 text-sm">Sin asignar</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-right">
                              {producto.controla_inventario ? (
                                <Badge variant={producto.existencia_total > 10 ? "outline" : "destructive"}>
                                  {producto.existencia_total}
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="bg-blue-50 text-blue-600">∞</Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-right">{formatCurrency(producto.precio_compra)}</td>
                            <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(producto.precio_venta)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Resumen */}
          <TabsContent value="resumen" className="space-y-4">
            {/* Selector de mes/año */}
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-4">
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Mes</label>
                    <Select value={mesSeleccionado.toString()} onValueChange={(v) => setMesSeleccionado(parseInt(v))}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {meses.map(m => (
                          <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-500 mb-1 block">Año</label>
                    <Select value={anioSeleccionado.toString()} onValueChange={(v) => setAnioSeleccionado(parseInt(v))}>
                      <SelectTrigger className="w-[100px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[2024, 2025, 2026].map(a => (
                          <SelectItem key={a} value={a.toString()}>{a}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={fetchResumenMensual} variant="outline" className="mt-5">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Actualizar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {resumenMensual && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-gradient-to-br from-purple-50 to-white">
                    <CardContent className="pt-6">
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Total Consumos del Mes</p>
                        <p className="text-3xl font-bold text-purple-700">{resumenMensual.total_consumos}</p>
                        <p className="text-sm text-gray-400 mt-1">unidades</p>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className="bg-gradient-to-br from-amber-50 to-white">
                    <CardContent className="pt-6">
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Monto Vendido del Mes</p>
                        <p className="text-3xl font-bold text-amber-700">{formatCurrency(resumenMensual.total_costo)}</p>
                        <p className="text-sm text-gray-400 mt-1">en productos sociedad</p>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Consumo por Producto</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {resumenMensual.por_producto?.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead className="bg-gray-50 border-b">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Monto Vendido</th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">% del Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {resumenMensual.por_producto.map((item, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3">
                                  <div>
                                    <p className="text-sm font-medium">{item.producto_nombre}</p>
                                    <p className="text-xs text-gray-500">{item.producto_codigo}</p>
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-sm text-right font-medium">{item.cantidad}</td>
                                <td className="px-4 py-3 text-sm text-right">{formatCurrency(item.costo_total)}</td>
                                <td className="px-4 py-3 text-right">
                                  <Badge variant="outline">
                                    {resumenMensual.total_costo > 0 
                                      ? ((item.costo_total / resumenMensual.total_costo) * 100).toFixed(1) 
                                      : 0}%
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        No hay consumos registrados para este período
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>
        </Tabs>

        {/* Dialog: Crear/Editar Sociedad */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <Building2 className="w-5 h-5 text-purple-600" />
                {editingSociedad ? 'Editar Sociedad' : 'Nueva Sociedad'}
              </DialogTitle>
              <DialogDescription>
                {editingSociedad ? 'Modifica los datos de la sociedad médica.' : 'Crea una nueva sociedad médica para asignar productos.'}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData(prev => ({ ...prev, nombre: e.target.value }))}
                  placeholder="Ej: Sociedad de Glaucoma"
                  data-testid="input-sociedad-nombre"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="descripcion">Descripción</Label>
                <Textarea
                  id="descripcion"
                  value={formData.descripcion}
                  onChange={(e) => setFormData(prev => ({ ...prev, descripcion: e.target.value }))}
                  placeholder="Descripción de la sociedad..."
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nit">NIT</Label>
                  <Input
                    id="nit"
                    value={formData.nit}
                    onChange={(e) => setFormData(prev => ({ ...prev, nit: e.target.value }))}
                    placeholder="12345678-9"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telefono">Teléfono</Label>
                  <Input
                    id="telefono"
                    value={formData.telefono}
                    onChange={(e) => setFormData(prev => ({ ...prev, telefono: e.target.value }))}
                    placeholder="2222-3333"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="contacto@sociedad.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contacto">Persona de Contacto</Label>
                <Input
                  id="contacto"
                  value={formData.contacto}
                  onChange={(e) => setFormData(prev => ({ ...prev, contacto: e.target.value }))}
                  placeholder="Dr. Juan Pérez"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="direccion">Dirección</Label>
                <Input
                  id="direccion"
                  value={formData.direccion}
                  onChange={(e) => setFormData(prev => ({ ...prev, direccion: e.target.value }))}
                  placeholder="Zona 10, Ciudad de Guatemala"
                />
              </div>

              <div className="space-y-2">
                <Label>Color identificador</Label>
                <div className="flex flex-wrap gap-2">
                  {COLORES_SOCIEDAD.map(color => (
                    <button
                      key={color.id}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, color: color.id }))}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all ${color.class} ${
                        formData.color === color.id ? 'ring-2 ring-offset-2 ring-purple-500' : 'opacity-70 hover:opacity-100'
                      }`}
                    >
                      {color.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSaveSociedad} disabled={savingSociedad} data-testid="submit-sociedad-btn">
                {savingSociedad ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                {editingSociedad ? 'Guardar Cambios' : 'Crear Sociedad'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Confirmar Eliminación */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Sociedad</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar la sociedad &quot;{sociedadToDelete?.nombre}&quot;? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleConfirmDelete} data-testid="confirm-delete-sociedad-btn">
                Eliminar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Sociedades;
