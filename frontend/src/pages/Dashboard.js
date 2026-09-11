import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { NogAlertasBanner } from '../components/NogAlertasBanner';
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
  ResponsiveContainer
} from 'recharts';

const CHART_COLORS = ['#7DD8C0', '#0F6E56', '#2B5EA7', '#8B6914', '#C53030'];

const StatCard = ({ title, value, icon: Icon, colorClass, subtitle }) => (
  <Card className="card-teal card-hover">
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>{title}</p>
          <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
          {subtitle && <p className="text-xs mt-1" style={{ color: 'var(--text-hint)' }}>{subtitle}</p>}
        </div>
        <div className="p-3 rounded-xl gradient-teal">
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const MetricCard = ({ title, value, icon: Icon, bgClass, iconColor }) => (
  <Card className="card-metrics border-0 shadow-none">
    <CardContent className="p-4 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${bgClass}`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
      <div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{title}</p>
        <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{value}</p>
      </div>
    </CardContent>
  </Card>
);

const AlertCard = ({ title, alerts, type, icon: Icon }) => {
  const styles = {
    overdue: {
      borderClass: 'alert-card-overdue',
      iconColor: 'text-[#C53030]',
      badgeBg: 'bg-[#FDE8E8]',
      badgeText: 'text-[#9B2C2C]'
    },
    '30days': {
      borderClass: 'alert-card-30days',
      iconColor: 'text-[#8B6914]',
      badgeBg: 'bg-[#FEF4E0]',
      badgeText: 'text-[#8B6914]'
    },
    '60days': {
      borderClass: 'alert-card-60days',
      iconColor: 'text-[#2B5EA7]',
      badgeBg: 'bg-[#E6F0FA]',
      badgeText: 'text-[#2B5EA7]'
    }
  };

  const style = styles[type] || styles['30days'];

  return (
    <Card className={`card-teal overflow-hidden`}>
      <div className={`${style.borderClass} h-full`}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Icon className={`w-5 h-5 ${style.iconColor}`} />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <p className="text-sm text-center py-4" style={{ color: 'var(--text-hint)' }}>
              No hay alertas pendientes
            </p>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div 
                  key={alert.id} 
                  className="p-3 rounded-lg bg-white/50"
                  data-testid={`alert-item-${alert.id}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{alert.name}</p>
                    <Badge className={`${style.badgeBg} ${style.badgeText} border-0 text-xs`}>
                      {alert.days_remaining} días
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Vence: {formatDate(alert.due_date)}
                    </span>
                    <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {formatCurrency(alert.remaining_amount)}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-1">
                    <Badge className={`badge-${alert.type} text-[10px] border-0`}>
                      {typeLabels[alert.type]}
                    </Badge>
                    <Badge className={`badge-${alert.status} text-[10px] border-0`}>
                      {statusLabels[alert.status]}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </div>
    </Card>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [alerts30, setAlerts30] = useState([]);
  const [alerts60, setAlerts60] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, chartRes, alerts30Res, alerts60Res] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getChartData(),
        dashboardApi.getAlerts30(),
        dashboardApi.getAlerts60()
      ]);

      setStats(statsRes.data);
      setChartData(chartRes.data || []);
      setAlerts30(alerts30Res.data || []);
      setAlerts60(alerts60Res.data || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
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
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Dashboard</h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Resumen financiero de la clínica</p>
        </div>

        {/* Alertas de contratos NOG (IGSS) */}
        <NogAlertasBanner
          onVer={(a) => navigate(`/configuracion/unidades-igss?nogUnidad=${a.unidad_id}&nog=${a.nog_id}&nombre=${encodeURIComponent(a.unidad_nombre || '')}`)}
        />

        {/* Main Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Gastos"
            value={formatCurrency(stats?.total_gastos || 0)}
            icon={Wallet}
            colorClass="metric-blue"
            subtitle="Mes actual"
          />
          <StatCard
            title="Pagos Pendientes"
            value={formatCurrency(stats?.gastos_pendientes || 0)}
            icon={Clock}
            colorClass="metric-amber"
            subtitle={`${stats?.alertas_30_dias || 0} por vencer (30d)`}
          />
          <StatCard
            title="Gastos Pagados"
            value={formatCurrency(stats?.gastos_pagados || 0)}
            icon={CheckCircle2}
            colorClass="metric-teal"
            subtitle="Mes actual"
          />
          <StatCard
            title="Alertas Activas"
            value={`${(stats?.alertas_30_dias || 0) + (stats?.alertas_60_dias || 0)}`}
            icon={AlertTriangle}
            colorClass="metric-red"
            subtitle={`${stats?.gastos_vencidos || 0} vencidos`}
          />
        </div>

        {/* Category Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Gastos Fijos"
            value={formatCurrency(stats?.total_fijos || 0)}
            icon={Repeat}
            bgClass="bg-[#E6F0FA]"
            iconColor="text-[#2B5EA7]"
          />
          <MetricCard
            title="Pagos Proveedores"
            value={formatCurrency(stats?.total_proveedores || 0)}
            icon={Building2}
            bgClass="bg-[#E1F5EE]"
            iconColor="text-[#0F6E56]"
          />
          <MetricCard
            title="Gastos Variables"
            value={formatCurrency(stats?.total_variables || 0)}
            icon={TrendingUp}
            bgClass="bg-[#FEF4E0]"
            iconColor="text-[#8B6914]"
          />
        </div>

        {/* Charts and Alerts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart */}
          <Card className="card-teal lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                Gastos Últimos 6 Meses
              </CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartData}>
                    <defs>
                      <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#7DD8C0" />
                        <stop offset="100%" stopColor="#0F6E56" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#D4E4DE" />
                    <XAxis 
                      dataKey="month" 
                      tick={{ fill: '#5A7A72', fontSize: 12 }}
                      axisLine={{ stroke: '#D4E4DE' }}
                    />
                    <YAxis 
                      tick={{ fill: '#5A7A72', fontSize: 12 }}
                      axisLine={{ stroke: '#D4E4DE' }}
                      tickFormatter={(value) => `Q${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip 
                      formatter={(value) => formatCurrency(value)}
                      contentStyle={{ 
                        background: 'white', 
                        border: '1px solid #D4E4DE',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(12, 46, 42, 0.08)'
                      }}
                    />
                    <Bar 
                      dataKey="total" 
                      fill="url(#barGradient)" 
                      radius={[4, 4, 0, 0]}
                      name="Total"
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[280px] flex items-center justify-center">
                  <p style={{ color: 'var(--text-hint)' }}>No hay datos disponibles</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Progress by Type */}
          <Card className="card-teal">
            <CardHeader>
              <CardTitle className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                Desglose por Tipo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Fixed */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>Gastos Fijos</span>
                  <span className="font-medium" style={{ color: 'var(--type-fixed-text)' }}>
                    {formatCurrency(stats?.total_fijos || 0)}
                  </span>
                </div>
                <div className="h-2 bg-[#EDF5F2] rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full animate-progress progress-bar-fixed"
                    style={{ 
                      width: `${stats?.total_gastos ? ((stats?.total_fijos || 0) / stats.total_gastos) * 100 : 0}%`
                    }}
                  />
                </div>
              </div>
              
              {/* Providers */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>Proveedores</span>
                  <span className="font-medium" style={{ color: 'var(--type-provider-text)' }}>
                    {formatCurrency(stats?.total_proveedores || 0)}
                  </span>
                </div>
                <div className="h-2 bg-[#EDF5F2] rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full animate-progress progress-bar-provider"
                    style={{ 
                      width: `${stats?.total_gastos ? ((stats?.total_proveedores || 0) / stats.total_gastos) * 100 : 0}%`
                    }}
                  />
                </div>
              </div>
              
              {/* Variable */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>Variables</span>
                  <span className="font-medium" style={{ color: 'var(--type-variable-text)' }}>
                    {formatCurrency(stats?.total_variables || 0)}
                  </span>
                </div>
                <div className="h-2 bg-[#EDF5F2] rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full animate-progress progress-bar-variable"
                    style={{ 
                      width: `${stats?.total_gastos ? ((stats?.total_variables || 0) / stats.total_gastos) * 100 : 0}%`
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Alerts Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AlertCard
            title="Vencimientos a 30 días"
            alerts={alerts30}
            type="30days"
            icon={AlertCircle}
          />
          <AlertCard
            title="Vencimientos a 60 días"
            alerts={alerts60}
            type="60days"
            icon={Clock}
          />
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
