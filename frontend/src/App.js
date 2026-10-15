import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import DashboardFinanciero from './pages/DashboardFinanciero';
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
import OpticaPOS from './pages/OpticaPOS';
import OpticaCompras from './pages/OpticaCompras';
import OpticaDashboard from './pages/OpticaDashboard';
import Medicos from './pages/Medicos';
import TiposLente from './pages/TiposLente';
import LentesContacto from './pages/LentesContacto';
import AutorizacionesPendientes from './pages/AutorizacionesPendientes';
import SalaOperaciones from './pages/SalaOperaciones';
import AuditLogs from './pages/AuditLogs';
import EvaluacionOftalmologica from './pages/EvaluacionOftalmologica';
import Caja from './pages/Caja';
import Agenda from './pages/Agenda';
import CRMCirugias from './pages/CRMCirugias';
import ImportarPacientes from './pages/ImportarPacientes';
import ImportarEvaluaciones from './pages/ImportarEvaluaciones';
import LaboratorioPruebas from './pages/LaboratorioPruebas';
import CuentasCobrarOptica from './pages/CuentasCobrarOptica';
import CuentasCobrarFinanzas from './pages/CuentasCobrarFinanzas';
import ErrorBoundary from './components/ErrorBoundary';
// Módulo Inventario
import PanelInventario from './pages/inventario/PanelInventario';
import ProductosInventario from './pages/inventario/Productos';
import LotesInventario from './pages/inventario/Lotes';
import MovimientosInventario from './pages/inventario/Movimientos';
import BodegasInventario from './pages/inventario/Bodegas';
import CategoriasInventario from './pages/inventario/Categorias';
import ReporteRentabilidad from './pages/inventario/ReporteRentabilidad';
import Sociedades from './pages/inventario/Sociedades';
// Punto de Venta (POS)
import PuntoVenta from './pages/PuntoVenta';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, requiredPermission, requiredRole, requiredMenu }) => {
  const { isAuthenticated, loading, hasPermission, user, isMenuEnabled, menusLoaded } = useAuth();

  const waitingForMenus = requiredMenu && user?.role !== 'superadmin' && !menusLoaded;

  if (loading || waitingForMenus) {
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

  // Determinar página de redirección basada en rol
  const defaultPage = user?.role === 'superadmin' ? '/dashboard' : '/pacientes';

  // Verificar rol requerido (ej: 'superadmin')
  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to={defaultPage} replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to={defaultPage} replace />;
  }

  // Acceso por módulo/menú habilitado para el rol (configurable desde Roles/Menús)
  if (requiredMenu && !isMenuEnabled(requiredMenu)) {
    return <Navigate to={defaultPage} replace />;
  }

  return children;
};

// Public Route Component (redirect if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();

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
    // Superadmin va al dashboard, otros usuarios van a pacientes
    const redirectTo = user?.role === 'superadmin' ? '/dashboard' : '/pacientes';
    return <Navigate to={redirectTo} replace />;
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
          <ProtectedRoute requiredRole="superadmin">
            <Dashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/dashboard-financiero" 
        element={
          <ProtectedRoute requiredRole="superadmin">
            <DashboardFinanciero />
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
        path="/igss/unidades" 
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
        path="/optica/dashboard" 
        element={
          <ProtectedRoute requiredRole="superadmin">
            <OpticaDashboard />
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
        path="/optica/punto-venta" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <OpticaPOS />
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
      <Route 
        path="/optica/lentes-contacto" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <LentesContacto />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/optica/cuentas-cobrar" 
        element={
          <ProtectedRoute requiredPermission="view_optica">
            <CuentasCobrarOptica />
          </ProtectedRoute>
        } 
      />

      {/* Cuentas por Cobrar - Finanzas/Clínica */}
      <Route 
        path="/cuentas-cobrar-finanzas" 
        element={
          <ProtectedRoute>
            <CuentasCobrarFinanzas />
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

      {/* Sala de Operaciones - Acceso configurable por rol desde Roles/Menús */}
      <Route 
        path="/sala-operaciones" 
        element={
          <ProtectedRoute requiredMenu="sala_operaciones">
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
          <ProtectedRoute requiredPermission="view_evaluacion">
            <EvaluacionOftalmologica />
          </ProtectedRoute>
        } 
      />

      {/* CRM Cirugías - Gestión de candidatos a cirugía */}
      <Route 
        path="/crm-cirugias" 
        element={
          <ProtectedRoute>
            <CRMCirugias />
          </ProtectedRoute>
        } 
      />

      {/* Caja - Control financiero del área clínica */}
      <Route 
        path="/caja" 
        element={
          <ProtectedRoute requiredPermission="manage_caja">
            <Caja />
          </ProtectedRoute>
        } 
      />

      {/* Agenda - Citas de pacientes */}
      <Route 
        path="/agenda" 
        element={
          <ProtectedRoute requiredPermission="view_agenda">
            <Agenda />
          </ProtectedRoute>
        } 
      />

      {/* ==================== PUNTO DE VENTA (POS) ==================== */}
      <Route 
        path="/punto-venta" 
        element={
          <ProtectedRoute>
            <PuntoVenta />
          </ProtectedRoute>
        } 
      />

      {/* ==================== MÓDULO DE INVENTARIO ==================== */}
      <Route 
        path="/inventario" 
        element={
          <ProtectedRoute>
            <PanelInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/productos" 
        element={
          <ProtectedRoute>
            <ProductosInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/lotes" 
        element={
          <ProtectedRoute>
            <LotesInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/movimientos" 
        element={
          <ProtectedRoute>
            <MovimientosInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/bodegas" 
        element={
          <ProtectedRoute>
            <BodegasInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/categorias" 
        element={
          <ProtectedRoute>
            <CategoriasInventario />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/inventario/rentabilidad" 
        element={
          <ProtectedRoute requiredRole="superadmin">
            <ReporteRentabilidad />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/sociedades" 
        element={
          <ProtectedRoute requiredPermission="manage_users">
            <Sociedades />
          </ProtectedRoute>
        } 
      />

      {/* Importación Masiva de Pacientes */}
      <Route 
        path="/importar-pacientes" 
        element={
          <ProtectedRoute requiredPermission="import_patients">
            <ImportarPacientes />
          </ProtectedRoute>
        } 
      />

      {/* Importación Masiva de Evaluaciones */}
      <Route 
        path="/importar-evaluaciones" 
        element={
          <ProtectedRoute requiredPermission="import_patients">
            <ImportarEvaluaciones />
          </ProtectedRoute>
        } 
      />

      {/* Laboratorio de Pruebas - Solo SuperAdmin, solo desarrollo */}
      <Route 
        path="/laboratorio-pruebas" 
        element={
          <ProtectedRoute requiredPermission="view_audit_logs">
            <LaboratorioPruebas />
          </ProtectedRoute>
        } 
      />

      {/* Default Redirect - basado en rol */}
      <Route path="/" element={<DefaultRedirect />} />
      <Route path="*" element={<DefaultRedirect />} />
    </Routes>
  );
}

// Componente para redirección por defecto basada en rol
const DefaultRedirect = () => {
  const { user, isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // Superadmin va al dashboard, otros usuarios van a pacientes
  const redirectTo = user?.role === 'superadmin' ? '/dashboard' : '/pacientes';
  return <Navigate to={redirectTo} replace />;
};

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
