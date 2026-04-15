import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  Receipt, 
  History, 
  Clock, 
  Users,
  LogOut,
  Menu,
  X,
  Settings,
  Building2,
  ChevronDown,
  ChevronRight,
  FileCheck,
  Truck,
  CalendarClock,
  UserRound,
  Building,
  Glasses,
  ShoppingCart,
  Stethoscope,
  Eye,
  Package,
  Wallet
} from 'lucide-react';
import { Badge } from './ui/badge';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png";

const roleLabels = {
  superadmin: 'Super Admin',
  admin: 'Administrador',
  usuario: 'Usuario',
  optica: 'Óptica'
};

const Layout = ({ children }) => {
  const { user, logout, canViewUserManagement, hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(location.pathname.startsWith('/configuracion'));
  const [opticaOpen, setOpticaOpen] = useState(location.pathname.startsWith('/optica'));
  const [finanzasOpen, setFinanzasOpen] = useState(
    ['/gastos', '/historial-pagos', '/pagos-por-vencer', '/autorizacion-pagos'].some(p => location.pathname.startsWith(p))
  );

  const isSuperAdmin = user?.role === 'superadmin';
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';
  const canViewOptica = hasPermission('view_optica');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Items principales del sidebar
  const navItems = [];
  
  // Dashboard - Solo para roles que no sean optica
  if (user?.role !== 'optica') {
    navItems.push({ path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', testId: 'nav-dashboard' });
  }
  
  // Pacientes - Visible para todos
  navItems.push({ path: '/pacientes', icon: UserRound, label: 'Pacientes', testId: 'nav-pacientes' });

  // Finanzas sub-items (visible para todos los roles autenticados)
  // Finanzas sub-items (NO visible para optica)
  const finanzasItems = user?.role !== 'optica' ? [
    { path: '/gastos', icon: Receipt, label: 'Gastos', testId: 'nav-gastos' },
    { path: '/historial-pagos', icon: History, label: 'Historial de pagos', testId: 'nav-historial-pagos' },
    { path: '/pagos-por-vencer', icon: Clock, label: 'Pagos por vencer', testId: 'nav-pagos-por-vencer' },
  ] : [];
  
  // Agregar Autorización de Pagos solo para Admin y SuperAdmin
  if (isAdminOrSuperAdmin) {
    finanzasItems.push({ 
      path: '/autorizacion-pagos', 
      icon: FileCheck, 
      label: 'Autorización de pagos', 
      testId: 'nav-autorizacion-pagos' 
    });
  }

  // Config sub-items
  const configItems = [];
  
  // Proveedores - disponible para Admin, SuperAdmin y Optica
  if (isAdminOrSuperAdmin || canViewOptica) {
    configItems.push({ 
      path: '/configuracion/proveedores', 
      icon: Truck, 
      label: 'Proveedores', 
      testId: 'nav-proveedores' 
    });
  }
  
  // Gastos Fijos - solo Admin y SuperAdmin
  if (isAdminOrSuperAdmin) {
    configItems.push({ 
      path: '/configuracion/gastos-fijos', 
      icon: CalendarClock, 
      label: 'Gastos Fijos', 
      testId: 'nav-gastos-fijos' 
    });
  }
  
  // Cuentas Bancarias - solo SuperAdmin
  if (isSuperAdmin) {
    configItems.push({ 
      path: '/configuracion/cuentas-bancarias', 
      icon: Building2, 
      label: 'Cuentas Bancarias', 
      testId: 'nav-cuentas-bancarias' 
    });
    configItems.push({ 
      path: '/configuracion/unidades-igss', 
      icon: Building, 
      label: 'Unidades IGSS', 
      testId: 'nav-unidades-igss' 
    });
  }

  const getRoleBadgeClass = (role) => {
    const classes = {
      superadmin: 'badge-superadmin',
      admin: 'badge-admin',
      usuario: 'badge-usuario',
      optica: 'badge-optica'
    };
    return classes[role] || 'badge-usuario';
  };

  // Optica sub-items (solo para rol optica y superadmin) - Sin Médicos
  const opticaItems = canViewOptica ? [
    { path: '/optica/inventario', icon: Package, label: 'Inventario', testId: 'nav-optica-inventario' },
    { path: '/optica/ventas', icon: ShoppingCart, label: 'Ventas', testId: 'nav-optica-ventas' },
    { path: '/optica/compras', icon: Receipt, label: 'Compras', testId: 'nav-optica-compras' },
    { path: '/optica/tipos-lente', icon: Eye, label: 'Tipos de Lente', testId: 'nav-optica-tipos-lente' },
  ] : [];

  const NavLink = ({ item }) => {
    const isActive = location.pathname === item.path;
    const Icon = item.icon;
    
    return (
      <Link
        to={item.path}
        className={`sidebar-item flex items-center gap-3 mx-2 ${isActive ? 'active' : ''}`}
        onClick={() => setSidebarOpen(false)}
        data-testid={item.testId}
      >
        <Icon className={`w-5 h-5 icon ${isActive ? 'opacity-100' : 'opacity-60'}`} />
        <span className="font-medium text-sm">{item.label}</span>
      </Link>
    );
  };

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--bg-page)' }}>
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-[240px] sidebar-teal text-white
          flex flex-col
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          sidebar-dark
        `}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="py-6 px-5 flex items-center justify-between border-b border-white/10">
          <Link to="/dashboard">
            <img 
              src={LOGO_URL}
              alt="NovaVision"
              className="w-44 h-auto"
              data-testid="sidebar-logo"
            />
          </Link>
          <button 
            className="lg:hidden p-1 hover:bg-[#134840] rounded transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5 text-white/60" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 space-y-1 overflow-y-auto">
          {/* 1. Dashboard y 2. Pacientes */}
          {navItems.map((item) => (
            <NavLink key={item.path} item={item} />
          ))}

          {/* 3. Optica Section - Solo para optica y superadmin */}
          {canViewOptica && opticaItems.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setOpticaOpen(!opticaOpen)}
                className={`sidebar-item flex items-center justify-between w-full mx-2 ${
                  location.pathname.startsWith('/optica') ? 'active' : ''
                }`}
                data-testid="nav-optica"
              >
                <div className="flex items-center gap-3">
                  <Glasses className={`w-5 h-5 icon ${location.pathname.startsWith('/optica') ? 'opacity-100' : 'opacity-60'}`} />
                  <span className="font-medium text-sm">Óptica</span>
                </div>
                {opticaOpen ? (
                  <ChevronDown className="w-4 h-4 opacity-60" />
                ) : (
                  <ChevronRight className="w-4 h-4 opacity-60" />
                )}
              </button>
              
              {opticaOpen && (
                <div className="ml-4 mt-1 space-y-1">
                  {opticaItems.map((item) => (
                    <NavLink key={item.path} item={item} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4. Finanzas Section - NO para optica */}
          {finanzasItems.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setFinanzasOpen(!finanzasOpen)}
                className={`sidebar-item flex items-center justify-between w-full mx-2 ${
                  ['/gastos', '/historial-pagos', '/pagos-por-vencer', '/autorizacion-pagos'].some(p => location.pathname.startsWith(p)) ? 'active' : ''
                }`}
                data-testid="nav-finanzas"
              >
                <div className="flex items-center gap-3">
                  <Wallet className={`w-5 h-5 icon ${['/gastos', '/historial-pagos', '/pagos-por-vencer', '/autorizacion-pagos'].some(p => location.pathname.startsWith(p)) ? 'opacity-100' : 'opacity-60'}`} />
                  <span className="font-medium text-sm">Finanzas</span>
                </div>
                {finanzasOpen ? (
                  <ChevronDown className="w-4 h-4 opacity-60" />
                ) : (
                  <ChevronRight className="w-4 h-4 opacity-60" />
                )}
              </button>
              
              {finanzasOpen && (
                <div className="ml-4 mt-1 space-y-1">
                  {finanzasItems.map((item) => (
                    <NavLink key={item.path} item={item} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 5. Médicos - Solo para optica y superadmin */}
          {canViewOptica && (
            <NavLink item={{ path: '/optica/medicos', icon: Stethoscope, label: 'Médicos', testId: 'nav-medicos' }} />
          )}

          {/* 6. Gestión de Usuarios - Solo SuperAdmin */}
          {canViewUserManagement() && (
            <NavLink item={{ path: '/usuarios', icon: Users, label: 'Gestión de usuarios', testId: 'nav-usuarios' }} />
          )}
          
          {/* 7. Configuration Section - Admin, SuperAdmin y Optica (si tiene items) */}
          {configItems.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setConfigOpen(!configOpen)}
                className={`sidebar-item flex items-center justify-between w-full mx-2 ${
                  location.pathname.startsWith('/configuracion') ? 'active' : ''
                }`}
                data-testid="nav-configuracion"
              >
                <div className="flex items-center gap-3">
                  <Settings className={`w-5 h-5 icon ${location.pathname.startsWith('/configuracion') ? 'opacity-100' : 'opacity-60'}`} />
                  <span className="font-medium text-sm">Configuración</span>
                </div>
                {configOpen ? (
                  <ChevronDown className="w-4 h-4 opacity-60" />
                ) : (
                  <ChevronRight className="w-4 h-4 opacity-60" />
                )}
              </button>
              
              {configOpen && (
                <div className="ml-4 mt-1 space-y-1">
                  {configItems.map((item) => (
                    <NavLink key={item.path} item={item} />
                  ))}
                </div>
              )}
            </div>
          )}
        </nav>

        {/* User Section */}
        <div className="border-t border-white/10 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
              style={{ background: 'linear-gradient(135deg, #0F6E56, #1D9E75)' }}
            >
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm text-white truncate">{user?.name}</p>
              <Badge className={`text-[10px] px-2 py-0.5 ${getRoleBadgeClass(user?.role)}`}>
                {roleLabels[user?.role] || user?.role}
              </Badge>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-white/50 hover:text-white hover:bg-[#134840] transition-all"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4" />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen lg:ml-0">
        {/* Header - Mobile only */}
        <header className="lg:hidden h-16 bg-white border-b flex items-center px-4" style={{ borderColor: 'var(--border-card)' }}>
          <button 
            className="p-2 hover:bg-[#EDF5F2] rounded-lg transition-colors"
            onClick={() => setSidebarOpen(true)}
            data-testid="mobile-menu-button"
          >
            <Menu className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
          </button>
          <div className="flex-1 flex justify-center">
            <img 
              src={LOGO_URL}
              alt="NovaVision"
              className="h-10 w-auto"
            />
          </div>
          <div className="w-10" />
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 lg:p-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
