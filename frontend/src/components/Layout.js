import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  Receipt, 
  Users, 
  LogOut, 
  Menu,
  X
} from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Avatar, AvatarFallback } from './ui/avatar';
import { roleLabels } from '../services/api';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_novavision-finanzas/artifacts/cjnymxl0_logo%20nova.png";

const Layout = ({ children }) => {
  const { user, logout, canViewUserManagement } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { 
      path: '/dashboard', 
      label: 'Dashboard', 
      icon: LayoutDashboard,
      show: true
    },
    { 
      path: '/gastos', 
      label: 'Gastos', 
      icon: Receipt,
      show: true
    },
    { 
      path: '/usuarios', 
      label: 'Usuarios', 
      icon: Users,
      show: canViewUserManagement()
    },
  ];

  const filteredNavItems = navItems.filter(item => item.show);

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-white border-r border-slate-200
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200">
            <Link to="/dashboard" className="flex items-center">
              <img 
                src={LOGO_URL} 
                alt="NovaVision" 
                className="h-10 w-auto"
              />
            </Link>
            <button 
              className="lg:hidden p-1 hover:bg-slate-100 rounded"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.path.slice(1)}`}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg
                    transition-all duration-200 font-medium text-sm
                    ${isActive(item.path) 
                      ? 'bg-teal-50 text-teal-800 border-r-2 border-teal-600' 
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }
                  `}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* User info at bottom */}
          <div className="p-4 border-t border-slate-200">
            <div className="flex items-center gap-3 px-2">
              <Avatar className="h-9 w-9 bg-teal-100">
                <AvatarFallback className="bg-teal-100 text-teal-800 font-medium">
                  {user?.name?.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{user?.name}</p>
                <p className="text-xs text-slate-500">{roleLabels[user?.role]}</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-8">
          <button 
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg"
            onClick={() => setSidebarOpen(true)}
            data-testid="mobile-menu-button"
          >
            <Menu className="w-5 h-5 text-slate-600" />
          </button>

          <div className="flex-1" />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                className="flex items-center gap-2 hover:bg-slate-100"
                data-testid="user-menu-button"
              >
                <Avatar className="h-8 w-8 bg-teal-100">
                  <AvatarFallback className="bg-teal-100 text-teal-800 font-medium text-sm">
                    {user?.name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden sm:inline text-sm font-medium text-slate-700">
                  {user?.name}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div>
                  <p className="font-medium">{user?.name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                  <p className="text-xs text-teal-600 mt-1">{roleLabels[user?.role]}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={handleLogout}
                className="text-rose-600 focus:text-rose-600 cursor-pointer"
                data-testid="logout-button"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Cerrar Sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
