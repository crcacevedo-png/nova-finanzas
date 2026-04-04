import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Gastos from './pages/Gastos';
import Usuarios from './pages/Usuarios';
import HistorialPagos from './pages/HistorialPagos';
import PagosPorVencer from './pages/PagosPorVencer';
import CuentasBancarias from './pages/CuentasBancarias';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, requiredPermission }) => {
  const { isAuthenticated, loading, hasPermission } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-[#9FE1CB] border-t-[#0F6E56] rounded-full animate-spin" />
          <p className="text-slate-500">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Public Route Component (redirect if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-[#9FE1CB] border-t-[#0F6E56] rounded-full animate-spin" />
          <p className="text-slate-500">Cargando...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route 
        path="/login" 
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        } 
      />

      {/* Protected Routes */}
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/gastos" 
        element={
          <ProtectedRoute>
            <Gastos />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/historial-pagos" 
        element={
          <ProtectedRoute>
            <HistorialPagos />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/pagos-por-vencer" 
        element={
          <ProtectedRoute>
            <PagosPorVencer />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/usuarios" 
        element={
          <ProtectedRoute requiredPermission="view_user_management">
            <Usuarios />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/configuracion/cuentas-bancarias" 
        element={
          <ProtectedRoute requiredPermission="view_user_management">
            <CuentasBancarias />
          </ProtectedRoute>
        } 
      />

      {/* Default Redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
