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
  
  createCita: (data) => axios.post(`${API_URL}/api/agenda/citas`, data, getAuthHeaders()),
  
  updateCita: (id, data) => axios.put(`${API_URL}/api/agenda/citas/${id}`, data, getAuthHeaders()),
  
  cambiarEstado: (id, estado) => 
    axios.patch(`${API_URL}/api/agenda/citas/${id}/estado`, { estado }, getAuthHeaders()),
  
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
  
  // Mi día (médico)
  getMiDia: () => axios.get(`${API_URL}/api/agenda/mi-dia`, getAuthHeaders()),
  
  // Walk-in
  createWalkIn: (data) => axios.post(`${API_URL}/api/agenda/walk-in`, data, getAuthHeaders()),
  
  // Próxima cita (desde evaluación)
  createProximaCita: (data) => axios.post(`${API_URL}/api/agenda/proxima-cita`, data, getAuthHeaders()),
  
  // Configuración
  getConfig: () => axios.get(`${API_URL}/api/agenda/configuracion`, getAuthHeaders()),
  updateConfig: (data) => axios.put(`${API_URL}/api/agenda/configuracion`, data, getAuthHeaders()),
  
  // Médicos para agenda
  getMedicosAgenda: () => axios.get(`${API_URL}/api/medicos-agenda`, getAuthHeaders()),
  updateMedicoAgenda: (id, data) => axios.patch(`${API_URL}/api/medicos-agenda/${id}`, data, getAuthHeaders())
};

export default agendaApi;
