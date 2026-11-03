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
  Truck,
  CalendarClock,
  UserRound,
  Building,
  Glasses,
  ShoppingCart,
  Stethoscope,
  Eye,
  Package,
  Syringe,
  Wallet,
  Calculator,
  ClipboardCheck,
  Scissors,
  Shield,
  CalendarDays,
  TrendingUp,
  Boxes,
  AlertTriangle,
  ArrowLeftRight,
  FileText,
  ClipboardList,
  Store,
  Upload,
  FlaskConical,
  CreditCard,
  CircleDot,
  Warehouse,
  Tag,
  PieChart,
  KeyRound,
  DatabaseBackup,
  Watch
} from 'lucide-react';
import { Badge } from './ui/badge';
import { ChangePasswordDialog } from './ChangePasswordDialog';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/qvzbrum6_logo%20nova%20transparente.png";

const roleLabels = {
  superadmin: 'Super Admin',
  admin: 'Administrador',
  usuario: 'Usuario',
  optica: 'Óptica'
};

const Layout = ({ children }) => {
  const { user, logout, canViewUserManagement, hasPermission, isMenuEnabled } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(location.pathname.startsWith('/configuracion'));
  const [opticaOpen, setOpticaOpen] = useState(location.pathname.startsWith('/optica'));
  const [finanzasOpen, setFinanzasOpen] = useState(
    ['/gastos', '/historial-pagos', '/autorizaciones-pendientes', '/caja', '/configuracion/gastos-fijos', '/punto-venta', '/cierre-diario'].some(p => location.pathname.startsWith(p))
  );
  const [inventarioOpen, setInventarioOpen] = useState(location.pathname.startsWith('/inventario'));
  const [igssOpen, setIgssOpen] = useState(location.pathname.startsWith('/igss'));
  
  // Estado para menús habilitados del usuario
  const [changePwdOpen, setChangePwdOpen] = useState(false);

  const isSuperAdmin = user?.role === 'superadmin';
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';
  const canViewOptica = hasPermission('view_optica');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Items principales del sidebar - Filtrados por configuración de menús
  const navItems = [];
  
  // Dashboard del Sistema - Solo SuperAdmin y si está habilitado
  if (isSuperAdmin && isMenuEnabled('dashboard')) {
    navItems.push({ path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', testId: 'nav-dashboard' });
  }
  
  // Dashboard Financiero - Solo SuperAdmin y si está habilitado
  if (isSuperAdmin && isMenuEnabled('dashboard_financiero')) {
    navItems.push({ path: '/dashboard-financiero', icon: TrendingUp, label: 'Dashboard Financiero', testId: 'nav-dashboard-financiero' });
  }
  
  // Pacientes - Visible si está habilitado
  if (isMenuEnabled('pacientes')) {
    navItems.push({ path: '/pacientes', icon: UserRound, label: 'Pacientes', testId: 'nav-pacientes' });
  }
  
  // Evaluación Oftalmológica - Visible si está habilitado
  if (isMenuEnabled('evaluacion_oftalmologica')) {
    navItems.push({ path: '/evaluacion-oftalmologica', icon: Eye, label: 'Evaluación Oftalmológica', testId: 'nav-evaluacion' });
  }
  
  // Sala de Operaciones - Visible si está habilitado
  if (isMenuEnabled('sala_operaciones')) {
    navItems.push({ path: '/sala-operaciones', icon: Scissors, label: 'Sala de operaciones', testId: 'nav-sala-operaciones' });
  }
  if (isMenuEnabled('quirofano_insumos')) {
    navItems.push({ path: '/quirofano/insumos-equipos', icon: Package, label: 'Insumos y Equipos Qx', testId: 'nav-quirofano-insumos' });
  }
  if (isMenuEnabled('quirofano_anestesia')) {
    navItems.push({ path: '/quirofano/anestesia', icon: Syringe, label: 'Proced. de Anestesia', testId: 'nav-quirofano-anestesia' });
  }
  
  // CRM Cirugías - Admin/SuperAdmin y si está habilitado
  if (isAdminOrSuperAdmin && isMenuEnabled('crm_cirugias')) {
    navItems.push({ path: '/crm-cirugias', icon: Stethoscope, label: 'CRM Cirugías', testId: 'nav-crm-cirugias' });
  }
  
  // Agenda de Pacientes - Visible si está habilitado
  if (isMenuEnabled('agenda')) {
    navItems.push({ path: '/agenda', icon: CalendarDays, label: 'Agenda', testId: 'nav-agenda' });
  }

  // Orden específico para el rol Médico: Agenda, Pacientes, Evaluación Oftalmológica
  if (user?.role === 'medico') {
    const ordenMedico = ['/agenda', '/pacientes', '/evaluacion-oftalmologica'];
    navItems.sort((a, b) => {
      const ia = ordenMedico.indexOf(a.path);
      const ib = ordenMedico.indexOf(b.path);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
  }

  // Finanzas sub-items - Filtrados por configuración de menús
  const finanzasItems = [];
  if (user?.role !== 'optica') {
    if (isMenuEnabled('finanzas_pos')) finanzasItems.push({ path: '/punto-venta', icon: Store, label: 'Punto de Venta', testId: 'nav-punto-venta' });
    if (isMenuEnabled('finanzas_caja')) finanzasItems.push({ path: '/caja', icon: Wallet, label: 'Caja', testId: 'nav-caja' });
    if (isMenuEnabled('finanzas_cxc')) finanzasItems.push({ path: '/cuentas-cobrar-finanzas', icon: CreditCard, label: 'Cuentas por Cobrar', testId: 'nav-cxc-finanzas' });
    if (isMenuEnabled('finanzas_gastos')) finanzasItems.push({ path: '/gastos', icon: Receipt, label: 'Gastos', testId: 'nav-gastos' });
    if (isMenuEnabled('finanzas_pagos')) finanzasItems.push({ path: '/historial-pagos', icon: History, label: 'Historial de pagos', testId: 'nav-historial-pagos' });
    if (isAdminOrSuperAdmin && isMenuEnabled('finanzas_gastos_fijos')) finanzasItems.push({ path: '/configuracion/gastos-fijos', icon: CalendarClock, label: 'Gastos Fijos', testId: 'nav-gastos-fijos' });
    if (isAdminOrSuperAdmin && isMenuEnabled('finanzas_autorizaciones')) finanzasItems.push({ path: '/autorizaciones-pendientes', icon: ClipboardCheck, label: 'Autorizaciones', testId: 'nav-autorizaciones' });
    if (isAdminOrSuperAdmin) finanzasItems.push({ path: '/cierre-diario', icon: Calculator, label: 'Cierre del Día', testId: 'nav-cierre-diario' });
  }
  
  // Inventario sub-items - Filtrados por configuración de menús
  const inventarioItems = [];
  if (user?.role !== 'optica') {
    if (isMenuEnabled('inventario_panel')) inventarioItems.push({ path: '/inventario', icon: LayoutDashboard, label: 'Panel', testId: 'nav-inv-panel' });
    if (isMenuEnabled('inventario_bodegas')) inventarioItems.push({ path: '/inventario/bodegas', icon: Warehouse, label: 'Bodegas', testId: 'nav-inv-bodegas' });
    if (isMenuEnabled('inventario_productos')) inventarioItems.push({ path: '/inventario/productos', icon: Package, label: 'Productos', testId: 'nav-inv-productos' });
    if (isMenuEnabled('inventario_lotes')) inventarioItems.push({ path: '/inventario/lotes', icon: AlertTriangle, label: 'Lotes y Vencimientos', testId: 'nav-inv-lotes' });
    if (isMenuEnabled('inventario_kardex')) inventarioItems.push({ path: '/inventario/movimientos', icon: FileText, label: 'Kardex', testId: 'nav-inv-movimientos' });
    if (isAdminOrSuperAdmin && isMenuEnabled('inventario_categorias')) inventarioItems.push({ path: '/inventario/categorias', icon: Tag, label: 'Categorías', testId: 'nav-inv-categorias' });
    if (isSuperAdmin && isMenuEnabled('inventario_rentabilidad')) inventarioItems.push({ path: '/inventario/rentabilidad', icon: PieChart, label: 'Rentabilidad', testId: 'nav-inv-rentabilidad' });
    if (isAdminOrSuperAdmin && isMenuEnabled('inventario_sociedades')) inventarioItems.push({ path: '/sociedades', icon: Users, label: 'Sociedades', testId: 'nav-inv-sociedades' });
  }

  // Config sub-items
  const configItems = [];
  
  // Proveedores - disponible para Admin, SuperAdmin y Optica
  if ((isAdminOrSuperAdmin || canViewOptica) && isMenuEnabled('finanzas_proveedores')) {
    configItems.push({ 
      path: '/configuracion/proveedores', 
      icon: Truck, 
      label: 'Proveedores', 
      testId: 'nav-proveedores' 
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
  }

  // Módulo IGSS - visible si el menú está habilitado y el usuario tiene el permiso
  const igssItems = [];
  if (isMenuEnabled('unidades_igss') && hasPermission('manage_igss_units')) {
    igssItems.push({ 
      path: '/igss/unidades', 
      icon: Building, 
      label: 'Unidades IGSS', 
      testId: 'nav-unidades-igss' 
    });
  }
  if (hasPermission('manage_igss_units')) {
    igssItems.push({
      path: '/igss/nog',
      icon: ClipboardList,
      label: 'NOG',
      testId: 'nav-gestion-nog'
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

  // Optica sub-items - Filtrados por configuración de menús
  const opticaItems = [];
  if (canViewOptica) {
    if (isMenuEnabled('optica_dashboard')) opticaItems.push({ path: '/optica/dashboard', icon: LayoutDashboard, label: 'Dashboard', testId: 'nav-optica-dashboard' });
    if (isMenuEnabled('optica_armazones')) opticaItems.push({ path: '/optica/inventario', icon: Package, label: 'Armazones', testId: 'nav-optica-inventario' });
    if (isMenuEnabled('optica_lentes_contacto')) opticaItems.push({ path: '/optica/lentes-contacto', icon: CircleDot, label: 'Lentes de Contacto', testId: 'nav-optica-lentes-contacto' });
    if (isMenuEnabled('optica_tipos_lente')) opticaItems.push({ path: '/optica/tipos-lente', icon: Eye, label: 'Lentes Oftálmicos', testId: 'nav-optica-tipos-lente' });
    if (isMenuEnabled('optica_accesorios')) opticaItems.push({ path: '/optica/accesorios', icon: Watch, label: 'Accesorios', testId: 'nav-optica-accesorios' });
    if (isMenuEnabled('optica_pos')) opticaItems.push({ path: '/optica/punto-venta', icon: ShoppingCart, label: 'Punto de Venta', testId: 'nav-optica-pos' });
    if (isMenuEnabled('optica_cxc')) opticaItems.push({ path: '/optica/cuentas-cobrar', icon: CreditCard, label: 'Cuentas por Cobrar', testId: 'nav-optica-cxc' });
    if (hasPermission('manage_sales')) opticaItems.push({ path: '/punto-venta', icon: Store, label: 'Punto de Venta Clínica', testId: 'nav-optica-pos-clinica' });
    if (hasPermission('manage_caja')) opticaItems.push({ path: '/caja', icon: Wallet, label: 'Caja', testId: 'nav-optica-caja' });
    if (isMenuEnabled('optica_compras')) opticaItems.push({ path: '/optica/compras', icon: Receipt, label: 'Compras', testId: 'nav-optica-compras' });
  }

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
              alt="Novavisión"
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
                  ['/gastos', '/historial-pagos', '/autorizaciones-pendientes', '/caja', '/punto-venta', '/cierre-diario'].some(p => location.pathname.startsWith(p)) ? 'active' : ''
                }`}
                data-testid="nav-finanzas"
              >
                <div className="flex items-center gap-3">
                  <Wallet className={`w-5 h-5 icon ${['/gastos', '/historial-pagos', '/autorizaciones-pendientes', '/caja', '/punto-venta', '/cierre-diario'].some(p => location.pathname.startsWith(p)) ? 'opacity-100' : 'opacity-60'}`} />
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

          {/* 4.5. Inventario Section - NO para optica */}
          {inventarioItems.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setInventarioOpen(!inventarioOpen)}
                className={`sidebar-item flex items-center justify-between w-full mx-2 ${
                  location.pathname.startsWith('/inventario') ? 'active' : ''
                }`}
                data-testid="nav-inventario"
              >
                <div className="flex items-center gap-3">
                  <Boxes className={`w-5 h-5 icon ${location.pathname.startsWith('/inventario') ? 'opacity-100' : 'opacity-60'}`} />
                  <span className="font-medium text-sm">Inventario</span>
                </div>
                {inventarioOpen ? (
                  <ChevronDown className="w-4 h-4 opacity-60" />
                ) : (
                  <ChevronRight className="w-4 h-4 opacity-60" />
                )}
              </button>
              
              {inventarioOpen && (
                <div className="ml-4 mt-1 space-y-1">
                  {inventarioItems.map((item) => (
                    <NavLink key={item.path} item={item} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4.75. IGSS Section */}
          {igssItems.length > 0 && (
            <div className="mt-4">
              <button
                onClick={() => setIgssOpen(!igssOpen)}
                className={`sidebar-item flex items-center justify-between w-full mx-2 ${
                  location.pathname.startsWith('/igss') ? 'active' : ''
                }`}
                data-testid="nav-igss"
              >
                <div className="flex items-center gap-3">
                  <Building className={`w-5 h-5 icon ${location.pathname.startsWith('/igss') ? 'opacity-100' : 'opacity-60'}`} />
                  <span className="font-medium text-sm">IGSS</span>
                </div>
                {igssOpen ? (
                  <ChevronDown className="w-4 h-4 opacity-60" />
                ) : (
                  <ChevronRight className="w-4 h-4 opacity-60" />
                )}
              </button>
              
              {igssOpen && (
                <div className="ml-4 mt-1 space-y-1">
                  {igssItems.map((item) => (
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

          {/* 7. Registro de Auditoría - Solo SuperAdmin */}
          {hasPermission('view_audit_logs') && (
            <NavLink item={{ path: '/auditoria', icon: Shield, label: 'Auditoría', testId: 'nav-auditoria' }} />
          )}

          {/* 7.5. Laboratorio de Pruebas - Solo SuperAdmin (desarrollo) */}
          {isSuperAdmin && (
            <NavLink item={{ path: '/laboratorio-pruebas', icon: FlaskConical, label: 'Lab. Pruebas', testId: 'nav-laboratorio-pruebas' }} />
          )}

          {/* 7.6. Respaldos - Solo SuperAdmin */}
          {isSuperAdmin && (
            <NavLink item={{ path: '/respaldos', icon: DatabaseBackup, label: 'Respaldos', testId: 'nav-respaldos' }} />
          )}
          
          {/* 8. Configuration Section - Admin, SuperAdmin y Optica (si tiene items) */}
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
            onClick={() => setChangePwdOpen(true)}
            className="flex items-center gap-2 w-full px-3 py-2 mb-1 rounded-lg text-sm text-white/50 hover:text-white hover:bg-[#134840] transition-all"
            data-testid="change-password-button"
          >
            <KeyRound className="w-4 h-4" />
            <span>Cambiar contraseña</span>
          </button>
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

      <ChangePasswordDialog open={changePwdOpen} onOpenChange={setChangePwdOpen} />

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
              alt="Novavisión"
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
