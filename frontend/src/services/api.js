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

// Format currency helper
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('es-GT', {
    style: 'currency',
    currency: 'GTQ',
    minimumFractionDigits: 2,
  }).format(amount);
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
