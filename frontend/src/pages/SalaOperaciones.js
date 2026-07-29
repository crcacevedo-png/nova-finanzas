import React, { useState, useEffect, useMemo } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { surgeryApi, formatCurrency } from '../services/api';
import { 
  Plus, Search, Filter, Download, ChevronDown, ChevronRight,
  Eye, Pencil, Trash2, X, Calendar, Clock, User, Building2,
  Stethoscope, Activity, Package, FileText
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';

// Constantes
const ANESTHESIA_TYPES = [
  { value: 'local', label: 'Local' },
  { value: 'topica', label: 'Tópica' },
  { value: 'general', label: 'General' },
  { value: 'retrobulbar', label: 'Retrobulbar' },
  { value: 'peribulbar', label: 'Peribulbar' },
  { value: 'sedacion', label: 'Sedación' },
];

const INSTITUTIONS = [
  'IGSS', 'Privado', 'UNAERC', 'Hospital Roosevelt', 'Hospital San Juan de Dios', 'Otro'
];

const PROCEDURES_SUGGESTIONS = [
  'Facoemulsificación + LIO', 'Vitrectomía', 'Pterigión', 'Trabeculectomía',
  'Capsulotomía YAG', 'Iridotomía YAG', 'Crosslinking', 'LASIK', 'PRK',
  'Dacriocistorrinostomía', 'Enucleación', 'Blefaroplastía', 'Chalazión',
  'Transplante de córnea', 'Cerclaje escleral', 'Inyección intravítrea', 'Cirugía de estrabismo'
];

const EQUIPMENT_SUGGESTIONS = [
  'Facoemulsificador Centurion', 'Facoemulsificador Stellaris', 'Microscopio Zeiss Lumera 700',
  'Microscopio Leica M822', 'Vitrectomo Constellation', 'Láser YAG', 'Láser Femtosegundo',
  'Set instrumental cataratas', 'Set instrumental vitrectomía', 'Set instrumental córnea',
  'Set instrumental glaucoma', 'Tonómetro', 'Autorefractómetro'
];

const SUPPLY_SUGGESTIONS = [
  'Lente intraocular AcrySof IQ', 'Lente intraocular Tecnis', 'Lente intraocular tórico',
  'Lente intraocular multifocal', 'Viscoelástico Healon', 'Viscoelástico Provisc',
  'Viscoelástico Discovisc', 'Sutura nylon 10-0', 'Sutura vicryl 8-0', 'Sutura prolene 9-0',
  'Solución BSS', 'Mitomicina C', 'Triamcinolona', 'Bevacizumab (Avastin)',
  'Ranibizumab (Lucentis)', 'Aflibercept (Eylea)', 'Tinción tripán azul', 'Esponjas Weck-Cel',
  'Cuchillete 2.75mm', 'Cuchillete 15°', 'Cuchillete 45°', 'Cánula de irrigación/aspiración',
  'Cánula de hidrodisección', 'Anillo de tensión capsular', 'Iris hooks', 'Aceite de silicón',
  'Gas SF6', 'Gas C3F8'
];

const SUPPLY_CATEGORIES = [
  { value: 'lente', label: 'Lente', color: 'bg-blue-100 text-blue-700' },
  { value: 'medicamento', label: 'Medicamento', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'material', label: 'Material', color: 'bg-amber-100 text-amber-700' },
  { value: 'descartable', label: 'Descartable', color: 'bg-slate-100 text-slate-600' },
  { value: 'sutura', label: 'Sutura', color: 'bg-purple-100 text-purple-700' },
  { value: 'viscoelastico', label: 'Viscoelástico', color: 'bg-pink-100 text-pink-700' },
  { value: 'otro', label: 'Otro', color: 'bg-gray-100 text-gray-600' },
];

// Helpers
const formatDateDisplay = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr + 'T00:00:00');
  const day = date.getDate().toString().padStart(2, '0');
  const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  return `${day} ${month} ${year}`;
};

const getEyeBadge = (eye) => {
  // Normalizar OI legacy a OS
  const normalizedEye = eye === 'OI' ? 'OS' : eye;
  const styles = {
    OD: 'bg-blue-50 text-blue-700 border border-blue-200',
    OS: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    AO: 'bg-amber-50 text-amber-700 border border-amber-200',
  };
  return <Badge className={`${styles[normalizedEye] || styles.OS} font-medium`}>{normalizedEye}</Badge>;
};

const getCategoryBadge = (category) => {
  const cat = SUPPLY_CATEGORIES.find(c => c.value === category) || SUPPLY_CATEGORIES[6];
  return <Badge className={`${cat.color} border-0 font-normal text-xs`}>{cat.label}</Badge>;
};

