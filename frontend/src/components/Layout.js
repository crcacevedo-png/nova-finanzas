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
  Building
} from 'lucide-react';
import { Badge } from './ui/badge';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png";

const roleLabels = {
  superadmin: 'Super Admin',
  admin: 'Administrador',
  usuario: 'Usuario'
};

const Layout = ({ children }) => {
  const { user, logout, canViewUserManagement } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(location.pathname.startsWith('/configuracion'));

  const isSuperAdmin = user?.role === 'superadmin';
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', testId: 'nav-dashboard' },
    { path: '/pacientes', icon: UserRound, label: 'Pacientes', testId: 'nav-pacientes' },
    { path: '/gastos', icon: Receipt, label: 'Gastos', testId: 'nav-gastos' },
    { path: '/historial-pagos', icon: History, label: 'Historial de pagos', testId: 'nav-historial-pagos' },
    { path: '/pagos-por-vencer', icon: Clock, label: 'Pagos por vencer', testId: 'nav-pagos-por-vencer' },
  ];

  // Agregar Autorización de Pagos para Admin y SuperAdmin
  if (isAdminOrSuperAdmin) {
    navItems.push({ 
      path: '/autorizacion-pagos', 
      icon: FileCheck, 
      label: 'Autorización de pagos', 
      testId: 'nav-autorizacion-pagos' 
    });
  }

  if (canViewUserManagement()) {
    navItems.push({ 
      path: '/usuarios', 
      icon: Users, 
      label: 'Gestión de usuarios', 
      testId: 'nav-usuarios' 
    });
  }

  // Config sub-items (Admin y SuperAdmin)
  const configItems = [];
  
  // Proveedores - disponible para Admin y SuperAdmin
  if (isAdminOrSuperAdmin) {
    configItems.push({ 
      path: '/configuracion/proveedores', 
      icon: Truck, 
      label: 'Proveedores', 
      testId: 'nav-proveedores' 
    });
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
      usuario: 'badge-usuario'
    };
    return classes[role] || 'badge-usuario';
  };

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
          {navItems.map((item) => (
            <NavLink key={item.path} item={item} />
          ))}
          
          {/* Configuration Section - Admin y SuperAdmin */}
          {isAdminOrSuperAdmin && configItems.length > 0 && (
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
