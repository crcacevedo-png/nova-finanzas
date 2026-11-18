import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { igssLibroApi } from '../../services/api';

// Confirma con la hoja física las dosis autorizadas de una orden marcada "Confirmar dosis"
export const ConfirmarDosisDialog = ({ orden, onOpenChange, onSaved }) => {
  const [dosis, setDosis] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { if (orden) setDosis(String(orden.dosis_autorizadas || 1)); }, [orden]);

  const confirmar = async () => {
    const n = Number(dosis);
    if (!Number.isInteger(n) || n < 1) { toast.error('Indique las dosis autorizadas en la hoja'); return; }
    setEnviando(true);
    try {
      const { data } = await igssLibroApi.confirmarDosis(orden.id, n);
      toast.success(`Dosis confirmadas: ${data.numero_libro} queda ${data.estado === 'completa' ? 'completa' : data.estado.replace('_', ' ')}`);
      onOpenChange(false);
      onSaved?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudieron confirmar las dosis');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={!!orden} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="confirmar-dosis-dialog">
        <DialogHeader>
          <DialogTitle>Confirmar dosis {orden?.numero_libro}</DialogTitle>
          <DialogDescription>
            Revise la hoja física ({orden?.no_sps}). Lleva {orden?.dosis_aplicadas ?? 0} dosis aplicadas. Mientras no se confirme, la orden no llega a completa ni se cobra.
          </DialogDescription>
        </DialogHeader>
        <Label className="text-xs">Dosis autorizadas en la hoja *</Label>
        <Input type="number" min={1} value={dosis} onChange={(e) => setDosis(e.target.value)} data-testid="confirmar-dosis-input" />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={confirmar} disabled={enviando} className="bg-teal-600 hover:bg-teal-700" data-testid="confirmar-dosis-guardar">
            {enviando && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Confirmar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
