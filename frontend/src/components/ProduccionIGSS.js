import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { Skeleton } from './ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { Printer, FolderOpen, Download } from 'lucide-react';
import { igssNogApi, igssUnitApi, igssLibroApi } from '../services/api';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
const fmtDia = (f) => (f ? String(f).slice(0, 10).split('-').reverse().join('/') : '—');
const Q = (n) => `Q ${Number(n || 0).toLocaleString('es-GT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const ESTADOS = [
  { key: 'impreso', label: 'Impreso' },
  { key: 'enviado', label: 'Enviado' },
  { key: 'facturado', label: 'Facturado' },
  { key: 'pagado', label: 'Pagado' },
];
const COBRO = ['facturado', 'pagado'];

export const ProduccionIGSS = () => {
  const navigate = useNavigate();
  const [modo, setModo] = useState('dia');
  const hoy = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Guatemala' });
  const [fecha, setFecha] = useState(hoy);
  const [desde, setDesde] = useState(hoy);
  const [hasta, setHasta] = useState(hoy);
  const [unidadId, setUnidadId] = useState('all');
  const [nog, setNog] = useState('');
  const [unidades, setUnidades] = useState([]);
  const [rows, setRows] = useState([]);
  const [totales, setTotales] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    igssUnitApi.getAll().then((r) => setUnidades(r.data?.data || r.data || [])).catch(() => setUnidades([]));
  }, []);

  const params = useCallback(() => {
    const p = {};
    if (modo === 'dia') p.fecha = fecha;
    else { p.desde = desde; p.hasta = hasta; }
    if (unidadId && unidadId !== 'all') p.unidad_id = unidadId;
    if (nog.trim()) p.nog = nog.trim();
    return p;
  }, [modo, fecha, desde, hasta, unidadId, nog]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await igssNogApi.getProduccion(params());
      setRows(res.data?.data || []);
      setTotales(res.data?.totales || null);
    } catch (e) {
      toast.error('Error al cargar la producción');
      setRows([]); setTotales(null);
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    const t = setTimeout(() => { fetchData(); }, 350);
    return () => clearTimeout(t);
  }, [fetchData]);

  const toggleEstado = async (row, key) => {
    const nuevo = !row[key];
    setRows((prev) => prev.map((r) => r.orden_id === row.orden_id ? { ...r, [key]: nuevo } : r));
    try {
      await igssLibroApi.editar(row.orden_id, { [key]: nuevo });
      toast.success(`${ESTADOS.find((e) => e.key === key)?.label}: ${nuevo ? 'marcado' : 'desmarcado'}`);
    } catch (e) {
      setRows((prev) => prev.map((r) => r.orden_id === row.orden_id ? { ...r, [key]: !nuevo } : r));
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'No se pudo actualizar el estado');
    }
    fetchData();
  };

  const guardarCosto = async (row, valor) => {
    const num = parseFloat(valor);
    if (isNaN(num) || num === row.costo) return;
    try {
      await igssLibroApi.editar(row.orden_id, { costo_override: num });
      toast.success('Costo actualizado');
      fetchData();
    } catch (e) {
      toast.error('No se pudo actualizar el costo');
    }
  };

  const abrirExpediente = (row) => navigate(`/evaluacion-oftalmologica?paciente_id=${row.paciente_id}`);

  const imprimirExpediente = async (row) => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/evaluaciones/${row.evaluacion_id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` }, responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
      await igssLibroApi.editar(row.orden_id, { impreso: true });
      fetchData();
    } catch (e) {
      toast.error('No se pudo generar el PDF');
    }
  };

  const exportarExcel = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(igssNogApi.produccionExcelUrl(params()), {
        headers: { Authorization: `Bearer ${token}` }, responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.download = `produccion_igss.xlsx`; a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error('No se pudo exportar');
    }
  };

  // Agrupar por unidad -> NOG
  const grupos = {};
  rows.forEach((r) => {
    const uk = r.unidad_nombre || 'Sin unidad';
    const nk = r.nog || '—';
    grupos[uk] = grupos[uk] || { total: 0, monto: 0, nogs: {} };
    grupos[uk].total += 1; grupos[uk].monto += r.costo;
    grupos[uk].nogs[nk] = grupos[uk].nogs[nk] || { rows: [], monto: 0 };
    grupos[uk].nogs[nk].rows.push(r);
    grupos[uk].nogs[nk].monto += r.costo;
  });

  return (
    <div className="space-y-4" data-testid="produccion-igss">
      {/* Filtros */}
      <Card className="card-teal">
        <CardContent className="pt-4 flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Periodo</Label>
            <Select value={modo} onValueChange={setModo}>
              <SelectTrigger className="input-teal h-9 w-32" data-testid="prod-modo"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="dia">Día</SelectItem>
                <SelectItem value="rango">Rango</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {modo === 'dia' ? (
            <div className="space-y-1">
              <Label className="text-xs">Fecha</Label>
              <Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="input-teal h-9 w-40" data-testid="prod-fecha" />
            </div>
          ) : (
            <>
              <div className="space-y-1">
                <Label className="text-xs">Desde</Label>
                <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="input-teal h-9 w-40" data-testid="prod-desde" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Hasta</Label>
                <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="input-teal h-9 w-40" data-testid="prod-hasta" />
              </div>
            </>
          )}
          <div className="space-y-1">
            <Label className="text-xs">Unidad</Label>
            <Select value={unidadId} onValueChange={setUnidadId}>
              <SelectTrigger className="input-teal h-9 w-48" data-testid="prod-unidad"><SelectValue placeholder="Todas" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las unidades</SelectItem>
                {unidades.map((u) => <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">NOG</Label>
            <Input value={nog} onChange={(e) => setNog(e.target.value)} placeholder="Filtrar NOG" className="input-teal h-9 w-32" data-testid="prod-nog" />
          </div>
          <Button variant="outline" onClick={exportarExcel} className="h-9 text-emerald-700 border-emerald-200" data-testid="prod-export">
            <Download className="w-4 h-4 mr-1" /> Exportar
          </Button>
        </CardContent>
      </Card>

      {/* Barra de totales */}
      {totales && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2" data-testid="prod-totales">
          <TotCard label="Órdenes" value={totales.servicios} />
          <TotCard label="Producción" value={Q(totales.total_costo)} />
          <TotCard label="Pagado" value={Q(totales.total_pagado)} accent="text-green-700" />
          <TotCard label="Pendiente" value={Q(totales.total_pendiente)} accent="text-amber-700" />
          <TotCard label="Facturado" value={`${totales.por_estado.facturado.cantidad} · ${Q(totales.por_estado.facturado.monto)}`} />
          <TotCard label="Enviado" value={`${totales.por_estado.enviado.cantidad} · ${Q(totales.por_estado.enviado.monto)}`} />
        </div>
      )}

      {loading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <Card><CardContent className="py-10 text-center text-sm text-gray-500" data-testid="prod-vacio">No hay órdenes IGSS atendidas en el periodo seleccionado.</CardContent></Card>
      ) : (
        Object.entries(grupos).map(([unidad, g]) => (
          <Card key={unidad} data-testid={`prod-unidad-${unidad}`}>
            <CardHeader className="py-3">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span>{unidad}</span>
                <span className="text-xs font-normal text-gray-500">{g.total} orden(es) · {Q(g.monto)}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-4">
              {Object.entries(g.nogs).map(([nk, gn]) => (
                <div key={nk}>
                  <div className="flex items-center justify-between text-xs font-semibold text-blue-700 bg-blue-50 rounded px-2 py-1 mb-1">
                    <span className="flex items-center gap-1.5">
                      {gn.rows[0]?.numero_nog ? `NOG ${nk}` : nk}
                      <Badge className="bg-white text-blue-700 border border-blue-200 text-[10px] font-medium">{gn.rows[0]?.modalidad || '—'}</Badge>
                    </span>
                    <span>{gn.rows.length} · {Q(gn.monto)}</span>
                  </div>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="table-header">Paciente</TableHead>
                          <TableHead className="table-header">Exp.</TableHead>
                          <TableHead className="table-header">No. SPS</TableHead>
                          <TableHead className="table-header">Procedimiento</TableHead>
                          <TableHead className="table-header">Médico</TableHead>
                          <TableHead className="table-header">1ª atención</TableHead>
                          <TableHead className="table-header text-center">Dosis</TableHead>
                          <TableHead className="table-header">Costo (Q)</TableHead>
                          {ESTADOS.map((e) => <TableHead key={e.key} className="table-header text-center">{e.label}</TableHead>)}
                          <TableHead className="table-header text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {gn.rows.map((r) => (
                          <TableRow key={r.orden_id} data-testid={`prod-row-${r.orden_id}`}>
                            <TableCell className="font-medium">
                              {r.paciente_nombre}
                              {!r.paciente_activo && <span className="ml-1 text-[10px] text-gray-400">(inactivo)</span>}
                            </TableCell>
                            <TableCell className="font-mono text-xs">{r.expediente || '—'}</TableCell>
                            <TableCell className="text-xs">
                              {r.no_sps || '—'}
                              {r.sps_por_revisar && (
                                <Badge variant="outline" className="ml-1 h-5 px-1.5 text-[10px] bg-amber-50 text-amber-700 border-amber-300 whitespace-nowrap" title="Confirme el No. SPS en el Libro IGSS antes de facturar" data-testid={`prod-revisar-sps-${r.orden_id}`}>Revisar SPS</Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-xs">{r.procedimiento || '—'}</TableCell>
                            <TableCell className="text-xs">{r.medico_nombre || '—'}</TableCell>
                            <TableCell className="text-xs">{fmtDia(r.fecha)}</TableCell>
                            <TableCell className="text-xs text-center" data-testid={`prod-dosis-${r.orden_id}`}>{r.dosis_aplicadas} / {r.dosis_autorizadas}</TableCell>
                            <TableCell>
                              <Input
                                key={`${r.orden_id}-${r.costo}`}
                                type="number" step="0.01" min="0" defaultValue={r.costo}
                                onBlur={(e) => guardarCosto(r, e.target.value)}
                                className={`input-teal h-8 w-24 text-xs ${r.costo_editado ? 'border-amber-300' : ''}`}
                                data-testid={`prod-costo-${r.orden_id}`}
                              />
                            </TableCell>
                            {ESTADOS.map((e) => (
                              <TableCell key={e.key} className="text-center">
                                <Checkbox checked={!!r[e.key]} onCheckedChange={() => toggleEstado(r, e.key)} data-testid={`prod-${e.key}-${r.orden_id}`}
                                  disabled={r.sps_por_revisar && COBRO.includes(e.key) && !r[e.key]}
                                  title={r.sps_por_revisar && COBRO.includes(e.key) ? 'Confirme el No. SPS antes de facturar' : undefined} />
                              </TableCell>
                            ))}
                            <TableCell className="text-right whitespace-nowrap">
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Abrir expediente" onClick={() => abrirExpediente(r)} data-testid={`prod-abrir-${r.orden_id}`}>
                                <FolderOpen className="w-4 h-4 text-blue-600" />
                              </Button>
                              {r.evaluacion_id && (
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Imprimir expediente" onClick={() => imprimirExpediente(r)} data-testid={`prod-imprimir-${r.orden_id}`}>
                                  <Printer className="w-4 h-4 text-emerald-600" />
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
};

const TotCard = ({ label, value, accent }) => (
  <div className="rounded-lg border bg-white p-3">
    <div className="text-xs text-gray-500">{label}</div>
    <div className={`text-sm font-semibold ${accent || 'text-slate-800'}`}>{value}</div>
  </div>
);

export default ProduccionIGSS;
