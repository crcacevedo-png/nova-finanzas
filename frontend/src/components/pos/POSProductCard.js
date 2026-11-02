// Componente de tarjeta de producto para POS de Óptica
import React from 'react';
import { Glasses, Eye, CircleDot, Plus, Watch } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { formatCurrency } from '../../services/api';

const POSProductCard = ({ 
  producto, 
  categoriaActiva, 
  tipoProducto,
  onAgregar 
}) => {
  const esLenteContacto = tipoProducto === 'lentes_contacto';
  const esLenteOftalmico = tipoProducto === 'tipos_lente';
  const esAccesorio = categoriaActiva === 'accesorios';

  const getProductIcon = () => {
    if (categoriaActiva === 'armazones') {
      return <Glasses className="h-10 w-10 text-teal-500" />;
    }
    if (esAccesorio) {
      return <Watch className="h-10 w-10 text-amber-500" />;
    }
    if (esLenteContacto) {
      return <CircleDot className="h-10 w-10 text-green-500" />;
    }
    return <Eye className="h-10 w-10 text-purple-500" />;
  };

  const getProductName = () => {
    if (categoriaActiva === 'armazones') {
      return `${producto.brand} ${producto.model}`;
    }
    if (esAccesorio) {
      return `${producto.brand || ''} ${producto.name || ''}`.trim();
    }
    if (esLenteContacto) {
      return `${producto.brand || ''} ${producto.name || ''}`.trim();
    }
    return producto.name;
  };

  const showStock = categoriaActiva === 'armazones' || esLenteContacto || esAccesorio;

  return (
    <Card 
      className="cursor-pointer hover:border-teal-500 transition-all hover:shadow-lg group"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}
      onClick={() => onAgregar(producto, tipoProducto)}
    >
      <CardContent className="p-3">
        {/* Badge de tipo de lente */}
        {categoriaActiva === 'lentes' && (
          <Badge 
            className={`mb-2 text-xs ${esLenteContacto ? 'bg-green-500' : 'bg-purple-500'}`}
          >
            {esLenteContacto ? 'Contacto' : 'Oftálmico'}
          </Badge>
        )}
        
        {/* Imagen o ícono */}
        <div 
          className="h-20 rounded-md mb-2 flex items-center justify-center"
          style={{ background: 'var(--bg-hover)' }}
        >
          {getProductIcon()}
        </div>
        
        {/* Info del producto */}
        <div className="space-y-1">
          <p className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)' }}>
            {getProductName()}
          </p>
          
          {categoriaActiva === 'armazones' && producto.color && (
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Color: {producto.color}
            </p>
          )}
          
          <div className="flex items-center justify-between">
            <p className="font-bold text-teal-500">
              {formatCurrency(producto.sale_price || producto.price || 0)}
            </p>
            
            {showStock && (
              <Badge 
                variant={producto.stock > 5 ? 'default' : producto.stock > 0 ? 'warning' : 'destructive'}
                className="text-xs"
              >
                {producto.stock || 0}
              </Badge>
            )}
          </div>
        </div>
        
        {/* Botón agregar (visible en hover) */}
        <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            size="sm" 
            className="w-full bg-teal-600 hover:bg-teal-700"
          >
            <Plus className="h-4 w-4 mr-1" /> Agregar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default POSProductCard;
