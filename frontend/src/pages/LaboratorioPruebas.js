// /app/frontend/src/pages/LaboratorioPruebas.js
// Panel de Laboratorio de Pruebas - Solo SuperAdmin
// Generación y ejecución de pruebas E2E

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { 
  FlaskConical, Database, Users, Play, Trash2, 
  AlertTriangle, CheckCircle, XCircle, Clock,
  Download, RefreshCw, FileText, Shield
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function LaboratorioPruebas() {
  const { user, hasRole } = useAuth();
  const navigate = useNavigate();
  
  const [estado, setEstado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [operacionEnCurso, setOperacionEnCurso] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [credenciales, setCredenciales] = useState(null);
  const [confirmacionPurga, setConfirmacionPurga] = useState('');

  // Verificar acceso
  useEffect(() => {
    if (!hasRole('superadmin')) {
      navigate('/dashboard');
    }
  }, [hasRole, navigate]);

  // Cargar estado inicial
  const cargarEstado = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/laboratorio-pruebas/estado`);
      setEstado(response.data);
      setError(null);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('El Laboratorio de Pruebas no está disponible en producción.');
      } else {
        setError(err.response?.data?.detail || 'Error al cargar estado');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarEstado();
  }, [cargarEstado]);

  // Seed datos maestros
  const seedDatosMaestros = async () => {
    try {
      setOperacionEnCurso('seed_maestros');
      setResultado(null);
      const response = await axios.post(`${API_URL}/api/laboratorio-pruebas/seed/datos-maestros`);
      setResultado(response.data);
      await cargarEstado();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al generar datos maestros');
    } finally {
      setOperacionEnCurso(null);
    }
  };

  // Seed pacientes
  const seedPacientes = async () => {
    try {
      setOperacionEnCurso('seed_pacientes');
      setResultado(null);
      const response = await axios.post(`${API_URL}/api/laboratorio-pruebas/seed/pacientes`);
      setResultado(response.data);
      await cargarEstado();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al generar pacientes');
    } finally {
      setOperacionEnCurso(null);
    }
  };

  // Seed completo
  const seedCompleto = async () => {
    try {
      setOperacionEnCurso('seed_completo');
      setResultado(null);
      const response = await axios.post(`${API_URL}/api/laboratorio-pruebas/seed/completo`);
      setResultado(response.data);
      await cargarEstado();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al ejecutar seed completo');
    } finally {
      setOperacionEnCurso(null);
    }
  };

  // Purgar datos
  const purgarDatos = async () => {
    if (confirmacionPurga !== 'ELIMINAR DATOS DE PRUEBA') {
      setError('Debe escribir exactamente: ELIMINAR DATOS DE PRUEBA');
      return;
    }
    
    try {
      setOperacionEnCurso('purga');
      setResultado(null);
      const response = await axios.delete(
        `${API_URL}/api/laboratorio-pruebas/purgar?confirmacion=${encodeURIComponent(confirmacionPurga)}`
      );
      setResultado(response.data);
      setConfirmacionPurga('');
      await cargarEstado();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al purgar datos');
    } finally {
      setOperacionEnCurso(null);
    }
  };

  // Obtener credenciales
  const obtenerCredenciales = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/laboratorio-pruebas/credenciales-prueba`);
      setCredenciales(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al obtener credenciales');
    }
  };

  if (!hasRole('superadmin')) {
    return null;
  }

  const totalDatosPrueba = estado ? Object.values(estado.conteo_por_coleccion).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      {/* Banner de advertencia si hay datos de prueba */}
      {estado?.tiene_datos_prueba && (
        <Alert className="mb-6 border-amber-500 bg-amber-500/10">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <AlertTitle className="text-amber-500">Datos de Prueba Activos</AlertTitle>
          <AlertDescription className="text-amber-400">
            Hay {totalDatosPrueba.toLocaleString()} registros de prueba en la base de datos.
            Estos datos tienen el prefijo PRB- y la bandera esDatoPrueba: true.
          </AlertDescription>
        </Alert>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-teal-500/20 rounded-lg">
            <FlaskConical className="h-8 w-8 text-teal-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Laboratorio de Pruebas</h1>
            <p className="text-slate-400">Generación y verificación de datos E2E</p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-4">
          <Shield className="h-4 w-4 text-amber-400" />
          <span className="text-sm text-amber-400">Solo disponible para SuperAdmin en ambiente de desarrollo</span>
        </div>
      </div>

      {/* Error global */}
      {error && (
        <Alert className="mb-6 border-red-500 bg-red-500/10">
          <XCircle className="h-5 w-5 text-red-500" />
          <AlertTitle className="text-red-500">Error</AlertTitle>
          <AlertDescription className="text-red-400">{error}</AlertDescription>
        </Alert>
      )}

      {/* Resultado de operación */}
      {resultado && (
        <Alert className={`mb-6 ${resultado.success ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'}`}>
          {resultado.success ? (
            <CheckCircle className="h-5 w-5 text-green-500" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500" />
          )}
          <AlertTitle className={resultado.success ? 'text-green-500' : 'text-red-500'}>
            {resultado.success ? 'Operación Exitosa' : 'Operación Fallida'}
          </AlertTitle>
          <AlertDescription className={resultado.success ? 'text-green-400' : 'text-red-400'}>
            {resultado.message}
            {resultado.datos_creados && Object.keys(resultado.datos_creados).length > 0 && (
              <div className="mt-2">
                <strong>Datos creados:</strong>
                <ul className="list-disc list-inside ml-2">
                  {Object.entries(resultado.datos_creados).map(([key, value]) => (
                    <li key={key}>{key}: {value}</li>
                  ))}
                </ul>
              </div>
            )}
            {resultado.datos_eliminados && Object.keys(resultado.datos_eliminados).length > 0 && (
              <div className="mt-2">
                <strong>Datos eliminados:</strong>
                <ul className="list-disc list-inside ml-2">
                  {Object.entries(resultado.datos_eliminados).map(([key, value]) => (
                    <li key={key}>{key}: {value}</li>
                  ))}
                </ul>
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Estado actual */}
        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Database className="h-5 w-5 text-teal-400" />
              Estado de Datos de Prueba
            </CardTitle>
            <CardDescription className="text-slate-400">
              Registros con esDatoPrueba: true
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 text-teal-400 animate-spin" />
              </div>
            ) : estado ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                  <span className="text-slate-300">Total registros de prueba</span>
                  <span className="text-2xl font-bold text-teal-400">{totalDatosPrueba.toLocaleString()}</span>
                </div>
                
                {Object.keys(estado.conteo_por_coleccion).length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {Object.entries(estado.conteo_por_coleccion).map(([col, count]) => (
                      <div key={col} className="flex items-center justify-between p-2 bg-slate-700/30 rounded">
                        <span className="text-sm text-slate-400">{col}</span>
                        <span className="text-sm font-medium text-white">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-4">No hay datos de prueba</p>
                )}
                
                {estado.fecha_ultimo_seed && (
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Clock className="h-4 w-4" />
                    Último seed: {new Date(estado.fecha_ultimo_seed).toLocaleString()}
                  </div>
                )}
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={cargarEstado}
                  className="w-full mt-4"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Actualizar
                </Button>
              </div>
            ) : (
              <p className="text-red-400">Error al cargar estado</p>
            )}
          </CardContent>
        </Card>

        {/* Generación de datos */}
        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-400" />
              Generación de Datos
            </CardTitle>
            <CardDescription className="text-slate-400">
              Crear datos sintéticos para pruebas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              className="w-full bg-blue-600 hover:bg-blue-700"
              onClick={seedDatosMaestros}
              disabled={operacionEnCurso !== null}
            >
              {operacionEnCurso === 'seed_maestros' ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Database className="h-4 w-4 mr-2" />
              )}
              Fase 1: Datos Maestros
            </Button>
            <p className="text-xs text-slate-500">
              Bodegas, proveedores, productos, usuarios, médicos
            </p>

            <Button
              className="w-full bg-green-600 hover:bg-green-700"
              onClick={seedPacientes}
              disabled={operacionEnCurso !== null}
            >
              {operacionEnCurso === 'seed_pacientes' ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Users className="h-4 w-4 mr-2" />
              )}
              Fase 2: Pacientes
            </Button>
            <p className="text-xs text-slate-500">
              14 pacientes sintéticos con perfiles específicos
            </p>

            <div className="border-t border-slate-700 pt-4">
              <Button
                className="w-full bg-teal-600 hover:bg-teal-700"
                onClick={seedCompleto}
                disabled={operacionEnCurso !== null}
              >
                {operacionEnCurso === 'seed_completo' ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Ejecutar Seed Completo
              </Button>
              <p className="text-xs text-slate-500 mt-2">
                Ejecuta Fase 1 + Fase 2 en secuencia
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Credenciales de prueba */}
        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Shield className="h-5 w-5 text-purple-400" />
              Credenciales de Prueba
            </CardTitle>
            <CardDescription className="text-slate-400">
              Usuarios generados para testing
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!credenciales ? (
              <Button
                variant="outline"
                onClick={obtenerCredenciales}
                className="w-full"
              >
                Mostrar Credenciales
              </Button>
            ) : (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {credenciales.usuarios_prueba.map((u, i) => (
                  <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm text-teal-400">{u.username}</span>
                      <span className="text-xs px-2 py-1 bg-slate-600 rounded text-slate-300">{u.role}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Contraseña: <span className="font-mono text-slate-300">{u.password}</span>
                    </div>
                    {u.nota && <div className="text-xs text-slate-500">{u.nota}</div>}
                  </div>
                ))}
                <Alert className="border-amber-500 bg-amber-500/10">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <AlertDescription className="text-xs text-amber-400">
                    {credenciales.advertencia}
                  </AlertDescription>
                </Alert>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Purga de datos */}
        <Card className="bg-slate-800/50 border-red-900/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-red-400" />
              Purgar Datos de Prueba
            </CardTitle>
            <CardDescription className="text-slate-400">
              Eliminar TODOS los datos con esDatoPrueba: true
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-red-500 bg-red-500/10">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <AlertDescription className="text-xs text-red-400">
                Esta acción es irreversible. Se eliminarán todos los datos de prueba.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <label className="text-sm text-slate-400">
                Escriba &quot;ELIMINAR DATOS DE PRUEBA&quot; para confirmar:
              </label>
              <input
                type="text"
                value={confirmacionPurga}
                onChange={(e) => setConfirmacionPurga(e.target.value)}
                placeholder="ELIMINAR DATOS DE PRUEBA"
                className="w-full p-2 bg-slate-700 border border-slate-600 rounded text-white text-sm"
              />
            </div>
            
            <Button
              variant="destructive"
              className="w-full"
              onClick={purgarDatos}
              disabled={operacionEnCurso !== null || confirmacionPurga !== 'ELIMINAR DATOS DE PRUEBA'}
            >
              {operacionEnCurso === 'purga' ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Purgar Datos de Prueba
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Próximamente */}
      <Card className="mt-6 bg-slate-800/50 border-slate-700 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-400" />
            Próximamente
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-slate-500">
            <div className="p-4 bg-slate-700/30 rounded-lg">
              <h4 className="font-medium text-slate-300 mb-2">Fase 3: Recorridos E2E</h4>
              <p className="text-sm">Ejecución de los 9 recorridos de prueba automatizados</p>
            </div>
            <div className="p-4 bg-slate-700/30 rounded-lg">
              <h4 className="font-medium text-slate-300 mb-2">Fase 4: Batería de Pruebas</h4>
              <p className="text-sm">70+ pruebas de verificación con reportes detallados</p>
            </div>
            <div className="p-4 bg-slate-700/30 rounded-lg">
              <h4 className="font-medium text-slate-300 mb-2">Fase 5: Pruebas de Volumen</h4>
              <p className="text-sm">Generación de datos masivos y medición de rendimiento</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
