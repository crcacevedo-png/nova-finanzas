import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { userApi, roleLabels, formatDate } from '../services/api';
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
  KeyRound
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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

const initialEditFormState = {
  name: '',
  role: '',
  password: '',
  is_active: true
};

const Usuarios = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [userToEdit, setUserToEdit] = useState(null);
  const [formData, setFormData] = useState(initialFormState);
  const [editFormData, setEditFormData] = useState(initialEditFormState);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showEditPassword, setShowEditPassword] = useState(false);
  const [changePassword, setChangePassword] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await userApi.getAll();
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Error al cargar los usuarios');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = () => {
    setFormData(initialFormState);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormData(initialFormState);
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.username || !formData.name || !formData.password) {
      toast.error('Por favor completa todos los campos');
      return;
    }

    if (formData.password.length < 6) {
      toast.error('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    setSubmitting(true);
    try {
      await userApi.create(formData);
      toast.success('Usuario creado correctamente');
      handleCloseDialog();
      fetchUsers();
    } catch (error) {
      let message = 'Error al crear el usuario';
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors
        message = detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (detail && typeof detail === 'object') {
        message = detail.msg || detail.message || JSON.stringify(detail);
      }
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (userId) => {
    try {
      const response = await userApi.toggleActive(userId);
      toast.success(response.data.is_active ? 'Usuario activado' : 'Usuario desactivado');
      fetchUsers();
    } catch (error) {
      toast.error('Error al cambiar el estado del usuario');
    }
  };

  const handleEditClick = (user) => {
    setUserToEdit(user);
    setEditFormData({
      name: user.name,
      role: user.role,
      password: '',
      is_active: user.is_active
    });
    setChangePassword(false);
    setShowEditPassword(false);
    setEditDialogOpen(true);
  };

  const handleEditInputChange = (field, value) => {
    setEditFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    
    if (!editFormData.name) {
      toast.error('El nombre es requerido');
      return;
    }

    // Validar contraseña solo si se va a cambiar
    if (changePassword) {
      if (!editFormData.password) {
        toast.error('Ingresa la nueva contraseña');
        return;
      }
      if (editFormData.password.length < 8) {
        toast.error('La contraseña debe tener al menos 8 caracteres');
        return;
      }
      // Validar fortaleza
      if (!/[A-Z]/.test(editFormData.password)) {
        toast.error('La contraseña debe contener al menos una mayúscula');
        return;
      }
      if (!/[a-z]/.test(editFormData.password)) {
        toast.error('La contraseña debe contener al menos una minúscula');
        return;
      }
      if (!/\d/.test(editFormData.password)) {
        toast.error('La contraseña debe contener al menos un número');
        return;
      }
    }

    setSubmitting(true);
    try {
      const updateData = {
        name: editFormData.name,
        role: editFormData.role,
        is_active: editFormData.is_active
      };
      
      // Solo incluir contraseña si se va a cambiar
      if (changePassword && editFormData.password) {
        updateData.password = editFormData.password;
      }

      await userApi.update(userToEdit.id, updateData);
      toast.success('Usuario actualizado correctamente');
      setEditDialogOpen(false);
      setUserToEdit(null);
      fetchUsers();
    } catch (error) {
      let message = 'Error al actualizar el usuario';
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (detail && typeof detail === 'object') {
        message = detail.msg || detail.message || JSON.stringify(detail);
      }
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
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
      fetchUsers();
    } catch (error) {
      let message = 'Error al eliminar el usuario';
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else if (detail && typeof detail === 'object') {
        message = detail.msg || detail.message || JSON.stringify(detail);
      }
      toast.error(message);
    } finally {
      setDeleteDialogOpen(false);
      setUserToDelete(null);
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'superadmin':
        return <ShieldCheck className="w-4 h-4" />;
      case 'admin':
        return <Shield className="w-4 h-4" />;
      case 'optica':
        return <Glasses className="w-4 h-4" />;
      default:
        return <User className="w-4 h-4" />;
    }
  };

  const getRoleBadge = (role) => {
    const colors = {
      superadmin: 'badge-superadmin border-0',
      admin: 'badge-admin border-0',
      usuario: 'badge-usuario border-0',
      optica: 'badge-optica border-0'
    };
    return (
      <Badge className={`${colors[role] || 'badge-usuario border-0'} flex items-center gap-1`}>
        {getRoleIcon(role)}
        {roleLabels[role] || role}
      </Badge>
    );
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="usuarios-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Usuarios</h1>
            <p className="text-slate-500 text-sm">Administra los usuarios del sistema</p>
          </div>
          <Button 
            onClick={handleOpenDialog}
            className="btn-primary"
            data-testid="add-user-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Usuario
          </Button>
        </div>

        {/* Table */}
        <Card className="border border-slate-200">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : users.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-slate-500">No hay usuarios registrados</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead className="font-semibold text-slate-600">Usuario</TableHead>
                      <TableHead className="font-semibold text-slate-600">Nombre de Usuario</TableHead>
                      <TableHead className="font-semibold text-slate-600">Rol</TableHead>
                      <TableHead className="font-semibold text-slate-600">Último Acceso</TableHead>
                      <TableHead className="font-semibold text-slate-600">Estado</TableHead>
                      <TableHead className="font-semibold text-slate-600 text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow 
                        key={user.id} 
                        className="table-row-hover"
                        data-testid={`user-row-${user.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-[#E1F5EE] flex items-center justify-center">
                              <span className="text-[#0F6E56] font-semibold">
                                {user.name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium text-slate-900">{user.name}</p>
                              {user.id === currentUser?.id && (
                                <span className="text-xs text-[#0F6E56]">(Tú)</span>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-600 font-mono text-sm">{user.username}</TableCell>
                        <TableCell>{getRoleBadge(user.role)}</TableCell>
                        <TableCell className="text-slate-500 text-sm">
                          {user.last_login ? formatDate(user.last_login) : 'Nunca'}
                        </TableCell>
                        <TableCell>
                          <Badge className={user.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}>
                            {user.is_active ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {user.id !== currentUser?.id && (
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEditClick(user)}
                                className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                                title="Editar usuario"
                                data-testid={`edit-user-${user.id}`}
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleActive(user.id)}
                                className={`h-8 w-8 p-0 ${user.is_active ? 'hover:bg-amber-50 hover:text-amber-700' : 'hover:bg-emerald-50 hover:text-emerald-700'}`}
                                title={user.is_active ? 'Desactivar' : 'Activar'}
                                data-testid={`toggle-user-${user.id}`}
                              >
                                {user.is_active ? (
                                  <ToggleRight className="w-5 h-5" />
                                ) : (
                                  <ToggleLeft className="w-5 h-5" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteClick(user)}
                                className="h-8 w-8 p-0 hover:bg-rose-50 hover:text-rose-700"
                                title="Eliminar usuario"
                                data-testid={`delete-user-${user.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          )}
                          {user.id === currentUser?.id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditClick(user)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              title="Editar mi perfil"
                              data-testid={`edit-user-${user.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Create User Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Nuevo Usuario</DialogTitle>
              <DialogDescription>
                Crea una nueva cuenta de usuario para el sistema
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre Completo *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Juan Pérez"
                  data-testid="user-name-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="username">Nombre de Usuario *</Label>
                <Input
                  id="username"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value.toLowerCase().replace(/\s/g, ''))}
                  placeholder="juanperez"
                  data-testid="user-username-input"
                />
                <p className="text-xs text-slate-500">Solo letras minúsculas y números, sin espacios</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña *</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                    className="pr-10"
                    data-testid="user-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-slate-500">8+ caracteres, mayúscula, minúscula y número</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Rol *</Label>
                <Select
                  value={formData.role}
                  onValueChange={(value) => handleInputChange('role', value)}
                >
                  <SelectTrigger data-testid="user-role-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="superadmin">Super Admin</SelectItem>
                    <SelectItem value="admin">Administrador</SelectItem>
                    <SelectItem value="usuario">Usuario</SelectItem>
                    <SelectItem value="optica">Óptica</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCloseDialog}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting}
                  data-testid="user-submit-button"
                >
                  {submitting ? 'Creando...' : 'Crear Usuario'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit User Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit'] flex items-center gap-2">
                <Pencil className="w-5 h-5 text-[#0F6E56]" />
                Editar Usuario
              </DialogTitle>
              <DialogDescription>
                Modifica la información de <span className="font-semibold">{userToEdit?.username}</span>
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              {/* Info del usuario */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-sm text-slate-600">
                  <span className="font-medium">Usuario:</span> {userToEdit?.username}
                </p>
                <p className="text-sm text-slate-600">
                  <span className="font-medium">Creado:</span> {userToEdit?.created_at ? formatDate(userToEdit.created_at) : 'N/A'}
                </p>
              </div>

              {/* Nombre */}
              <div className="space-y-2">
                <Label htmlFor="edit-name">Nombre Completo *</Label>
                <Input
                  id="edit-name"
                  value={editFormData.name}
                  onChange={(e) => handleEditInputChange('name', e.target.value)}
                  placeholder="Juan Pérez"
                  data-testid="edit-user-name-input"
                />
              </div>

              {/* Rol - solo editable si no es el usuario actual */}
              <div className="space-y-2">
                <Label htmlFor="edit-role">Rol</Label>
                <Select
                  value={editFormData.role}
                  onValueChange={(value) => handleEditInputChange('role', value)}
                  disabled={userToEdit?.id === currentUser?.id}
                >
                  <SelectTrigger data-testid="edit-user-role-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="superadmin">Super Admin</SelectItem>
                    <SelectItem value="admin">Administrador</SelectItem>
                    <SelectItem value="usuario">Usuario</SelectItem>
                    <SelectItem value="optica">Óptica</SelectItem>
                  </SelectContent>
                </Select>
                {userToEdit?.id === currentUser?.id && (
                  <p className="text-xs text-amber-600">No puedes cambiar tu propio rol</p>
                )}
              </div>

              {/* Estado activo/inactivo */}
              {userToEdit?.id !== currentUser?.id && (
                <div className="space-y-2">
                  <Label>Estado del Usuario</Label>
                  <div className="flex items-center gap-4">
                    <button
                      type="button"
                      onClick={() => handleEditInputChange('is_active', true)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                        editFormData.is_active
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                          : 'border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                      data-testid="edit-user-active-btn"
                    >
                      <ToggleRight className="w-4 h-4" />
                      Activo
                    </button>
                    <button
                      type="button"
                      onClick={() => handleEditInputChange('is_active', false)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                        !editFormData.is_active
                          ? 'border-rose-500 bg-rose-50 text-rose-700'
                          : 'border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                      data-testid="edit-user-inactive-btn"
                    >
                      <ToggleLeft className="w-4 h-4" />
                      Inactivo
                    </button>
                  </div>
                </div>
              )}

              {/* Cambiar contraseña */}
              <div className="space-y-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2 text-amber-800">
                    <KeyRound className="w-4 h-4" />
                    Cambiar Contraseña
                  </Label>
                  <button
                    type="button"
                    onClick={() => {
                      setChangePassword(!changePassword);
                      if (!changePassword) {
                        handleEditInputChange('password', '');
                      }
                    }}
                    className={`px-3 py-1 text-sm rounded-full transition-all ${
                      changePassword
                        ? 'bg-amber-200 text-amber-800'
                        : 'bg-white text-amber-700 border border-amber-300'
                    }`}
                  >
                    {changePassword ? 'Cancelar' : 'Cambiar'}
                  </button>
                </div>
                
                {changePassword && (
                  <div className="space-y-2">
                    <div className="relative">
                      <Input
                        id="edit-password"
                        type={showEditPassword ? "text" : "password"}
                        value={editFormData.password}
                        onChange={(e) => handleEditInputChange('password', e.target.value)}
                        placeholder="Nueva contraseña"
                        className="pr-10 bg-white"
                        data-testid="edit-user-password-input"
                      />
                      <button
                        type="button"
                        onClick={() => setShowEditPassword(!showEditPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showEditPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-xs text-amber-700">
                      Requisitos: 8+ caracteres, 1 mayúscula, 1 minúscula, 1 número
                    </p>
                  </div>
                )}
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setEditDialogOpen(false)}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting}
                  data-testid="edit-user-submit-button"
                >
                  {submitting ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
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
