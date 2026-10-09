import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Set up axios interceptor for auth token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Expense API
export const expenseApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.type) params.append('type', filters.type);
    if (filters.status) params.append('status', filters.status);
    if (filters.search) params.append('search', filters.search);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.limit) params.append('limit', filters.limit.toString());
    if (filters.sortBy) params.append('sortBy', filters.sortBy);
    if (filters.sortOrder) params.append('sortOrder', filters.sortOrder);
    return axios.get(`${API_URL}/expenses?${params.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/expenses/${id}`),
  create: (data) => axios.post(`${API_URL}/expenses`, data),
  update: (id, data) => axios.put(`${API_URL}/expenses/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/expenses/${id}`),
  getPayments: (expenseId) => axios.get(`${API_URL}/expenses/${expenseId}/payments`),
  toggleAuthorization: (id) => axios.put(`${API_URL}/expenses/${id}/toggle-authorization`),
  authorizeWithBank: (id, bankAccountId) => axios.post(`${API_URL}/expenses/${id}/authorize`, { bank_account_id: bankAccountId }),
  confirmAuthorizations: () => axios.post(`${API_URL}/expenses/confirm-authorizations`),
  exportReport: (filters = {}) => {
    const params = new URLSearchParams();
    params.append('format', filters.format || 'xlsx');
    if (filters.type) params.append('type', filters.type);
    if (filters.status) params.append('status', filters.status);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    return `${API_URL}/reports/expenses?${params.toString()}`;
  }
};

// Payment API
export const paymentApi = {
  getAll: (expenseId = null) => {
    const params = expenseId ? `?expense_id=${expenseId}` : '';
    return axios.get(`${API_URL}/payments${params}`);
  },
  create: (data) => axios.post(`${API_URL}/payments`, data),
  delete: (id) => axios.delete(`${API_URL}/payments/${id}`),
};

// User API
export const userApi = {
  getAll: () => axios.get(`${API_URL}/users`),
  create: (data) => axios.post(`${API_URL}/users`, data),
  update: (id, data) => axios.put(`${API_URL}/users/${id}`, data),
  toggleActive: (id) => axios.put(`${API_URL}/users/${id}/toggle-active`),
  delete: (id) => axios.delete(`${API_URL}/users/${id}`),
};

// Dashboard API
export const dashboardApi = {
  getSummary: () => axios.get(`${API_URL}/dashboard/summary`),
  getMonthlyChart: () => axios.get(`${API_URL}/dashboard/monthly-chart`),
  getUpcoming: () => axios.get(`${API_URL}/dashboard/upcoming`),
  // Legacy endpoints for backwards compatibility
  getStats: () => axios.get(`${API_URL}/dashboard/stats`),
  getAlerts30: () => axios.get(`${API_URL}/dashboard/alerts/30`),
  getAlerts60: () => axios.get(`${API_URL}/dashboard/alerts/60`),
  getChartData: () => axios.get(`${API_URL}/dashboard/chart-data`),
};

// Bank Accounts API
export const bankAccountApi = {
  getAll: () => axios.get(`${API_URL}/bank-accounts`),
  getById: (id) => axios.get(`${API_URL}/bank-accounts/${id}`),
  create: (data) => axios.post(`${API_URL}/bank-accounts`, data),
  update: (id, data) => axios.put(`${API_URL}/bank-accounts/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/bank-accounts/${id}`),
};

// Payment Authorization API
export const paymentAuthorizationApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    const queryString = params.toString();
    return axios.get(`${API_URL}/payment-authorizations${queryString ? `?${queryString}` : ''}`);
  },
  getById: (id) => axios.get(`${API_URL}/payment-authorizations/${id}`),
  getExpensesPendingAuth: () => axios.get(`${API_URL}/expenses-pending-authorization`),
  create: (data) => axios.post(`${API_URL}/payment-authorizations`, data),
  update: (id, data) => axios.put(`${API_URL}/payment-authorizations/${id}`, data),
  execute: (id, paymentData = {}) => axios.post(`${API_URL}/payment-authorizations/${id}/execute`, paymentData),
  cancel: (id) => axios.post(`${API_URL}/payment-authorizations/${id}/cancel`),
  delete: (id) => axios.delete(`${API_URL}/payment-authorizations/${id}`),
};

