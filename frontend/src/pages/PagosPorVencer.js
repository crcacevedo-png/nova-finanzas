import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { dashboardApi, formatCurrency, formatDate, typeLabels } from '../services/api';
import { 
  AlertTriangle, 
  AlertCircle,
  Clock,
  Calendar,
  DollarSign,
  ArrowRight,
  XCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const PagosPorVencer = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [overdue, setOverdue] = useState([]);
  const [due30, setDue30] = useState([]);
  const [due60, setDue60] = useState([]);
  const [activeTab, setActiveTab] = useState('vencidos');

  useEffect(() => {
    fetchUpcomingPayments();
  }, []);

  const fetchUpcomingPayments = async () => {
    try {
      const [overdueRes, alerts30Res, alerts60Res] = await Promise.all([
        dashboardApi.getUpcoming(),
        dashboardApi.getAlerts30(),
        dashboardApi.getAlerts60()
      ]);
      
      // Handle both possible response structures
      if (overdueRes.data.overdue) {
        setOverdue(overdueRes.data.overdue);
        setDue30(overdueRes.data.due_30 || []);
        setDue60(overdueRes.data.due_60 || []);
      } else {
        setOverdue(overdueRes.data.filter(e => e.days_remaining < 0) || []);
        setDue30(alerts30Res.data || []);
        setDue60(alerts60Res.data || []);
      }
    } catch (error) {
      console.error('Error fetching upcoming payments:', error);
      // Try legacy endpoints
      try {
        const [alerts30Res, alerts60Res] = await Promise.all([
          dashboardApi.getAlerts30(),
          dashboardApi.getAlerts60()
        ]);
        setDue30(alerts30Res.data || []);
        setDue60(alerts60Res.data || []);
        setOverdue([]);
      } catch (e) {
        console.error('Error with legacy endpoints:', e);
      }
    } finally {
      setLoading(false);
    }
  };

  const getTypeBadge = (type) => {
    const colors = {
      fijo: 'badge-fixed border-0',
      proveedor: 'badge-provider border-0',
      variable: 'badge-variable border-0'
    };
    return <Badge className={colors[type]}>{typeLabels[type]}</Badge>;
  };

  const getUrgencyBadge = (daysRemaining) => {
    if (daysRemaining < 0) {
      return (
        <Badge className="badge-overdue border-0">
          <XCircle className="w-3 h-3 mr-1" />
          Vencido hace {Math.abs(daysRemaining)} días
        </Badge>
      );
    } else if (daysRemaining <= 7) {
      return (
        <Badge className="badge-overdue border-0">
          <AlertCircle className="w-3 h-3 mr-1" />
          {daysRemaining} días
        </Badge>
      );
    } else if (daysRemaining <= 30) {
      return (
        <Badge className="badge-pending border-0">
          <AlertTriangle className="w-3 h-3 mr-1" />
          {daysRemaining} días
        </Badge>
      );
    } else {
      return (
        <Badge className="badge-admin border-0">
          <Clock className="w-3 h-3 mr-1" />
          {daysRemaining} días
        </Badge>
      );
    }
  };

  const goToExpenses = () => {
    navigate('/gastos');
  };

  const ExpenseTable = ({ expenses, emptyMessage }) => {
    if (expenses.length === 0) {
      return (
        <div className="p-12 text-center">
          <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">{emptyMessage}</p>
        </div>
      );
    }

    return (
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50">
              <TableHead className="font-semibold text-slate-600">Gasto</TableHead>
              <TableHead className="font-semibold text-slate-600">Tipo</TableHead>
              <TableHead className="font-semibold text-slate-600">Monto Total</TableHead>
              <TableHead className="font-semibold text-slate-600">Pendiente</TableHead>
              <TableHead className="font-semibold text-slate-600">Vencimiento</TableHead>
              <TableHead className="font-semibold text-slate-600">Urgencia</TableHead>
              <TableHead className="font-semibold text-slate-600 text-right">Acción</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {expenses.map((expense) => (
              <TableRow 
                key={expense.id} 
                className="table-row-hover"
                data-testid={`upcoming-expense-${expense.id}`}
              >
                <TableCell>
                  <div>
                    <p className="font-medium text-slate-900">{expense.name}</p>
                    {expense.invoice_number && (
                      <p className="text-xs text-slate-500">Factura: {expense.invoice_number}</p>
                    )}
                  </div>
                </TableCell>
                <TableCell>{getTypeBadge(expense.type)}</TableCell>
                <TableCell className="font-medium">
                  {formatCurrency(expense.amount)}
                </TableCell>
                <TableCell>
                  <p className="font-semibold text-[#8B6914]">
                    {formatCurrency(expense.remaining_amount)}
                  </p>
                </TableCell>
                <TableCell className="text-slate-600">
                  {formatDate(expense.due_date)}
                </TableCell>
                <TableCell>
                  {getUrgencyBadge(expense.days_remaining)}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    onClick={goToExpenses}
                    className="btn-primary"
                    data-testid={`pay-upcoming-${expense.id}`}
                  >
                    <DollarSign className="w-4 h-4 mr-1" />
                    Pagar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  };

  return (
    <Layout>
      <div className="space-y-6 animate-fade-in" data-testid="pagos-por-vencer-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 font-['Outfit']">Pagos por Vencer</h1>
            <p className="text-slate-500 text-sm">Gastos con fechas de vencimiento próximas</p>
          </div>
          <Button 
            onClick={goToExpenses}
            variant="outline"
            className="btn-outline"
          >
            Ver todos los gastos
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className={`border-2 ${overdue.length > 0 ? 'border-[#C53030] bg-[#FDE8E8]/50' : 'border-[#DCE8E3]'}`}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-3 rounded-xl ${overdue.length > 0 ? 'bg-[#FDE8E8]' : 'bg-[#EDF5F2]'}`}>
                <XCircle className={`w-5 h-5 ${overdue.length > 0 ? 'text-[#C53030]' : 'text-[#5A7A72]'}`} />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Vencidos</p>
                <p className={`text-2xl font-bold ${overdue.length > 0 ? 'text-[#C53030]' : ''}`} style={{ color: overdue.length === 0 ? 'var(--text-primary)' : undefined }}>
                  {overdue.length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className={`border-2 ${due30.length > 0 ? 'border-[#8B6914] bg-[#FEF4E0]/50' : 'border-[#DCE8E3]'}`}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-3 rounded-xl ${due30.length > 0 ? 'bg-[#FEF4E0]' : 'bg-[#EDF5F2]'}`}>
                <AlertTriangle className={`w-5 h-5 ${due30.length > 0 ? 'text-[#8B6914]' : 'text-[#5A7A72]'}`} />
              </div>
              <div>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Próximos 30 días</p>
                <p className={`text-2xl font-bold ${due30.length > 0 ? 'text-[#8B6914]' : ''}`} style={{ color: due30.length === 0 ? 'var(--text-primary)' : undefined }}>
                  {due30.length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className={`border-2 ${due60.length > 0 ? 'border-blue-300 bg-blue-50/50' : 'border-slate-200'}`}>
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-3 rounded-xl ${due60.length > 0 ? 'bg-blue-100' : 'bg-slate-100'}`}>
                <Clock className={`w-5 h-5 ${due60.length > 0 ? 'text-blue-700' : 'text-slate-500'}`} />
              </div>
              <div>
                <p className="text-sm text-slate-500">30 - 60 días</p>
                <p className={`text-2xl font-bold ${due60.length > 0 ? 'text-blue-700' : 'text-slate-900'}`}>
                  {due60.length}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs with Tables */}
        <Card className="border border-slate-200">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : (
              <Tabs defaultValue="vencidos" className="w-full">
                <div className="border-b border-slate-200 px-4 pt-4">
                  <TabsList className="bg-slate-100">
                    <TabsTrigger 
                      value="vencidos" 
                      className="data-[state=active]:bg-rose-100 data-[state=active]:text-rose-700"
                      data-testid="tab-vencidos"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Vencidos ({overdue.length})
                    </TabsTrigger>
                    <TabsTrigger 
                      value="30dias"
                      className="data-[state=active]:bg-amber-100 data-[state=active]:text-amber-700"
                      data-testid="tab-30dias"
                    >
                      <AlertTriangle className="w-4 h-4 mr-2" />
                      Próximos 30 días ({due30.length})
                    </TabsTrigger>
                    <TabsTrigger 
                      value="60dias"
                      className="data-[state=active]:bg-blue-100 data-[state=active]:text-blue-700"
                      data-testid="tab-60dias"
                    >
                      <Clock className="w-4 h-4 mr-2" />
                      30-60 días ({due60.length})
                    </TabsTrigger>
                  </TabsList>
                </div>
                
                <TabsContent value="vencidos" className="m-0">
                  <ExpenseTable 
                    expenses={overdue} 
                    emptyMessage="No hay gastos vencidos" 
                  />
                </TabsContent>
                
                <TabsContent value="30dias" className="m-0">
                  <ExpenseTable 
                    expenses={due30} 
                    emptyMessage="No hay gastos por vencer en los próximos 30 días" 
                  />
                </TabsContent>
                
                <TabsContent value="60dias" className="m-0">
                  <ExpenseTable 
                    expenses={due60} 
                    emptyMessage="No hay gastos por vencer entre 30 y 60 días" 
                  />
                </TabsContent>
              </Tabs>
            )}
          </CardContent>
        </Card>

        {/* Total Amounts Card */}
        <Card className="border border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold font-['Outfit']">Resumen de Montos Pendientes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-4 rounded-xl bg-[#FDE8E8] border border-[#C53030]/20">
                <p className="text-sm text-[#C53030] mb-1">Total Vencido</p>
                <p className="text-2xl font-bold text-[#C53030]">
                  {formatCurrency(overdue.reduce((sum, e) => sum + e.remaining_amount, 0))}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-[#FEF4E0] border border-[#8B6914]/20">
                <p className="text-sm text-[#8B6914] mb-1">Por vencer (30 días)</p>
                <p className="text-2xl font-bold text-[#8B6914]">
                  {formatCurrency(due30.reduce((sum, e) => sum + e.remaining_amount, 0))}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                <p className="text-sm text-blue-600 mb-1">Por vencer (30-60 días)</p>
                <p className="text-2xl font-bold text-blue-700">
                  {formatCurrency(due60.reduce((sum, e) => sum + e.remaining_amount, 0))}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default PagosPorVencer;
