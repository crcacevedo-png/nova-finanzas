// Grid de tarjetas de responsables
import React from 'react';
import { Plus, Edit, Trash2, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { getTipoResponsableInfo } from './constants';

const CXCResponsablesGrid = ({
  responsables,
  loading,
  onNuevo,
  onEditar,
  onEliminar
}) => {
  if (loading) {
    return (
      <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Catálogo de Responsables</CardTitle>
          <Skeleton className="h-10 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Catálogo de Responsables</CardTitle>
        <Button 
          className="bg-blue-600 hover:bg-blue-700"
          onClick={onNuevo}
        >
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Responsable
        </Button>
      </CardHeader>
      <CardContent>
        {responsables.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No hay responsables registrados</p>
            <p className="text-sm">Cree responsables para asignar a las cuentas por cobrar</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {responsables.map((resp) => {
              const tipoInfo = getTipoResponsableInfo(resp.tipo);
              const Icon = tipoInfo.icon;
              return (
                <div 
                  key={resp.id}
                  className="p-4 rounded-lg border hover:shadow-md transition-shadow"
                  style={{ borderColor: 'var(--border-color)' }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full ${tipoInfo.color} flex items-center justify-center`}>
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <p className="font-medium">{resp.nombre}</p>
                        <Badge variant="outline" className="text-xs">
                          {tipoInfo.label}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => onEditar(resp)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        className="text-red-500 hover:text-red-700"
                        onClick={() => onEliminar(resp.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  <div className="space-y-1 text-sm text-slate-500">
                    {resp.nit && <p>NIT: {resp.nit}</p>}
                    {resp.telefono && <p>Tel: {resp.telefono}</p>}
                    {resp.email && <p>{resp.email}</p>}
                    <p>Plazo: {resp.plazo_dias} días</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CXCResponsablesGrid;
