import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { 
  Shield, 
  Search, 
  RefreshCw, 
  ChevronLeft, 
  ChevronRight,
  Filter,
  Clock,
  User,
  Globe,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  LogIn,
  LogOut,
  UserPlus,
  UserMinus,
  Key,
  Activity
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { toast, Toaster } from 'sonner';
import { securityApi, auditActionLabels, userApi } from '../services/api';

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
  const [securityStatus, setSecurityStatus] = useState(null);
  
  // Paginación
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState({
    action: '',
    user_id: '',
    date_from: '',
    date_to: ''
  });

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await securityApi.getAuditLogs({
        page,
        limit: 30,
        search: searchTerm,
        ...filters
      });
      setLogs(response.data.data || []);
      setTotalPages(response.data.total_pages || 1);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      toast.error('Error al cargar los registros de auditoría');
    } finally {
      setLoading(false);
    }
  }, [page, searchTerm, filters]);

  const fetchActions = useCallback(async () => {
    try {
      const response = await securityApi.getAuditActions();
      setActions(response.data.actions || []);
    } catch (error) {
      console.error('Error fetching actions:', error);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const response = await userApi.getAll();
      setUsers(response.data || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  }, []);

  const fetchSecurityStatus = useCallback(async () => {
    try {
      const response = await securityApi.getSecurityStatus();
      setSecurityStatus(response.data);
    } catch (error) {
      console.error('Error fetching security status:', error);
    }
  }, []);

  useEffect(() => {
    fetchActions();
    fetchUsers();
    fetchSecurityStatus();
  }, [fetchActions, fetchUsers, fetchSecurityStatus]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const clearFilters = () => {
    setFilters({
      action: '',
      user_id: '',
      date_from: '',
      date_to: ''
    });
    setSearchTerm('');
    setPage(1);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    // Mostrar siempre en hora de Guatemala (GMT-6)
    const parts = new Intl.DateTimeFormat('es-GT', {
      timeZone: 'America/Guatemala',
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).formatToParts(date).reduce((acc, p) => { acc[p.type] = p.value; return acc; }, {});
    return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}:${parts.second}`;
  };

  const getActionIcon = (action) => {
    const iconMap = {
      LOGIN_SUCCESS: <LogIn className="w-4 h-4 text-green-600" />,
      LOGIN_FAILED: <AlertTriangle className="w-4 h-4 text-red-600" />,
      LOGOUT: <LogOut className="w-4 h-4 text-gray-600" />,
      PASSWORD_CHANGE: <Key className="w-4 h-4 text-blue-600" />,
      USER_CREATED: <UserPlus className="w-4 h-4 text-green-600" />,
      USER_UPDATED: <User className="w-4 h-4 text-blue-600" />,
      USER_DELETED: <UserMinus className="w-4 h-4 text-red-600" />,
      USER_ACTIVATED: <CheckCircle className="w-4 h-4 text-green-600" />,
      USER_DEACTIVATED: <XCircle className="w-4 h-4 text-orange-600" />,
    };
    return iconMap[action] || <Activity className="w-4 h-4 text-gray-500" />;
  };

  const getActionBadgeClass = (action) => {
    if (action.includes('FAILED') || action.includes('DELETED') || action.includes('CANCELLED')) {
      return 'bg-red-100 text-red-700 border-red-200';
    }
    if (action.includes('SUCCESS') || action.includes('CREATED') || action.includes('ACTIVATED')) {
      return 'bg-green-100 text-green-700 border-green-200';
    }
    if (action.includes('UPDATED') || action.includes('CHANGE')) {
      return 'bg-blue-100 text-blue-700 border-blue-200';
    }
    if (action.includes('LOGOUT') || action.includes('DEACTIVATED')) {
      return 'bg-orange-100 text-orange-700 border-orange-200';
    }
    return 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const renderDetails = (details) => {
    if (!details || Object.keys(details).length === 0) return '-';
    
    const relevantKeys = ['reason', 'target_user', 'changes', 'expense_name', 'patient_name', 'surgery_type'];
    const filtered = Object.entries(details).filter(([key]) => relevantKeys.includes(key) || !key.startsWith('_'));
    
    if (filtered.length === 0) return '-';
    
    return (
      <div className="text-xs space-y-0.5">
        {filtered.slice(0, 3).map(([key, value]) => (
          <div key={key} className="flex gap-1">
            <span className="text-gray-500">{key}:</span>
            <span className="text-gray-700 truncate max-w-[150px]">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
        {filtered.length > 3 && (
          <span className="text-gray-400">+{filtered.length - 3} más</span>
        )}
      </div>
    );
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="audit-logs-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Shield className="w-7 h-7 text-blue-600" />
              Registro de Auditoría
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Historial de acciones y eventos del sistema
            </p>
          </div>
          <Button 
            variant="outline"
            onClick={() => {
              fetchLogs();
              fetchSecurityStatus();
            }}
            className="btn-outline"
            data-testid="refresh-audit-logs"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualizar
          </Button>
        </div>

        {/* Security Status Cards */}
        {securityStatus && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="card-metrics border-0 shadow-none">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 rounded-xl bg-blue-100">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Total Registros</p>
                  <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{total}</p>
                </div>
              </CardContent>
            </Card>
            
            <Card className="card-metrics border-0 shadow-none">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 rounded-xl bg-red-100">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Logins Fallidos (24h)</p>
                  <p className="text-2xl font-bold text-red-600">{securityStatus.failed_logins_24h}</p>
                </div>
              </CardContent>
            </Card>
            
            <Card className="card-metrics border-0 shadow-none">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 rounded-xl bg-green-100">
                  <User className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Usuarios Activos</p>
                  <p className="text-2xl font-bold text-green-600">{securityStatus.active_users}</p>
                </div>
              </CardContent>
            </Card>
            
            <Card className="card-metrics border-0 shadow-none">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 rounded-xl bg-orange-100">
                  <Key className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Tokens Revocados</p>
                  <p className="text-2xl font-bold text-orange-600">{securityStatus.blacklisted_tokens}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Search and Filters */}
        <Card className="card-teal">
          <CardContent className="p-4 space-y-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Buscar por usuario, acción o IP..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-teal pl-10"
                  data-testid="search-audit"
                />
              </div>
              <Button type="submit" className="btn-primary">
                Buscar
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setFilterOpen(!filterOpen)}
                className="btn-outline"
              >
                <Filter className="w-4 h-4 mr-2" />
                Filtros
              </Button>
            </form>

            {filterOpen && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4 border-t">
                <div>
                  <Label className="text-xs">Acción</Label>
                  <Select
                    value={filters.action}
                    onValueChange={(value) => setFilters(prev => ({ ...prev, action: value === 'all' ? '' : value }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue placeholder="Todas las acciones" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas las acciones</SelectItem>
                      {actions.map((action) => (
                        <SelectItem key={action} value={action}>
                          {auditActionLabels[action] || action}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Usuario</Label>
                  <Select
                    value={filters.user_id}
                    onValueChange={(value) => setFilters(prev => ({ ...prev, user_id: value === 'all' ? '' : value }))}
                  >
                    <SelectTrigger className="input-teal">
                      <SelectValue placeholder="Todos los usuarios" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos los usuarios</SelectItem>
                      {users.map((user) => (
                        <SelectItem key={user.id} value={user.id}>
                          {user.name} ({user.username})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Desde</Label>
                  <Input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                    className="input-teal"
                  />
                </div>
                <div>
                  <Label className="text-xs">Hasta</Label>
                  <Input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                    className="input-teal"
                  />
                </div>
                <div className="md:col-span-4 flex justify-end">
                  <Button variant="outline" onClick={clearFilters} className="btn-outline">
                    Limpiar filtros
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Historial de Auditoría
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(8)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : logs.length === 0 ? (
              <div className="p-12 text-center">
                <Shield className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>
                  No hay registros de auditoría
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header w-[180px]">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Fecha/Hora
                        </div>
                      </TableHead>
                      <TableHead className="table-header">Acción</TableHead>
                      <TableHead className="table-header">
                        <div className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          Usuario
                        </div>
                      </TableHead>
                      <TableHead className="table-header">
                        <div className="flex items-center gap-1">
                          <Globe className="w-3 h-3" />
                          IP
                        </div>
                      </TableHead>
                      <TableHead className="table-header">Detalles</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow 
                        key={log.id} 
                        className="table-row-hover"
                        data-testid={`audit-row-${log.id}`}
                      >
                        <TableCell>
                          <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                            {formatDate(log.timestamp)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getActionIcon(log.action)}
                            <Badge className={`text-xs ${getActionBadgeClass(log.action)}`}>
                              {auditActionLabels[log.action] || log.action}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                            {log.user_name || 'Sistema'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs font-mono" style={{ color: 'var(--text-hint)' }}>
                            {log.ip_address || '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          {renderDetails(log.details)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Paginación */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-4 border-t">
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Página {page} de {totalPages} ({total} registros)
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default AuditLogs;
