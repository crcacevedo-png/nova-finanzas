// Diálogo para crear/editar responsables
import React from 'react';
import { RefreshCw, CheckCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { TIPOS_RESPONSABLE } from './constants';

const CXCResponsableDialog = ({
  open,
  onOpenChange,
  editando,
  form,
  setForm,
  submitting,
  onGuardar,
  onCancel
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {editando ? 'Editar Responsable' : 'Nuevo Responsable'}
          </DialogTitle>
          <DialogDescription>
            Defina los datos del responsable de las cuentas por cobrar
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Tipo */}
          <div>
            <Label>Tipo de Responsable</Label>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {TIPOS_RESPONSABLE.map(tipo => {
                const Icon = tipo.icon;
                return (
                  <button
                    key={tipo.value}
                    onClick={() => setForm({...form, tipo: tipo.value})}
                    className={`
                      p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all
                      ${form.tipo === tipo.value 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'}
                    `}
                  >
                    <div className={`w-8 h-8 rounded-full ${tipo.color} flex items-center justify-center`}>
                      <Icon className="h-4 w-4 text-white" />
                    </div>
                    <span className="text-xs">{tipo.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          
          {/* Nombre */}
          <div>
            <Label>Nombre *</Label>
            <Input
              value={form.nombre}
              onChange={(e) => setForm({...form, nombre: e.target.value})}
              placeholder="Nombre del responsable"
              className="mt-2"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>NIT</Label>
              <Input
                value={form.nit}
                onChange={(e) => setForm({...form, nit: e.target.value})}
                placeholder="NIT"
                className="mt-2"
              />
            </div>
            <div>
              <Label>Teléfono</Label>
              <Input
                value={form.telefono}
                onChange={(e) => setForm({...form, telefono: e.target.value})}
                placeholder="Teléfono"
                className="mt-2"
              />
            </div>
          </div>
          
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm({...form, email: e.target.value})}
              placeholder="correo@ejemplo.com"
              className="mt-2"
            />
          </div>
          
          <div>
            <Label>Dirección</Label>
            <Input
              value={form.direccion}
              onChange={(e) => setForm({...form, direccion: e.target.value})}
              placeholder="Dirección"
              className="mt-2"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Persona de Contacto</Label>
              <Input
                value={form.contacto}
                onChange={(e) => setForm({...form, contacto: e.target.value})}
                placeholder="Nombre del contacto"
                className="mt-2"
              />
            </div>
            <div>
              <Label>Plazo de Pago (días)</Label>
              <Input
                type="number"
                min="0"
                max="365"
                value={form.plazo_dias}
                onChange={(e) => setForm({...form, plazo_dias: parseInt(e.target.value) || 30})}
                className="mt-2"
              />
            </div>
          </div>
          
          <div>
            <Label>Notas</Label>
            <Textarea
              value={form.notas}
              onChange={(e) => setForm({...form, notas: e.target.value})}
              placeholder="Notas adicionales..."
              rows={2}
              className="mt-2"
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
          <Button 
            className="bg-blue-600 hover:bg-blue-700"
            onClick={onGuardar}
            disabled={submitting || !form.nombre.trim()}
          >
            {submitting ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                {editando ? 'Actualizar' : 'Crear'}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CXCResponsableDialog;
