import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Eye, Save, Plus, Trash2, RefreshCw, Search, Printer, 
  ChevronDown, ChevronUp, Lock, Clock, Calendar,
  User, FileText, Stethoscope, Pill, Activity, ClipboardList,
  Glasses, Contact, CheckCircle, Wifi, WifiOff, CloudOff, Cloud, FileDown
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import axios from 'axios';
import { agendaApi } from '../services/agendaApi';
import { getGuatemalaDate } from '../services/api';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Formatea una fecha (YYYY-MM-DD o ISO) a DD/MM/YYYY para el historial
const formatFechaHistorial = (f) => {
  if (!f) return 'Sin fecha';
  const s = String(f).slice(0, 10);
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : s;
};

// Determina si el formulario tiene datos clínicos reales (para no autoguardar borradores vacíos)
const tieneDatosClinicos = (fd) => {
  if (!fd) return false;
  const textos = ['motivo_consulta', 'padecimiento_actual', 'plan', 'lectura_examenes'];
  if (textos.some((k) => (fd[k] || '').toString().trim())) return true;
  if (Array.isArray(fd.diagnosticos) && fd.diagnosticos.length > 0) return true;
  if (Array.isArray(fd.procedimientos) && fd.procedimientos.length > 0) return true;
  // Examen: cualquier subcampo con valor
  const ex = fd.examen || {};
  for (const v of Object.values(ex)) {
    if (v && typeof v === 'object') {
      if (Object.values(v).some((x) => (x ?? '').toString().trim())) return true;
    } else if ((v ?? '').toString().trim()) {
      return true;
    }
  }
  // Recetas
  const r = fd.recetas || {};
  if ((r.medicamentos?.items || []).length > 0) return true;
  if ((r.anteojos_lista || []).length > 0) return true;
  if ((r.lentes_contacto_lista || []).length > 0) return true;
  // Recomendaciones
  const rec = fd.recomendaciones || {};
  if ((rec.recomendaciones_generales || '').toString().trim()) return true;
  if ((rec.estudios_a_realizar || []).length > 0) return true;
  // Antecedentes (solo texto libre)
  const ant = fd.antecedentes || {};
  for (const v of Object.values(ant)) {
    if (typeof v === 'string' && v.trim()) return true;
  }
  return false;
};

// Componente de Autocomplete reutilizable
const Autocomplete = ({ value, onChange, placeholder, fetchUrl, disabled, className }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const wrapperRef = useRef(null);

  const fetchSuggestions = useCallback(async (search) => {
    if (!search || search.length < 2) {
      setSuggestions([]);
      return;
    }
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}${fetchUrl}?search=${encodeURIComponent(search)}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuggestions(response.data || []);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    } finally {
      setLoading(false);
    }
  }, [fetchUrl]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSuggestions(value);
    }, 300);
    return () => clearTimeout(timer);
  }, [value, fetchSuggestions]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={wrapperRef} className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowSuggestions(true);
        }}
        onFocus={() => setShowSuggestions(true)}
        placeholder={placeholder}
        disabled={disabled}
        className={className}
      />
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto">
          {suggestions.map((item, index) => (
            <div
              key={item.id || index}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm"
              onClick={() => {
                onChange(item.nombre || item.nombre_completo || item.name || '');
                setShowSuggestions(false);
              }}
            >
              {item.nombre || item.nombre_completo || item.name}
              {item.usos && <span className="text-gray-400 ml-2">({item.usos} usos)</span>}
            </div>
          ))}
        </div>
      )}
      {loading && (
        <div className="absolute right-2 top-2">
          <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
        </div>
      )}
    </div>
  );
};

// Componente de sección colapsable
const CollapsibleSection = ({ title, icon: Icon, children, defaultOpen = true, badge, onPrint }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'var(--border-card)' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-blue-50 to-white hover:from-blue-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-blue-600" />}
          <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{title}</span>
          {badge && <Badge className="ml-2 bg-blue-100 text-blue-700 text-xs">{badge}</Badge>}
        </div>
        <div className="flex items-center gap-2">
          {onPrint && (
            <span
              onClick={(e) => {
                e.stopPropagation();
                onPrint();
              }}
              className="p-1.5 rounded-md hover:bg-blue-100 text-blue-600 cursor-pointer transition-colors"
              title="Imprimir receta"
            >
              <Printer className="w-4 h-4" />
            </span>
          )}
          {isOpen ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
        </div>
      </button>
      {isOpen && <div className="p-4 bg-white">{children}</div>}
    </div>
  );
};

// Componente para campos OD/OS
const CampoODOS = ({ label, valueOD, valueOS, onChangeOD, onChangeOS, disabled, type = "text", placeholder = "" }) => (
  <div className="grid grid-cols-3 gap-2 items-center">
    <Label className="text-xs text-right pr-2">{label}</Label>
    <Input
      value={valueOD}
      onChange={(e) => onChangeOD(e.target.value)}
      disabled={disabled}
      type={type}
      placeholder={placeholder || "OD"}
      className="input-teal text-sm h-8"
    />
    <Input
      value={valueOS}
      onChange={(e) => onChangeOS(e.target.value)}
      disabled={disabled}
      type={type}
      placeholder={placeholder || "OS"}
      className="input-teal text-sm h-8"
    />
  </div>
);

