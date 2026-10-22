import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Stethoscope,
  Search,
  Phone,
  Mail,
  Upload
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
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
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { toast, Toaster } from 'sonner';
import { doctorApi } from '../services/api';

// Días de la semana (isoweekday: 1=Lunes .. 7=Domingo)
const DIAS_SEMANA = [
  { num: '1', label: 'Lunes' },
  { num: '2', label: 'Martes' },
  { num: '3', label: 'Miércoles' },
  { num: '4', label: 'Jueves' },
  { num: '5', label: 'Viernes' },
  { num: '6', label: 'Sábado' },
  { num: '7', label: 'Domingo' },
];

const buildHorario = (existente) => {
  const base = {};
  DIAS_SEMANA.forEach(({ num }) => {
    const prev = existente?.[num] || {};
    base[num] = {
      activo: prev.activo || false,
      hora_inicio: prev.hora_inicio || '08:00',
      hora_fin: prev.hora_fin || '17:00',
    };
  });
  return base;
};

const Medicos = () => {
  const { hasPermission } = useAuth();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState(null);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    specialty: '',
    phone: '',
    email: '',
    license_number: '',
    notes: '',
    firma_digital: '',
    horario: buildHorario(null)
  });

  const canManage = hasPermission('manage_doctors');

  const fetchDoctors = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const response = await doctorApi.getAll(searchTerm);
      const nuevos = response.data.data || [];
      if (silent) {
        const previos = knownDoctorIdsRef.current;
        const nuevosDeOtros = previos.size > 0 ? nuevos.filter((d) => !previos.has(d.id)) : [];
        if (nuevosDeOtros.length > 0) {
          toast.info(`Se agregó ${nuevosDeOtros.length} médico(s) nuevo(s)`, { duration: 3000 });
        }
      }
      setDoctors(nuevos);
    } catch (error) {
      console.error('Error fetching doctors:', error);
      if (!silent) toast.error('Error al cargar médicos');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [searchTerm]);

  // Detección de médicos nuevos agregados por otros usuarios (aviso discreto)
  const knownDoctorIdsRef = useRef(new Set());
  useEffect(() => {
    knownDoctorIdsRef.current = new Set((doctors || []).map((d) => d.id));
  }, [doctors]);

  useEffect(() => {
    fetchDoctors();
  }, [fetchDoctors]);

  // Auto-actualización en tiempo real: refresca la lista cada 15s en segundo
  // plano para que, con varios usuarios simultáneos, los médicos nuevos
  // aparezcan sin necesidad de recargar la página.
  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) fetchDoctors(true);
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchDoctors]);

  const handleOpenDialog = (doctor = null) => {
    if (doctor) {
      setEditingDoctor(doctor);
      setFormData({
        name: doctor.name || '',
        specialty: doctor.specialty || '',
        phone: doctor.phone || '',
        email: doctor.email || '',
        license_number: doctor.license_number || '',
        notes: doctor.notes || '',
        firma_digital: doctor.firma_digital || '',
        horario: buildHorario(doctor.horario_semanal)
      });
    } else {
      setEditingDoctor(null);
      setFormData({
        name: '',
        specialty: '',
        phone: '',
        email: '',
        license_number: '',
        notes: '',
        firma_digital: '',
        horario: buildHorario(null)
      });
    }
    setDialogOpen(true);
  };

  const handleFirmaUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Selecciona un archivo de imagen');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = new Image();
      img.onload = () => {
        const maxDim = 400;
        let { width, height } = img;
        const scale = Math.min(1, maxDim / Math.max(width, height));
        width = Math.round(width * scale);
        height = Math.round(height * scale);
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        setFormData(prev => ({ ...prev, firma_digital: canvas.toDataURL('image/png') }));
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    const algunDiaActivo = Object.values(formData.horario || {}).some(d => d?.activo);
    const payload = {
      name: formData.name.trim(),
      specialty: formData.specialty.trim(),
      phone: formData.phone.trim(),
      email: formData.email.trim(),
      license_number: formData.license_number.trim(),
      notes: formData.notes.trim(),
      firma_digital: formData.firma_digital || '',
      horario_semanal: algunDiaActivo ? formData.horario : null
    };

    setSubmitting(true);
    try {
      if (editingDoctor) {
        await doctorApi.update(editingDoctor.id, payload);
        toast.success('Médico actualizado exitosamente');
      } else {
        await doctorApi.create(payload);
        toast.success('Médico creado exitosamente');
      }
      setDialogOpen(false);
      fetchDoctors();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedDoctor) return;
    
    setSubmitting(true);
    try {
      await doctorApi.delete(selectedDoctor.id);
      toast.success('Médico eliminado exitosamente');
      setDeleteDialogOpen(false);
      setSelectedDoctor(null);
      fetchDoctors();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  // Obtener iniciales del nombre
  const getInitials = (name) => {
    if (!name) return '??';
    const parts = name.replace(/^(Dr\.?|Dra\.?)\s*/i, '').split(' ');
    if (parts.length >= 2) {
      return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
    }
    return parts[0].charAt(0).toUpperCase();
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="medicos-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Médicos
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Base de datos de médicos referentes
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchDoctors} className="btn-outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Actualizar
            </Button>
            {canManage && (
              <Button onClick={() => handleOpenDialog()} className="btn-primary" data-testid="add-doctor-button">
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Médico
              </Button>
            )}
          </div>
        </div>

        {/* Stats */}
        <Card className="card-metrics border-0 shadow-none">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-blue-100">
              <Stethoscope className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Médicos</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{doctors.length}</p>
            </div>
          </CardContent>
        </Card>

        {/* Search */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por nombre o especialidad..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-teal pl-10"
                data-testid="search-doctor"
              />
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Médicos ({doctors.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : doctors.length === 0 ? (
              <div className="p-12 text-center">
                <Stethoscope className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay médicos registrados</p>
                {canManage && (
                  <Button onClick={() => handleOpenDialog()} className="btn-primary mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Agregar primer médico
                  </Button>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Especialidad</TableHead>
                      <TableHead className="table-header">No. Licencia</TableHead>
                      <TableHead className="table-header">Contacto</TableHead>
                      {canManage && <TableHead className="table-header text-right">Acciones</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doctors.map((doctor) => (
                      <TableRow key={doctor.id} className="table-row-hover" data-testid={`doctor-row-${doctor.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div 
                              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-sm"
                              style={{ background: 'linear-gradient(135deg, #0F6E56, #1D9E75)' }}
                            >
                              {getInitials(doctor.name)}
                            </div>
                            <div>
                              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                                {doctor.name}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          {doctor.specialty ? (
                            <Badge className="bg-blue-100 text-blue-700">{doctor.specialty}</Badge>
                          ) : (
                            <span style={{ color: 'var(--text-hint)' }}>-</span>
                          )}
                        </TableCell>
                        <TableCell style={{ color: 'var(--text-secondary)' }}>
                          {doctor.license_number || '-'}
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {doctor.phone && (
                              <div className="flex items-center gap-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                                <Phone className="w-3 h-3" />
                                <span>{doctor.phone}</span>
                              </div>
                            )}
                            {doctor.email && (
                              <div className="flex items-center gap-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                                <Mail className="w-3 h-3" />
                                <span>{doctor.email}</span>
                              </div>
                            )}
                            {!doctor.phone && !doctor.email && (
                              <span style={{ color: 'var(--text-hint)' }}>-</span>
                            )}
                          </div>
                        </TableCell>
                        {canManage && (
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleOpenDialog(doctor)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                data-testid={`edit-doctor-${doctor.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setSelectedDoctor(doctor); setDeleteDialogOpen(true); }}
                                className="h-8 w-8 p-0 hover:bg-red-100 hover:text-red-600"
                                data-testid={`delete-doctor-${doctor.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingDoctor ? 'Editar Médico' : 'Nuevo Médico'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingDoctor ? 'Actualiza los datos del médico' : 'Ingresa los datos del nuevo médico'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre Completo *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="input-teal"
                  placeholder="Dr. Juan Pérez"
                  data-testid="doctor-name"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="specialty">Especialidad</Label>
                  <Input
                    id="specialty"
                    value={formData.specialty}
                    onChange={(e) => setFormData(prev => ({ ...prev, specialty: e.target.value }))}
                    className="input-teal"
                    placeholder="Oftalmología"
                    data-testid="doctor-specialty"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="license_number">No. Licencia</Label>
                  <Input
                    id="license_number"
                    value={formData.license_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, license_number: e.target.value }))}
                    className="input-teal"
                    placeholder="12345"
                    data-testid="doctor-license"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="input-teal"
                    placeholder="5555-1234"
                    data-testid="doctor-phone"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Correo</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                    className="input-teal"
                    placeholder="doctor@clinica.com"
                    data-testid="doctor-email"
                  />
                </div>
              </div>

              {/* Horario de disponibilidad semanal */}
              <div className="space-y-2 rounded-lg border p-3" data-testid="doctor-horario-section">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold">Horario de disponibilidad</Label>
                  <span className="text-xs text-slate-500">Activa los días y define la franja de atención</span>
                </div>
                <div className="space-y-1.5">
                  {DIAS_SEMANA.map(({ num, label }) => {
                    const dia = formData.horario[num];
                    return (
                      <div key={num} className="flex items-center gap-2" data-testid={`horario-dia-${num}`}>
                        <div className="flex items-center gap-2 w-32 shrink-0">
                          <Switch
                            checked={dia.activo}
                            onCheckedChange={(v) => setFormData(prev => ({
                              ...prev,
                              horario: { ...prev.horario, [num]: { ...prev.horario[num], activo: v } }
                            }))}
                            data-testid={`horario-activo-${num}`}
                          />
                          <span className={`text-sm ${dia.activo ? 'text-slate-800 font-medium' : 'text-slate-400'}`}>{label}</span>
                        </div>
                        <Input
                          type="time"
                          value={dia.hora_inicio}
                          disabled={!dia.activo}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            horario: { ...prev.horario, [num]: { ...prev.horario[num], hora_inicio: e.target.value } }
                          }))}
                          className="h-8 w-28"
                          data-testid={`horario-inicio-${num}`}
                        />
                        <span className="text-slate-400 text-sm">a</span>
                        <Input
                          type="time"
                          value={dia.hora_fin}
                          disabled={!dia.activo}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            horario: { ...prev.horario, [num]: { ...prev.horario[num], hora_fin: e.target.value } }
                          }))}
                          className="h-8 w-28"
                          data-testid={`horario-fin-${num}`}
                        />
                      </div>
                    );
                  })}
                </div>
                <p className="text-xs text-slate-500">Si no activas ningún día, el médico queda sin restricción de horario.</p>
              </div>

              {/* Firma digital del médico */}
              <div className="space-y-2 rounded-lg border p-3" data-testid="doctor-firma-section">
                <Label className="text-sm font-semibold">Firma digital</Label>
                <p className="text-xs text-slate-500">Se incluirá en el expediente impreso (máx. 3 cm × 2 cm).</p>
                {formData.firma_digital ? (
                  <div className="flex items-center gap-3">
                    <img
                      src={formData.firma_digital}
                      alt="Firma del médico"
                      className="h-16 border rounded bg-white object-contain px-2"
                      data-testid="doctor-firma-preview"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="btn-outline"
                      onClick={() => setFormData(prev => ({ ...prev, firma_digital: '' }))}
                      data-testid="doctor-firma-remove"
                    >
                      <Trash2 className="w-4 h-4 mr-1" /> Quitar
                    </Button>
                  </div>
                ) : (
                  <label
                    className="inline-flex items-center gap-2 cursor-pointer text-sm text-teal-700 border border-dashed border-teal-300 rounded px-3 py-2 hover:bg-teal-50 transition-colors"
                    data-testid="doctor-firma-upload-label"
                  >
                    <Upload className="w-4 h-4" /> Subir imagen de firma
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleFirmaUpload}
                      data-testid="doctor-firma-input"
                    />
                  </label>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="submit-doctor">
                  {submitting ? 'Guardando...' : (editingDoctor ? 'Guardar' : 'Crear')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Médico</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de eliminar a {selectedDoctor?.name}?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
                Cancelar
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={submitting} data-testid="confirm-delete-doctor">
                {submitting ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Medicos;
