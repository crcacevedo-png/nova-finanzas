// /app/frontend/src/pages/ImportarEvaluaciones.js
// Módulo de Importación Masiva de Evaluaciones Oftalmológicas - NovaVision
// Enlaza cada evaluación con su paciente por expediente (record_number) o DPI.

import React, { useState, useCallback } from 'react';
import Layout from '../components/Layout';
import {
  Upload, FileJson, CheckCircle, XCircle, AlertTriangle,
  Download, Play, Link2, Users, ClipboardList
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { toast, Toaster } from 'sonner';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BATCH_SIZE = 500;

export default function ImportarEvaluaciones() {
  const [file, setFile] = useState(null);
  const [jsonData, setJsonData] = useState(null);
  const [parseError, setParseError] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [totalBatches, setTotalBatches] = useState(0);
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [results, setResults] = useState(null);

  const getToken = () => localStorage.getItem('token');

  const handleFileSelect = useCallback((e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
    setFile(selectedFile);
    setParseError(null);
    setValidationResult(null);
    setResults(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        let data = JSON.parse(ev.target.result);
        if (!Array.isArray(data)) {
          const arrProps = Object.keys(data).filter(k => Array.isArray(data[k]));
          if (arrProps.length > 0) {
            data = data[arrProps[0]];
            toast.info(`Detectado array en propiedad "${arrProps[0]}"`);
          } else {
            throw new Error('El archivo JSON debe contener un array de evaluaciones');
          }
        }
        setJsonData(data);
        setTotalBatches(Math.ceil(data.length / BATCH_SIZE));
        toast.success(`Archivo cargado: ${data.length.toLocaleString()} evaluaciones`);
      } catch (err) {
        setParseError(err.message);
        setJsonData(null);
        toast.error('Error al parsear JSON: ' + err.message);
      }
    };
    reader.onerror = () => {
      setParseError('Error al leer el archivo');
      toast.error('Error al leer el archivo');
    };
    reader.readAsText(selectedFile);
  }, []);

  const handleValidate = async () => {
    if (!jsonData) return;
    setIsValidating(true);
    setValidationResult(null);
    try {
      const sample = jsonData.slice(0, Math.min(2000, jsonData.length));
      const { data } = await axios.post(
        `${API_URL}/evaluaciones/import/validate`,
        sample,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      setValidationResult(data);
      if (data.linkable_records === 0) {
        toast.error('Ninguna evaluación pudo enlazarse con un paciente. Revisa los expedientes.');
      } else if (data.huerfanas_count > 0 || data.sin_clave_enlace > 0) {
        toast.warning(`${data.linkable_records} enlazan, pero ${data.huerfanas_count} sin paciente y ${data.sin_clave_enlace} sin clave.`);
      } else {
        toast.success(`${data.linkable_records} evaluaciones listas para importar`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al validar');
    } finally {
      setIsValidating(false);
    }
  };

  const handleImport = async () => {
    if (!jsonData) return;
    setIsImporting(true);
    setProgress(0);
    const totals = { inserted: 0, orphaned: 0, sin_clave: 0, duplicates: 0, orphanedDetails: [] };
    const batches = Math.ceil(jsonData.length / BATCH_SIZE);
    try {
      for (let i = 0; i < batches; i++) {
        const start = i * BATCH_SIZE;
        const batchData = jsonData.slice(start, Math.min(start + BATCH_SIZE, jsonData.length));
        const { data } = await axios.post(
          `${API_URL}/evaluaciones/import/batch`,
          { items: batchData, batch_number: i + 1, skip_duplicates: skipDuplicates },
          { headers: { Authorization: `Bearer ${getToken()}` } }
        );
        totals.inserted += data.inserted;
        totals.orphaned += data.orphaned;
        totals.sin_clave += data.sin_clave;
        totals.duplicates += data.duplicates;
        if (data.orphaned_details?.length) {
          totals.orphanedDetails = [...totals.orphanedDetails, ...data.orphaned_details].slice(-50);
        }
        setProgress(Math.round(((i + 1) / batches) * 100));
        setResults({ ...totals });
      }
      toast.success(`Importación completa: ${totals.inserted.toLocaleString()} evaluaciones insertadas`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error durante la importación');
    } finally {
      setIsImporting(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const { data } = await axios.get(
        `${API_URL}/evaluaciones/import/template`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'plantilla_evaluaciones.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('No se pudo descargar la plantilla');
    }
  };

  return (
    <Layout>
      <Toaster position="top-right" richColors />
      <div className="max-w-5xl mx-auto space-y-6" data-testid="importar-evaluaciones-page">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
              <ClipboardList className="w-8 h-8 text-emerald-700" />
              Importar Evaluaciones
            </h1>
            <p className="text-slate-500 mt-1 text-sm">
              Carga masiva de expedientes clínicos enlazados por número de expediente.
            </p>
          </div>
          <Button variant="outline" onClick={downloadTemplate} data-testid="download-template-btn">
            <Download className="w-4 h-4 mr-2" /> Descargar plantilla
          </Button>
        </div>

        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-5 text-sm text-amber-900 flex gap-3">
            <Link2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <strong>Importante:</strong> importa primero los <b>pacientes</b> (preservando su expediente).
              Cada evaluación debe incluir <code>expediente</code> (igual al del paciente) o <code>dpi</code> para enlazarse.
              Incluye <code>id_origen</code> para evitar duplicados en reimportaciones.
            </div>
          </CardContent>
        </Card>

        {/* Paso 1: Cargar archivo */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileJson className="w-5 h-5" /> 1. Selecciona el archivo JSON
            </CardTitle>
            <CardDescription>Array JSON de evaluaciones exportadas de Access.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              type="file"
              accept=".json,application/json"
              onChange={handleFileSelect}
              data-testid="file-input"
              className="block w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-700 file:text-white hover:file:bg-emerald-800 cursor-pointer"
            />
            {parseError && (
              <div className="text-sm text-red-600 flex items-center gap-2" data-testid="parse-error">
                <XCircle className="w-4 h-4" /> {parseError}
              </div>
            )}
            {jsonData && (
              <div className="flex items-center gap-3 flex-wrap" data-testid="file-loaded-info">
                <Badge variant="secondary" className="text-sm">
                  <Users className="w-4 h-4 mr-1" /> {jsonData.length.toLocaleString()} registros
                </Badge>
                <Badge variant="outline">{totalBatches} lote(s) de {BATCH_SIZE}</Badge>
                <span className="text-xs text-slate-500 truncate">{file?.name}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Paso 2: Validar */}
        {jsonData && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle className="w-5 h-5" /> 2. Validar enlace con pacientes
              </CardTitle>
              <CardDescription>Verifica cuántas evaluaciones encuentran a su paciente por expediente/DPI.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={handleValidate} disabled={isValidating} data-testid="validate-btn">
                {isValidating ? 'Validando...' : 'Validar muestra'}
              </Button>

              {validationResult && (
                <div className="space-y-4" data-testid="validation-result">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg bg-emerald-50 text-center">
                      <div className="text-2xl font-bold text-emerald-700" data-testid="stat-linkable">{validationResult.linkable_records}</div>
                      <div className="text-xs text-slate-600">Enlazan</div>
                    </div>
                    <div className="p-3 rounded-lg bg-red-50 text-center">
                      <div className="text-2xl font-bold text-red-600" data-testid="stat-orphaned">{validationResult.huerfanas_count}</div>
                      <div className="text-xs text-slate-600">Sin paciente</div>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-50 text-center">
                      <div className="text-2xl font-bold text-amber-600" data-testid="stat-nokey">{validationResult.sin_clave_enlace}</div>
                      <div className="text-xs text-slate-600">Sin clave</div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-100 text-center">
                      <div className="text-2xl font-bold text-slate-700" data-testid="stat-total">{validationResult.total_records}</div>
                      <div className="text-xs text-slate-600">Total muestra</div>
                    </div>
                  </div>

                  {validationResult.sample?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-2">Vista previa del enlace</p>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Clave</TableHead>
                            <TableHead>Paciente enlazado</TableHead>
                            <TableHead>Fecha</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {validationResult.sample.map((s, i) => (
                            <TableRow key={i}>
                              <TableCell className="font-mono text-xs">{s.clave}</TableCell>
                              <TableCell>{s.paciente || '—'}</TableCell>
                              <TableCell>{s.fecha || '—'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {validationResult.huerfanas?.length > 0 && (
                    <div className="text-sm text-red-700 bg-red-50 p-3 rounded-lg flex gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <span>{validationResult.huerfanas.length} evaluación(es) no encontraron paciente. Ejemplos de clave: {validationResult.huerfanas.slice(0, 8).map(h => h.clave).join(', ')}</span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Paso 3: Importar */}
        {jsonData && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Play className="w-5 h-5" /> 3. Importar
              </CardTitle>
              <CardDescription>Procesa {jsonData.length.toLocaleString()} evaluaciones en {totalBatches} lote(s).</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="skip-dup"
                  checked={skipDuplicates}
                  onCheckedChange={setSkipDuplicates}
                  data-testid="skip-duplicates-checkbox"
                />
                <Label htmlFor="skip-dup" className="text-sm cursor-pointer">
                  Omitir duplicados (por <code>id_origen</code>)
                </Label>
              </div>

              <Button
                onClick={handleImport}
                disabled={isImporting}
                className="bg-emerald-700 hover:bg-emerald-800"
                data-testid="import-btn"
              >
                <Upload className="w-4 h-4 mr-2" />
                {isImporting ? `Importando... ${progress}%` : 'Iniciar importación'}
              </Button>

              {(isImporting || progress > 0) && (
                <Progress value={progress} className="h-2" data-testid="import-progress" />
              )}

              {results && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="import-results">
                  <div className="p-3 rounded-lg bg-emerald-50 text-center">
                    <div className="text-2xl font-bold text-emerald-700" data-testid="result-inserted">{results.inserted.toLocaleString()}</div>
                    <div className="text-xs text-slate-600">Insertadas</div>
                  </div>
                  <div className="p-3 rounded-lg bg-red-50 text-center">
                    <div className="text-2xl font-bold text-red-600" data-testid="result-orphaned">{results.orphaned.toLocaleString()}</div>
                    <div className="text-xs text-slate-600">Sin paciente</div>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-50 text-center">
                    <div className="text-2xl font-bold text-amber-600">{results.sin_clave.toLocaleString()}</div>
                    <div className="text-xs text-slate-600">Sin clave</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-100 text-center">
                    <div className="text-2xl font-bold text-slate-700">{results.duplicates.toLocaleString()}</div>
                    <div className="text-xs text-slate-600">Duplicados</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
