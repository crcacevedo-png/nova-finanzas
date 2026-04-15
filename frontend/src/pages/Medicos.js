import React, { useState, useEffect, useCallback } from 'react';
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
  Mail
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
    notes: ''
  });

  const canManage = hasPermission('manage_doctors');

  const fetchDoctors = useCallback(async () => {
    try {
      setLoading(true);
      const response = await doctorApi.getAll(searchTerm);
      setDoctors(response.data.data || []);
    } catch (error) {
      console.error('Error fetching doctors:', error);
      toast.error('Error al cargar médicos');
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    fetchDoctors();
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
        notes: doctor.notes || ''
      });
    } else {
      setEditingDoctor(null);
      setFormData({
        name: '',
        specialty: '',
        phone: '',
        email: '',
        license_number: '',
        notes: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }

    const payload = {
      name: formData.name.trim(),
      specialty: formData.specialty.trim(),
      phone: formData.phone.trim(),
      email: formData.email.trim(),
      license_number: formData.license_number.trim(),
      notes: formData.notes.trim()
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
            <div className="p-3 rounded-xl bg-teal-100">
              <Stethoscope className="w-5 h-5 text-teal-600" />
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
          <DialogContent className="sm:max-w-[500px]">
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
