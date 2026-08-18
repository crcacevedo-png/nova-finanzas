import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useInactivityTimeout } from '../hooks/useInactivityTimeout';
import { InactivityWarning } from '../components/InactivityWarning';

const AuthContext = createContext(null);

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Configuración de timeout de inactividad (SEC-007)
// 30 minutos por defecto, configurable via variable de entorno
const INACTIVITY_TIMEOUT = parseInt(process.env.REACT_APP_INACTIVITY_TIMEOUT || '30', 10) * 60 * 1000;
const WARNING_TIME = 5 * 60 * 1000; // 5 minutos de advertencia

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState({});
  const [logoutReason, setLogoutReason] = useState(null);

  // Función de logout
  const logout = useCallback(async (reason = null) => {
    // Intentar invalidar token en el servidor
    if (token) {
      try {
        await axios.post(`${API_URL}/auth/logout`);
      } catch (error) {
        // Ignorar errores de logout en servidor
        console.log('Logout del servidor falló, continuando con logout local');
      }
    }
    
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
    setPermissions({});
    setLogoutReason(reason);
  }, [token]);

  // Hook de inactividad (SEC-007)
  const {
    showWarning,
    remainingTimeFormatted,
    extendSession
  } = useInactivityTimeout({
    timeout: INACTIVITY_TIMEOUT,
    warningTime: WARNING_TIME,
    enabled: !!user, // Solo activar si hay usuario logueado
    onTimeout: () => {
      console.log('Sesión cerrada por inactividad');
      logout('inactivity');
    },
    onWarning: () => {
      console.log('Advertencia de inactividad mostrada');
    }
  });

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`);
      setUser(response.data);
      setPermissions(response.data.permissions || {});
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { username, password });
    const { access_token, user: userData, must_change_password, is_new_device } = response.data;
    
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
    setPermissions(userData.permissions || {});
    setLogoutReason(null); // Limpiar razón de logout anterior
    
    return { 
      user: userData, 
      must_change_password: must_change_password || false,
      is_new_device: is_new_device || false
    };
  };

  const hasRole = (roles) => {
    if (!user) return false;
    if (typeof roles === 'string') return user.role === roles;
    return roles.includes(user.role);
  };

  const hasPermission = (permission) => {
    return permissions[permission] === true;
  };

  const canCreateExpenses = () => hasPermission('create_expenses');
  const canEditExpenses = () => hasPermission('edit_expenses');
  const canDeleteExpenses = () => hasPermission('delete_expenses');
  const canRegisterPayments = () => hasPermission('register_payments');
  const canDeletePayments = () => hasPermission('delete_payments');
  const canManageUsers = () => hasPermission('manage_users');
  const canViewUserManagement = () => hasPermission('view_user_management');
  const canExportReports = () => hasPermission('export_reports');

  // Manejar "Continuar trabajando" en el modal de inactividad
  const handleContinueSession = () => {
    extendSession();
  };

  // Manejar "Cerrar sesión ahora" en el modal de inactividad
  const handleLogoutNow = () => {
    logout('manual');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      permissions,
      login,
      logout,
      hasRole,
      hasPermission,
      canCreateExpenses,
      canEditExpenses,
      canDeleteExpenses,
      canRegisterPayments,
      canDeletePayments,
      canManageUsers,
      canViewUserManagement,
      canExportReports,
      isAuthenticated: !!user,
      logoutReason, // Para mostrar mensaje en login si fue por inactividad
      inactivityTimeout: INACTIVITY_TIMEOUT / 60000 // En minutos, para mostrar en UI
    }}>
      {children}
      
      {/* Modal de advertencia de inactividad */}
      <InactivityWarning
        open={showWarning && !!user}
        remainingTime={remainingTimeFormatted}
        onContinue={handleContinueSession}
        onLogout={handleLogoutNow}
      />
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
