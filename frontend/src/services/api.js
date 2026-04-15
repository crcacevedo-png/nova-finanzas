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
  getAll: (status = null) => {
    const params = status ? `?status=${status}` : '';
    return axios.get(`${API_URL}/payment-authorizations${params}`);
  },
  getById: (id) => axios.get(`${API_URL}/payment-authorizations/${id}`),
  getExpensesPendingAuth: () => axios.get(`${API_URL}/expenses-pending-authorization`),
  create: (data) => axios.post(`${API_URL}/payment-authorizations`, data),
  update: (id, data) => axios.put(`${API_URL}/payment-authorizations/${id}`, data),
  execute: (id) => axios.post(`${API_URL}/payment-authorizations/${id}/execute`),
  cancel: (id) => axios.post(`${API_URL}/payment-authorizations/${id}/cancel`),
  delete: (id) => axios.delete(`${API_URL}/payment-authorizations/${id}`),
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
  getById: (id) => axios.get(`${API_URL}/igss-units/${id}`),
  create: (data) => axios.post(`${API_URL}/igss-units`, data),
  update: (id, data) => axios.put(`${API_URL}/igss-units/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/igss-units/${id}`),
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
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.age_from) params.append('age_from', filters.age_from.toString());
    if (filters.age_to) params.append('age_to', filters.age_to.toString());
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
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.dateFrom) params.append('dateFrom', filters.dateFrom);
    if (filters.dateTo) params.append('dateTo', filters.dateTo);
    return `${API_URL}/patients/export/excel?${params.toString()}`;
  },
  exportPdf: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.referral_institution) params.append('referral_institution', filters.referral_institution);
    if (filters.gender) params.append('gender', filters.gender);
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

// Format date helper
export const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('es-GT', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
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
