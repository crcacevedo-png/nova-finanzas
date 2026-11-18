import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { toast } from 'sonner';
import { OrdenesIgssPaciente } from './igss/OrdenesIgssPaciente';
import { OrdenesIgssFicha } from './igss/OrdenesIgssFicha';
import { puedeVerLibroIgss } from '../lib/igssLibro';
import { useAuth } from '../context/AuthContext';
import {
  patientApi,
  igssUnitApi,
  referralInstitutionLabels,
  genderLabels,
  calculateAge,
  getGuatemalaDate,
} from '../services/api';

const emptyForm = {
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
  comments: '',
};

const extractErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg || (typeof d === 'string' ? d : JSON.stringify(d))).join(', ');
  if (typeof detail === 'string') return detail;
  return fallback;
};

// Diálogo de edición completa de un paciente, pensado para usarse desde
// Sala de Operaciones / Editar cirugía (fuera del módulo general de Pacientes).
export const PatientEditDialog = ({ open, onOpenChange, patientId, onSaved }) => {
  const { user } = useAuth();
  const [formData, setFormData] = useState(emptyForm);
  const [igssUnits, setIgssUnits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadIgssUnits = useCallback(async () => {
    try {
      const res = await igssUnitApi.getAll();
      setIgssUnits(res.data.data || []);
    } catch (error) {
      // silencioso: el select simplemente queda vacío
    }
  }, []);

  const loadPatient = useCallback(async () => {
    if (!patientId) return;
    setLoading(true);
    try {
      const res = await patientApi.getById(patientId);
      const p = res.data;
      setFormData({
        first_name: p.first_name || '',
        last_name: p.last_name || '',
        gender: p.gender || '',
        birth_date: p.birth_date || '',
        profession: p.profession || '',
        phone: p.phone || '',
        email: p.email || '',
        dpi: p.dpi || '',
        address: p.address || '',
        marital_status: p.marital_status || '',
        emergency_phone: p.emergency_phone || '',
        emergency_contact_name: p.emergency_contact_name || '',
        emergency_contact_relationship: p.emergency_contact_relationship || '',
        referral_institution: p.referral_institution || '',
        insurance_name: p.insurance_name || '',
        other_institution_name: p.other_institution_name || '',
        igss_unit_id: p.igss_unit_id || '',
        igss_afiliacion: p.igss_afiliacion || '',
        igss_no_sps: p.igss_no_sps || '',
        igss_codigo: p.igss_codigo || '',
        igss_tipo_compra: p.igss_tipo_compra || '',
        igss_nog: p.igss_nog || '',
        igss_tipo_paciente: p.igss_tipo_paciente || '',
        igss_ordenes: (p.igss_ordenes && p.igss_ordenes.length > 0) ? p.igss_ordenes.map((o) => ({ ...o })) : [],
        comments: p.comments || '',
      });
    } catch (error) {
      toast.error('No se pudo cargar la información del paciente');
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  }, [patientId, onOpenChange]);

  useEffect(() => {
    if (open && patientId) {
      loadPatient();
      loadIgssUnits();
    }
  }, [open, patientId, loadPatient, loadIgssUnits]);

  const validateForm = () => {
    if (!formData.first_name.trim()) { toast.error('El nombre es obligatorio'); return false; }
    if (!formData.last_name.trim()) { toast.error('El apellido es obligatorio'); return false; }
    if (!formData.gender) { toast.error('El género es obligatorio'); return false; }
    if (!formData.birth_date) { toast.error('La fecha de nacimiento es obligatoria'); return false; }
    if (new Date(formData.birth_date) > new Date()) { toast.error('La fecha de nacimiento no puede ser futura'); return false; }
    if (!formData.phone.trim()) { toast.error('El teléfono es obligatorio'); return false; }
    if (formData.dpi && (!/^\d{13}$/.test(formData.dpi))) { toast.error('El DPI debe tener exactamente 13 dígitos numéricos'); return false; }
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { toast.error('Formato de email inválido'); return false; }
    if (!formData.referral_institution) { toast.error('La institución referente es obligatoria'); return false; }
    if (formData.referral_institution === 'igss' && !formData.igss_unit_id) { toast.error('Debe seleccionar una unidad IGSS'); return false; }
    if (formData.referral_institution === 'igss' && !formData.dpi.trim()) { toast.error('El DPI es obligatorio para pacientes IGSS'); return false; }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    try {
      // Las órdenes IGSS (No. SPS / NOG) se manejan en el libro, no con el expediente
      const { igss_ordenes, igss_nog, igss_no_sps, igss_codigo, ...payload } = formData;
      if (payload.referral_institution !== 'igss') {
        payload.igss_unit_id = '';
      }
      if (payload.referral_institution !== 'seguro_privado') payload.insurance_name = '';
      if (payload.referral_institution !== 'otra') payload.other_institution_name = '';

      await patientApi.update(patientId, payload);
      toast.success('Paciente actualizado exitosamente');
      onOpenChange(false);
      if (onSaved) onSaved();
    } catch (error) {
      toast.error(extractErrorMessage(error, 'Error al guardar el paciente'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto" data-testid="surgery-patient-edit-dialog">
        <DialogHeader>
          <DialogTitle>Editar Paciente</DialogTitle>
          <DialogDescription>Actualiza los datos del paciente vinculado a esta cirugía</DialogDescription>
        </DialogHeader>
        {loading ? (
          <div className="py-10 text-center text-sm text-slate-400">Cargando datos del paciente...</div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="pe-first-name">Nombre *</Label>
                <Input id="pe-first-name" value={formData.first_name} onChange={(e) => setFormData((p) => ({ ...p, first_name: e.target.value }))} placeholder="Nombre(s)" data-testid="patient-edit-first-name" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pe-last-name">Apellido *</Label>
                <Input id="pe-last-name" value={formData.last_name} onChange={(e) => setFormData((p) => ({ ...p, last_name: e.target.value }))} placeholder="Apellido(s)" data-testid="patient-edit-last-name" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Género *</Label>
                <Select value={formData.gender} onValueChange={(value) => setFormData((p) => ({ ...p, gender: value }))}>
                  <SelectTrigger data-testid="patient-edit-gender"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(genderLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="pe-birth-date">Fecha de Nacimiento *</Label>
                <Input id="pe-birth-date" type="date" value={formData.birth_date} onChange={(e) => setFormData((p) => ({ ...p, birth_date: e.target.value }))} max={getGuatemalaDate()} data-testid="patient-edit-birth-date" />
              </div>
              <div className="space-y-2">
                <Label>Edad</Label>
                <div className="h-10 px-3 py-2 rounded-md border bg-gray-50 flex items-center">
                  <span className="font-semibold">{formData.birth_date ? calculateAge(formData.birth_date) : '-'} años</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="pe-profession">Profesión</Label>
                <Input id="pe-profession" value={formData.profession} onChange={(e) => setFormData((p) => ({ ...p, profession: e.target.value }))} placeholder="Ej: Ingeniero, Médico, Estudiante" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pe-dpi">DPI (13 dígitos){formData.referral_institution === 'igss' ? ' *' : ''}</Label>
                <Input id="pe-dpi" value={formData.dpi} onChange={(e) => setFormData((p) => ({ ...p, dpi: e.target.value.replace(/\D/g, '').slice(0, 13) }))} placeholder="0000000000000" maxLength={13} data-testid="patient-edit-dpi" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Estado Civil</Label>
                <Select value={formData.marital_status} onValueChange={(value) => setFormData((p) => ({ ...p, marital_status: value }))}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar estado civil" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="soltero">Soltero(a)</SelectItem>
                    <SelectItem value="casado">Casado(a)</SelectItem>
                    <SelectItem value="unido">Unido(a)</SelectItem>
                    <SelectItem value="divorciado">Divorciado(a)</SelectItem>
                    <SelectItem value="viudo">Viudo(a)</SelectItem>
                    <SelectItem value="infante">Infante</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="pe-address">Dirección</Label>
                <Input id="pe-address" value={formData.address} onChange={(e) => setFormData((p) => ({ ...p, address: e.target.value }))} placeholder="Dirección completa del paciente" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="pe-phone">Teléfono *</Label>
                <Input id="pe-phone" value={formData.phone} onChange={(e) => setFormData((p) => ({ ...p, phone: e.target.value }))} placeholder="5555-1234" data-testid="patient-edit-phone" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pe-email">Email</Label>
                <Input id="pe-email" type="email" value={formData.email} onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))} placeholder="correo@ejemplo.com" />
              </div>
            </div>

            <div className="border-t pt-4">
              <Label className="text-sm font-semibold mb-2 block">Contacto de Emergencia</Label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs">Nombre</Label>
                  <Input value={formData.emergency_contact_name} onChange={(e) => setFormData((p) => ({ ...p, emergency_contact_name: e.target.value }))} placeholder="Nombre del contacto" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Parentesco</Label>
                  <Input value={formData.emergency_contact_relationship} onChange={(e) => setFormData((p) => ({ ...p, emergency_contact_relationship: e.target.value }))} placeholder="Ej: Esposo(a), Hijo(a)" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Teléfono</Label>
                  <Input value={formData.emergency_phone} onChange={(e) => setFormData((p) => ({ ...p, emergency_phone: e.target.value }))} placeholder="5555-0000" />
                </div>
              </div>
            </div>

            <div className="border-t pt-4">
              <Label className="text-sm font-semibold mb-2 block">Institución Referente *</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Select
                    value={formData.referral_institution}
                    onValueChange={(value) => setFormData((prev) => ({
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
                      other_institution_name: value !== 'otra' ? '' : prev.other_institution_name,
                    }))}
                  >
                    <SelectTrigger data-testid="patient-edit-referral-institution"><SelectValue placeholder="Seleccionar institución" /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(referralInstitutionLabels).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {formData.referral_institution === 'igss' && (
                  <div className="space-y-2">
                    <Label className="text-xs">Unidad IGSS *</Label>
                    <Select value={formData.igss_unit_id} onValueChange={(value) => setFormData((p) => ({ ...p, igss_unit_id: value }))}>
                      <SelectTrigger data-testid="patient-edit-igss-unit"><SelectValue placeholder="Seleccionar unidad" /></SelectTrigger>
                      <SelectContent>
                        {igssUnits.length === 0 ? (
                          <div className="px-2 py-1.5 text-sm text-gray-500">No hay unidades IGSS registradas</div>
                        ) : (
                          igssUnits.map((unit) => <SelectItem key={unit.id} value={unit.id}>{unit.name}</SelectItem>)
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {formData.referral_institution === 'igss' && (
                  <>
                    <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                      <div className="space-y-2">
                        <Label className="text-xs">Afiliación</Label>
                        <Input value={formData.igss_afiliacion} onChange={(e) => setFormData((p) => ({ ...p, igss_afiliacion: e.target.value }))} placeholder="No. Afiliación" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">Tipo de Compra</Label>
                        <Select value={formData.igss_tipo_compra} onValueChange={(value) => setFormData((p) => ({ ...p, igss_tipo_compra: value }))}>
                          <SelectTrigger><SelectValue placeholder="Seleccionar tipo" /></SelectTrigger>
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
                        <Select value={formData.igss_tipo_paciente || ''} onValueChange={(value) => setFormData((p) => ({ ...p, igss_tipo_paciente: value }))}>
                          <SelectTrigger><SelectValue placeholder="Seleccionar tipo" /></SelectTrigger>
                          <SelectContent>
                            {['Afiliado', 'Esposa', 'Beneficiario Hijo', 'Pensionado', 'Jubilado'].map((t) => (
                              <SelectItem key={t} value={t}>{t}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="md:col-span-2 pt-2" data-testid="patient-edit-igss-ordenes">
                      {puedeVerLibroIgss(user)
                        ? <OrdenesIgssPaciente pacienteId={patientId} unidadId={formData.igss_unit_id} />
                        : <OrdenesIgssFicha pacienteId={patientId} />}
                    </div>
                  </>
                )}

                {formData.referral_institution === 'seguro_privado' && (
                  <div className="space-y-2">
                    <Label className="text-xs">Nombre de la Aseguradora</Label>
                    <Input value={formData.insurance_name} onChange={(e) => setFormData((p) => ({ ...p, insurance_name: e.target.value }))} placeholder="Ej: Seguros G&T, El Roble" />
                  </div>
                )}

                {formData.referral_institution === 'otra' && (
                  <div className="space-y-2">
                    <Label className="text-xs">Nombre de la Institución</Label>
                    <Input value={formData.other_institution_name} onChange={(e) => setFormData((p) => ({ ...p, other_institution_name: e.target.value }))} placeholder="Nombre de la institución" />
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pe-comments">Comentarios</Label>
              <Textarea id="pe-comments" value={formData.comments} onChange={(e) => setFormData((p) => ({ ...p, comments: e.target.value }))} className="min-h-[80px]" placeholder="Observaciones, antecedentes médicos relevantes, etc." />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
              <Button type="submit" disabled={submitting} data-testid="patient-edit-submit">
                {submitting ? 'Guardando...' : 'Guardar cambios'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
