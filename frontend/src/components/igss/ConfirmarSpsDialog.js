import React, { useState } from 'react';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../ui/alert-dialog';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { igssLibroApi } from '../../services/api';

// Confirmar contra la hoja física el No. SPS de una orden marcada "Revisar SPS" (solo roles del libro)
export const ConfirmarSpsDialog = ({ orden, onClose, onSaved }) => {
  const [enviando, setEnviando] = useState(false);
  const confirmar = async () => {
    setEnviando(true);
    try {
      await igssLibroApi.confirmarSps(orden.id);
      toast.success(`No. SPS ${orden.no_sps} confirmado`);
      onClose();
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo confirmar el No. SPS');
    } finally {
      setEnviando(false);
    }
  };
  return (
    <AlertDialog open={!!orden} onOpenChange={(v) => !v && !enviando && onClose()}>
      <AlertDialogContent data-testid="confirmar-sps-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Confirmar No. SPS {orden?.numero_libro}</AlertDialogTitle>
          <AlertDialogDescription>
            Compare con la hoja física: <b className="font-mono text-slate-800">{orden?.no_sps}</b> de {orden?.paciente_nombre}.
            Si el número está mal escrito, corríjalo primero en la orden. Al confirmar queda registrado quién y cuándo.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={enviando} data-testid="confirmar-sps-cancelar">Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={(e) => { e.preventDefault(); confirmar(); }} disabled={enviando} data-testid="confirmar-sps-btn">
            {enviando && <Loader2 className="w-4 h-4 mr-1 animate-spin" />} Coincide con la hoja
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
