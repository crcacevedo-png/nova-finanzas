import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { formatCurrency, getGuatemalaDate } from '../services/api';
import { toast, Toaster } from 'sonner';
import {
  RefreshCw, Mail, TrendingUp, Banknote, CreditCard, Clock, ArrowDownCircle,
  Users, Calculator, CheckCircle, AlertTriangle, Store
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const METODO_LABEL = {
  efectivo: 'Efectivo', tarjeta: 'Tarjeta', transferencia: 'Transferencia',
  cheque: 'Cheque', otro: 'Otro'
};

const Card = ({ title, value, sub, color, icon: Icon, testId }) => (
  <div
    data-testid={testId}
    className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-1 shadow-sm"
  >
    <div className="flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-wide text-gray-500">{title}</span>
      {Icon && <Icon className="w-4 h-4" style={{ color }} />}
    </div>
    <span className="text-2xl font-bold" style={{ color }}>{value}</span>
    {sub && <span className="text-[11px] text-gray-400">{sub}</span>}
  </div>
);

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
      const dests = res.data.destinatarios || [];
      toast.success(res.data.message || 'Cierre enviado');
      if ((res.data.errores || []).length > 0) {
        res.data.errores.forEach((e) => toast.warning(`${e.to}: ${e.error}`));
      }
      if (dests.length === 0 && (res.data.errores || []).length === 0) {
        toast.warning('No hay destinatarios enviados');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo enviar el cierre por correo');
    } finally {
      setEnviando(false);
    }
  };

  const r = data?.resumen || {};
  const metodos = data?.cobrado_por_metodo || {};

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
              Diagnóstico y conciliación de todos los usuarios (Clínica + Óptica)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="w-40"
              data-testid="cierre-fecha-input"
            />
            <Button
              variant="outline"
              onClick={fetchCierre}
              disabled={loading}
              data-testid="cierre-refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              onClick={enviarCorreo}
              disabled={enviando || loading}
              className="bg-blue-700 hover:bg-blue-800 text-white"
              data-testid="cierre-enviar-correo-btn"
            >
              <Mail className="w-4 h-4 mr-2" />
              {enviando ? 'Enviando...' : 'Enviar por correo'}
            </Button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-6" data-testid="cierre-resumen">
          <Card title="Ingreso facturado" value={formatCurrency(r.ingreso_facturado || 0)}
            sub="Incluye cuentas por cobrar de hoy" color="#1e3a8a" icon={TrendingUp}
            testId="card-ingreso-facturado" />
          <Card title="Cobrado del día" value={formatCurrency(r.total_cobrado || 0)}
            sub="Dinero realmente recibido" color="#047857" icon={Banknote}
            testId="card-cobrado" />
          <Card title="Cuentas por cobrar (hoy)" value={formatCurrency(r.cxc_generada_hoy || 0)}
            sub="Pendiente de ventas de hoy" color="#b45309" icon={CreditCard}
            testId="card-cxc-generada" />
          <Card title="Abonos de días previos" value={formatCurrency(r.abonos_cuentas_previas || 0)}
            sub="Cobros de cuentas anteriores" color="#6d28d9" icon={Clock}
            testId="card-abonos-previos" />
          <Card title="Egresos del día" value={formatCurrency(r.egresos || 0)}
            sub="Salidas de caja clínica" color="#b91c1c" icon={ArrowDownCircle}
            testId="card-egresos" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
          {/* Cobrado por método */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm" data-testid="cierre-metodos">
            <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-gray-500" /> Cobrado por método de pago
            </h2>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-100">
                {['efectivo', 'tarjeta', 'transferencia', 'cheque', 'otro'].map((k) => {
                  const val = metodos[k] || 0;
                  if (val === 0 && k === 'otro') return null;
                  return (
                    <tr key={k} data-testid={`metodo-row-${k}`}>
                      <td className="py-2 text-gray-600">{METODO_LABEL[k]}</td>
                      <td className="py-2 text-right font-semibold text-gray-900">{formatCurrency(val)}</td>
                    </tr>
                  );
                })}
                <tr className="border-t-2 border-gray-200">
                  <td className="py-2 font-bold text-gray-900">Total cobrado</td>
                  <td className="py-2 text-right font-bold text-green-700" data-testid="metodo-total">
                    {formatCurrency(r.total_cobrado || 0)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Por usuario */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm lg:col-span-2" data-testid="cierre-usuarios">
            <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-500" /> Ventas por usuario
            </h2>
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
                  {(data?.por_usuario || []).map((u) => (
                    <tr key={u.usuario_id} data-testid={`usuario-row-${u.usuario_id}`}>
                      <td className="py-2 pr-2 font-medium text-gray-900">{u.usuario_nombre}</td>
                      <td className="py-2 px-2 text-center text-gray-600">{u.num_ventas}</td>
                      <td className="py-2 px-2 text-right">{formatCurrency(u.facturado)}</td>
                      <td className="py-2 px-2 text-right text-green-700">{formatCurrency(u.cobrado)}</td>
                      <td className="py-2 pl-2 text-right text-amber-700">{formatCurrency(u.cxc_generada)}</td>
                    </tr>
                  ))}
                  {(data?.por_usuario || []).length === 0 && (
                    <tr><td colSpan={5} className="py-6 text-center text-gray-400">Sin ventas registradas</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Conciliación de cajas */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm mb-6" data-testid="cierre-conciliacion">
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

        {/* Ventas del día */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm" data-testid="cierre-ventas">
          <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Store className="w-4 h-4 text-gray-500" /> Ventas del día ({data?.resumen?.num_ventas || 0})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="py-2 pr-2">Módulo</th>
                  <th className="py-2 px-2">Documento</th>
                  <th className="py-2 px-2">Usuario</th>
                  <th className="py-2 px-2">Cliente</th>
                  <th className="py-2 px-2 text-right">Total</th>
                  <th className="py-2 px-2 text-right">Cobrado</th>
                  <th className="py-2 pl-2 text-right">Pendiente</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(data?.ventas || []).map((v, i) => (
                  <tr key={i} data-testid={`venta-row-${i}`}>
                    <td className="py-2 pr-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${v.modulo === 'Óptica' ? 'bg-indigo-100 text-indigo-700' : 'bg-blue-100 text-blue-700'}`}>
                        {v.modulo}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-gray-600">{v.numero || '—'}</td>
                    <td className="py-2 px-2 text-gray-700">{v.usuario}</td>
                    <td className="py-2 px-2 text-gray-700">{v.cliente}</td>
                    <td className="py-2 px-2 text-right font-medium">{formatCurrency(v.total)}</td>
                    <td className="py-2 px-2 text-right text-green-700">{formatCurrency(v.cobrado)}</td>
                    <td className="py-2 pl-2 text-right text-amber-700">{formatCurrency(v.pendiente)}</td>
                  </tr>
                ))}
                {(data?.ventas || []).length === 0 && (
                  <tr><td colSpan={7} className="py-6 text-center text-gray-400">Sin ventas este día</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
