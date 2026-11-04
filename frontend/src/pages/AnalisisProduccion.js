import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import axios from 'axios';
import { formatCurrency } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  BarChart3, TrendingUp, ShoppingCart, Receipt, Users, Stethoscope, Tag, Package
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PERIODOS = [
  { value: 'hoy', label: 'Hoy' },
  { value: 'semana', label: 'Esta semana' },
  { value: 'mes', label: 'Este mes' },
  { value: 'rango', label: 'Rango' },
];

const KpiCard = ({ title, value, icon: Icon, testId }) => (
  <Card className="card-teal card-hover" data-testid={testId}>
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>{title}</p>
          <p className="text-2xl font-bold metric-teal">{value}</p>
        </div>
        <div className="p-3 rounded-xl gradient-teal">
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const AnalisisProduccion = () => {
  const [periodo, setPeriodo] = useState('mes');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { periodo };
      if (periodo === 'rango') { params.desde = desde; params.hasta = hasta; }
      const res = await axios.get(`${API_URL}/ventas/analisis`, { params });
      setData(res.data);
      if (periodo !== 'rango') {
        setDesde(res.data?.desde || '');
        setHasta(res.data?.hasta || '');
      }
    } catch (error) {
      console.error('Error fetching análisis:', error);
    } finally {
      setLoading(false);
    }
  }, [periodo, desde, hasta]);

  useEffect(() => {
    if (periodo !== 'rango') fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo]);

  const kpis = data?.kpis || {};

  return (
    <Layout>
      <div className="space-y-6 p-1" data-testid="analisis-produccion-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <BarChart3 className="w-6 h-6 text-teal-600" /> Análisis de Producción
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Ventas de clínica (Punto de Venta){data ? ` · ${data.desde} — ${data.hasta}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {PERIODOS.map(p => (
              <Button
                key={p.value}
                size="sm"
                variant={periodo === p.value ? 'default' : 'outline'}
                className={periodo === p.value ? 'gradient-teal text-white h-8' : 'h-8'}
                onClick={() => setPeriodo(p.value)}
                data-testid={`periodo-${p.value}`}
              >{p.label}</Button>
            ))}
          </div>
        </div>

        {periodo === 'rango' && (
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="text-xs text-slate-500">Desde</label>
              <Input type="date" value={desde} onChange={e => setDesde(e.target.value)} className="h-8" data-testid="analisis-desde" />
            </div>
            <div>
              <label className="text-xs text-slate-500">Hasta</label>
              <Input type="date" value={hasta} onChange={e => setHasta(e.target.value)} className="h-8" data-testid="analisis-hasta" />
            </div>
            <Button size="sm" className="gradient-teal text-white h-8" onClick={fetchData} disabled={!desde || !hasta} data-testid="analisis-aplicar">
              Aplicar
            </Button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-20 text-slate-400">Cargando análisis...</div>
        ) : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <KpiCard title="Total Vendido" value={formatCurrency(kpis.total_vendido || 0)} icon={TrendingUp} testId="kpi-total" />
              <KpiCard title="N° de Ventas" value={`${kpis.num_ventas || 0}`} icon={ShoppingCart} testId="kpi-ventas" />
              <KpiCard title="Ticket Promedio" value={formatCurrency(kpis.ticket_promedio || 0)} icon={Receipt} testId="kpi-ticket" />
            </div>

            {/* Tendencia */}
            <Card className="card-teal">
              <CardHeader><CardTitle className="text-lg flex items-center gap-2"><TrendingUp className="w-5 h-5 text-teal-600" /> Tendencia por día</CardTitle></CardHeader>
              <CardContent>
                {(data?.tendencia || []).length === 0 ? (
                  <p className="text-center text-slate-400 py-10">Sin ventas en el período</p>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={data.tendencia}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="fecha" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v) => formatCurrency(v)} />
                      <Line type="monotone" dataKey="monto" stroke="#0d9488" strokeWidth={2} dot={{ r: 3 }} name="Ventas" />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            {/* Top productos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card className="card-teal" data-testid="top-ingresos">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Package className="w-5 h-5 text-teal-600" /> Top productos (ingresos)</CardTitle></CardHeader>
                <CardContent>
                  <RankTable rows={data?.top_productos_ingresos} labelKey="nombre" valueFmt={(r) => formatCurrency(r.monto)} sub={(r) => `${r.cantidad} u.`} empty="Sin datos" />
                </CardContent>
              </Card>
              <Card className="card-teal" data-testid="top-unidades">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Package className="w-5 h-5 text-teal-600" /> Top productos (unidades)</CardTitle></CardHeader>
                <CardContent>
                  <RankTable rows={data?.top_productos_unidades} labelKey="nombre" valueFmt={(r) => `${r.cantidad} u.`} sub={(r) => formatCurrency(r.monto)} empty="Sin datos" />
                </CardContent>
              </Card>
            </div>

            {/* Cajero / Médico */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card className="card-teal" data-testid="por-cajero">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Users className="w-5 h-5 text-teal-600" /> Ventas por cajero</CardTitle></CardHeader>
                <CardContent>
                  <RankTable rows={data?.por_cajero} labelKey="vendedor_nombre" valueFmt={(r) => formatCurrency(r.monto)} sub={(r) => `${r.num_ventas} ventas`} empty="Sin datos" />
                </CardContent>
              </Card>
              <Card className="card-teal" data-testid="por-medico">
                <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Stethoscope className="w-5 h-5 text-teal-600" /> Ventas por médico que refiere</CardTitle></CardHeader>
                <CardContent>
                  <RankTable rows={data?.por_medico} labelKey="medico_nombre" valueFmt={(r) => formatCurrency(r.monto)} sub={(r) => `${r.num_ventas} ventas`} empty="Sin datos" />
                </CardContent>
              </Card>
            </div>

            {/* Categoría */}
            <Card className="card-teal" data-testid="por-categoria">
              <CardHeader><CardTitle className="text-lg flex items-center gap-2"><Tag className="w-5 h-5 text-teal-600" /> Ventas por categoría</CardTitle></CardHeader>
              <CardContent>
                <RankTable rows={data?.por_categoria} labelKey="categoria" valueFmt={(r) => formatCurrency(r.monto)} sub={(r) => `${r.cantidad} u.`} empty="Sin datos" />
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </Layout>
  );
};

const RankTable = ({ rows, labelKey, valueFmt, sub, empty }) => {
  if (!rows || rows.length === 0) return <p className="text-center text-slate-400 py-8">{empty}</p>;
  const max = Math.max(...rows.map(r => Math.abs(r.monto ?? r.cantidad ?? 0)), 1);
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8">#</TableHead>
          <TableHead>Nombre</TableHead>
          <TableHead className="text-right">Monto / Detalle</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={i}>
            <TableCell><Badge variant="outline">{i + 1}</Badge></TableCell>
            <TableCell className="font-medium truncate max-w-[220px]">{r[labelKey]}</TableCell>
            <TableCell className="text-right">
              <div className="font-semibold text-slate-800">{valueFmt(r)}</div>
              <div className="text-xs text-slate-400">{sub(r)}</div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default AnalisisProduccion;
