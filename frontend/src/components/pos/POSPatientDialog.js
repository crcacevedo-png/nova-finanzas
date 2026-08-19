// Diálogo de selección de paciente para POS
import React from 'react';
import { Search, RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Input } from '../ui/input';

const POSPatientDialog = ({
  open,
  onOpenChange,
  searchValue,
  onSearchChange,
  searching,
  results,
  onSelectPatient
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Seleccionar Paciente</DialogTitle>
          <DialogDescription>
            Busca un paciente por nombre, DPI o teléfono
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Buscar paciente..."
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10"
              autoFocus
            />
          </div>
          
          <div className="max-h-60 overflow-y-auto space-y-2">
            {searching ? (
              <div className="text-center py-4 text-slate-500">
                <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2" />
                Buscando...
              </div>
            ) : results.length === 0 ? (
              <div className="text-center py-4 text-slate-500">
                {searchValue.length >= 2 ? 'No se encontraron pacientes' : 'Escribe al menos 2 caracteres'}
              </div>
            ) : (
              results.map(p => (
                <div
                  key={p.id}
                  className="p-3 rounded-lg cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  onClick={() => onSelectPatient(p)}
                >
                  <p className="font-medium">
                    {p.primer_nombre} {p.segundo_nombre} {p.primer_apellido} {p.segundo_apellido}
                  </p>
                  <p className="text-sm text-slate-500">
                    {p.dpi || 'Sin DPI'} • {p.telefono || 'Sin teléfono'}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default POSPatientDialog;
