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
  Glasses
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

const Usuarios = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [formData, setFormData] = useState(initialFormState);
  const [submitting, setSubmitting] = useState(false);

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
      const message = error.response?.data?.detail || 'Error al crear el usuario';
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
      const message = error.response?.data?.detail || 'Error al eliminar el usuario';
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
                            <div className="flex items-center justify-end gap-2">
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
                                data-testid={`delete-user-${user.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
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
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  data-testid="user-password-input"
                />
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

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle className="font-['Outfit']">Eliminar Usuario</DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas eliminar a "{userToDelete?.name}"? 
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
