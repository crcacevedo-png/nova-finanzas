// /app/frontend/src/pages/ImportarPacientes.js
// Módulo de Importación Masiva de Pacientes - NovaVision
// Soporta hasta 16,000+ registros con procesamiento por lotes

import React, { useState, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { 
  Upload, FileJson, CheckCircle, XCircle, AlertTriangle, 
  Download, Play, Pause, RefreshCw, Users, FileText,
  ChevronDown, ChevronUp, Trash2, Eye, BarChart3
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import { toast, Toaster } from 'sonner';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Tamaño de lote recomendado
const BATCH_SIZE = 500;

export default function ImportarPacientes() {
  const { user } = useAuth();
  const fileInputRef = useRef(null);
  
  // Estados principales
  const [file, setFile] = useState(null);
  const [jsonData, setJsonData] = useState(null);
  const [parseError, setParseError] = useState(null);
  
  // Estados de validación
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  
  // Estados de importación
  const [isImporting, setIsImporting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentBatch, setCurrentBatch] = useState(0);
  const [totalBatches, setTotalBatches] = useState(0);
  const [importProgress, setImportProgress] = useState(0);
  const [importResults, setImportResults] = useState({
    inserted: 0,
    duplicates: 0,
    errors: 0,
    errorDetails: [],
    duplicateDetails: []
  });
  
  // Opciones de importación
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [preserveRecordNumbers, setPreserveRecordNumbers] = useState(false);
  
  // Diálogos
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [showStatsDialog, setShowStatsDialog] = useState(false);
  const [importStats, setImportStats] = useState(null);
  
  // Referencia para control de importación
  const importControlRef = useRef({ paused: false, cancelled: false });

  // Manejar selección de archivo
  const handleFileSelect = useCallback((event) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;
    
    // Validar tipo de archivo
    if (!selectedFile.name.endsWith('.json')) {
      toast.error('Por favor seleccione un archivo JSON');
      return;
    }
    
    // Validar tamaño (máx 50MB)
    if (selectedFile.size > 50 * 1024 * 1024) {
      toast.error('El archivo es demasiado grande. Máximo 50MB.');
      return;
    }
    
    setFile(selectedFile);
    setParseError(null);
    setValidationResult(null);
    setImportResults({ inserted: 0, duplicates: 0, errors: 0, errorDetails: [], duplicateDetails: [] });
    
    // Leer y parsear archivo
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target.result;
        let data = JSON.parse(text);
        
        // Si no es array, buscar propiedad que sea array
        if (!Array.isArray(data)) {
          const arrayProps = Object.keys(data).filter(k => Array.isArray(data[k]));
          if (arrayProps.length > 0) {
            data = data[arrayProps[0]];
            toast.info(`Detectado array en propiedad "${arrayProps[0]}"`);
          } else {
            throw new Error('El archivo JSON debe contener un array de pacientes');
          }
        }
        
        setJsonData(data);
        toast.success(`Archivo cargado: ${data.length.toLocaleString()} registros`);
        
        // Calcular lotes
        const batches = Math.ceil(data.length / BATCH_SIZE);
        setTotalBatches(batches);
        
      } catch (error) {
        setParseError(error.message);
        setJsonData(null);
        toast.error('Error al parsear JSON: ' + error.message);
      }
    };
    
    reader.onerror = () => {
      setParseError('Error al leer el archivo');
      toast.error('Error al leer el archivo');
    };
    
    reader.readAsText(selectedFile);
  }, []);

  // Validar datos antes de importar
  const handleValidate = async () => {
    if (!jsonData || jsonData.length === 0) {
      toast.error('No hay datos para validar');
      return;
    }
    
    setIsValidating(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // Validar solo una muestra (primeros 1000)
      const sampleSize = Math.min(jsonData.length, 1000);
      const sample = jsonData.slice(0, sampleSize);
      
      const response = await axios.post(
        `${API_URL}/patients/import/validate`,
        sample,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setValidationResult(response.data);
      
      if (response.data.valid) {
        toast.success('Validación completada exitosamente');
      } else {
        toast.warning(`Validación completada con ${response.data.invalid_records} errores`);
      }
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al validar datos');
    } finally {
      setIsValidating(false);
    }
  };

  // Iniciar importación
  const handleStartImport = async () => {
    if (!jsonData || jsonData.length === 0) {
      toast.error('No hay datos para importar');
      return;
    }
    
    importControlRef.current = { paused: false, cancelled: false };
    setIsImporting(true);
    setIsPaused(false);
    setCurrentBatch(0);
    setImportProgress(0);
    setImportResults({ inserted: 0, duplicates: 0, errors: 0, errorDetails: [], duplicateDetails: [] });
    
    const token = localStorage.getItem('token');
    const batches = Math.ceil(jsonData.length / BATCH_SIZE);
    setTotalBatches(batches);
    
    let totalInserted = 0;
    let totalDuplicates = 0;
    let totalErrors = 0;
    let allErrorDetails = [];
    let allDuplicateDetails = [];
    
    for (let i = 0; i < batches; i++) {
      // Verificar si está pausado o cancelado
      while (importControlRef.current.paused) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      if (importControlRef.current.cancelled) {
        toast.warning('Importación cancelada');
        break;
      }
      
      const start = i * BATCH_SIZE;
      const end = Math.min((i + 1) * BATCH_SIZE, jsonData.length);
      const batchData = jsonData.slice(start, end);
      
      setCurrentBatch(i + 1);
      
      try {
        const response = await axios.post(
          `${API_URL}/patients/import/batch`,
          {
            patients: batchData,
            batch_number: i + 1,
            total_batches: batches,
            skip_duplicates: skipDuplicates,
            preserve_record_numbers: preserveRecordNumbers
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        const result = response.data;
        totalInserted += result.inserted;
        totalDuplicates += result.duplicates;
        totalErrors += result.errors;
        
        if (result.error_details?.length > 0) {
          allErrorDetails = [...allErrorDetails, ...result.error_details.map(e => ({
            ...e,
            batch: i + 1,
            globalRow: start + e.row
          }))];
        }
        
        if (result.duplicate_details?.length > 0) {
          allDuplicateDetails = [...allDuplicateDetails, ...result.duplicate_details.map(d => ({
            ...d,
            batch: i + 1,
            globalRow: start + d.row
          }))];
        }
        
        // Actualizar progreso
        const progress = Math.round(((i + 1) / batches) * 100);
        setImportProgress(progress);
        setImportResults({
          inserted: totalInserted,
          duplicates: totalDuplicates,
          errors: totalErrors,
          errorDetails: allErrorDetails.slice(-50),
          duplicateDetails: allDuplicateDetails.slice(-50)
        });
        
      } catch (error) {
        console.error(`Error en lote ${i + 1}:`, error);
        totalErrors += batchData.length;
        toast.error(`Error en lote ${i + 1}: ${error.response?.data?.detail || error.message}`);
      }
      
      // Pequeña pausa entre lotes para no sobrecargar
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    setIsImporting(false);
    
    if (!importControlRef.current.cancelled) {
      toast.success(
        `Importación completada: ${totalInserted.toLocaleString()} insertados, ` +
        `${totalDuplicates.toLocaleString()} duplicados, ${totalErrors.toLocaleString()} errores`
      );
    }
  };

  // Pausar/Reanudar importación
  const handleTogglePause = () => {
    importControlRef.current.paused = !importControlRef.current.paused;
    setIsPaused(!isPaused);
    toast.info(isPaused ? 'Importación reanudada' : 'Importación pausada');
  };

  // Cancelar importación
  const handleCancel = () => {
    importControlRef.current.cancelled = true;
    importControlRef.current.paused = false;
    setIsPaused(false);
  };

  // Descargar plantilla
  const handleDownloadTemplate = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/patients/import/template`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'plantilla_importacion_pacientes.json';
      a.click();
      URL.revokeObjectURL(url);
      
      toast.success('Plantilla descargada');
    } catch (error) {
      toast.error('Error al descargar plantilla');
    }
  };

  // Obtener estadísticas
  const handleShowStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/patients/import/stats`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setImportStats(response.data);
      setShowStatsDialog(true);
    } catch (error) {
      toast.error('Error al obtener estadísticas');
    }
  };

  // Limpiar todo
  const handleClear = () => {
    setFile(null);
    setJsonData(null);
    setParseError(null);
    setValidationResult(null);
    setImportResults({ inserted: 0, duplicates: 0, errors: 0, errorDetails: [], duplicateDetails: [] });
    setCurrentBatch(0);
    setImportProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Verificar permisos
  const canImport = user?.role === 'superadmin' || user?.role === 'admin';

  if (!canImport) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <Card className="p-8 text-center">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Acceso Denegado</h2>
            <p className="text-gray-500">Solo administradores pueden importar pacientes.</p>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      
      <div className="space-y-6 p-6 max-w-6xl mx-auto" data-testid="importar-pacientes-page">
        {/* Encabezado */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Upload className="w-7 h-7 text-blue-600" />
              Importación Masiva de Pacientes
            </h1>
            <p className="text-gray-500 mt-1">
              Importe hasta 16,000+ pacientes desde archivo JSON
            </p>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleDownloadTemplate}
              className="flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Plantilla
            </Button>
            <Button
              variant="outline"
              onClick={handleShowStats}
              className="flex items-center gap-2"
            >
              <BarChart3 className="w-4 h-4" />
              Estadísticas
            </Button>
          </div>
        </div>

        {/* Paso 1: Cargar archivo */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">1</span>
              Cargar Archivo JSON
            </CardTitle>
            <CardDescription>
              Seleccione un archivo JSON con los datos de pacientes a importar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div 
              className={`
                border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
                ${file ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'}
              `}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="hidden"
                disabled={isImporting}
              />
              
              {file ? (
                <div className="space-y-2">
                  <FileJson className="w-12 h-12 text-green-600 mx-auto" />
                  <p className="font-medium text-green-700">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                  {jsonData && (
                    <Badge className="bg-blue-100 text-blue-700">
                      {jsonData.length.toLocaleString()} registros detectados
                    </Badge>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                  <p className="text-gray-600">
                    Haga clic para seleccionar archivo o arrastre aquí
                  </p>
                  <p className="text-sm text-gray-400">
                    Formato: JSON • Máximo: 50MB
                  </p>
                </div>
              )}
            </div>
            
            {parseError && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-2 text-red-700">
                  <XCircle className="w-5 h-5" />
                  <span className="font-medium">Error de formato:</span>
                </div>
                <p className="text-red-600 mt-1">{parseError}</p>
              </div>
            )}
            
            {file && jsonData && (
              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowPreviewDialog(true)}
                  className="flex items-center gap-2"
                >
                  <Eye className="w-4 h-4" />
                  Vista Previa
                </Button>
                <Button
                  variant="outline"
                  onClick={handleClear}
                  className="flex items-center gap-2 text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                  Limpiar
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Paso 2: Validar y Configurar */}
        {jsonData && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">2</span>
                Validar y Configurar
              </CardTitle>
              <CardDescription>
                Valide los datos y configure las opciones de importación
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Opciones */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="skip-duplicates" 
                    checked={skipDuplicates}
                    onCheckedChange={setSkipDuplicates}
                    disabled={isImporting}
                  />
                  <Label htmlFor="skip-duplicates" className="text-sm cursor-pointer">
                    Omitir duplicados (por DPI)
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="preserve-records" 
                    checked={preserveRecordNumbers}
                    onCheckedChange={setPreserveRecordNumbers}
                    disabled={isImporting}
                  />
                  <Label htmlFor="preserve-records" className="text-sm cursor-pointer">
                    Preservar números de expediente originales
                  </Label>
                </div>
              </div>
              
              {/* Botón de validación */}
              <Button
                onClick={handleValidate}
                disabled={isValidating || isImporting}
                className="w-full md:w-auto"
              >
                {isValidating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Validando...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Validar Datos
                  </>
                )}
              </Button>
              
              {/* Resultado de validación */}
              {validationResult && (
                <div className={`p-4 rounded-lg border ${
                  validationResult.valid ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
                }`}>
                  <div className="flex items-center gap-2 mb-3">
                    {validationResult.valid ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-600" />
                    )}
                    <span className="font-medium">
                      {validationResult.valid ? 'Validación exitosa' : 'Validación con advertencias'}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Total:</span>
                      <span className="ml-2 font-medium">{validationResult.total_records.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Válidos:</span>
                      <span className="ml-2 font-medium text-green-600">{validationResult.valid_records.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Duplicados:</span>
                      <span className="ml-2 font-medium text-amber-600">{validationResult.duplicate_records.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Inválidos:</span>
                      <span className="ml-2 font-medium text-red-600">{validationResult.invalid_records.toLocaleString()}</span>
                    </div>
                  </div>
                  
                  {/* Errores y duplicados */}
                  {(validationResult.errors?.length > 0 || validationResult.duplicates?.length > 0) && (
                    <Accordion type="single" collapsible className="mt-4">
                      {validationResult.errors?.length > 0 && (
                        <AccordionItem value="errors">
                          <AccordionTrigger className="text-sm text-red-600">
                            Ver {validationResult.errors.length} errores
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="max-h-40 overflow-y-auto text-xs">
                              {validationResult.errors.map((e, i) => (
                                <div key={i} className="py-1 border-b">
                                  <span className="font-medium">Fila {e.row}:</span> {e.error}
                                </div>
                              ))}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      )}
                      {validationResult.duplicates?.length > 0 && (
                        <AccordionItem value="duplicates">
                          <AccordionTrigger className="text-sm text-amber-600">
                            Ver {validationResult.duplicates.length} duplicados
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="max-h-40 overflow-y-auto text-xs">
                              {validationResult.duplicates.map((d, i) => (
                                <div key={i} className="py-1 border-b">
                                  <span className="font-medium">Fila {d.row}:</span> {d.name} ({d.type}: {d.value})
                                </div>
                              ))}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      )}
                    </Accordion>
                  )}
                  
                  {/* Muestra de datos normalizados */}
                  {validationResult.sample_data?.length > 0 && (
                    <Accordion type="single" collapsible className="mt-2">
                      <AccordionItem value="sample">
                        <AccordionTrigger className="text-sm">
                          Ver muestra de datos normalizados
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="overflow-x-auto">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Nombre</TableHead>
                                  <TableHead>Apellido</TableHead>
                                  <TableHead>Género</TableHead>
                                  <TableHead>Nacimiento</TableHead>
                                  <TableHead>Teléfono</TableHead>
                                  <TableHead>DPI</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {validationResult.sample_data.map((p, i) => (
                                  <TableRow key={i}>
                                    <TableCell>{p.first_name}</TableCell>
                                    <TableCell>{p.last_name}</TableCell>
                                    <TableCell>{p.gender}</TableCell>
                                    <TableCell>{p.birth_date}</TableCell>
                                    <TableCell>{p.phone}</TableCell>
                                    <TableCell>{p.dpi || '-'}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Paso 3: Importar */}
        {jsonData && validationResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">3</span>
                Ejecutar Importación
              </CardTitle>
              <CardDescription>
                Se procesarán {jsonData.length.toLocaleString()} registros en {totalBatches} lotes de {BATCH_SIZE}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Controles de importación */}
              <div className="flex flex-wrap gap-2">
                {!isImporting ? (
                  <Button
                    onClick={handleStartImport}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Iniciar Importación
                  </Button>
                ) : (
                  <>
                    <Button
                      onClick={handleTogglePause}
                      variant="outline"
                    >
                      {isPaused ? (
                        <>
                          <Play className="w-4 h-4 mr-2" />
                          Reanudar
                        </>
                      ) : (
                        <>
                          <Pause className="w-4 h-4 mr-2" />
                          Pausar
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={handleCancel}
                      variant="destructive"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Cancelar
                    </Button>
                  </>
                )}
              </div>
              
              {/* Barra de progreso */}
              {(isImporting || importProgress > 0) && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>
                      Lote {currentBatch} de {totalBatches}
                      {isPaused && <span className="text-amber-600 ml-2">(Pausado)</span>}
                    </span>
                    <span>{importProgress}%</span>
                  </div>
                  <Progress value={importProgress} className="h-3" />
                </div>
              )}
              
              {/* Resultados de importación */}
              {(importResults.inserted > 0 || importResults.duplicates > 0 || importResults.errors > 0) && (
                <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {importResults.inserted.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500">Insertados</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-amber-600">
                      {importResults.duplicates.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500">Duplicados</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600">
                      {importResults.errors.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-500">Errores</div>
                  </div>
                </div>
              )}
              
              {/* Detalles de errores */}
              {importResults.errorDetails?.length > 0 && (
                <Accordion type="single" collapsible>
                  <AccordionItem value="errors">
                    <AccordionTrigger className="text-sm text-red-600">
                      Ver últimos {importResults.errorDetails.length} errores
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="max-h-40 overflow-y-auto text-xs">
                        {importResults.errorDetails.map((e, i) => (
                          <div key={i} className="py-1 border-b">
                            <span className="font-medium">Fila {e.globalRow} (Lote {e.batch}):</span> {e.error}
                          </div>
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              )}
            </CardContent>
          </Card>
        )}

        {/* Recomendaciones */}
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-lg text-blue-800 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Recomendaciones para 16,000+ Registros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-blue-700">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Divida el archivo</strong> en archivos más pequeños (5,000-8,000 registros) si experimenta problemas de memoria del navegador.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Use la opción &quot;Omitir duplicados&quot;</strong> para evitar duplicados por DPI. Si no tiene DPIs, los duplicados se detectarán por nombre exacto.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Valide antes de importar</strong> para detectar problemas en el formato de los datos antes de ejecutar la importación.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>No cierre el navegador</strong> durante la importación. Puede pausar y reanudar si necesita esperar.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Horario recomendado:</strong> Ejecute importaciones masivas fuera del horario pico (noche o fin de semana).</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><strong>Formatos de fecha aceptados:</strong> DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY. El sistema los normaliza automáticamente.</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Dialog de vista previa */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Vista Previa de Datos</DialogTitle>
            <DialogDescription>
              Primeros 10 registros del archivo cargado
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-auto">
            {jsonData && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    {Object.keys(jsonData[0] || {}).slice(0, 8).map(key => (
                      <TableHead key={key} className="text-xs">{key}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jsonData.slice(0, 10).map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{idx + 1}</TableCell>
                      {Object.keys(jsonData[0] || {}).slice(0, 8).map(key => (
                        <TableCell key={key} className="text-xs max-w-[150px] truncate">
                          {String(row[key] || '-')}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
          
          <DialogFooter>
            <Button onClick={() => setShowPreviewDialog(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog de estadísticas */}
      <Dialog open={showStatsDialog} onOpenChange={setShowStatsDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Estadísticas de Pacientes
            </DialogTitle>
          </DialogHeader>
          
          {importStats && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg text-center">
                  <div className="text-3xl font-bold text-blue-700">
                    {importStats.total_patients?.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-600">Total Pacientes</div>
                </div>
                <div className="p-4 bg-green-50 rounded-lg text-center">
                  <div className="text-3xl font-bold text-green-700">
                    {importStats.imported_patients?.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-600">Importados</div>
                </div>
              </div>
              
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-gray-600">Porcentaje importado</span>
                  <span className="font-medium">{importStats.import_percentage}%</span>
                </div>
                <Progress value={importStats.import_percentage} />
              </div>
              
              {importStats.recent_batches?.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Últimas importaciones</h4>
                  <div className="space-y-1 text-sm">
                    {importStats.recent_batches.map((batch, i) => (
                      <div key={i} className="flex justify-between text-gray-600">
                        <span>Lote {batch._id}</span>
                        <span>{batch.count} registros</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button onClick={() => setShowStatsDialog(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
