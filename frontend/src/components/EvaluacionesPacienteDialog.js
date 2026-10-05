import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { toast } from 'sonner';
import {
  FileText,
  Download,
  Lock,
  ChevronLeft,
  Calendar,
  Stethoscope,
  Eye,
  Glasses,
  Pill,
  ClipboardList,
  Activity,
  Scissors,
} from 'lucide-react';
import { NotaCirugia } from './NotaCirugia';
import { surgeryNoteApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Formatea una fecha (YYYY-MM-DD o ISO) a DD/MM/YYYY
const formatFecha = (f) => {
  if (!f) return 'Sin fecha';
  try {
    const soloFecha = String(f).split('T')[0];
    const [y, m, d] = soloFecha.split('-');
    if (y && m && d) return `${d}/${m}/${y}`;
    return String(f);
  } catch (e) {
    return String(f);
  }
};

// Muestra el ojo (OD/OS/OU) como etiqueta legible
const ojoLabel = (ojo) => ({ OD: 'Ojo derecho', OS: 'Ojo izquierdo', OU: 'Ambos ojos' }[ojo] || ojo || '');

const Campo = ({ label, value }) => {
  if (!value) return null;
  return (
    <div className="flex flex-col">
      <span className="text-[11px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-sm text-slate-800 whitespace-pre-wrap">{value}</span>
    </div>
  );
};

const SeccionDetalle = ({ icon: Icon, titulo, children, testid }) => (
  <div className="rounded-lg border border-slate-200 bg-white p-4" data-testid={testid}>
    <div className="mb-3 flex items-center gap-2">
      <Icon className="h-4 w-4 text-[#0F6E56]" />
      <h4 className="text-sm font-semibold text-slate-800">{titulo}</h4>
    </div>
    {children}
  </div>
);

// Render de una receta de anteojos
const RecetaAnteojos = ({ receta }) => {
  const od = receta.od || {};
  const os = receta.os || {};
  return (
    <div className="rounded-md bg-slate-50 p-3 text-sm">
      <div className="grid grid-cols-[80px_1fr_1fr_1fr_1fr] gap-2 text-xs font-semibold text-slate-500">
        <span>Ojo</span><span>Esfera</span><span>Cilindro</span><span>Eje</span><span>Adición</span>
      </div>
      {[['OD', od], ['OS', os]].map(([lbl, ojo]) => (
        <div key={lbl} className="grid grid-cols-[80px_1fr_1fr_1fr_1fr] gap-2 py-0.5 text-slate-800">
          <span className="font-semibold">{lbl}</span>
          <span>{ojo.esfera || '—'}</span>
          <span>{ojo.cilindro || '—'}</span>
          <span>{ojo.eje || '—'}</span>
          <span>{ojo.adicion || '—'}</span>
        </div>
      ))}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        {receta.tipo_lente && <span><strong>Tipo:</strong> {receta.tipo_lente}</span>}
        {receta.material && <span><strong>Material:</strong> {receta.material}</span>}
        {receta.tratamientos && <span><strong>Tratamientos:</strong> {receta.tratamientos}</span>}
        {receta.distancia_pupilar && <span><strong>DP:</strong> {receta.distancia_pupilar}</span>}
        {receta.uso && <span><strong>Uso:</strong> {receta.uso}</span>}
      </div>
      {receta.observaciones && (
        <p className="mt-1 text-xs italic text-slate-500">{receta.observaciones}</p>
      )}
    </div>
  );
};

// Render de una receta de lentes de contacto
const RecetaLentes = ({ receta }) => {
  const od = receta.od || {};
  const os = receta.os || {};
  return (
    <div className="rounded-md bg-slate-50 p-3 text-sm">
      <div className="grid grid-cols-[80px_1fr_1fr_1fr] gap-2 text-xs font-semibold text-slate-500">
        <span>Ojo</span><span>Poder</span><span>Curva base</span><span>Diámetro</span>
      </div>
      {[['OD', od], ['OS', os]].map(([lbl, ojo]) => (
        <div key={lbl} className="grid grid-cols-[80px_1fr_1fr_1fr] gap-2 py-0.5 text-slate-800">
          <span className="font-semibold">{lbl}</span>
          <span>{ojo.poder || '—'}</span>
          <span>{ojo.curva_base || '—'}</span>
          <span>{ojo.diametro || '—'}</span>
        </div>
      ))}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        {receta.marca && <span><strong>Marca:</strong> {receta.marca}</span>}
        {receta.tipo && <span><strong>Tipo:</strong> {receta.tipo}</span>}
        {receta.regimen_reemplazo && <span><strong>Reemplazo:</strong> {receta.regimen_reemplazo}</span>}
      </div>
      {receta.observaciones && (
        <p className="mt-1 text-xs italic text-slate-500">{receta.observaciones}</p>
      )}
    </div>
  );
};

export const EvaluacionesPacienteDialog = ({ patient, open, onOpenChange }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [notas, setNotas] = useState([]);
  const [selectedNota, setSelectedNota] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  const [pdfLoadingId, setPdfLoadingId] = useState(null);

  const fetchNotas = useCallback(async (pid) => {
    try {
      const { data } = await surgeryNoteApi.getByPatient(pid);
      setNotas(data.data || []);
    } catch (error) {
      setNotas([]);
    }
  }, []);

  const fetchEvaluaciones = useCallback(async (pid) => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API_URL}/evaluaciones?paciente_id=${pid}&limit=100`);
      const list = data.data || [];
      list.sort((a, b) => {
        const fa = a.fecha || '';
        const fb = b.fecha || '';
        if (fa !== fb) return fb.localeCompare(fa);
        return (b.fecha_creacion || '').localeCompare(a.fecha_creacion || '');
      });
      setEvaluaciones(list);
    } catch (error) {
      console.error('Error al cargar evaluaciones:', error);
      toast.error('No se pudieron cargar las evaluaciones del paciente');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && patient?.id) {
      setSelected(null);
      setSelectedNota(null);
      fetchEvaluaciones(patient.id);
      fetchNotas(patient.id);
    }
    if (!open) {
      setEvaluaciones([]);
      setNotas([]);
      setSelected(null);
      setSelectedNota(null);
    }
  }, [open, patient?.id, fetchEvaluaciones, fetchNotas]);

  const abrirDetalle = async (ev) => {
    setLoadingDetalle(true);
    setSelected({ id: ev.id });
    try {
      const { data } = await axios.get(`${API_URL}/evaluaciones/${ev.id}`);
      setSelected(data);
    } catch (error) {
      console.error('Error al cargar la evaluación:', error);
      toast.error('No se pudo abrir la evaluación');
      setSelected(null);
    } finally {
      setLoadingDetalle(false);
    }
  };

  const descargarPDF = async (ev) => {
    setPdfLoadingId(ev.id);
    try {
      const response = await axios.get(`${API_URL}/evaluaciones/${ev.id}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `evaluacion_${(patient?.record_number || patient?.id || '').toString()}_${formatFecha(ev.fecha).replace(/\//g, '-')}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error al descargar PDF:', error);
      toast.error('No se pudo generar el PDF de la evaluación');
    } finally {
      setPdfLoadingId(null);
    }
  };

  const nombrePaciente = patient?.full_name
    || [patient?.first_name, patient?.last_name].filter(Boolean).join(' ')
    || patient?.paciente_nombre
    || 'Paciente';

  const renderLista = () => {
    if (loading) {
      return (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      );
    }
    if (evaluaciones.length === 0 && notas.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <ClipboardList className="mb-3 h-10 w-10 text-slate-300" />
          <p className="text-sm text-slate-500">Este paciente aún no tiene registros clínicos</p>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        {/* Eventos de cirugía */}
        {notas.length > 0 && (
          <div className="space-y-2" data-testid="lista-notas-cirugia">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cirugías</p>
            {notas.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => setSelectedNota(n)}
                className="flex w-full items-center justify-between rounded-lg border border-purple-200 bg-purple-50/40 p-3 text-left transition-colors hover:border-purple-400 hover:bg-purple-50"
                data-testid={`nota-cirugia-item-${n.id}`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Scissors className="h-4 w-4 text-purple-600" />
                    <span className="truncate font-semibold text-slate-800">{n.procedure}</span>
                    {n.estado === 'cerrada' && <Badge className="bg-red-100 text-red-700 text-[10px]"><Lock className="mr-1 h-3 w-3" />Cerrada</Badge>}
                    {n.estado !== 'cerrada' && n.bloqueada && <Badge className="bg-amber-100 text-amber-700 text-[10px]"><Lock className="mr-1 h-3 w-3" />Bloqueada</Badge>}
                    {n.estado !== 'cerrada' && !n.bloqueada && <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Abierta</Badge>}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">{formatFecha(n.fecha)} · {n.eye} · {n.surgeon}</p>
                </div>
                <Eye className="h-4 w-4 shrink-0 text-purple-600" />
              </button>
            ))}
          </div>
        )}

        {/* Evaluaciones */}
        {evaluaciones.length > 0 && (
          <div className="space-y-2" data-testid="lista-evaluaciones-paciente">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Evaluaciones</p>
            {evaluaciones.map((ev) => {
          const dxList = Array.isArray(ev.diagnosticos) ? ev.diagnosticos : [];
          const dxPrincipal = dxList.length > 0
            ? (dxList[0].descripcion || dxList[0].nombre || '')
            : (ev.diagnostico || '');
          const dxExtra = dxList.length > 1 ? ` +${dxList.length - 1} más` : '';
          return (
            <div
              key={ev.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 p-3 transition-colors hover:border-[#0F6E56] hover:bg-[#F0FBF7]"
              data-testid={`evaluacion-item-${ev.id}`}
            >
              <button
                type="button"
                onClick={() => abrirDetalle(ev)}
                className="flex-1 text-left"
                data-testid={`abrir-evaluacion-${ev.id}`}
              >
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-[#0F6E56]" />
                  <span className="font-semibold text-slate-800">{formatFecha(ev.fecha)}</span>
                  {ev.sellado && (
                    <Badge className="bg-red-100 text-red-700 text-[10px]">
                      <Lock className="mr-1 h-3 w-3" />Sellado
                    </Badge>
                  )}
                </div>
                {dxPrincipal ? (
                  <p className="mt-1 truncate text-xs text-teal-700">
                    <strong>Dx:</strong> {dxPrincipal}{dxExtra}
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-slate-400">Sin diagnóstico registrado</p>
                )}
                {ev.medico_nombre && (
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                    <Stethoscope className="h-3 w-3" />{ev.medico_nombre}
                  </p>
                )}
              </button>
              <div className="flex items-center gap-1 pl-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => abrirDetalle(ev)}
                  className="h-8 gap-1 text-[#0F6E56] hover:bg-[#E1F5EE]"
                  data-testid={`ver-detalle-evaluacion-${ev.id}`}
                >
                  <Eye className="h-4 w-4" />
                  <span className="hidden sm:inline">Ver</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => descargarPDF(ev)}
                  disabled={pdfLoadingId === ev.id}
                  className="h-8 gap-1 text-slate-600 hover:bg-slate-100"
                  data-testid={`pdf-evaluacion-${ev.id}`}
                >
                  <Download className="h-4 w-4" />
                  <span className="hidden sm:inline">{pdfLoadingId === ev.id ? 'Generando…' : 'PDF'}</span>
                </Button>
              </div>
            </div>
          );
        })}
          </div>
        )}
      </div>
    );
  };

  const renderDetalle = () => {
    if (loadingDetalle || !selected?.paciente_id) {
      return (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      );
    }
    const ev = selected;
    const examen = ev.examen || {};
    const recetas = ev.recetas || {};
    const anteojosLista = Array.isArray(recetas.anteojos_lista) ? recetas.anteojos_lista : [];
    const lentesLista = Array.isArray(recetas.lentes_contacto_lista) ? recetas.lentes_contacto_lista : [];
    const medicamentos = recetas.medicamentos?.items || [];
    const dxList = Array.isArray(ev.diagnosticos) ? ev.diagnosticos : [];
    const recomendaciones = ev.recomendaciones || {};

    return (
      <div className="space-y-3" data-testid="detalle-evaluacion">
        {/* Encabezado */}
        <SeccionDetalle icon={Calendar} titulo="Datos de la consulta" testid="detalle-encabezado">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Fecha" value={formatFecha(ev.fecha)} />
            <Campo label="Médico" value={ev.medico_nombre} />
            <Campo label="Motivo de consulta" value={ev.motivo_consulta} />
            <Campo label="Padecimiento actual" value={ev.padecimiento_actual} />
          </div>
        </SeccionDetalle>

        {/* Diagnósticos */}
        {dxList.length > 0 && (
          <SeccionDetalle icon={Stethoscope} titulo="Diagnósticos" testid="detalle-diagnosticos">
            <div className="space-y-2">
              {dxList.map((dx, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <Badge className="bg-teal-100 text-teal-800">{dx.codigo_cie10 || 'CIE—'}</Badge>
                  <div>
                    <span className="text-slate-800">{dx.descripcion || dx.nombre || 'Sin descripción'}</span>
                    {dx.ojo && <span className="ml-2 text-xs text-slate-500">({ojoLabel(dx.ojo)})</span>}
                  </div>
                </div>
              ))}
            </div>
          </SeccionDetalle>
        )}

        {/* Examen resumido */}
        <SeccionDetalle icon={Activity} titulo="Examen oftalmológico" testid="detalle-examen">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="AV s/c OD" value={examen.avsc_od} />
            <Campo label="AV s/c OS" value={examen.avsc_os} />
            <Campo label="AV c/c OD" value={examen.avcc_od} />
            <Campo label="AV c/c OS" value={examen.avcc_os} />
            <Campo label="PIO OD" value={examen.pio_od} />
            <Campo label="PIO OS" value={examen.pio_os} />
            <Campo label="Segmento anterior" value={examen.segmento_anterior} />
            <Campo label="Segmento posterior" value={examen.segmento_posterior} />
            <Campo label="Motilidad ocular" value={examen.motilidad_ocular} />
            <Campo label="Pupilas / reflejos" value={examen.pupilas_reflejos} />
          </div>
        </SeccionDetalle>

        {/* Recetas de anteojos */}
        {anteojosLista.length > 0 && (
          <SeccionDetalle icon={Glasses} titulo={`Recetas de anteojos (${anteojosLista.length})`} testid="detalle-anteojos">
            <div className="space-y-2">
              {anteojosLista.map((r, i) => <RecetaAnteojos key={r.id || i} receta={r} />)}
            </div>
          </SeccionDetalle>
        )}

        {/* Recetas de lentes de contacto */}
        {lentesLista.length > 0 && (
          <SeccionDetalle icon={Eye} titulo={`Recetas de lentes de contacto (${lentesLista.length})`} testid="detalle-lentes">
            <div className="space-y-2">
              {lentesLista.map((r, i) => <RecetaLentes key={r.id || i} receta={r} />)}
            </div>
          </SeccionDetalle>
        )}

        {/* Medicamentos */}
        {medicamentos.length > 0 && (
          <SeccionDetalle icon={Pill} titulo="Medicamentos recetados" testid="detalle-medicamentos">
            <div className="space-y-2">
              {medicamentos.map((m, i) => (
                <div key={i} className="rounded-md bg-slate-50 p-2 text-sm">
                  <span className="font-semibold text-slate-800">{m.medicamento || 'Medicamento'}</span>
                  {m.presentacion && <span className="text-slate-600"> · {m.presentacion}</span>}
                  <div className="text-xs text-slate-500">
                    {[m.dosis, m.frecuencia, m.duracion, m.via].filter(Boolean).join(' · ')}
                  </div>
                  {m.indicaciones && <p className="text-xs italic text-slate-500">{m.indicaciones}</p>}
                </div>
              ))}
            </div>
          </SeccionDetalle>
        )}

        {/* Plan y recomendaciones */}
        {(ev.plan || recomendaciones.recomendaciones_generales) && (
          <SeccionDetalle icon={ClipboardList} titulo="Plan y recomendaciones" testid="detalle-plan">
            <div className="space-y-2">
              <Campo label="Plan" value={ev.plan} />
              <Campo label="Recomendaciones generales" value={recomendaciones.recomendaciones_generales} />
            </div>
          </SeccionDetalle>
        )}

        <div className="flex justify-end">
          <Button
            variant="outline"
            onClick={() => descargarPDF(ev)}
            disabled={pdfLoadingId === ev.id}
            className="gap-2"
            data-testid="detalle-descargar-pdf"
          >
            <Download className="h-4 w-4" />
            {pdfLoadingId === ev.id ? 'Generando PDF…' : 'Descargar PDF completo'}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[740px] max-h-[88vh] overflow-y-auto" data-testid="evaluaciones-paciente-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[#0F6E56]">
            <ClipboardList className="h-5 w-5" />
            {selectedNota ? 'Nota de cirugía' : selected ? 'Detalle de evaluación' : 'Historial clínico'}
          </DialogTitle>
          <DialogDescription>
            {nombrePaciente}
            {patient?.record_number ? ` · Exp. ${patient.record_number}` : ''}
            {!selected && !selectedNota && !loading && (evaluaciones.length > 0 || notas.length > 0) ? ` · ${notas.length} cirugía(s), ${evaluaciones.length} evaluación(es)` : ''}
          </DialogDescription>
        </DialogHeader>

        {(selected || selectedNota) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setSelected(null); setSelectedNota(null); }}
            className="mb-1 w-fit gap-1 text-slate-600 hover:bg-slate-100"
            data-testid="volver-lista-evaluaciones"
          >
            <ChevronLeft className="h-4 w-4" />
            Volver al historial
          </Button>
        )}

        {selectedNota ? (
          <NotaCirugia
            note={selectedNota}
            isSuperadmin={user?.role === 'superadmin'}
            onUpdated={(data) => {
              setSelectedNota(data);
              setNotas((prev) => prev.map((n) => (n.id === data.id ? data : n)));
            }}
          />
        ) : selected ? renderDetalle() : renderLista()}
      </DialogContent>
    </Dialog>
  );
};

export default EvaluacionesPacienteDialog;