// Surgery API (Sala de Operaciones)
export const surgeryApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.page) params.append('page', filters.page);
    if (filters.limit) params.append('limit', filters.limit);
    if (filters.search) params.append('search', filters.search);
    if (filters.surgeon) params.append('surgeon', filters.surgeon);
    if (filters.institution) params.append('institution', filters.institution);
    if (filters.eye) params.append('eye', filters.eye);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    if (filters.sortBy) params.append('sortBy', filters.sortBy);
    if (filters.sortOrder) params.append('sortOrder', filters.sortOrder);
    const queryString = params.toString();
    return axios.get(`${API_URL}/surgeries${queryString ? `?${queryString}` : ''}`);
  },
  getById: (id) => axios.get(`${API_URL}/surgeries/${id}`),
  getOptions: () => axios.get(`${API_URL}/surgeries/options`),
  create: (data) => axios.post(`${API_URL}/surgeries`, data),
  update: (id, data) => axios.put(`${API_URL}/surgeries/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/surgeries/${id}`),
  cancel: (id, reason, rescheduleDate) => axios.post(`${API_URL}/surgeries/${id}/cancel`, { reason, reschedule_date: rescheduleDate }),
  // Equipment
  addEquipment: (surgeryId, data) => axios.post(`${API_URL}/surgeries/${surgeryId}/equipment`, data),
  deleteEquipment: (surgeryId, equipmentId) => axios.delete(`${API_URL}/surgeries/${surgeryId}/equipment/${equipmentId}`),
  // Supplies
  addSupply: (surgeryId, data) => axios.post(`${API_URL}/surgeries/${surgeryId}/supplies`, data),
  updateSupply: (surgeryId, supplyId, data) => axios.put(`${API_URL}/surgeries/${surgeryId}/supplies/${supplyId}`, data),
  deleteSupply: (surgeryId, supplyId) => axios.delete(`${API_URL}/surgeries/${surgeryId}/supplies/${supplyId}`),
  // Export
  exportReport: (filters = {}) => {
    const params = new URLSearchParams();
    params.append('format', filters.format || 'xlsx');
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    if (filters.surgeon) params.append('surgeon', filters.surgeon);
    if (filters.institution) params.append('institution', filters.institution);
    if (filters.eye) params.append('eye', filters.eye);
    return axios.get(`${API_URL}/reports/surgeries?${params.toString()}`, { responseType: 'blob' });
  },
};

// Suppliers API
export const supplierApi = {
  getAll: () => axios.get(`${API_URL}/suppliers`),
  getById: (id) => axios.get(`${API_URL}/suppliers/${id}`),
  create: (data) => axios.post(`${API_URL}/suppliers`, data),
  update: (id, data) => axios.put(`${API_URL}/suppliers/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/suppliers/${id}`),
};

// Fixed Expenses API (Gastos Fijos Recurrentes)
export const fixedExpenseApi = {
  getAll: () => axios.get(`${API_URL}/fixed-expenses`),
  getById: (id) => axios.get(`${API_URL}/fixed-expenses/${id}`),
  create: (data) => axios.post(`${API_URL}/fixed-expenses`, data),
  update: (id, data) => axios.put(`${API_URL}/fixed-expenses/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/fixed-expenses/${id}`),
  generateNow: () => axios.post(`${API_URL}/fixed-expenses/generate-now`),
};

// IGSS Units API (Catálogo de Unidades IGSS)
export const igssUnitApi = {
  getAll: () => axios.get(`${API_URL}/igss-units`),
  getReporte: () => axios.get(`${API_URL}/igss-units/reporte`),
  getById: (id) => axios.get(`${API_URL}/igss-units/${id}`),
  create: (data) => axios.post(`${API_URL}/igss-units`, data),
  update: (id, data) => axios.put(`${API_URL}/igss-units/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/igss-units/${id}`),
};

