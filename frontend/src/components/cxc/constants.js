// Constantes y utilidades para Cuentas por Cobrar
import { 
  Banknote, 
  CreditCard, 
  Building2, 
  FileText,
  Stethoscope,
  Building,
  Shield,
  Briefcase,
  Users,
  User,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ArrowDownCircle
} from 'lucide-react';

// Métodos de pago para abonos
export const METODOS_PAGO = [
  { value: 'Efectivo', label: 'Efectivo', icon: Banknote },
  { value: 'Tarjeta', label: 'Tarjeta', icon: CreditCard },
  { value: 'Transferencia', label: 'Transferencia', icon: Building2 },
  { value: 'Cheque', label: 'Cheque', icon: FileText },
];

// Estados de cuenta
export const ESTADOS_CXC = [
  { value: 'all', label: 'Todos' },
  { value: 'Pendiente', label: 'Pendiente', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'Parcial', label: 'Parcial', color: 'bg-blue-100 text-blue-700' },
  { value: 'Pagado', label: 'Pagado', color: 'bg-green-100 text-green-700' },
  { value: 'Vencido', label: 'Vencido', color: 'bg-red-100 text-red-700' },
  { value: 'Anulado', label: 'Anulado', color: 'bg-slate-100 text-slate-700' },
];

// Tipos de responsable
export const TIPOS_RESPONSABLE = [
  { value: 'medico', label: 'Médico', icon: Stethoscope, color: 'bg-blue-500' },
  { value: 'institucion', label: 'Institución', icon: Building, color: 'bg-purple-500' },
  { value: 'seguro', label: 'Seguro', icon: Shield, color: 'bg-green-500' },
  { value: 'convenio', label: 'Convenio', icon: Briefcase, color: 'bg-orange-500' },
  { value: 'igss', label: 'IGSS', icon: Users, color: 'bg-teal-500' },
  { value: 'otro', label: 'Otro', icon: User, color: 'bg-slate-500' },
];

// Obtener info de tipo de responsable
export const getTipoResponsableInfo = (tipo) => {
  return TIPOS_RESPONSABLE.find(t => t.value === tipo) || TIPOS_RESPONSABLE[5];
};

// Obtener ícono de estado
export const getEstadoIcon = (estado) => {
  switch (estado) {
    case 'Pendiente': return Clock;
    case 'Parcial': return ArrowDownCircle;
    case 'Pagado': return CheckCircle;
    case 'Vencido': return AlertTriangle;
    case 'Anulado': return XCircle;
    default: return null;
  }
};

// Obtener color de estado
export const getEstadoConfig = (estado) => {
  return ESTADOS_CXC.find(e => e.value === estado);
};