const EvaluacionOftalmologica = () => {
  const { user, hasPermission } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [evaluaciones, setEvaluaciones] = useState([]);
  // Ref con el id del paciente actual (para acotar el Historial a ese paciente)
  const pacienteIdRef = useRef(null);
  const preseleccionDoneRef = useRef(false);
  const [searchParams] = useSearchParams();
  const [evaluacionActual, setEvaluacionActual] = useState(null);
  // Snapshot de la evaluación en curso (del día) para poder regresar tras ver el historial
  const [viendoHistorial, setViendoHistorial] = useState(false);
  const borradorRef = useRef(null);
  const [pacientes, setPacientes] = useState([]);
  const [medicos, setMedicos] = useState([]);
  const [searchPaciente, setSearchPaciente] = useState('');
  const [showPacienteList, setShowPacienteList] = useState(false);
  const [autoguardadoStatus, setAutoguardadoStatus] = useState('');
  const [tiempoRestante, setTiempoRestante] = useState(null);
  const [printDialogOpen, setPrintDialogOpen] = useState(false);
  const [printType, setPrintType] = useState('');
  const [crmDialogOpen, setCrmDialogOpen] = useState(false);
  const [crmForm, setCrmForm] = useState({
    tipo_cirugia: '',
    ojo: 'OU',
    diagnostico: '',
    prioridad: 'normal',
    nivel_interes: 'interesado',
    notas: ''
  });
  const [tiposCirugia, setTiposCirugia] = useState([]);
  const [crmEnviado, setCrmEnviado] = useState(false); // Para mostrar si ya se envió al CRM
  
  // Estado para índice de receta a imprimir
  const [printRecetaIndex, setPrintRecetaIndex] = useState(0);
  
  // Estados para soporte offline
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingSync, setPendingSync] = useState([]);
  const [syncStatus, setSyncStatus] = useState(''); // '', 'syncing', 'synced', 'pending'
  
  const autoguardadoRef = useRef(null);
  const lastSavedRef = useRef(null);
  const syncIntervalRef = useRef(null);
  
  const OFFLINE_STORAGE_KEY = 'novavision_evaluaciones_offline';
  
  const canEdit = hasPermission('view_evaluacion');
  const isReadOnly = !canEdit || evaluacionActual?.sellado;

  // Estado inicial de evaluación
  const evaluacionVacia = {
    paciente_id: '',
    paciente_nombre: '',
    paciente_edad: 0,
    paciente_sexo: '',
    paciente_expediente: '',
    fecha: getGuatemalaDate(),
    medico_id: '',
    medico_nombre: '',
    motivo_consulta: '',
    padecimiento_actual: '',
    antecedentes: {
      personales_patologicos: '',
      diabetes: false,
      hipertension: false,
      cardiopatia: false,
      enfermedad_tiroidea: false,
      otros_patologicos: false,
      oftalmologicos: '',
      quirurgicos: '',
      alergias: '',
      familiares: '',
      habitos: ''
    },
    medicamentos_actuales: [],
    medicamentos_previos: [],
    examen: {
      avsc_od: '', avsc_os: '',
      avcc_od: '', avcc_os: '',
      lensometria_od: { esfera: '', cilindro: '', eje: '' },
      lensometria_os: { esfera: '', cilindro: '', eje: '' },
      refraccion_od: { esfera: '', cilindro: '', eje: '', adicion: '' },
      refraccion_os: { esfera: '', cilindro: '', eje: '', adicion: '' },
      queratometria_od: '', queratometria_os: '',
      pio_od: '', pio_os: '', pio_metodo: '',
      segmento_anterior: '',  // Simplificado a un solo campo de texto
      segmento_posterior: '', // Antes "fondo de ojo", simplificado
      motilidad_ocular: ''
    },
    diagnosticos: [],
    plan: '',
    lectura_examenes: '',
    recomendaciones: {
      estudios_a_realizar: [],
      recomendaciones_generales: ''
    },
    proxima_cita: {
      agendar: false,
      medico_id: '',
      medico_nombre: '',
      fecha: '',
      hora: '',
      tipo_cita: 'Subsecuente',
      notas: ''
    },
    procedimientos: [],
    recetas: {
      medicamentos: { items: [] },
      // Arrays de múltiples recetas
      anteojos_lista: [],
      lentes_contacto_lista: [],
      // Receta activa (para edición - compatibilidad hacia atrás)
      anteojos: {
        od: { esfera: '', cilindro: '', eje: '', adicion: '' },
        os: { esfera: '', cilindro: '', eje: '', adicion: '' },
        distancia_pupilar: '',
        tipo_lente: '',
        material: '',
        tratamientos: '',
        uso: '',
        observaciones: ''
      },
      lentes_contacto: {
        od: { poder: '', curva_base: '', diametro: '', adicion: '' },
        os: { poder: '', curva_base: '', diametro: '', adicion: '' },
        marca: '',
        tipo: '',
        regimen_reemplazo: '',
        observaciones: ''
      }
    }
  };

  // Template para nueva receta de anteojos
  const nuevaRecetaAnteojos = () => ({
    id: `ant_${Date.now()}`,
    od: { esfera: '', cilindro: '', eje: '', adicion: '' },
    os: { esfera: '', cilindro: '', eje: '', adicion: '' },
    distancia_pupilar: '',
    tipo_lente: '',
    material: '',
    tratamientos: '',
    uso: '',
    observaciones: '',
    fecha_creacion: new Date().toISOString()
  });

  // Template para nueva receta de lentes de contacto
  const nuevaRecetaLentesContacto = () => ({
    id: `lc_${Date.now()}`,
    od: { poder: '', curva_base: '', diametro: '', adicion: '' },
    os: { poder: '', curva_base: '', diametro: '', adicion: '' },
    marca: '',
    tipo: '',
    regimen_reemplazo: '',
    observaciones: '',
    fecha_creacion: new Date().toISOString()
  });

  const [formData, setFormData] = useState(evaluacionVacia);

  // Fetch del historial: SOLO evaluaciones del paciente actual, ordenadas por fecha clínica
  const fetchEvaluaciones = useCallback(async (pacienteIdArg = null) => {
    const pid = pacienteIdArg || pacienteIdRef.current;
    if (!pid) {
      setEvaluaciones([]);
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/evaluaciones?paciente_id=${pid}&limit=100`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const list = response.data.data || [];
      // Ordenar por fecha clínica (desc) y, a igualdad, por fecha de creación (desc)
      list.sort((a, b) => {
        const fa = a.fecha || '';
        const fb = b.fecha || '';
        if (fa !== fb) return fb.localeCompare(fa);
        return (b.fecha_creacion || '').localeCompare(a.fecha_creacion || '');
      });
      setEvaluaciones(list);
    } catch (error) {
      console.error('Error fetching evaluaciones:', error);
    }
  }, []);

  const fetchMedicos = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/doctors`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMedicos(response.data.data || []);
    } catch (error) {
      console.error('Error fetching médicos:', error);
    }
  }, []);

  // Para usuarios con rol médico: autoseleccionar su propio médico asignado
  useEffect(() => {
    if (user?.role !== 'medico' || !medicos.length || formData.medico_id) return;
    const mio = medicos.find(m => m.usuario_id === user.id);
    if (mio) {
      setFormData(prev => ({ ...prev, medico_id: mio.id, medico_nombre: mio.name }));
    }
  }, [medicos, user, formData.medico_id]);

  // Mantener sincronizado el ref del paciente actual (para acotar el Historial)
  useEffect(() => {
    pacienteIdRef.current = formData.paciente_id || null;
  }, [formData.paciente_id]);

  const buscarPacientes = useCallback(async (search) => {
    if (!search || search.length < 2) {
      setPacientes([]);
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/pacientes/buscar?search=${encodeURIComponent(search)}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPacientes(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchEvaluaciones(), fetchMedicos()]);
      // Cargar tipos de cirugía para CRM
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API_URL}/surgery-crm/tipos-cirugia`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTiposCirugia(response.data || []);
      } catch (error) {
        console.error('Error fetching tipos cirugía:', error);
      }
      // Cargar datos offline pendientes
      loadPendingOfflineData();
      setLoading(false);
    };
    init();
  }, [fetchEvaluaciones, fetchMedicos]);

  // ==================== SOPORTE OFFLINE ====================
  
  // Cargar datos pendientes de sincronización
  const loadPendingOfflineData = useCallback(() => {
    try {
      const stored = localStorage.getItem(OFFLINE_STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored);
        setPendingSync(data);
        if (data.length > 0) {
          setSyncStatus('pending');
        }
      }
    } catch (error) {
      console.error('Error loading offline data:', error);
    }
  }, []);

  // Guardar datos offline
  const saveOfflineData = useCallback((evaluacionData, action = 'save') => {
    try {
      const stored = localStorage.getItem(OFFLINE_STORAGE_KEY);
      const pending = stored ? JSON.parse(stored) : [];
      
      // Buscar si ya existe una entrada para esta evaluación
      const existingIndex = pending.findIndex(p => 
        p.data.paciente_id === evaluacionData.paciente_id && 
        (!p.data.id || p.data.id === evaluacionData.id)
      );
      
      const offlineEntry = {
        id: evaluacionData.id || `offline_${Date.now()}`,
        action,
        data: evaluacionData,
        timestamp: new Date().toISOString(),
        synced: false
      };
      
      if (existingIndex >= 0) {
        pending[existingIndex] = offlineEntry;
      } else {
        pending.push(offlineEntry);
      }
      
      localStorage.setItem(OFFLINE_STORAGE_KEY, JSON.stringify(pending));
      setPendingSync(pending);
      setSyncStatus('pending');
      
      return offlineEntry.id;
    } catch (error) {
      console.error('Error saving offline data:', error);
      return null;
    }
  }, []);

  // Sincronizar datos pendientes cuando hay conexión
  const syncPendingData = useCallback(async () => {
    if (!isOnline || pendingSync.length === 0) return;
    
    setSyncStatus('syncing');
    const token = localStorage.getItem('token');
    const newPending = [];
    let syncedCount = 0;
    
    for (const item of pendingSync) {
      if (item.synced) continue;
      
      try {
        if (item.data.id && !item.data.id.startsWith('offline_')) {
          // Actualizar evaluación existente
          await axios.patch(
            `${API_URL}/evaluaciones/${item.data.id}/autoguardar`,
            item.data,
            { headers: { Authorization: `Bearer ${token}` } }
          );
        } else {
          // Crear nueva evaluación
          const response = await axios.post(
            `${API_URL}/evaluaciones`,
            item.data,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          // Actualizar el ID local si la evaluación actual es esta
          if (evaluacionActual && evaluacionActual.id === item.id) {
            setEvaluacionActual(response.data);
          }
        }
        syncedCount++;
        item.synced = true;
      } catch (error) {
        console.error('Error syncing item:', error);
        newPending.push(item);
      }
    }
    
    // Actualizar almacenamiento
    const unsyncedItems = pendingSync.filter(p => !p.synced);
    if (unsyncedItems.length === 0) {
      localStorage.removeItem(OFFLINE_STORAGE_KEY);
      setPendingSync([]);
      setSyncStatus('synced');
      if (syncedCount > 0) {
        toast.success(`${syncedCount} evaluación(es) sincronizada(s)`);
        fetchEvaluaciones();
      }
    } else {
      localStorage.setItem(OFFLINE_STORAGE_KEY, JSON.stringify(unsyncedItems));
      setPendingSync(unsyncedItems);
      setSyncStatus('pending');
    }
  }, [isOnline, pendingSync, evaluacionActual, fetchEvaluaciones]);

  // Detectar cambios en la conexión
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      toast.success('Conexión restaurada');
      // Sincronizar datos pendientes
      setTimeout(() => syncPendingData(), 1000);
    };
    
    const handleOffline = () => {
      setIsOnline(false);
      toast.warning('Sin conexión - Los cambios se guardarán localmente');
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [syncPendingData]);

  // Intentar sincronizar periódicamente
  useEffect(() => {
    if (isOnline && pendingSync.length > 0) {
      syncIntervalRef.current = setInterval(() => {
        syncPendingData();
      }, 30000); // Cada 30 segundos
    }
    
    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    };
  }, [isOnline, pendingSync.length, syncPendingData]);

  // Limpiar estado 'synced' después de 3 segundos
  useEffect(() => {
    if (syncStatus === 'synced') {
      const timer = setTimeout(() => {
        setSyncStatus('');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [syncStatus]);

  // Guardar antes de cerrar la ventana si hay cambios sin guardar
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (autoguardadoStatus === 'Cambios sin guardar' && formData.paciente_id) {
        // Guardar offline antes de cerrar
        const dataToSave = {
          ...formData,
          id: evaluacionActual?.id || null
        };
        saveOfflineData(dataToSave, evaluacionActual?.id ? 'update' : 'create');
        
        // Mostrar advertencia
        e.preventDefault();
        e.returnValue = 'Tienes cambios sin guardar. ¿Estás seguro de salir?';
        return e.returnValue;
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [autoguardadoStatus, formData, evaluacionActual?.id, saveOfflineData]);

  useEffect(() => {
    const timer = setTimeout(() => {
      buscarPacientes(searchPaciente);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchPaciente, buscarPacientes]);

  // Calcular tiempo restante para sellado
  useEffect(() => {
    // No mostrar tiempo si no hay evaluación, está sellada, o es offline/nueva
    if (!evaluacionActual || evaluacionActual.sellado || !evaluacionActual.fecha_creacion || String(evaluacionActual.id).startsWith('offline_')) {
      setTiempoRestante(null);
      return;
    }
    
    const calcularTiempo = () => {
      const creacion = new Date(evaluacionActual.fecha_creacion);
      // Validar que la fecha sea válida
      if (isNaN(creacion.getTime())) {
        setTiempoRestante(null);
        return;
      }
      const limite = new Date(creacion.getTime() + 24 * 60 * 60 * 1000);
      const ahora = new Date();
      const diff = limite - ahora;
      
      if (diff <= 0) {
        setTiempoRestante(null);
        setEvaluacionActual(prev => ({ ...prev, sellado: true }));
        return;
      }
      
      const horas = Math.floor(diff / (1000 * 60 * 60));
      const minutos = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setTiempoRestante(`${horas}h ${minutos}m`);
    };
    
    calcularTiempo();
    const interval = setInterval(calcularTiempo, 60000);
    return () => clearInterval(interval);
  }, [evaluacionActual]);

  // Autoguardado - funciona tanto online como offline
  useEffect(() => {
    // No autoguardar si es solo lectura o no hay paciente seleccionado
    if (isReadOnly || !formData.paciente_id) return;
    
    if (autoguardadoRef.current) {
      clearTimeout(autoguardadoRef.current);
    }
    
    setAutoguardadoStatus('Cambios sin guardar');
    
    autoguardadoRef.current = setTimeout(async () => {
      // No crear evaluaciones VACÍAS por autoguardado: si es nueva y no hay datos clínicos reales, no guardar
      const esNueva = !evaluacionActual?.id;
      if (esNueva && !tieneDatosClinicos(formData)) {
        setAutoguardadoStatus('');
        return;
      }
      // === MODO OFFLINE ===
      if (!isOnline) {
        try {
          setAutoguardadoStatus('Guardando localmente...');
          const dataToSave = {
            ...formData,
            id: evaluacionActual?.id || null
          };
          const savedId = saveOfflineData(dataToSave, evaluacionActual?.id ? 'update' : 'create');
          
          if (savedId) {
            const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' });
            setAutoguardadoStatus(`Guardado offline ${now}`);
            lastSavedRef.current = new Date();
            // Si es nueva evaluación, guardar ID temporal
            if (!evaluacionActual?.id) {
              setEvaluacionActual({ ...formData, id: savedId });
            }
          } else {
            setAutoguardadoStatus('Error guardando offline');
          }
        } catch (error) {
          setAutoguardadoStatus('Error guardando offline');
          console.error('Error autoguardando offline:', error);
        }
        return;
      }
      
      // === MODO ONLINE ===
      try {
        setAutoguardadoStatus('Guardando...');
        const token = localStorage.getItem('token');
        
        if (evaluacionActual?.id && !String(evaluacionActual.id).startsWith('offline_')) {
          // Actualizar evaluación existente
          await axios.patch(
            `${API_URL}/evaluaciones/${evaluacionActual.id}/autoguardar`,
            formData,
            { headers: { Authorization: `Bearer ${token}` } }
          );
        } else {
          // Crear nueva evaluación automáticamente
          const response = await axios.post(
            `${API_URL}/evaluaciones`,
            formData,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          setEvaluacionActual(response.data);
          fetchEvaluaciones(); // Actualizar lista
        }
        
        const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' });
        setAutoguardadoStatus(`Guardado a las ${now}`);
        lastSavedRef.current = new Date();
      } catch (error) {
        if (error.response?.status === 423) {
          toast.error('Expediente sellado. No se puede editar.');
          setEvaluacionActual(prev => ({ ...prev, sellado: true }));
        } else {
          // Si falla la conexión, guardar offline
          console.warn('Error de red, guardando offline:', error);
          setAutoguardadoStatus('Guardando localmente...');
          const dataToSave = {
            ...formData,
            id: evaluacionActual?.id || null
          };
          const savedId = saveOfflineData(dataToSave, evaluacionActual?.id ? 'update' : 'create');
          if (savedId) {
            const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' });
            setAutoguardadoStatus(`Guardado offline ${now}`);
          } else {
            setAutoguardadoStatus('Error al guardar');
          }
        }
      }
    }, 2000); // 2 segundos de debounce
    
    return () => {
      if (autoguardadoRef.current) {
        clearTimeout(autoguardadoRef.current);
      }
    };
  }, [formData, evaluacionActual?.id, isReadOnly, fetchEvaluaciones, isOnline, saveOfflineData]);

  // Cargar evaluación
  const cargarEvaluacion = async (evaluacion) => {
    // Guardar un snapshot de la evaluación en curso (del día) para poder regresar a ella
    if (!viendoHistorial) {
      borradorRef.current = { formData, evaluacionActual, searchPaciente };
    }
    setViendoHistorial(true);
    setEvaluacionActual(evaluacion);
    
    // Resetear estado CRM al cargar nueva evaluación
    setCrmEnviado(false);
    setCrmForm({
      tipo_cirugia: '',
      ojo: 'OU',
      diagnostico: '',
      prioridad: 'normal',
      nivel_interes: 'interesado',
      notas: ''
    });
    
    // Migrar datos antiguos (oi → os) si es necesario
    const examenData = evaluacion.examen || {};
    const migratedExamen = {
      ...evaluacionVacia.examen,
      avsc_od: examenData.avsc_od || '',
      avsc_os: examenData.avsc_os || examenData.avsc_oi || '',
      avcc_od: examenData.avcc_od || '',
      avcc_os: examenData.avcc_os || examenData.avcc_oi || '',
      lensometria_od: { ...evaluacionVacia.examen.lensometria_od, ...examenData.lensometria_od },
      lensometria_os: { ...evaluacionVacia.examen.lensometria_os, ...(examenData.lensometria_os || examenData.lensometria_oi) },
      refraccion_od: { ...evaluacionVacia.examen.refraccion_od, ...examenData.refraccion_od },
      refraccion_os: { ...evaluacionVacia.examen.refraccion_os, ...(examenData.refraccion_os || examenData.refraccion_oi) },
      queratometria_od: examenData.queratometria_od || '',
      queratometria_os: examenData.queratometria_os || examenData.queratometria_oi || '',
      pio_od: examenData.pio_od || '',
      pio_os: examenData.pio_os || examenData.pio_oi || '',
      pio_metodo: examenData.pio_metodo || '',
      segmento_anterior: examenData.segmento_anterior || '',
      segmento_posterior: examenData.segmento_posterior || '',
      motilidad_ocular: examenData.motilidad_ocular || ''
    };
    
    // Migrar recetas (oi → os) y convertir a formato de múltiples recetas
    const recetasData = evaluacion.recetas || {};
    
    // Migrar receta de anteojos antigua a la nueva estructura
    const anteojosLegacy = {
      ...evaluacionVacia.recetas.anteojos,
      ...recetasData.anteojos,
      od: { ...evaluacionVacia.recetas.anteojos.od, ...recetasData.anteojos?.od },
      os: { ...evaluacionVacia.recetas.anteojos.os, ...(recetasData.anteojos?.os || recetasData.anteojos?.oi) }
    };
    
    // Migrar receta de lentes de contacto antigua
    const lentesLegacy = {
      ...evaluacionVacia.recetas.lentes_contacto,
      ...recetasData.lentes_contacto,
      od: { ...evaluacionVacia.recetas.lentes_contacto.od, ...recetasData.lentes_contacto?.od },
      os: { ...evaluacionVacia.recetas.lentes_contacto.os, ...(recetasData.lentes_contacto?.os || recetasData.lentes_contacto?.oi) }
    };
    
    // Si ya tiene listas, usarlas; si no, migrar la receta individual a lista
    let anteojosLista = recetasData.anteojos_lista || [];
    let lentesLista = recetasData.lentes_contacto_lista || [];
    
    // Migrar receta antigua si existe y la lista está vacía
    if (anteojosLista.length === 0 && (anteojosLegacy.od?.esfera || anteojosLegacy.os?.esfera)) {
      anteojosLista = [{ ...anteojosLegacy, id: `ant_migrated_${Date.now()}`, fecha_creacion: evaluacion.fecha_creacion || new Date().toISOString() }];
    }
    if (lentesLista.length === 0 && (lentesLegacy.od?.poder || lentesLegacy.os?.poder)) {
      lentesLista = [{ ...lentesLegacy, id: `lc_migrated_${Date.now()}`, fecha_creacion: evaluacion.fecha_creacion || new Date().toISOString() }];
    }
    
    const migratedRecetas = {
      medicamentos: { items: recetasData.medicamentos?.items || [] },
      anteojos_lista: anteojosLista,
      lentes_contacto_lista: lentesLista,
      anteojos: anteojosLegacy,
      lentes_contacto: lentesLegacy
    };
    
    setFormData({
      ...evaluacionVacia,
      ...evaluacion,
      antecedentes: { ...evaluacionVacia.antecedentes, ...evaluacion.antecedentes },
      examen: migratedExamen,
      lectura_examenes: evaluacion.lectura_examenes || '',
      recomendaciones: { ...evaluacionVacia.recomendaciones, ...evaluacion.recomendaciones },
      recetas: migratedRecetas
    });
    setSearchPaciente(evaluacion.paciente_nombre || '');
    setAutoguardadoStatus('');
  };

  // Regresar a la evaluación del día (en curso) tras haber abierto una del historial
  const volverAEvaluacionActual = () => {
    const b = borradorRef.current;
    if (b) {
      setEvaluacionActual(b.evaluacionActual);
      setFormData(b.formData);
      setSearchPaciente(b.searchPaciente || '');
      setAutoguardadoStatus('');
    }
    setViendoHistorial(false);
  };

  // Nueva evaluación
  const nuevaEvaluacion = () => {
    setEvaluacionActual(null);
    setViendoHistorial(false);
    borradorRef.current = null;
    setFormData(evaluacionVacia);
    setSearchPaciente('');
    setAutoguardadoStatus('');
    setTiempoRestante(null);
    // Limpiar el historial (no hay paciente seleccionado)
    pacienteIdRef.current = null;
    setEvaluaciones([]);
    // Resetear estado CRM
    setCrmEnviado(false);
    setCrmForm({
      tipo_cirugia: '',
      ojo: 'OU',
      diagnostico: '',
      prioridad: 'normal',
      nivel_interes: 'interesado',
      notas: ''
    });
  };

  // Limpiar borradores vacíos generados por el autoguardado (solo admin/superadmin)
  const handleLimpiarVacias = async () => {
    try {
      const token = localStorage.getItem('token');
      const { data } = await axios.get(`${API_URL}/evaluaciones/vacias/contar`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const n = data.vacias || 0;
      if (n === 0) {
        toast.info('No hay evaluaciones vacías para eliminar');
        return;
      }
      toast(`Se encontraron ${n} evaluaciones vacías`, {
        description: 'Se eliminarán las evaluaciones sin datos (no selladas ni importadas). Esta acción no se puede deshacer.',
        duration: 12000,
        action: {
          label: `Eliminar ${n}`,
          onClick: async () => {
            try {
              const res = await axios.delete(`${API_URL}/evaluaciones/vacias/purgar`, {
                headers: { Authorization: `Bearer ${token}` }
              });
              toast.success(`${res.data.eliminadas} evaluaciones vacías eliminadas`);
              fetchEvaluaciones();
            } catch (e) {
              toast.error('Error al eliminar evaluaciones vacías');
            }
          }
        }
      });
    } catch (e) {
      toast.error('Error al contar evaluaciones vacías');
    }
  };

  // Guardar evaluación
  const guardarEvaluacion = async () => {
    if (!formData.paciente_id) {
      toast.error('Debe seleccionar un paciente');
      return;
    }
    
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      let evaluacionId = evaluacionActual?.id;
      
      if (evaluacionActual?.id) {
        // Actualizar
        const response = await axios.put(
          `${API_URL}/evaluaciones/${evaluacionActual.id}`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setEvaluacionActual(response.data);
        evaluacionId = response.data.id;
        toast.success('Evaluación guardada correctamente');
      } else {
        // Crear nueva
        const response = await axios.post(
          `${API_URL}/evaluaciones`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setEvaluacionActual(response.data);
        evaluacionId = response.data.id;
        toast.success('Evaluación creada correctamente');
      }
      
      // Guardar historial médico del paciente (antecedentes y medicamentos persisten)
      try {
        await axios.put(
          `${API_URL}/evaluaciones/paciente/${formData.paciente_id}/historial-medico`,
          {
            antecedentes: formData.antecedentes,
            medicamentos_actuales: formData.medicamentos_actuales,
            medicamentos_previos: formData.medicamentos_previos
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } catch (historialError) {
        console.error('Error guardando historial médico:', historialError);
      }
      
      // Agregar medicamentos de la receta al historial de medicamentos actuales
      const medicamentosReceta = formData.recetas?.medicamentos?.items || [];
      for (const med of medicamentosReceta) {
        if (med.medicamento) {
          try {
            await axios.post(
              `${API_URL}/evaluaciones/paciente/${formData.paciente_id}/agregar-medicamento-receta`,
              {
                medicamento: med.medicamento,
                dosis: med.dosis || '',
                frecuencia: med.frecuencia || '',
                via: med.via || ''
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );
          } catch (medError) {
            // Ignorar errores de medicamentos individuales
            console.error('Error agregando medicamento:', medError);
          }
        }
      }
      
      // Crear próxima cita si está habilitada
      if (formData.proxima_cita?.agendar && formData.proxima_cita?.fecha && formData.proxima_cita?.hora && formData.proxima_cita?.medico_id) {
        try {
          await agendaApi.createProximaCita({
            paciente_id: formData.paciente_id,
            paciente_nombre: formData.paciente_nombre,
            medico_id: formData.proxima_cita.medico_id,
            medico_nombre: formData.proxima_cita.medico_nombre,
            fecha: formData.proxima_cita.fecha,
            hora_inicio: formData.proxima_cita.hora,
            tipo_cita: formData.proxima_cita.tipo_cita || 'Subsecuente',
            notas: formData.proxima_cita.notas,
            evaluacion_id: evaluacionId
          });
          toast.success('Próxima cita agendada');
        } catch (citaError) {
          if (citaError.response?.status === 400) {
            toast.info('Ya existe una cita para esa fecha y hora');
          } else {
            console.error('Error al crear cita:', citaError);
          }
        }
      }
      
      const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' });
      setAutoguardadoStatus(`Guardado a las ${now}`);
      fetchEvaluaciones();
    } catch (error) {
      if (error.response?.status === 423) {
        toast.error('Expediente sellado. No se puede modificar.');
        setEvaluacionActual(prev => ({ ...prev, sellado: true }));
      } else {
        toast.error(error.response?.data?.detail || 'Error al guardar');
      }
    } finally {
      setSaving(false);
    }
  };

  // Seleccionar paciente y cargar historial médico
  const seleccionarPaciente = async (paciente) => {
    setFormData(prev => ({
      ...prev,
      paciente_id: paciente.id,
      paciente_nombre: paciente.nombre_completo,
      paciente_edad: paciente.edad || 0,
      paciente_sexo: paciente.gender || '',
      paciente_expediente: paciente.record_number || ''
    }));
    setSearchPaciente(paciente.nombre_completo);
    setShowPacienteList(false);
    // Acotar el Historial a las evaluaciones de ESTE paciente
    pacienteIdRef.current = paciente.id;
    // Nuevo contexto de borrador para este paciente
    borradorRef.current = null;
    setViendoHistorial(false);
    fetchEvaluaciones(paciente.id);
    
    // Cargar historial médico del paciente (antecedentes y medicamentos)
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/evaluaciones/paciente/${paciente.id}/historial-medico`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data) {
        const historial = response.data;
        setFormData(prev => ({
          ...prev,
          antecedentes: historial.antecedentes || prev.antecedentes,
          medicamentos_actuales: historial.medicamentos_actuales || prev.medicamentos_actuales,
          medicamentos_previos: historial.medicamentos_previos || prev.medicamentos_previos
        }));
        
        if (historial.fuente === 'historial_guardado' || historial.fuente === 'ultima_evaluacion') {
          toast.info('Se cargaron los antecedentes y medicamentos previos del paciente');
        }
      }
    } catch (error) {
      console.error('Error cargando historial médico:', error);
      // No mostrar error, simplemente continuar sin historial
    }
  };

  // Preseleccionar paciente cuando se llega desde el listado de Pacientes (?paciente_id=)
  useEffect(() => {
    const pid = searchParams.get('paciente_id');
    if (!pid || preseleccionDoneRef.current || loading) return;
    preseleccionDoneRef.current = true;
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const { data: p } = await axios.get(`${API_URL}/patients/${pid}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Calcular edad a partir de la fecha de nacimiento
        let edad = 0;
        if (p.birth_date) {
          const nac = new Date(p.birth_date);
          const hoy = new Date();
          edad = hoy.getFullYear() - nac.getFullYear();
          const m = hoy.getMonth() - nac.getMonth();
          if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) edad--;
        }
        await seleccionarPaciente({
          id: p.id,
          nombre_completo: `${p.first_name || ''} ${p.last_name || ''}`.trim(),
          edad: edad > 0 ? edad : 0,
          gender: p.gender || '',
          record_number: p.record_number || ''
        });
        toast.success('Paciente cargado para nueva evaluación');
      } catch (error) {
        console.error('Error preseleccionando paciente:', error);
        toast.error('No se pudo cargar el paciente seleccionado');
      }
    })();
  }, [searchParams, loading]);

  // Actualizar campo anidado
  const updateNestedField = (path, value) => {
    setFormData(prev => {
      const newData = { ...prev };
      const keys = path.split('.');
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        if (Array.isArray(current[keys[i]])) {
          current[keys[i]] = [...current[keys[i]]];
        } else {
          current[keys[i]] = { ...current[keys[i]] };
        }
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = value;
      return newData;
    });
  };

  // Agregar item a array
  const addArrayItem = (path, item) => {
    setFormData(prev => {
      const newData = { ...prev };
      const keys = path.split('.');
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = [...(current[keys[keys.length - 1]] || []), item];
      return newData;
    });
  };

  // Eliminar item de array
  const removeArrayItem = (path, index) => {
    setFormData(prev => {
      const newData = { ...prev };
      const keys = path.split('.');
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = current[keys[keys.length - 1]].filter((_, i) => i !== index);
      return newData;
    });
  };

  // Actualizar item en array
  const updateArrayItem = (path, index, field, value) => {
    setFormData(prev => {
      const newData = { ...prev };
      const keys = path.split('.');
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      const arr = [...current[keys[keys.length - 1]]];
      arr[index] = { ...arr[index], [field]: value };
      current[keys[keys.length - 1]] = arr;
      return newData;
    });
  };

  // Imprimir receta
  const handlePrint = (type) => {
    setPrintType(type);
    setPrintDialogOpen(true);
    setTimeout(() => {
      window.print();
    }, 500);
  };

  // Exportar evaluación completa a PDF
  const handleExportPDF = async () => {
    if (!evaluacionActual?.id) {
      toast.error('Debe guardar la evaluación antes de exportar a PDF');
      return;
    }
    
    try {
      toast.loading('Generando PDF...', { id: 'pdf-loading' });
      
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/evaluaciones/${evaluacionActual.id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Crear enlace de descarga
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Obtener nombre del archivo del header o usar default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'evaluacion_oftalmologica.pdf';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) filename = match[1];
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF descargado correctamente', { id: 'pdf-loading' });
    } catch (error) {
      console.error('Error exportando PDF:', error);
      toast.error('Error al generar PDF', { id: 'pdf-loading' });
    }
  };

  // Enviar a CRM de Cirugías
  const handleEnviarCRM = async () => {
    if (!crmForm.tipo_cirugia) {
      toast.error('Debe seleccionar un tipo de cirugía');
      return;
    }
    
    if (!formData.paciente_id) {
      toast.error('Debe seleccionar un paciente primero');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      let evaluacionId = evaluacionActual?.id;
      
      // Si no hay evaluación guardada, guardarla primero
      if (!evaluacionId) {
        setAutoguardadoStatus('Guardando evaluación...');
        const response = await axios.post(
          `${API_URL}/evaluaciones`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setEvaluacionActual(response.data);
        evaluacionId = response.data.id;
        fetchEvaluaciones();
        const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guatemala' });
        setAutoguardadoStatus(`Guardado a las ${now}`);
      }
      
      // Auto-completar diagnóstico si está vacío
      const diagnosticoAuto = crmForm.diagnostico || 
        formData.diagnosticos?.map(d => d.descripcion).join(', ') || '';
      
      await axios.post(
        `${API_URL}/evaluaciones/${evaluacionId}/agregar-crm-cirugia`,
        {
          tipo_cirugia: crmForm.tipo_cirugia,
          ojo: crmForm.ojo,
          diagnostico: diagnosticoAuto,
          prioridad: crmForm.prioridad,
          nivel_interes: crmForm.nivel_interes,
          notas: crmForm.notas
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Paciente agregado al CRM de Cirugías para ${crmForm.tipo_cirugia}`);
      setCrmEnviado(true);
      setCrmDialogOpen(false);
      // No resetear el form para que se vea lo que se envió
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al agregar al CRM');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-6 space-y-4">
          <Skeleton className="h-16 w-full" />
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-96" />
            <Skeleton className="h-96" />
            <Skeleton className="h-96" />
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      {/* Print Styles - Optimizado para Media Carta HORIZONTAL (8.5" x 5.5" landscape) */}
      <style>{`
        @media print {
          @page {
            size: 8.5in 5.5in landscape;
            margin: 0.3in 0.4in;
          }
          body * { visibility: hidden; }
          .print-area, .print-area * { visibility: visible; }
          .print-area { 
            position: absolute; 
            left: 0; 
            top: 0; 
            width: 8in;
            font-size: 9pt;
          }
          .no-print { display: none !important; }
          .print-header { border-bottom: 2px solid #0F6E56 !important; }
          .print-title { color: #0F6E56 !important; }
          .print-table th { 
            background-color: #f0f9f6 !important; 
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .print-med-card {
            border: 1px solid #e5e7eb !important;
            break-inside: avoid;
            page-break-inside: avoid;
          }
          .print-med-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
          }
          .print-cita-box {
            background-color: #eff6ff !important;
            border: 2px solid #3b82f6 !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
        }
      `}</style>
      
      <div className="space-y-4 animate-fade-in no-print" data-testid="evaluacion-page">
        {/* Barra Superior */}
        <div className="bg-white rounded-xl border p-4 shadow-sm" style={{ borderColor: 'var(--border-card)' }}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Selector de Paciente */}
            <div className="flex items-center gap-4 flex-1">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  value={searchPaciente}
                  onChange={(e) => {
                    setSearchPaciente(e.target.value);
                    setShowPacienteList(true);
                  }}
                  onFocus={() => setShowPacienteList(true)}
                  placeholder="Buscar paciente por nombre o expediente..."
                  className="input-teal pl-10"
                  disabled={isReadOnly}
                  data-testid="search-paciente"
                />
                {showPacienteList && pacientes.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {pacientes.map((p) => (
                      <div
                        key={p.id}
                        className="px-4 py-3 hover:bg-blue-50 cursor-pointer border-b last:border-b-0"
                        data-testid={`eval-paciente-option-${p.id}`}
                        onClick={() => seleccionarPaciente(p)}
                      >
                        <div className="font-medium text-sm">{p.nombre_completo}</div>
                        <div className="text-xs text-gray-500">
                          Exp: {p.record_number} | {p.edad} años | {p.gender === 'masculino' ? 'M' : p.gender === 'femenino' ? 'F' : '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Datos del paciente seleccionado */}
              {formData.paciente_id && (
                <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 rounded-lg">
                  <User className="w-5 h-5 text-blue-600" />
                  <div>
                    <div className="font-semibold text-sm">{formData.paciente_nombre}</div>
                    <div className="text-xs text-gray-600">
                      {formData.paciente_expediente} | {formData.paciente_edad} años | {formData.paciente_sexo === 'masculino' ? 'Masculino' : formData.paciente_sexo === 'femenino' ? 'Femenino' : '-'}
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Fecha y Médico */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Label className="text-xs">Fecha:</Label>
                <Input
                  type="date"
                  value={formData.fecha}
                  onChange={(e) => updateNestedField('fecha', e.target.value)}
                  disabled={isReadOnly}
                  className="input-teal w-36 h-9"
                />
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-xs">Médico:</Label>
                <Select
                  value={formData.medico_id}
                  onValueChange={(value) => {
                    const med = medicos.find(m => m.id === value);
                    updateNestedField('medico_id', value);
                    updateNestedField('medico_nombre', med?.name || '');
                  }}
                  disabled={isReadOnly}
                >
                  <SelectTrigger className="input-teal w-48 h-9">
                    <SelectValue placeholder="Seleccionar médico" />
                  </SelectTrigger>
                  <SelectContent>
                    {medicos.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Botones y Estado */}
            <div className="flex items-center gap-2">
              {/* Indicador de conexión */}
              <div className="flex items-center gap-1.5" data-testid="connection-status">
                {isOnline ? (
                  <Badge className="bg-emerald-100 text-emerald-700 text-xs flex items-center gap-1">
                    <Wifi className="w-3 h-3" />
                    <span className="hidden sm:inline">En línea</span>
                  </Badge>
                ) : (
                  <Badge className="bg-red-100 text-red-700 text-xs flex items-center gap-1 animate-pulse">
                    <WifiOff className="w-3 h-3" />
                    <span className="hidden sm:inline">Sin conexión</span>
                  </Badge>
                )}
                
                {/* Indicador de sincronización pendiente */}
                {pendingSync.length > 0 && (
                  <Badge 
                    className={`text-xs flex items-center gap-1 ${
                      syncStatus === 'syncing' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-amber-100 text-amber-700'
                    }`}
                    data-testid="sync-status"
                  >
                    {syncStatus === 'syncing' ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span className="hidden sm:inline">Sincronizando...</span>
                      </>
                    ) : (
                      <>
                        <CloudOff className="w-3 h-3" />
                        <span className="hidden sm:inline">{pendingSync.length} pendiente(s)</span>
                      </>
                    )}
                  </Badge>
                )}
                
                {syncStatus === 'synced' && pendingSync.length === 0 && (
                  <Badge className="bg-emerald-100 text-emerald-700 text-xs flex items-center gap-1" data-testid="sync-complete">
                    <Cloud className="w-3 h-3" />
                    <span className="hidden sm:inline">Sincronizado</span>
                  </Badge>
                )}
              </div>
              
              {/* Estado de guardado */}
              {autoguardadoStatus && (
                <Badge className={`text-xs ${
                  autoguardadoStatus.includes('Guardado') ? 'bg-green-100 text-green-700' :
                  autoguardadoStatus.includes('Guardando') || autoguardadoStatus.includes('localmente') ? 'bg-blue-100 text-blue-700' :
                  autoguardadoStatus.includes('offline') ? 'bg-amber-100 text-amber-700' :
                  'bg-orange-100 text-orange-700'
                }`}>
                  {autoguardadoStatus}
                </Badge>
              )}
              
              {/* Tiempo restante para sellado */}
              {tiempoRestante && !evaluacionActual?.sellado && (
                <Badge className="bg-amber-100 text-amber-700 text-xs">
                  <Clock className="w-3 h-3 mr-1" />
                  Se sella en {tiempoRestante}
                </Badge>
              )}
              
              {/* Indicador de sellado */}
              {evaluacionActual?.sellado && (
                <Badge className="bg-red-100 text-red-700 text-xs">
                  <Lock className="w-3 h-3 mr-1" />
                  Expediente sellado
                </Badge>
              )}
              
              {/* Dropdown de Historial */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="btn-outline" data-testid="historial-toggle-btn">
                    <FileText className="w-4 h-4 mr-1" />
                    Historial
                    <ChevronDown className="w-3 h-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-80 max-h-96 overflow-y-auto">
                  {viendoHistorial && borradorRef.current && (
                    <DropdownMenuItem
                      onClick={volverAEvaluacionActual}
                      data-testid="historial-volver-actual"
                      className="flex flex-col items-start py-2 cursor-pointer bg-teal-50 border-b border-teal-100"
                    >
                      <span className="font-semibold text-sm text-teal-700">← Volver a la evaluación del día</span>
                      <span className="text-xs text-gray-500">Evaluación en curso (sin cerrar)</span>
                    </DropdownMenuItem>
                  )}
                  {evaluaciones.length === 0 ? (
                    <div className="px-3 py-4 text-center text-gray-500 text-sm">
                      {formData.paciente_id ? 'Este paciente no tiene evaluaciones registradas' : 'Selecciona un paciente para ver su historial'}
                    </div>
                  ) : (
                    evaluaciones.map((ev) => {
                      // Diagnóstico principal: primer elemento del array 'diagnosticos' (o el legacy 'diagnostico')
                      const dxList = Array.isArray(ev.diagnosticos) ? ev.diagnosticos : [];
                      const dxPrincipal = dxList.length > 0
                        ? (dxList[0].descripcion || dxList[0].nombre || '')
                        : (ev.diagnostico || '');
                      const dxExtra = dxList.length > 1 ? ` +${dxList.length - 1} más` : '';
                      return (
                        <DropdownMenuItem 
                          key={ev.id}
                          onClick={() => cargarEvaluacion(ev)}
                          data-testid={`historial-item-${ev.id}`}
                          className={`flex flex-col items-start py-2 cursor-pointer ${
                            evaluacionActual?.id === ev.id ? 'bg-blue-50' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="font-semibold text-sm text-slate-800" data-testid={`historial-fecha-${ev.id}`}>
                              {formatFechaHistorial(ev.fecha)}
                            </span>
                            {ev.sellado && (
                              <Lock className="w-3 h-3 text-red-500 ml-2 flex-shrink-0" />
                            )}
                          </div>
                          {dxPrincipal ? (
                            <span className="text-xs text-teal-700 mt-0.5 truncate max-w-[270px]" data-testid={`historial-dx-${ev.id}`}>
                              <strong>Dx:</strong> {dxPrincipal.length > 55 ? dxPrincipal.substring(0, 55) + '…' : dxPrincipal}{dxExtra}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400 mt-0.5">Sin diagnóstico registrado</span>
                          )}
                          {ev.motivo_consulta && (
                            <span className="text-xs text-gray-500 truncate max-w-[270px]">
                              {ev.motivo_consulta.length > 50 ? ev.motivo_consulta.substring(0, 50) + '…' : ev.motivo_consulta}
                            </span>
                          )}
                        </DropdownMenuItem>
                      );
                    })
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              
              <Button
                variant="outline"
                size="sm"
                onClick={nuevaEvaluacion}
                className="btn-outline"
                disabled={!canEdit}
              >
                <Plus className="w-4 h-4 mr-1" />
                Nueva
              </Button>
              
              {canEdit && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleLimpiarVacias}
                  className="btn-outline text-amber-600 border-amber-300 hover:bg-amber-50"
                  data-testid="limpiar-vacias-btn"
                  title="Eliminar borradores vacíos generados por el autoguardado"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Limpiar vacías
                </Button>
              )}
              
              {canEdit && !isReadOnly && (
                <Button
                  size="sm"
                  onClick={guardarEvaluacion}
                  disabled={saving || !formData.paciente_id}
                  className="btn-primary"
                >
                  <Save className="w-4 h-4 mr-1" />
                  {saving ? 'Guardando...' : 'Guardar'}
                </Button>
              )}
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="btn-outline">
                    <Printer className="w-4 h-4 mr-1" />
                    Imprimir
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleExportPDF()}>
                    <FileDown className="w-4 h-4 mr-2" />
                    Exportar PDF Completo
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => handlePrint('medicamentos')}>
                    <Pill className="w-4 h-4 mr-2" />
                    Receta de Medicamentos
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handlePrint('anteojos')}>
                    <Glasses className="w-4 h-4 mr-2" />
                    Receta de Anteojos
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handlePrint('lentes_contacto')}>
                    <Contact className="w-4 h-4 mr-2" />
                    Receta de Lentes de Contacto
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Layout de 3 Columnas */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          
          {/* COLUMNA IZQUIERDA: Antecedentes y Medicamentos */}
          <div className="space-y-4">
            {/* Motivo de Consulta */}
            <Card className="card-teal">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Stethoscope className="w-4 h-4 text-blue-600" />
                  Motivo de Consulta
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={formData.motivo_consulta}
                  onChange={(e) => updateNestedField('motivo_consulta', e.target.value)}
                  disabled={isReadOnly}
                  placeholder="Motivo principal de la consulta..."
                  className="input-teal min-h-[60px]"
                />
                <div>
                  <Label className="text-xs">Padecimiento Actual</Label>
                  <Textarea
                    value={formData.padecimiento_actual}
                    onChange={(e) => updateNestedField('padecimiento_actual', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Historia detallada del padecimiento..."
                    className="input-teal min-h-[80px]"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Antecedentes */}
            <CollapsibleSection title="Antecedentes de Importancia" icon={ClipboardList}>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs">Personales Patológicos</Label>
                  <Textarea
                    value={formData.antecedentes.personales_patologicos}
                    onChange={(e) => updateNestedField('antecedentes.personales_patologicos', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Diabetes, hipertensión, cardiopatía, tiroides, otras enfermedades crónicas..."
                    className="input-teal min-h-[60px] text-sm"
                  />
                </div>
                
                <div>
                  <Label className="text-xs">Oftalmológicos</Label>
                  <Textarea
                    value={formData.antecedentes.oftalmologicos}
                    onChange={(e) => updateNestedField('antecedentes.oftalmologicos', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Cirugías oculares, uso de lentes, glaucoma..."
                    className="input-teal min-h-[50px] text-sm"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Quirúrgicos</Label>
                    <Textarea
                      value={formData.antecedentes.quirurgicos}
                      onChange={(e) => updateNestedField('antecedentes.quirurgicos', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal min-h-[40px] text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Alergias</Label>
                    <Textarea
                      value={formData.antecedentes.alergias}
                      onChange={(e) => updateNestedField('antecedentes.alergias', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal min-h-[40px] text-sm"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Familiares</Label>
                    <Textarea
                      value={formData.antecedentes.familiares}
                      onChange={(e) => updateNestedField('antecedentes.familiares', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal min-h-[40px] text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Hábitos</Label>
                    <Textarea
                      value={formData.antecedentes.habitos}
                      onChange={(e) => updateNestedField('antecedentes.habitos', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal min-h-[40px] text-sm"
                    />
                  </div>
                </div>
              </div>
            </CollapsibleSection>

            {/* Medicamentos */}
            <CollapsibleSection 
              title="Medicamentos" 
              icon={Pill}
              badge={`${formData.medicamentos_actuales.length + formData.medicamentos_previos.length}`}
            >
              <div className="space-y-4">
                {/* Medicamentos Actuales */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-semibold">Actuales</Label>
                    {!isReadOnly && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addArrayItem('medicamentos_actuales', { nombre: '', dosis: '', frecuencia: '', via: '', desde: '' })}
                        className="h-6 text-xs text-blue-600 hover:text-blue-700"
                      >
                        <Plus className="w-3 h-3 mr-1" /> Agregar
                      </Button>
                    )}
                  </div>
                  {formData.medicamentos_actuales.map((med, idx) => (
                    <div key={idx} className="flex gap-2 mb-2 items-start">
                      <div className="flex-1 grid grid-cols-2 gap-1">
                        <Autocomplete
                          value={med.nombre}
                          onChange={(v) => updateArrayItem('medicamentos_actuales', idx, 'nombre', v)}
                          placeholder="Medicamento"
                          fetchUrl="/catalogos/medicamentos"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                        <Input
                          value={med.dosis}
                          onChange={(e) => updateArrayItem('medicamentos_actuales', idx, 'dosis', e.target.value)}
                          placeholder="Dosis"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                        <Input
                          value={med.frecuencia}
                          onChange={(e) => updateArrayItem('medicamentos_actuales', idx, 'frecuencia', e.target.value)}
                          placeholder="Frecuencia"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                        <Input
                          value={med.via}
                          onChange={(e) => updateArrayItem('medicamentos_actuales', idx, 'via', e.target.value)}
                          placeholder="Vía"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                      </div>
                      {!isReadOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeArrayItem('medicamentos_actuales', idx)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                
                {/* Medicamentos Previos */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-semibold">Previos</Label>
                    {!isReadOnly && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addArrayItem('medicamentos_previos', { nombre: '', dosis: '', motivo: '', periodo: '' })}
                        className="h-6 text-xs text-blue-600 hover:text-blue-700"
                      >
                        <Plus className="w-3 h-3 mr-1" /> Agregar
                      </Button>
                    )}
                  </div>
                  {formData.medicamentos_previos.map((med, idx) => (
                    <div key={idx} className="flex gap-2 mb-2 items-start">
                      <div className="flex-1 grid grid-cols-2 gap-1">
                        <Autocomplete
                          value={med.nombre}
                          onChange={(v) => updateArrayItem('medicamentos_previos', idx, 'nombre', v)}
                          placeholder="Medicamento"
                          fetchUrl="/catalogos/medicamentos"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                        <Input
                          value={med.motivo}
                          onChange={(e) => updateArrayItem('medicamentos_previos', idx, 'motivo', e.target.value)}
                          placeholder="Motivo"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                      </div>
                      {!isReadOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeArrayItem('medicamentos_previos', idx)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </CollapsibleSection>
          </div>

          {/* COLUMNA CENTRAL: Examen Oftalmológico */}
          <div className="space-y-4">
            <CollapsibleSection title="Examen Oftalmológico" icon={Eye} defaultOpen={true}>
              <div className="space-y-4">
                {/* Encabezado OD/OS */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div></div>
                  <div className="bg-blue-100 rounded py-1 text-xs font-semibold text-blue-700">OD (Derecho)</div>
                  <div className="bg-blue-100 rounded py-1 text-xs font-semibold text-blue-700">OS (Izquierdo)</div>
                </div>
                
                {/* Agudeza Visual */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Agudeza Visual</Label>
                  <CampoODOS
                    label="Sin Corrección"
                    valueOD={formData.examen.avsc_od}
                    valueOS={formData.examen.avsc_os}
                    onChangeOD={(v) => updateNestedField('examen.avsc_od', v)}
                    onChangeOS={(v) => updateNestedField('examen.avsc_os', v)}
                    disabled={isReadOnly}
                    placeholder="20/..."
                  />
                  <CampoODOS
                    label="Con Corrección"
                    valueOD={formData.examen.avcc_od}
                    valueOS={formData.examen.avcc_os}
                    onChangeOD={(v) => updateNestedField('examen.avcc_od', v)}
                    onChangeOS={(v) => updateNestedField('examen.avcc_os', v)}
                    disabled={isReadOnly}
                    placeholder="20/..."
                  />
                </div>
                
                {/* Lensometría */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Lensometría</Label>
                  <div className="grid grid-cols-4 gap-1 text-center text-xs">
                    <div></div>
                    <div className="text-gray-500">Esfera</div>
                    <div className="text-gray-500">Cilindro</div>
                    <div className="text-gray-500">Eje</div>
                  </div>
                  <div className="grid grid-cols-4 gap-1 items-center">
                    <Label className="text-xs text-right">OD</Label>
                    {['esfera', 'cilindro', 'eje'].map(field => (
                      <Input
                        key={field}
                        value={formData.examen.lensometria_od[field]}
                        onChange={(e) => updateNestedField(`examen.lensometria_od.${field}`, e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-4 gap-1 items-center">
                    <Label className="text-xs text-right">OS</Label>
                    {['esfera', 'cilindro', 'eje'].map(field => (
                      <Input
                        key={field}
                        value={formData.examen.lensometria_os[field]}
                        onChange={(e) => updateNestedField(`examen.lensometria_os.${field}`, e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                    ))}
                  </div>
                </div>
                
                {/* Refracción */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Refracción</Label>
                  <div className="grid grid-cols-5 gap-1 text-center text-xs">
                    <div></div>
                    <div className="text-gray-500">Esfera</div>
                    <div className="text-gray-500">Cilindro</div>
                    <div className="text-gray-500">Eje</div>
                    <div className="text-gray-500">Adición</div>
                  </div>
                  <div className="grid grid-cols-5 gap-1 items-center">
                    <Label className="text-xs text-right">OD</Label>
                    {['esfera', 'cilindro', 'eje', 'adicion'].map(field => (
                      <Input
                        key={field}
                        value={formData.examen.refraccion_od[field]}
                        onChange={(e) => updateNestedField(`examen.refraccion_od.${field}`, e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-5 gap-1 items-center">
                    <Label className="text-xs text-right">OS</Label>
                    {['esfera', 'cilindro', 'eje', 'adicion'].map(field => (
                      <Input
                        key={field}
                        value={formData.examen.refraccion_os[field]}
                        onChange={(e) => updateNestedField(`examen.refraccion_os.${field}`, e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                    ))}
                  </div>
                </div>
                
                {/* PIO */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Presión Intraocular</Label>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs">OD (mmHg)</Label>
                      <Input
                        value={formData.examen.pio_od}
                        onChange={(e) => updateNestedField('examen.pio_od', e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-sm h-8"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">OS (mmHg)</Label>
                      <Input
                        value={formData.examen.pio_os}
                        onChange={(e) => updateNestedField('examen.pio_os', e.target.value)}
                        disabled={isReadOnly}
                        className="input-teal text-sm h-8"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Método</Label>
                      <Input
                        value={formData.examen.pio_metodo}
                        onChange={(e) => updateNestedField('examen.pio_metodo', e.target.value)}
                        disabled={isReadOnly}
                        placeholder="Goldmann..."
                        className="input-teal text-sm h-8"
                      />
                    </div>
                  </div>
                </div>
                
                {/* Segmento Anterior - Simplificado a un solo textarea */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Segmento Anterior</Label>
                  <Textarea
                    value={formData.examen.segmento_anterior}
                    onChange={(e) => updateNestedField('examen.segmento_anterior', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Párpados, conjuntiva, córnea, cámara anterior, iris, cristalino..."
                    className="input-teal min-h-[100px] text-sm"
                  />
                </div>
                
                {/* Segmento Posterior - Simplificado a un solo textarea */}
                <div className="space-y-2">
                  <Label className="text-xs font-semibold text-blue-700">Segmento Posterior</Label>
                  <Textarea
                    value={formData.examen.segmento_posterior}
                    onChange={(e) => updateNestedField('examen.segmento_posterior', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Vítreo, papila, mácula, retina, vasos..."
                    className="input-teal min-h-[100px] text-sm"
                  />
                </div>
                
                {/* Motilidad Ocular */}
                <div className="space-y-2">
                  <div>
                    <Label className="text-xs">Motilidad Ocular</Label>
                    <Textarea
                      value={formData.examen.motilidad_ocular}
                      onChange={(e) => updateNestedField('examen.motilidad_ocular', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal min-h-[40px] text-sm"
                    />
                  </div>
                </div>
              </div>
            </CollapsibleSection>
          </div>

          {/* COLUMNA DERECHA: Diagnóstico, Recomendaciones y Recetas */}
          <div className="space-y-4">
            {/* Diagnósticos y Plan (movido de columna central) */}
            <CollapsibleSection title="Diagnóstico y Plan" icon={Activity} badge={`${formData.diagnosticos.length}`}>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-semibold">Diagnósticos</Label>
                    {!isReadOnly && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addArrayItem('diagnosticos', { descripcion: '', codigo_cie10: '', ojo: 'OU' })}
                        className="h-6 text-xs text-blue-600 hover:text-blue-700"
                      >
                        <Plus className="w-3 h-3 mr-1" /> Agregar
                      </Button>
                    )}
                  </div>
                  {formData.diagnosticos.map((diag, idx) => (
                    <div key={idx} className="flex gap-2 mb-2 items-start">
                      <div className="flex-1 grid grid-cols-3 gap-1">
                        <div className="col-span-2">
                          <Autocomplete
                            value={diag.descripcion}
                            onChange={(v) => updateArrayItem('diagnosticos', idx, 'descripcion', v)}
                            placeholder="Diagnóstico"
                            fetchUrl="/catalogos/diagnosticos"
                            disabled={isReadOnly}
                            className="input-teal text-xs h-8"
                          />
                        </div>
                        <Select
                          value={diag.ojo}
                          onValueChange={(v) => updateArrayItem('diagnosticos', idx, 'ojo', v)}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="OD">OD</SelectItem>
                            <SelectItem value="OS">OS</SelectItem>
                            <SelectItem value="OU">OU</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      {!isReadOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeArrayItem('diagnosticos', idx)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                
                {/* Estudios a Realizar (movido aquí desde Recomendaciones) */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs font-semibold">Estudios a Realizar</Label>
                    {!isReadOnly && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => addArrayItem('recomendaciones.estudios_a_realizar', { estudio: '', ojo: 'OU', indicaciones: '' })}
                        className="h-6 text-xs text-blue-600 hover:text-blue-700"
                      >
                        <Plus className="w-3 h-3 mr-1" /> Agregar
                      </Button>
                    )}
                  </div>
                  {formData.recomendaciones.estudios_a_realizar.map((est, idx) => (
                    <div key={idx} className="flex gap-2 mb-2 items-start">
                      <div className="flex-1 grid grid-cols-3 gap-1">
                        <div className="col-span-2">
                          <Autocomplete
                            value={est.estudio}
                            onChange={(v) => {
                              const estudios = [...formData.recomendaciones.estudios_a_realizar];
                              estudios[idx] = { ...estudios[idx], estudio: v };
                              updateNestedField('recomendaciones.estudios_a_realizar', estudios);
                            }}
                            placeholder="Estudio"
                            fetchUrl="/catalogos/estudios"
                            disabled={isReadOnly}
                            className="input-teal text-xs h-8"
                          />
                        </div>
                        <Select
                          value={est.ojo}
                          onValueChange={(v) => {
                            const estudios = [...formData.recomendaciones.estudios_a_realizar];
                            estudios[idx] = { ...estudios[idx], ojo: v };
                            updateNestedField('recomendaciones.estudios_a_realizar', estudios);
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="OD">OD</SelectItem>
                            <SelectItem value="OS">OS</SelectItem>
                            <SelectItem value="OU">OU</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      {!isReadOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeArrayItem('recomendaciones.estudios_a_realizar', idx)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                <div>
                  <Label className="text-xs font-semibold">Plan</Label>
                  <Textarea
                    value={formData.plan}
                    onChange={(e) => updateNestedField('plan', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Conducta a seguir, indicaciones..."
                    className="input-teal min-h-[80px] text-sm"
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold">Lectura de Exámenes</Label>
                  <Textarea
                    value={formData.lectura_examenes}
                    onChange={(e) => updateNestedField('lectura_examenes', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Interpretación de estudios auxiliares, laboratorios, imágenes..."
                    className="input-teal min-h-[80px] text-sm"
                  />
                </div>
              </div>
            </CollapsibleSection>

            {/* Candidato a Cirugía - Sección integrada */}
            <CollapsibleSection 
              title="Candidato a Cirugía" 
              icon={Stethoscope}
              defaultOpen={false}
            >
              <div className="space-y-4">
                {crmEnviado ? (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-purple-700 mb-2">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Paciente agregado al CRM de Cirugías</span>
                    </div>
                    <div className="text-sm text-purple-600">
                      <p>Tipo: <strong>{crmForm.tipo_cirugia}</strong></p>
                      <p>Ojo: {crmForm.ojo} | Interés: {crmForm.nivel_interes}</p>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2 text-xs"
                      onClick={() => {
                        setCrmEnviado(false);
                        setCrmForm({
                          tipo_cirugia: '',
                          ojo: 'OU',
                          diagnostico: '',
                          prioridad: 'normal',
                          nivel_interes: 'interesado',
                          notas: ''
                        });
                      }}
                    >
                      Agregar otro tipo de cirugía
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="bg-purple-50/50 border border-purple-100 rounded-lg p-3 text-xs text-purple-700">
                      <p>Complete los datos para agregar este paciente al CRM de Cirugías. El diagnóstico se auto-completa con los diagnósticos de esta evaluación.</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Tipo de Cirugía *</Label>
                        <Select
                          value={crmForm.tipo_cirugia || undefined}
                          onValueChange={(v) => setCrmForm(prev => ({ ...prev, tipo_cirugia: v }))}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue placeholder="Seleccionar..." />
                          </SelectTrigger>
                          <SelectContent>
                            {tiposCirugia.map(tipo => (
                              <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-1">
                        <Label className="text-xs">Ojo</Label>
                        <Select
                          value={crmForm.ojo}
                          onValueChange={(v) => setCrmForm(prev => ({ ...prev, ojo: v }))}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="OD">OD (Derecho)</SelectItem>
                            <SelectItem value="OS">OS (Izquierdo)</SelectItem>
                            <SelectItem value="OU">OU (Ambos)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Nivel de Interés *</Label>
                        <Select
                          value={crmForm.nivel_interes}
                          onValueChange={(v) => setCrmForm(prev => ({ ...prev, nivel_interes: v }))}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="muy_interesado">Muy Interesado</SelectItem>
                            <SelectItem value="interesado">Interesado</SelectItem>
                            <SelectItem value="indeciso">Indeciso</SelectItem>
                            <SelectItem value="poco_interesado">Poco Interesado</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-1">
                        <Label className="text-xs">Prioridad</Label>
                        <Select
                          value={crmForm.prioridad}
                          onValueChange={(v) => setCrmForm(prev => ({ ...prev, prioridad: v }))}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="alta">Alta</SelectItem>
                            <SelectItem value="normal">Normal</SelectItem>
                            <SelectItem value="baja">Baja</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    <div className="space-y-1">
                      <Label className="text-xs">Notas adicionales</Label>
                      <Textarea
                        value={crmForm.notas}
                        onChange={(e) => setCrmForm(prev => ({ ...prev, notas: e.target.value }))}
                        disabled={isReadOnly}
                        placeholder="Observaciones relevantes para el seguimiento..."
                        className="input-teal min-h-[50px] text-xs"
                      />
                    </div>
                    
                    <Button
                      onClick={handleEnviarCRM}
                      disabled={!formData.paciente_id || !crmForm.tipo_cirugia || isReadOnly}
                      className="w-full btn-primary bg-purple-600 hover:bg-purple-700"
                    >
                      <Stethoscope className="w-4 h-4 mr-2" />
                      Agregar al CRM de Cirugías
                    </Button>
                    
                    {!formData.paciente_id && (
                      <p className="text-xs text-amber-600 text-center">
                        Seleccione un paciente primero
                      </p>
                    )}
                  </>
                )}
              </div>
            </CollapsibleSection>

            {/* Recomendaciones Generales */}
            <CollapsibleSection title="Recomendaciones" icon={FileText}>
              <div>
                <Label className="text-xs">Recomendaciones Generales</Label>
                <Textarea
                  value={formData.recomendaciones.recomendaciones_generales}
                  onChange={(e) => updateNestedField('recomendaciones.recomendaciones_generales', e.target.value)}
                  disabled={isReadOnly}
                  placeholder="Indicaciones generales para el paciente..."
                  className="input-teal min-h-[60px] text-sm"
                />
              </div>
            </CollapsibleSection>

            {/* Próxima Cita */}
            <CollapsibleSection title="Próxima Cita" icon={Calendar}>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="agendar_cita"
                    checked={formData.proxima_cita?.agendar || false}
                    onCheckedChange={(checked) => updateNestedField('proxima_cita.agendar', checked)}
                    disabled={isReadOnly}
                  />
                  <Label htmlFor="agendar_cita" className="text-sm cursor-pointer">
                    Agendar próxima cita para este paciente
                  </Label>
                </div>
                
                {formData.proxima_cita?.agendar && (
                  <div className="pl-6 space-y-3 border-l-2 border-blue-200">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Médico</Label>
                        <Select
                          value={formData.proxima_cita?.medico_id || ''}
                          onValueChange={(value) => {
                            const med = medicos.find(m => m.id === value);
                            updateNestedField('proxima_cita.medico_id', value);
                            updateNestedField('proxima_cita.medico_nombre', med?.name || '');
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue placeholder="Seleccionar médico" />
                          </SelectTrigger>
                          <SelectContent>
                            {medicos.map((m) => (
                              <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Tipo de cita</Label>
                        <Select
                          value={formData.proxima_cita?.tipo_cita || 'Subsecuente'}
                          onValueChange={(value) => updateNestedField('proxima_cita.tipo_cita', value)}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="input-teal h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Subsecuente">Subsecuente</SelectItem>
                            <SelectItem value="Control post-operatorio">Control post-operatorio</SelectItem>
                            <SelectItem value="Estudio">Estudio</SelectItem>
                            <SelectItem value="Otro">Otro</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Fecha</Label>
                        <Input
                          type="date"
                          value={formData.proxima_cita?.fecha || ''}
                          onChange={(e) => updateNestedField('proxima_cita.fecha', e.target.value)}
                          disabled={isReadOnly}
                          className="input-teal h-8 text-xs"
                          min={getGuatemalaDate()}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Hora</Label>
                        <Input
                          type="time"
                          value={formData.proxima_cita?.hora || ''}
                          onChange={(e) => updateNestedField('proxima_cita.hora', e.target.value)}
                          disabled={isReadOnly}
                          className="input-teal h-8 text-xs"
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Notas</Label>
                      <Input
                        value={formData.proxima_cita?.notas || ''}
                        onChange={(e) => updateNestedField('proxima_cita.notas', e.target.value)}
                        disabled={isReadOnly}
                        placeholder="Indicaciones para la próxima cita..."
                        className="input-teal h-8 text-xs"
                      />
                    </div>
                  </div>
                )}
              </div>
            </CollapsibleSection>

            {/* Receta de Medicamentos */}
            <CollapsibleSection 
              title="Receta de Medicamentos" 
              icon={Pill}
              badge={`${formData.recetas.medicamentos.items.length}`}
              onPrint={() => handlePrint('medicamentos')}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold">Medicamentos</Label>
                  {!isReadOnly && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const items = [...formData.recetas.medicamentos.items, {
                          medicamento: '', presentacion: '', dosis: '', frecuencia: '', duracion: '', via: '', indicaciones: ''
                        }];
                        updateNestedField('recetas.medicamentos.items', items);
                      }}
                      className="h-6 text-xs text-blue-600 hover:text-blue-700"
                    >
                      <Plus className="w-3 h-3 mr-1" /> Agregar
                    </Button>
                  )}
                </div>
                {formData.recetas.medicamentos.items.map((item, idx) => (
                  <div key={idx} className="p-2 border rounded-lg bg-gray-50 space-y-1">
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <Autocomplete
                          value={item.medicamento}
                          onChange={(v) => {
                            const items = [...formData.recetas.medicamentos.items];
                            items[idx] = { ...items[idx], medicamento: v };
                            updateNestedField('recetas.medicamentos.items', items);
                          }}
                          placeholder="Medicamento"
                          fetchUrl="/catalogos/medicamentos"
                          disabled={isReadOnly}
                          className="input-teal text-xs h-8"
                        />
                      </div>
                      {!isReadOnly && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const items = formData.recetas.medicamentos.items.filter((_, i) => i !== idx);
                            updateNestedField('recetas.medicamentos.items', items);
                          }}
                          className="h-8 w-8 p-0 text-red-500"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                    <Input
                      value={item.dosis}
                      onChange={(e) => {
                        const items = [...formData.recetas.medicamentos.items];
                        items[idx] = { ...items[idx], dosis: e.target.value };
                        updateNestedField('recetas.medicamentos.items', items);
                      }}
                      placeholder="Dosis, frecuencia y duración (ej. 1 gota cada 8 horas por 7 días)"
                      disabled={isReadOnly}
                      className="text-xs h-7 input-teal"
                    />
                  </div>
                ))}
              </div>
            </CollapsibleSection>

            {/* Recetas de Anteojos - Lista Múltiple */}
            <CollapsibleSection 
              title="Recetas de Anteojos" 
              icon={Glasses} 
              defaultOpen={false} 
              badge={`${formData.recetas.anteojos_lista?.length || 0}`}
            >
              <div className="space-y-3">
                {/* Botón agregar nueva receta */}
                {!isReadOnly && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const nuevaReceta = nuevaRecetaAnteojos();
                      updateNestedField('recetas.anteojos_lista', [...(formData.recetas.anteojos_lista || []), nuevaReceta]);
                    }}
                    className="w-full border-dashed border-teal-400 text-teal-600 hover:bg-teal-50"
                  >
                    <Plus className="w-4 h-4 mr-1" /> Agregar Receta de Anteojos
                  </Button>
                )}
                
                {/* Lista de recetas */}
                {(formData.recetas.anteojos_lista || []).map((receta, idx) => (
                  <Card key={receta.id || idx} className="border border-teal-200">
                    <CardHeader className="py-2 px-3 bg-teal-50 flex flex-row items-center justify-between">
                      <CardTitle className="text-xs font-medium flex items-center gap-2">
                        <Glasses className="w-4 h-4 text-teal-600" />
                        Receta #{idx + 1}
                        {receta.fecha_creacion && (
                          <span className="text-gray-400 font-normal">
                            ({new Date(receta.fecha_creacion).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' })})
                          </span>
                        )}
                      </CardTitle>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setPrintRecetaIndex(idx);
                            handlePrint('anteojos');
                          }}
                          className="h-6 px-2 text-blue-600 hover:bg-blue-50"
                          title="Imprimir receta"
                        >
                          <Printer className="w-3 h-3" />
                        </Button>
                        {!isReadOnly && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const lista = formData.recetas.anteojos_lista.filter((_, i) => i !== idx);
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            className="h-6 px-2 text-red-600 hover:bg-red-50"
                            title="Eliminar receta"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="p-3 space-y-2">
                      <div className="grid grid-cols-5 gap-1 text-center text-xs">
                        <div></div>
                        <div className="text-gray-500">Esfera</div>
                        <div className="text-gray-500">Cilindro</div>
                        <div className="text-gray-500">Eje</div>
                        <div className="text-gray-500">ADD</div>
                      </div>
                      <div className="grid grid-cols-5 gap-1 items-center">
                        <Label className="text-xs text-right">OD</Label>
                        {['esfera', 'cilindro', 'eje', 'adicion'].map(field => (
                          <Input
                            key={field}
                            value={receta.od?.[field] || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], od: { ...lista[idx].od, [field]: e.target.value }};
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                          />
                        ))}
                      </div>
                      <div className="grid grid-cols-5 gap-1 items-center">
                        <Label className="text-xs text-right">OS</Label>
                        {['esfera', 'cilindro', 'eje', 'adicion'].map(field => (
                          <Input
                            key={field}
                            value={receta.os?.[field] || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], os: { ...lista[idx].os, [field]: e.target.value }};
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                          />
                        ))}
                      </div>
                      <div className="grid grid-cols-4 gap-2 pt-2">
                        <div>
                          <Label className="text-xs">DP</Label>
                          <Input
                            value={receta.distancia_pupilar || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], distancia_pupilar: e.target.value };
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                            placeholder="mm"
                            className="input-teal text-xs h-7"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Tipo Lente</Label>
                          <Select
                            value={receta.tipo_lente || ''}
                            onValueChange={(v) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], tipo_lente: v };
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                          >
                            <SelectTrigger className="input-teal h-7 text-xs">
                              <SelectValue placeholder="Tipo" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Monofocal">Monofocal</SelectItem>
                              <SelectItem value="Bifocal">Bifocal</SelectItem>
                              <SelectItem value="Progresivo">Progresivo</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Material</Label>
                          <Input
                            value={receta.material || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], material: e.target.value };
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Uso</Label>
                          <Select
                            value={receta.uso || ''}
                            onValueChange={(v) => {
                              const lista = [...formData.recetas.anteojos_lista];
                              lista[idx] = { ...lista[idx], uso: v };
                              updateNestedField('recetas.anteojos_lista', lista);
                            }}
                            disabled={isReadOnly}
                          >
                            <SelectTrigger className="input-teal h-7 text-xs">
                              <SelectValue placeholder="Uso" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Permanente">Permanente</SelectItem>
                              <SelectItem value="Lectura">Lectura</SelectItem>
                              <SelectItem value="Distancia">Distancia</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs">Tratamientos</Label>
                        <Input
                          value={receta.tratamientos || ''}
                          onChange={(e) => {
                            const lista = [...formData.recetas.anteojos_lista];
                            lista[idx] = { ...lista[idx], tratamientos: e.target.value };
                            updateNestedField('recetas.anteojos_lista', lista);
                          }}
                          disabled={isReadOnly}
                          placeholder="Antirreflejo, filtro azul, fotocromático..."
                          className="input-teal text-xs h-7"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Observaciones</Label>
                        <Input
                          value={receta.observaciones || ''}
                          onChange={(e) => {
                            const lista = [...formData.recetas.anteojos_lista];
                            lista[idx] = { ...lista[idx], observaciones: e.target.value };
                            updateNestedField('recetas.anteojos_lista', lista);
                          }}
                          disabled={isReadOnly}
                          className="input-teal text-xs h-7"
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {(formData.recetas.anteojos_lista || []).length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-4">No hay recetas de anteojos</p>
                )}
              </div>
            </CollapsibleSection>

            {/* Recetas de Lentes de Contacto - Lista Múltiple */}
            <CollapsibleSection 
              title="Recetas de Lentes de Contacto" 
              icon={Contact} 
              defaultOpen={false}
              badge={`${formData.recetas.lentes_contacto_lista?.length || 0}`}
            >
              <div className="space-y-3">
                {/* Botón agregar nueva receta */}
                {!isReadOnly && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const nuevaReceta = nuevaRecetaLentesContacto();
                      updateNestedField('recetas.lentes_contacto_lista', [...(formData.recetas.lentes_contacto_lista || []), nuevaReceta]);
                    }}
                    className="w-full border-dashed border-teal-400 text-teal-600 hover:bg-teal-50"
                  >
                    <Plus className="w-4 h-4 mr-1" /> Agregar Receta de Lentes de Contacto
                  </Button>
                )}
                
                {/* Lista de recetas */}
                {(formData.recetas.lentes_contacto_lista || []).map((receta, idx) => (
                  <Card key={receta.id || idx} className="border border-teal-200">
                    <CardHeader className="py-2 px-3 bg-teal-50 flex flex-row items-center justify-between">
                      <CardTitle className="text-xs font-medium flex items-center gap-2">
                        <Contact className="w-4 h-4 text-teal-600" />
                        Receta #{idx + 1}
                        {receta.fecha_creacion && (
                          <span className="text-gray-400 font-normal">
                            ({new Date(receta.fecha_creacion).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' })})
                          </span>
                        )}
                      </CardTitle>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setPrintRecetaIndex(idx);
                            handlePrint('lentes_contacto');
                          }}
                          className="h-6 px-2 text-blue-600 hover:bg-blue-50"
                          title="Imprimir receta"
                        >
                          <Printer className="w-3 h-3" />
                        </Button>
                        {!isReadOnly && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const lista = formData.recetas.lentes_contacto_lista.filter((_, i) => i !== idx);
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            className="h-6 px-2 text-red-600 hover:bg-red-50"
                            title="Eliminar receta"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="p-3 space-y-2">
                      <div className="grid grid-cols-5 gap-1 text-center text-xs">
                        <div></div>
                        <div className="text-gray-500">Poder</div>
                        <div className="text-gray-500">CB</div>
                        <div className="text-gray-500">DIA</div>
                        <div className="text-gray-500">ADD</div>
                      </div>
                      <div className="grid grid-cols-5 gap-1 items-center">
                        <Label className="text-xs text-right">OD</Label>
                        {['poder', 'curva_base', 'diametro', 'adicion'].map(field => (
                          <Input
                            key={field}
                            value={receta.od?.[field] || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.lentes_contacto_lista];
                              lista[idx] = { ...lista[idx], od: { ...lista[idx].od, [field]: e.target.value }};
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                            placeholder={field === 'adicion' ? '+0.00' : ''}
                          />
                        ))}
                      </div>
                      <div className="grid grid-cols-5 gap-1 items-center">
                        <Label className="text-xs text-right">OS</Label>
                        {['poder', 'curva_base', 'diametro', 'adicion'].map(field => (
                          <Input
                            key={field}
                            value={receta.os?.[field] || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.lentes_contacto_lista];
                              lista[idx] = { ...lista[idx], os: { ...lista[idx].os, [field]: e.target.value }};
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                            placeholder={field === 'adicion' ? '+0.00' : ''}
                          />
                        ))}
                      </div>
                      <div className="grid grid-cols-3 gap-2 pt-2">
                        <div>
                          <Label className="text-xs">Marca</Label>
                          <Input
                            value={receta.marca || ''}
                            onChange={(e) => {
                              const lista = [...formData.recetas.lentes_contacto_lista];
                              lista[idx] = { ...lista[idx], marca: e.target.value };
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            disabled={isReadOnly}
                            className="input-teal text-xs h-7"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Tipo</Label>
                          <Select
                            value={receta.tipo || ''}
                            onValueChange={(v) => {
                              const lista = [...formData.recetas.lentes_contacto_lista];
                              lista[idx] = { ...lista[idx], tipo: v };
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            disabled={isReadOnly}
                          >
                            <SelectTrigger className="input-teal h-7 text-xs">
                              <SelectValue placeholder="Tipo" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Blando">Blando</SelectItem>
                              <SelectItem value="Rígido">Rígido</SelectItem>
                              <SelectItem value="Tórico">Tórico</SelectItem>
                              <SelectItem value="Multifocal">Multifocal</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Reemplazo</Label>
                          <Select
                            value={receta.regimen_reemplazo || ''}
                            onValueChange={(v) => {
                              const lista = [...formData.recetas.lentes_contacto_lista];
                              lista[idx] = { ...lista[idx], regimen_reemplazo: v };
                              updateNestedField('recetas.lentes_contacto_lista', lista);
                            }}
                            disabled={isReadOnly}
                          >
                            <SelectTrigger className="input-teal h-7 text-xs">
                              <SelectValue placeholder="Reemplazo" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Diario">Diario</SelectItem>
                              <SelectItem value="Quincenal">Quincenal</SelectItem>
                              <SelectItem value="Mensual">Mensual</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs">Observaciones</Label>
                        <Input
                          value={receta.observaciones || ''}
                          onChange={(e) => {
                            const lista = [...formData.recetas.lentes_contacto_lista];
                            lista[idx] = { ...lista[idx], observaciones: e.target.value };
                            updateNestedField('recetas.lentes_contacto_lista', lista);
                          }}
                          disabled={isReadOnly}
                          className="input-teal text-xs h-7"
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {(formData.recetas.lentes_contacto_lista || []).length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-4">No hay recetas de lentes de contacto</p>
                )}
              </div>
            </CollapsibleSection>
          </div>
        </div>
      </div>

      {/* Área de Impresión - Optimizada para Media Carta HORIZONTAL */}
      {printDialogOpen && (
        <div className="print-area fixed inset-0 bg-white p-3" style={{ zIndex: 9999 }}>
          <div className="mx-auto" style={{ maxWidth: '8in' }}>
            {/* Encabezado Compacto - Horizontal */}
            <div className="print-header flex items-center justify-between mb-2 border-b-2 pb-2" style={{ borderColor: '#0F6E56' }}>
              <div className="flex items-center gap-3">
                <img 
                  src="https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png" 
                  alt="Logo" 
                  className="h-12"
                />
                <div>
                  <h1 className="print-title text-sm font-bold" style={{ color: '#0F6E56' }}>NovaVision</h1>
                  <p className="text-xs text-gray-500">Clínica Oftalmológica | Tel: (502) 2222-3333</p>
                </div>
              </div>
              <div className="text-right text-xs">
                <div><span className="font-semibold">Paciente:</span> {formData.paciente_nombre}</div>
                <div><span className="font-semibold">Exp:</span> {formData.paciente_expediente} | <span className="font-semibold">Edad:</span> {formData.paciente_edad} años</div>
                <div><span className="font-semibold">Fecha:</span> {formData.fecha}</div>
              </div>
            </div>
            
            {/* Contenido según tipo de receta */}
            {printType === 'medicamentos' && (
              <div>
                <h2 className="print-title text-sm font-bold mb-2 text-center uppercase tracking-wide" style={{ color: '#0F6E56' }}>
                  Receta Médica
                </h2>
                
                {/* Lista de medicamentos en GRID 2 columnas para horizontal */}
                <div className="print-med-grid grid grid-cols-2 gap-2">
                  {formData.recetas.medicamentos.items.map((item, idx) => (
                    <div key={idx} className="print-med-card border rounded p-2 bg-white text-xs">
                      <div className="flex items-start gap-1">
                        <span className="font-bold" style={{ color: '#0F6E56' }}>{idx + 1}.</span>
                        <div className="flex-1">
                          <div className="font-semibold text-sm">{item.medicamento}</div>
                          {item.presentacion && (
                            <div className="text-gray-600">{item.presentacion}</div>
                          )}
                          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0">
                            {item.dosis && <span><b>Dosis:</b> {item.dosis}</span>}
                            {item.frecuencia && <span><b>Frec:</b> {item.frecuencia}</span>}
                            {item.duracion && <span><b>Dur:</b> {item.duracion}</span>}
                            {item.via && <span><b>Vía:</b> {item.via}</span>}
                          </div>
                          {item.indicaciones && (
                            <div className="mt-1 italic text-gray-600 border-t pt-1 text-xs">
                              {item.indicaciones}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Indicaciones generales */}
                {formData.recetas.medicamentos.indicaciones_generales && (
                  <div className="mt-2 p-2 border rounded bg-yellow-50 text-xs">
                    <span className="font-semibold">Indicaciones:</span> {formData.recetas.medicamentos.indicaciones_generales}
                  </div>
                )}
              </div>
            )}
            
            {printType === 'anteojos' && (
              <div>
                <h2 className="print-title text-sm font-bold mb-2 text-center uppercase tracking-wide" style={{ color: '#0F6E56' }}>
                  Receta de Anteojos {formData.recetas.anteojos_lista?.length > 1 ? `(#${printRecetaIndex + 1})` : ''}
                </h2>
                {(() => {
                  // Obtener la receta del índice seleccionado, o la primera disponible
                  const receta = formData.recetas.anteojos_lista?.[printRecetaIndex] || formData.recetas.anteojos_lista?.[0] || formData.recetas.anteojos;
                  return (
                    <div className="flex gap-4">
                      {/* Tabla de graduación */}
                      <div className="flex-1">
                        <table className="print-table w-full text-xs border-collapse">
                          <thead>
                            <tr className="border-b-2" style={{ borderColor: '#0F6E56' }}>
                              <th className="text-left py-1 px-2 bg-gray-50">Ojo</th>
                              <th className="text-center py-1 px-2 bg-gray-50">Esfera</th>
                              <th className="text-center py-1 px-2 bg-gray-50">Cilindro</th>
                              <th className="text-center py-1 px-2 bg-gray-50">Eje</th>
                              <th className="text-center py-1 px-2 bg-gray-50">ADD</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b">
                              <td className="py-2 px-2 font-semibold" style={{ color: '#0F6E56' }}>OD</td>
                              <td className="text-center py-2">{receta?.od?.esfera || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.cilindro || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.eje || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.adicion || '-'}</td>
                            </tr>
                            <tr className="border-b">
                              <td className="py-2 px-2 font-semibold" style={{ color: '#0F6E56' }}>OS</td>
                              <td className="text-center py-2">{receta?.os?.esfera || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.cilindro || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.eje || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.adicion || '-'}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      {/* Datos adicionales */}
                      <div className="w-48 text-xs p-2 bg-gray-50 rounded">
                        <div className="space-y-1">
                          <div><span className="font-semibold">DP:</span> {receta?.distancia_pupilar || '-'}</div>
                          <div><span className="font-semibold">Tipo:</span> {receta?.tipo_lente || '-'}</div>
                          <div><span className="font-semibold">Material:</span> {receta?.material || '-'}</div>
                          <div><span className="font-semibold">Uso:</span> {receta?.uso || '-'}</div>
                          {receta?.tratamientos && (
                            <div className="pt-1 border-t"><span className="font-semibold">Tratamientos:</span> {receta.tratamientos}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
            
            {printType === 'lentes_contacto' && (
              <div>
                <h2 className="print-title text-sm font-bold mb-2 text-center uppercase tracking-wide" style={{ color: '#0F6E56' }}>
                  Receta de Lentes de Contacto {formData.recetas.lentes_contacto_lista?.length > 1 ? `(#${printRecetaIndex + 1})` : ''}
                </h2>
                {(() => {
                  // Obtener la receta del índice seleccionado, o la primera disponible
                  const receta = formData.recetas.lentes_contacto_lista?.[printRecetaIndex] || formData.recetas.lentes_contacto_lista?.[0] || formData.recetas.lentes_contacto;
                  return (
                    <div className="flex gap-4">
                      {/* Tabla de parámetros */}
                      <div className="flex-1">
                        <table className="print-table w-full text-xs border-collapse">
                          <thead>
                            <tr className="border-b-2" style={{ borderColor: '#0F6E56' }}>
                              <th className="text-left py-1 px-2 bg-gray-50">Ojo</th>
                              <th className="text-center py-1 px-2 bg-gray-50">Poder</th>
                              <th className="text-center py-1 px-2 bg-gray-50">CB</th>
                              <th className="text-center py-1 px-2 bg-gray-50">DIA</th>
                              <th className="text-center py-1 px-2 bg-gray-50">ADD</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b">
                              <td className="py-2 px-2 font-semibold" style={{ color: '#0F6E56' }}>OD</td>
                              <td className="text-center py-2">{receta?.od?.poder || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.curva_base || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.diametro || '-'}</td>
                              <td className="text-center py-2">{receta?.od?.adicion || '-'}</td>
                            </tr>
                            <tr className="border-b">
                              <td className="py-2 px-2 font-semibold" style={{ color: '#0F6E56' }}>OS</td>
                              <td className="text-center py-2">{receta?.os?.poder || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.curva_base || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.diametro || '-'}</td>
                              <td className="text-center py-2">{receta?.os?.adicion || '-'}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      {/* Datos adicionales */}
                      <div className="w-56 text-xs p-2 bg-gray-50 rounded">
                        <div className="space-y-1">
                          <div><span className="font-semibold">Marca:</span> {receta?.marca || '-'}</div>
                          <div><span className="font-semibold">Tipo:</span> {receta?.tipo || '-'}</div>
                          <div><span className="font-semibold">Reemplazo:</span> {receta?.regimen_reemplazo || '-'}</div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
            
            {/* Próxima Cita (si está agendada) - Formato destacado */}
            {formData.proxima_cita?.agendar && formData.proxima_cita?.fecha && (
              <div className="print-cita-box mt-3 p-2 border-2 border-blue-300 rounded bg-blue-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    <span className="font-bold text-sm text-blue-700">PRÓXIMA CITA</span>
                  </div>
                  <div className="text-xs flex gap-4">
                    <span><b>Fecha:</b> {new Date(formData.proxima_cita.fecha + 'T12:00:00').toLocaleDateString('es-GT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Guatemala' })}</span>
                    <span><b>Hora:</b> {formData.proxima_cita.hora}</span>
                    <span><b>Médico:</b> {formData.proxima_cita.medico_nombre}</span>
                    {formData.proxima_cita.tipo_cita && <span><b>Tipo:</b> {formData.proxima_cita.tipo_cita}</span>}
                  </div>
                </div>
              </div>
            )}
            
            {/* Pie de Receta */}
            <div className="mt-4 pt-3 border-t" style={{ borderColor: '#0F6E56' }}>
              <div className="text-xs text-gray-600 text-center">
                <p>Fecha de emisión: {new Date().toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' })}</p>
                <p className="text-gray-400 mt-1">NovaVision © {new Date().getFullYear()}</p>
              </div>
            </div>
            
            {/* Botón para cerrar (no se imprime) */}
            <div className="mt-4 text-center no-print">
              <Button onClick={() => setPrintDialogOpen(false)} className="btn-primary">
                Cerrar Vista Previa
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default EvaluacionOftalmologica;
