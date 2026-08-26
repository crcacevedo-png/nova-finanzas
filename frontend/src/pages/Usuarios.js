import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { userApi, menuConfigApi, roleLabels, formatDate } from '../services/api';
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
  Save
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
  role: 'usuario'
};

const roleColors = {
  superadmin: 'bg-red-100 text-red-800 border border-red-200',
  admin: 'bg-blue-100 text-blue-800 border border-blue-200',
  usuario: 'bg-gray-100 text-gray-800 border border-gray-200',
  optica: 'bg-purple-100 text-purple-800 border border-purple-200',
};

const getRoleIcon = (role) => {
  switch (role) {
    case 'superadmin': return <ShieldCheck className="w-4 h-4" />;
    case 'admin': return <Shield className="w-4 h-4" />;
    case 'optica': return <Glasses className="w-4 h-4" />;
    default: return <User className="w-4 h-4" />;
  }
};

const Usuarios = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState(initialFormState);
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

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    if (activeTab === 'menus') {
      fetchMenuConfigs();
    }
  }, [activeTab, fetchMenuConfigs]);

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
        await userApi.create(formData);
        toast.success('Usuario creado correctamente');
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
    setFormData({
      username: user.username,
      name: user.name,
      password: '',
      role: user.role
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
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="usuarios" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Usuarios
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
                            <Badge className={`${roleColors[user.role]} flex items-center gap-1 w-fit`}>
                              {getRoleIcon(user.role)}
                              {roleLabels[user.role]}
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
                              {roleLabels[role]}
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
                      Tienes cambios sin guardar para el rol "{roleLabels[selectedRole]}"
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
                    <SelectItem value="usuario">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4" />
                        Usuario
                      </div>
                    </SelectItem>
                    <SelectItem value="admin">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4" />
                        Administrador
                      </div>
                    </SelectItem>
                    <SelectItem value="optica">
                      <div className="flex items-center gap-2">
                        <Glasses className="w-4 h-4" />
                        Óptica
                      </div>
                    </SelectItem>
                    {currentUser?.role === 'superadmin' && (
                      <SelectItem value="superadmin">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4" />
                          Super Admin
                        </div>
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
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
      </div>
    </Layout>
  );
};

export default Usuarios;
