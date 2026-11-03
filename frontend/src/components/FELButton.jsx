import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from './ui/dialog';
import { FileText, Download, Ban, Loader2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { felApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

const descargarPdf = (pdfBase64, nombre) => {
  try {
    const bytes = atob(pdfBase64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) {
    toast.error('No se pudo abrir el PDF');
  }
};

// origen: 'clinica' | 'optica' ; sale: objeto con id y (opcional) fel
export const FELButton = ({ origen, sale, defaultNombre = '', onUpdated }) => {
  const { user } = useAuth();
  const esAdmin = ['superadmin', 'admin'].includes(user?.role);
  const fel = sale?.fel || null;
  const certificado = fel && fel.estado === 'certificado';
  const anulado = fel && fel.estado === 'anulado';

  const [open, setOpen] = useState(false);
  const [esCF, setEsCF] = useState(true);
  const [nit, setNit] = useState('');
  const [nombre, setNombre] = useState(defaultNombre || '');
  const [loading, setLoading] = useState(false);
  const [anularOpen, setAnularOpen] = useState(false);
  const [motivo, setMotivo] = useState('');

  const handleCertificar = async () => {
    try {
      setLoading(true);
      const res = await felApi.certificar({
        origen,
        sale_id: sale.id,
        receptor_nit: esCF ? null : nit.trim(),
        receptor_nombre: esCF ? null : nombre.trim(),
      });
      toast.success(`Factura certificada: serie ${res.data.serie} No. ${res.data.numero}`);
      if (res.data.pdf_base64) descargarPdf(res.data.pdf_base64, `factura-${sale.id}.pdf`);
      setOpen(false);
      onUpdated && onUpdated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al certificar la factura');
    } finally {
      setLoading(false);
    }
  };

  const handleVer = async () => {
    try {
      const res = await felApi.getDocumento(origen, sale.id);
      if (res.data.pdf_base64) descargarPdf(res.data.pdf_base64);
      else toast.error('No hay PDF disponible');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo obtener el documento');
    }
  };

  const handleAnular = async () => {
    if (motivo.trim().length < 3) { toast.error('Indica el motivo de anulación'); return; }
    try {
      setLoading(true);
      await felApi.anular({ origen, sale_id: sale.id, motivo: motivo.trim() });
      toast.success('Factura anulada');
      setAnularOpen(false);
      onUpdated && onUpdated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al anular');
    } finally {
      setLoading(false);
    }
  };

  if (anulado) {
    return <Badge variant="destructive" data-testid="fel-badge-anulado">FEL anulada</Badge>;
  }

  if (certificado) {
    return (
      <div className="flex items-center gap-1.5 flex-wrap">
        <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100" data-testid="fel-badge-certificado">
          <CheckCircle className="w-3 h-3 mr-1" /> FEL {fel.serie}-{fel.numero}
        </Badge>
        <Button size="sm" variant="outline" onClick={handleVer} data-testid="fel-ver-btn">
          <Download className="w-3.5 h-3.5 mr-1" /> Ver
        </Button>
        {esAdmin && (
          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => setAnularOpen(true)} data-testid="fel-anular-btn">
            <Ban className="w-3.5 h-3.5 mr-1" /> Anular
          </Button>
        )}
        <Dialog open={anularOpen} onOpenChange={setAnularOpen}>
          <DialogContent data-testid="fel-anular-dialog">
            <DialogHeader>
              <DialogTitle>Anular factura FEL</DialogTitle>
              <DialogDescription>Se anulará ante la SAT. Indica el motivo.</DialogDescription>
            </DialogHeader>
            <Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Motivo de la anulación" data-testid="fel-motivo-input" />
            <DialogFooter>
              <Button variant="outline" onClick={() => setAnularOpen(false)}>Cancelar</Button>
              <Button variant="destructive" onClick={handleAnular} disabled={loading} data-testid="fel-anular-confirm-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Anular factura'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid="fel-facturar-btn">
        <FileText className="w-3.5 h-3.5 mr-1" /> Facturar FEL
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="fel-facturar-dialog">
          <DialogHeader>
            <DialogTitle>Emitir factura electrónica (FEL)</DialogTitle>
            <DialogDescription>Se certificará ante la SAT vía Digifact.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={esCF} onChange={(e) => setEsCF(e.target.checked)} data-testid="fel-cf-checkbox" />
              Consumidor Final (sin NIT)
            </label>
            {!esCF && (
              <div className="space-y-3">
                <div>
                  <Label>NIT del cliente</Label>
                  <Input value={nit} onChange={(e) => setNit(e.target.value)} placeholder="Ej. 1234567" data-testid="fel-nit-input" />
                </div>
                <div>
                  <Label>Nombre / Razón social</Label>
                  <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre del cliente" data-testid="fel-nombre-input" />
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleCertificar} disabled={loading} data-testid="fel-certificar-confirm-btn">
              {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Certificando...</> : 'Certificar factura'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FELButton;
