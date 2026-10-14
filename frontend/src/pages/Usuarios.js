import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { userApi, menuConfigApi, rolesApi, roleLabels, formatDate } from '../services/api';
import { agendaApi } from '../services/agendaApi';
import { 
  Plus, 
  Trash2,
  Shield,
  ShieldCheck,
  User,
  ToggleLeft,
  ToggleRight,
  Glasses,
  Pencil,
  Eye,
  EyeOff,
  KeyRound,
  Menu,
  Settings,
  RefreshCw,
  Check,
  X,
  RotateCcw,
  Save,
  Users,
  Lock,
  Palette,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Building
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
import { toast, Toaster } from 'sonner';

const initialFormState = {
  username: '',
  name: '',
  password: '',
  role: 'usuario',
  medico_ficha_id: ''
};

const roleColors = {
  superadmin: 'bg-red-100 text-red-800 border border-red-200',
  admin: 'bg-blue-100 text-blue-800 border border-blue-200',
  usuario: 'bg-gray-100 text-gray-800 border border-gray-200',
  optica: 'bg-purple-100 text-purple-800 border border-purple-200',
  administrador_igss: 'bg-teal-100 text-teal-800 border border-teal-200',
};

// Colores disponibles para roles personalizados
const availableColors = [
  { id: 'red', label: 'Rojo', class: 'bg-red-100 text-red-800 border-red-200' },
  { id: 'blue', label: 'Azul', class: 'bg-blue-100 text-blue-800 border-blue-200' },
  { id: 'green', label: 'Verde', class: 'bg-green-100 text-green-800 border-green-200' },
  { id: 'purple', label: 'Morado', class: 'bg-purple-100 text-purple-800 border-purple-200' },
  { id: 'orange', label: 'Naranja', class: 'bg-orange-100 text-orange-800 border-orange-200' },
  { id: 'teal', label: 'Turquesa', class: 'bg-teal-100 text-teal-800 border-teal-200' },
  { id: 'pink', label: 'Rosa', class: 'bg-pink-100 text-pink-800 border-pink-200' },
  { id: 'gray', label: 'Gris', class: 'bg-gray-100 text-gray-800 border-gray-200' },
];

const getColorClass = (color) => {
  const found = availableColors.find(c => c.id === color);
  return found ? found.class : 'bg-gray-100 text-gray-800 border-gray-200';
};

const getRoleIcon = (role) => {
  switch (role) {
    case 'superadmin': return <ShieldCheck className="w-4 h-4" />;
    case 'admin': return <Shield className="w-4 h-4" />;
    case 'optica': return <Glasses className="w-4 h-4" />;
    case 'administrador_igss': return <Building className="w-4 h-4" />;
    default: return <User className="w-4 h-4" />;
  }
};

const Usuarios = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState(initialFormState);
  const [medicosFichas, setMedicosFichas] = useState([]);
  const [editingUser, setEditingUser] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('usuarios');
  
  // Estados para configuración de menús
  const [availableMenus, setAvailableMenus] = useState(null);
  const [menuConfigs, setMenuConfigs] = useState({});
  const [selectedRole, setSelectedRole] = useState('admin');
  const [editedMenus, setEditedMenus] = useState({});
  const [loadingMenus, setLoadingMenus] = useState(false);
  const [savingMenus, setSavingMenus] = useState(false);
  const [hasMenuChanges, setHasMenuChanges] = useState(false);
  
  // Estados para gestión de roles
  const [roles, setRoles] = useState([]);
  const [availablePermissions, setAvailablePermissions] = useState(null);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [deleteRoleDialogOpen, setDeleteRoleDialogOpen] = useState(false);
  const [roleToDelete, setRoleToDelete] = useState(null);
  const [roleFormData, setRoleFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    color: 'gray',
    permissions: {}
  });
  const [savingRole, setSavingRole] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState({});
  const [resetRoleDialogOpen, setResetRoleDialogOpen] = useState(false);
  const [roleToReset, setRoleToReset] = useState(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await userApi.getAll();
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  };

  const fetchMenuConfigs = useCallback(async () => {
    try {
      setLoadingMenus(true);
      const [availableRes, configsRes] = await Promise.all([
        menuConfigApi.getAvailableMenus(),
        menuConfigApi.getAllMenuConfigs()
      ]);
      setAvailableMenus(availableRes.data);
      setMenuConfigs(configsRes.data);
      
      // Inicializar editedMenus con la configuración actual
      const initialEdited = {};
      Object.keys(configsRes.data).forEach(role => {
        initialEdited[role] = [...configsRes.data[role].enabled_menus];
      });
      setEditedMenus(initialEdited);
    } catch (error) {
      console.error('Error fetching menu configs:', error);
      toast.error('Error al cargar configuración de menús');
    } finally {
      setLoadingMenus(false);
    }
  }, []);

  // Función para cargar roles
  const fetchRoles = useCallback(async () => {
    try {
      setLoadingRoles(true);
      const [rolesRes, permissionsRes] = await Promise.all([
        rolesApi.getAll(),
        rolesApi.getAvailablePermissions()
      ]);
      setRoles(rolesRes.data);
      setAvailablePermissions(permissionsRes.data);
    } catch (error) {
      console.error('Error fetching roles:', error);
      toast.error('Error al cargar roles');
    } finally {
      setLoadingRoles(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchRoles();
    agendaApi.getMedicosAgenda()
      .then((r) => setMedicosFichas((r.data?.data) || r.data || []))
      .catch(() => setMedicosFichas([]));
  }, [fetchRoles]);

  useEffect(() => {
    if (activeTab === 'menus') {
      fetchMenuConfigs();
    }
    if (activeTab === 'roles') {
      fetchRoles();
    }
  }, [activeTab, fetchMenuConfigs, fetchRoles]);

  // Detectar cambios en menús
  useEffect(() => {
    if (!menuConfigs[selectedRole]) return;
    
    const original = menuConfigs[selectedRole]?.enabled_menus || [];
    const edited = editedMenus[selectedRole] || [];
    
    const hasChanges = original.length !== edited.length || 
      !original.every(m => edited.includes(m)) ||
      !edited.every(m => original.includes(m));
    
    setHasMenuChanges(hasChanges);
  }, [editedMenus, menuConfigs, selectedRole]);

  const handleToggleMenu = (menuId) => {
    setEditedMenus(prev => {
      const current = prev[selectedRole] || [];
      const newMenus = current.includes(menuId)
        ? current.filter(m => m !== menuId)
        : [...current, menuId];
      
      return { ...prev, [selectedRole]: newMenus };
    });
  };

  const handleSaveMenuConfig = async () => {
    try {
      setSavingMenus(true);
      await menuConfigApi.updateMenuConfig(selectedRole, {
        role: selectedRole,
        enabled_menus: editedMenus[selectedRole] || []
      });
      
      toast.success(`Configuración de menús guardada para rol "${roleLabels[selectedRole]}"`);
      
      // Recargar configuraciones
      await fetchMenuConfigs();
    } catch (error) {
      console.error('Error saving menu config:', error);
      toast.error('Error al guardar configuración de menús');
    } finally {
      setSavingMenus(false);
    }
  };

  const handleResetMenuConfig = async () => {
    try {
      setSavingMenus(true);
      await menuConfigApi.resetMenuConfig(selectedRole);
      
      toast.success(`Configuración restaurada a valores por defecto para "${roleLabels[selectedRole]}"`);
      
      // Recargar configuraciones
      await fetchMenuConfigs();
    } catch (error) {
      console.error('Error resetting menu config:', error);
      toast.error('Error al restaurar configuración');
    } finally {
      setSavingMenus(false);
    }
  };

  const handleSelectAllCategory = (categoryMenus, selected) => {
    setEditedMenus(prev => {
      const current = prev[selectedRole] || [];
      const menuIds = categoryMenus.map(m => m.id);
      
      let newMenus;
      if (selected) {
        // Agregar todos los de la categoría
        newMenus = [...new Set([...current, ...menuIds])];
      } else {
        // Quitar todos los de la categoría
        newMenus = current.filter(m => !menuIds.includes(m));
      }
      
      return { ...prev, [selectedRole]: newMenus };
    });
  };

  // === FUNCIONES CRUD DE ROLES ===
  
  const handleNewRole = () => {
    setEditingRole(null);
    setRoleFormData({
      name: '',
      display_name: '',
      description: '',
      color: 'gray',
      permissions: {}
    });
    setExpandedCategories({});
    setRoleDialogOpen(true);
  };

  const handleEditRole = (role) => {
    setEditingRole(role);
    setRoleFormData({
      name: role.name,
      display_name: role.display_name,
      description: role.description || '',
      color: role.color || 'gray',
      permissions: role.permissions || {}
    });
    // Expandir todas las categorías que tienen permisos activos
    if (availablePermissions?.categories) {
      const expanded = {};
      Object.keys(availablePermissions.categories).forEach(catId => {
        const catPerms = availablePermissions.categories[catId].permissions;
        const hasActivePerms = catPerms.some(p => role.permissions?.[p.id]);
        if (hasActivePerms) expanded[catId] = true;
      });
      setExpandedCategories(expanded);
    }
    setRoleDialogOpen(true);
  };

  const handleCopyPermissionsFrom = (roleName) => {
    if (!roleName || roleName === '__none__') {
      setRoleFormData(prev => ({ ...prev, permissions: {} }));
      setExpandedCategories({});
      return;
    }
    const base = roles.find(r => r.name === roleName);
    if (!base) return;
    const perms = { ...(base.permissions || {}) };
    setRoleFormData(prev => ({ ...prev, permissions: perms }));
    if (availablePermissions?.categories) {
      const expanded = {};
      Object.keys(availablePermissions.categories).forEach(catId => {
        const catPerms = availablePermissions.categories[catId].permissions;
        if (catPerms.some(p => perms?.[p.id])) expanded[catId] = true;
      });
      setExpandedCategories(expanded);
    }
    toast.success(`Permisos copiados de "${base.display_name || base.name}"`);
  };

  const handleDeleteRoleClick = (role) => {
    setRoleToDelete(role);
    setDeleteRoleDialogOpen(true);
  };

  const handleConfirmDeleteRole = async () => {
    if (!roleToDelete) return;
    
    try {
      await rolesApi.delete(roleToDelete.name);
      toast.success(`Rol "${roleToDelete.display_name}" eliminado correctamente`);
      setDeleteRoleDialogOpen(false);
      setRoleToDelete(null);
      fetchRoles();
    } catch (error) {
      console.error('Error deleting role:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar rol');
    }
  };

  const handleSaveRole = async () => {
    if (!roleFormData.display_name) {
      toast.error('El nombre del rol es requerido');
      return;
    }

    try {
      setSavingRole(true);
      
      if (editingRole) {
        // Actualizar rol existente
        await rolesApi.update(editingRole.name, {
          display_name: roleFormData.display_name,
          description: roleFormData.description,
          color: roleFormData.color,
          permissions: roleFormData.permissions
        });
        toast.success(`Rol "${roleFormData.display_name}" actualizado correctamente`);
      } else {
        // Crear nuevo rol
        if (!roleFormData.name) {
          toast.error('El identificador del rol es requerido');
          setSavingRole(false);
          return;
        }
        await rolesApi.create({
          name: roleFormData.name,
          display_name: roleFormData.display_name,
          description: roleFormData.description,
          color: roleFormData.color,
          permissions: roleFormData.permissions
        });
        toast.success(`Rol "${roleFormData.display_name}" creado correctamente`);
      }
      
      setRoleDialogOpen(false);
      fetchRoles();
    } catch (error) {
      console.error('Error saving role:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar rol');
    } finally {
      setSavingRole(false);
    }
  };

  const handleResetRoleClick = (role) => {
    setRoleToReset(role);
    setResetRoleDialogOpen(true);
  };

  const handleConfirmResetPermissions = async () => {
    if (!roleToReset) return;
    
    try {
      await rolesApi.resetPermissions(roleToReset.name);
      toast.success(`Permisos de "${roleToReset.display_name}" restaurados a valores por defecto`);
      setResetRoleDialogOpen(false);
      setRoleToReset(null);
      fetchRoles();
    } catch (error) {
      console.error('Error resetting role permissions:', error);
      toast.error(error.response?.data?.detail || 'Error al restaurar permisos');
    }
  };

  const togglePermission = (permissionId) => {
    setRoleFormData(prev => ({
      ...prev,
      permissions: {
        ...prev.permissions,
        [permissionId]: !prev.permissions[permissionId]
      }
    }));
  };

  const toggleCategoryExpanded = (categoryId) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryId]: !prev[categoryId]
    }));
  };

  const toggleAllCategoryPermissions = (categoryPerms, enable) => {
    setRoleFormData(prev => {
      const newPermissions = { ...prev.permissions };
      categoryPerms.forEach(p => {
        newPermissions[p.id] = enable;
      });
      return { ...prev, permissions: newPermissions };
    });
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!formData.username || !formData.name || (!editingUser && !formData.password)) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    try {
      setIsSubmitting(true);
      let targetUserId = editingUser?.id;
      if (editingUser) {
        const updateData = {
          name: formData.name,
          role: formData.role,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await userApi.update(editingUser.id, updateData);
        toast.success('Usuario actualizado correctamente');
      } else {
        const res = await userApi.create(formData);
        targetUserId = res.data?.id;
        toast.success('Usuario creado correctamente');
      }
      // Vincular/actualizar la ficha de médico asignada a la cuenta
      if (formData.role === 'medico' && formData.medico_ficha_id && targetUserId) {
        try {
          await agendaApi.updateMedicoAgenda(formData.medico_ficha_id, { usuario_id: targetUserId });
          // Refrescar fichas para reflejar el vínculo
          const r = await agendaApi.getMedicosAgenda();
          setMedicosFichas((r.data?.data) || r.data || []);
        } catch (e) {
          toast.error('Usuario guardado, pero no se pudo vincular la ficha de médico');
        }
      }
      setIsDialogOpen(false);
      setFormData(initialFormState);
      setEditingUser(null);
      fetchUsers();
    } catch (error) {
      console.error('Error saving user:', error);
      const errorMessage = error.response?.data?.detail || 'Error al guardar usuario';
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    const fichaAsignada = medicosFichas.find((m) => m.usuario_id === user.id);
    setFormData({
      username: user.username,
      name: user.name,
      password: '',
      role: user.role,
      medico_ficha_id: fichaAsignada ? fichaAsignada.id : ''
    });
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (user) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!userToDelete) return;
    
    try {
      await userApi.delete(userToDelete.id);
      toast.success('Usuario eliminado correctamente');
      setDeleteDialogOpen(false);
      setUserToDelete(null);
      fetchUsers();
    } catch (error) {
      console.error('Error deleting user:', error);
      toast.error(error.response?.data?.detail || 'Error al eliminar usuario');
    }
  };

  const handleToggleStatus = async (user) => {
    try {
      await userApi.toggleStatus(user.id);
      toast.success(`Usuario ${user.is_active ? 'desactivado' : 'activado'} correctamente`);
      fetchUsers();
    } catch (error) {
      console.error('Error toggling user status:', error);
      toast.error('Error al cambiar estado del usuario');
    }
  };

  const handleNewUser = () => {
    setEditingUser(null);
    setFormData(initialFormState);
    setShowPassword(false);
    setIsDialogOpen(true);
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6" data-testid="gestion-usuarios">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 font-['Outfit'] flex items-center gap-2">
              <Settings className="w-7 h-7 text-blue-600" />
              Gestión de Usuarios
            </h1>
            <p className="text-gray-500 mt-1">Administra usuarios y configura permisos de menú por rol</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full max-w-lg grid-cols-3">
            <TabsTrigger value="usuarios" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Usuarios
            </TabsTrigger>
            <TabsTrigger value="roles" className="flex items-center gap-2" data-testid="tab-roles">
              <Shield className="w-4 h-4" />
              Roles
            </TabsTrigger>
            <TabsTrigger value="menus" className="flex items-center gap-2">
              <Menu className="w-4 h-4" />
              Menús por Rol
            </TabsTrigger>
          </TabsList>

          {/* Tab: Usuarios */}
          <TabsContent value="usuarios" className="space-y-4">
            <div className="flex justify-end">
              <Button onClick={handleNewUser} data-testid="create-user-button">
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Usuario
              </Button>
            </div>

            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-6 space-y-4">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Usuario</TableHead>
                        <TableHead>Nombre</TableHead>
                        <TableHead>Rol</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Último Acceso</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((user) => (
                        <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                          <TableCell className="font-medium">{user.username}</TableCell>
                          <TableCell>{user.name}</TableCell>
                          <TableCell>
                            <Badge className={`${roleColors[user.role] || 'bg-slate-100 text-slate-700'} flex items-center gap-1 w-fit`}>
                              {getRoleIcon(user.role)}
                              {roles.find((r) => r.name === user.role)?.display_name || roleLabels[user.role] || user.role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.is_active ? "default" : "secondary"}>
                              {user.is_active ? 'Activo' : 'Inactivo'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-gray-500">
                            {user.last_login ? formatDate(user.last_login) : 'Nunca'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleStatus(user)}
                                disabled={user.id === currentUser?.id}
                                title={user.is_active ? 'Desactivar' : 'Activar'}
                              >
                                {user.is_active ? (
                                  <ToggleRight className="w-4 h-4 text-green-600" />
                                ) : (
                                  <ToggleLeft className="w-4 h-4 text-gray-400" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(user)}
                                title="Editar"
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteClick(user)}
                                disabled={user.id === currentUser?.id || user.role === 'superadmin'}
                                title="Eliminar"
                              >
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab: Gestión de Roles */}
          <TabsContent value="roles" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-500">
                Administra los roles del sistema y sus permisos asociados
              </p>
              <Button onClick={handleNewRole} data-testid="create-role-button">
                <Plus className="w-4 h-4 mr-2" />
                Nuevo Rol
              </Button>
            </div>

            {loadingRoles ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
              </div>
            ) : (
              <div className="grid gap-4">
                {roles.map((role) => (
                  <Card key={role.id} className={`overflow-hidden ${!role.is_active ? 'opacity-60' : ''}`} data-testid={`role-card-${role.name}`}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge className={`${getColorClass(role.color)} flex items-center gap-1`}>
                            {role.is_system ? <Lock className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                            {role.display_name}
                          </Badge>
                          {role.is_system && (
                            <Badge variant="outline" className="text-xs">Sistema</Badge>
                          )}
                          {!role.is_active && (
                            <Badge variant="secondary" className="text-xs">Inactivo</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-500 flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            {role.user_count} usuario{role.user_count !== 1 ? 's' : ''}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditRole(role)}
                            title="Editar permisos"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          {role.is_system ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleResetRoleClick(role)}
                              title="Restaurar permisos por defecto"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteRoleClick(role)}
                              disabled={role.user_count > 0}
                              title={role.user_count > 0 ? 'No se puede eliminar: tiene usuarios asignados' : 'Eliminar rol'}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </div>
                      {role.description && (
                        <CardDescription className="mt-2">{role.description}</CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(role.permissions || {})
                          .filter(([_, enabled]) => enabled)
                          .slice(0, 8)
                          .map(([permId]) => (
                            <Badge key={permId} variant="outline" className="text-xs font-normal">
                              {permId.replace(/_/g, ' ')}
                            </Badge>
                          ))}
                        {Object.values(role.permissions || {}).filter(Boolean).length > 8 && (
                          <Badge variant="outline" className="text-xs font-normal">
                            +{Object.values(role.permissions || {}).filter(Boolean).length - 8} más
                          </Badge>
                        )}
                        {Object.values(role.permissions || {}).filter(Boolean).length === 0 && (
                          <span className="text-sm text-gray-400 italic">Sin permisos configurados</span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {roles.length === 0 && (
                  <Card className="p-8 text-center">
                    <Shield className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                    <p className="text-gray-500">No hay roles configurados</p>
                    <Button className="mt-4" onClick={handleNewRole}>
                      <Plus className="w-4 h-4 mr-2" />
                      Crear primer rol
                    </Button>
                  </Card>
                )}
              </div>
            )}
          </TabsContent>

          {/* Tab: Configuración de Menús */}
          <TabsContent value="menus" className="space-y-4">
            {loadingMenus ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
              </div>
            ) : availableMenus && (
              <>
                {/* Selector de Rol y Acciones */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Label className="text-sm font-medium">Configurar menús para:</Label>
                    <Select value={selectedRole} onValueChange={setSelectedRole}>
                      <SelectTrigger className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableMenus.roles.filter(r => r !== 'superadmin').map(role => (
                          <SelectItem key={role} value={role}>
                            <div className="flex items-center gap-2">
                              {getRoleIcon(role)}
                              {roleLabels[role] || role}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {menuConfigs[selectedRole]?.is_custom && (
                      <Badge variant="outline" className="text-amber-600 border-amber-300">
                        Personalizado
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      onClick={handleResetMenuConfig}
                      disabled={savingMenus || !menuConfigs[selectedRole]?.is_custom}
                    >
                      <RotateCcw className="w-4 h-4 mr-2" />
                      Restaurar
                    </Button>
                    <Button 
                      onClick={handleSaveMenuConfig}
                      disabled={savingMenus || !hasMenuChanges}
                    >
                      {savingMenus ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Save className="w-4 h-4 mr-2" />
                      )}
                      Guardar Cambios
                    </Button>
                  </div>
                </div>

                {/* Info de SuperAdmin */}
                {selectedRole === 'superadmin' && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">
                      <strong>Nota:</strong> El rol SuperAdmin siempre tiene acceso a todos los menús del sistema. 
                      Esta configuración no puede ser modificada.
                    </p>
                  </div>
                )}

                {/* Grid de Categorías */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {availableMenus.categories.map(category => {
                    const currentMenus = editedMenus[selectedRole] || [];
                    const categoryMenuIds = category.menus.map(m => m.id);
                    const selectedInCategory = categoryMenuIds.filter(id => currentMenus.includes(id));
                    const allSelected = selectedInCategory.length === categoryMenuIds.length;
                    const someSelected = selectedInCategory.length > 0 && !allSelected;
                    
                    return (
                      <Card key={category.category_id} className="overflow-hidden">
                        <CardHeader className="pb-3 bg-gray-50 border-b">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-base font-medium">
                              {category.category_label}
                            </CardTitle>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500">
                                {selectedInCategory.length}/{categoryMenuIds.length}
                              </span>
                              <Checkbox
                                checked={allSelected}
                                indeterminate={someSelected}
                                onCheckedChange={(checked) => handleSelectAllCategory(category.menus, checked)}
                                disabled={selectedRole === 'superadmin'}
                              />
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="p-0">
                          <div className="divide-y">
                            {category.menus.map(menu => {
                              const isEnabled = currentMenus.includes(menu.id);
                              
                              return (
                                <div 
                                  key={menu.id}
                                  className={`flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors ${
                                    isEnabled ? 'bg-green-50/50' : ''
                                  }`}
                                >
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-sm">{menu.label}</span>
                                      {isEnabled && (
                                        <Check className="w-4 h-4 text-green-600" />
                                      )}
                                    </div>
                                    <p className="text-xs text-gray-500 mt-0.5">{menu.description}</p>
                                    <code className="text-xs text-gray-400">{menu.path}</code>
                                  </div>
                                  <Checkbox
                                    checked={isEnabled}
                                    onCheckedChange={() => handleToggleMenu(menu.id)}
                                    disabled={selectedRole === 'superadmin'}
                                  />
                                </div>
                              );
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {/* Resumen de cambios */}
                {hasMenuChanges && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between">
                    <p className="text-sm text-amber-700">
                      Tienes cambios sin guardar para el rol &quot;{roleLabels[selectedRole]}&quot;
                    </p>
                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => {
                          setEditedMenus(prev => ({
                            ...prev,
                            [selectedRole]: [...(menuConfigs[selectedRole]?.enabled_menus || [])]
                          }));
                        }}
                      >
                        <X className="w-4 h-4 mr-1" />
                        Descartar
                      </Button>
                      <Button size="sm" onClick={handleSaveMenuConfig} disabled={savingMenus}>
                        <Save className="w-4 h-4 mr-1" />
                        Guardar
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>

        {/* Dialog: Crear/Editar Usuario */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">
                {editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
              </DialogTitle>
              <DialogDescription>
                {editingUser 
                  ? 'Modifica los datos del usuario. Deja la contraseña vacía para mantener la actual.'
                  : 'Completa los datos para crear un nuevo usuario.'
                }
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="username">Usuario</Label>
                <Input
                  id="username"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  disabled={!!editingUser}
                  placeholder="nombre.usuario"
                  data-testid="input-username"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Nombre Completo</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Nombre del usuario"
                  data-testid="input-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">
                  Contraseña {editingUser && '(dejar vacío para mantener)'}
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    placeholder={editingUser ? '••••••••' : 'Contraseña segura'}
                    data-testid="input-password"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Rol</Label>
                <Select 
                  value={formData.role} 
                  onValueChange={(value) => handleInputChange('role', value)}
                >
                  <SelectTrigger data-testid="select-role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {roles
                      .filter((r) => r.name !== 'superadmin' || currentUser?.role === 'superadmin')
                      .map((r) => (
                        <SelectItem key={r.name} value={r.name}>
                          <div className="flex items-center gap-2">
                            {getRoleIcon(r.name)}
                            {r.display_name || roleLabels[r.name] || r.name}
                            {r.is_system === false && (
                              <span className="text-xs text-muted-foreground">(personalizado)</span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              {formData.role === 'medico' && (
                <div className="space-y-2">
                  <Label htmlFor="medico_ficha">Médico asignado (ficha)</Label>
                  <Select
                    value={formData.medico_ficha_id || ''}
                    onValueChange={(value) => handleInputChange('medico_ficha_id', value)}
                  >
                    <SelectTrigger data-testid="select-medico-ficha">
                      <SelectValue placeholder="Selecciona la ficha de médico" />
                    </SelectTrigger>
                    <SelectContent>
                      {medicosFichas.map((m) => (
                        <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Vincula esta cuenta con su ficha de médico para que la Agenda muestre solo sus citas.
                  </p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting}
                data-testid="submit-user-button"
              >
                {isSubmitting ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : editingUser ? (
                  <KeyRound className="w-4 h-4 mr-2" />
                ) : (
                  <Plus className="w-4 h-4 mr-2" />
                )}
                {editingUser ? 'Guardar Cambios' : 'Crear Usuario'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Confirmar Eliminación */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Usuario</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar a &quot;{userToDelete?.name}&quot;? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDelete}
                data-testid="confirm-delete-user-button"
              >
                Eliminar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Crear/Editar Rol */}
        <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
          <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-600" />
                {editingRole ? `Editar Rol: ${editingRole.display_name}` : 'Nuevo Rol'}
              </DialogTitle>
              <DialogDescription>
                {editingRole 
                  ? 'Modifica los permisos y configuración del rol.'
                  : 'Crea un nuevo rol personalizado con permisos específicos.'
                }
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Información básica del rol */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="role-name">Identificador</Label>
                  <Input
                    id="role-name"
                    value={roleFormData.name}
                    onChange={(e) => setRoleFormData(prev => ({ ...prev, name: e.target.value.toLowerCase().replace(/\s+/g, '_') }))}
                    disabled={!!editingRole}
                    placeholder="mi_rol"
                    data-testid="input-role-name"
                  />
                  <p className="text-xs text-gray-500">Solo letras, números y guiones bajos</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role-display-name">Nombre visible</Label>
                  <Input
                    id="role-display-name"
                    value={roleFormData.display_name}
                    onChange={(e) => setRoleFormData(prev => ({ ...prev, display_name: e.target.value }))}
                    placeholder="Mi Rol Personalizado"
                    data-testid="input-role-display-name"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role-description">Descripción</Label>
                <Input
                  id="role-description"
                  value={roleFormData.description}
                  onChange={(e) => setRoleFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Descripción del rol y sus responsabilidades"
                />
              </div>

              <div className="space-y-2">
                <Label>Color del badge</Label>
                <div className="flex flex-wrap gap-2">
                  {availableColors.map(color => (
                    <button
                      key={color.id}
                      type="button"
                      onClick={() => setRoleFormData(prev => ({ ...prev, color: color.id }))}
                      className={`px-3 py-1.5 rounded-full text-sm transition-all ${color.class} ${
                        roleFormData.color === color.id ? 'ring-2 ring-offset-2 ring-blue-500' : 'opacity-70 hover:opacity-100'
                      }`}
                    >
                      {color.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Copiar permisos de un rol base (solo al crear) */}
              {!editingRole && (
                <div className="space-y-2">
                  <Label htmlFor="copy-permissions">Copiar permisos de</Label>
                  <Select defaultValue="__none__" onValueChange={handleCopyPermissionsFrom}>
                    <SelectTrigger id="copy-permissions" data-testid="select-copy-permissions">
                      <SelectValue placeholder="Ninguno (partir de cero)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">Ninguno (partir de cero)</SelectItem>
                      {roles
                        .filter((r) => r.name !== 'superadmin' || currentUser?.role === 'superadmin')
                        .map((r) => (
                          <SelectItem key={r.name} value={r.name}>
                            {r.display_name || roleLabels[r.name] || r.name}
                            {r.is_system === false ? ' (personalizado)' : ''}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-500">Precarga los permisos del rol elegido; puedes ajustarlos abajo antes de guardar</p>
                </div>
              )}

              {/* Permisos */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  Permisos
                </Label>
                
                {editingRole?.is_system && editingRole?.name === 'superadmin' ? (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">
                      El rol SuperAdmin tiene todos los permisos del sistema y no puede ser modificado.
                    </p>
                  </div>
                ) : availablePermissions?.categories && (
                  <div className="border rounded-lg divide-y">
                    {Object.entries(availablePermissions.categories).map(([catId, category]) => {
                      const isExpanded = expandedCategories[catId];
                      const enabledCount = category.permissions.filter(p => roleFormData.permissions[p.id]).length;
                      const totalCount = category.permissions.length;
                      
                      return (
                        <div key={catId}>
                          <button
                            type="button"
                            onClick={() => toggleCategoryExpanded(catId)}
                            className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{category.label}</span>
                              <Badge variant="outline" className="text-xs">
                                {enabledCount}/{totalCount}
                              </Badge>
                            </div>
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            )}
                          </button>
                          
                          {isExpanded && (
                            <div className="px-3 pb-3 space-y-2">
                              <div className="flex gap-2 mb-2">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => toggleAllCategoryPermissions(category.permissions, true)}
                                >
                                  Seleccionar todos
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => toggleAllCategoryPermissions(category.permissions, false)}
                                >
                                  Quitar todos
                                </Button>
                              </div>
                              
                              <div className="grid grid-cols-1 gap-2">
                                {category.permissions.map(perm => (
                                  <label
                                    key={perm.id}
                                    className={`flex items-start gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                                      roleFormData.permissions[perm.id] ? 'bg-green-50' : 'hover:bg-gray-50'
                                    }`}
                                  >
                                    <Checkbox
                                      checked={roleFormData.permissions[perm.id] || false}
                                      onCheckedChange={() => togglePermission(perm.id)}
                                    />
                                    <div className="flex-1">
                                      <span className="font-medium text-sm">{perm.label}</span>
                                      <p className="text-xs text-gray-500">{perm.description}</p>
                                    </div>
                                  </label>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setRoleDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSaveRole}
                disabled={savingRole || (editingRole?.is_system && editingRole?.name === 'superadmin')}
                data-testid="submit-role-button"
              >
                {savingRole ? (
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                {editingRole ? 'Guardar Cambios' : 'Crear Rol'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Confirmar Eliminación de Rol */}
        <Dialog open={deleteRoleDialogOpen} onOpenChange={setDeleteRoleDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-500" />
                Eliminar Rol
              </DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar el rol &quot;{roleToDelete?.display_name}&quot;? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteRoleDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDeleteRole}
                data-testid="confirm-delete-role-button"
              >
                Eliminar Rol
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog: Confirmar Restauración de Permisos */}
        <Dialog open={resetRoleDialogOpen} onOpenChange={setResetRoleDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-amber-500" />
                Restaurar Permisos
              </DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas restaurar los permisos del rol &quot;{roleToReset?.display_name}&quot; 
                a sus valores por defecto? Se eliminarán todas las personalizaciones realizadas.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setResetRoleDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmResetPermissions}
                className="bg-amber-500 hover:bg-amber-600"
                data-testid="confirm-reset-role-button"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Restaurar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default Usuarios;
