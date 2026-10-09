import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import {
  Search, Plus, Phone, Mail, Calendar, User, Activity,
  ChevronDown, Filter, MoreVertical, CheckCircle, XCircle,
  Clock, MessageSquare, Eye, RefreshCw, Stethoscope, Trash2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Skeleton } from '../components/ui/skeleton';
import { toast, Toaster } from 'sonner';
import api, { getGuatemalaDate } from '../services/api';

const CRMCirugias = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState({});
  const [tiposCirugia, setTiposCirugia] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  
  // Filtros
  const [search, setSearch] = useState('');
  const [filterEstado, setFilterEstado] = useState('');
  const [filterTipo, setFilterTipo] = useState('');
  const [filterPrioridad, setFilterPrioridad] = useState('');
  
  // Modales
  const [newCandidateOpen, setNewCandidateOpen] = useState(false);
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [discardMotivo, setDiscardMotivo] = useState('');
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  
  // Forms
  const [newCandidate, setNewCandidate] = useState({
    paciente_id: '',
    paciente_nombre: '',
    tipo_cirugia: '',
    ojo: 'OU',
    diagnostico: '',
    prioridad: 'normal',
    notas: ''
  });
  
  const [followUp, setFollowUp] = useState({
    tipo: 'llamada',
    notas: '',
    resultado: 'interesado',
    proxima_accion: '',
    fecha_proxima_accion: ''
  });
  
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleNotes, setScheduleNotes] = useState('');
  const [searchPaciente, setSearchPaciente] = useState('');
  const [showPacienteList, setShowPacienteList] = useState(false);

  const canEdit = user?.role === 'superadmin' || user?.role === 'admin';

  // Fetch candidatos
  const fetchCandidates = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filterEstado) params.append('estado', filterEstado);
      if (filterTipo) params.append('tipo_cirugia', filterTipo);
      if (filterPrioridad) params.append('prioridad', filterPrioridad);
      
      const response = await api.get(`/surgery-crm?${params.toString()}`);
      setCandidates(response.data.data || []);
      setStats(response.data.stats || {});
    } catch (error) {
      console.error('Error fetching candidates:', error);
      toast.error('Error al cargar candidatos');
    }
  }, [search, filterEstado, filterTipo, filterPrioridad]);

  // Fetch tipos de cirugía
  const fetchTiposCirugia = useCallback(async () => {
    try {
      const response = await api.get('/surgery-crm/tipos-cirugia');
      setTiposCirugia(response.data || []);
    } catch (error) {
      console.error('Error fetching tipos:', error);
    }
  }, []);

  // Buscar pacientes
  const buscarPacientes = useCallback(async (search) => {
    if (!search || search.length < 2) {
      setPacientes([]);
      return;
    }
    try {
      const response = await api.get(`/pacientes/buscar?search=${encodeURIComponent(search)}&limit=10`);
      setPacientes(response.data || []);
    } catch (error) {
      console.error('Error searching pacientes:', error);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchCandidates(), fetchTiposCirugia()]);
      setLoading(false);
    };
    init();
  }, [fetchCandidates, fetchTiposCirugia]);

  useEffect(() => {
    const timer = setTimeout(() => {
      buscarPacientes(searchPaciente);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchPaciente, buscarPacientes]);

  // Crear candidato
  const handleCreateCandidate = async () => {
    if (!newCandidate.paciente_id || !newCandidate.tipo_cirugia) {
      toast.error('Debe seleccionar paciente y tipo de cirugía');
      return;
    }
    
    try {
      await api.post('/surgery-crm', newCandidate);
      toast.success('Candidato agregado al CRM');
      setNewCandidateOpen(false);
      setNewCandidate({
        paciente_id: '',
        paciente_nombre: '',
        tipo_cirugia: '',
        ojo: 'OU',
        diagnostico: '',
        prioridad: 'normal',
        notas: ''
      });
      setSearchPaciente('');
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear candidato');
    }
  };

  // Agregar seguimiento
  const handleAddFollowUp = async () => {
    if (!followUp.notas) {
      toast.error('Debe agregar notas del seguimiento');
      return;
    }
    
    try {
      await api.post(`/surgery-crm/${selectedCandidate.id}/seguimiento`, followUp);
      toast.success('Seguimiento registrado');
      setFollowUpOpen(false);
      setFollowUp({
        tipo: 'llamada',
        notas: '',
        resultado: 'interesado',
        proxima_accion: '',
        fecha_proxima_accion: ''
      });
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al registrar seguimiento');
    }
  };

  // Programar cirugía
  const handleSchedule = async () => {
    if (!scheduleDate) {
      toast.error('Debe seleccionar una fecha');
      return;
    }
    
    try {
      await api.post(`/surgery-crm/${selectedCandidate.id}/programar`, {
        fecha_programada: scheduleDate,
        notas: scheduleNotes
      });
      toast.success('Cirugía programada');
      setScheduleOpen(false);
      setScheduleDate('');
      setScheduleNotes('');
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al programar');
    }
  };

  // Marcar como operado
  const handleMarkOperated = async (candidate) => {
    try {
      await api.post(`/surgery-crm/${candidate.id}/marcar-operado`, { notas: '' });
      toast.success('Marcado como operado');
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error');
    }
  };

  // Descartar
  const handleDiscard = async () => {
    if (!discardMotivo.trim()) {
      toast.error('Debe indicar el motivo del descarte');
      return;
    }
    try {
      await api.post(`/surgery-crm/${selectedCandidate.id}/descartar`, { motivo: discardMotivo });
      toast.success('Candidato descartado');
      setDiscardOpen(false);
      setDiscardMotivo('');
      setSelectedCandidate(null);
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error');
    }
  };

  // Eliminar candidato descartado
  const handleDelete = async (candidate) => {
    if (!window.confirm('¿Eliminar permanentemente este registro?')) return;
    try {
      await api.delete(`/surgery-crm/${candidate.id}`);
      toast.success('Registro eliminado');
      fetchCandidates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar');
    }
  };

  // Seleccionar paciente
  const seleccionarPaciente = (paciente) => {
    setNewCandidate(prev => ({
      ...prev,
      paciente_id: paciente.id,
      paciente_nombre: paciente.nombre_completo
    }));
    setSearchPaciente(paciente.nombre_completo);
    setShowPacienteList(false);
  };

  // Obtener badge de estado
  const getEstadoBadge = (estado) => {
    const styles = {
      pendiente: 'bg-amber-100 text-amber-700',
      contactado: 'bg-blue-100 text-blue-700',
      programado: 'bg-purple-100 text-purple-700',
      operado: 'bg-emerald-100 text-emerald-700',
      descartado: 'bg-gray-100 text-gray-500'
    };
    const labels = {
      pendiente: 'Pendiente',
      contactado: 'Contactado',
      programado: 'Programado',
      operado: 'Operado',
      descartado: 'Descartado'
    };
    return <Badge className={styles[estado] || styles.pendiente}>{labels[estado] || estado}</Badge>;
  };

  // Obtener badge de prioridad
  const getPrioridadBadge = (prioridad) => {
    const styles = {
      alta: 'bg-red-100 text-red-700',
      normal: 'bg-blue-100 text-blue-700',
      baja: 'bg-gray-100 text-gray-600'
    };
    return <Badge className={styles[prioridad] || styles.normal}>{prioridad}</Badge>;
  };

  // Obtener badge de nivel de interés
  const getInteresBadge = (nivel) => {
    const styles = {
      muy_interesado: 'bg-emerald-100 text-emerald-700',
      interesado: 'bg-blue-100 text-blue-700',
      indeciso: 'bg-amber-100 text-amber-700',
      poco_interesado: 'bg-red-100 text-red-700'
    };
    const labels = {
      muy_interesado: 'Muy Interesado',
      interesado: 'Interesado',
      indeciso: 'Indeciso',
      poco_interesado: 'Poco Interesado'
    };
    return <Badge className={styles[nivel] || styles.interesado}>{labels[nivel] || nivel}</Badge>;
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-6 space-y-4">
          <Skeleton className="h-20 w-full" />
          <div className="grid grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-24" />)}
          </div>
          <Skeleton className="h-96" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      <div className="space-y-6 animate-fade-in" data-testid="crm-cirugias-page">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              CRM Cirugías
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Gestión de pacientes interesados en cirugía
            </p>
          </div>
          
          {canEdit && (
            <Button 
              onClick={() => setNewCandidateOpen(true)}
              className="btn-primary"
            >
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Candidato
            </Button>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="card-teal">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Pendientes</p>
                  <p className="text-2xl font-bold text-amber-600">{stats.pendiente || 0}</p>
                </div>
                <Clock className="w-8 h-8 text-amber-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="card-teal">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Contactados</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.contactado || 0}</p>
                </div>
                <Phone className="w-8 h-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="card-teal">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Programados</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.programado || 0}</p>
                </div>
                <Calendar className="w-8 h-8 text-purple-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="card-teal">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Operados</p>
                  <p className="text-2xl font-bold text-emerald-600">{stats.operado || 0}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-emerald-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="card-teal">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Total</p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{stats.total || 0}</p>
                </div>
                <Activity className="w-8 h-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filtros */}
        <Card className="card-teal">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Buscar por nombre, diagnóstico..."
                    className="input-teal pl-10"
                  />
                </div>
              </div>
              
              <Select value={filterEstado || undefined} onValueChange={(v) => setFilterEstado(v === 'all' ? '' : v)}>
                <SelectTrigger className="input-teal w-40">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pendiente">Pendiente</SelectItem>
                  <SelectItem value="contactado">Contactado</SelectItem>
                  <SelectItem value="programado">Programado</SelectItem>
                  <SelectItem value="operado">Operado</SelectItem>
                  <SelectItem value="descartado">Descartado</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={filterTipo || undefined} onValueChange={(v) => setFilterTipo(v === 'all' ? '' : v)}>
                <SelectTrigger className="input-teal w-40">
                  <SelectValue placeholder="Tipo Cirugía" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {tiposCirugia.map(tipo => (
                    <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={filterPrioridad || undefined} onValueChange={(v) => setFilterPrioridad(v === 'all' ? '' : v)}>
                <SelectTrigger className="input-teal w-32">
                  <SelectValue placeholder="Prioridad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="alta">Alta</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="baja">Baja</SelectItem>
                </SelectContent>
              </Select>
              
              <Button
                variant="outline"
                onClick={() => {
                  setSearch('');
                  setFilterEstado('');
                  setFilterTipo('');
                  setFilterPrioridad('');
                }}
                className="btn-outline"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tabla */}
        <Card className="card-teal">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-blue-50/50">
                  <TableHead>Paciente</TableHead>
                  <TableHead>Tipo Cirugía</TableHead>
                  <TableHead>Ojo</TableHead>
                  <TableHead>Diagnóstico</TableHead>
                  <TableHead>Prioridad</TableHead>
                  <TableHead>Interés</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Seguimientos</TableHead>
                  <TableHead>Fecha Prog.</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidates.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8 text-gray-500">
                      No hay candidatos registrados
                    </TableCell>
                  </TableRow>
                ) : (
                  candidates.map((candidate) => (
                    <TableRow 
                      key={candidate.id}
                      className="hover:bg-blue-50/30 cursor-pointer"
                      onClick={() => {
                        setSelectedCandidate(candidate);
                        setDetailOpen(true);
                      }}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-400" />
                          <div>
                            <div className="font-medium text-sm">{candidate.paciente_nombre}</div>
                            {candidate.paciente_telefono && (
                              <div className="text-xs text-gray-500">{candidate.paciente_telefono}</div>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="border-blue-200 text-blue-700">
                          {candidate.tipo_cirugia}
                        </Badge>
                      </TableCell>
                      <TableCell>{candidate.ojo}</TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm">
                        {candidate.diagnostico || '-'}
                      </TableCell>
                      <TableCell>{getPrioridadBadge(candidate.prioridad)}</TableCell>
                      <TableCell>{getInteresBadge(candidate.nivel_interes)}</TableCell>
                      <TableCell>{getEstadoBadge(candidate.estado)}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {candidate.seguimientos?.length || 0}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {candidate.fecha_programada ? (
                          <span className="text-sm">{candidate.fecha_programada}</span>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => {
                              e.stopPropagation();
                              setSelectedCandidate(candidate);
                              setFollowUpOpen(true);
                            }}>
                              <MessageSquare className="w-4 h-4 mr-2" />
                              Registrar Seguimiento
                            </DropdownMenuItem>
                            {candidate.estado !== 'programado' && candidate.estado !== 'operado' && (
                              <DropdownMenuItem onClick={(e) => {
                                e.stopPropagation();
                                setSelectedCandidate(candidate);
                                setScheduleOpen(true);
                              }}>
                                <Calendar className="w-4 h-4 mr-2" />
                                Programar Cirugía
                              </DropdownMenuItem>
                            )}
                            {candidate.estado === 'programado' && (
                              <DropdownMenuItem onClick={(e) => {
                                e.stopPropagation();
                                handleMarkOperated(candidate);
                              }}>
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Marcar Operado
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {candidate.estado !== 'descartado' && candidate.estado !== 'operado' && (
                              <DropdownMenuItem 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedCandidate(candidate);
                                  setDiscardOpen(true);
                                }}
                                className="text-red-600"
                              >
                                <XCircle className="w-4 h-4 mr-2" />
                                Descartar
                              </DropdownMenuItem>
                            )}
                            {(candidate.estado === 'descartado' || candidate.estado === 'operado') && (
                              <DropdownMenuItem 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(candidate);
                                }}
                                className="text-red-600"
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Eliminar Registro
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Modal Nuevo Candidato */}
        <Dialog open={newCandidateOpen} onOpenChange={setNewCandidateOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Nuevo Candidato a Cirugía</DialogTitle>
              <DialogDescription>
                Agregue un paciente interesado en cirugía al CRM
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Buscar Paciente */}
              <div>
                <Label>Paciente *</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    value={searchPaciente}
                    onChange={(e) => {
                      setSearchPaciente(e.target.value);
                      setShowPacienteList(true);
                    }}
                    onFocus={() => setShowPacienteList(true)}
                    placeholder="Buscar paciente..."
                    className="input-teal pl-10"
                  />
                  {showPacienteList && pacientes.length > 0 && (
                    <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                      {pacientes.map((p) => (
                        <div
                          key={p.id}
                          className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
                          onClick={() => seleccionarPaciente(p)}
                        >
                          <div className="font-medium text-sm">{p.nombre_completo}</div>
                          <div className="text-xs text-gray-500">Exp: {p.record_number}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Tipo de Cirugía */}
              <div>
                <Label>Tipo de Cirugía *</Label>
                <Select
                  value={newCandidate.tipo_cirugia}
                  onValueChange={(v) => setNewCandidate(prev => ({ ...prev, tipo_cirugia: v }))}
                >
                  <SelectTrigger className="input-teal">
                    <SelectValue placeholder="Seleccionar..." />
                  </SelectTrigger>
                  <SelectContent>
                    {tiposCirugia.map(tipo => (
                      <SelectItem key={tipo} value={tipo}>{tipo}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Ojo y Prioridad */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Ojo</Label>
                  <Select
                    value={newCandidate.ojo}
                    onValueChange={(v) => setNewCandidate(prev => ({ ...prev, ojo: v }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="OD">OD (Derecho)</SelectItem>
                      <SelectItem value="OS">OS (Izquierdo)</SelectItem>
                      <SelectItem value="OU">OU (Ambos)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Prioridad</Label>
                  <Select
                    value={newCandidate.prioridad}
                    onValueChange={(v) => setNewCandidate(prev => ({ ...prev, prioridad: v }))}
                  >
                    <SelectTrigger className="input-teal">
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
              
              {/* Diagnóstico */}
              <div>
                <Label>Diagnóstico</Label>
                <Input
                  value={newCandidate.diagnostico}
                  onChange={(e) => setNewCandidate(prev => ({ ...prev, diagnostico: e.target.value }))}
                  placeholder="Diagnóstico del paciente..."
                  className="input-teal"
                />
              </div>
              
              {/* Notas */}
              <div>
                <Label>Notas</Label>
                <Textarea
                  value={newCandidate.notas}
                  onChange={(e) => setNewCandidate(prev => ({ ...prev, notas: e.target.value }))}
                  placeholder="Notas adicionales..."
                  className="input-teal min-h-[80px]"
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setNewCandidateOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCreateCandidate} className="btn-primary">
                Agregar Candidato
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal Seguimiento */}
        <Dialog open={followUpOpen} onOpenChange={setFollowUpOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Registrar Seguimiento</DialogTitle>
              <DialogDescription>
                {selectedCandidate?.paciente_nombre} - {selectedCandidate?.tipo_cirugia}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Tipo de Contacto</Label>
                  <Select
                    value={followUp.tipo}
                    onValueChange={(v) => setFollowUp(prev => ({ ...prev, tipo: v }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="llamada">Llamada</SelectItem>
                      <SelectItem value="whatsapp">WhatsApp</SelectItem>
                      <SelectItem value="email">Email</SelectItem>
                      <SelectItem value="presencial">Presencial</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Resultado</Label>
                  <Select
                    value={followUp.resultado}
                    onValueChange={(v) => setFollowUp(prev => ({ ...prev, resultado: v }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="interesado">Interesado</SelectItem>
                      <SelectItem value="no_contesta">No Contesta</SelectItem>
                      <SelectItem value="reprogramar">Reprogramar</SelectItem>
                      <SelectItem value="no_interesado">No Interesado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div>
                <Label>Notas del Seguimiento *</Label>
                <Textarea
                  value={followUp.notas}
                  onChange={(e) => setFollowUp(prev => ({ ...prev, notas: e.target.value }))}
                  placeholder="Detalles de la conversación..."
                  className="input-teal min-h-[100px]"
                />
              </div>
              
              <div>
                <Label>Próxima Acción</Label>
                <Input
                  value={followUp.proxima_accion}
                  onChange={(e) => setFollowUp(prev => ({ ...prev, proxima_accion: e.target.value }))}
                  placeholder="Ej: Llamar la próxima semana"
                  className="input-teal"
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setFollowUpOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleAddFollowUp} className="btn-primary">
                Registrar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal Programar Cirugía */}
        <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Programar Cirugía</DialogTitle>
              <DialogDescription>
                {selectedCandidate?.paciente_nombre} - {selectedCandidate?.tipo_cirugia}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <Label>Fecha de Cirugía *</Label>
                <Input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => setScheduleDate(e.target.value)}
                  min={getGuatemalaDate()}
                  className="input-teal"
                />
              </div>
              
              <div>
                <Label>Notas</Label>
                <Textarea
                  value={scheduleNotes}
                  onChange={(e) => setScheduleNotes(e.target.value)}
                  placeholder="Notas adicionales..."
                  className="input-teal min-h-[80px]"
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setScheduleOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleSchedule} className="btn-primary">
                Programar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Modal Detalle */}
        <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
          <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <Stethoscope className="w-5 h-5 text-blue-600" />
                Detalle del Candidato
              </DialogTitle>
            </DialogHeader>
            
            {selectedCandidate && (
              <div className="space-y-6">
                {/* Info del Paciente */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-lg">{selectedCandidate.paciente_nombre}</h3>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                        {selectedCandidate.paciente_telefono && (
                          <span className="flex items-center gap-1">
                            <Phone className="w-3 h-3" />
                            {selectedCandidate.paciente_telefono}
                          </span>
                        )}
                        {selectedCandidate.paciente_email && (
                          <span className="flex items-center gap-1">
                            <Mail className="w-3 h-3" />
                            {selectedCandidate.paciente_email}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      {getEstadoBadge(selectedCandidate.estado)}
                      <div className="mt-1">
                        {getPrioridadBadge(selectedCandidate.prioridad)}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Info de la Cirugía */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">Tipo de Cirugía</Label>
                    <p className="font-medium">{selectedCandidate.tipo_cirugia}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Ojo</Label>
                    <p className="font-medium">{selectedCandidate.ojo}</p>
                  </div>
                  <div className="col-span-2">
                    <Label className="text-xs text-gray-500">Diagnóstico</Label>
                    <p>{selectedCandidate.diagnostico || 'No especificado'}</p>
                  </div>
                  {selectedCandidate.fecha_programada && (
                    <div className="col-span-2">
                      <Label className="text-xs text-gray-500">Fecha Programada</Label>
                      <p className="font-medium text-purple-600">{selectedCandidate.fecha_programada}</p>
                    </div>
                  )}
                  {selectedCandidate.notas && (
                    <div className="col-span-2">
                      <Label className="text-xs text-gray-500">Notas</Label>
                      <p className="text-sm whitespace-pre-wrap">{selectedCandidate.notas}</p>
                    </div>
                  )}
                </div>
                
                {/* Historial de Seguimientos */}
                <div>
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Historial de Seguimientos ({selectedCandidate.seguimientos?.length || 0})
                  </h4>
                  {selectedCandidate.seguimientos?.length > 0 ? (
                    <div className="space-y-3">
                      {selectedCandidate.seguimientos.map((seg, idx) => (
                        <div key={seg.id || idx} className="border-l-2 border-blue-200 pl-3 py-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {seg.tipo}
                              </Badge>
                              <Badge className={`text-xs ${
                                seg.resultado === 'interesado' ? 'bg-green-100 text-green-700' :
                                seg.resultado === 'no_interesado' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {seg.resultado}
                              </Badge>
                            </div>
                            <span className="text-xs text-gray-500">
                              {seg.fecha ? new Date(seg.fecha).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' }) : ''}
                            </span>
                          </div>
                          <p className="text-sm mt-1">{seg.notas}</p>
                          {seg.usuario_nombre && (
                            <p className="text-xs text-gray-400 mt-1">Por: {seg.usuario_nombre}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic">No hay seguimientos registrados</p>
                  )}
                </div>
                
                {/* Origen */}
                <div className="text-xs text-gray-500 pt-2 border-t">
                  <span>Origen: {selectedCandidate.origen === 'evaluacion' ? 'Evaluación Oftalmológica' : 'Registro Manual'}</span>
                  {selectedCandidate.created_at && (
                    <span className="ml-4">
                      Creado: {new Date(selectedCandidate.created_at).toLocaleDateString('es-GT', { timeZone: 'America/Guatemala' })}
                    </span>
                  )}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Modal Descartar */}
        <Dialog open={discardOpen} onOpenChange={(open) => {
          setDiscardOpen(open);
          if (!open) setDiscardMotivo('');
        }}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] text-red-600 flex items-center gap-2">
                <XCircle className="w-5 h-5" />
                Descartar Candidato
              </DialogTitle>
              <DialogDescription>
                {selectedCandidate?.paciente_nombre} - {selectedCandidate?.tipo_cirugia}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <Label>Motivo del Descarte *</Label>
                <Textarea
                  value={discardMotivo}
                  onChange={(e) => setDiscardMotivo(e.target.value)}
                  placeholder="Explique el motivo por el cual se descarta este candidato..."
                  className="input-teal min-h-[100px]"
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setDiscardOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleDiscard} className="bg-red-600 hover:bg-red-700 text-white">
                Descartar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default CRMCirugias;
