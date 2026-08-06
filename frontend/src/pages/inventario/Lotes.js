// /app/frontend/src/pages/inventario/Lotes.js
// Gestión de Lotes y Vencimientos

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
import {
  Search, AlertTriangle, Clock, AlertCircle, Trash2, Package
} from 'lucide-react';
import { inventarioApi, formatCurrency } from '../../services/api';
import { toast } from 'sonner';

const Lotes = () => {
  const [loading, setLoading] = useState(true);
  const [lotes, setLotes] = useState([]);
  const [bodegas, setBodegas] = useState([]);
  
  // Filtros
  const [search, setSearch] = useState('');
  const [bodegaFilter, setBodegaFilter] = useState('all');
  const [estadoFilter, setEstadoFilter] = useState('all');
  
  // Modal de baja
  const [bajaModalOpen, setBajaModalOpen] = useState(false);
  const [selectedLote, setSelectedLote] = useState(null);
  const [motivoBaja, setMotivoBaja] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [lotesRes, bodegasRes] = await Promise.all([
        inventarioApi.getLotes({
          bodega_id: bodegaFilter !== 'all' ? bodegaFilter : undefined,
          estado: estadoFilter !== 'all' ? estadoFilter : undefined
        }),
        inventarioApi.getBodegas()
      ]);
      
      let lotesData = lotesRes.data.data || [];
      
      // Filtrar por búsqueda local
      if (search) {
        const searchLower = search.toLowerCase();
        lotesData = lotesData.filter(l => 
          l.producto_nombre?.toLowerCase().includes(searchLower) ||
          l.numero_lote?.toLowerCase().includes(searchLower)
        );
      }
      
      setLotes(lotesData);
      setBodegas(bodegasRes.data.data || []);
    } catch (error) {
      console.error('Error cargando lotes:', error);
      toast.error('Error al cargar lotes');
    } finally {
      setLoading(false);
    }
  }, [search, bodegaFilter, estadoFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getVencimientoBadge = (lote) => {
    const dias = lote.dias_para_vencer;
    
    if (dias === null || dias === undefined) {
      return <Badge variant="secondary">Sin fecha</Badge>;
    }
    
    if (dias < 0) {
      return <Badge variant="destructive">VENCIDO ({Math.abs(dias)} días)</Badge>;
    } else if (dias <= 30) {
      return <Badge className="bg-red-100 text-red-800">Vence en {dias} días</Badge>;
    } else if (dias <= 60) {
      return <Badge className="bg-orange-100 text-orange-800">Vence en {dias} días</Badge>;
    } else if (dias <= 90) {
      return <Badge className="bg-amber-100 text-amber-800">Vence en {dias} días</Badge>;
    } else {
      return <Badge className="bg-green-100 text-green-800">Vence en {dias} días</Badge>;
    }
  };

  const handleOpenBaja = (lote) => {
    setSelectedLote(lote);
    setMotivoBaja('');
    setBajaModalOpen(true);
  };

  const handleBaja = async () => {
    if (!motivoBaja.trim() || motivoBaja.length < 5) {
      toast.error('El motivo debe tener al menos 5 caracteres');
      return;
    }

    try {
      await inventarioApi.darBajaLote(selectedLote.id, { motivo: motivoBaja });
      toast.success('Lote dado de baja exitosamente');
      setBajaModalOpen(false);
      loadData();
    } catch (error) {
      console.error('Error dando de baja:', error);
      toast.error(error.response?.data?.detail || 'Error al dar de baja el lote');
    }
  };

  // Estadísticas
  const stats = {
    total: lotes.length,
    vencidos: lotes.filter(l => l.dias_para_vencer !== null && l.dias_para_vencer < 0).length,
    por30: lotes.filter(l => l.dias_para_vencer !== null && l.dias_para_vencer >= 0 && l.dias_para_vencer <= 30).length,
    por60: lotes.filter(l => l.dias_para_vencer !== null && l.dias_para_vencer > 30 && l.dias_para_vencer <= 60).length,
    por90: lotes.filter(l => l.dias_para_vencer !== null && l.dias_para_vencer > 60 && l.dias_para_vencer <= 90).length,
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="lotes-inventario">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lotes y Vencimientos</h1>
          <p className="text-gray-500">Control de lotes con fechas de vencimiento</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Package className="w-5 h-5 text-gray-500" />
                <span className="text-2xl font-bold">{stats.total}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Total Lotes</p>
            </CardContent>
          </Card>
          
          <Card className={stats.vencidos > 0 ? 'border-red-200 bg-red-50' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <AlertCircle className={`w-5 h-5 ${stats.vencidos > 0 ? 'text-red-500' : 'text-gray-400'}`} />
                <span className="text-2xl font-bold">{stats.vencidos}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Vencidos</p>
            </CardContent>
          </Card>
          
          <Card className={stats.por30 > 0 ? 'border-red-200 bg-red-50/50' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Clock className={`w-5 h-5 ${stats.por30 > 0 ? 'text-red-500' : 'text-gray-400'}`} />
                <span className="text-2xl font-bold">{stats.por30}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Vencen en 30d</p>
            </CardContent>
          </Card>
          
          <Card className={stats.por60 > 0 ? 'border-orange-200 bg-orange-50/50' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Clock className={`w-5 h-5 ${stats.por60 > 0 ? 'text-orange-500' : 'text-gray-400'}`} />
                <span className="text-2xl font-bold">{stats.por60}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Vencen en 60d</p>
            </CardContent>
          </Card>
          
          <Card className={stats.por90 > 0 ? 'border-amber-200 bg-amber-50/50' : ''}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Clock className={`w-5 h-5 ${stats.por90 > 0 ? 'text-amber-500' : 'text-gray-400'}`} />
                <span className="text-2xl font-bold">{stats.por90}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Vencen en 90d</p>
            </CardContent>
          </Card>
        </div>

        {/* Filtros */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Buscar por producto o número de lote..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <Select value={bodegaFilter} onValueChange={setBodegaFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Bodega" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las bodegas</SelectItem>
                  {bodegas.map(b => (
                    <SelectItem key={b.id} value={b.id}>{b.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={estadoFilter} onValueChange={setEstadoFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="disponible">Disponible</SelectItem>
                  <SelectItem value="agotado">Agotado</SelectItem>
                  <SelectItem value="vencido">Vencido</SelectItem>
                  <SelectItem value="bloqueado">Bloqueado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Tabla de lotes */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
              </div>
            ) : lotes.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No se encontraron lotes</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nº Lote</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bodega</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Vencimiento</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Disponible</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Unit.</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Valor</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {lotes.map((lote) => {
                      const valor = lote.cantidad_disponible * lote.costo_unitario;
                      const esVencido = lote.dias_para_vencer !== null && lote.dias_para_vencer < 0;
                      
                      return (
                        <tr 
                          key={lote.id} 
                          className={`hover:bg-gray-50 ${esVencido ? 'bg-red-50/50' : ''}`}
                          data-testid={`lote-row-${lote.id}`}
                        >
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium">{lote.producto_nombre}</p>
                          </td>
                          <td className="px-4 py-3 text-sm font-mono">{lote.numero_lote}</td>
                          <td className="px-4 py-3 text-sm">{lote.bodega_nombre}</td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex flex-col items-center gap-1">
                              <span className="text-sm">{lote.fecha_vencimiento}</span>
                              {getVencimientoBadge(lote)}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-sm font-medium">
                              {lote.cantidad_disponible} / {lote.cantidad_inicial}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-sm">{formatCurrency(lote.costo_unitario)}</td>
                          <td className="px-4 py-3 text-right text-sm font-medium">{formatCurrency(valor)}</td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant={lote.estado === 'disponible' ? 'secondary' : 'outline'}>
                              {lote.estado}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {lote.cantidad_disponible > 0 && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => handleOpenBaja(lote)}
                                data-testid={`btn-baja-${lote.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            )}
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

        {/* Modal de Baja */}
        <Dialog open={bajaModalOpen} onOpenChange={setBajaModalOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Dar de Baja Lote
              </DialogTitle>
            </DialogHeader>
            
            {selectedLote && (
              <div className="py-4 space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                  <p><strong>Producto:</strong> {selectedLote.producto_nombre}</p>
                  <p><strong>Nº Lote:</strong> {selectedLote.numero_lote}</p>
                  <p><strong>Cantidad a dar de baja:</strong> {selectedLote.cantidad_disponible} unidades</p>
                  <p><strong>Valor:</strong> {formatCurrency(selectedLote.cantidad_disponible * selectedLote.costo_unitario)}</p>
                </div>
                
                <div className="space-y-2">
                  <Label>Motivo de la baja *</Label>
                  <Textarea
                    value={motivoBaja}
                    onChange={(e) => setMotivoBaja(e.target.value)}
                    placeholder="Describa el motivo de la baja (mínimo 5 caracteres)..."
                    rows={3}
                  />
                </div>
                
                <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded">
                  Esta acción generará un movimiento de baja en el kardex y no se puede deshacer.
                </p>
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setBajaModalOpen(false)}>
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleBaja}>
                Confirmar Baja
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Lotes;
