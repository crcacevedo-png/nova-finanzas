// /app/frontend/src/pages/inventario/Productos.js
// Catálogo de productos del módulo de Inventario

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import {
  Search, Plus, Edit, Package, AlertTriangle, Filter, ChevronLeft, ChevronRight,
  ArrowDownToLine, Truck, Calendar, Trash2, Upload, FileSpreadsheet, Download, 
  Power, PowerOff
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';

const Productos = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [bodegas, setBodegas] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [sociedades, setSociedades] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  
  // Filtros
  const [search, setSearch] = useState('');
  const [categoriaFilter, setCategoriaFilter] = useState('all');
  const [tipoFilter, setTipoFilter] = useState('all');
  const [bajoMinimoFilter, setBajoMinimoFilter] = useState(false);
  
  // Modal de producto
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  
  // Modal de confirmación eliminar
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  
  // Modal de importar Excel
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importPreview, setImportPreview] = useState([]);
  const [importErrors, setImportErrors] = useState([]);
  
  // Modal de Entrada Rápida
  const [entradaModalOpen, setEntradaModalOpen] = useState(false);
  const [productoParaEntrada, setProductoParaEntrada] = useState(null);
  const [entradaSubmitting, setEntradaSubmitting] = useState(false);
  const [entradaData, setEntradaData] = useState({
    bodega_id: '',
    cantidad: 1,
    costo_unitario: 0,
    proveedor_id: '',
    numero_lote: '',
    fecha_vencimiento: '',
    observaciones: ''
  });
  
  // Modal de Ajuste de Inventario
  const [ajusteModalOpen, setAjusteModalOpen] = useState(false);
  const [productoParaAjuste, setProductoParaAjuste] = useState(null);
  const [ajusteSubmitting, setAjusteSubmitting] = useState(false);
  const [ajusteData, setAjusteData] = useState({
    bodega_id: '',
    cantidad_nueva: 0,
    motivo: ''
  });
  
  const [formData, setFormData] = useState({
    codigo: '',
    codigo_barras: '',
    nombre: '',
    nombre_generico: '',
    descripcion: '',
    categoria_id: '',
    tipo: 'producto',
    presentacion: '',
    unidad_medida: 'unidad',
    unidad_compra: '',
    factor_conversion: 1,
    controla_inventario: true,
    controla_lotes: false,
    requiere_receta: false,
    es_sociedad: false,
    sociedad_id: '',
    precio_compra: 0,
    precio_venta: 0,
    afecto_iva: true,
    existencia_minima: 0,
    existencia_maxima: 0,
    proveedor_preferido_id: '',
    imagen: '',
    activo: true
  });

  const loadCategorias = useCallback(async () => {
    try {
      const res = await inventarioApi.getCategorias();
      setCategorias(res.data.data || []);
    } catch (error) {
      console.error('Error cargando categorías:', error);
    }
  }, []);

  const loadBodegasYProveedores = useCallback(async () => {
    try {
      const [bodegasRes, proveedoresRes] = await Promise.all([
        inventarioApi.getBodegas(),
        inventarioApi.getProveedores()
      ]);
      setBodegas(bodegasRes.data.data || []);
      setProveedores(proveedoresRes.data.data || []);
    } catch (error) {
      console.error('Error cargando bodegas/proveedores:', error);
    }
  }, []);

  const loadSociedades = useCallback(async () => {
    try {
      const res = await inventarioApi.getSociedades(true);
      setSociedades(res.data || []);
    } catch (error) {
      console.error('Error cargando sociedades:', error);
    }
  }, []);

  const loadProductos = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        page,
        limit,
        search: search || undefined,
        categoria_id: categoriaFilter !== 'all' ? categoriaFilter : undefined,
        tipo: tipoFilter !== 'all' ? tipoFilter : undefined,
        bajo_minimo: bajoMinimoFilter || undefined
      };
      const res = await inventarioApi.getProductos(params);
      setProductos(res.data.data || []);
      setTotal(res.data.total || 0);
    } catch (error) {
      console.error('Error cargando productos:', error);
      toast.error('Error al cargar productos');
    } finally {
      setLoading(false);
    }
  }, [page, limit, search, categoriaFilter, tipoFilter, bajoMinimoFilter]);

  useEffect(() => {
    loadCategorias();
    loadBodegasYProveedores();
    loadSociedades();
  }, [loadCategorias, loadBodegasYProveedores, loadSociedades]);

  // Abrir modal de entrada si viene desde el panel
  useEffect(() => {
    if (searchParams.get('action') === 'entrada') {
      // El usuario llegó desde "Entrada Rápida" del panel
      // Se abrirá el modal cuando seleccione un producto
    }
  }, [searchParams]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadProductos();
    }, 300);
    return () => clearTimeout(timer);
  }, [loadProductos]);

  const handleOpenModal = (producto = null) => {
    if (producto) {
      setEditingProduct(producto);
      setFormData({
        codigo: producto.codigo || '',
        codigo_barras: producto.codigo_barras || '',
        nombre: producto.nombre || '',
        nombre_generico: producto.nombre_generico || '',
        descripcion: producto.descripcion || '',
        categoria_id: producto.categoria_id || '',
        tipo: producto.tipo || 'producto',
        presentacion: producto.presentacion || '',
        unidad_medida: producto.unidad_medida || 'unidad',
        unidad_compra: producto.unidad_compra || '',
        factor_conversion: producto.factor_conversion || 1,
        controla_inventario: producto.controla_inventario ?? true,
        controla_lotes: producto.controla_lotes ?? false,
        requiere_receta: producto.requiere_receta ?? false,
        es_sociedad: producto.es_sociedad ?? false,
        sociedad_id: producto.sociedad_id || '',
        precio_compra: producto.precio_compra || 0,
        precio_venta: producto.precio_venta || 0,
        afecto_iva: producto.afecto_iva ?? true,
        existencia_minima: producto.existencia_minima || 0,
        existencia_maxima: producto.existencia_maxima || 0,
        proveedor_preferido_id: producto.proveedor_preferido_id || '',
        imagen: producto.imagen || '',
        activo: producto.activo ?? true
      });
    } else {
      setEditingProduct(null);
      setFormData({
        codigo: '',
        codigo_barras: '',
        nombre: '',
        nombre_generico: '',
        descripcion: '',
        categoria_id: '',
        tipo: 'producto',
        presentacion: '',
        unidad_medida: 'unidad',
        unidad_compra: '',
        factor_conversion: 1,
        controla_inventario: true,
        controla_lotes: false,
        requiere_receta: false,
        es_sociedad: false,
        sociedad_id: '',
        precio_compra: 0,
        precio_venta: 0,
        afecto_iva: true,
        existencia_minima: 0,
        existencia_maxima: 0,
        proveedor_preferido_id: '',
        imagen: '',
        activo: true
      });
    }
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.nombre.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    try {
      // Si es servicio, desactivar control de inventario
      const dataToSend = { ...formData };
      if (dataToSend.tipo === 'servicio') {
        dataToSend.controla_inventario = false;
        dataToSend.controla_lotes = false;
      }

      if (editingProduct) {
        await inventarioApi.updateProducto(editingProduct.id, dataToSend);
        toast.success('Producto actualizado');
      } else {
        await inventarioApi.createProducto(dataToSend);
        toast.success('Producto creado');
      }
      setModalOpen(false);
      loadProductos();
    } catch (error) {
      console.error('Error guardando producto:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar producto');
    }
  };

  // ==================== ELIMINAR PRODUCTO (Solo SuperAdmin) ====================
  
  const handleDeleteClick = (producto) => {
    setProductToDelete(producto);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async (forceDelete = false) => {
    if (!productToDelete) return;
    
    setDeleting(true);
    try {
      const response = await inventarioApi.deleteProducto(productToDelete.id, forceDelete);
      const movimientosEliminados = response.data.movimientos_eliminados || 0;
      
      if (movimientosEliminados > 0) {
        toast.success(`Producto "${productToDelete.nombre}" eliminado con ${movimientosEliminados} movimientos`);
      } else {
        toast.success(`Producto "${productToDelete.nombre}" eliminado correctamente`);
      }
      
      setDeleteModalOpen(false);
      setProductToDelete(null);
      loadProductos();
    } catch (error) {
      console.error('Error eliminando producto:', error);
      const errorMsg = error.response?.data?.detail || 'Error al eliminar producto';
      
      // Si tiene movimientos y no se forzó, mostrar opción de forzar
      if (errorMsg.includes('movimientos') && !forceDelete) {
        toast.error(errorMsg);
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setDeleting(false);
    }
  };

  // ==================== DESACTIVAR PRODUCTO ====================
  
  const handleToggleActive = async (producto) => {
    try {
      await inventarioApi.cambiarEstadoProducto(producto.id, !producto.activo);
      toast.success(`Producto ${producto.activo ? 'desactivado' : 'activado'} correctamente`);
      loadProductos();
    } catch (error) {
      console.error('Error cambiando estado:', error);
      toast.error(error.response?.data?.detail || 'Error al cambiar estado del producto');
    }
  };

  // ==================== IMPORTAR DESDE EXCEL ====================
  
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validar tipo de archivo
    const validTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv'
    ];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls|csv)$/i)) {
      toast.error('Por favor seleccione un archivo Excel (.xlsx, .xls) o CSV');
      return;
    }
    
    setImportFile(file);
    setImportErrors([]);
    
    // Leer preview del archivo
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('preview_only', 'true');
      
      const response = await inventarioApi.importarProductosPreview(formData);
      setImportPreview(response.data.preview || []);
      setImportErrors(response.data.errors || []);
    } catch (error) {
      console.error('Error leyendo archivo:', error);
      toast.error('Error al leer el archivo. Verifique el formato.');
      setImportPreview([]);
    }
  };

  const handleImportSubmit = async () => {
    if (!importFile) {
      toast.error('Seleccione un archivo primero');
      return;
    }
    
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      
      const response = await inventarioApi.importarProductos(formData);
      const { imported, errors, skipped } = response.data;
      
      if (imported > 0) {
        toast.success(`Se importaron ${imported} productos correctamente`);
      }
      if (skipped > 0) {
        toast.info(`Se omitieron ${skipped} productos (ya existentes)`);
      }
      if (errors?.length > 0) {
        toast.warning(`${errors.length} filas con errores`);
      }
      
      setImportModalOpen(false);
      setImportFile(null);
      setImportPreview([]);
      setImportErrors([]);
      loadProductos();
    } catch (error) {
      console.error('Error importando:', error);
      toast.error(error.response?.data?.detail || 'Error al importar productos');
    } finally {
      setImporting(false);
    }
  };

  const downloadTemplate = () => {
    // Crear CSV de plantilla
    const headers = [
      'codigo', 'codigo_barras', 'nombre', 'nombre_generico', 'descripcion',
      'categoria', 'tipo', 'presentacion', 'unidad_medida', 'precio_compra', 'precio_venta',
      'existencia_minima', 'existencia_maxima', 'controla_inventario', 'controla_lotes',
      'requiere_receta', 'afecto_iva'
    ];
    
    const sampleRow = [
      'PROD-001', '7501234567890', 'Producto Ejemplo', 'Nombre Genérico', 'Descripción del producto',
      'Medicamentos', 'producto', 'Caja x 10', 'unidad', '80.00', '100.00',
      '5', '100', 'true', 'false', 'false', 'true'
    ];
    
    const csvContent = [
      headers.join(','),
      sampleRow.join(','),
      '# tipo: producto, servicio, insumo',
      '# unidad_medida: unidad, caja, frasco, tubo, sobre, ampolla, ml, litro, mg, gramo, kg',
      '# controla_inventario, controla_lotes, requiere_receta, afecto_iva: true o false'
    ].join('\n');
    
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'plantilla_inventario.csv';
    link.click();
  };

  // ==================== ENTRADA RÁPIDA ====================
  
  const abrirEntradaRapida = (producto) => {
    setProductoParaEntrada(producto);
    // Pre-seleccionar Dispensario si existe, si no la primera bodega activa
    const dispensario = bodegas.find(b => b.nombre === 'Dispensario' && b.activo);
    const bodegaDefault = dispensario || bodegas.find(b => b.activo);
    
    setEntradaData({
      bodega_id: bodegaDefault?.id || '',
      cantidad: 1,
      costo_unitario: producto.costo_promedio || 0,
      proveedor_id: producto.proveedor_preferido_id || '',
      numero_lote: '',
      fecha_vencimiento: '',
      observaciones: ''
    });
    setEntradaModalOpen(true);
  };

  const handleEntradaRapida = async () => {
    // Validaciones
    if (!entradaData.bodega_id) {
      toast.error('Seleccione una bodega');
      return;
    }
    if (entradaData.cantidad <= 0) {
      toast.error('La cantidad debe ser mayor a 0');
      return;
    }
    if (entradaData.costo_unitario < 0) {
      toast.error('El costo no puede ser negativo');
      return;
    }
    if (productoParaEntrada.controla_lotes) {
      if (!entradaData.numero_lote.trim()) {
        toast.error('Este producto requiere número de lote');
        return;
      }
      if (!entradaData.fecha_vencimiento) {
        toast.error('Este producto requiere fecha de vencimiento');
        return;
      }
    }

    setEntradaSubmitting(true);
    try {
      // Usar el endpoint de entrada rápida
      const data = {
        producto_id: productoParaEntrada.id,
        bodega_id: entradaData.bodega_id,
        cantidad: parseInt(entradaData.cantidad),
        costo_unitario: parseFloat(entradaData.costo_unitario) || 0,
        numero_lote: productoParaEntrada.controla_lotes ? entradaData.numero_lote : null,
        fecha_vencimiento: productoParaEntrada.controla_lotes ? entradaData.fecha_vencimiento : null,
        motivo: entradaData.observaciones || `Entrada rápida: ${productoParaEntrada.nombre}`
      };

      await inventarioApi.registrarEntrada(data);
      
      toast.success(`✓ Entrada registrada: ${entradaData.cantidad} ${productoParaEntrada.nombre}`);
      setEntradaModalOpen(false);
      loadProductos(); // Recargar para ver el nuevo stock
      
    } catch (error) {
      console.error('Error en entrada rápida:', error);
      toast.error(error.response?.data?.detail || 'Error al registrar entrada');
    } finally {
      setEntradaSubmitting(false);
    }
  };

  // Función para abrir modal de ajuste
  const handleOpenAjuste = (producto) => {
    setProductoParaAjuste(producto);
    setAjusteData({
      bodega_id: bodegas[0]?.id || '',
      cantidad_nueva: producto.existencia_total || 0,
      motivo: ''
    });
    setAjusteModalOpen(true);
  };

  // Función para realizar ajuste de inventario
  const handleAjusteSubmit = async () => {
    if (!ajusteData.bodega_id) {
      toast.error('Seleccione una bodega');
      return;
    }
    if (ajusteData.cantidad_nueva < 0) {
      toast.error('La cantidad no puede ser negativa');
      return;
    }
    if (!ajusteData.motivo || ajusteData.motivo.trim().length < 5) {
      toast.error('Ingrese un motivo válido (mínimo 5 caracteres)');
      return;
    }

    setAjusteSubmitting(true);
    try {
      const response = await inventarioApi.registrarAjuste({
        producto_id: productoParaAjuste.id,
        bodega_id: ajusteData.bodega_id,
        cantidad_nueva: parseInt(ajusteData.cantidad_nueva),
        motivo: ajusteData.motivo.trim()
      });
      
      toast.success(response.data.message || 'Ajuste realizado correctamente');
      setAjusteModalOpen(false);
      loadProductos();
      
    } catch (error) {
      console.error('Error en ajuste:', error);
      toast.error(error.response?.data?.detail || 'Error al realizar ajuste');
    } finally {
      setAjusteSubmitting(false);
    }
  };

  const getStockBadge = (producto) => {
    if (!producto.controla_inventario) return null;
    
    const stock = producto.existencia_total || 0;
    const min = producto.existencia_minima || 0;
    
    if (stock === 0) {
      return <Badge variant="destructive">Sin Stock</Badge>;
    } else if (stock < min) {
      return <Badge variant="warning" className="bg-amber-100 text-amber-800">Bajo Mínimo</Badge>;
    } else {
      return <Badge variant="secondary" className="bg-green-100 text-green-800">{stock} und</Badge>;
    }
  };

  const getTipoBadge = (tipo) => {
    const styles = {
      producto: 'bg-blue-100 text-blue-800',
      servicio: 'bg-purple-100 text-purple-800',
      insumo: 'bg-orange-100 text-orange-800'
    };
    return <Badge className={styles[tipo] || 'bg-gray-100'}>{tipo}</Badge>;
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <Layout>
      <div className="space-y-6" data-testid="productos-inventario">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Catálogo de Productos</h1>
            <p className="text-gray-500">{total} productos en el sistema</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={downloadTemplate} data-testid="btn-descargar-plantilla">
              <Download className="w-4 h-4 mr-2" />
              Plantilla
            </Button>
            <Button variant="outline" onClick={() => setImportModalOpen(true)} data-testid="btn-importar-excel">
              <Upload className="w-4 h-4 mr-2" />
              Importar Excel
            </Button>
            <Button onClick={() => handleOpenModal()} data-testid="btn-nuevo-producto">
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Producto
            </Button>
          </div>
        </div>

        {/* Filtros */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por nombre, código o genérico..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  className="pl-10"
                  data-testid="search-productos"
                />
              </div>
              
              <Select value={categoriaFilter} onValueChange={(v) => { setCategoriaFilter(v); setPage(1); }}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Categoría" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las categorías</SelectItem>
                  {categorias.map(cat => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={tipoFilter} onValueChange={(v) => { setTipoFilter(v); setPage(1); }}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  <SelectItem value="producto">Producto</SelectItem>
                  <SelectItem value="servicio">Servicio</SelectItem>
                  <SelectItem value="insumo">Insumo</SelectItem>
                </SelectContent>
              </Select>
              
              <Button
                variant={bajoMinimoFilter ? "default" : "outline"}
                size="sm"
                onClick={() => { setBajoMinimoFilter(!bajoMinimoFilter); setPage(1); }}
              >
                <AlertTriangle className="w-4 h-4 mr-1" />
                Bajo Mínimo
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla de productos */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : productos.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No se encontraron productos</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoría</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Presentación</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Existencia</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Compra</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">P. Venta</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Margen</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {productos.map((producto) => {
                      // Usar precio_compra para calcular margen, fallback a costo_promedio
                      const precioCompra = producto.precio_compra || producto.costo_promedio || 0;
                      const margen = producto.precio_venta > 0 && precioCompra > 0
                        ? ((producto.precio_venta - precioCompra) / producto.precio_venta * 100).toFixed(1)
                        : '-';
                      
                      return (
                        <tr key={producto.id} className="hover:bg-gray-50" data-testid={`producto-row-${producto.id}`}>
                          <td className="px-4 py-3 text-sm font-mono">{producto.codigo}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-start gap-2">
                              <div>
                                <p className="text-sm font-medium">{producto.nombre}</p>
                                {producto.nombre_generico && (
                                  <p className="text-xs text-gray-500">{producto.nombre_generico}</p>
                                )}
                              </div>
                              {producto.es_sociedad && (
                                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 text-xs">
                                  👥 Sociedad
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">{producto.categoria_nombre || '-'}</td>
                          <td className="px-4 py-3">{getTipoBadge(producto.tipo)}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{producto.presentacion || '-'}</td>
                          <td className="px-4 py-3 text-right">{getStockBadge(producto)}</td>
                          <td className="px-4 py-3 text-right text-sm text-gray-600">
                            {precioCompra > 0 ? formatCurrency(precioCompra) : '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-sm font-medium">{formatCurrency(producto.precio_venta)}</td>
                          <td className="px-4 py-3 text-right text-sm">
                            {margen !== '-' ? (
                              <span className={parseFloat(margen) >= 30 ? 'text-green-600 font-medium' : parseFloat(margen) >= 15 ? 'text-amber-600' : 'text-red-600'}>
                                {margen}%
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {producto.controla_inventario && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => abrirEntradaRapida(producto)}
                                  className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                  title="Entrada rápida"
                                  data-testid={`btn-entrada-${producto.id}`}
                                >
                                  <ArrowDownToLine className="w-4 h-4" />
                                </Button>
                              )}
                              {/* Botón de Ajuste de Inventario - Solo admin/superadmin */}
                              {producto.controla_inventario && isAdminOrSuperAdmin && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleOpenAjuste(producto)}
                                  className="text-purple-600 hover:text-purple-700 hover:bg-purple-50"
                                  title="Ajustar existencia"
                                  data-testid={`btn-ajuste-${producto.id}`}
                                >
                                  <Package className="w-4 h-4" />
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenModal(producto)}
                                data-testid={`btn-edit-${producto.id}`}
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              {isSuperAdmin && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleToggleActive(producto)}
                                    className={producto.activo 
                                      ? "text-orange-600 hover:text-orange-700 hover:bg-orange-50" 
                                      : "text-green-600 hover:text-green-700 hover:bg-green-50"}
                                    title={producto.activo ? "Desactivar producto" : "Activar producto"}
                                    data-testid={`btn-toggle-${producto.id}`}
                                  >
                                    {producto.activo ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteClick(producto)}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                    title="Eliminar producto"
                                    data-testid={`btn-delete-${producto.id}`}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Mostrando {((page - 1) * limit) + 1} - {Math.min(page * limit, total)} de {total}
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
                Página {page} de {totalPages}
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

        {/* Modal de Producto */}
        <Dialog open={modalOpen} onOpenChange={setModalOpen}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingProduct ? 'Editar Producto' : 'Nuevo Producto'}
              </DialogTitle>
            </DialogHeader>
            
            <div className="grid grid-cols-2 gap-4 py-4">
              <div className="space-y-2">
                <Label>Código (auto si vacío)</Label>
                <Input
                  value={formData.codigo}
                  onChange={(e) => setFormData({ ...formData, codigo: e.target.value })}
                  placeholder="PROD-00001"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Código de Barras</Label>
                <Input
                  value={formData.codigo_barras}
                  onChange={(e) => setFormData({ ...formData, codigo_barras: e.target.value })}
                  placeholder="7501234567890"
                />
              </div>
              
              <div className="space-y-2 col-span-2">
                <Label>Nombre *</Label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Nombre del producto"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Nombre Genérico</Label>
                <Input
                  value={formData.nombre_generico}
                  onChange={(e) => setFormData({ ...formData, nombre_generico: e.target.value })}
                  placeholder="Principio activo"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Categoría</Label>
                <Select 
                  value={formData.categoria_id} 
                  onValueChange={(v) => setFormData({ ...formData, categoria_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    {categorias.map(cat => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select 
                  value={formData.tipo} 
                  onValueChange={(v) => {
                    // Si cambia a servicio, desactivar controles de inventario automáticamente
                    if (v === 'servicio') {
                      setFormData({ 
                        ...formData, 
                        tipo: v, 
                        controla_inventario: false, 
                        controla_lotes: false,
                        existencia_minima: 0,
                        existencia_maxima: 0
                      });
                    } else {
                      setFormData({ ...formData, tipo: v });
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="producto">Producto</SelectItem>
                    <SelectItem value="servicio">Servicio</SelectItem>
                    <SelectItem value="insumo">Insumo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Presentación</Label>
                <Input
                  value={formData.presentacion}
                  onChange={(e) => setFormData({ ...formData, presentacion: e.target.value })}
                  placeholder="Frasco 5ml, Caja 30 tabs..."
                />
              </div>
              
              <div className="space-y-2">
                <Label>Unidad de Medida</Label>
                <Select 
                  value={formData.unidad_medida} 
                  onValueChange={(v) => setFormData({ ...formData, unidad_medida: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unidad">Unidad</SelectItem>
                    <SelectItem value="frasco">Frasco</SelectItem>
                    <SelectItem value="caja">Caja</SelectItem>
                    <SelectItem value="par">Par</SelectItem>
                    <SelectItem value="jeringa">Jeringa</SelectItem>
                    <SelectItem value="servicio">Servicio</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Precio de Compra (GTQ)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.precio_compra}
                  onChange={(e) => setFormData({ ...formData, precio_compra: parseFloat(e.target.value) || 0 })}
                  data-testid="input-precio-compra"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Precio de Venta (GTQ)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.precio_venta}
                  onChange={(e) => setFormData({ ...formData, precio_venta: parseFloat(e.target.value) || 0 })}
                  data-testid="input-precio-venta"
                />
              </div>
              
              {/* Indicador de Margen en Tiempo Real */}
              {formData.precio_compra > 0 && formData.precio_venta > 0 && (
                <div className="col-span-2">
                  <div className={`p-3 rounded-lg border ${
                    formData.precio_venta > formData.precio_compra 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700">Margen de Ganancia:</span>
                        <span className={`text-lg font-bold ${
                          formData.precio_venta > formData.precio_compra 
                            ? ((formData.precio_venta - formData.precio_compra) / formData.precio_venta * 100) >= 30
                              ? 'text-green-600'
                              : 'text-amber-600'
                            : 'text-red-600'
                        }`}>
                          {formData.precio_venta > formData.precio_compra 
                            ? `${((formData.precio_venta - formData.precio_compra) / formData.precio_venta * 100).toFixed(1)}%`
                            : 'Precio venta menor que compra'
                          }
                        </span>
                      </div>
                      {formData.precio_venta > formData.precio_compra && (
                        <div className="text-sm text-gray-600">
                          Ganancia: <span className="font-semibold text-green-700">
                            Q{(formData.precio_venta - formData.precio_compra).toFixed(2)}
                          </span> por unidad
                        </div>
                      )}
                    </div>
                    {formData.precio_venta > formData.precio_compra && (
                      <div className="mt-2 text-xs text-gray-500">
                        Markup: {((formData.precio_venta - formData.precio_compra) / formData.precio_compra * 100).toFixed(1)}% sobre costo
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {formData.tipo !== 'servicio' && (
                <>
                  <div className="space-y-2">
                    <Label>Existencia Mínima</Label>
                    <Input
                      type="number"
                      value={formData.existencia_minima}
                      onChange={(e) => setFormData({ ...formData, existencia_minima: parseInt(e.target.value) || 0 })}
                      disabled={!isAdminOrSuperAdmin}
                      className={!isAdminOrSuperAdmin ? 'bg-gray-100 cursor-not-allowed' : ''}
                    />
                    {!isAdminOrSuperAdmin && (
                      <p className="text-xs text-gray-500">Solo administradores pueden modificar</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Existencia Máxima</Label>
                    <Input
                      type="number"
                      value={formData.existencia_maxima}
                      onChange={(e) => setFormData({ ...formData, existencia_maxima: parseInt(e.target.value) || 0 })}
                      disabled={!isAdminOrSuperAdmin}
                      className={!isAdminOrSuperAdmin ? 'bg-gray-100 cursor-not-allowed' : ''}
                    />
                    {!isAdminOrSuperAdmin && (
                      <p className="text-xs text-gray-500">Solo administradores pueden modificar</p>
                    )}
                  </div>
                </>
              )}
              
              <div className="col-span-2 space-y-2">
                <Label>Descripción</Label>
                <Textarea
                  value={formData.descripcion}
                  onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                  rows={2}
                />
              </div>
              
              {formData.tipo !== 'servicio' && (
                <div className="col-span-2 flex flex-wrap gap-6 pt-2 border-t">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="controla_inventario"
                      checked={formData.controla_inventario}
                      onCheckedChange={(v) => setFormData({ ...formData, controla_inventario: v })}
                    />
                    <Label htmlFor="controla_inventario">Controla Inventario</Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="controla_lotes"
                      checked={formData.controla_lotes}
                      onCheckedChange={(v) => setFormData({ ...formData, controla_lotes: v })}
                    />
                    <Label htmlFor="controla_lotes">Controla Lotes</Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="requiere_receta"
                      checked={formData.requiere_receta}
                      onCheckedChange={(v) => setFormData({ ...formData, requiere_receta: v })}
                    />
                    <Label htmlFor="requiere_receta">Requiere Receta</Label>
                  </div>
                </div>
              )}
              
              {/* Switches de Sociedad y Activo - siempre visibles */}
              <div className="col-span-2 flex flex-wrap gap-6 pt-2 border-t">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="es_sociedad"
                    checked={formData.es_sociedad}
                    onCheckedChange={(v) => setFormData({ ...formData, es_sociedad: v, sociedad_id: v ? formData.sociedad_id : '' })}
                  />
                  <Label htmlFor="es_sociedad" className="flex items-center gap-1">
                    <span className="text-purple-600">👥</span> Sociedad
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Switch
                    id="activo"
                    checked={formData.activo}
                    onCheckedChange={(v) => setFormData({ ...formData, activo: v })}
                  />
                  <Label htmlFor="activo">Activo</Label>
                </div>
              </div>
              
              {/* Selector de Sociedad - aparece cuando es_sociedad está activo */}
              {formData.es_sociedad && (
                <div className="col-span-2 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                  <Label className="text-purple-700 font-medium mb-2 block">
                    Asignar a Sociedad Médica
                  </Label>
                  <Select 
                    value={formData.sociedad_id} 
                    onValueChange={(v) => setFormData({ ...formData, sociedad_id: v })}
                  >
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Selecciona una sociedad..." />
                    </SelectTrigger>
                    <SelectContent>
                      {sociedades.length === 0 ? (
                        <SelectItem value="__empty__" disabled>No hay sociedades creadas</SelectItem>
                      ) : (
                        sociedades.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            <span className="flex items-center gap-2">
                              <span className={`w-2 h-2 rounded-full ${
                                s.color === 'blue' ? 'bg-blue-500' :
                                s.color === 'green' ? 'bg-green-500' :
                                s.color === 'red' ? 'bg-red-500' :
                                s.color === 'orange' ? 'bg-orange-500' :
                                s.color === 'teal' ? 'bg-teal-500' :
                                s.color === 'pink' ? 'bg-pink-500' :
                                'bg-purple-500'
                              }`}></span>
                              {s.nombre}
                            </span>
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {sociedades.length === 0 && (
                    <p className="text-xs text-purple-600 mt-2">
                      Debes crear sociedades en el menú Inventario → Sociedades para asignar productos.
                    </p>
                  )}
                </div>
              )}
              
              {formData.controla_lotes && (
                <div className="col-span-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                  <AlertTriangle className="w-4 h-4 inline mr-2" />
                  Este producto requiere número de lote y fecha de vencimiento en cada entrada.
                </div>
              )}
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setModalOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit}>
                {editingProduct ? 'Guardar Cambios' : 'Crear Producto'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal de Entrada Rápida */}
        <Dialog open={entradaModalOpen} onOpenChange={setEntradaModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ArrowDownToLine className="w-5 h-5 text-blue-600" />
                Entrada Rápida
              </DialogTitle>
              <DialogDescription>
                Agregar unidades al inventario
              </DialogDescription>
            </DialogHeader>
            
            {productoParaEntrada && (
              <div className="space-y-4">
                {/* Info del producto */}
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="font-medium text-slate-800">{productoParaEntrada.nombre}</p>
                  <p className="text-sm text-slate-500">{productoParaEntrada.codigo}</p>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span>Stock actual: <strong>{productoParaEntrada.existencia_total || 0}</strong></span>
                    <span>Costo prom: <strong>{formatCurrency(productoParaEntrada.costo_promedio)}</strong></span>
                  </div>
                </div>

                {/* Bodega */}
                <div>
                  <Label>Bodega destino *</Label>
                  <Select 
                    value={entradaData.bodega_id} 
                    onValueChange={(v) => setEntradaData({...entradaData, bodega_id: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar bodega..." />
                    </SelectTrigger>
                    <SelectContent>
                      {bodegas.filter(b => b.activo).map(b => (
                        <SelectItem key={b.id} value={b.id}>{b.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Cantidad y Costo */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Cantidad *</Label>
                    <Input
                      type="number"
                      min="1"
                      value={entradaData.cantidad}
                      onChange={(e) => setEntradaData({...entradaData, cantidad: parseInt(e.target.value) || 0})}
                      className="text-center font-bold text-lg"
                      data-testid="entrada-cantidad"
                    />
                  </div>
                  <div>
                    <Label>Costo Unitario (Q)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={entradaData.costo_unitario}
                      onChange={(e) => setEntradaData({...entradaData, costo_unitario: parseFloat(e.target.value) || 0})}
                      data-testid="entrada-costo"
                    />
                  </div>
                </div>

                {/* Lote y Vencimiento (solo si controla lotes) */}
                {productoParaEntrada.controla_lotes && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
                    <p className="text-sm text-amber-800 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Este producto requiere información de lote
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Número de Lote *</Label>
                        <Input
                          value={entradaData.numero_lote}
                          onChange={(e) => setEntradaData({...entradaData, numero_lote: e.target.value})}
                          placeholder="Ej: LOT-2024-001"
                          data-testid="entrada-lote"
                        />
                      </div>
                      <div>
                        <Label>Fecha Vencimiento *</Label>
                        <Input
                          type="date"
                          value={entradaData.fecha_vencimiento}
                          onChange={(e) => setEntradaData({...entradaData, fecha_vencimiento: e.target.value})}
                          data-testid="entrada-vencimiento"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Observaciones */}
                <div>
                  <Label>Observaciones (opcional)</Label>
                  <Textarea
                    value={entradaData.observaciones}
                    onChange={(e) => setEntradaData({...entradaData, observaciones: e.target.value})}
                    placeholder="Notas adicionales..."
                    rows={2}
                  />
                </div>

                {/* Resumen */}
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>Resumen:</strong> Entrada de <strong>{entradaData.cantidad}</strong> unidades 
                    {entradaData.costo_unitario > 0 && (
                      <> a <strong>{formatCurrency(entradaData.costo_unitario)}</strong> c/u = <strong>{formatCurrency(entradaData.cantidad * entradaData.costo_unitario)}</strong></>
                    )}
                  </p>
                </div>
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setEntradaModalOpen(false)}>
                Cancelar
              </Button>
              <Button 
                onClick={handleEntradaRapida} 
                disabled={entradaSubmitting}
                className="bg-blue-600 hover:bg-blue-700"
                data-testid="btn-confirmar-entrada"
              >
                {entradaSubmitting ? 'Registrando...' : 'Registrar Entrada'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal de Confirmación Eliminar (Solo SuperAdmin) */}
        <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Eliminar Producto
              </DialogTitle>
              <DialogDescription>
                Esta acción no se puede deshacer. El producto será eliminado permanentemente del sistema.
              </DialogDescription>
            </DialogHeader>
            
            {productToDelete && (
              <div className="space-y-3">
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="font-medium text-red-800">{productToDelete.nombre}</p>
                  <p className="text-sm text-red-600">Código: {productToDelete.codigo || 'Sin código'}</p>
                </div>
                
                {productToDelete.existencia_total > 0 && (
                  <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg">
                    <p className="font-semibold text-amber-800 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      ¡ATENCIÓN! Producto con inventario
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      Este producto tiene <strong>{productToDelete.existencia_total} unidades</strong> en stock 
                      y movimientos registrados en el kardex.
                    </p>
                    <div className="mt-3 p-3 bg-amber-100 rounded text-xs text-amber-800">
                      <p className="font-medium mb-1">Si elimina este producto:</p>
                      <ul className="list-disc list-inside space-y-1">
                        <li>Se eliminarán TODOS los movimientos del kardex</li>
                        <li>Se eliminarán las existencias en todas las bodegas</li>
                        <li>Se eliminarán los lotes asociados</li>
                        <li>Los reportes históricos pueden verse afectados</li>
                      </ul>
                    </div>
                  </div>
                )}
                
                {productToDelete.existencia_total === 0 && (
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600">
                    Este producto no tiene existencias. Se eliminará de forma segura.
                  </div>
                )}
              </div>
            )}
            
            <DialogFooter className="flex gap-2 sm:gap-2">
              <Button variant="outline" onClick={() => setDeleteModalOpen(false)}>
                Cancelar
              </Button>
              {productToDelete?.existencia_total > 0 ? (
                <>
                  <Button 
                    variant="outline"
                    onClick={() => handleToggleActive(productToDelete)}
                    className="border-orange-300 text-orange-600 hover:bg-orange-50"
                  >
                    <PowerOff className="w-4 h-4 mr-1" />
                    Solo Desactivar
                  </Button>
                  <Button 
                    variant="destructive"
                    onClick={() => handleDeleteConfirm(true)}
                    disabled={deleting}
                    data-testid="btn-confirmar-eliminar-forzado"
                  >
                    {deleting ? 'Eliminando...' : '🗑️ Eliminar Todo'}
                  </Button>
                </>
              ) : (
                <Button 
                  variant="destructive"
                  onClick={() => handleDeleteConfirm(false)}
                  disabled={deleting}
                  data-testid="btn-confirmar-eliminar"
                >
                  {deleting ? 'Eliminando...' : 'Eliminar'}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal de Importar Excel */}
        <Dialog open={importModalOpen} onOpenChange={setImportModalOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5" />
                Importar Productos desde Excel
              </DialogTitle>
              <DialogDescription>
                Suba un archivo Excel (.xlsx, .xls) o CSV con los productos a importar.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Instrucciones */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                <p className="font-medium text-blue-800 mb-2">Columnas requeridas:</p>
                <ul className="text-blue-700 space-y-1 text-xs">
                  <li>• <strong>nombre</strong> (obligatorio)</li>
                  <li>• codigo, codigo_barras, nombre_generico, descripcion</li>
                  <li>• categoria, tipo (producto/servicio/insumo), presentacion</li>
                  <li>• unidad_medida, precio_compra, precio_venta, existencia_minima, existencia_maxima</li>
                  <li>• controla_inventario, controla_lotes, requiere_receta, afecto_iva (true/false)</li>
                </ul>
                <Button 
                  variant="link" 
                  size="sm" 
                  className="p-0 h-auto mt-2"
                  onClick={downloadTemplate}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar plantilla de ejemplo
                </Button>
              </div>

              {/* Selector de archivo */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="import-file-input"
                  data-testid="input-import-file"
                />
                <label 
                  htmlFor="import-file-input" 
                  className="cursor-pointer"
                >
                  <Upload className="w-10 h-10 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600">
                    {importFile ? (
                      <span className="text-green-600 font-medium">{importFile.name}</span>
                    ) : (
                      <>Click para seleccionar archivo o arrástrelo aquí</>
                    )}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">Excel (.xlsx, .xls) o CSV</p>
                </label>
              </div>

              {/* Preview */}
              {importPreview.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 border-b">
                    <p className="text-sm font-medium">Vista previa ({importPreview.length} productos)</p>
                  </div>
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-2 py-1 text-left">Código</th>
                          <th className="px-2 py-1 text-left">Nombre</th>
                          <th className="px-2 py-1 text-left">Tipo</th>
                          <th className="px-2 py-1 text-right">Precio</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {importPreview.slice(0, 10).map((item, idx) => (
                          <tr key={idx}>
                            <td className="px-2 py-1 font-mono">{item.codigo || '-'}</td>
                            <td className="px-2 py-1">{item.nombre}</td>
                            <td className="px-2 py-1">{item.tipo || 'producto'}</td>
                            <td className="px-2 py-1 text-right">{formatCurrency(item.precio_venta || 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {importPreview.length > 10 && (
                      <p className="text-xs text-gray-500 p-2 text-center">
                        ... y {importPreview.length - 10} más
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Errores */}
              {importErrors.length > 0 && (
                <div className="border border-red-200 bg-red-50 rounded-lg p-3">
                  <p className="text-sm font-medium text-red-800 mb-2">Errores encontrados:</p>
                  <ul className="text-xs text-red-700 space-y-1 max-h-32 overflow-y-auto">
                    {importErrors.map((err, idx) => (
                      <li key={idx}>• Fila {err.row}: {err.message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => {
                  setImportModalOpen(false);
                  setImportFile(null);
                  setImportPreview([]);
                  setImportErrors([]);
                }}
              >
                Cancelar
              </Button>
              <Button 
                onClick={handleImportSubmit}
                disabled={importing || !importFile || importPreview.length === 0}
                data-testid="btn-confirmar-importar"
              >
                {importing ? 'Importando...' : `Importar ${importPreview.length} Productos`}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal de Ajuste de Inventario */}
        <Dialog open={ajusteModalOpen} onOpenChange={setAjusteModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Package className="w-5 h-5 text-purple-600" />
                Ajustar Existencia
              </DialogTitle>
              <DialogDescription>
                Modifique la cantidad en inventario de {productoParaAjuste?.nombre}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Información del producto */}
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="font-medium text-gray-900">{productoParaAjuste?.nombre}</p>
                <p className="text-sm text-gray-600">Código: {productoParaAjuste?.codigo}</p>
                <p className="text-sm text-purple-600 font-medium mt-1">
                  Existencia actual: {productoParaAjuste?.existencia_total || 0} unidades
                </p>
              </div>

              {/* Bodega */}
              <div className="space-y-2">
                <Label>Bodega *</Label>
                <Select 
                  value={ajusteData.bodega_id} 
                  onValueChange={(v) => setAjusteData({ ...ajusteData, bodega_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar bodega" />
                  </SelectTrigger>
                  <SelectContent>
                    {bodegas.map(b => (
                      <SelectItem key={b.id} value={b.id}>{b.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Nueva cantidad */}
              <div className="space-y-2">
                <Label>Nueva cantidad *</Label>
                <Input
                  type="number"
                  min="0"
                  value={ajusteData.cantidad_nueva}
                  onChange={(e) => setAjusteData({ ...ajusteData, cantidad_nueva: parseInt(e.target.value) || 0 })}
                  className="text-lg font-medium"
                />
                {productoParaAjuste && (
                  <p className={`text-sm ${
                    ajusteData.cantidad_nueva > (productoParaAjuste?.existencia_total || 0) 
                      ? 'text-green-600' 
                      : ajusteData.cantidad_nueva < (productoParaAjuste?.existencia_total || 0)
                        ? 'text-red-600'
                        : 'text-gray-500'
                  }`}>
                    {ajusteData.cantidad_nueva > (productoParaAjuste?.existencia_total || 0) 
                      ? `↑ Aumentará ${ajusteData.cantidad_nueva - (productoParaAjuste?.existencia_total || 0)} unidades`
                      : ajusteData.cantidad_nueva < (productoParaAjuste?.existencia_total || 0)
                        ? `↓ Disminuirá ${(productoParaAjuste?.existencia_total || 0) - ajusteData.cantidad_nueva} unidades`
                        : 'Sin cambios'}
                  </p>
                )}
              </div>

              {/* Motivo */}
              <div className="space-y-2">
                <Label>Motivo del ajuste *</Label>
                <Textarea
                  value={ajusteData.motivo}
                  onChange={(e) => setAjusteData({ ...ajusteData, motivo: e.target.value })}
                  placeholder="Ej: Ajuste por inventario físico, corrección de error, etc."
                  rows={2}
                />
                <p className="text-xs text-gray-500">Mínimo 5 caracteres. Este registro quedará en el historial.</p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAjusteModalOpen(false)}>
                Cancelar
              </Button>
              <Button 
                onClick={handleAjusteSubmit}
                disabled={ajusteSubmitting || !ajusteData.motivo || ajusteData.motivo.length < 5}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {ajusteSubmitting ? 'Guardando...' : 'Realizar Ajuste'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Productos;
