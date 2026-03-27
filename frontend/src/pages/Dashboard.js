import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { dashboardApi, formatCurrency, formatDate, typeLabels, statusLabels } from '../services/api';
import { 
  Wallet, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  TrendingUp,
  Building2,
  Repeat,
  AlertCircle,
  XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const CHART_COLORS = ['#115e59', '#14b8a6', '#99f6e4', '#f59e0b', '#10b981'];

const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
  <Card className="border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
          <p className="text-2xl font-bold text-slate-900 font-['Outfit']">{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const AlertCard = ({ title, alerts, color, icon: Icon }) => (
  <Card className={`border ${color === 'amber' ? 'border-amber-200' : 'border-rose-200'}`}>
    <CardHeader className="pb-3">
      <CardTitle className="text-lg font-semibold flex items-center gap-2 font-['Outfit']">
        <Icon className={`w-5 h-5 ${color === 'amber' ? 'text-amber-600' : 'text-rose-600'}`} />
        {title}
      </CardTitle>
    </CardHeader>
    <CardContent>
      {alerts.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-4">No hay alertas pendientes</p>
      ) : (
        <div className="space-y-3">
          {alerts.slice(0, 5).map((alert) => (
            <div 
              key={alert.id} 
              className={`p-3 rounded-lg ${color === 'amber' ? 'bg-amber-50' : 'bg-rose-50'}`}
              data-testid={`alert-item-${alert.id}`}
            >
              <div className="flex items-center justify-between mb-1">
                <p className="font-medium text-slate-900 text-sm">{alert.name}</p>
                <Badge 
                  variant="outline" 
                  className={color === 'amber' ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-rose-100 text-rose-700 border-rose-200'}
                >
                  {alert.days_remaining} días
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">
                  Vence: {formatDate(alert.due_date)}
                </span>
                <span className={`font-semibold ${color === 'amber' ? 'text-amber-700' : 'text-rose-700'}`}>
                  {formatCurrency(alert.remaining_amount)}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Badge className="text-xs bg-slate-100 text-slate-600 border-slate-200">
                  {typeLabels[alert.type]}
                </Badge>
                {alert.status === 'parcial' && (
                  <Badge className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                    Pago parcial
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </CardContent>
  </Card>
);

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [alerts30, setAlerts30] = useState([]);
  const [alerts60, setAlerts60] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, alerts30Res, alerts60Res, chartRes] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getAlerts30(),
        dashboardApi.getAlerts60(),
        dashboardApi.getChartData()
      ]);
      
      setStats(statsRes.data);
      setAlerts30(alerts30Res.data);
      setAlerts60(alerts60Res.data);
      setChartData(chartRes.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const pieData = stats ? [
    { name: 'Gastos Fijos', value: stats.total_fijos },
    { name: 'Pagos Proveedores', value: stats.total_proveedores },
    { name: 'Gastos Variables', value: stats.total_variables }
  ].filter(d => d.value > 0) : [];

  if (loading) {
    return (
      <Layout>
        <div className="space-y-6" data-testid="dashboard-loading">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6 animate-fade-in" data-testid="dashboard-page">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Dashboard</h1>
          <p className="text-slate-500 text-sm">Resumen financiero de la clínica</p>
        </div>

        {/* Main Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Gastos"
            value={formatCurrency(stats?.total_gastos || 0)}
            icon={Wallet}
            color="bg-teal-800"
            subtitle="Histórico total"
          />
          <StatCard
            title="Pagos Pendientes"
            value={formatCurrency(stats?.gastos_pendientes || 0)}
            icon={Clock}
            color="bg-amber-500"
            subtitle={`${stats?.alertas_30_dias || 0} por vencer (30d)`}
          />
          <StatCard
            title="Gastos Pagados"
            value={formatCurrency(stats?.gastos_pagados || 0)}
            icon={CheckCircle2}
            color="bg-emerald-600"
            subtitle="Completados"
          />
          <StatCard
            title="Alertas Activas"
            value={`${(stats?.alertas_30_dias || 0) + (stats?.alertas_60_dias || 0)}`}
            icon={AlertTriangle}
            color="bg-rose-500"
            subtitle={`${stats?.gastos_vencidos || 0} vencidos`}
          />
        </div>

        {/* Status Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-100">
                <Clock className="w-4 h-4 text-amber-700" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Pendientes</p>
                <p className="font-semibold text-slate-900">{formatCurrency(stats?.gastos_pendientes || 0)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <TrendingUp className="w-4 h-4 text-blue-700" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Parciales</p>
                <p className="font-semibold text-slate-900">{formatCurrency(stats?.gastos_parciales || 0)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-100">
                <CheckCircle2 className="w-4 h-4 text-emerald-700" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Pagados</p>
                <p className="font-semibold text-slate-900">{formatCurrency(stats?.gastos_pagados || 0)}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-rose-100">
                <XCircle className="w-4 h-4 text-rose-700" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Vencidos</p>
                <p className="font-semibold text-slate-900">{formatCurrency(stats?.gastos_vencidos || 0)}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Category Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-teal-100">
                <Repeat className="w-5 h-5 text-teal-800" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Gastos Fijos</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(stats?.total_fijos || 0)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-cyan-100">
                <Building2 className="w-5 h-5 text-cyan-800" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Pagos Proveedores</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(stats?.total_proveedores || 0)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-amber-100">
                <TrendingUp className="w-5 h-5 text-amber-700" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Gastos Variables</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(stats?.total_variables || 0)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Alerts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AlertCard
            title="Vencimientos a 30 días"
            alerts={alerts30}
            color="rose"
            icon={AlertCircle}
          />
          <AlertCard
            title="Vencimientos a 60 días"
            alerts={alerts60}
            color="amber"
            icon={AlertTriangle}
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Bar Chart */}
          <Card className="lg:col-span-2 border border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-semibold font-['Outfit']">
                Gastos por Mes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="mes" tick={{ fontSize: 12 }} stroke="#64748b" />
                    <YAxis tick={{ fontSize: 12 }} stroke="#64748b" />
                    <Tooltip 
                      formatter={(value) => formatCurrency(value)}
                      contentStyle={{ 
                        borderRadius: '8px', 
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="fijo" name="Gastos Fijos" fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="proveedor" name="Proveedores" fill={CHART_COLORS[1]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="variable" name="Variables" fill={CHART_COLORS[3]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-500">
                  No hay datos disponibles
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pie Chart */}
          <Card className="border border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-semibold font-['Outfit']">
                Distribución por Tipo
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatCurrency(value)} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-500">
                  No hay datos disponibles
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
