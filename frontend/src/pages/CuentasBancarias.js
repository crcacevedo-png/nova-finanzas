import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { 
  Plus, 
  Pencil,
  Trash2,
  Building2,
  CreditCard,
  Tag
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
import { bankAccountApi } from '../services/api';

const initialFormState = {
  bank_name: '',
  account_number: '',
  account_alias: ''
};

const CuentasBancarias = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [accountToDelete, setAccountToDelete] = useState(null);
  const [formData, setFormData] = useState(initialFormState);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await bankAccountApi.getAll();
      setAccounts(response.data.data || []);
    } catch (error) {
      console.error('Error fetching bank accounts:', error);
      toast.error('Error al cargar las cuentas bancarias');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (account = null) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        bank_name: account.bank_name,
        account_number: account.account_number,
        account_alias: account.account_alias
      });
    } else {
      setEditingAccount(null);
      setFormData(initialFormState);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingAccount(null);
    setFormData(initialFormState);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.bank_name || !formData.account_number || !formData.account_alias) {
      toast.error('Por favor completa todos los campos');
      return;
    }

    setSubmitting(true);
    try {
      if (editingAccount) {
        await bankAccountApi.update(editingAccount.id, formData);
        toast.success('Cuenta bancaria actualizada');
      } else {
        await bankAccountApi.create(formData);
        toast.success('Cuenta bancaria creada');
      }
      handleCloseDialog();
      fetchAccounts();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al guardar la cuenta';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteClick = (account) => {
    setAccountToDelete(account);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!accountToDelete) return;

    try {
      await bankAccountApi.delete(accountToDelete.id);
      toast.success('Cuenta bancaria eliminada');
      fetchAccounts();
    } catch (error) {
      const message = error.response?.data?.detail || 'Error al eliminar la cuenta';
      toast.error(message);
    } finally {
      setDeleteDialogOpen(false);
      setAccountToDelete(null);
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="space-y-6 animate-fade-in" data-testid="cuentas-bancarias-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Cuentas Bancarias
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Administra las cuentas bancarias de la clínica
            </p>
          </div>
          <Button 
            onClick={() => handleOpenDialog()}
            className="btn-primary"
            data-testid="add-account-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nueva Cuenta
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#E6F0FA]">
                <Building2 className="w-5 h-5 text-[#2B5EA7]" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Cuentas</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {accounts.length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#E1F5EE]">
                <CreditCard className="w-5 h-5 text-[#0F6E56]" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Cuentas Activas</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {accounts.filter(a => a.is_active).length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="card-metrics border-0 shadow-none">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-[#FEF4E0]">
                <Tag className="w-5 h-5 text-[#8B6914]" />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Bancos</p>
                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  {new Set(accounts.map(a => a.bank_name)).size}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Table */}
        <Card className="card-teal">
          <CardHeader>
            <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              Lista de Cuentas
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : accounts.length === 0 ? (
              <div className="p-12 text-center">
                <Building2 className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-hint)' }} />
                <p style={{ color: 'var(--text-secondary)' }}>No hay cuentas bancarias registradas</p>
                <Button 
                  onClick={() => handleOpenDialog()}
                  className="btn-primary mt-4"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Agregar primera cuenta
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow style={{ backgroundColor: 'var(--bg-metrics)' }}>
                      <TableHead className="table-header">Nombre</TableHead>
                      <TableHead className="table-header">Banco</TableHead>
                      <TableHead className="table-header">Número de Cuenta</TableHead>
                      <TableHead className="table-header text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {accounts.map((account) => (
                      <TableRow 
                        key={account.id} 
                        className="table-row-hover"
                        data-testid={`account-row-${account.id}`}
                      >
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-[#E1F5EE] flex items-center justify-center">
                              <span className="text-[#0F6E56] font-semibold">
                                {account.account_alias.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                                {account.account_alias}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="badge-admin px-2 py-1 rounded-md text-sm">
                            {account.bank_name}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                            {account.account_number}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenDialog(account)}
                              className="h-8 w-8 p-0 hover:bg-[#E1F5EE] hover:text-[#0F6E56]"
                              data-testid={`edit-account-${account.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(account)}
                              className="h-8 w-8 p-0 hover:bg-[#FDE8E8] hover:text-[#C53030]"
                              data-testid={`delete-account-${account.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[450px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>
                {editingAccount ? 'Editar Cuenta Bancaria' : 'Nueva Cuenta Bancaria'}
              </DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                {editingAccount 
                  ? 'Modifica los datos de la cuenta bancaria'
                  : 'Ingresa los datos de la nueva cuenta bancaria'
                }
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bank_name">Banco *</Label>
                <Input
                  id="bank_name"
                  value={formData.bank_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, bank_name: e.target.value }))}
                  placeholder="Ej: Banco Industrial, BAM, Banrural..."
                  className="input-teal"
                  data-testid="account-bank-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="account_number">Número de Cuenta *</Label>
                <Input
                  id="account_number"
                  value={formData.account_number}
                  onChange={(e) => setFormData(prev => ({ ...prev, account_number: e.target.value }))}
                  placeholder="Ej: 01-234567-89"
                  className="input-teal font-mono"
                  data-testid="account-number-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="account_alias">Nombre de la Cuenta *</Label>
                <Input
                  id="account_alias"
                  value={formData.account_alias}
                  onChange={(e) => setFormData(prev => ({ ...prev, account_alias: e.target.value }))}
                  placeholder="Ej: Cuenta Principal, Cuenta Proveedores..."
                  className="input-teal"
                  data-testid="account-alias-input"
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleCloseDialog} className="btn-outline">
                  Cancelar
                </Button>
                <Button type="submit" className="btn-primary" disabled={submitting} data-testid="account-submit-button">
                  {submitting ? 'Guardando...' : editingAccount ? 'Actualizar' : 'Crear'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-[400px]">
            <DialogHeader>
              <DialogTitle style={{ color: 'var(--text-primary)' }}>Eliminar Cuenta</DialogTitle>
              <DialogDescription style={{ color: 'var(--text-secondary)' }}>
                ¿Estás seguro de que deseas eliminar la cuenta &quot;{accountToDelete?.account_alias}&quot;? 
                Esta acción no se puede deshacer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="btn-outline">
                Cancelar
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleConfirmDelete}
                data-testid="confirm-delete-account-button"
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

export default CuentasBancarias;
