import React, { useState } from 'react';
import { KeyRound, Eye, EyeOff } from 'lucide-react';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

const PwdInput = ({ id, label, value, onChange, testId }) => {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-xs">{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-teal pr-10"
          data-testid={testId}
          autoComplete="off"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          tabIndex={-1}
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
};

// Diálogo para que el usuario autenticado cambie su propia contraseña.
export const ChangePasswordDialog = ({ open, onOpenChange }) => {
  const { changePassword } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setCurrent('');
    setNext('');
    setConfirm('');
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!current || !next || !confirm) {
      toast.error('Completa todos los campos');
      return;
    }
    if (next.length < 8 || !/[A-Z]/.test(next) || !/[a-z]/.test(next) || !/\d/.test(next)) {
      toast.error('La nueva contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número');
      return;
    }
    if (next !== confirm) {
      toast.error('La nueva contraseña y su confirmación no coinciden');
      return;
    }
    if (next === current) {
      toast.error('La nueva contraseña debe ser diferente a la actual');
      return;
    }
    setSaving(true);
    try {
      await changePassword(current, next);
      toast.success('Contraseña actualizada correctamente');
      reset();
      onOpenChange(false);
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'No se pudo cambiar la contraseña');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent className="sm:max-w-[420px]" data-testid="change-password-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-[#0F6E56]" />
            Cambiar contraseña
          </DialogTitle>
          <DialogDescription>
            Ingresa tu contraseña actual y define una nueva. Por seguridad, se cerrarán tus otras sesiones.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <PwdInput id="cp-current" label="Contraseña actual" value={current} onChange={setCurrent} testId="cp-current" />
          <PwdInput id="cp-new" label="Nueva contraseña" value={next} onChange={setNext} testId="cp-new" />
          <p className="text-[11px] text-gray-500 -mt-1">Mínimo 8 caracteres, con una mayúscula, una minúscula y un número.</p>
          <PwdInput id="cp-confirm" label="Confirmar nueva contraseña" value={confirm} onChange={setConfirm} testId="cp-confirm" />
          <DialogFooter>
            <Button type="button" variant="outline" className="btn-outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" className="btn-primary" disabled={saving} data-testid="cp-submit">
              {saving ? 'Guardando...' : 'Cambiar contraseña'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default ChangePasswordDialog;
