// Diálogo de receta óptica para POS
import React from 'react';
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

const POSRecetaDialog = ({
  open,
  onOpenChange,
  receta,
  setReceta
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Receta Óptica</DialogTitle>
          <DialogDescription>
            Ingresa la graduación para los lentes
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* OD - Ojo Derecho */}
          <div>
            <Label className="font-bold">Ojo Derecho (OD)</Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              <div>
                <Label className="text-xs">Esfera</Label>
                <Input
                  placeholder="-0.00"
                  value={receta.od_esfera}
                  onChange={(e) => setReceta({...receta, od_esfera: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">Cilindro</Label>
                <Input
                  placeholder="-0.00"
                  value={receta.od_cilindro}
                  onChange={(e) => setReceta({...receta, od_cilindro: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">Eje</Label>
                <Input
                  placeholder="0°"
                  value={receta.od_eje}
                  onChange={(e) => setReceta({...receta, od_eje: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">ADD</Label>
                <Input
                  placeholder="+0.00"
                  value={receta.od_add}
                  onChange={(e) => setReceta({...receta, od_add: e.target.value})}
                />
              </div>
            </div>
          </div>
          
          {/* OI - Ojo Izquierdo */}
          <div>
            <Label className="font-bold">Ojo Izquierdo (OI)</Label>
            <div className="grid grid-cols-4 gap-2 mt-2">
              <div>
                <Label className="text-xs">Esfera</Label>
                <Input
                  placeholder="-0.00"
                  value={receta.oi_esfera}
                  onChange={(e) => setReceta({...receta, oi_esfera: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">Cilindro</Label>
                <Input
                  placeholder="-0.00"
                  value={receta.oi_cilindro}
                  onChange={(e) => setReceta({...receta, oi_cilindro: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">Eje</Label>
                <Input
                  placeholder="0°"
                  value={receta.oi_eje}
                  onChange={(e) => setReceta({...receta, oi_eje: e.target.value})}
                />
              </div>
              <div>
                <Label className="text-xs">ADD</Label>
                <Input
                  placeholder="+0.00"
                  value={receta.oi_add}
                  onChange={(e) => setReceta({...receta, oi_add: e.target.value})}
                />
              </div>
            </div>
          </div>
          
          {/* DP y Altura */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Distancia Pupilar (DP)</Label>
              <Input
                placeholder="62mm"
                value={receta.dp}
                onChange={(e) => setReceta({...receta, dp: e.target.value})}
              />
            </div>
            <div>
              <Label>Altura</Label>
              <Input
                placeholder="mm"
                value={receta.altura}
                onChange={(e) => setReceta({...receta, altura: e.target.value})}
              />
            </div>
          </div>
          
          <div>
            <Label>Observaciones</Label>
            <Textarea
              placeholder="Notas sobre la receta..."
              value={receta.observaciones}
              onChange={(e) => setReceta({...receta, observaciones: e.target.value})}
              rows={2}
            />
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button className="bg-teal-600" onClick={() => onOpenChange(false)}>
            Guardar Receta
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default POSRecetaDialog;