// NOG por Unidad IGSS API (contratos de servicios y acreditaciones)
export const igssNogApi = {
  getByUnit: (unitId) => axios.get(`${API_URL}/igss-units/${unitId}/nogs`),
  getActivos: (unitId) => axios.get(`${API_URL}/igss-units/${unitId}/nogs-activos`),
  getAlertas: () => axios.get(`${API_URL}/igss-units/nogs/alertas`),
  getResumen: () => axios.get(`${API_URL}/igss-units/nogs/resumen`),
  create: (unitId, data) => axios.post(`${API_URL}/igss-units/${unitId}/nogs`, data),
  update: (nogId, data) => axios.put(`${API_URL}/igss-units/nogs/${nogId}`, data),
  delete: (nogId) => axios.delete(`${API_URL}/igss-units/nogs/${nogId}`),
  recalcular: (nogId) => axios.post(`${API_URL}/igss-units/nogs/${nogId}/recalcular`),
  getPacientes: (nogId) => axios.get(`${API_URL}/igss-units/nogs/${nogId}/pacientes`),
  anularAcreditacion: (nogId, acredId, motivo) =>
    axios.post(`${API_URL}/igss-units/nogs/${nogId}/acreditaciones/${acredId}/anular`, { motivo }),
  exportExcel: (nogId) =>
    axios.get(`${API_URL}/igss-units/nogs/${nogId}/export/excel`, { responseType: 'blob' }),
  exportUnidadExcel: (unitId) =>
    axios.get(`${API_URL}/igss-units/${unitId}/nogs/export/excel`, { responseType: 'blob' }),
};

// Google Calendar API (sincronización de Agenda por médico)
export const googleCalendarApi = {
  getStatus: () => axios.get(`${API_URL}/google-calendar/status`),
  getCalendars: (doctorId) => axios.get(`${API_URL}/google-calendar/calendars`, { params: { doctor_id: doctorId } }),
  selectCalendar: (doctorId, calendarId, calendarName) =>
    axios.post(`${API_URL}/google-calendar/select-calendar`, { doctor_id: doctorId, calendar_id: calendarId, calendar_name: calendarName }),
  getConnectUrl: (doctorId) => axios.get(`${API_URL}/oauth/calendar/connect`, { params: { doctor_id: doctorId } }),
  disconnect: (doctorId) => axios.post(`${API_URL}/google-calendar/disconnect`, { doctor_id: doctorId }),
  sync: () => axios.post(`${API_URL}/google-calendar/sync`),
  limpiarDuplicados: () => axios.post(`${API_URL}/google-calendar/limpiar-duplicados`),
};

// Menu Configuration API
export const menuConfigApi = {
  getAvailableMenus: () => axios.get(`${API_URL}/menu-config/available-menus`),
  getMenuConfigForRole: (role) => axios.get(`${API_URL}/menu-config/role/${role}`),
  getAllMenuConfigs: () => axios.get(`${API_URL}/menu-config/all-roles`),
  updateMenuConfig: (role, data) => axios.put(`${API_URL}/menu-config/role/${role}`, data),
  resetMenuConfig: (role) => axios.post(`${API_URL}/menu-config/reset/${role}`),
  getMyMenus: () => axios.get(`${API_URL}/menu-config/my-menus`),
};

// Roles API (CRUD de roles y permisos)
export const rolesApi = {
  getAll: () => axios.get(`${API_URL}/roles/`),
  getById: (roleName) => axios.get(`${API_URL}/roles/${roleName}`),
  create: (data) => axios.post(`${API_URL}/roles/`, data),
  update: (roleName, data) => axios.put(`${API_URL}/roles/${roleName}`, data),
  delete: (roleName) => axios.delete(`${API_URL}/roles/${roleName}`),
  getAvailablePermissions: () => axios.get(`${API_URL}/roles/available-permissions`),
  resetPermissions: (roleName) => axios.post(`${API_URL}/roles/${roleName}/reset-permissions`),
  getRoleUsers: (roleName) => axios.get(`${API_URL}/roles/${roleName}/users`),
};