const SalaOperaciones = () => {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin';
  const canEdit = user?.role === 'superadmin' || user?.role === 'admin';

  // State
  const [surgeries, setSurgeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [options, setOptions] = useState({ surgeons: [], institutions: [], anesthesiologists: [] });
  const [expandedRows, setExpandedRows] = useState({});
  
  // Filters
  const [search, setSearch] = useState('');
  const [filterSurgeon, setFilterSurgeon] = useState('');
  const [filterInstitution, setFilterInstitution] = useState('');
  const [filterEye, setFilterEye] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Dialogs
  const [surgeryDialogOpen, setSurgeryDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [equipmentDialogOpen, setEquipmentDialogOpen] = useState(false);
  const [supplyDialogOpen, setSupplyDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  
  // Selected/Form state
  const [selectedSurgery, setSelectedSurgery] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    time: new Date().toTimeString().slice(0, 5),
    patient_name: '',
    procedure: '',
    surgeon: '',
    eye: '',
    anesthesia_type: '',
    anesthesiologist: '',
    institution: '',
    igss_data: { unit: '', sps: '', affiliation_number: '', code: '', procedure_cost: '' },
    observations: '',
  });
  
  // Equipment/Supply form
  const [equipmentForm, setEquipmentForm] = useState({ name: '', quantity: 1, notes: '' });
  const [supplyForm, setSupplyForm] = useState({ name: '', category: 'otro', quantity: 1, unit_cost: 0, notes: '' });
  const [cancelForm, setCancelForm] = useState({ reason: '', reschedule_date: '' });

  // Fetch data
  useEffect(() => {
    fetchSurgeries();
    fetchOptions();
  }, [page, filterSurgeon, filterInstitution, filterEye, dateFrom, dateTo]);

  const fetchSurgeries = async () => {
    try {
      setLoading(true);
      const response = await surgeryApi.getAll({
        page,
        limit: 20,
        search: search || undefined,
        surgeon: filterSurgeon || undefined,
        institution: filterInstitution || undefined,
        eye: filterEye || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      });
      setSurgeries(response.data.data || []);
      setTotalPages(response.data.total_pages || 1);
    } catch (error) {
      console.error('Error fetching surgeries:', error);
      toast.error('Error al cargar las cirugías');
    } finally {
      setLoading(false);
    }
  };

  const fetchOptions = async () => {
    try {
      const response = await surgeryApi.getOptions();
      setOptions(response.data);
    } catch (error) {
      console.error('Error fetching options:', error);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchSurgeries();
  };

  const clearFilters = () => {
    setSearch('');
    setFilterSurgeon('');
    setFilterInstitution('');
    setFilterEye('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  const toggleRowExpand = (id) => {
    setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Surgery CRUD
  const openCreateDialog = () => {
    setEditMode(false);
    setFormData({
      date: new Date().toISOString().split('T')[0],
      time: new Date().toTimeString().slice(0, 5),
      patient_name: '',
      procedure: '',
      surgeon: '',
      eye: '',
      anesthesia_type: '',
      anesthesiologist: '',
      institution: '',
      igss_data: { unit: '', sps: '', affiliation_number: '', code: '', procedure_cost: '' },
      observations: '',
    });
    setSurgeryDialogOpen(true);
  };

  const openEditDialog = (surgery) => {
    setEditMode(true);
    setSelectedSurgery(surgery);
    setFormData({
      date: surgery.date,
      time: surgery.time,
      patient_name: surgery.patient_name,
      procedure: surgery.procedure,
      surgeon: surgery.surgeon,
      eye: surgery.eye,
      anesthesia_type: surgery.anesthesia_type,
      anesthesiologist: surgery.anesthesiologist,
      institution: surgery.institution,
      igss_data: surgery.igss_data || { unit: '', sps: '', affiliation_number: '', code: '', procedure_cost: '' },
      observations: surgery.observations || '',
    });
    setSurgeryDialogOpen(true);
  };

  const handleSaveSurgery = async () => {
    // Validaciones
    if (!formData.date || !formData.time || !formData.patient_name || !formData.procedure ||
        !formData.surgeon || !formData.eye || !formData.anesthesia_type || 
        !formData.anesthesiologist || !formData.institution) {
      toast.error('Complete todos los campos obligatorios');
      return;
    }
    
    if (formData.institution === 'IGSS') {
      const igss = formData.igss_data;
      if (!igss.unit || !igss.sps || !igss.affiliation_number || !igss.code || !igss.procedure_cost) {
        toast.error('Complete todos los campos de IGSS');
        return;
      }
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        igss_data: formData.institution === 'IGSS' ? {
          ...formData.igss_data,
          procedure_cost: parseFloat(formData.igss_data.procedure_cost) || 0
        } : null
      };
      
      if (editMode) {
        await surgeryApi.update(selectedSurgery.id, payload);
        toast.success('Cirugía actualizada');
      } else {
        await surgeryApi.create(payload);
        toast.success('Cirugía registrada');
      }
      
      setSurgeryDialogOpen(false);
      fetchSurgeries();
    } catch (error) {
      console.error('Error saving surgery:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSurgery = async () => {
    if (!selectedSurgery) return;
    setSubmitting(true);
    try {
      await surgeryApi.delete(selectedSurgery.id);
      toast.success('Cirugía eliminada');
      setDeleteDialogOpen(false);
      setSelectedSurgery(null);
      fetchSurgeries();
    } catch (error) {
      console.error('Error deleting surgery:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelSurgery = async () => {
    if (!selectedSurgery || !cancelForm.reason) {
      toast.error('Indique el motivo de cancelación');
      return;
    }
    setSubmitting(true);
    try {
      await surgeryApi.cancel(selectedSurgery.id, cancelForm.reason, cancelForm.reschedule_date || null);
      toast.success('Cirugía cancelada');
      setCancelDialogOpen(false);
      setSelectedSurgery(null);
      setCancelForm({ reason: '', reschedule_date: '' });
      fetchSurgeries();
    } catch (error) {
      console.error('Error canceling surgery:', error);
      toast.error(error.response?.data?.detail || 'Error al cancelar');
    } finally {
      setSubmitting(false);
    }
  };

  // Equipment handlers
  const handleAddEquipment = async () => {
    if (!equipmentForm.name) {
      toast.error('Ingrese el nombre del equipo');
      return;
    }
    setSubmitting(true);
    try {
      await surgeryApi.addEquipment(selectedSurgery.id, equipmentForm);
      toast.success('Equipo agregado');
      setEquipmentDialogOpen(false);
      setEquipmentForm({ name: '', quantity: 1, notes: '' });
      // Refetch selected surgery
      const updated = await surgeryApi.getById(selectedSurgery.id);
      setSelectedSurgery(updated.data);
      fetchSurgeries();
    } catch (error) {
      console.error('Error adding equipment:', error);
      toast.error('Error al agregar equipo');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteEquipment = async (equipmentId) => {
    try {
      await surgeryApi.deleteEquipment(selectedSurgery.id, equipmentId);
      toast.success('Equipo eliminado');
      const updated = await surgeryApi.getById(selectedSurgery.id);
      setSelectedSurgery(updated.data);
      fetchSurgeries();
    } catch (error) {
      console.error('Error deleting equipment:', error);
      toast.error('Error al eliminar equipo');
    }
  };

  // Supply handlers
  const handleAddSupply = async () => {
    if (!supplyForm.name || !supplyForm.quantity) {
      toast.error('Complete los campos obligatorios');
      return;
    }
    setSubmitting(true);
    try {
      await surgeryApi.addSupply(selectedSurgery.id, supplyForm);
      toast.success('Insumo agregado');
      setSupplyDialogOpen(false);
      setSupplyForm({ name: '', category: 'otro', quantity: 1, unit_cost: 0, notes: '' });
      const updated = await surgeryApi.getById(selectedSurgery.id);
      setSelectedSurgery(updated.data);
      fetchSurgeries();
    } catch (error) {
      console.error('Error adding supply:', error);
      toast.error('Error al agregar insumo');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSupply = async (supplyId) => {
    try {
      await surgeryApi.deleteSupply(selectedSurgery.id, supplyId);
      toast.success('Insumo eliminado');
      const updated = await surgeryApi.getById(selectedSurgery.id);
      setSelectedSurgery(updated.data);
      fetchSurgeries();
    } catch (error) {
      console.error('Error deleting supply:', error);
      toast.error('Error al eliminar insumo');
    }
  };

  // Calculated values
  const getSuppliesTotal = (supplies) => {
    return (supplies || []).reduce((sum, s) => sum + (s.total_cost || 0), 0);
  };

  const getTotalGeneral = (surgery) => {
    const procedureCost = surgery.igss_data?.procedure_cost || 0;
    const suppliesTotal = getSuppliesTotal(surgery.supplies);
    return procedureCost + suppliesTotal;
  };

  // Export handler
  const handleExport = async (format) => {
    try {
      toast.info(`Generando reporte ${format.toUpperCase()}...`);
      const response = await surgeryApi.exportReport({
        format,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        surgeon: filterSurgeon || undefined,
        institution: filterInstitution || undefined,
        eye: filterEye || undefined,
      });
      
      // Crear blob y descargar
      const blob = new Blob([response.data], { 
        type: format === 'xlsx' 
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
          : 'application/pdf' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `cirugias_novavision.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Reporte ${format.toUpperCase()} descargado`);
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('Error al exportar el reporte');
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="sala-operaciones-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 font-['Outfit']">Sala de operaciones</h1>
            <p className="text-slate-500 text-sm">Registro de cirugías oftalmológicas</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Export Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" data-testid="export-btn">
                  <Download className="w-4 h-4 mr-2" />
                  Exportar
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleExport('xlsx')} data-testid="export-excel-btn">
                  <FileText className="w-4 h-4 mr-2 text-emerald-600" />
                  Exportar a Excel
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('pdf')} data-testid="export-pdf-btn">
                  <FileText className="w-4 h-4 mr-2 text-red-600" />
                  Exportar a PDF
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            {canEdit && (
              <Button onClick={openCreateDialog} className="btn-primary" data-testid="register-surgery-btn">
                <Plus className="w-4 h-4 mr-2" />
                Registrar cirugía
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <Card className="border border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[250px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    placeholder="Buscar por paciente, procedimiento o cirujano..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="pl-10"
                    data-testid="search-input"
                  />
                </div>
              </div>
              
              <Select value={filterSurgeon || "all"} onValueChange={(v) => setFilterSurgeon(v === "all" ? "" : v)}>
                <SelectTrigger className="w-[180px]" data-testid="filter-surgeon">
                  <SelectValue placeholder="Todos los cirujanos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los cirujanos</SelectItem>
                  {options.surgeons.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={filterInstitution || "all"} onValueChange={(v) => setFilterInstitution(v === "all" ? "" : v)}>
                <SelectTrigger className="w-[180px]" data-testid="filter-institution">
                  <SelectValue placeholder="Todas las instituciones" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas las instituciones</SelectItem>
                  {INSTITUTIONS.map(i => (
                    <SelectItem key={i} value={i}>{i}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={filterEye || "all"} onValueChange={(v) => setFilterEye(v === "all" ? "" : v)}>
                <SelectTrigger className="w-[120px]" data-testid="filter-eye">
                  <SelectValue placeholder="Ojo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="OD">OD</SelectItem>
                  <SelectItem value="OS">OS</SelectItem>
                  <SelectItem value="AO">AO</SelectItem>
                </SelectContent>
              </Select>
              
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-[140px]"
                placeholder="Desde"
              />
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-[140px]"
                placeholder="Hasta"
              />
              
              <Button variant="ghost" onClick={clearFilters} className="text-slate-500">
                Limpiar filtros
              </Button>
              
              <Button variant="ghost" onClick={handleSearch} className="text-teal-600">
                <Search className="w-4 h-4 mr-1" />
                Buscar
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="border border-slate-200">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : surgeries.length === 0 ? (
              <div className="p-16 text-center">
                <Stethoscope className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No hay cirugías registradas</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50 border-b border-slate-200">
                      <TableHead className="w-10"></TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Fecha</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Hora</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Paciente</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Procedimiento</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Cirujano</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Ojo</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Anestesia</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold">Institución</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold text-right">Costo Proc.</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold text-right">Insumos</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold text-right">Total</TableHead>
                      <TableHead className="text-xs uppercase text-slate-500 font-semibold text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {surgeries.map((surgery) => (
                      <React.Fragment key={surgery.id}>
                        <TableRow 
                          className={`hover:bg-slate-50 border-b border-slate-100 ${surgery.status === 'cancelado' ? 'opacity-60 bg-red-50' : ''}`}
                          data-testid={`surgery-row-${surgery.id}`}
                        >
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleRowExpand(surgery.id)}
                              className="h-8 w-8 p-0"
                            >
                              {expandedRows[surgery.id] ? (
                                <ChevronDown className="w-4 h-4" />
                              ) : (
                                <ChevronRight className="w-4 h-4" />
                              )}
                            </Button>
                          </TableCell>
                          <TableCell className="text-sm">{formatDateDisplay(surgery.date)}</TableCell>
                          <TableCell className="text-sm">{surgery.time}</TableCell>
                          <TableCell className="font-medium">{surgery.patient_name}</TableCell>
                          <TableCell className="text-sm">{surgery.procedure}</TableCell>
                          <TableCell className="text-sm">{surgery.surgeon}</TableCell>
                          <TableCell>{getEyeBadge(surgery.eye)}</TableCell>
                          <TableCell className="text-sm capitalize">{surgery.anesthesia_type}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <span className="text-sm">{surgery.institution}</span>
                              {surgery.institution === 'IGSS' && (
                                <Badge className="bg-blue-100 text-blue-700 border-0 text-xs">IGSS</Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {surgery.igss_data?.procedure_cost ? formatCurrency(surgery.igss_data.procedure_cost) : '—'}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {formatCurrency(getSuppliesTotal(surgery.supplies))}
                          </TableCell>
                          <TableCell className="text-right font-semibold text-teal-600">
                            {formatCurrency(getTotalGeneral(surgery))}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setSelectedSurgery(surgery); setDetailDialogOpen(true); }}
                                className="h-8 w-8 p-0"
                                title="Ver detalle"
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                              {canEdit && surgery.status !== 'cancelado' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => openEditDialog(surgery)}
                                  className="h-8 w-8 p-0"
                                  title="Editar"
                                >
                                  <Pencil className="w-4 h-4" />
                                </Button>
                              )}
                              {isSuperAdmin && surgery.status !== 'cancelado' && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => { setSelectedSurgery(surgery); setCancelDialogOpen(true); }}
                                    className="h-8 w-8 p-0 text-amber-600 hover:text-amber-700"
                                    title="Cancelar"
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => { setSelectedSurgery(surgery); setDeleteDialogOpen(true); }}
                                    className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                                    title="Eliminar"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                        
                        {/* Expanded Row */}
                        {expandedRows[surgery.id] && (
                          <TableRow>
                            <TableCell colSpan={13} className="bg-slate-50 p-0">
                              <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Equipment Column */}
                                <div>
                                  <div className="flex items-center justify-between mb-3">
                                    <h4 className="font-semibold text-sm text-slate-700">Equipo utilizado</h4>
                                    {canEdit && surgery.status !== 'cancelado' && (
                                      <Button
                                        variant="link"
                                        size="sm"
                                        onClick={() => { setSelectedSurgery(surgery); setEquipmentDialogOpen(true); }}
                                        className="text-teal-600 text-xs h-auto p-0"
                                      >
                                        + Agregar
                                      </Button>
                                    )}
                                  </div>
                                  {surgery.equipment?.length > 0 ? (
                                    <ul className="space-y-1">
                                      {surgery.equipment.map(eq => (
                                        <li key={eq.id} className="flex items-center justify-between text-sm">
                                          <span className="flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                                            {eq.name}
                                            <span className="text-slate-400">x{eq.quantity}</span>
                                          </span>
                                          {canEdit && surgery.status !== 'cancelado' && (
                                            <button
                                              onClick={() => { setSelectedSurgery(surgery); handleDeleteEquipment(eq.id); }}
                                              className="text-slate-400 hover:text-red-500"
                                            >
                                              <X className="w-3 h-3" />
                                            </button>
                                          )}
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="text-sm text-slate-400 italic">Sin equipo registrado</p>
                                  )}
                                </div>
                                
                                {/* Supplies Column */}
                                <div>
                                  <div className="flex items-center justify-between mb-3">
                                    <h4 className="font-semibold text-sm text-slate-700">Insumos utilizados</h4>
                                    {canEdit && surgery.status !== 'cancelado' && (
                                      <Button
                                        variant="link"
                                        size="sm"
                                        onClick={() => { setSelectedSurgery(surgery); setSupplyDialogOpen(true); }}
                                        className="text-teal-600 text-xs h-auto p-0"
                                      >
                                        + Agregar
                                      </Button>
                                    )}
                                  </div>
                                  {surgery.supplies?.length > 0 ? (
                                    <div className="overflow-x-auto">
                                      <table className="w-full text-sm">
                                        <thead>
                                          <tr className="text-xs text-slate-500 border-b">
                                            <th className="text-left py-1">Insumo</th>
                                            <th className="text-left py-1">Cat.</th>
                                            <th className="text-right py-1">Cant.</th>
                                            <th className="text-right py-1">Unit.</th>
                                            <th className="text-right py-1">Total</th>
                                            <th></th>
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {surgery.supplies.map(sup => (
                                            <tr key={sup.id} className="border-b border-slate-100">
                                              <td className="py-1">{sup.name}</td>
                                              <td>{getCategoryBadge(sup.category)}</td>
                                              <td className="text-right">{sup.quantity}</td>
                                              <td className="text-right">{formatCurrency(sup.unit_cost)}</td>
                                              <td className="text-right font-medium">{formatCurrency(sup.total_cost)}</td>
                                              <td className="text-right">
                                                {canEdit && surgery.status !== 'cancelado' && (
                                                  <button
                                                    onClick={() => { setSelectedSurgery(surgery); handleDeleteSupply(sup.id); }}
                                                    className="text-slate-400 hover:text-red-500"
                                                  >
                                                    <X className="w-3 h-3" />
                                                  </button>
                                                )}
                                              </td>
                                            </tr>
                                          ))}
                                          <tr className="font-semibold">
                                            <td colSpan={4} className="text-right py-2">TOTAL INSUMOS:</td>
                                            <td className="text-right text-teal-600">{formatCurrency(getSuppliesTotal(surgery.supplies))}</td>
                                            <td></td>
                                          </tr>
                                        </tbody>
                                      </table>
                                    </div>
                                  ) : (
                                    <p className="text-sm text-slate-400 italic">Sin insumos registrados</p>
                                  )}
                                </div>
                              </div>
                              
                              {/* Financial Summary */}
                              <div className="mx-4 mb-4 p-4 bg-slate-100 rounded-lg">
                                <div className="grid grid-cols-3 gap-4 text-sm">
                                  <div>
                                    <span className="text-slate-500">Costo procedimiento (IGSS):</span>
                                    <span className="ml-2 font-medium">
                                      {surgery.igss_data?.procedure_cost ? formatCurrency(surgery.igss_data.procedure_cost) : '—'}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500">Total insumos:</span>
                                    <span className="ml-2 font-medium">{formatCurrency(getSuppliesTotal(surgery.supplies))}</span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500">TOTAL GENERAL:</span>
                                    <span className="ml-2 font-bold text-lg text-teal-600">{formatCurrency(getTotalGeneral(surgery))}</span>
                                  </div>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t">
                <span className="text-sm text-slate-500">Página {page} de {totalPages}</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                    Anterior
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Surgery Dialog (Create/Edit) */}
        <Dialog open={surgeryDialogOpen} onOpenChange={setSurgeryDialogOpen}>
          <DialogContent className="max-w-[720px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">
                {editMode ? `Editar cirugía — ${selectedSurgery?.patient_name}` : 'Registrar cirugía'}
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* Section: Datos generales */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-slate-200"></div>
                  <span className="text-xs uppercase text-slate-400 font-medium">Datos generales</span>
                  <div className="h-px flex-1 bg-slate-200"></div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Hora *</Label>
                    <Input
                      type="time"
                      value={formData.time}
                      onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label>Fecha *</Label>
                    <Input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    />
                  </div>
                  <div className="col-span-2">
                    <Label>Nombre del paciente *</Label>
                    <Input
                      value={formData.patient_name}
                      onChange={(e) => setFormData({ ...formData, patient_name: e.target.value })}
                      placeholder="Nombre completo del paciente"
                    />
                  </div>
                  <div className="col-span-2">
                    <Label>Procedimiento *</Label>
                    <Input
                      value={formData.procedure}
                      onChange={(e) => setFormData({ ...formData, procedure: e.target.value })}
                      list="procedures-list"
                      placeholder="Seleccione o escriba el procedimiento"
                    />
                    <datalist id="procedures-list">
                      {PROCEDURES_SUGGESTIONS.map(p => <option key={p} value={p} />)}
                    </datalist>
                  </div>
                  <div>
                    <Label>Cirujano *</Label>
                    <Input
                      value={formData.surgeon}
                      onChange={(e) => setFormData({ ...formData, surgeon: e.target.value })}
                      list="surgeons-list"
                      placeholder="Nombre del cirujano"
                    />
                    <datalist id="surgeons-list">
                      {options.surgeons.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                  <div>
                    <Label>Ojo a operar *</Label>
                    <div className="flex gap-2 mt-1">
                      {['OD', 'OS', 'AO'].map(eye => (
                        <button
                          key={eye}
                          type="button"
                          onClick={() => setFormData({ ...formData, eye })}
                          className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-colors ${
                            formData.eye === eye
                              ? eye === 'OD' ? 'bg-blue-50 border-blue-300 text-blue-700'
                                : eye === 'OS' ? 'bg-emerald-50 border-emerald-300 text-emerald-700'
                                : 'bg-amber-50 border-amber-300 text-amber-700'
                              : 'bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100'
                          }`}
                        >
                          {eye}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Section: Anestesia */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-slate-200"></div>
                  <span className="text-xs uppercase text-slate-400 font-medium">Anestesia</span>
                  <div className="h-px flex-1 bg-slate-200"></div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Tipo de anestesia *</Label>
                    <Select value={formData.anesthesia_type} onValueChange={(v) => setFormData({ ...formData, anesthesia_type: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccione..." />
                      </SelectTrigger>
                      <SelectContent>
                        {ANESTHESIA_TYPES.map(t => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Anestesiólogo *</Label>
                    <Input
                      value={formData.anesthesiologist}
                      onChange={(e) => setFormData({ ...formData, anesthesiologist: e.target.value })}
                      list="anesthesiologists-list"
                      placeholder="Nombre del anestesiólogo"
                    />
                    <datalist id="anesthesiologists-list">
                      {options.anesthesiologists.map(a => <option key={a} value={a} />)}
                    </datalist>
                  </div>
                </div>
              </div>
              
              {/* Section: Institución */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-slate-200"></div>
                  <span className="text-xs uppercase text-slate-400 font-medium">Institución</span>
                  <div className="h-px flex-1 bg-slate-200"></div>
                </div>
                
                <div>
                  <Label>Institución *</Label>
                  <Select value={formData.institution} onValueChange={(v) => setFormData({ ...formData, institution: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccione..." />
                    </SelectTrigger>
                    <SelectContent>
                      {INSTITUTIONS.map(i => (
                        <SelectItem key={i} value={i}>{i}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* IGSS Data */}
                {formData.institution === 'IGSS' && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-4 animate-in slide-in-from-top-2">
                    <Badge className="bg-blue-100 text-blue-700 border-0">Datos IGSS</Badge>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Unidad *</Label>
                        <Input
                          value={formData.igss_data.unit}
                          onChange={(e) => setFormData({ ...formData, igss_data: { ...formData.igss_data, unit: e.target.value } })}
                          placeholder="Ej: Consulta Externa Z.9"
                        />
                      </div>
                      <div>
                        <Label>SPS *</Label>
                        <Input
                          value={formData.igss_data.sps}
                          onChange={(e) => setFormData({ ...formData, igss_data: { ...formData.igss_data, sps: e.target.value } })}
                          placeholder="Número SPS"
                        />
                      </div>
                      <div>
                        <Label>No. de afiliación *</Label>
                        <Input
                          value={formData.igss_data.affiliation_number}
                          onChange={(e) => setFormData({ ...formData, igss_data: { ...formData.igss_data, affiliation_number: e.target.value } })}
                          placeholder="Número de afiliación"
                        />
                      </div>
                      <div>
                        <Label>Código de procedimiento *</Label>
                        <Input
                          value={formData.igss_data.code}
                          onChange={(e) => setFormData({ ...formData, igss_data: { ...formData.igss_data, code: e.target.value } })}
                          placeholder="Ej: OFT-001"
                        />
                      </div>
                      <div className="col-span-2">
                        <Label>Costo del procedimiento (GTQ) *</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.igss_data.procedure_cost}
                          onChange={(e) => setFormData({ ...formData, igss_data: { ...formData.igss_data, procedure_cost: e.target.value } })}
                          placeholder="0.00"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Section: Observaciones */}
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-slate-200"></div>
                  <span className="text-xs uppercase text-slate-400 font-medium">Observaciones</span>
                  <div className="h-px flex-1 bg-slate-200"></div>
                </div>
                
                <Textarea
                  value={formData.observations}
                  onChange={(e) => setFormData({ ...formData, observations: e.target.value })}
                  placeholder="Notas adicionales: indicaciones especiales, alergias, antecedentes relevantes, complicaciones..."
                  rows={3}
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setSurgeryDialogOpen(false)} disabled={submitting}>
                Cancelar
              </Button>
              <Button onClick={handleSaveSurgery} disabled={submitting} className="btn-primary">
                {submitting ? 'Guardando...' : 'Guardar registro'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
            {selectedSurgery && (
              <>
                <DialogHeader>
                  <DialogTitle className="font-['Outfit'] text-lg">{selectedSurgery.patient_name}</DialogTitle>
                  <DialogDescription className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    {formatDateDisplay(selectedSurgery.date)} - {selectedSurgery.time}
                    {selectedSurgery.status === 'cancelado' && (
                      <Badge className="bg-red-100 text-red-700 ml-2">CANCELADO</Badge>
                    )}
                  </DialogDescription>
                </DialogHeader>
                
                <div className="space-y-6">
                  {/* Datos del procedimiento */}
                  <div className="grid grid-cols-2 gap-4">
                    <div><span className="text-xs uppercase text-slate-400">Paciente</span><p className="font-medium">{selectedSurgery.patient_name}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Procedimiento</span><p className="font-medium">{selectedSurgery.procedure}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Cirujano</span><p className="font-medium">{selectedSurgery.surgeon}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Ojo</span><p>{getEyeBadge(selectedSurgery.eye)}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Tipo anestesia</span><p className="font-medium capitalize">{selectedSurgery.anesthesia_type}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Anestesiólogo</span><p className="font-medium">{selectedSurgery.anesthesiologist}</p></div>
                    <div><span className="text-xs uppercase text-slate-400">Institución</span><p className="font-medium">{selectedSurgery.institution}</p></div>
                  </div>
                  
                  {/* IGSS Data */}
                  {selectedSurgery.institution === 'IGSS' && selectedSurgery.igss_data && (
                    <div className="p-4 bg-blue-50 rounded-xl">
                      <Badge className="bg-blue-100 text-blue-700 border-0 mb-3">Datos IGSS</Badge>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div><span className="text-slate-500">Unidad:</span> <span className="font-medium">{selectedSurgery.igss_data.unit}</span></div>
                        <div><span className="text-slate-500">SPS:</span> <span className="font-medium">{selectedSurgery.igss_data.sps}</span></div>
                        <div><span className="text-slate-500">No. afiliación:</span> <span className="font-medium">{selectedSurgery.igss_data.affiliation_number}</span></div>
                        <div><span className="text-slate-500">Código:</span> <span className="font-medium">{selectedSurgery.igss_data.code}</span></div>
                        <div><span className="text-slate-500">Costo:</span> <span className="font-semibold text-teal-600">{formatCurrency(selectedSurgery.igss_data.procedure_cost)}</span></div>
                      </div>
                    </div>
                  )}
                  
                  {/* Equipment */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold">Equipo utilizado</h4>
                      {canEdit && selectedSurgery.status !== 'cancelado' && (
                        <Button variant="link" size="sm" onClick={() => setEquipmentDialogOpen(true)} className="text-teal-600">
                          + Agregar equipo
                        </Button>
                      )}
                    </div>
                    {selectedSurgery.equipment?.length > 0 ? (
                      <ul className="space-y-1">
                        {selectedSurgery.equipment.map(eq => (
                          <li key={eq.id} className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded">
                            <span>{eq.name} <span className="text-slate-400">x{eq.quantity}</span></span>
                            {canEdit && selectedSurgery.status !== 'cancelado' && (
                              <button onClick={() => handleDeleteEquipment(eq.id)} className="text-slate-400 hover:text-red-500">
                                <X className="w-4 h-4" />
                              </button>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin equipo registrado</p>
                    )}
                  </div>
                  
                  {/* Supplies */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold">Insumos utilizados</h4>
                      {canEdit && selectedSurgery.status !== 'cancelado' && (
                        <Button variant="link" size="sm" onClick={() => setSupplyDialogOpen(true)} className="text-teal-600">
                          + Agregar insumo
                        </Button>
                      )}
                    </div>
                    {selectedSurgery.supplies?.length > 0 ? (
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-xs text-slate-500 border-b">
                            <th className="text-left py-2">Insumo</th>
                            <th className="text-left py-2">Categoría</th>
                            <th className="text-right py-2">Cant.</th>
                            <th className="text-right py-2">Unitario</th>
                            <th className="text-right py-2">Total</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedSurgery.supplies.map(sup => (
                            <tr key={sup.id} className="border-b border-slate-100">
                              <td className="py-2">{sup.name}</td>
                              <td>{getCategoryBadge(sup.category)}</td>
                              <td className="text-right">{sup.quantity}</td>
                              <td className="text-right">{formatCurrency(sup.unit_cost)}</td>
                              <td className="text-right font-medium">{formatCurrency(sup.total_cost)}</td>
                              <td className="text-right">
                                {canEdit && selectedSurgery.status !== 'cancelado' && (
                                  <button onClick={() => handleDeleteSupply(sup.id)} className="text-slate-400 hover:text-red-500">
                                    <X className="w-4 h-4" />
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                          <tr className="font-semibold">
                            <td colSpan={4} className="text-right py-2">TOTAL:</td>
                            <td className="text-right text-teal-600">{formatCurrency(getSuppliesTotal(selectedSurgery.supplies))}</td>
                            <td></td>
                          </tr>
                        </tbody>
                      </table>
                    ) : (
                      <p className="text-sm text-slate-400 italic">Sin insumos registrados</p>
                    )}
                  </div>
                  
                  {/* Financial Summary */}
                  <div className="p-4 bg-slate-100 rounded-xl">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span>Costo procedimiento (IGSS):</span>
                      <span className="font-medium">{selectedSurgery.igss_data?.procedure_cost ? formatCurrency(selectedSurgery.igss_data.procedure_cost) : '—'}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span>Total insumos:</span>
                      <span className="font-medium">{formatCurrency(getSuppliesTotal(selectedSurgery.supplies))}</span>
                    </div>
                    <div className="h-px bg-slate-300 my-2"></div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">TOTAL GENERAL:</span>
                      <span className="text-xl font-bold text-teal-600">{formatCurrency(getTotalGeneral(selectedSurgery))}</span>
                    </div>
                  </div>
                  
                  {/* Observations */}
                  {selectedSurgery.observations && (
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <span className="text-xs uppercase text-slate-400">Observaciones</span>
                      <p className="text-sm mt-1">{selectedSurgery.observations}</p>
                    </div>
                  )}
                  
                  {/* Cancellation info */}
                  {selectedSurgery.status === 'cancelado' && selectedSurgery.cancellation_reason && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <span className="text-xs uppercase text-red-500">Motivo de cancelación</span>
                      <p className="text-sm mt-1 text-red-700">{selectedSurgery.cancellation_reason}</p>
                      {selectedSurgery.rescheduled_to && (
                        <p className="text-sm mt-2 text-red-600">Reagendado para: {formatDateDisplay(selectedSurgery.rescheduled_to)}</p>
                      )}
                    </div>
                  )}
                </div>
                
                <DialogFooter>
                  <Button variant="ghost" onClick={() => setDetailDialogOpen(false)}>Cerrar</Button>
                  {canEdit && selectedSurgery.status !== 'cancelado' && (
                    <Button variant="outline" onClick={() => { setDetailDialogOpen(false); openEditDialog(selectedSurgery); }}>
                      Editar
                    </Button>
                  )}
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>

        {/* Equipment Dialog */}
        <Dialog open={equipmentDialogOpen} onOpenChange={setEquipmentDialogOpen}>
          <DialogContent className="max-w-[460px]">
            <DialogHeader>
              <DialogTitle>Agregar equipo — {selectedSurgery?.patient_name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Equipo utilizado *</Label>
                <Input
                  value={equipmentForm.name}
                  onChange={(e) => setEquipmentForm({ ...equipmentForm, name: e.target.value })}
                  list="equipment-list"
                  placeholder="Seleccione o escriba el equipo"
                />
                <datalist id="equipment-list">
                  {EQUIPMENT_SUGGESTIONS.map(e => <option key={e} value={e} />)}
                </datalist>
              </div>
              <div>
                <Label>Cantidad</Label>
                <Input
                  type="number"
                  min="1"
                  value={equipmentForm.quantity}
                  onChange={(e) => setEquipmentForm({ ...equipmentForm, quantity: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div>
                <Label>Notas</Label>
                <Input
                  value={equipmentForm.notes}
                  onChange={(e) => setEquipmentForm({ ...equipmentForm, notes: e.target.value })}
                  placeholder="Detalles adicionales..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEquipmentDialogOpen(false)}>Cancelar</Button>
              <Button onClick={handleAddEquipment} disabled={submitting} className="btn-primary">
                {submitting ? 'Agregando...' : 'Agregar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Supply Dialog */}
        <Dialog open={supplyDialogOpen} onOpenChange={setSupplyDialogOpen}>
          <DialogContent className="max-w-[540px]">
            <DialogHeader>
              <DialogTitle>Agregar insumo — {selectedSurgery?.patient_name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Insumo *</Label>
                <Input
                  value={supplyForm.name}
                  onChange={(e) => setSupplyForm({ ...supplyForm, name: e.target.value })}
                  list="supply-list"
                  placeholder="Seleccione o escriba el insumo"
                />
                <datalist id="supply-list">
                  {SUPPLY_SUGGESTIONS.map(s => <option key={s} value={s} />)}
                </datalist>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Categoría *</Label>
                  <Select value={supplyForm.category} onValueChange={(v) => setSupplyForm({ ...supplyForm, category: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SUPPLY_CATEGORIES.map(c => (
                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Cantidad *</Label>
                  <Input
                    type="number"
                    min="1"
                    value={supplyForm.quantity}
                    onChange={(e) => setSupplyForm({ ...supplyForm, quantity: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>
              <div>
                <Label>Costo unitario (GTQ) *</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={supplyForm.unit_cost}
                  onChange={(e) => setSupplyForm({ ...supplyForm, unit_cost: parseFloat(e.target.value) || 0 })}
                  placeholder="0.00"
                />
              </div>
              <div className="p-3 bg-slate-100 rounded-lg">
                <span className="text-sm text-slate-500">Total calculado:</span>
                <span className="ml-2 font-semibold text-lg text-teal-600">
                  {formatCurrency(supplyForm.quantity * supplyForm.unit_cost)}
                </span>
              </div>
              <div>
                <Label>Notas</Label>
                <Input
                  value={supplyForm.notes}
                  onChange={(e) => setSupplyForm({ ...supplyForm, notes: e.target.value })}
                  placeholder="Lote, fecha de vencimiento, etc."
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSupplyDialogOpen(false)}>Cancelar</Button>
              <Button onClick={handleAddSupply} disabled={submitting} className="btn-primary">
                {submitting ? 'Agregando...' : 'Agregar insumo'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="text-red-600">Eliminar cirugía</DialogTitle>
              <DialogDescription>
                ¿Está seguro de eliminar esta cirugía? Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            {selectedSurgery && (
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="font-medium">{selectedSurgery.patient_name}</p>
                <p className="text-sm text-slate-600">{selectedSurgery.procedure} - {formatDateDisplay(selectedSurgery.date)}</p>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancelar</Button>
              <Button variant="destructive" onClick={handleDeleteSurgery} disabled={submitting}>
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Cancel Dialog */}
        <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
          <DialogContent className="max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="text-amber-600">Cancelar cirugía</DialogTitle>
              <DialogDescription>
                Indique el motivo de cancelación y opcionalmente la fecha de reagendamiento.
              </DialogDescription>
            </DialogHeader>
            {selectedSurgery && (
              <div className="space-y-4">
                <div className="p-3 bg-amber-50 rounded-lg">
                  <p className="font-medium">{selectedSurgery.patient_name}</p>
                  <p className="text-sm text-slate-600">{selectedSurgery.procedure} - {formatDateDisplay(selectedSurgery.date)}</p>
                </div>
                <div>
                  <Label>Motivo de cancelación *</Label>
                  <Textarea
                    value={cancelForm.reason}
                    onChange={(e) => setCancelForm({ ...cancelForm, reason: e.target.value })}
                    placeholder="Indique el motivo..."
                    rows={3}
                  />
                </div>
                <div>
                  <Label>Reagendar para (opcional)</Label>
                  <Input
                    type="date"
                    value={cancelForm.reschedule_date}
                    onChange={(e) => setCancelForm({ ...cancelForm, reschedule_date: e.target.value })}
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>Volver</Button>
              <Button onClick={handleCancelSurgery} disabled={submitting} className="bg-amber-600 hover:bg-amber-700 text-white">
                {submitting ? 'Cancelando...' : 'Cancelar cirugía'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default SalaOperaciones;
