// /app/frontend/src/pages/Agenda.js
// Módulo de Agenda de Pacientes - Vista principal con submenú

import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { useAgendaWebSocket } from '../hooks/useWebSocket';
import { 
  Calendar, Clock, Users, UserCheck, ChevronLeft, ChevronRight, Plus, 
  RefreshCw, Search, Filter, MoreVertical, Play, CheckCircle, XCircle,
  AlertCircle, Phone, Eye, Printer, Settings, User, CalendarDays, Wifi, WifiOff
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import { agendaApi } from '../services/agendaApi';
import { patientApi, googleCalendarApi } from '../services/api';
import { GoogleCalendarDialog } from '../components/GoogleCalendarDialog';

// Estados de cita con colores
const ESTADOS_CITA = {
  'Agendada': { color: 'bg-slate-100 text-slate-700 border-slate-300', icon: Calendar },
  'Confirmada': { color: 'bg-blue-100 text-blue-700 border-blue-300', icon: CheckCircle },
  'Presente': { color: 'bg-amber-100 text-amber-700 border-amber-300', icon: UserCheck },
  'En consulta': { color: 'bg-purple-100 text-purple-700 border-purple-300', icon: Play },
  'Atendida': { color: 'bg-green-100 text-green-700 border-green-300', icon: CheckCircle },
  'No asistió': { color: 'bg-red-100 text-red-700 border-red-300', icon: XCircle },
  'Cancelada': { color: 'bg-gray-100 text-gray-500 border-gray-300', icon: XCircle }
};

const TIPOS_CITA = [
  'Primera vez', 'Subsecuente', 'Control post-operatorio', 'Estudio', 'Otro'
];

// Helper para formatear fecha
const formatDate = (date) => {
  return new Date(date).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala', 
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
  });
};

const formatTime = (time) => {
  if (!time) return '';
  const [h, m] = time.split(':');
  const hour = parseInt(h);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  return `${hour12}:${m} ${ampm}`;
};

// Componente de tarjeta de cita compacta
const CitaCard = ({ cita, onEstadoChange, onAsignar, onEdit, onVerPaciente, compact = false }) => {
  const estadoConfig = ESTADOS_CITA[cita.estado] || ESTADOS_CITA['Agendada'];
  const IconoEstado = estadoConfig.icon;
  
  return (
    <div 
      className={`
        rounded-lg border p-2 mb-1 cursor-pointer transition-all hover:shadow-md
        ${estadoConfig.color} ${compact ? 'text-xs' : 'text-sm'}
      `}
      style={{ borderLeftWidth: '3px', borderLeftColor: cita.medico_color || '#0F6E56' }}
    >
      <div className="flex items-start justify-between gap-1">
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{cita.paciente_nombre}</div>
          <div className="text-xs opacity-75 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatTime(cita.hora_inicio)}
            {cita.tipo_cita && <span className="ml-1">• {cita.tipo_cita}</span>}
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <MoreVertical className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {cita.estado === 'Agendada' && (
              <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'Confirmada')}>
                <CheckCircle className="w-4 h-4 mr-2" /> Confirmar
              </DropdownMenuItem>
            )}
            {['Agendada', 'Confirmada'].includes(cita.estado) && (
              <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'Presente')}>
                <UserCheck className="w-4 h-4 mr-2" /> Marcar llegada
              </DropdownMenuItem>
            )}
            {cita.estado === 'Presente' && (
              <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'En consulta')}>
                <Play className="w-4 h-4 mr-2" /> Iniciar consulta
              </DropdownMenuItem>
            )}
            {cita.estado === 'En consulta' && (
              <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'Atendida')}>
                <CheckCircle className="w-4 h-4 mr-2" /> Marcar atendida
              </DropdownMenuItem>
            )}
            {!['Atendida', 'No asistió', 'Cancelada'].includes(cita.estado) && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'No asistió')}>
                  <XCircle className="w-4 h-4 mr-2" /> No asistió
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEstadoChange(cita.id, 'Cancelada')}>
                  <XCircle className="w-4 h-4 mr-2" /> Cancelar
                </DropdownMenuItem>
              </>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onVerPaciente(cita.paciente_id)}>
              <Eye className="w-4 h-4 mr-2" /> Ver paciente
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit(cita)}>
              <Calendar className="w-4 h-4 mr-2" /> Editar cita
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
};

