import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Building,
  AlertCircle,
  Users,
  FileBarChart,
  ClipboardList,
  Download,
  FileStack,
  AlertTriangle,
  XCircle,
  Eye
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import { igssUnitApi, igssNogApi } from '../services/api';
import { NogsUnidadDialog } from '../components/NogsUnidadDialog';

// Exporta el reporte por unidad a CSV
const exportarReporteCSV = (data) => {
  const rows = [['Unidad', 'Código', 'Estado', 'Pacientes', 'Evaluaciones']];
  (data.unidades || []).forEach((u) => {
    rows.push([u.nombre, u.codigo || '', u.activa ? 'Activa' : 'Inactiva', u.pacientes, u.evaluaciones]);
  });
  if (data.sin_unidad) {
    rows.push(['Sin unidad asignada', '', '', data.sin_unidad.pacientes, data.sin_unidad.evaluaciones]);
  }
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `reporte_unidades_igss_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const MetricCard = ({ icon: Icon, label, value, color }) => (
  <Card className="card-metrics border-0 shadow-none">
    <CardContent className="p-4 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${color}`}><Icon className="w-5 h-5" /></div>
      <div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</p>
        <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{value}</p>
      </div>
    </CardContent>
  </Card>
);

// Reporte: pacientes y evaluaciones por unidad IGSS
const ReporteIGSS = ({ data, loading, onRefresh }) => {
  if (loading || !data) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  const t = data.totales || {};
  const unidades = data.unidades || [];
  const sin = data.sin_unidad || { pacientes: 0, evaluaciones: 0 };
  return (
    <div className="space-y-6" data-testid="reporte-igss">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard icon={Building} label="Unidades IGSS" value={t.unidades ?? 0} color="bg-green-100 text-green-600" />
        <MetricCard icon={Users} label="Pacientes con unidad" value={t.pacientes_con_unidad ?? 0} color="bg-blue-100 text-blue-600" />
        <MetricCard icon={ClipboardList} label="Evaluaciones con unidad" value={t.evaluaciones_con_unidad ?? 0} color="bg-teal-100 text-teal-600" />
      </div>

      <Card className="card-teal">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            Pacientes y evaluaciones por unidad
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="btn-outline" onClick={onRefresh} data-testid="reporte-refresh">
              <RefreshCw className="w-4 h-4 mr-2" />Actualizar
            </Button>
            <Button variant="outline" size="sm" className="btn-outline" onClick={() => exportarReporteCSV(data)} data-testid="reporte-export-csv">
              <Download className="w-4 h-4 mr-2" />Exportar CSV
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                  <TableHead className="table-header">Unidad</TableHead>
                  <TableHead className="table-header">Código</TableHead>
                  <TableHead className="table-header">Estado</TableHead>
                  <TableHead className="table-header text-right">Pacientes</TableHead>
                  <TableHead className="table-header text-right">Evaluaciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unidades.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center py-8 text-gray-500">No hay unidades IGSS registradas</TableCell></TableRow>
                ) : unidades.map((u) => (
                  <TableRow key={u.unidad_id} data-testid={`reporte-row-${u.unidad_id}`}>
                    <TableCell className="font-medium" style={{ color: 'var(--text-primary)' }}>{u.nombre}</TableCell>
                    <TableCell style={{ color: 'var(--text-secondary)' }}>{u.codigo || '—'}</TableCell>
                    <TableCell>
                      <Badge className={u.activa ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}>
                        {u.activa ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-semibold">{u.pacientes}</TableCell>
                    <TableCell className="text-right font-semibold">{u.evaluaciones}</TableCell>
                  </TableRow>
                ))}
                {(sin.pacientes > 0 || sin.evaluaciones > 0) && (
                  <TableRow className="bg-amber-50" data-testid="reporte-row-sin-unidad">
                    <TableCell className="italic text-amber-700" colSpan={3}>Sin unidad IGSS asignada</TableCell>
                    <TableCell className="text-right font-semibold text-amber-700">{sin.pacientes}</TableCell>
                    <TableCell className="text-right font-semibold text-amber-700">{sin.evaluaciones}</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const UnidadesIGSS = () => {
  const { user, hasPermission } = useAuth();
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState(null);
  const [selectedUnit, setSelectedUnit] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeView, setActiveView] = useState('catalogo');
  const [reporte, setReporte] = useState(null);
  const [loadingReporte, setLoadingReporte] = useState(false);
  const [nogUnit, setNogUnit] = useState(null);
  const [nogDialogOpen, setNogDialogOpen] = useState(false);
  const [nogInicial, setNogInicial] = useState(null);
  const [alertas, setAlertas] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    description: ''
  });

  // Acceso por permiso (SuperAdmin y roles con manage_igss_units, p. ej. Administrador IGSS)
  const canManageIgss = user?.role === 'superadmin' || hasPermission('manage_igss_units');

  const fetchUnits = useCallback(async () => {
    try {
      setLoading(true);
      const response = await igssUnitApi.getAll();
      setUnits(response.data.data || []);
    } catch (error) {
      console.error('Error fetching IGSS units:', error);
      toast.error('Error al cargar las unidades IGSS');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAlertas = useCallback(async () => {
    try {
      const response = await igssNogApi.getAlertas();
      setAlertas(response.data);
    } catch (error) {
      // Silencioso: la alerta es informativa
      setAlertas(null);
    }
  }, []);

  const abrirNogsUnidad = (unit, nogId = null) => {
    setNogUnit(unit);
    setNogInicial(nogId);
    setNogDialogOpen(true);
  };

  const fetchReporte = useCallback(async () => {
    try {
      setLoadingReporte(true);
      const response = await igssUnitApi.getReporte();
      setReporte(response.data);
    } catch (error) {
      console.error('Error fetching IGSS report:', error);
      toast.error('Error al cargar el reporte por unidad IGSS');
    } finally {
      setLoadingReporte(false);
    }
  }, []);

  useEffect(() => {
    fetchUnits();
    fetchAlertas();
  }, [fetchUnits, fetchAlertas]);

  const handleOpenDialog = (unit = null) => {
    if (unit) {
      setEditingUnit(unit);
      setFormData({
        name: unit.name,
        code: unit.code || '',
        description: unit.description || ''
      });
    } else {
      setEditingUnit(null);
      setFormData({
        name: '',
        code: '',
        description: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre de la unidad es obligatorio');
      return;
    }

    setSubmitting(true);
    try {
      if (editingUnit) {
        await igssUnitApi.update(editingUnit.id, formData);
        toast.success('Unidad IGSS actualizada exitosamente');
      } else {
        await igssUnitApi.create(formData);
        toast.success('Unidad IGSS creada exitosamente');
      }
      setDialogOpen(false);
      fetchUnits();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar la unidad IGSS';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedUnit) return;
    
    setSubmitting(true);
    try {
      await igssUnitApi.delete(selectedUnit.id);
      toast.success('Unidad IGSS eliminada exitosamente');
      setDeleteDialogOpen(false);
      setSelectedUnit(null);
      fetchUnits();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar la unidad IGSS';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUnits = units.filter(unit =>
    unit.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (unit.code && unit.code.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (!canManageIgss) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <AlertCircle className="w-12 h-12 text-amber-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">Acceso Restringido</h2>
          <p className="text-gray-500">No tienes permiso para gestionar el catálogo de Unidades IGSS.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="unidades-igss-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Unidades IGSS
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Catálogo de unidades del Instituto Guatemalteco de Seguridad Social
            </p>
          </div>
          {activeView === 'catalogo' && (
            <div className="flex gap-2">
              <Button 
                variant="outline"
                onClick={fetchUnits}
                className="btn-outline"
                data-testid="refresh-button"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Actualizar
              </Button>
              <Button 
                onClick={() => handleOpenDialog()}
                className="btn-primary"
                data-testid="add-unit-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nueva Unidad
              </Button>
            </div>
          )}
        </div>

        {/* Alertas de límite de NOG (90%+ y completados) */}
        {alertas && alertas.total > 0 && (
          <Card className="border-l-4 border-l-amber-500 bg-amber-50/50" data-testid="nog-alertas-banner">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2 text-amber-800">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                Alertas de contratos NOG
                <Badge className="bg-amber-200 text-amber-900" data-testid="nog-alertas-count">{alertas.total}</Badge>
              </CardTitle>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {alertas.completados > 0 && (
                  <span className="text-red-700 font-medium">{alertas.completados} completado(s)</span>
                )}
                {alertas.completados > 0 && alertas.por_completarse > 0 && ' · '}
                {alertas.por_completarse > 0 && (
                  <span className="text-amber-700 font-medium">{alertas.por_completarse} por completarse (≥{alertas.umbral_aviso}%)</span>
                )}
                {' '}— renueva el contrato a tiempo.
              </p>
            </CardHeader>
            <CardContent className="pt-0 space-y-2">
              {alertas.alertas.map((a) => {
                const completado = a.estado === 'completado';
                return (
                  <div
                    key={a.nog_id}
                    className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border ${completado ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-white'}`}
                    data-testid={`nog-alerta-${a.nog_id}`}
                  >
                    <div className="flex items-center gap-3">
                      {completado
                        ? <XCircle className="w-5 h-5 text-red-500 shrink-0" />
                        : <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />}
                      <div>
                        <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {a.numero}
                          {a.nombre_servicio ? <span className="font-normal text-gray-500"> — {a.nombre_servicio}</span> : null}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {a.unidad_nombre} · {a.acreditados}/{a.cantidad} servicios ({a.porcentaje}%) · {a.disponibles} disponibles
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 sm:justify-end">
                      <Badge className={completado ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>
                        {completado ? 'Completado' : 'Por completarse'}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        className="btn-outline"
                        onClick={() => abrirNogsUnidad({ id: a.unidad_id, name: a.unidad_nombre, code: a.unidad_codigo }, a.nog_id)}
                        data-testid={`nog-alerta-ver-${a.nog_id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" />Ver
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}

        <Tabs value={activeView} onValueChange={setActiveView} className="w-full">
          <TabsList data-testid="unidades-igss-tabs">
            <TabsTrigger value="catalogo" data-testid="tab-catalogo">
              <Building className="w-4 h-4 mr-2" />Catálogo
            </TabsTrigger>
            <TabsTrigger value="reporte" data-testid="tab-reporte" onClick={fetchReporte}>
              <FileBarChart className="w-4 h-4 mr-2" />Reporte
            </TabsTrigger>
          </TabsList>

          <TabsContent value="catalogo" className="space-y-6 mt-4">

        {/* Summary Card */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-green-100">
              <Building className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Unidades IGSS</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {units.length}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <Input
              placeholder="Buscar por nombre o código..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-teal max-w-md"
              data-testid="search-unit"
            />
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Unidades IGSS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : filteredUnits.length === 0 ? (
              <div className="p-12 text-center">
                <Building className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {searchTerm ? 'No se encontraron unidades' : 'No hay unidades IGSS registradas'}
                </p>
                {!searchTerm && (
                  <Button 
                    onClick={() => handleOpenDialog()}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primera unidad
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Código</TableHead>
                      <TableHead className="table-header">Descripción</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUnits.map((unit) => (
                      <TableRow 
                        key={unit.id} 
                        className="table-row-hover"
                        data-testid={`unit-row-${unit.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-green-50">
                              <Building className="w-4 h-4 text-green-600" />
                            </div>
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {unit.name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {unit.code ? (
                            <span className="font-mono text-sm" style={{ color: 'var(--text-secondary)' }}>
                              {unit.code}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {unit.description || '-'}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => abrirNogsUnidad(unit)}
                              className="h-8 px-2 text-[#0F6E56] hover:bg-[#E1F5EE]"
                              data-testid={`nogs-unit-${unit.id}`}
                            >
                              <FileStack className="w-4 h-4 mr-1" />NOG
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(unit)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`edit-unit-${unit.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedUnit(unit);
                                setDeleteDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                              data-testid={`delete-unit-${unit.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card className="card-teal border-l-4 border-l-green-500">
          <CardContent className="p-4">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              <strong>Nota:</strong> Este catálogo permite administrar las unidades del IGSS que pueden ser asignadas 
              a pacientes cuando su institución referente es &quot;IGSS&quot;. El catálogo inicia vacío y puede ser 
              completado según las necesidades de la clínica.
            </p>
          </CardContent>
        </Card>
          </TabsContent>

          <TabsContent value="reporte" className="mt-4">
            <ReporteIGSS data={reporte} loading={loadingReporte} onRefresh={fetchReporte} />
          </TabsContent>
        </Tabs>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingUnit ? 'Editar Unidad IGSS' : 'Nueva Unidad IGSS'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingUnit 
                  ? 'Actualiza los datos de la unidad IGSS'
                  : 'Ingresa los datos de la nueva unidad IGSS'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre de la Unidad *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: Hospital General de Enfermedades"
                  data-testid="unit-name-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="code">Código (opcional)</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                  className="input-teal"
                  placeholder="Ej: HGE-001"
                  data-testid="unit-code-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Descripción (opcional)</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  className="input-teal"
                  placeholder="Descripción o ubicación de la unidad"
                  data-testid="unit-description-input"
                />
              </div>

              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setDialogOpen(false)} 
                  className="btn-outline"
                >
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={submitting}
                  data-testid="submit-unit-button"
                >
                  {submitting 
                    ? (editingUnit ? 'Guardando...' : 'Creando...') 
                    : (editingUnit ? 'Guardar cambios' : 'Crear unidad')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Eliminar Unidad IGSS
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar la unidad &quot;{selectedUnit?.name}&quot;? 
                Esta acción no se puede deshacer.
                <br /><br />
                <strong className="text-amber-600">Nota:</strong> No se podrá eliminar si hay pacientes usando esta unidad.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => setDeleteDialogOpen(false)} 
                className="btn-outline"
              >
                Cancelar
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete}
                disabled={submitting}
                data-testid="confirm-delete-button"
              >
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* NOG por Unidad IGSS */}
        {nogUnit && (
          <NogsUnidadDialog
            unit={nogUnit}
            open={nogDialogOpen}
            onOpenChange={setNogDialogOpen}
            initialNogId={nogInicial}
            onChanged={fetchAlertas}
          />
        )}
      </div>
    </Layout>
  );
};

export default UnidadesIGSS;
