import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Users,
  Search,
  FileSpreadsheet,
  FileText,
  Download,
  Filter,
  Eye,
  UserCheck,
  UserX,
  ClipboardList,
  Stethoscope,
  ChevronLeft,
  ChevronRight,
  X
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
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { EvaluacionesPacienteDialog } from '../components/EvaluacionesPacienteDialog';
import { NogSelector } from '../components/NogSelector';
import { toast, Toaster } from 'sonner';
import { 
  patientApi, 
  igssUnitApi,
  igssNogApi,
  formatDate, 
  referralInstitutionLabels, 
  genderLabels,
  calculateAge,
  getGuatemalaDate
} from '../services/api';

// Extrae un mensaje de error legible (FastAPI 422 devuelve detail como lista de objetos)
const extractErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map(d => d?.msg || (typeof d === 'string' ? d : JSON.stringify(d))).join(', ');
  if (typeof detail === 'string') return detail;
  return fallback;
};

const Pacientes = () => {
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [igssUnits, setIgssUnits] = useState([]);
  const [filterNogs, setFilterNogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [evaluacionesDialogOpen, setEvaluacionesDialogOpen] = useState(false);
  const [evaluacionesPatient, setEvaluacionesPatient] = useState(null);
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [duplicateInfo, setDuplicateInfo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // Paginación y búsqueda
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    referral_institution: '',
    igss_unit_id: '',
    igss_nog: '',
    gender: '',
    dateFrom: '',
    dateTo: '',
    is_active: true
  });
  
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    gender: '',
    birth_date: '',
    profession: '',
    phone: '',
    email: '',
    dpi: '',
    emergency_phone: '',
    emergency_contact_name: '',
    emergency_contact_relationship: '',
    referral_institution: '',
    insurance_name: '',
    other_institution_name: '',
    igss_unit_id: '',
    comments: ''
  });

  const canCreate = hasPermission('create_patients');
  const canEdit = hasPermission('edit_patients');
  const canDelete = hasPermission('delete_patients');
  const canExport = hasPermission('export_patients');
  // Roles con permiso de crear/editar evaluaciones (coherente con el backend y EvaluacionOftalmologica)
  const canCreateEvaluacion = user?.role === 'superadmin' || user?.role === 'admin' || user?.role === 'usuario' || user?.role === 'medico';

  const fetchIgssUnits = useCallback(async () => {
    try {
      const response = await igssUnitApi.getAll();
      setIgssUnits(response.data.data || []);
    } catch (error) {
      console.error('Error fetching IGSS units:', error);
    }
  }, []);

  const fetchPatients = useCallback(async () => {
    try {
      setLoading(true);
      const response = await patientApi.getAll({
        page,
        limit: 20,
        search: searchTerm,
        ...filters
      });
      setPatients(response.data.data || []);
      setTotalPages(response.data.total_pages || 1);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching patients:', error);
      toast.error('Error al cargar los pacientes');
    } finally {
      setLoading(false);
    }
  }, [page, searchTerm, filters]);

  useEffect(() => {
    fetchIgssUnits();
  }, [fetchIgssUnits]);

  // Cargar los NOG de la unidad elegida en el filtro (cascada unidad -> NOG)
  useEffect(() => {
    const unitId = filters.igss_unit_id;
    if (!unitId) {
      setFilterNogs([]);
      return;
    }
    let cancelled = false;
    igssNogApi.getActivos(unitId)
      .then((res) => { if (!cancelled) setFilterNogs(res.data || []); })
      .catch(() => { if (!cancelled) setFilterNogs([]); });
    return () => { cancelled = true; };
  }, [filters.igss_unit_id]);

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  // Detección de pacientes nuevos creados por otros usuarios (aviso discreto)
  const knownPatientIdsRef = useRef(new Set());
  useEffect(() => {
    knownPatientIdsRef.current = new Set((patients || []).map((p) => p.id));
  }, [patients]);

  // Refresco silencioso: refleja registros nuevos entre usuarios simultáneos
  // sin recargar la página. No se ejecuta con el formulario abierto.
  const pollPatients = useCallback(async () => {
    if (dialogOpen) return;
    try {
      const response = await patientApi.getAll({
        page,
        limit: 20,
        search: searchTerm,
        ...filters
      });
      const nuevos = response.data.data || [];
      const previos = knownPatientIdsRef.current;
      const nuevosDeOtros = previos.size > 0 ? nuevos.filter((p) => !previos.has(p.id)) : [];
      setPatients(nuevos);
      setTotalPages(response.data.total_pages || 1);
      setTotal(response.data.total || 0);
      if (nuevosDeOtros.length > 0) {
        toast.info(`Lista actualizada: ${nuevosDeOtros.length} paciente(s) nuevo(s)`, { duration: 3000 });
      }
    } catch (e) {
      // silencioso
    }
  }, [page, searchTerm, filters, dialogOpen]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) pollPatients();
    }, 15000);
    return () => clearInterval(interval);
  }, [pollPatients]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchPatients();
  };

  const resetForm = () => {
    setFormData({
      first_name: '',
      last_name: '',
      gender: '',
      birth_date: '',
      profession: '',
      phone: '',
      email: '',
      dpi: '',
      address: '',
      marital_status: '',
      emergency_phone: '',
      emergency_contact_name: '',
      emergency_contact_relationship: '',
      referral_institution: '',
      insurance_name: '',
      other_institution_name: '',
      igss_unit_id: '',
      igss_afiliacion: '',
      igss_no_sps: '',
      igss_codigo: '',
      igss_tipo_compra: '',
      igss_nog: '',
      igss_tipo_paciente: '',
      igss_ordenes: [],
      comments: ''
    });
    setEditingPatient(null);
  };

  const handleOpenDialog = (patient = null) => {
    if (patient) {
      setEditingPatient(patient);
      setFormData({
        first_name: patient.first_name,
        last_name: patient.last_name,
        gender: patient.gender,
        birth_date: patient.birth_date,
        profession: patient.profession || '',
        phone: patient.phone,
        email: patient.email || '',
        dpi: patient.dpi || '',
        address: patient.address || '',
        marital_status: patient.marital_status || '',
        emergency_phone: patient.emergency_phone || '',
        emergency_contact_name: patient.emergency_contact_name || '',
        emergency_contact_relationship: patient.emergency_contact_relationship || '',
        referral_institution: patient.referral_institution,
        insurance_name: patient.insurance_name || '',
        other_institution_name: patient.other_institution_name || '',
        igss_unit_id: patient.igss_unit_id || '',
        igss_afiliacion: patient.igss_afiliacion || '',
        igss_no_sps: patient.igss_no_sps || '',
        igss_codigo: patient.igss_codigo || '',
        igss_tipo_compra: patient.igss_tipo_compra || '',
        igss_nog: patient.igss_nog || '',
        igss_tipo_paciente: patient.igss_tipo_paciente || '',
        igss_ordenes: (patient.igss_ordenes && patient.igss_ordenes.length > 0)
          ? patient.igss_ordenes.map(o => ({ ...o }))
          : [],
        comments: patient.comments || ''
      });
    } else {
      resetForm();
    }
    setDialogOpen(true);
  };

  // Gestión de órdenes IGSS (múltiples NOG/SPS por paciente)
  const addOrdenIgss = () => setFormData(prev => ({
    ...prev,
    igss_ordenes: [...(prev.igss_ordenes || []), { id: `ord_${Date.now()}`, nog: '', no_sps: '', codigo: '', procedimiento: '' }]
  }));
  const removeOrdenIgss = (idx) => setFormData(prev => ({
    ...prev,
    igss_ordenes: (prev.igss_ordenes || []).filter((_, i) => i !== idx)
  }));
  const updateOrdenIgss = (idx, field, value) => setFormData(prev => {
    const arr = [...(prev.igss_ordenes || [])];
    arr[idx] = { ...arr[idx], [field]: value };
    return { ...prev, igss_ordenes: arr };
  });

  const validateForm = () => {
    if (!formData.first_name.trim()) {
      toast.error('El nombre es obligatorio');
      return false;
    }
    if (!formData.last_name.trim()) {
      toast.error('El apellido es obligatorio');
      return false;
    }
    if (!formData.gender) {
      toast.error('El género es obligatorio');
      return false;
    }
    if (!formData.birth_date) {
      toast.error('La fecha de nacimiento es obligatoria');
      return false;
    }
    // Validar fecha no futura
    if (new Date(formData.birth_date) > new Date()) {
      toast.error('La fecha de nacimiento no puede ser futura');
      return false;
    }
    if (!formData.phone.trim()) {
      toast.error('El teléfono es obligatorio');
      return false;
    }
    // Validar DPI (13 dígitos si se proporciona)
    if (formData.dpi && (!/^\d{13}$/.test(formData.dpi))) {
      toast.error('El DPI debe tener exactamente 13 dígitos numéricos');
      return false;
    }
    // Validar email
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      toast.error('Formato de email inválido');
      return false;
    }
    if (!formData.referral_institution) {
      toast.error('La institución referente es obligatoria');
      return false;
    }
    // Validar unidad IGSS si es requerida
    if (formData.referral_institution === 'igss' && !formData.igss_unit_id) {
      toast.error('Debe seleccionar una unidad IGSS');
      return false;
    }
    // DPI obligatorio solo para pacientes IGSS
    if (formData.referral_institution === 'igss' && !formData.dpi.trim()) {
      toast.error('El DPI es obligatorio para pacientes IGSS');
      return false;
    }
    return true;
  };

  const checkDuplicate = async () => {
    try {
      const response = await patientApi.checkDuplicate({
        dpi: formData.dpi || undefined,
        first_name: formData.first_name,
        last_name: formData.last_name,
        birth_date: formData.birth_date,
        exclude_id: editingPatient?.id
      });
      
      if (response.data.exists) {
        setDuplicateInfo(response.data);
        setDuplicateDialogOpen(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error checking duplicate:', error);
      return false;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    // Verificar duplicados al crear
    if (!editingPatient) {
      const hasDuplicate = await checkDuplicate();
      if (hasDuplicate) return;
    }

    setSubmitting(true);
    try {
      const payload = { ...formData };
      
      // Limpiar campos condicionales
      if (payload.referral_institution !== 'igss') {
        payload.igss_unit_id = '';
        payload.igss_ordenes = [];
      }
      if (payload.referral_institution !== 'seguro_privado') {
        payload.insurance_name = '';
      }
      if (payload.referral_institution !== 'otra') {
        payload.other_institution_name = '';
      }

      if (editingPatient) {
        await patientApi.update(editingPatient.id, payload);
        toast.success('Paciente actualizado exitosamente');
      } else {
        await patientApi.create(payload);
        toast.success('Paciente creado exitosamente');
      }
      setDialogOpen(false);
      resetForm();
      fetchPatients();
    } catch (error) {
      const message = extractErrorMessage(error, 'Error al guardar el paciente');
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedPatient) return;
    
    setSubmitting(true);
    try {
      await patientApi.delete(selectedPatient.id);
      toast.success('Paciente desactivado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedPatient(null);
      fetchPatients();
    } catch (error) {
      const message = extractErrorMessage(error, 'Error al desactivar el paciente');
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReactivate = async (patient) => {
    try {
      await patientApi.reactivate(patient.id);
      toast.success('Paciente reactivado exitosamente');
      fetchPatients();
    } catch (error) {
      toast.error('Error al reactivar el paciente');
    }
  };

  const handleExportExcel = () => {
    const url = patientApi.exportExcel(filters);
    window.open(url, '_blank');
  };

  const handleExportPdf = () => {
    const url = patientApi.exportPdf(filters);
    window.open(url, '_blank');
  };

  const handleDownloadTemplate = () => {
    window.open(patientApi.downloadTemplate(), '_blank');
  };

  const clearFilters = () => {
    setFilters({
      referral_institution: '',
      igss_unit_id: '',
      igss_nog: '',
      gender: '',
      dateFrom: '',
      dateTo: '',
      is_active: true
    });
    setSearchTerm('');
    setPage(1);
  };

  const getGenderBadgeClass = (gender) => {
    const classes = {
      masculino: 'bg-blue-100 text-blue-700',
      femenino: 'bg-pink-100 text-pink-700',
      otro: 'bg-purple-100 text-purple-700'
    };
    return classes[gender] || 'bg-gray-100 text-gray-700';
  };

  const getInstitutionBadgeClass = (institution) => {
    const classes = {
      particular: 'bg-gray-100 text-gray-700',
      igss: 'bg-green-100 text-green-700',
      seguro_privado: 'bg-blue-100 text-blue-700',
      otra: 'bg-orange-100 text-orange-700'
    };
    return classes[institution] || 'bg-gray-100 text-gray-700';
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="pacientes-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Base de Datos de Pacientes
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestiona la información de los pacientes de la clínica
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button 
              variant="outline"
              onClick={fetchPatients}
              className="btn-outline"
              data-testid="refresh-button"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canExport && (
              <>
                <Button 
                  variant="outline"
                  onClick={handleExportExcel}
                  className="btn-outline"
                  data-testid="export-excel-button"
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  Excel
                </Button>
                <Button 
                  variant="outline"
                  onClick={handleExportPdf}
                  className="btn-outline"
                  data-testid="export-pdf-button"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  PDF
                </Button>
                <Button 
                  variant="outline"
                  onClick={handleDownloadTemplate}
                  className="btn-outline"
                  data-testid="download-template-button"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Plantilla
                </Button>
              </>
            )}
            {canCreate && (
              <Button 
                onClick={() => handleOpenDialog()}
                className="btn-primary"
                data-testid="add-patient-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Paciente
              </Button>
            )}
          </div>
        </div>

        {/* Summary Card */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-blue-100">
              <Users className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Pacientes</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {total}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Search and Filters */}
        <Card className="card-teal">
          <CardContent className="p-4 space-y-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por nombre, DPI, teléfono o expediente..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                  data-testid="search-patient"
                />
              </div>
              <Button type="submit" className="btn-primary">
                Buscar
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setFilterOpen(!filterOpen)}
                className="btn-outline"
              >
                <Filter className="w-4 h-4 mr-2" />
                Filtros
              </Button>
            </form>

            {filterOpen && (
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 pt-4 border-t">
                <div>
                  <Label className="text-xs">Institución Referente</Label>
                  <Select
                    value={filters.referral_institution}
                    onValueChange={(value) => setFilters(prev => ({
                      ...prev,
                      referral_institution: value === 'all' ? '' : value,
                      igss_unit_id: value === 'igss' ? prev.igss_unit_id : '',
                      igss_nog: value === 'igss' ? prev.igss_nog : ''
                    }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue placeholder="Todas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas</SelectItem>
                      {Object.entries(referralInstitutionLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Género</Label>
                  <Select
                    value={filters.gender}
                    onValueChange={(value) => setFilters(prev => ({ ...prev, gender: value === 'all' ? '' : value }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue placeholder="Todos" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {Object.entries(genderLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {filters.referral_institution === 'igss' && (
                  <>
                    <div>
                      <Label className="text-xs">Unidad IGSS</Label>
                      <Select
                        value={filters.igss_unit_id || 'all'}
                        onValueChange={(value) => setFilters(prev => ({ ...prev, igss_unit_id: value === 'all' ? '' : value, igss_nog: '' }))}
                      >
                        <SelectTrigger className="input-teal" data-testid="filter-igss-unit">
                          <SelectValue placeholder="Todas las unidades" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Todas las unidades</SelectItem>
                          {igssUnits.map((u) => (
                            <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">NOG</Label>
                      {filters.igss_unit_id && filterNogs.length > 0 ? (
                        <Select
                          value={filters.igss_nog || 'all'}
                          onValueChange={(value) => setFilters(prev => ({ ...prev, igss_nog: value === 'all' ? '' : value }))}
                        >
                          <SelectTrigger className="input-teal" data-testid="filter-igss-nog-select">
                            <SelectValue placeholder="Todos los NOG" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="all">Todos los NOG</SelectItem>
                            {filterNogs.map((n) => (
                              <SelectItem key={n.id} value={n.numero}>
                                {n.numero}{n.nombre_servicio ? ` — ${n.nombre_servicio}` : ''} ({n.pacientes_asignados || 0} pac. · {n.acreditados || 0}/{n.cantidad || 0})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          type="text"
                          value={filters.igss_nog}
                          onChange={(e) => setFilters(prev => ({ ...prev, igss_nog: e.target.value }))}
                          className="input-teal"
                          placeholder="Buscar por NOG..."
                          data-testid="filter-igss-nog"
                        />
                      )}
                    </div>
                  </>
                )}
                <div>
                  <Label className="text-xs">Fecha registro desde</Label>
                  <Input
                    type="date"
                    value={filters.dateFrom}
                    onChange={(e) => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                    className="input-teal"
                  />
                </div>
                <div>
                  <Label className="text-xs">Fecha registro hasta</Label>
                  <Input
                    type="date"
                    value={filters.dateTo}
                    onChange={(e) => setFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                    className="input-teal"
                  />
                </div>
                <div className="flex items-end">
                  <Button variant="outline" onClick={clearFilters} className="btn-outline w-full">
                    <X className="w-4 h-4 mr-2" />
                    Limpiar filtros
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Pacientes
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : patients.length === 0 ? (
              <div className="p-12 text-center">
                <Users className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  {searchTerm ? 'No se encontraron pacientes' : 'No hay pacientes registrados'}
                </p>
                {!searchTerm && canCreate && (
                  <Button 
                    onClick={() => handleOpenDialog()}
                    className="btn-primary mt-4"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer paciente
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Expediente</TableHead>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Género</TableHead>
                      <TableHead className="table-header text-center">Edad</TableHead>
                      <TableHead className="table-header">Teléfono</TableHead>
                      <TableHead className="table-header">Institución</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {patients.map((patient) => (
                      <TableRow 
                        key={patient.id} 
                        className={`table-row-hover ${!patient.is_active ? 'opacity-50' : ''}`}
                        data-testid={`patient-row-${patient.id}`}
                      >
                        <TableCell>
                          <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                            {patient.record_number}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div>
                            <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {patient.full_name}
                            </span>
                            {patient.dpi && (
                              <p className="text-xs" style={{ color: 'var(--text-hint)' }}>
                                DPI: {patient.dpi}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getGenderBadgeClass(patient.gender)}>
                            {genderLabels[patient.gender] || patient.gender}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {patient.age}
                          </span>
                          <span className="text-xs ml-1" style={{ color: 'var(--text-hint)' }}>años</span>
                        </TableCell>
                        <TableCell>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {patient.phone}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={getInstitutionBadgeClass(patient.referral_institution)}>
                            {patient.referral_institution_label || referralInstitutionLabels[patient.referral_institution]}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedPatient(patient);
                                setDetailDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`view-patient-${patient.id}`}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {canCreateEvaluacion && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => navigate(`/evaluacion-oftalmologica?paciente_id=${patient.id}`)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              title="Crear evaluación"
                              data-testid={`crear-evaluacion-patient-${patient.id}`}
                            >
                              <Stethoscope className="w-4 h-4" />
                            </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEvaluacionesPatient(patient);
                                setEvaluacionesDialogOpen(true);
                              }}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              title="Ver evaluaciones previas"
                              data-testid={`evaluaciones-patient-${patient.id}`}
                            >
                              <ClipboardList className="w-4 h-4" />
                            </Button>
                            {canEdit && patient.is_active && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenDialog(patient)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                data-testid={`edit-patient-${patient.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                            )}
                            {canDelete && patient.is_active && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setSelectedPatient(patient);
                                  setDeleteDialogOpen(true);
                                }}
                                className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                                data-testid={`delete-patient-${patient.id}`}
                              >
                                <UserX className="w-4 h-4" />
                              </Button>
                            )}
                            {canDelete && !patient.is_active && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleReactivate(patient)}
                                className="h-8 w-8 p-0 hover:bg-green-100 hover:text-green-600"
                                data-testid={`reactivate-patient-${patient.id}`}
                              >
                                <UserCheck className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Paginación */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t">
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Página {page} de {totalPages} ({total} pacientes)
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
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingPatient ? 'Editar Paciente' : 'Nuevo Paciente'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingPatient 
                  ? 'Actualiza los datos del paciente'
                  : 'Completa la información del nuevo paciente'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Datos personales */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">Nombre *</Label>
                  <Input
                    id="first_name"
                    value={formData.first_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                    className="input-teal"
                    placeholder="Nombre(s)"
                    data-testid="patient-first-name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name">Apellido *</Label>
                  <Input
                    id="last_name"
                    value={formData.last_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                    className="input-teal"
                    placeholder="Apellido(s)"
                    data-testid="patient-last-name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="gender">Género *</Label>
                  <Select
                    value={formData.gender}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, gender: value }))}
                  >
                    <SelectTrigger className="input-teal" data-testid="patient-gender">
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(genderLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="birth_date">Fecha de Nacimiento *</Label>
                  <Input
                    id="birth_date"
                    type="date"
                    value={formData.birth_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, birth_date: e.target.value }))}
                    className="input-teal"
                    max={getGuatemalaDate()}
                    data-testid="patient-birth-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Edad</Label>
                  <div className="h-10 px-3 py-2 rounded-md border bg-gray-50 flex items-center">
                    <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {formData.birth_date ? calculateAge(formData.birth_date) : '-'} años
                    </span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="profession">Profesión</Label>
                  <Input
                    id="profession"
                    value={formData.profession}
                    onChange={(e) => setFormData(prev => ({ ...prev, profession: e.target.value }))}
                    className="input-teal"
                    placeholder="Ej: Ingeniero, Médico, Estudiante"
                    data-testid="patient-profession"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dpi">DPI (13 dígitos){formData.referral_institution === 'igss' ? ' *' : ''}</Label>
                  <Input
                    id="dpi"
                    value={formData.dpi}
                    onChange={(e) => setFormData(prev => ({ ...prev, dpi: e.target.value.replace(/\D/g, '').slice(0, 13) }))}
                    className="input-teal"
                    placeholder="0000000000000"
                    maxLength={13}
                    data-testid="patient-dpi"
                  />
                </div>
              </div>

              {/* Estado Civil y Dirección */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="marital_status">Estado Civil</Label>
                  <Select
                    value={formData.marital_status}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, marital_status: value }))}
                  >
                    <SelectTrigger className="input-teal" data-testid="patient-marital-status">
                      <SelectValue placeholder="Seleccionar estado civil" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="soltero">Soltero(a)</SelectItem>
                      <SelectItem value="casado">Casado(a)</SelectItem>
                      <SelectItem value="unido">Unido(a)</SelectItem>
                      <SelectItem value="divorciado">Divorciado(a)</SelectItem>
                      <SelectItem value="viudo">Viudo(a)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="address">Dirección</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                    className="input-teal"
                    placeholder="Dirección completa del paciente"
                    data-testid="patient-address"
                  />
                </div>
              </div>

              {/* Contacto */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono *</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="input-teal"
                    placeholder="5555-1234"
                    data-testid="patient-phone"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="input-teal"
                    placeholder="correo@ejemplo.com"
                    data-testid="patient-email"
                  />
                </div>
              </div>

              {/* Contacto de emergencia */}
              <div className="border-t pt-4">
                <Label className="text-sm font-semibold mb-2 block">Contacto de Emergencia</Label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_name" className="text-xs">Nombre</Label>
                    <Input
                      id="emergency_contact_name"
                      value={formData.emergency_contact_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, emergency_contact_name: e.target.value }))}
                      className="input-teal"
                      placeholder="Nombre del contacto"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_relationship" className="text-xs">Parentesco</Label>
                    <Input
                      id="emergency_contact_relationship"
                      value={formData.emergency_contact_relationship}
                      onChange={(e) => setFormData(prev => ({ ...prev, emergency_contact_relationship: e.target.value }))}
                      className="input-teal"
                      placeholder="Ej: Esposo(a), Hijo(a)"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emergency_phone" className="text-xs">Teléfono</Label>
                    <Input
                      id="emergency_phone"
                      value={formData.emergency_phone}
                      onChange={(e) => setFormData(prev => ({ ...prev, emergency_phone: e.target.value }))}
                      className="input-teal"
                      placeholder="5555-0000"
                    />
                  </div>
                </div>
              </div>

              {/* Institución referente */}
              <div className="border-t pt-4">
                <Label className="text-sm font-semibold mb-2 block">Institución Referente *</Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Select
                      value={formData.referral_institution}
                      onValueChange={(value) => setFormData(prev => ({ 
                        ...prev, 
                        referral_institution: value,
                        igss_unit_id: value !== 'igss' ? '' : prev.igss_unit_id,
                        igss_afiliacion: value !== 'igss' ? '' : prev.igss_afiliacion,
                        igss_no_sps: value !== 'igss' ? '' : prev.igss_no_sps,
                        igss_codigo: value !== 'igss' ? '' : prev.igss_codigo,
                        igss_tipo_compra: value !== 'igss' ? '' : prev.igss_tipo_compra,
                        igss_nog: value !== 'igss' ? '' : prev.igss_nog,
                        igss_tipo_paciente: value !== 'igss' ? '' : prev.igss_tipo_paciente,
                        insurance_name: value !== 'seguro_privado' ? '' : prev.insurance_name,
                        other_institution_name: value !== 'otra' ? '' : prev.other_institution_name
                      }))}
                    >
                      <SelectTrigger className="input-teal" data-testid="patient-referral-institution">
                        <SelectValue placeholder="Seleccionar institución" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(referralInstitutionLabels).map(([key, label]) => (
                          <SelectItem key={key} value={key}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Campo condicional: Unidad IGSS */}
                  {formData.referral_institution === 'igss' && (
                    <div className="space-y-2">
                      <Label className="text-xs">Unidad IGSS *</Label>
                      <Select
                        value={formData.igss_unit_id}
                        onValueChange={(value) => setFormData(prev => ({ ...prev, igss_unit_id: value }))}
                      >
                        <SelectTrigger className="input-teal" data-testid="patient-igss-unit">
                          <SelectValue placeholder="Seleccionar unidad" />
                        </SelectTrigger>
                        <SelectContent>
                          {igssUnits.length === 0 ? (
                            <div className="px-2 py-1.5 text-sm text-gray-500">No hay unidades IGSS registradas</div>
                          ) : (
                            igssUnits.map((unit) => (
                              <SelectItem key={unit.id} value={unit.id}>{unit.name}</SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      {igssUnits.length === 0 && (
                        <p className="text-xs text-amber-600">
                          El administrador debe crear unidades IGSS en Configuración primero.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Campos adicionales IGSS */}
                  {formData.referral_institution === 'igss' && (
                    <>
                      <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                        <div className="space-y-2">
                          <Label className="text-xs">Afiliación</Label>
                          <Input
                            value={formData.igss_afiliacion}
                            onChange={(e) => setFormData(prev => ({ ...prev, igss_afiliacion: e.target.value }))}
                            className="input-teal"
                            placeholder="No. Afiliación"
                            data-testid="patient-igss-afiliacion"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs">Tipo de Compra</Label>
                          <Select
                            value={formData.igss_tipo_compra}
                            onValueChange={(value) => setFormData(prev => ({ ...prev, igss_tipo_compra: value }))}
                          >
                            <SelectTrigger className="input-teal" data-testid="patient-igss-tipo-compra">
                              <SelectValue placeholder="Seleccionar tipo" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="compra_directa">Compra Directa</SelectItem>
                              <SelectItem value="baja_cuantia">Baja Cuantía</SelectItem>
                              <SelectItem value="contrato">Contrato</SelectItem>
                              <SelectItem value="convenio">Convenio</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs">Tipo de Paciente</Label>
                          <Select
                            value={formData.igss_tipo_paciente || ''}
                            onValueChange={(value) => setFormData(prev => ({ ...prev, igss_tipo_paciente: value }))}
                          >
                            <SelectTrigger className="input-teal" data-testid="patient-igss-tipo-paciente">
                              <SelectValue placeholder="Seleccionar tipo" />
                            </SelectTrigger>
                            <SelectContent>
                              {['Afiliado', 'Esposa', 'Beneficiario Hijo', 'Pensionado', 'Jubilado'].map((t) => (
                                <SelectItem key={t} value={t}>{t}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Órdenes IGSS (una o varias por paciente) */}
                      <div className="md:col-span-2 space-y-2 pt-2" data-testid="patient-igss-ordenes">
                        <div className="flex items-center justify-between">
                          <Label className="text-sm font-semibold text-blue-700">Órdenes IGSS</Label>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={addOrdenIgss}
                            disabled={!formData.igss_unit_id}
                            className="h-7 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                            data-testid="patient-add-orden"
                          >
                            <Plus className="w-3 h-3 mr-1" /> Agregar orden
                          </Button>
                        </div>
                        {!formData.igss_unit_id && (
                          <p className="text-xs text-gray-500">Selecciona una unidad IGSS para agregar órdenes.</p>
                        )}
                        {(formData.igss_ordenes || []).length === 0 && formData.igss_unit_id && (
                          <p className="text-xs text-gray-500">Sin órdenes. Agrega al menos una con su NOG y No. SPS.</p>
                        )}
                        {(formData.igss_ordenes || []).map((orden, idx) => (
                          <div key={orden.id || idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 items-end border border-gray-100 rounded-lg p-2 bg-gray-50" data-testid={`patient-orden-row-${idx}`}>
                            <div className="md:col-span-3 space-y-1">
                              <Label className="text-xs">NOG {idx + 1}</Label>
                              <NogSelector
                                unitId={formData.igss_unit_id}
                                value={orden.nog}
                                onChange={(val) => updateOrdenIgss(idx, 'nog', val)}
                              />
                            </div>
                            <div className="md:col-span-2 space-y-1">
                              <Label className="text-xs">No. SPS</Label>
                              <Input
                                value={orden.no_sps || ''}
                                onChange={(e) => updateOrdenIgss(idx, 'no_sps', e.target.value)}
                                className="input-teal" placeholder="No. SPS"
                                data-testid={`patient-orden-sps-${idx}`}
                              />
                            </div>
                            <div className="md:col-span-2 space-y-1">
                              <Label className="text-xs">Código</Label>
                              <Input
                                value={orden.codigo || ''}
                                onChange={(e) => updateOrdenIgss(idx, 'codigo', e.target.value)}
                                className="input-teal" placeholder="Código"
                                data-testid={`patient-orden-codigo-${idx}`}
                              />
                            </div>
                            <div className="md:col-span-4 space-y-1">
                              <Label className="text-xs">Procedimiento / Estudio</Label>
                              <Input
                                value={orden.procedimiento || ''}
                                onChange={(e) => updateOrdenIgss(idx, 'procedimiento', e.target.value)}
                                className="input-teal" placeholder="Ej: Catarata OD"
                                data-testid={`patient-orden-proc-${idx}`}
                              />
                            </div>
                            <div className="md:col-span-1 flex justify-end">
                              <Button
                                type="button" variant="ghost" size="sm"
                                onClick={() => removeOrdenIgss(idx)}
                                className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                                data-testid={`patient-orden-remove-${idx}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {/* Campo condicional: Nombre de aseguradora */}
                  {formData.referral_institution === 'seguro_privado' && (
                    <div className="space-y-2">
                      <Label className="text-xs">Nombre de la Aseguradora</Label>
                      <Input
                        value={formData.insurance_name}
                        onChange={(e) => setFormData(prev => ({ ...prev, insurance_name: e.target.value }))}
                        className="input-teal"
                        placeholder="Ej: Seguros G&T, El Roble"
                        data-testid="patient-insurance-name"
                      />
                    </div>
                  )}

                  {/* Campo condicional: Otra institución */}
                  {formData.referral_institution === 'otra' && (
                    <div className="space-y-2">
                      <Label className="text-xs">Nombre de la Institución</Label>
                      <Input
                        value={formData.other_institution_name}
                        onChange={(e) => setFormData(prev => ({ ...prev, other_institution_name: e.target.value }))}
                        className="input-teal"
                        placeholder="Nombre de la institución"
                        data-testid="patient-other-institution"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Comentarios */}
              <div className="space-y-2">
                <Label htmlFor="comments">Comentarios</Label>
                <Textarea
                  id="comments"
                  value={formData.comments}
                  onChange={(e) => setFormData(prev => ({ ...prev, comments: e.target.value }))}
                  className="input-teal min-h-[80px]"
                  placeholder="Observaciones, antecedentes médicos relevantes, etc."
                  data-testid="patient-comments"
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
                  data-testid="submit-patient-button"
                >
                  {submitting 
                    ? (editingPatient ? 'Guardando...' : 'Creando...') 
                    : (editingPatient ? 'Guardar cambios' : 'Crear paciente')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Detalle del Paciente
              </DialogTitle>
            </DialogHeader>
            {selectedPatient && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-2xl font-bold text-blue-600">
                      {selectedPatient.first_name?.charAt(0)}{selectedPatient.last_name?.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                      {selectedPatient.full_name}
                    </h3>
                    <p className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {selectedPatient.record_number}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Género</p>
                    <p style={{ color: 'var(--text-primary)' }}>{genderLabels[selectedPatient.gender]}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Edad</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.age} años</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Fecha de Nacimiento</p>
                    <p style={{ color: 'var(--text-primary)' }}>{formatDate(selectedPatient.birth_date)}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Profesión</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.profession || '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Teléfono</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.phone}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Email</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.email || '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>DPI</p>
                    <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.dpi || '-'}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--text-hint)' }}>Institución</p>
                    <p style={{ color: 'var(--text-primary)' }}>
                      {selectedPatient.referral_institution_label}
                      {selectedPatient.igss_unit_name && ` - ${selectedPatient.igss_unit_name}`}
                      {selectedPatient.insurance_name && ` - ${selectedPatient.insurance_name}`}
                      {selectedPatient.other_institution_name && ` - ${selectedPatient.other_institution_name}`}
                    </p>
                  </div>
                  {selectedPatient.referral_institution === 'igss' && selectedPatient.igss_tipo_paciente && (
                    <div>
                      <p style={{ color: 'var(--text-hint)' }}>Tipo de Paciente</p>
                      <p style={{ color: 'var(--text-primary)' }}>{selectedPatient.igss_tipo_paciente}</p>
                    </div>
                  )}
                  {selectedPatient.referral_institution === 'igss' && selectedPatient.igss_nog && (
                    <div>
                      <p style={{ color: 'var(--text-hint)' }}>NOG</p>
                      <p style={{ color: 'var(--text-primary)' }} data-testid="view-patient-igss-nog">{selectedPatient.igss_nog}</p>
                    </div>
                  )}
                </div>

                {selectedPatient.emergency_contact_name && (
                  <div className="border-t pt-4">
                    <p className="font-semibold text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
                      Contacto de Emergencia
                    </p>
                    <p style={{ color: 'var(--text-secondary)' }}>
                      {selectedPatient.emergency_contact_name}
                      {selectedPatient.emergency_contact_relationship && ` (${selectedPatient.emergency_contact_relationship})`}
                      {selectedPatient.emergency_phone && ` - Tel: ${selectedPatient.emergency_phone}`}
                    </p>
                  </div>
                )}

                {selectedPatient.comments && (
                  <div className="border-t pt-4">
                    <p className="font-semibold text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
                      Comentarios
                    </p>
                    <p style={{ color: 'var(--text-secondary)' }}>
                      {selectedPatient.comments}
                    </p>
                  </div>
                )}

                <div className="border-t pt-4 text-xs" style={{ color: 'var(--text-hint)' }}>
                  <p>Registrado: {formatDate(selectedPatient.created_at)} por {selectedPatient.created_by_name}</p>
                  {selectedPatient.updated_by_name && (
                    <p>Última modificación: {formatDate(selectedPatient.updated_at)} por {selectedPatient.updated_by_name}</p>
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              {canEdit && selectedPatient?.is_active && (
                <Button 
                  onClick={() => {
                    setDetailDialogOpen(false);
                    handleOpenDialog(selectedPatient);
                  }}
                  className="btn-primary"
                >
                  <Pencil className="w-4 h-4 mr-2" />
                  Editar
                </Button>
              )}
              <Button 
                variant="outline" 
                onClick={() => setDetailDialogOpen(false)}
                className="btn-outline"
              >
                Cerrar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Diálogo de evaluaciones previas del paciente */}
        <EvaluacionesPacienteDialog
          patient={evaluacionesPatient}
          open={evaluacionesDialogOpen}
          onOpenChange={setEvaluacionesDialogOpen}
        />

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                Desactivar Paciente
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de desactivar al paciente &quot;{selectedPatient?.full_name}&quot;? 
                El registro no será eliminado y podrá ser reactivado posteriormente.
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
                {submitting ? 'Desactivando...' : 'Desactivar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Duplicate Warning Dialog */}
        <Dialog open={duplicateDialogOpen} onOpenChange={setDuplicateDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="text-amber-600">
                Posible Paciente Duplicado
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                Se encontró un paciente con datos similares:
              </DialogDescription>
            </DialogHeader>
            {duplicateInfo && (
              <div className="p-4 bg-amber-50 rounded-lg">
                <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {duplicateInfo.patient_name}
                </p>
                <p className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                  {duplicateInfo.patient_record_number}
                </p>
                <p className="text-xs mt-2" style={{ color: 'var(--text-hint)' }}>
                  Coincidencia por: {duplicateInfo.match_type === 'dpi' ? 'DPI' : 'Nombre y fecha de nacimiento'}
                </p>
              </div>
            )}
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => {
                  setDuplicateDialogOpen(false);
                  // Abrir el paciente existente
                  if (duplicateInfo?.patient_id) {
                    patientApi.getById(duplicateInfo.patient_id).then(res => {
                      setSelectedPatient(res.data);
                      setDetailDialogOpen(true);
                    });
                  }
                }}
                className="btn-outline"
              >
                Ver paciente existente
              </Button>
              <Button 
                onClick={() => {
                  setDuplicateDialogOpen(false);
                  setDialogOpen(false);
                }}
                className="btn-primary"
              >
                Cancelar registro
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Pacientes;