// Patients API (Base de Datos de Pacientes)
export const patientApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.limit) params.append('limit', filters.limit.toString());
    if (filters.search) params.append('search', filters.search);
    if (filters.referral_institution) params.append('referral_institution', filters.referral_institution);
    if (filters.igss_unit_id) params.append('igss_unit_id', filters.igss_unit_id);
    if (filters.igss_nog) params.append('igss_nog', filters.igss_nog);
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString());
    return axios.get(`${API_URL}/patients?${params.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/patients/${id}`),
  create: (data) => axios.post(`${API_URL}/patients`, data),
  update: (id, data) => axios.put(`${API_URL}/patients/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/patients/${id}`),
  reactivate: (id) => axios.post(`${API_URL}/patients/${id}/reactivate`),
  search: (q, limit = 10) => axios.get(`${API_URL}/patients/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  checkDuplicate: (params) => axios.get(`${API_URL}/patients/check-duplicate`, { params }),
  exportExcel: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.referral_institution) params.append('referral_institution', filters.referral_institution);
    if (filters.igss_unit_id) params.append('igss_unit_id', filters.igss_unit_id);
    if (filters.igss_nog) params.append('igss_nog', filters.igss_nog);
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    return `${API_URL}/patients/export/excel?${params.toString()}`;
  },
  exportPdf: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.referral_institution) params.append('referral_institution', filters.referral_institution);
    if (filters.igss_unit_id) params.append('igss_unit_id', filters.igss_unit_id);
    if (filters.igss_nog) params.append('igss_nog', filters.igss_nog);
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    return `${API_URL}/patients/export/pdf?${params.toString()}`;
  },
  downloadTemplate: () => `${API_URL}/patients/export/template`,
};

// ==================== OPTICA APIs ====================

// Doctors API (Médicos)
export const doctorApi = {
  getAll: (search = '') => axios.get(`${API_URL}/doctors${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getById: (id) => axios.get(`${API_URL}/doctors/${id}`),
  create: (data) => axios.post(`${API_URL}/doctors`, data),
  update: (id, data) => axios.put(`${API_URL}/doctors/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/doctors/${id}`),
  search: (q, limit = 10) => axios.get(`${API_URL}/doctors/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

export const surgeryNoteApi = {
  getByPatient: (patientId) => axios.get(`${API_URL}/surgery-notes?patient_id=${patientId}`),
  get: (id) => axios.get(`${API_URL}/surgery-notes/${id}`),
  update: (id, contenido) => axios.put(`${API_URL}/surgery-notes/${id}`, { contenido }),
  close: (id) => axios.post(`${API_URL}/surgery-notes/${id}/close`),
};


// Frame Inventory API (Inventario de Aros)
export const frameApi = {
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.low_stock) queryParams.append('low_stock', 'true');
    return axios.get(`${API_URL}/optica/frames?${queryParams.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/optica/frames/${id}`),
  create: (data) => axios.post(`${API_URL}/optica/frames`, data),
  update: (id, data) => axios.put(`${API_URL}/optica/frames/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/optica/frames/${id}`),
  search: (q, limit = 10) => axios.get(`${API_URL}/optica/frames/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

// Contact Lens Inventory API (Lentes de Contacto)
export const contactLensApi = {
  getAll: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.lens_type) queryParams.append('lens_type', params.lens_type);
    if (params.low_stock) queryParams.append('low_stock', 'true');
    return axios.get(`${API_URL}/optica/contact-lenses?${queryParams.toString()}`);
  },
  create: (data) => axios.post(`${API_URL}/optica/contact-lenses`, data),
  update: (id, data) => axios.put(`${API_URL}/optica/contact-lenses/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/optica/contact-lenses/${id}`),
  search: (q, limit = 10) => axios.get(`${API_URL}/optica/contact-lenses/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

// Lens Type Catalog API (Catálogo de Tipos de Lente)
export const lensTypeApi = {
  getAll: () => axios.get(`${API_URL}/optica/lens-types`),
  create: (data) => axios.post(`${API_URL}/optica/lens-types`, data),
  update: (id, data) => axios.put(`${API_URL}/optica/lens-types/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/optica/lens-types/${id}`),
};

// Optica Sales API (Ventas de Óptica)
export const opticaSaleApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.search) params.append('search', filters.search);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    return axios.get(`${API_URL}/optica/sales?${params.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/optica/sales/${id}`),
  create: (data) => axios.post(`${API_URL}/optica/sales`, data),
  getPending: () => axios.get(`${API_URL}/optica/sales/pending`),
  addPayment: (saleId, data) => axios.post(`${API_URL}/optica/sales/${saleId}/payments`, data),
  cancel: (saleId) => axios.put(`${API_URL}/optica/sales/${saleId}/cancel`),
  // Dashboard básico
  getDashboardStats: () => axios.get(`${API_URL}/optica/dashboard/stats`),
  getMonthlyChart: () => axios.get(`${API_URL}/optica/dashboard/monthly-chart`),
  getTopDoctors: (limit = 5) => axios.get(`${API_URL}/optica/dashboard/top-doctors?limit=${limit}`),
  getTopBrands: (limit = 5) => axios.get(`${API_URL}/optica/dashboard/top-brands?limit=${limit}`),
  // Dashboard avanzado
  getVentasDelDia: () => axios.get(`${API_URL}/optica/dashboard/ventas-dia`),
  getRentabilidad: (periodo = 'mes') => axios.get(`${API_URL}/optica/dashboard/rentabilidad?periodo=${periodo}`),
  getVentasPorOrigen: (params = {}) => {
    const urlParams = new URLSearchParams();
    if (params.fecha_inicio) urlParams.append('fecha_inicio', params.fecha_inicio);
    if (params.fecha_fin) urlParams.append('fecha_fin', params.fecha_fin);
    return axios.get(`${API_URL}/optica/dashboard/ventas-por-origen?${urlParams.toString()}`);
  },
  getInformeMensual: (year, month) => axios.get(`${API_URL}/optica/dashboard/informe-mensual?year=${year}&month=${month}`),
  getHistorialMensual: (meses = 12) => axios.get(`${API_URL}/optica/dashboard/historial-mensual?meses=${meses}`),
  // Reports
  getMonthlyReport: (year, month, format = 'json') => {
    const url = `${API_URL}/optica/reports/monthly?year=${year}&month=${month}&format=${format}`;
    if (format === 'json') {
      return axios.get(url);
    }
    return axios.get(url, { responseType: 'blob' });
  },
};

// Optica Purchases API
export const opticaPurchaseApi = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.category) params.append('category', filters.category);
    return axios.get(`${API_URL}/optica/purchases?${params.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/optica/purchases/${id}`),
  create: (data) => axios.post(`${API_URL}/optica/purchases`, data),
  update: (id, data) => axios.put(`${API_URL}/optica/purchases/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/optica/purchases/${id}`),
};

// Format currency helper
// Format currency helper - Format: Q 1,234.56
export const formatCurrency = (amount) => {
  const formatted = Number(amount).toLocaleString('es-GT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  return `Q ${formatted}`;
};

// Zona horaria de Guatemala (UTC-6)
const GUATEMALA_TIMEZONE = 'America/Guatemala';

// Format date helper - Formato dd/mm/yy (estándar Guatemala) con zona horaria correcta
export const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  // Usar Intl.DateTimeFormat con zona horaria de Guatemala
  return date.toLocaleDateString('es-GT', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    timeZone: GUATEMALA_TIMEZONE
  });
};

// Formatear fecha y hora completa en zona horaria de Guatemala
export const formatDateTime = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('es-GT', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: GUATEMALA_TIMEZONE
  });
};

// Formatear solo hora en zona horaria de Guatemala
export const formatTime = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleTimeString('es-GT', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: GUATEMALA_TIMEZONE
  });
};

// Obtener fecha actual en Guatemala (para comparaciones)
export const getGuatemalaDate = () => {
  return new Date().toLocaleDateString('en-CA', { timeZone: GUATEMALA_TIMEZONE }); // Formato YYYY-MM-DD
};

// Obtener fecha y hora actual en Guatemala
export const getGuatemalaDateTime = () => {
  return new Date().toLocaleString('es-GT', { timeZone: GUATEMALA_TIMEZONE });
};

// Obtener hora actual 'HH:MM' en Guatemala (para inputs de tipo time)
export const getGuatemalaTimeHM = () => {
  return new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: GUATEMALA_TIMEZONE
  });
};

// Type labels (categorías)
export const typeLabels = {
  fijo: 'Gasto Fijo',
  proveedor: 'Pago Proveedor',
  variable: 'Gasto Variable',
  igss: 'Gasto IGSS',
};

// Status labels
export const statusLabels = {
  pendiente: 'Pendiente',
  parcial: 'Parcial',
  pagado: 'Pagado',
  vencido: 'Vencido',
};

// Payment method labels
export const paymentMethodLabels = [
  'Efectivo',
  'Transferencia bancaria',
  'Tarjeta de crédito',
  'Tarjeta de débito',
  'Cheque'
];

// Role labels
export const roleLabels = {
  superadmin: 'Super Admin',
  admin: 'Administrador',
  usuario: 'Usuario',
  optica: 'Óptica',
  administrador_igss: 'Administrador IGSS',
};

// Patient referral institution labels
export const referralInstitutionLabels = {
  particular: 'Particular',
  igss: 'IGSS',
  seguro_privado: 'Seguro Privado',
  otra: 'Otra Institución',
};

// Patient gender labels
export const genderLabels = {
  masculino: 'Masculino',
  femenino: 'Femenino',
  otro: 'Otro',
};

// Calculate age from birth date
export const calculateAge = (birthDate) => {
  if (!birthDate) return 0;
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return Math.max(0, age);
};

// Optica - Contact Lens Types
export const contactLensTypeLabels = {
  esferico: 'Esférico',
  torico: 'Tórico',
  multifocal: 'Multifocal',
  cosmetico: 'Cosmético',
};

// Optica - Payment Methods
export const opticaPaymentMethodLabels = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
  cheque: 'Cheque',
  mixto: 'Mixto',
};

// Optica - Sale Status
export const saleStatusLabels = {
  pendiente: 'Pendiente',
  pagado: 'Pagado',
  cancelado: 'Cancelado',
};

// Security / Audit API (Solo SuperAdmin)
export const securityApi = {
  getAuditLogs: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.limit) params.append('limit', filters.limit.toString());
    if (filters.action) params.append('action', filters.action);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.date_from) params.append('date_from', filters.date_from);
    if (filters.date_to) params.append('date_to', filters.date_to);
    if (filters.search) params.append('search', filters.search);
    return axios.get(`${API_URL}/security/audit-logs?${params.toString()}`);
  },
  getAuditActions: () => axios.get(`${API_URL}/security/audit-actions`),
  getSecurityStatus: () => axios.get(`${API_URL}/security/status`),
};

// Audit Action Labels (Etiquetas en español)
export const auditActionLabels = {
  LOGIN_SUCCESS: 'Inicio de sesión exitoso',
  LOGIN_FAILED: 'Intento de login fallido',
  LOGOUT: 'Cierre de sesión',
  PASSWORD_CHANGE: 'Cambio de contraseña',
  USER_CREATED: 'Usuario creado',
  USER_UPDATED: 'Usuario actualizado',
  USER_DELETED: 'Usuario eliminado',
  USER_ACTIVATED: 'Usuario activado',
  USER_DEACTIVATED: 'Usuario desactivado',
  EXPENSE_CREATED: 'Gasto creado',
  EXPENSE_UPDATED: 'Gasto actualizado',
  EXPENSE_DELETED: 'Gasto eliminado',
  PAYMENT_CREATED: 'Pago registrado',
  PAYMENT_DELETED: 'Pago eliminado',
  AUTHORIZATION_EXECUTED: 'Autorización ejecutada',
  FIXED_EXPENSE_CREATED: 'Gasto fijo creado',
  FIXED_EXPENSE_UPDATED: 'Gasto fijo actualizado',
  FIXED_EXPENSE_DELETED: 'Gasto fijo eliminado',
  SURGERY_CREATED: 'Cirugía creada',
  SURGERY_UPDATED: 'Cirugía actualizada',
  SURGERY_CANCELLED: 'Cirugía cancelada',
  PATIENT_CREATED: 'Paciente creado',
  PATIENT_UPDATED: 'Paciente actualizado',
  PATIENT_DELETED: 'Paciente eliminado',
  PRODUCT_DELETED: 'Producto eliminado de inventario',
  PRODUCT_DELETED_FORCE: '⚠️ Producto eliminado FORZADAMENTE (con movimientos)',
  PRODUCT_IMPORTED: 'Productos importados',
};

// ==================== API DE INVENTARIO ====================
export const inventarioApi = {
  // Panel / Dashboard
  getPanel: () => axios.get(`${API_URL}/inventario/panel`),
  getAlertas: () => axios.get(`${API_URL}/inventario/alertas`),
  getConfig: () => axios.get(`${API_URL}/inventario/config`),
  updateConfig: (data) => axios.put(`${API_URL}/inventario/config`, data),
  
  // Bodegas
  getBodegas: (params) => axios.get(`${API_URL}/inventario/bodegas`, { params }),
  createBodega: (data) => axios.post(`${API_URL}/inventario/bodegas`, data),
  updateBodega: (id, data) => axios.put(`${API_URL}/inventario/bodegas/${id}`, data),
  deleteBodega: (id) => axios.delete(`${API_URL}/inventario/bodegas/${id}`),
  
  // Proveedores (wrapper para inventario)
  getProveedores: () => axios.get(`${API_URL}/suppliers`),
  
  // Categorías
  getCategorias: (params) => axios.get(`${API_URL}/inventario/categorias`, { params }),
  createCategoria: (data) => axios.post(`${API_URL}/inventario/categorias`, data),
  updateCategoria: (id, data) => axios.put(`${API_URL}/inventario/categorias/${id}`, data),
  deleteCategoria: (id) => axios.delete(`${API_URL}/inventario/categorias/${id}`),
  
  // Productos
  getProductos: (params) => axios.get(`${API_URL}/inventario/productos`, { params }),
  getProducto: (id) => axios.get(`${API_URL}/inventario/productos/${id}`),
  createProducto: (data) => axios.post(`${API_URL}/inventario/productos`, data),
  updateProducto: (id, data) => axios.put(`${API_URL}/inventario/productos/${id}`, data),
  deleteProducto: (id, force = false) => axios.delete(`${API_URL}/inventario/productos/${id}`, { params: { force } }),
  cambiarEstadoProducto: (id, activo) => axios.patch(`${API_URL}/inventario/productos/${id}/estado`, { activo }),
  importarProductosPreview: (formData) => axios.post(`${API_URL}/inventario/productos/importar/preview`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  importarProductos: (formData) => axios.post(`${API_URL}/inventario/productos/importar`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  
  // Existencias
  getExistencias: (params) => axios.get(`${API_URL}/inventario/existencias`, { params }),
  getExistenciasMatriz: (params) => axios.get(`${API_URL}/inventario/existencias/matriz`, { params }),
  getExistenciasProducto: (productoId) => axios.get(`${API_URL}/inventario/existencias/${productoId}`),
  
  // Lotes
  getLotes: (params) => axios.get(`${API_URL}/inventario/lotes`, { params }),
  darBajaLote: (id, data) => axios.post(`${API_URL}/inventario/lotes/${id}/baja`, data),
  
  // Movimientos / Kardex
  getMovimientos: (params) => axios.get(`${API_URL}/inventario/movimientos`, { params }),
  getKardexProducto: (productoId, params) => axios.get(`${API_URL}/inventario/kardex/${productoId}`, { params }),
  
  // Entrada y Ajuste
  registrarEntrada: (data) => axios.post(`${API_URL}/inventario/entrada`, data),
  registrarAjuste: (data) => axios.post(`${API_URL}/inventario/ajuste`, data),
  
  // Órdenes de Compra
  getOrdenes: (params) => axios.get(`${API_URL}/inventario/ordenes`, { params }),
  getOrden: (id) => axios.get(`${API_URL}/inventario/ordenes/${id}`),
  createOrden: (data) => axios.post(`${API_URL}/inventario/ordenes`, data),
  updateOrden: (id, data) => axios.put(`${API_URL}/inventario/ordenes/${id}`, data),
  autorizarOrden: (id) => axios.patch(`${API_URL}/inventario/ordenes/${id}/autorizar`),
  cancelarOrden: (id) => axios.patch(`${API_URL}/inventario/ordenes/${id}/cancelar`),
  sugerirBajoMinimo: () => axios.get(`${API_URL}/inventario/ordenes/sugerir-bajo-minimo`),
  
  // Recepciones
  getRecepciones: (params) => axios.get(`${API_URL}/inventario/recepciones`, { params }),
  createRecepcion: (data) => axios.post(`${API_URL}/inventario/recepciones`, data),
  
  // Transferencias
  getTransferencias: (params) => axios.get(`${API_URL}/inventario/transferencias`, { params }),
  createTransferencia: (data) => axios.post(`${API_URL}/inventario/transferencias`, data),
  
  // Tomas Físicas
  getTomas: (params) => axios.get(`${API_URL}/inventario/tomas`, { params }),
  createToma: (data) => axios.post(`${API_URL}/inventario/tomas`, data),
  actualizarConteo: (id, items) => axios.put(`${API_URL}/inventario/tomas/${id}/conteo`, items),
  cerrarToma: (id) => axios.post(`${API_URL}/inventario/tomas/${id}/cerrar`),
  getHojaConteo: (id) => axios.get(`${API_URL}/inventario/tomas/${id}/hoja-conteo`),
  
  // Reportes
  getReporteRentabilidadCategorias: (params) => axios.get(`${API_URL}/inventario/reportes/rentabilidad-categorias`, { params }),
  getReporteRentabilidadHistorico: (params) => axios.get(`${API_URL}/inventario/reportes/rentabilidad-historico`, { params }),
  
  // Sociedades - Catálogo
  getSociedades: (activo) => axios.get(`${API_URL}/inventario/sociedades/catalogo`, { params: activo !== undefined ? { activo } : {} }),
  getSociedad: (id) => axios.get(`${API_URL}/inventario/sociedades/catalogo/${id}`),
  createSociedad: (data) => axios.post(`${API_URL}/inventario/sociedades/catalogo`, data),
  updateSociedad: (id, data) => axios.put(`${API_URL}/inventario/sociedades/catalogo/${id}`, data),
  deleteSociedad: (id) => axios.delete(`${API_URL}/inventario/sociedades/catalogo/${id}`),
  getProductosSociedad: (sociedadId) => axios.get(`${API_URL}/inventario/sociedades/catalogo/${sociedadId}/productos`),
};

// ==================== API DE PUNTO DE VENTA (POS) ====================
export const ventasApi = {
  // Búsqueda de productos para POS
  buscarProductos: (params) => axios.get(`${API_URL}/ventas/productos`, { params }),
  
  // Productos más vendidos para acceso rápido
  getProductosRapidos: (params) => axios.get(`${API_URL}/ventas/productos-rapidos`, { params }),
  
  // Obtener bodega predeterminada para POS
  getBodegaPOS: () => axios.get(`${API_URL}/ventas/bodega-pos`),
  
  // Verificar stock antes de vender
  verificarStock: (data) => axios.post(`${API_URL}/ventas/verificar-stock`, data),
  
  // CRUD de ventas
  crear: (data) => axios.post(`${API_URL}/ventas`, data),
  getAll: (params) => axios.get(`${API_URL}/ventas`, { params }),
  getById: (id) => axios.get(`${API_URL}/ventas/${id}`),
  getVentasHoy: () => axios.get(`${API_URL}/ventas/hoy`),
  getResumenDia: (fecha) => axios.get(`${API_URL}/ventas/resumen-dia`, { params: { fecha } }),
  
  // Anular venta
  anular: (id, data) => axios.post(`${API_URL}/ventas/${id}/anular`, data),
  
  // Ticket para impresión
  getTicket: (id) => axios.get(`${API_URL}/ventas/${id}/ticket`),
};

// Instancia de axios configurada para usar en componentes
const api = axios.create({
  baseURL: API_URL
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
