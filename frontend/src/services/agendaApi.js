// /app/frontend/src/services/agendaApi.js
// API service para el módulo de Agenda

import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };
};

export const agendaApi = {
  // Citas
  getCitas: (fecha, medicoId, estado) => {
    const params = new URLSearchParams();
    if (fecha) params.append('fecha', fecha);
    if (medicoId) params.append('medico_id', medicoId);
    if (estado) params.append('estado', estado);
    return axios.get(`${API_URL}/api/agenda/citas?${params}`, getAuthHeaders());
  },
  
  getCitasRango: (desde, hasta, medicoId) => {
    const params = new URLSearchParams({ desde, hasta });
    if (medicoId) params.append('medico_id', medicoId);
    return axios.get(`${API_URL}/api/agenda/citas/rango?${params}`, getAuthHeaders());
  },
  
  getCita: (id) => axios.get(`${API_URL}/api/agenda/citas/${id}`, getAuthHeaders()),

  getCitaHoyPaciente: (pacienteId) => axios.get(`${API_URL}/api/agenda/cita-hoy-paciente/${pacienteId}`, getAuthHeaders()),

  getCitasFuturasPaciente: (pacienteId) => axios.get(`${API_URL}/api/agenda/paciente/${pacienteId}/citas-futuras`, getAuthHeaders()),
  
  createCita: (data) => axios.post(`${API_URL}/api/agenda/citas`, data, getAuthHeaders()),
  
  updateCita: (id, data) => axios.put(`${API_URL}/api/agenda/citas/${id}`, data, getAuthHeaders()),
  
  cambiarEstado: (id, estado) => 
    axios.patch(`${API_URL}/api/agenda/citas/${id}/estado`, { estado }, getAuthHeaders()),
  
  revertirLlegada: (id) => 
    axios.patch(`${API_URL}/api/agenda/citas/${id}/revertir-llegada`, {}, getAuthHeaders()),
  
  asignarCita: (id, medicoId, medicoNombre) => 
    axios.patch(`${API_URL}/api/agenda/citas/${id}/asignar`, {
      asignado_a_medico_id: medicoId,
      asignado_a_medico_nombre: medicoNombre
    }, getAuthHeaders()),
  
  deleteCita: (id) => axios.delete(`${API_URL}/api/agenda/citas/${id}`, getAuthHeaders()),
  
  // Presentes
  getPresentes: (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    return axios.get(`${API_URL}/api/agenda/presentes${params}`, getAuthHeaders());
  },
  
  // Contadores
  getContadores: (fecha) => {
    const params = fecha ? `?fecha=${fecha}` : '';
    return axios.get(`${API_URL}/api/agenda/contadores${params}`, getAuthHeaders());
  },
  
  // Reconciliar pacientes atendidos (histórico) — marca Atendida las citas con evaluación
  reconciliarAtendidos: () => axios.post(`${API_URL}/api/agenda/reconciliar-atendidos`, {}, getAuthHeaders()),
  
  // Mi día (médico)
  getMiDia: (fecha) => axios.get(`${API_URL}/api/agenda/mi-dia${fecha ? `?fecha=${fecha}` : ''}`, getAuthHeaders()),
  getMiSemana: (desde, hasta) => axios.get(`${API_URL}/api/agenda/mi-semana?desde=${desde}&hasta=${hasta}`, getAuthHeaders()),
  getPreferenciasMedicos: () => axios.get(`${API_URL}/api/agenda/preferencias-medicos`, getAuthHeaders()),
  setPreferenciasMedicos: (orden, ocultos) => axios.put(`${API_URL}/api/agenda/preferencias-medicos`, { orden, ocultos }, getAuthHeaders()),
  
  // Walk-in
  createWalkIn: (data) => axios.post(`${API_URL}/api/agenda/walk-in`, data, getAuthHeaders()),
  
  // Próxima cita (desde evaluación)
  createProximaCita: (data) => axios.post(`${API_URL}/api/agenda/proxima-cita`, data, getAuthHeaders()),

  getHorariosDisponibles: (medicoId, fecha, duracion = 20) =>
    axios.get(`${API_URL}/api/agenda/horarios-disponibles?medico_id=${medicoId}&fecha=${fecha}&duracion=${duracion}`, getAuthHeaders()),

  verificarHorario: (medicoId, fecha, hora, duracion = 20) =>
    axios.get(`${API_URL}/api/agenda/verificar-horario?medico_id=${medicoId}&fecha=${fecha}&hora=${hora}&duracion=${duracion}`, getAuthHeaders()),
  
  // Configuración
  getConfig: () => axios.get(`${API_URL}/api/agenda/configuracion`, getAuthHeaders()),
  updateConfig: (data) => axios.put(`${API_URL}/api/agenda/configuracion`, data, getAuthHeaders()),
  
  // Médicos para agenda
  getMedicosAgenda: () => axios.get(`${API_URL}/api/medicos-agenda`, getAuthHeaders()),
  updateMedicoAgenda: (id, data) => axios.patch(`${API_URL}/api/medicos-agenda/${id}`, data, getAuthHeaders()),

  // Bloqueos de agenda
  getBloqueos: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.medico_id) qs.append('medico_id', params.medico_id);
    if (params.fecha) qs.append('fecha', params.fecha);
    if (params.desde) qs.append('desde', params.desde);
    if (params.hasta) qs.append('hasta', params.hasta);
    return axios.get(`${API_URL}/api/agenda/bloqueos?${qs}`, getAuthHeaders());
  },
  crearBloqueo: (data) => axios.post(`${API_URL}/api/agenda/bloqueos`, data, getAuthHeaders()),
  eliminarBloqueo: (id) => axios.delete(`${API_URL}/api/agenda/bloqueos/${id}`, getAuthHeaders())
};

export default agendaApi;