// Componente de paciente presente
const PacientePresenteCard = ({ paciente, onEstadoChange, onAsignar, onVerEvaluacion, medicos }) => {
  const tiempoEspera = paciente.tiempo_espera_minutos;
  const colorEspera = tiempoEspera > 60 ? 'text-red-600' : tiempoEspera > 30 ? 'text-amber-600' : 'text-green-600';
  
  return (
    <Card className="mb-2 border-l-4" style={{ borderLeftColor: paciente.medico_color || '#0F6E56' }}>
      <CardContent className="p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold">{paciente.paciente_nombre}</div>
            <div className="text-xs text-gray-500 flex items-center gap-2">
              <span>Llegó: {new Date(paciente.hora_llegada).toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' })}</span>
              <span className={`font-medium ${colorEspera}`}>
                • Espera: {tiempoEspera} min
              </span>
            </div>
            <Badge variant="outline" className="mt-1 text-xs">{paciente.tipo_cita}</Badge>
          </div>
          <div className="flex gap-1">
            {paciente.estado === 'Presente' && (
              <Button 
                size="sm" 
                className="bg-purple-600 hover:bg-purple-700"
                onClick={() => onEstadoChange(paciente.cita_id, 'En consulta')}
              >
                <Play className="w-3 h-3 mr-1" /> Iniciar
              </Button>
            )}
            {paciente.estado === 'En consulta' && (
              <Button 
                size="sm" 
                className="bg-green-600 hover:bg-green-700"
                onClick={() => onEstadoChange(paciente.cita_id, 'Atendida')}
              >
                <CheckCircle className="w-3 h-3 mr-1" /> Atendida
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => onVerEvaluacion(paciente.paciente_id)}>
                  <Eye className="w-4 h-4 mr-2" /> Ver evaluación
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onEstadoChange(paciente.cita_id, 'No asistió')}>
                  <XCircle className="w-4 h-4 mr-2" /> No asistió
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ==================== COMPONENTE PRINCIPAL ====================
const Agenda = () => {
  const { user, hasPermission } = useAuth();
  const [activeTab, setActiveTab] = useState('calendario');
  const [loading, setLoading] = useState(true);
  const [gcalOpen, setGcalOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [vistaCalendario, setVistaCalendario] = useState('dia');
  const [dragCita, setDragCita] = useState(null);
  const [dragOverSlot, setDragOverSlot] = useState(null);
  const [citasRango, setCitasRango] = useState([]);
  const isSuperAdmin = user?.role === 'superadmin';

  // Helpers de fechas (semana/mes)
  const parseISO = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  const toISODate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const startOfWeek = (s) => { const d = parseISO(s); const off = (d.getDay() + 6) % 7; return addDays(d, -off); };
  const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const [fechaSeleccionada, setFechaSeleccionada] = useState(new Date().toISOString().split('T')[0]);
  
  // WebSocket para actualizaciones en tiempo real
  const { isConnected: wsConnected, lastMessage: wsMessage } = useAgendaWebSocket({
    onMessage: (message) => {
      console.log('📩 WebSocket Agenda:', message.type);
      
      // Solo actualizar si la cita es de la fecha seleccionada
      const citaFecha = message.data?.fecha || message.data?.cita?.fecha;
      
      switch (message.type) {
        case 'cita_creada':
          if (citaFecha === fechaSeleccionada) {
            toast.success('Nueva cita agregada');
            fetchCitas();
          }
          break;
          
        case 'cita_actualizada':
          if (citaFecha === fechaSeleccionada) {
            fetchCitas();
          }
          break;
          
        case 'cita_estado_cambiado':
          if (citaFecha === fechaSeleccionada) {
            const estadoMsg = message.data?.nuevo_estado;
            if (estadoMsg === 'Presente') {
              toast.info('Paciente llegó a consulta');
            }
            fetchCitas();
            fetchPresentes();
          }
          break;
          
        default:
          break;
      }
    },
    enabled: true
  });
  
  // Datos
  const [citas, setCitas] = useState([]);
  const [medicos, setMedicos] = useState([]);
  const [contadores, setContadores] = useState(null);
  const [presentes, setPresentes] = useState({ por_medico: [], total_presentes: 0 });
  const [miAgenda, setMiAgenda] = useState(null);
  const [config, setConfig] = useState(null);
  
  // Filtros
  const [medicoFiltro, setMedicoFiltro] = useState('todos');
  const [estadoFiltro, setEstadoFiltro] = useState('todos');
  
  // Modal de cita
  const [citaDialogOpen, setCitaDialogOpen] = useState(false);
  const [editingCita, setEditingCita] = useState(null);
  const [citaForm, setCitaForm] = useState({
    paciente_id: '',
    paciente_nombre: '',
    medico_id: '',
    medico_nombre: '',
    fecha: '',
    hora_inicio: '08:00',
    tipo_cita: 'Subsecuente',
    duracion_minutos: 15,
    notas: '',
    // Campos para paciente nuevo
    es_paciente_nuevo: false,
    nuevo_paciente_telefono: '',
    nuevo_paciente_edad: ''
  });
  
  // Búsqueda de pacientes
  const [pacienteSearch, setPacienteSearch] = useState('');
  const [pacienteResults, setPacienteResults] = useState([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);
  const [creandoPaciente, setCreandoPaciente] = useState(false);
  
  // Walk-in dialog
  const [walkInDialogOpen, setWalkInDialogOpen] = useState(false);
  
  const isAdmin = user?.role === 'super_admin' || user?.role === 'admin';
  
  // ==================== FETCH DATA ====================
  const fetchMedicos = useCallback(async () => {
    try {
      const response = await agendaApi.getMedicosAgenda();
      setMedicos(response.data.data || []);
    } catch (error) {
      console.error('Error fetching médicos:', error);
    }
  }, []);
  
  const fetchCitas = useCallback(async () => {
    try {
      const medicoId = medicoFiltro !== 'todos' ? medicoFiltro : undefined;
      const estado = estadoFiltro !== 'todos' ? estadoFiltro : undefined;
      const response = await agendaApi.getCitas(fechaSeleccionada, medicoId, estado);
      setCitas(response.data.data || []);
    } catch (error) {
      console.error('Error fetching citas:', error);
      toast.error('Error al cargar citas');
    }
  }, [fechaSeleccionada, medicoFiltro, estadoFiltro]);
  
  const fetchContadores = useCallback(async () => {
    try {
      const response = await agendaApi.getContadores(fechaSeleccionada);
      setContadores(response.data);
    } catch (error) {
      console.error('Error fetching contadores:', error);
    }
  }, [fechaSeleccionada]);
  
  const fetchPresentes = useCallback(async () => {
    try {
      const response = await agendaApi.getPresentes(fechaSeleccionada);
      setPresentes(response.data);
    } catch (error) {
      console.error('Error fetching presentes:', error);
    }
  }, [fechaSeleccionada]);
  
  const fetchMiAgenda = useCallback(async () => {
    try {
      const response = await agendaApi.getMiDia();
      setMiAgenda(response.data);
    } catch (error) {
      console.error('Error fetching mi agenda:', error);
    }
  }, []);
  
  const fetchConfig = useCallback(async () => {
    try {
      const response = await agendaApi.getConfig();
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  }, []);
  
  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchMedicos(),
      fetchCitas(),
      fetchContadores(),
      fetchPresentes(),
      fetchConfig()
    ]);
    if (activeTab === 'mi-agenda') {
      await fetchMiAgenda();
    }
    setLoading(false);
  }, [fetchMedicos, fetchCitas, fetchContadores, fetchPresentes, fetchConfig, fetchMiAgenda, activeTab]);
  
  // Cargar citas del rango visible en vista semana/mes
  useEffect(() => {
    if (activeTab !== 'calendario' || vistaCalendario === 'dia') return;
    const fetchRango = async () => {
      let desde, hasta;
      if (vistaCalendario === 'semana') {
        const sw = startOfWeek(fechaSeleccionada);
        desde = toISODate(sw); hasta = toISODate(addDays(sw, 6));
      } else {
        const d = parseISO(fechaSeleccionada);
        desde = toISODate(new Date(d.getFullYear(), d.getMonth(), 1));
        hasta = toISODate(new Date(d.getFullYear(), d.getMonth() + 1, 0));
      }
      try {
        const r = await agendaApi.getCitasRango(desde, hasta);
        const arr = Array.isArray(r.data) ? r.data : (r.data?.data || []);
        setCitasRango(arr);
      } catch (e) {
        setCitasRango([]);
      }
    };
    fetchRango();
  }, [vistaCalendario, fechaSeleccionada, activeTab, citas]);

  
  const handleActualizar = useCallback(async () => {
    setSyncing(true);
    try {
      const res = await googleCalendarApi.sync();
      const d = res.data || {};
      if (d.configured && d.medicos_sincronizados > 0) {
        const partes = [];
        if (d.importadas) partes.push(`${d.importadas} importada(s)`);
        if (d.actualizadas) partes.push(`${d.actualizadas} actualizada(s)`);
        if (d.canceladas) partes.push(`${d.canceladas} cancelada(s)`);
        toast.success(
          partes.length
            ? `Google Calendar sincronizado: ${partes.join(', ')}.`
            : 'Google Calendar sincronizado (sin cambios).'
        );
      }
    } catch (e) {
      // La sincronización con Google es opcional; no bloquear la recarga local
      console.error('Error sincronizando Google Calendar:', e);
    } finally {
      setSyncing(false);
    }
    await fetchAll();
  }, [fetchAll]);

  // Aviso al volver de la conexión OAuth de Google (?gcal=connected|error)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gcal = params.get('gcal');
    if (gcal === 'connected') {
      toast.success('Cuenta de Google conectada correctamente.');
      window.history.replaceState({}, '', '/agenda');
    } else if (gcal === 'error') {
      toast.error('No se pudo conectar la cuenta de Google. Intenta de nuevo.');
      window.history.replaceState({}, '', '/agenda');
    }
  }, []);
  
  useEffect(() => {
    fetchAll();
    // Polling cada 30 segundos para actualizar presentes y contadores
    const interval = setInterval(() => {
      fetchContadores();
      fetchPresentes();
      if (activeTab === 'mi-agenda') fetchMiAgenda();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchAll, fetchContadores, fetchPresentes, fetchMiAgenda, activeTab]);
  
  // ==================== BÚSQUEDA DE PACIENTES ====================
  const searchPacientes = useCallback(async (query) => {
    if (query.length < 2) {
      setPacienteResults([]);
      return;
    }
    setSearchingPaciente(true);
    try {
      const response = await patientApi.search(query);
      setPacienteResults(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    } finally {
      setSearchingPaciente(false);
    }
  }, []);
  
  useEffect(() => {
    const timeout = setTimeout(() => {
      searchPacientes(pacienteSearch);
    }, 300);
    return () => clearTimeout(timeout);
  }, [pacienteSearch, searchPacientes]);
  
  // ==================== HANDLERS ====================
  const handleCambiarEstado = async (citaId, nuevoEstado) => {
    try {
      await agendaApi.cambiarEstado(citaId, nuevoEstado);
      toast.success(`Estado cambiado a "${nuevoEstado}"`);
      fetchCitas();
      fetchContadores();
      fetchPresentes();
      if (activeTab === 'mi-agenda') fetchMiAgenda();
    } catch (error) {
      toast.error('Error al cambiar estado');
    }
  };
  
  const handleAsignarMedico = async (citaId, medicoId, medicoNombre) => {
    try {
      await agendaApi.asignarCita(citaId, medicoId, medicoNombre);
      toast.success('Paciente asignado');
      fetchPresentes();
    } catch (error) {
      toast.error('Error al asignar');
    }
  };
  
  const handleOpenCitaDialog = (cita = null, prefill = null) => {
    if (cita) {
      setEditingCita(cita);
      setCitaForm({
        paciente_id: cita.paciente_id,
        paciente_nombre: cita.paciente_nombre,
        medico_id: cita.medico_id,
        medico_nombre: cita.medico_nombre,
        fecha: cita.fecha,
        hora_inicio: cita.hora_inicio,
        tipo_cita: cita.tipo_cita,
        duracion_minutos: cita.duracion_minutos,
        notas: cita.notas || '',
        es_paciente_nuevo: false,
        nuevo_paciente_telefono: '',
        nuevo_paciente_edad: ''
      });
    } else {
      const med = prefill?.medicoId ? medicos.find(m => m.id === prefill.medicoId) : medicos[0];
      setEditingCita(null);
      setCitaForm({
        paciente_id: '',
        paciente_nombre: '',
        medico_id: med?.id || '',
        medico_nombre: med?.name || '',
        fecha: prefill?.fecha || fechaSeleccionada,
        hora_inicio: prefill?.hora || '08:00',
        tipo_cita: 'Subsecuente',
        duracion_minutos: 15,
        notas: '',
        es_paciente_nuevo: false,
        nuevo_paciente_telefono: '',
        nuevo_paciente_edad: ''
      });
    }
    setPacienteSearch('');
    setPacienteResults([]);
    setCitaDialogOpen(true);
  };

  // Click en un slot vacío -> abrir "Nueva Cita" con médico/fecha/hora prellenados
  const handleSlotClick = (medicoId, slot) => {
    handleOpenCitaDialog(null, { medicoId, hora: slot, fecha: fechaSeleccionada });
  };

  // Drag & drop: mover una cita a otro horario/médico
  const handleMoverCita = async (medicoId, slot, fecha) => {
    const c = dragCita;
    setDragCita(null);
    if (!c) return;
    const nuevaFecha = fecha || c.fecha;
    if (c.medico_id === medicoId && c.hora_inicio === slot && c.fecha === nuevaFecha) return;
    try {
      const med = medicos.find(m => m.id === medicoId);
      await agendaApi.updateCita(c.id, {
        medico_id: medicoId,
        medico_nombre: med?.name || c.medico_nombre,
        hora_inicio: slot,
        fecha: nuevaFecha,
      });
      toast.success('Cita movida correctamente');
      fetchAll();
    } catch (e) {
      toast.error('No se pudo mover la cita');
    }
  };
  
  const handleSaveCita = async () => {
    // Si es paciente nuevo, validar campos adicionales
    if (citaForm.es_paciente_nuevo) {
      if (!citaForm.paciente_nombre.trim()) {
        toast.error('Ingrese el nombre del paciente');
        return;
      }
      if (!citaForm.medico_id) {
        toast.error('Seleccione un médico');
        return;
      }
    } else {
      if (!citaForm.paciente_id || !citaForm.medico_id) {
        toast.error('Seleccione paciente y médico');
        return;
      }
    }
    
    try {
      let pacienteId = citaForm.paciente_id;
      let pacienteNombre = citaForm.paciente_nombre;
      
      // Si es paciente nuevo, crearlo primero
      if (citaForm.es_paciente_nuevo && !citaForm.paciente_id) {
        setCreandoPaciente(true);
        
        // Usar campos separados de nombre y apellido
        const firstName = (citaForm.nuevo_paciente_nombre || '').trim();
        const lastName = (citaForm.nuevo_paciente_apellido || '').trim();
        
        // Validar que ambos campos tengan valor
        if (!firstName) {
          toast.error('Por favor ingrese el nombre del paciente');
          setCreandoPaciente(false);
          return;
        }
        if (!lastName) {
          toast.error('Por favor ingrese el apellido del paciente');
          setCreandoPaciente(false);
          return;
        }
        
        // Validar género antes de crear
        if (!citaForm.nuevo_paciente_genero) {
          toast.error('Por favor seleccione el género del paciente');
          setCreandoPaciente(false);
          return;
        }
        
        // Calcular fecha de nacimiento aproximada si se proporcionó edad
        let birthDate = '';
        if (citaForm.nuevo_paciente_edad) {
          const edad = parseInt(citaForm.nuevo_paciente_edad);
          if (!isNaN(edad)) {
            const hoy = new Date();
            const anioNacimiento = hoy.getFullYear() - edad;
            birthDate = `${anioNacimiento}-01-01`;
          }
        }
        
        const newPatientData = {
          first_name: firstName,
          last_name: lastName,
          phone: citaForm.nuevo_paciente_telefono || '',
          birth_date: birthDate,
          gender: citaForm.nuevo_paciente_genero,
          referral_institution: 'particular'
        };
        
        const response = await patientApi.create(newPatientData);
        pacienteId = response.data.id;
        pacienteNombre = `${response.data.first_name} ${response.data.last_name}`;
        toast.success('Paciente creado');
        setCreandoPaciente(false);
      }
      
      const citaData = {
        ...citaForm,
        paciente_id: pacienteId,
        paciente_nombre: pacienteNombre
      };
      
      if (editingCita) {
        await agendaApi.updateCita(editingCita.id, citaData);
        toast.success('Cita actualizada');
      } else {
        await agendaApi.createCita(citaData);
        toast.success('Cita creada');
      }
      setCitaDialogOpen(false);
      fetchCitas();
      fetchContadores();
    } catch (error) {
      setCreandoPaciente(false);
      // Manejar errores de validación de pydantic (arrays de objetos)
      const detail = error.response?.data?.detail;
      let errorMsg = 'Error al guardar cita';
      if (detail) {
        if (Array.isArray(detail)) {
          errorMsg = detail.map(d => d.msg || d.message || JSON.stringify(d)).join(', ');
        } else if (typeof detail === 'string') {
          errorMsg = detail;
        } else if (typeof detail === 'object') {
          errorMsg = detail.msg || detail.message || JSON.stringify(detail);
        }
      }
      toast.error(errorMsg);
    }
  };
  
  const handleWalkIn = async () => {
    if (!citaForm.paciente_id || !citaForm.medico_id) {
      toast.error('Seleccione paciente y médico');
      return;
    }
    
    try {
      await agendaApi.createWalkIn({
        paciente_id: citaForm.paciente_id,
        paciente_nombre: citaForm.paciente_nombre,
        medico_id: citaForm.medico_id,
        medico_nombre: citaForm.medico_nombre,
        tipo_cita: citaForm.tipo_cita,
        notas: citaForm.notas
      });
      toast.success('Paciente registrado como presente');
      setWalkInDialogOpen(false);
      fetchCitas();
      fetchContadores();
      fetchPresentes();
    } catch (error) {
      toast.error('Error al registrar');
    }
  };
  
  const handleVerPaciente = (pacienteId) => {
    window.open(`/pacientes?id=${pacienteId}`, '_blank');
  };
  
  const handleVerEvaluacion = (pacienteId) => {
    window.open(`/evaluacion-oftalmologica?paciente=${pacienteId}`, '_blank');
  };
  
  const navegarFecha = (dias) => {
    const fecha = new Date(fechaSeleccionada);
    fecha.setDate(fecha.getDate() + dias);
    setFechaSeleccionada(fecha.toISOString().split('T')[0]);
  };
  
  // ==================== GENERAR SLOTS DE TIEMPO ====================
  const generarSlots = () => {
    if (!config) return [];
    const slots = [];
    const [horaInicio] = config.hora_apertura.split(':').map(Number);
    const [horaFin] = config.hora_cierre.split(':').map(Number);
    const intervalo = config.duracion_slot_minutos || 15;
    
    for (let hora = horaInicio; hora < horaFin; hora++) {
      for (let min = 0; min < 60; min += intervalo) {
        slots.push(`${hora.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`);
      }
    }
    return slots;
  };
  
  // Agrupar citas por médico y slot
  const citasPorMedicoYSlot = () => {
    const resultado = {};
    const slots = generarSlots();
    const medicosToShow = medicoFiltro === 'todos' ? medicos : medicos.filter(m => m.id === medicoFiltro);
    
    medicosToShow.forEach(medico => {
      resultado[medico.id] = {
        medico,
        slots: {}
      };
      slots.forEach(slot => {
        resultado[medico.id].slots[slot] = [];
      });
    });
    
    citas.forEach(cita => {
      const medicoId = cita.medico_id;
      if (resultado[medicoId]) {
        const slotKey = cita.hora_inicio;
        if (resultado[medicoId].slots[slotKey]) {
          resultado[medicoId].slots[slotKey].push({
            ...cita,
            medico_color: resultado[medicoId].medico.color
          });
        }
      }
    });
    
    return resultado;
  };
  
  // ==================== RENDER ====================
  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <CalendarDays className="w-7 h-7 text-blue-600" />
              Agenda de Pacientes
            </h1>
            <p className="text-slate-500 text-sm">Gestión de citas y flujo de pacientes</p>
          </div>
          
          <div className="flex gap-2">
            <Button onClick={handleActualizar} variant="outline" size="sm" disabled={syncing} data-testid="agenda-actualizar-btn">
              <RefreshCw className={`w-4 h-4 mr-1 ${(loading || syncing) ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
            {isSuperAdmin && (
              <Button onClick={() => setGcalOpen(true)} variant="outline" size="sm" data-testid="agenda-gcal-btn">
                <CalendarDays className="w-4 h-4 mr-1" />
                Google Calendar
              </Button>
            )}
            <Button onClick={() => handleOpenCitaDialog()} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-1" />
              Nueva Cita
            </Button>
          </div>
        </div>
        
        <GoogleCalendarDialog open={gcalOpen} onOpenChange={setGcalOpen} />
        
        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
            <TabsTrigger value="calendario" className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span className="hidden sm:inline">Calendario</span>
            </TabsTrigger>
            <TabsTrigger value="tablero" className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              <span className="hidden sm:inline">Tablero del Día</span>
            </TabsTrigger>
            <TabsTrigger value="mi-agenda" className="flex items-center gap-1">
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">Mi Agenda</span>
            </TabsTrigger>
          </TabsList>
          
          {/* ==================== TAB: CALENDARIO ==================== */}
          <TabsContent value="calendario" className="mt-4">
            {/* Controles de fecha y filtros */}
            <Card className="mb-4">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center gap-4">
                  {/* Navegación de fecha */}
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => navegarFecha(-1)}>
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <Input
                      type="date"
                      value={fechaSeleccionada}
                      onChange={(e) => setFechaSeleccionada(e.target.value)}
                      className="w-40"
                    />
                    <Button variant="outline" size="sm" onClick={() => navegarFecha(1)}>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setFechaSeleccionada(new Date().toISOString().split('T')[0])}
                    >
                      Hoy
                    </Button>
                  </div>
                  
                  <div className="text-sm font-medium text-slate-700 capitalize">
                    {formatDate(fechaSeleccionada)}
                  </div>
                  
                  {/* Selector de vista */}
                  <div className="flex items-center rounded-lg border border-slate-200 overflow-hidden ml-2">
                    {[['dia', 'Día'], ['semana', 'Semana'], ['mes', 'Mes']].map(([v, label]) => (
                      <button
                        key={v}
                        onClick={() => setVistaCalendario(v)}
                        className={`px-3 py-1.5 text-sm transition-colors ${vistaCalendario === v ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
                        data-testid={`vista-${v}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  
                  {/* Filtros */}
                  <div className="flex gap-2 ml-auto">
                    <Select value={medicoFiltro} onValueChange={setMedicoFiltro}>
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Médico" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="todos">Todos los médicos</SelectItem>
                        {medicos.map(m => (
                          <SelectItem key={m.id} value={m.id}>
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                              {m.name}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    <Select value={estadoFiltro} onValueChange={setEstadoFiltro}>
                      <SelectTrigger className="w-32">
                        <SelectValue placeholder="Estado" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="todos">Todos</SelectItem>
                        {Object.keys(ESTADOS_CITA).map(estado => (
                          <SelectItem key={estado} value={estado}>{estado}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Vista de calendario por columnas */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <Card key={i}>
                    <CardHeader><Skeleton className="h-6 w-32" /></CardHeader>
                    <CardContent><Skeleton className="h-96 w-full" /></CardContent>
                  </Card>
                ))}
              </div>
            ) : vistaCalendario === 'dia' ? (
              <div className="overflow-x-auto">
                <div className="flex gap-4 min-w-max pb-4">
                  {Object.entries(citasPorMedicoYSlot()).map(([medicoId, data]) => (
                    <Card key={medicoId} className="w-64 flex-shrink-0">
                      <CardHeader className="py-3 px-4" style={{ backgroundColor: `${data.medico.color}15` }}>
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: data.medico.color }}
                          />
                          {data.medico.name}
                          <Badge variant="outline" className="ml-auto">
                            {citas.filter(c => c.medico_id === medicoId).length}
                          </Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="p-2 max-h-[600px] overflow-y-auto">
                        {generarSlots().map(slot => {
                          const citasSlot = data.slots[slot] || [];
                          return (
                            <div
                              key={slot}
                              className={`group border-b border-dashed border-gray-200 min-h-[40px] py-1 rounded transition-colors cursor-pointer ${dragOverSlot === `${medicoId}-${slot}` ? 'bg-blue-100 ring-2 ring-blue-400' : 'hover:bg-blue-50/60'}`}
                              onClick={() => citasSlot.length === 0 && handleSlotClick(medicoId, slot)}
                              onDragOver={(e) => { e.preventDefault(); }}
                              onDragEnter={() => dragCita && setDragOverSlot(`${medicoId}-${slot}`)}
                              onDragLeave={() => setDragOverSlot((p) => (p === `${medicoId}-${slot}` ? null : p))}
                              onDrop={(e) => { e.preventDefault(); setDragOverSlot(null); handleMoverCita(medicoId, slot, fechaSeleccionada); }}
                              data-testid={`slot-${medicoId}-${slot}`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-400 mb-1">{formatTime(slot)}</span>
                                {citasSlot.length === 0 && (
                                  <span className="text-[10px] text-blue-500 opacity-0 group-hover:opacity-100">+ Agregar</span>
                                )}
                              </div>
                              {citasSlot.map(cita => (
                                <div
                                  key={cita.id}
                                  draggable
                                  onDragStart={() => setDragCita(cita)}
                                  onDragEnd={() => setDragCita(null)}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <CitaCard
                                    cita={cita}
                                    compact
                                    onEstadoChange={handleCambiarEstado}
                                    onEdit={handleOpenCitaDialog}
                                    onVerPaciente={handleVerPaciente}
                                  />
                                </div>
                              ))}
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : vistaCalendario === 'semana' ? (
              medicoFiltro !== 'todos' ? (
                <div className="overflow-x-auto">
                  <div className="min-w-[900px]">
                    <div className="grid sticky top-0 z-10 bg-white" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
                      <div className="text-[10px] text-slate-400 py-2 text-center border-b">
                        {medicos.find(m => m.id === medicoFiltro)?.name?.split(' ')[0] || ''}
                      </div>
                      {Array.from({ length: 7 }).map((_, i) => {
                        const dia = addDays(startOfWeek(fechaSeleccionada), i);
                        const diaISO = toISODate(dia);
                        const esHoy = diaISO === toISODate(new Date());
                        return (
                          <button
                            key={diaISO}
                            onClick={() => { setFechaSeleccionada(diaISO); setVistaCalendario('dia'); }}
                            className={`py-1.5 text-center border-b border-l ${esHoy ? 'bg-blue-50' : 'bg-slate-50'} hover:bg-blue-100`}
                            data-testid={`semanamed-dia-${diaISO}`}
                          >
                            <div className="text-[11px] font-semibold text-slate-600">{DIAS_SEMANA[i]}</div>
                            <div className="text-sm font-bold text-slate-800">{dia.getDate()}</div>
                          </button>
                        );
                      })}
                    </div>
                    {generarSlots().map(slot => (
                      <div key={slot} className="grid" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
                        <div className="text-[10px] text-slate-400 py-1 pr-1 text-right border-b border-dashed border-gray-100">{formatTime(slot)}</div>
                        {Array.from({ length: 7 }).map((_, i) => {
                          const diaISO = toISODate(addDays(startOfWeek(fechaSeleccionada), i));
                          const key = `${diaISO}-${slot}`;
                          const cs = citasRango.filter(c => c.medico_id === medicoFiltro && c.fecha === diaISO && c.hora_inicio === slot);
                          return (
                            <div
                              key={key}
                              className={`min-h-[34px] border-b border-l border-dashed border-gray-100 p-0.5 cursor-pointer transition-colors ${dragOverSlot === key ? 'bg-blue-100 ring-2 ring-blue-400' : 'hover:bg-blue-50/60'}`}
                              onClick={() => cs.length === 0 && handleOpenCitaDialog(null, { medicoId: medicoFiltro, hora: slot, fecha: diaISO })}
                              onDragOver={(e) => e.preventDefault()}
                              onDragEnter={() => dragCita && setDragOverSlot(key)}
                              onDragLeave={() => setDragOverSlot((p) => (p === key ? null : p))}
                              onDrop={(e) => { e.preventDefault(); setDragOverSlot(null); handleMoverCita(medicoFiltro, slot, diaISO); }}
                              data-testid={`semanamed-slot-${key}`}
                            >
                              {cs.map(cita => (
                                <div
                                  key={cita.id}
                                  draggable
                                  onDragStart={() => setDragCita(cita)}
                                  onDragEnd={() => setDragCita(null)}
                                  onClick={(e) => { e.stopPropagation(); handleOpenCitaDialog(cita); }}
                                  className="text-[10px] rounded px-1 py-0.5 mb-0.5 text-white truncate"
                                  style={{ backgroundColor: medicos.find(m => m.id === cita.medico_id)?.color || '#3b82f6' }}
                                  title={`${cita.paciente_nombre} - ${cita.estado}`}
                                >
                                  {cita.paciente_nombre}
                                </div>
                              ))}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
              <div className="overflow-x-auto">
                <div className="grid grid-cols-7 gap-2 min-w-[900px]">
                  {Array.from({ length: 7 }).map((_, i) => {
                    const dia = addDays(startOfWeek(fechaSeleccionada), i);
                    const diaISO = toISODate(dia);
                    const esHoy = diaISO === toISODate(new Date());
                    const citasDia = citasRango
                      .filter(c => c.fecha === diaISO)
                      .sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
                    return (
                      <div key={diaISO} className={`rounded-lg border ${esHoy ? 'border-blue-400' : 'border-slate-200'} bg-white flex flex-col`}>
                        <button
                          onClick={() => { setFechaSeleccionada(diaISO); setVistaCalendario('dia'); }}
                          className={`px-2 py-2 text-center border-b ${esHoy ? 'bg-blue-50' : 'bg-slate-50'} hover:bg-blue-100 transition-colors`}
                          data-testid={`semana-dia-${diaISO}`}
                        >
                          <div className="text-xs font-semibold text-slate-600">{DIAS_SEMANA[i]}</div>
                          <div className="text-lg font-bold text-slate-800">{dia.getDate()}</div>
                          <div className="text-[10px] text-slate-400">{citasDia.length} cita(s)</div>
                        </button>
                        <div className="p-1.5 space-y-1 max-h-[520px] overflow-y-auto min-h-[120px]">
                          {citasDia.map(cita => (
                            <button
                              key={cita.id}
                              onClick={() => handleOpenCitaDialog(cita)}
                              className="w-full text-left text-xs p-1.5 rounded border-l-2 hover:bg-slate-50"
                              style={{ borderColor: medicos.find(m => m.id === cita.medico_id)?.color || '#3b82f6' }}
                              data-testid={`semana-cita-${cita.id}`}
                            >
                              <div className="font-medium text-slate-700">{formatTime(cita.hora_inicio)}</div>
                              <div className="text-slate-500 truncate">{cita.paciente_nombre}</div>
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              )
            ) : (
              (() => {
                const d = parseISO(fechaSeleccionada);
                const primerDia = new Date(d.getFullYear(), d.getMonth(), 1);
                const gridInicio = startOfWeek(toISODate(primerDia));
                const celdas = Array.from({ length: 42 }).map((_, i) => addDays(gridInicio, i));
                const hoyISO = toISODate(new Date());
                return (
                  <div>
                    <div className="text-center text-sm font-semibold text-slate-700 mb-2 capitalize">
                      {MESES[d.getMonth()]} {d.getFullYear()}
                    </div>
                    <div className="grid grid-cols-7 gap-px bg-slate-200 rounded-lg overflow-hidden border border-slate-200">
                      {DIAS_SEMANA.map(dn => (
                        <div key={dn} className="bg-slate-50 text-center text-xs font-semibold text-slate-500 py-2">{dn}</div>
                      ))}
                      {celdas.map((cel) => {
                        const celISO = toISODate(cel);
                        const esOtroMes = cel.getMonth() !== d.getMonth();
                        const esHoy = celISO === hoyISO;
                        const citasCel = citasRango.filter(c => c.fecha === celISO);
                        return (
                          <button
                            key={celISO}
                            onClick={() => { setFechaSeleccionada(celISO); setVistaCalendario('dia'); }}
                            className={`bg-white min-h-[90px] p-1.5 text-left align-top hover:bg-blue-50 transition-colors ${esOtroMes ? 'opacity-40' : ''} ${esHoy ? 'ring-2 ring-inset ring-blue-400' : ''}`}
                            data-testid={`mes-dia-${celISO}`}
                          >
                            <div className="text-xs font-semibold text-slate-600">{cel.getDate()}</div>
                            {citasCel.length > 0 && (
                              <div className="mt-1 space-y-0.5">
                                {citasCel.slice(0, 3).map(c => (
                                  <div key={c.id} className="text-[10px] truncate rounded px-1 py-0.5 text-white"
                                    style={{ backgroundColor: medicos.find(m => m.id === c.medico_id)?.color || '#3b82f6' }}>
                                    {formatTime(c.hora_inicio)} {c.paciente_nombre}
                                  </div>
                                ))}
                                {citasCel.length > 3 && (
                                  <div className="text-[10px] text-slate-500">+{citasCel.length - 3} más</div>
                                )}
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })()
            )}
          </TabsContent>
          
          {/* ==================== TAB: TABLERO DEL DÍA ==================== */}
          <TabsContent value="tablero" className="mt-4">
            {/* Contadores */}
            {contadores && (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
                <Card className="bg-slate-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-slate-700">{contadores.total_agendados}</div>
                    <div className="text-xs text-slate-500">Agendados</div>
                  </CardContent>
                </Card>
                <Card className="bg-blue-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-blue-700">{contadores.total_confirmados}</div>
                    <div className="text-xs text-blue-600">Confirmados</div>
                  </CardContent>
                </Card>
                <Card className="bg-amber-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-amber-700">{contadores.total_presentes}</div>
                    <div className="text-xs text-amber-600">Presentes</div>
                  </CardContent>
                </Card>
                <Card className="bg-purple-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-purple-700">{contadores.total_en_consulta}</div>
                    <div className="text-xs text-purple-600">En consulta</div>
                  </CardContent>
                </Card>
                <Card className="bg-green-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-green-700">{contadores.total_atendidos}</div>
                    <div className="text-xs text-green-600">Atendidos</div>
                  </CardContent>
                </Card>
                <Card className="bg-red-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-red-700">{contadores.total_no_asistio}</div>
                    <div className="text-xs text-red-600">No asistió</div>
                  </CardContent>
                </Card>
                <Card className="bg-gray-50">
                  <CardContent className="p-3 text-center">
                    <div className="text-2xl font-bold text-gray-700">{contadores.total_cancelados}</div>
                    <div className="text-xs text-gray-600">Cancelados</div>
                  </CardContent>
                </Card>
              </div>
            )}
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Lista de citas del día */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Calendar className="w-5 h-5" />
                      Citas del día
                    </span>
                    <Button variant="outline" size="sm" onClick={() => setWalkInDialogOpen(true)}>
                      <Plus className="w-4 h-4 mr-1" /> Walk-in
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent className="max-h-[500px] overflow-y-auto">
                  {citas.filter(c => !['Atendida', 'No asistió', 'Cancelada'].includes(c.estado)).length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No hay citas pendientes</p>
                  ) : (
                    citas
                      .filter(c => !['Atendida', 'No asistió', 'Cancelada'].includes(c.estado))
                      .map(cita => (
                        <CitaCard
                          key={cita.id}
                          cita={{...cita, medico_color: medicos.find(m => m.id === cita.medico_id)?.color}}
                          onEstadoChange={handleCambiarEstado}
                          onEdit={handleOpenCitaDialog}
                          onVerPaciente={handleVerPaciente}
                        />
                      ))
                  )}
                </CardContent>
              </Card>
              
              {/* Pacientes presentes en clínica */}
              <Card>
                <CardHeader className="py-3 bg-amber-50">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-amber-600" />
                    Pacientes Presentes en Clínica
                    <Badge className="ml-auto bg-amber-600">{presentes.total_presentes}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-3 max-h-[500px] overflow-y-auto">
                  {presentes.por_medico.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No hay pacientes presentes</p>
                  ) : (
                    presentes.por_medico.map(grupo => (
                      <div key={grupo.medico_id} className="mb-4">
                        <div 
                          className="text-sm font-semibold mb-2 flex items-center gap-2 p-2 rounded"
                          style={{ backgroundColor: `${grupo.medico_color}15` }}
                        >
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: grupo.medico_color }}
                          />
                          {grupo.medico_nombre}
                          <Badge variant="outline" className="ml-auto">{grupo.total}</Badge>
                        </div>
                        {grupo.pacientes.map(paciente => (
                          <PacientePresenteCard
                            key={paciente.cita_id}
                            paciente={{...paciente, medico_color: grupo.medico_color}}
                            onEstadoChange={handleCambiarEstado}
                            onVerEvaluacion={handleVerEvaluacion}
                            medicos={medicos}
                          />
                        ))}
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* ==================== TAB: MI AGENDA ==================== */}
          <TabsContent value="mi-agenda" className="mt-4">
            {miAgenda ? (
              <div className="space-y-4">
                {/* Header de mi agenda */}
                <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold">{miAgenda.medico_nombre}</h2>
                        <p className="text-blue-100">Mi agenda del {formatDate(miAgenda.fecha)}</p>
                      </div>
                      <div className="flex gap-4">
                        <div className="text-center">
                          <div className="text-3xl font-bold">{miAgenda.contadores.total}</div>
                          <div className="text-xs text-blue-100">Citas hoy</div>
                        </div>
                        <div className="text-center">
                          <div className="text-3xl font-bold">{miAgenda.contadores.presentes + miAgenda.contadores.en_consulta}</div>
                          <div className="text-xs text-blue-100">Presentes</div>
                        </div>
                        <div className="text-center">
                          <div className="text-3xl font-bold">{miAgenda.contadores.atendidos}</div>
                          <div className="text-xs text-blue-100">Atendidos</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Pacientes presentes (destacado) */}
                  <Card className="border-2 border-amber-200">
                    <CardHeader className="py-3 bg-amber-50">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <UserCheck className="w-5 h-5 text-amber-600" />
                        Mis Pacientes Presentes
                        <Badge className="ml-auto bg-amber-600">{miAgenda.pacientes_presentes.length}</Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3">
                      {miAgenda.pacientes_presentes.length === 0 ? (
                        <p className="text-center text-gray-500 py-8">No hay pacientes esperando</p>
                      ) : (
                        miAgenda.pacientes_presentes.map(paciente => (
                          <PacientePresenteCard
                            key={paciente.cita_id}
                            paciente={paciente}
                            onEstadoChange={handleCambiarEstado}
                            onVerEvaluacion={handleVerEvaluacion}
                            medicos={medicos}
                          />
                        ))
                      )}
                    </CardContent>
                  </Card>
                  
                  {/* Mis citas del día */}
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Calendar className="w-5 h-5" />
                        Mis Citas del Día
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="max-h-[400px] overflow-y-auto">
                      {miAgenda.citas_del_dia.length === 0 ? (
                        <p className="text-center text-gray-500 py-8">No hay citas programadas</p>
                      ) : (
                        miAgenda.citas_del_dia.map(cita => (
                          <CitaCard
                            key={cita.id}
                            cita={cita}
                            onEstadoChange={handleCambiarEstado}
                            onEdit={handleOpenCitaDialog}
                            onVerPaciente={handleVerPaciente}
                          />
                        ))
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Usuario no vinculado a médico</h3>
                  <p className="text-gray-500">
                    Tu usuario no está vinculado a un médico. 
                    Contacta al administrador para configurar tu perfil.
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
      
      {/* ==================== DIALOG: NUEVA/EDITAR CITA ==================== */}
      <Dialog open={citaDialogOpen} onOpenChange={setCitaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingCita ? 'Editar Cita' : 'Nueva Cita'}
            </DialogTitle>
            <DialogDescription>
              {editingCita ? 'Modifica los datos de la cita' : 'Programa una nueva cita para un paciente'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Búsqueda de paciente */}
            <div className="space-y-2">
              <Label>Paciente *</Label>
              {citaForm.paciente_id && !citaForm.es_paciente_nuevo ? (
                <div className="flex items-center gap-2 p-2 bg-blue-50 rounded border border-blue-200">
                  <User className="w-4 h-4 text-blue-600" />
                  <span className="flex-1">{citaForm.paciente_nombre}</span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setCitaForm(prev => ({ 
                      ...prev, 
                      paciente_id: '', 
                      paciente_nombre: '',
                      es_paciente_nuevo: false 
                    }))}
                  >
                    Cambiar
                  </Button>
                </div>
              ) : citaForm.es_paciente_nuevo ? (
                <div className="space-y-3 p-3 bg-amber-50 rounded border border-amber-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-amber-700 flex items-center gap-1">
                      <Plus className="w-4 h-4" /> Nuevo paciente
                    </span>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => setCitaForm(prev => ({ 
                        ...prev, 
                        es_paciente_nuevo: false,
                        nuevo_paciente_nombre: '',
                        nuevo_paciente_apellido: '',
                        paciente_nombre: '',
                        nuevo_paciente_telefono: '',
                        nuevo_paciente_edad: '',
                        nuevo_paciente_genero: ''
                      }))}
                    >
                      Cancelar
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        placeholder="Nombre(s) *"
                        value={citaForm.nuevo_paciente_nombre || ''}
                        onChange={(e) => setCitaForm(prev => ({ 
                          ...prev, 
                          nuevo_paciente_nombre: e.target.value,
                          paciente_nombre: `${e.target.value} ${prev.nuevo_paciente_apellido || ''}`.trim()
                        }))}
                        className="input-teal"
                        data-testid="nuevo-paciente-nombre"
                      />
                      <Input
                        placeholder="Apellido(s) *"
                        value={citaForm.nuevo_paciente_apellido || ''}
                        onChange={(e) => setCitaForm(prev => ({ 
                          ...prev, 
                          nuevo_paciente_apellido: e.target.value,
                          paciente_nombre: `${prev.nuevo_paciente_nombre || ''} ${e.target.value}`.trim()
                        }))}
                        className="input-teal"
                        data-testid="nuevo-paciente-apellido"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        placeholder="Teléfono"
                        value={citaForm.nuevo_paciente_telefono}
                        onChange={(e) => setCitaForm(prev => ({ ...prev, nuevo_paciente_telefono: e.target.value }))}
                        className="input-teal"
                        data-testid="nuevo-paciente-telefono"
                      />
                      <Input
                        placeholder="Edad (años)"
                        type="number"
                        min="0"
                        max="120"
                        value={citaForm.nuevo_paciente_edad}
                        onChange={(e) => setCitaForm(prev => ({ ...prev, nuevo_paciente_edad: e.target.value }))}
                        className="input-teal"
                        data-testid="nuevo-paciente-edad"
                      />
                      <Select
                        value={citaForm.nuevo_paciente_genero || ''}
                        onValueChange={(value) => setCitaForm(prev => ({ ...prev, nuevo_paciente_genero: value }))}
                      >
                        <SelectTrigger className="input-teal" data-testid="nuevo-paciente-genero">
                          <SelectValue placeholder="Género *" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="masculino">Masculino</SelectItem>
                          <SelectItem value="femenino">Femenino</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {editingCita && !citaForm.paciente_id && editingCita.paciente_nombre && (
                    <div className="p-2 rounded border border-amber-200 bg-amber-50 text-xs text-amber-800" data-testid="cita-google-ref">
                      <span className="font-semibold">Cita de Google sin ficha.</span> Texto original: "{editingCita.paciente_nombre}". Busca el paciente por su nombre para vincularlo, o créalo si no existe.
                    </div>
                  )}
                  <div className="relative">
                    <Input
                      placeholder="Buscar paciente por nombre o expediente..."
                      value={pacienteSearch}
                      onChange={(e) => setPacienteSearch(e.target.value)}
                      className="input-teal"
                    />
                    {pacienteResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                        {pacienteResults.map(p => {
                          const nombre = p.full_name || `${p.first_name || ''} ${p.last_name || ''}`.trim();
                          return (
                          <div
                            key={p.id}
                            className="p-2 hover:bg-blue-50 cursor-pointer"
                            data-testid={`cita-paciente-option-${p.id}`}
                            onClick={() => {
                              setCitaForm(prev => ({
                                ...prev,
                                paciente_id: p.id,
                                paciente_nombre: nombre,
                                es_paciente_nuevo: false
                              }));
                              setPacienteSearch('');
                              setPacienteResults([]);
                            }}
                          >
                            <div className="font-medium">{nombre || 'Sin nombre'}</div>
                            <div className="text-xs text-gray-500">Exp: {p.record_number}</div>
                          </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full text-amber-600 border-amber-300 hover:bg-amber-50"
                    onClick={() => setCitaForm(prev => ({ 
                      ...prev, 
                      es_paciente_nuevo: true,
                      paciente_id: '',
                      paciente_nombre: pacienteSearch // Usar lo que ya escribió
                    }))}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Crear paciente nuevo
                  </Button>
                </div>
              )}
            </div>
            
            {/* Médico */}
            <div className="space-y-2">
              <Label>Médico *</Label>
              <Select
                value={citaForm.medico_id}
                onValueChange={(value) => {
                  const medico = medicos.find(m => m.id === value);
                  setCitaForm(prev => ({
                    ...prev,
                    medico_id: value,
                    medico_nombre: medico?.name || ''
                  }));
                }}
              >
                <SelectTrigger className="input-teal">
                  <SelectValue placeholder="Seleccionar médico" />
                </SelectTrigger>
                <SelectContent>
                  {medicos.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                        {m.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Fecha y hora */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Fecha *</Label>
                <Input
                  type="date"
                  value={citaForm.fecha}
                  onChange={(e) => setCitaForm(prev => ({ ...prev, fecha: e.target.value }))}
                  className="input-teal"
                />
              </div>
              <div className="space-y-2">
                <Label>Hora *</Label>
                <Input
                  type="time"
                  value={citaForm.hora_inicio}
                  onChange={(e) => setCitaForm(prev => ({ ...prev, hora_inicio: e.target.value }))}
                  className="input-teal"
                />
              </div>
            </div>
            
            {/* Tipo y duración */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tipo de cita</Label>
                <Select
                  value={citaForm.tipo_cita}
                  onValueChange={(value) => setCitaForm(prev => ({ ...prev, tipo_cita: value }))}
                >
                  <SelectTrigger className="input-teal">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_CITA.map(tipo => (
                      <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Duración</Label>
                <Select
                  value={citaForm.duracion_minutos.toString()}
                  onValueChange={(value) => setCitaForm(prev => ({ ...prev, duracion_minutos: parseInt(value) }))}
                >
                  <SelectTrigger className="input-teal">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10 minutos</SelectItem>
                    <SelectItem value="15">15 minutos</SelectItem>
                    <SelectItem value="30">30 minutos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Notas */}
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea
                value={citaForm.notas}
                onChange={(e) => setCitaForm(prev => ({ ...prev, notas: e.target.value }))}
                className="input-teal"
                placeholder="Notas adicionales..."
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCitaDialogOpen(false)} disabled={creandoPaciente}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveCita} 
              className="bg-blue-600 hover:bg-blue-700"
              disabled={creandoPaciente}
            >
              {creandoPaciente ? 'Creando paciente...' : editingCita ? 'Guardar cambios' : citaForm.es_paciente_nuevo ? 'Crear paciente y cita' : 'Crear cita'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ==================== DIALOG: WALK-IN ==================== */}
      <Dialog open={walkInDialogOpen} onOpenChange={setWalkInDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Registrar Paciente sin Cita (Walk-in)</DialogTitle>
            <DialogDescription>
              Registra un paciente que llegó sin cita previa
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Búsqueda de paciente */}
            <div className="space-y-2">
              <Label>Paciente *</Label>
              {citaForm.paciente_nombre ? (
                <div className="flex items-center gap-2 p-2 bg-blue-50 rounded border border-blue-200">
                  <User className="w-4 h-4 text-blue-600" />
                  <span className="flex-1">{citaForm.paciente_nombre}</span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setCitaForm(prev => ({ ...prev, paciente_id: '', paciente_nombre: '' }))}
                  >
                    Cambiar
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <Input
                    placeholder="Buscar paciente..."
                    value={pacienteSearch}
                    onChange={(e) => setPacienteSearch(e.target.value)}
                    className="input-teal"
                  />
                  {pacienteResults.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
                      {pacienteResults.map(p => (
                        <div
                          key={p.id}
                          className="p-2 hover:bg-blue-50 cursor-pointer"
                          onClick={() => {
                            setCitaForm(prev => ({
                              ...prev,
                              paciente_id: p.id,
                              paciente_nombre: `${p.first_name} ${p.last_name}`
                            }));
                            setPacienteSearch('');
                            setPacienteResults([]);
                          }}
                        >
                          <div className="font-medium">{p.first_name} {p.last_name}</div>
                          <div className="text-xs text-gray-500">Exp: {p.record_number}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Médico */}
            <div className="space-y-2">
              <Label>Asignar a médico *</Label>
              <Select
                value={citaForm.medico_id}
                onValueChange={(value) => {
                  const medico = medicos.find(m => m.id === value);
                  setCitaForm(prev => ({
                    ...prev,
                    medico_id: value,
                    medico_nombre: medico?.name || ''
                  }));
                }}
              >
                <SelectTrigger className="input-teal">
                  <SelectValue placeholder="Seleccionar médico" />
                </SelectTrigger>
                <SelectContent>
                  {medicos.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                        {m.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Tipo */}
            <div className="space-y-2">
              <Label>Tipo de cita</Label>
              <Select
                value={citaForm.tipo_cita}
                onValueChange={(value) => setCitaForm(prev => ({ ...prev, tipo_cita: value }))}
              >
                <SelectTrigger className="input-teal">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPOS_CITA.map(tipo => (
                    <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Notas */}
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea
                value={citaForm.notas}
                onChange={(e) => setCitaForm(prev => ({ ...prev, notas: e.target.value }))}
                className="input-teal"
                placeholder="Motivo de visita..."
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setWalkInDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleWalkIn} className="bg-amber-600 hover:bg-amber-700">
              <UserCheck className="w-4 h-4 mr-1" />
              Registrar como presente
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Agenda;
