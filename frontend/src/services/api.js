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
    if (filters.categoria) params.append('categoria', filters.categoria);
    if (filters.estado) params.append('estado', filters.estado);
    return axios.get(`${API_URL}/expenses?${params.toString()}`);
  },
  getById: (id) => axios.get(`${API_URL}/expenses/${id}`),
  create: (data) => axios.post(`${API_URL}/expenses`, data),
  update: (id, data) => axios.put(`${API_URL}/expenses/${id}`, data),
  delete: (id) => axios.delete(`${API_URL}/expenses/${id}`),
  markAsPaid: (id) => axios.put(`${API_URL}/expenses/${id}/pay`),
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
  return new Date(dateString).toLocaleDateString('es-GT', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

// Category labels
export const categoryLabels = {
  gastos_fijos: 'Gastos Fijos',
  pagos_proveedores: 'Pagos Proveedores',
  gastos_variables: 'Gastos Variables',
};

// Status labels
export const statusLabels = {
  pagado: 'Pagado',
  pendiente: 'Pendiente',
};

// Role labels
export const roleLabels = {
  superadmin: 'Super Admin',
  admin: 'Administrador',
  usuario: 'Usuario',
};
