// /app/frontend/src/pages/inventario/Productos.js
// Catálogo de productos del módulo de Inventario

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import {
  Search, Plus, Edit, Package, AlertTriangle, Filter, ChevronLeft, ChevronRight
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { toast } from 'sonner';

const Productos = () => {
  const [loading, setLoading] = useState(true);
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  
  // Filtros
  const [search, setSearch] = useState('');
  const [categoriaFilter, setCategoriaFilter] = useState('all');
  const [tipoFilter, setTipoFilter] = useState('all');
  const [bajoMinimoFilter, setBajoMinimoFilter] = useState(false);
  
  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
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
  }, [loadCategorias]);

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
          <Button onClick={() => handleOpenModal()} data-testid="btn-nuevo-producto">
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Producto
          </Button>
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
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
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
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Prom.</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Precio Venta</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Margen</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {productos.map((producto) => {
                      const margen = producto.precio_venta > 0 && producto.costo_promedio > 0
                        ? ((producto.precio_venta - producto.costo_promedio) / producto.precio_venta * 100).toFixed(1)
                        : '-';
                      
                      return (
                        <tr key={producto.id} className="hover:bg-gray-50" data-testid={`producto-row-${producto.id}`}>
                          <td className="px-4 py-3 text-sm font-mono">{producto.codigo}</td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="text-sm font-medium">{producto.nombre}</p>
                              {producto.nombre_generico && (
                                <p className="text-xs text-gray-500">{producto.nombre_generico}</p>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm">{producto.categoria_nombre || '-'}</td>
                          <td className="px-4 py-3">{getTipoBadge(producto.tipo)}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{producto.presentacion || '-'}</td>
                          <td className="px-4 py-3 text-right">{getStockBadge(producto)}</td>
                          <td className="px-4 py-3 text-right text-sm">{formatCurrency(producto.costo_promedio)}</td>
                          <td className="px-4 py-3 text-right text-sm font-medium">{formatCurrency(producto.precio_venta)}</td>
                          <td className="px-4 py-3 text-right text-sm">
                            {margen !== '-' ? (
                              <span className={parseFloat(margen) >= 30 ? 'text-green-600' : 'text-amber-600'}>
                                {margen}%
                              </span>
                            ) : '-'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenModal(producto)}
                              data-testid={`btn-edit-${producto.id}`}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
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
                  onValueChange={(v) => setFormData({ ...formData, tipo: v })}
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
                <Label>Precio de Venta (GTQ)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.precio_venta}
                  onChange={(e) => setFormData({ ...formData, precio_venta: parseFloat(e.target.value) || 0 })}
                />
              </div>
              
              {formData.tipo !== 'servicio' && (
                <>
                  <div className="space-y-2">
                    <Label>Existencia Mínima</Label>
                    <Input
                      type="number"
                      value={formData.existencia_minima}
                      onChange={(e) => setFormData({ ...formData, existencia_minima: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Existencia Máxima</Label>
                    <Input
                      type="number"
                      value={formData.existencia_maxima}
                      onChange={(e) => setFormData({ ...formData, existencia_maxima: parseInt(e.target.value) || 0 })}
                    />
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
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="activo"
                      checked={formData.activo}
                      onCheckedChange={(v) => setFormData({ ...formData, activo: v })}
                    />
                    <Label htmlFor="activo">Activo</Label>
                  </div>
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
      </div>
    </Layout>
  );
};

export default Productos;
