// Componente del carrito para POS de Óptica
import React from 'react';
import { 
  ShoppingCart, 
  User, 
  X, 
  Trash2, 
  Plus, 
  Minus, 
  CreditCard,
  FileText 
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { formatCurrency } from '../../services/api';

const POSCart = ({
  carrito,
  paciente,
  receta,
  medico,
  medicoSearch,
  onMedicoSearchChange,
  medicosResults = [],
  onSeleccionarMedico,
  onRemoverMedico,
  calcularSubtotal,
  calcularTotal,
  calcularDescuento,
  descuentoPorcentaje,
  onDescuentoPorcentajeChange,
  descuentoAutoriza,
  onDescuentoAutorizaChange,
  onModificarCantidad,
  onEliminarItem,
  onLimpiarCarrito,
  onSeleccionarPaciente,
  onRemoverPaciente,
  onAbrirReceta,
  onAbrirPago
}) => {
  const tieneReceta = Object.values(receta || {}).some(v => v);
  const tieneLentesOftalmicos = carrito.some(item => item.tipo === 'tipos_lente');

  return (
    <div 
      className="w-96 flex flex-col border-l"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
    >
      {/* Header carrito */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border-color)' }}>
        <div className="flex items-center justify-between">
          <h2 className="font-bold" style={{ color: 'var(--text-primary)' }}>
            Carrito ({carrito.length})
          </h2>
          {carrito.length > 0 && (
            <Button variant="ghost" size="sm" onClick={onLimpiarCarrito}>
              <Trash2 className="h-4 w-4 mr-1" /> Limpiar
            </Button>
          )}
        </div>
        
        {/* Paciente */}
        <div className="mt-3">
          {paciente ? (
            <div 
              className="flex items-center justify-between p-2 rounded-lg"
              style={{ background: 'var(--bg-hover)' }}
            >
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-teal-500" />
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  {paciente.primer_nombre} {paciente.primer_apellido}
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={onRemoverPaciente}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              className="w-full"
              onClick={onSeleccionarPaciente}
            >
              <User className="h-4 w-4 mr-2" />
              Seleccionar Paciente
            </Button>
          )}
        </div>

        {/* Médico (obligatorio cuando hay paciente) - autollenable de la lista general */}
        {paciente && (
          <div className="mt-3" data-testid="pos-optica-medico-block">
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>
              Médico <span className="text-red-500">*</span>
            </label>
            {medico ? (
              <div className="flex items-center justify-between p-2 rounded-lg" style={{ background: 'var(--bg-hover)' }}>
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }} data-testid="pos-optica-medico-seleccionado">
                  {medico.name}
                </span>
                <Button variant="ghost" size="sm" onClick={onRemoverMedico} data-testid="pos-optica-medico-remover">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="relative">
                <Input
                  value={medicoSearch}
                  onChange={(e) => onMedicoSearchChange(e.target.value)}
                  placeholder="Buscar médico..."
                  className="h-9"
                  data-testid="pos-optica-medico-input"
                />
                {medicosResults.length > 0 && (
                  <div className="absolute z-20 mt-1 w-full bg-white border rounded-md shadow-lg max-h-48 overflow-y-auto" data-testid="pos-optica-medico-resultados">
                    {medicosResults.map((d) => (
                      <button
                        key={d.id}
                        type="button"
                        className="w-full text-left px-3 py-2 text-sm hover:bg-teal-50"
                        data-testid={`pos-optica-medico-opcion-${d.id}`}
                        onClick={() => onSeleccionarMedico({ id: d.id, name: d.name })}
                      >
                        {d.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Items del carrito */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {carrito.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <ShoppingCart className="h-12 w-12 mb-3 opacity-50" />
            <p>Carrito vacío</p>
            <p className="text-sm">Selecciona productos para agregar</p>
          </div>
        ) : (
          carrito.map((item) => (
            <div 
              key={item.key}
              className="p-3 rounded-lg"
              style={{ background: 'var(--bg-hover)' }}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                    {item.nombre}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {formatCurrency(item.precio)} c/u
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEliminarItem(item.key)}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onModificarCantidad(item.key, -1)}
                    disabled={item.cantidad <= 1}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <span className="w-8 text-center font-medium" style={{ color: 'var(--text-primary)' }}>
                    {item.cantidad}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onModificarCantidad(item.key, 1)}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                <p className="font-bold text-teal-500">
                  {formatCurrency(item.precio * item.cantidad)}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Totales y botón de pago */}
      <div className="p-4 border-t" style={{ borderColor: 'var(--border-color)' }}>
        {/* Botón de receta si hay lentes */}
        {tieneLentesOftalmicos && (
          <Button
            variant="outline"
            className="w-full mb-3"
            onClick={onAbrirReceta}
          >
            <FileText className="h-4 w-4 mr-2" />
            {tieneReceta ? 'Editar Receta' : 'Agregar Receta'}
          </Button>
        )}
        
        <div className="space-y-2 mb-4">
          <div className="flex justify-between">
            <span style={{ color: 'var(--text-secondary)' }}>Subtotal:</span>
            <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(calcularSubtotal())}</span>
          </div>

          {/* Descuento por porcentaje */}
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Descuento (%):</span>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={descuentoPorcentaje}
              onChange={(e) => onDescuentoPorcentajeChange(e.target.value)}
              placeholder="0"
              className="h-8 w-24 text-right"
              data-testid="pos-optica-descuento-pct"
            />
          </div>
          {(parseFloat(descuentoPorcentaje) || 0) > 0 && (
            <>
              <div className="flex justify-between text-sm text-red-500">
                <span>Descuento:</span>
                <span data-testid="pos-optica-descuento-monto">- {formatCurrency(calcularDescuento())}</span>
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>
                  Autoriza descuento <span className="text-red-500">*</span>
                </label>
                <Input
                  value={descuentoAutoriza}
                  onChange={(e) => onDescuentoAutorizaChange(e.target.value)}
                  placeholder="Nombre de quien autoriza"
                  className="h-8"
                  data-testid="pos-optica-descuento-autoriza"
                />
              </div>
            </>
          )}

          <div className="flex justify-between text-lg font-bold">
            <span style={{ color: 'var(--text-primary)' }}>Total:</span>
            <span className="text-teal-500">{formatCurrency(calcularTotal())}</span>
          </div>
        </div>
        
        <Button
          className="w-full h-14 text-lg bg-teal-600 hover:bg-teal-700"
          disabled={carrito.length === 0}
          onClick={onAbrirPago}
          data-testid="pos-pagar-btn"
        >
          <CreditCard className="h-5 w-5 mr-2" />
          Cobrar {formatCurrency(calcularTotal())}
        </Button>
      </div>
    </div>
  );
};

export default POSCart;
