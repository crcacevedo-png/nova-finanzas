import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Gastos from './pages/Gastos';
import Usuarios from './pages/Usuarios';
import HistorialPagos from './pages/HistorialPagos';
import CuentasBancarias from './pages/CuentasBancarias';
import Proveedores from './pages/Proveedores';
import GastosFijos from './pages/GastosFijos';
import Pacientes from './pages/Pacientes';
import UnidadesIGSS from './pages/UnidadesIGSS';
// Módulo Óptica
import OpticaInventario from './pages/OpticaInventario';
import OpticaVentas from './pages/OpticaVentas';
import OpticaCompras from './pages/OpticaCompras';
import Medicos from './pages/Medicos';
import TiposLente from './pages/TiposLente';
import AutorizacionesPendientes from './pages/AutorizacionesPendientes';
import SalaOperaciones from './pages/SalaOperaciones';
import AuditLogs from './pages/AuditLogs';
import EvaluacionOftalmologica from './pages/EvaluacionOftalmologica';
import Caja from './pages/Caja';
import Agenda from './pages/Agenda';
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
      <Route 
        path="/configuracion/proveedores" 
        element={
          <ProtectedRoute>
            <Proveedores />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/configuracion/gastos-fijos" 
        element={
          <ProtectedRoute requiredPermission="view_payment_authorizations">
            <GastosFijos />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/pacientes" 
        element={
          <ProtectedRoute requiredPermission="view_patients">
            <Pacientes />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/configuracion/unidades-igss" 
        element={
          <ProtectedRoute requiredPermission="manage_igss_units">
            <UnidadesIGSS />
          </ProtectedRoute>
        } 
      />

      {/* Módulo Óptica - Solo accesible para roles optica y superadmin */}
      <Route 
        path="/optica/inventario" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <OpticaInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/optica/ventas" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <OpticaVentas />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/optica/compras" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <OpticaCompras />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/optica/medicos" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <Medicos />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/optica/tipos-lente" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <TiposLente />
          </ProtectedRoute>
        } 
      />

      {/* Autorizaciones Pendientes - Admin y SuperAdmin */}
      <Route 
        path="/autorizaciones-pendientes" 
        element={
          <ProtectedRoute requiredPermission="view_payment_authorizations">
            <AutorizacionesPendientes />
          </ProtectedRoute>
        } 
      />

      {/* Sala de Operaciones - Todos los roles */}
      <Route 
        path="/sala-operaciones" 
        element={
          <ProtectedRoute>
            <SalaOperaciones />
          </ProtectedRoute>
        } 
      />

      {/* Registro de Auditoría - Solo SuperAdmin */}
      <Route 
        path="/auditoria" 
        element={
          <ProtectedRoute requiredPermission="view_audit_logs">
            <AuditLogs />
          </ProtectedRoute>
        } 
      />

      {/* Evaluación Oftalmológica - Admin y SuperAdmin pueden editar, Usuario solo lectura */}
      <Route 
        path="/evaluacion-oftalmologica" 
        element={
          <ProtectedRoute>
            <EvaluacionOftalmologica />
          </ProtectedRoute>
        } 
      />

      {/* Caja - Control financiero del área clínica */}
      <Route 
        path="/caja" 
        element={
          <ProtectedRoute requiredPermission="view_payment_authorizations">
            <Caja />
          </ProtectedRoute>
        } 
      />

      {/* Agenda - Citas de pacientes */}
      <Route 
        path="/agenda" 
        element={
          <ProtectedRoute>
            <Agenda />
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
