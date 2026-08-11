import React, { useState, useEffect, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Eye, Save, Plus, Trash2, RefreshCw, Search, Printer, 
  ChevronDown, ChevronUp, Lock, Clock, Calendar,
  User, FileText, Stethoscope, Pill, Activity, ClipboardList,
  Glasses, Contact
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
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
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import axios from 'axios';
import { agendaApi } from '../services/agendaApi';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  const [evaluacionActual, setEvaluacionActual] = useState(null);
  const [pacientes, setPacientes] = useState([]);
  const [medicos, setMedicos] = useState([]);
  const [searchPaciente, setSearchPaciente] = useState('');
  const [showPacienteList, setShowPacienteList] = useState(false);
  const [autoguardadoStatus, setAutoguardadoStatus] = useState('');
  const [tiempoRestante, setTiempoRestante] = useState(null);
  const [printDialogOpen, setPrintDialogOpen] = useState(false);
  const [printType, setPrintType] = useState('');
  
  const autoguardadoRef = useRef(null);
  const lastSavedRef = useRef(null);
  
  const canEdit = user?.role === 'superadmin' || user?.role === 'admin';
  const isReadOnly = !canEdit || evaluacionActual?.sellado;

  // Estado inicial de evaluación
  const evaluacionVacia = {
    paciente_id: '',
    paciente_nombre: '',
    paciente_edad: 0,
    paciente_sexo: '',
    paciente_expediente: '',
    fecha: new Date().toISOString().split('T')[0],
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
        od: { poder: '', curva_base: '', diametro: '' },
        os: { poder: '', curva_base: '', diametro: '' },
        marca: '',
        tipo: '',
        regimen_reemplazo: '',
        observaciones: ''
      }
    }
  };

  const [formData, setFormData] = useState(evaluacionVacia);

  // Fetch inicial
  const fetchEvaluaciones = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/evaluaciones?limit=50`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEvaluaciones(response.data.data || []);
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
      setLoading(false);
    };
    init();
  }, [fetchEvaluaciones, fetchMedicos]);

  useEffect(() => {
    const timer = setTimeout(() => {
      buscarPacientes(searchPaciente);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchPaciente, buscarPacientes]);

  // Calcular tiempo restante para sellado
  useEffect(() => {
    if (!evaluacionActual || evaluacionActual.sellado) {
      setTiempoRestante(null);
      return;
    }
    
    const calcularTiempo = () => {
      const creacion = new Date(evaluacionActual.fecha_creacion);
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

  // Autoguardado
  useEffect(() => {
    if (!evaluacionActual?.id || isReadOnly) return;
    
    if (autoguardadoRef.current) {
      clearTimeout(autoguardadoRef.current);
    }
    
    setAutoguardadoStatus('Cambios sin guardar');
    
    autoguardadoRef.current = setTimeout(async () => {
      try {
        setAutoguardadoStatus('Guardando...');
        const token = localStorage.getItem('token');
        await axios.patch(
          `${API_URL}/evaluaciones/${evaluacionActual.id}/autoguardar`,
          formData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit' });
        setAutoguardadoStatus(`Guardado a las ${now}`);
        lastSavedRef.current = new Date();
      } catch (error) {
        if (error.response?.status === 423) {
          toast.error('Expediente sellado. No se puede editar.');
          setEvaluacionActual(prev => ({ ...prev, sellado: true }));
        } else {
          setAutoguardadoStatus('Error al guardar');
          console.error('Error autoguardando:', error);
        }
      }
    }, 2500);
    
    return () => {
      if (autoguardadoRef.current) {
        clearTimeout(autoguardadoRef.current);
      }
    };
  }, [formData, evaluacionActual?.id, isReadOnly]);

  // Cargar evaluación
  const cargarEvaluacion = async (evaluacion) => {
    setEvaluacionActual(evaluacion);
    
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
    
    // Migrar recetas (oi → os)
    const recetasData = evaluacion.recetas || {};
    const migratedRecetas = {
      medicamentos: { items: recetasData.medicamentos?.items || [] },
      anteojos: {
        ...evaluacionVacia.recetas.anteojos,
        ...recetasData.anteojos,
        od: { ...evaluacionVacia.recetas.anteojos.od, ...recetasData.anteojos?.od },
        os: { ...evaluacionVacia.recetas.anteojos.os, ...(recetasData.anteojos?.os || recetasData.anteojos?.oi) }
      },
      lentes_contacto: {
        ...evaluacionVacia.recetas.lentes_contacto,
        ...recetasData.lentes_contacto,
        od: { ...evaluacionVacia.recetas.lentes_contacto.od, ...recetasData.lentes_contacto?.od },
        os: { ...evaluacionVacia.recetas.lentes_contacto.os, ...(recetasData.lentes_contacto?.os || recetasData.lentes_contacto?.oi) }
      }
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

  // Nueva evaluación
  const nuevaEvaluacion = () => {
    setEvaluacionActual(null);
    setFormData(evaluacionVacia);
    setSearchPaciente('');
    setAutoguardadoStatus('');
    setTiempoRestante(null);
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
      
      const now = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit' });
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

  // Seleccionar paciente
  const seleccionarPaciente = (paciente) => {
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
  };

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
      
      {/* Print Styles */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .print-area, .print-area * { visibility: visible; }
          .print-area { position: absolute; left: 0; top: 0; width: 100%; }
          .no-print { display: none !important; }
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
              {/* Estado de guardado */}
              {autoguardadoStatus && (
                <Badge className={`text-xs ${
                  autoguardadoStatus.includes('Guardado') ? 'bg-green-100 text-green-700' :
                  autoguardadoStatus.includes('Guardando') ? 'bg-blue-100 text-blue-700' :
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
                  <Button variant="outline" size="sm" className="btn-outline">
                    <FileText className="w-4 h-4 mr-1" />
                    Historial
                    <ChevronDown className="w-3 h-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-80 max-h-96 overflow-y-auto">
                  {evaluaciones.length === 0 ? (
                    <div className="px-3 py-4 text-center text-gray-500 text-sm">
                      No hay evaluaciones registradas
                    </div>
                  ) : (
                    evaluaciones.map((ev) => (
                      <DropdownMenuItem 
                        key={ev.id}
                        onClick={() => cargarEvaluacion(ev)}
                        className={`flex flex-col items-start py-2 cursor-pointer ${
                          evaluacionActual?.id === ev.id ? 'bg-blue-50' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="font-medium text-sm truncate max-w-[200px]">
                            {ev.paciente_nombre}
                          </span>
                          {ev.sellado && (
                            <Lock className="w-3 h-3 text-red-500 ml-2" />
                          )}
                        </div>
                        <span className="text-xs text-gray-500">
                          {ev.fecha} | {ev.paciente_expediente}
                        </span>
                      </DropdownMenuItem>
                    ))
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
                          min={new Date().toISOString().split('T')[0]}
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
                    <div className="grid grid-cols-3 gap-1">
                      <Input
                        value={item.dosis}
                        onChange={(e) => {
                          const items = [...formData.recetas.medicamentos.items];
                          items[idx] = { ...items[idx], dosis: e.target.value };
                          updateNestedField('recetas.medicamentos.items', items);
                        }}
                        placeholder="Dosis"
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                      <Input
                        value={item.frecuencia}
                        onChange={(e) => {
                          const items = [...formData.recetas.medicamentos.items];
                          items[idx] = { ...items[idx], frecuencia: e.target.value };
                          updateNestedField('recetas.medicamentos.items', items);
                        }}
                        placeholder="Frecuencia"
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                      <Input
                        value={item.duracion}
                        onChange={(e) => {
                          const items = [...formData.recetas.medicamentos.items];
                          items[idx] = { ...items[idx], duracion: e.target.value };
                          updateNestedField('recetas.medicamentos.items', items);
                        }}
                        placeholder="Duración"
                        disabled={isReadOnly}
                        className="input-teal text-xs h-7"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>

            {/* Receta de Anteojos */}
            <CollapsibleSection title="Receta de Anteojos" icon={Glasses} defaultOpen={false} onPrint={() => handlePrint('anteojos')}>
              <div className="space-y-3">
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
                      value={formData.recetas.anteojos.od[field]}
                      onChange={(e) => updateNestedField(`recetas.anteojos.od.${field}`, e.target.value)}
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
                      value={formData.recetas.anteojos.os[field]}
                      onChange={(e) => updateNestedField(`recetas.anteojos.os.${field}`, e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal text-xs h-7"
                    />
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Distancia Pupilar</Label>
                    <Input
                      value={formData.recetas.anteojos.distancia_pupilar}
                      onChange={(e) => updateNestedField('recetas.anteojos.distancia_pupilar', e.target.value)}
                      disabled={isReadOnly}
                      placeholder="mm"
                      className="input-teal text-xs h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Tipo de Lente</Label>
                    <Select
                      value={formData.recetas.anteojos.tipo_lente}
                      onValueChange={(v) => updateNestedField('recetas.anteojos.tipo_lente', v)}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="input-teal h-8 text-xs">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Monofocal">Monofocal</SelectItem>
                        <SelectItem value="Bifocal">Bifocal</SelectItem>
                        <SelectItem value="Progresivo">Progresivo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Material</Label>
                    <Input
                      value={formData.recetas.anteojos.material}
                      onChange={(e) => updateNestedField('recetas.anteojos.material', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal text-xs h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Uso</Label>
                    <Select
                      value={formData.recetas.anteojos.uso}
                      onValueChange={(v) => updateNestedField('recetas.anteojos.uso', v)}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="input-teal h-8 text-xs">
                        <SelectValue placeholder="Seleccionar" />
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
                    value={formData.recetas.anteojos.tratamientos}
                    onChange={(e) => updateNestedField('recetas.anteojos.tratamientos', e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Antirreflejo, filtro azul..."
                    className="input-teal text-xs h-8"
                  />
                </div>
                <div>
                  <Label className="text-xs">Observaciones</Label>
                  <Textarea
                    value={formData.recetas.anteojos.observaciones}
                    onChange={(e) => updateNestedField('recetas.anteojos.observaciones', e.target.value)}
                    disabled={isReadOnly}
                    className="input-teal min-h-[40px] text-xs"
                  />
                </div>
              </div>
            </CollapsibleSection>

            {/* Receta de Lentes de Contacto */}
            <CollapsibleSection title="Receta de Lentes de Contacto" icon={Contact} defaultOpen={false} onPrint={() => handlePrint('lentes_contacto')}>
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-1 text-center text-xs">
                  <div></div>
                  <div className="text-gray-500">Poder</div>
                  <div className="text-gray-500">Curva Base</div>
                  <div className="text-gray-500">Diámetro</div>
                </div>
                <div className="grid grid-cols-4 gap-1 items-center">
                  <Label className="text-xs text-right">OD</Label>
                  {['poder', 'curva_base', 'diametro'].map(field => (
                    <Input
                      key={field}
                      value={formData.recetas.lentes_contacto.od[field]}
                      onChange={(e) => updateNestedField(`recetas.lentes_contacto.od.${field}`, e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal text-xs h-7"
                    />
                  ))}
                </div>
                <div className="grid grid-cols-4 gap-1 items-center">
                  <Label className="text-xs text-right">OS</Label>
                  {['poder', 'curva_base', 'diametro'].map(field => (
                    <Input
                      key={field}
                      value={formData.recetas.lentes_contacto.os[field]}
                      onChange={(e) => updateNestedField(`recetas.lentes_contacto.os.${field}`, e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal text-xs h-7"
                    />
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Marca</Label>
                    <Input
                      value={formData.recetas.lentes_contacto.marca}
                      onChange={(e) => updateNestedField('recetas.lentes_contacto.marca', e.target.value)}
                      disabled={isReadOnly}
                      className="input-teal text-xs h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Tipo</Label>
                    <Select
                      value={formData.recetas.lentes_contacto.tipo}
                      onValueChange={(v) => updateNestedField('recetas.lentes_contacto.tipo', v)}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="input-teal h-8 text-xs">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Blando">Blando</SelectItem>
                        <SelectItem value="Rígido">Rígido</SelectItem>
                        <SelectItem value="Tórico">Tórico</SelectItem>
                        <SelectItem value="Multifocal">Multifocal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Régimen de Reemplazo</Label>
                  <Select
                    value={formData.recetas.lentes_contacto.regimen_reemplazo}
                    onValueChange={(v) => updateNestedField('recetas.lentes_contacto.regimen_reemplazo', v)}
                    disabled={isReadOnly}
                  >
                    <SelectTrigger className="input-teal h-8 text-xs">
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Diario">Diario</SelectItem>
                      <SelectItem value="Quincenal">Quincenal</SelectItem>
                      <SelectItem value="Mensual">Mensual</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Observaciones</Label>
                  <Textarea
                    value={formData.recetas.lentes_contacto.observaciones}
                    onChange={(e) => updateNestedField('recetas.lentes_contacto.observaciones', e.target.value)}
                    disabled={isReadOnly}
                    className="input-teal min-h-[40px] text-xs"
                  />
                </div>
              </div>
            </CollapsibleSection>
          </div>
        </div>
      </div>

      {/* Área de Impresión (oculta normalmente) */}
      {printDialogOpen && (
        <div className="print-area fixed inset-0 bg-white p-8" style={{ zIndex: 9999 }}>
          <div className="max-w-2xl mx-auto">
            {/* Encabezado de Receta */}
            <div className="flex items-center justify-between mb-6 border-b pb-4">
              <img 
                src="https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png" 
                alt="Logo" 
                className="h-16"
              />
              <div className="text-right">
                <h1 className="text-xl font-bold text-blue-700">NovaVision</h1>
                <p className="text-sm text-gray-600">Clínica Oftalmológica</p>
                <p className="text-xs text-gray-500">Tel: (502) 2222-3333</p>
              </div>
            </div>
            
            {/* Datos del Paciente */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><strong>Paciente:</strong> {formData.paciente_nombre}</div>
                <div><strong>Expediente:</strong> {formData.paciente_expediente}</div>
                <div><strong>Edad:</strong> {formData.paciente_edad} años</div>
                <div><strong>Fecha:</strong> {formData.fecha}</div>
              </div>
            </div>
            
            {/* Contenido según tipo de receta */}
            {printType === 'medicamentos' && (
              <div>
                <h2 className="text-lg font-bold mb-4 text-center">RECETA MÉDICA</h2>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Medicamento</th>
                      <th className="text-left py-2">Dosis</th>
                      <th className="text-left py-2">Frecuencia</th>
                      <th className="text-left py-2">Duración</th>
                    </tr>
                  </thead>
                  <tbody>
                    {formData.recetas.medicamentos.items.map((item, idx) => (
                      <tr key={idx} className="border-b">
                        <td className="py-2">{item.medicamento}</td>
                        <td className="py-2">{item.dosis}</td>
                        <td className="py-2">{item.frecuencia}</td>
                        <td className="py-2">{item.duracion}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {printType === 'anteojos' && (
              <div>
                <h2 className="text-lg font-bold mb-4 text-center">RECETA DE ANTEOJOS</h2>
                <table className="w-full text-sm mb-4">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Ojo</th>
                      <th className="text-center py-2">Esfera</th>
                      <th className="text-center py-2">Cilindro</th>
                      <th className="text-center py-2">Eje</th>
                      <th className="text-center py-2">Adición</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b">
                      <td className="py-2 font-medium">OD</td>
                      <td className="text-center">{formData.recetas.anteojos.od.esfera}</td>
                      <td className="text-center">{formData.recetas.anteojos.od.cilindro}</td>
                      <td className="text-center">{formData.recetas.anteojos.od.eje}</td>
                      <td className="text-center">{formData.recetas.anteojos.od.adicion}</td>
                    </tr>
                    <tr className="border-b">
                      <td className="py-2 font-medium">OS</td>
                      <td className="text-center">{formData.recetas.anteojos.os.esfera}</td>
                      <td className="text-center">{formData.recetas.anteojos.os.cilindro}</td>
                      <td className="text-center">{formData.recetas.anteojos.os.eje}</td>
                      <td className="text-center">{formData.recetas.anteojos.os.adicion}</td>
                    </tr>
                  </tbody>
                </table>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><strong>DP:</strong> {formData.recetas.anteojos.distancia_pupilar}</div>
                  <div><strong>Tipo:</strong> {formData.recetas.anteojos.tipo_lente}</div>
                  <div><strong>Material:</strong> {formData.recetas.anteojos.material}</div>
                  <div><strong>Uso:</strong> {formData.recetas.anteojos.uso}</div>
                </div>
                {formData.recetas.anteojos.tratamientos && (
                  <p className="mt-2 text-sm"><strong>Tratamientos:</strong> {formData.recetas.anteojos.tratamientos}</p>
                )}
              </div>
            )}
            
            {printType === 'lentes_contacto' && (
              <div>
                <h2 className="text-lg font-bold mb-4 text-center">RECETA DE LENTES DE CONTACTO</h2>
                <table className="w-full text-sm mb-4">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Ojo</th>
                      <th className="text-center py-2">Poder</th>
                      <th className="text-center py-2">Curva Base</th>
                      <th className="text-center py-2">Diámetro</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b">
                      <td className="py-2 font-medium">OD</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.od.poder}</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.od.curva_base}</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.od.diametro}</td>
                    </tr>
                    <tr className="border-b">
                      <td className="py-2 font-medium">OS</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.os.poder}</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.os.curva_base}</td>
                      <td className="text-center">{formData.recetas.lentes_contacto.os.diametro}</td>
                    </tr>
                  </tbody>
                </table>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><strong>Marca:</strong> {formData.recetas.lentes_contacto.marca}</div>
                  <div><strong>Tipo:</strong> {formData.recetas.lentes_contacto.tipo}</div>
                  <div><strong>Reemplazo:</strong> {formData.recetas.lentes_contacto.regimen_reemplazo}</div>
                </div>
              </div>
            )}
            
            {/* Próxima Cita (si está agendada) */}
            {formData.proxima_cita?.agendar && formData.proxima_cita?.fecha && (
              <div className="mt-6 p-4 border-2 border-blue-200 rounded-lg bg-blue-50">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  <span className="font-bold text-blue-700">PRÓXIMA CITA</span>
                </div>
                <div className="text-sm">
                  <p><strong>Fecha:</strong> {new Date(formData.proxima_cita.fecha + 'T12:00:00').toLocaleDateString('es-GT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
                  <p><strong>Hora:</strong> {formData.proxima_cita.hora}</p>
                  <p><strong>Médico:</strong> {formData.proxima_cita.medico_nombre}</p>
                  {formData.proxima_cita.tipo_cita && <p><strong>Tipo:</strong> {formData.proxima_cita.tipo_cita}</p>}
                </div>
              </div>
            )}
            
            {/* Pie de Receta */}
            <div className="mt-12 pt-8 border-t">
              <div className="flex justify-between items-end">
                <div className="text-sm text-gray-600">
                  <p>Fecha de emisión: {new Date().toLocaleDateString('es-GT')}</p>
                </div>
                <div className="text-center">
                  <div className="border-t border-black w-48 mb-2"></div>
                  <p className="font-medium">{formData.medico_nombre}</p>
                  <p className="text-xs text-gray-600">Médico Oftalmólogo</p>
                  <p className="text-xs text-gray-500">Colegiado No. _______</p>
                </div>
              </div>
            </div>
            
            {/* Botón para cerrar (no se imprime) */}
            <div className="mt-8 text-center no-print">
              <Button onClick={() => setPrintDialogOpen(false)} className="btn-primary">
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default EvaluacionOftalmologica;
