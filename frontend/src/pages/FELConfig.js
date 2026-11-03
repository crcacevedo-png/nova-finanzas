import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { FileText, Save, AlertTriangle, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { felApi } from '../services/api';

const FELConfig = () => {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const res = await felApi.getConfig();
      setCfg(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al cargar configuración FEL');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const set = (k, v) => setCfg((p) => ({ ...p, [k]: v }));

  const handleSave = async () => {
    if (cfg.enabled && (!cfg.nit || !cfg.emisor_nombre)) {
      toast.error('Para habilitar FEL debes ingresar el NIT y el nombre del emisor');
      return;
    }
    try {
      setSaving(true);
      const payload = {
        enabled: cfg.enabled,
        environment: cfg.environment,
        nit: (cfg.nit || '').trim(),
        emisor_nombre: cfg.emisor_nombre || '',
        nombre_comercial: cfg.nombre_comercial || '',
        afiliacion_iva: cfg.afiliacion_iva || 'GEN',
        establecimiento_codigo: parseInt(cfg.establecimiento_codigo, 10) || 1,
        direccion: cfg.direccion || 'Ciudad',
        municipio: cfg.municipio || 'Guatemala',
        departamento: cfg.departamento || 'Guatemala',
        codigo_postal: cfg.codigo_postal || '01001',
        pais: 'GT',
        frase_tipo: parseInt(cfg.frase_tipo, 10) || 1,
        frase_escenario: parseInt(cfg.frase_escenario, 10) || 1,
      };
      await felApi.setConfig(payload);
      toast.success('Configuración FEL guardada');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !cfg) {
    return <Layout><div className="p-8 text-slate-400">Cargando configuración FEL...</div></Layout>;
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6" data-testid="fel-config-page">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/20"><FileText className="h-6 w-6 text-indigo-600" /></div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Facturación Electrónica (FEL)</h1>
            <p className="text-sm text-slate-500">Configuración de Digifact — Guatemala (SAT)</p>
          </div>
        </div>

        {!cfg.credenciales_configuradas && (
          <div className="flex items-center gap-2 text-amber-700 bg-amber-50 rounded-md px-3 py-2 text-sm" data-testid="fel-sin-credenciales">
            <AlertTriangle className="w-4 h-4" /> Faltan las credenciales de Digifact (usuario y contraseña). Pídelas al administrador para completarlas de forma segura.
          </div>
        )}

        <Card>
          <CardHeader><CardTitle className="text-lg">Estado</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base">Habilitar facturación FEL</Label>
                <p className="text-xs text-slate-500">Al activar, las ventas podrán certificarse ante la SAT</p>
              </div>
              <Switch checked={cfg.enabled} onCheckedChange={(v) => set('enabled', v)} data-testid="fel-enabled-switch" />
            </div>
            <div>
              <Label>Ambiente</Label>
              <Select value={cfg.environment} onValueChange={(v) => set('environment', v)}>
                <SelectTrigger data-testid="fel-env-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="test">Pruebas (sin validez fiscal)</SelectItem>
                  <SelectItem value="prod">Producción (requiere firma SAT)</SelectItem>
                </SelectContent>
              </Select>
              {cfg.environment === 'prod' && (
                <p className="text-xs text-amber-600 mt-1">En producción se requiere la firma electrónica del emisor registrada en la Agencia Virtual SAT y credenciales productivas de Digifact.</p>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              {cfg.credenciales_configuradas
                ? <><CheckCircle className="w-4 h-4 text-emerald-600" /> Credenciales de Digifact configuradas</>
                : <><AlertTriangle className="w-4 h-4 text-amber-500" /> Credenciales pendientes</>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Datos del emisor</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label>NIT del emisor *</Label>
              <Input value={cfg.nit || ''} onChange={(e) => set('nit', e.target.value.replace(/[^0-9]/g, ''))} placeholder="Solo dígitos, ej. 1234567" data-testid="fel-nit-emisor-input" />
              <p className="text-xs text-slate-400 mt-1">Se usa junto al usuario de Digifact (GT.NIT.usuario).</p>
            </div>
            <div>
              <Label>Nombre / Razón social *</Label>
              <Input value={cfg.emisor_nombre || ''} onChange={(e) => set('emisor_nombre', e.target.value)} data-testid="fel-emisor-nombre-input" />
            </div>
            <div>
              <Label>Nombre comercial</Label>
              <Input value={cfg.nombre_comercial || ''} onChange={(e) => set('nombre_comercial', e.target.value)} />
            </div>
            <div>
              <Label>Afiliación IVA</Label>
              <Select value={cfg.afiliacion_iva} onValueChange={(v) => set('afiliacion_iva', v)}>
                <SelectTrigger data-testid="fel-afiliacion-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="GEN">General (IVA 12%)</SelectItem>
                  <SelectItem value="PEQ">Pequeño Contribuyente</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Código de establecimiento</Label>
              <Input type="number" value={cfg.establecimiento_codigo} onChange={(e) => set('establecimiento_codigo', e.target.value)} data-testid="fel-establecimiento-input" />
            </div>
            <div>
              <Label>Dirección</Label>
              <Input value={cfg.direccion || ''} onChange={(e) => set('direccion', e.target.value)} />
            </div>
            <div>
              <Label>Municipio</Label>
              <Input value={cfg.municipio || ''} onChange={(e) => set('municipio', e.target.value)} />
            </div>
            <div>
              <Label>Departamento</Label>
              <Input value={cfg.departamento || ''} onChange={(e) => set('departamento', e.target.value)} />
            </div>
            <div>
              <Label>Código postal</Label>
              <Input value={cfg.codigo_postal || ''} onChange={(e) => set('codigo_postal', e.target.value)} />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button className="bg-indigo-600 hover:bg-indigo-700" onClick={handleSave} disabled={saving} data-testid="fel-save-config-btn">
            <Save className="w-4 h-4 mr-2" /> {saving ? 'Guardando...' : 'Guardar configuración'}
          </Button>
        </div>
      </div>
    </Layout>
  );
};

export default FELConfig;
