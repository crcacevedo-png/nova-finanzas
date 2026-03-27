import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState({});

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
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
    setPermissions(userData.permissions || {});
    
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
    setPermissions({});
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
      isAuthenticated: !!user
    }}>
      {children}
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
