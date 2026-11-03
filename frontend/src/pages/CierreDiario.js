import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { formatCurrency, getGuatemalaDate } from '../services/api';
import { toast, Toaster } from 'sonner';
import {
  RefreshCw, Mail, TrendingUp, Banknote, CreditCard, Clock, ArrowDownCircle,
  Users, Calculator, CheckCircle, AlertTriangle, Stethoscope, Glasses
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const METODO_LABEL = {
  efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia',
  cheque: 'Cheque', otro: 'Otro'
};

const Card = ({ title, value, sub, color, icon: Icon, testId }) => (
  <div data-testid={testId} className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-1 shadow-sm">
    <div className="flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-wide text-gray-500">{title}</span>
      {Icon && <Icon className="w-4 h-4" style={{ color }} />}
    </div>
    <span className="text-2xl font-bold" style={{ color }}>{value}</span>
    {sub && <span className="text-[11px] text-gray-400">{sub}</span>}
  </div>
);

const MetodosTable = ({ metodos, total, testId }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm" data-testid={testId}>
    <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
      <CreditCard className="w-4 h-4 text-gray-500" /> Cobrado por método
    </h3>
    <table className="w-full text-sm">
      <tbody className="divide-y divide-gray-100">
        {['efectivo', 'tarjeta', 'transferencia', 'cheque', 'otro'].map((k) => {
          const val = (metodos && metodos[k]) || 0;
          if (val === 0 && k === 'otro') return null;
          return (
            <tr key={k} data-testid={`${testId}-${k}`}>
              <td className="py-2 text-gray-600">{METODO_LABEL[k]}</td>
              <td className="py-2 text-right font-semibold text-gray-900">{formatCurrency(val)}</td>
            </tr>
          );
        })}
        <tr className="border-t-2 border-gray-200">
          <td className="py-2 font-bold text-gray-900">Total cobrado</td>
          <td className="py-2 text-right font-bold text-green-700">{formatCurrency(total || 0)}</td>
        </tr>
      </tbody>
    </table>
  </div>
);

const UsuariosTable = ({ usuarios, testId }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm lg:col-span-2" data-testid={testId}>
    <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
      <Users className="w-4 h-4 text-gray-500" /> Ventas por usuario
    </h3>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
            <th className="py-2 pr-2">Usuario</th>
            <th className="py-2 px-2 text-center">Ventas</th>
            <th className="py-2 px-2 text-right">Facturado</th>
            <th className="py-2 px-2 text-right">Cobrado</th>
            <th className="py-2 pl-2 text-right">CxC</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {(usuarios || []).map((u) => (
            <tr key={u.usuario_id} data-testid={`${testId}-row-${u.usuario_id}`}>
              <td className="py-2 pr-2 font-medium text-gray-900">{u.usuario_nombre}</td>
              <td className="py-2 px-2 text-center text-gray-600">{u.num_ventas}</td>
              <td className="py-2 px-2 text-right">{formatCurrency(u.facturado)}</td>
              <td className="py-2 px-2 text-right text-green-700">{formatCurrency(u.cobrado)}</td>
              <td className="py-2 pl-2 text-right text-amber-700">{formatCurrency(u.cxc_generada)}</td>
            </tr>
          ))}
          {(usuarios || []).length === 0 && (
            <tr><td colSpan={5} className="py-6 text-center text-gray-400">Sin ventas registradas</td></tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);

const VentasTable = ({ ventas, testId }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm" data-testid={testId}>
    <h3 className="text-sm font-bold text-gray-900 mb-3">Ventas del día ({(ventas || []).length})</h3>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
            <th className="py-2 pr-2">Documento</th>
            <th className="py-2 px-2">Usuario</th>
            <th className="py-2 px-2">Cliente</th>
            <th className="py-2 px-2">Concepto</th>
            <th className="py-2 px-2 text-right">Total</th>
            <th className="py-2 px-2 text-right">Cobrado</th>
            <th className="py-2 pl-2 text-right">Pendiente</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {(ventas || []).map((v, i) => (
            <tr key={i} data-testid={`${testId}-row-${i}`}>
              <td className="py-2 pr-2 text-gray-600 whitespace-nowrap">{v.numero || '—'}</td>
              <td className="py-2 px-2 text-gray-700 whitespace-nowrap">{v.usuario}</td>
              <td className="py-2 px-2 text-gray-700">{v.cliente}</td>
              <td className="py-2 px-2 text-gray-500 max-w-[260px] truncate" title={v.concepto}>{v.concepto || '—'}</td>
              <td className="py-2 px-2 text-right font-medium whitespace-nowrap">{formatCurrency(v.total)}</td>
              <td className="py-2 px-2 text-right text-green-700 whitespace-nowrap">{formatCurrency(v.cobrado)}</td>
              <td className="py-2 pl-2 text-right text-amber-700 whitespace-nowrap">{formatCurrency(v.pendiente)}</td>
            </tr>
          ))}
          {(ventas || []).length === 0 && (
            <tr><td colSpan={7} className="py-6 text-center text-gray-400">Sin ventas este día</td></tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);

const ModuleSection = ({ title, icon: Icon, accent, mod, prefix, showEgresos }) => {
  const r = mod?.resumen || {};
  return (
    <div className="mb-8" data-testid={`seccion-${prefix}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accent}1a` }}>
          <Icon className="w-5 h-5" style={{ color: accent }} />
        </span>
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      </div>
      <div className={`grid grid-cols-2 sm:grid-cols-3 ${showEgresos ? 'lg:grid-cols-5' : 'lg:grid-cols-4'} gap-3 mb-4`}>
        <Card title="Ingreso facturado" value={formatCurrency(r.ingreso_facturado || 0)} sub="Incluye CxC de hoy" color="#1e3a8a" icon={TrendingUp} testId={`${prefix}-card-facturado`} />
        <Card title="Cobrado" value={formatCurrency(r.total_cobrado || 0)} sub="Dinero recibido" color="#047857" icon={Banknote} testId={`${prefix}-card-cobrado`} />
        <Card title="Cuentas por cobrar" value={formatCurrency(r.cxc_generada_hoy || 0)} sub="Pendiente de hoy" color="#b45309" icon={CreditCard} testId={`${prefix}-card-cxc`} />
        <Card title="Abonos previos" value={formatCurrency(r.abonos_cuentas_previas || 0)} sub="Cuentas anteriores" color="#6d28d9" icon={Clock} testId={`${prefix}-card-abonos`} />
        {showEgresos && (
          <Card title="Egresos" value={formatCurrency(r.egresos || 0)} sub="Salidas de caja" color="#b91c1c" icon={ArrowDownCircle} testId={`${prefix}-card-egresos`} />
        )}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <MetodosTable metodos={mod?.cobrado_por_metodo} total={r.total_cobrado} testId={`${prefix}-metodos`} />
        <UsuariosTable usuarios={mod?.por_usuario} testId={`${prefix}-usuarios`} />
      </div>
      <VentasTable ventas={mod?.ventas} testId={`${prefix}-ventas`} />
    </div>
  );
};

export default function CierreDiario() {
  const { user } = useAuth();
  const isAdminOrSuperAdmin = user?.role === 'superadmin' || user?.role === 'admin';

  const [fecha, setFecha] = useState(getGuatemalaDate());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const fetchCierre = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/caja/cierre-diario?fecha=${fecha}`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cargar el cierre del día');
    } finally {
      setLoading(false);
    }
  }, [fecha]);

  useEffect(() => { fetchCierre(); }, [fetchCierre]);

  const enviarCorreo = async () => {
    setEnviando(true);
    try {
      const res = await axios.post(`${API_URL}/caja/cierre-diario/enviar?fecha=${fecha}`);
      toast.success(res.data.message || 'Cierre enviado');
      (res.data.errores || []).forEach((e) => toast.warning(`${e.to}: ${e.error}`));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo enviar el cierre por correo');
    } finally {
      setEnviando(false);
    }
  };

  const g = data?.general || {};

  if (!isAdminOrSuperAdmin) {
    return (
      <Layout>
        <div data-testid="cierre-no-acceso" className="p-8 text-center text-gray-500">
          No tienes permiso para ver el cierre del día.
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="p-4 sm:p-6 max-w-7xl mx-auto" data-testid="cierre-diario-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Calculator className="w-6 h-6 text-blue-700" /> Cierre del Día
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Diagnóstico y conciliación — Clínica y Óptica por separado
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-40" data-testid="cierre-fecha-input" />
            <Button variant="outline" onClick={fetchCierre} disabled={loading} data-testid="cierre-refresh-btn">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={enviarCorreo} disabled={enviando || loading} className="bg-blue-700 hover:bg-blue-800 text-white" data-testid="cierre-enviar-correo-btn">
              <Mail className="w-4 h-4 mr-2" />
              {enviando ? 'Enviando...' : 'Enviar por correo'}
            </Button>
          </div>
        </div>

        {/* Resumen general */}
        <div className="mb-8" data-testid="cierre-general">
          <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Resumen general (Clínica + Óptica)</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <Card title="Ingreso facturado" value={formatCurrency(g.ingreso_facturado || 0)} sub="Incluye cuentas por cobrar" color="#1e3a8a" icon={TrendingUp} testId="general-card-facturado" />
            <Card title="Cobrado del día" value={formatCurrency(g.total_cobrado || 0)} sub="Dinero recibido" color="#047857" icon={Banknote} testId="general-card-cobrado" />
            <Card title="Cuentas por cobrar" value={formatCurrency(g.cxc_generada_hoy || 0)} sub="Pendiente de hoy" color="#b45309" icon={CreditCard} testId="general-card-cxc" />
            <Card title="Abonos previos" value={formatCurrency(g.abonos_cuentas_previas || 0)} sub="Cuentas anteriores" color="#6d28d9" icon={Clock} testId="general-card-abonos" />
            <Card title="Egresos" value={formatCurrency(g.egresos || 0)} sub="Salidas de caja clínica" color="#b91c1c" icon={ArrowDownCircle} testId="general-card-egresos" />
          </div>
        </div>

        {/* Clínica */}
        <ModuleSection title="Clínica" icon={Stethoscope} accent="#2563eb" mod={data?.clinica} prefix="clinica" showEgresos />

        {/* Óptica */}
        <ModuleSection title="Óptica" icon={Glasses} accent="#4f46e5" mod={data?.optica} prefix="optica" showEgresos={false} />

        {/* Conciliación de cajas (clínica) */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm" data-testid="cierre-conciliacion">
          <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-gray-500" /> Conciliación de cajas (Clínica)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-2">Cajero</th>
                  <th className="py-2 px-2 text-center">Estado</th>
                  <th className="py-2 px-2 text-right">Apertura</th>
                  <th className="py-2 px-2 text-right">Efectivo esperado</th>
                  <th className="py-2 px-2 text-right">Contado</th>
                  <th className="py-2 pl-2 text-right">Diferencia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(data?.conciliacion_cajas || []).map((c, i) => {
                  const dif = c.diferencia;
                  const ok = dif !== null && Math.abs(dif) < 0.01;
                  return (
                    <tr key={i} data-testid={`conciliacion-row-${i}`}>
                      <td className="py-2 pr-2 font-medium text-gray-900">{c.cajero}</td>
                      <td className="py-2 px-2 text-center">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${c.estado === 'Cerrado' ? 'bg-gray-100 text-gray-700' : 'bg-green-100 text-green-700'}`}>
                          {c.estado}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-gray-600">{formatCurrency(c.monto_apertura)}</td>
                      <td className="py-2 px-2 text-right">{formatCurrency(c.efectivo_esperado)}</td>
                      <td className="py-2 px-2 text-right">{c.efectivo_contado === null ? <span className="text-gray-400">Sin cerrar</span> : formatCurrency(c.efectivo_contado)}</td>
                      <td className="py-2 pl-2 text-right font-semibold">
                        {dif === null ? <span className="text-gray-400">—</span> : (
                          <span className={`inline-flex items-center gap-1 ${ok ? 'text-green-700' : 'text-red-600'}`}>
                            {ok ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                            {formatCurrency(dif)}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {(data?.conciliacion_cajas || []).length === 0 && (
                  <tr><td colSpan={6} className="py-6 text-center text-gray-400">Sin cajas abiertas este día</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
