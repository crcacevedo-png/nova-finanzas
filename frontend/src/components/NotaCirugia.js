// /app/frontend/src/components/NotaCirugia.js
// Editor de nota de cirugía con formato básico (negrita, cursiva, lista).
// La nota se bloquea al cerrarla o al cumplir 1 mes desde su creación.
// Una nota bloqueada es solo lectura, salvo para el superadmin.

import React, { useRef, useEffect, useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { Bold, Italic, List, Lock, Save, CheckCircle2, ShieldAlert, Printer } from 'lucide-react';
import { surgeryNoteApi } from '../services/api';

const formatFecha = (f) => {
  if (!f) return '';
  try {
    const s = String(f).split('T')[0];
    const [y, m, d] = s.split('-');
    return y && m && d ? `${d}/${m}/${y}` : String(f);
  } catch { return String(f); }
};

export const NotaCirugia = ({ note, isSuperadmin, onUpdated }) => {
  const editorRef = useRef(null);
  const [saving, setSaving] = useState(false);
  const [estado, setEstado] = useState(note);

  useEffect(() => {
    if (editorRef.current) editorRef.current.innerHTML = note.contenido || '';
    setEstado(note);
  }, [note]);

  const editable = estado.editable;

  const exec = (cmd) => {
    document.execCommand(cmd, false, null);
    editorRef.current?.focus();
  };

  const guardar = async () => {
    setSaving(true);
    try {
      const { data } = await surgeryNoteApi.update(estado.id, editorRef.current.innerHTML);
      setEstado(data);
      toast.success('Nota guardada');
      if (onUpdated) onUpdated(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar la nota');
    } finally {
      setSaving(false);
    }
  };

  const cerrar = async () => {
    setSaving(true);
    try {
      if (editable) {
        await surgeryNoteApi.update(estado.id, editorRef.current.innerHTML).catch(() => {});
      }
      const { data } = await surgeryNoteApi.close(estado.id);
      setEstado(data);
      toast.success('Nota cerrada y bloqueada');
      if (onUpdated) onUpdated(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo cerrar la nota');
    } finally {
      setSaving(false);
    }
  };

  const imprimir = () => {
    const contenido = editable ? (editorRef.current?.innerHTML || '') : (estado.contenido || '');
    const win = window.open('', '_blank', 'width=800,height=900');
    if (!win) { toast.error('Habilita las ventanas emergentes para imprimir'); return; }
    win.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Nota operatoria — ${estado.procedure || ''}</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, Helvetica, sans-serif; color: #1e293b; margin: 40px; line-height: 1.5; }
        h1 { font-size: 20px; margin: 0 0 4px; color: #0F6E56; }
        .meta { font-size: 13px; color: #475569; margin-bottom: 4px; }
        .divider { border: none; border-top: 2px solid #0F6E56; margin: 16px 0; }
        .label { font-weight: bold; }
        .content { font-size: 14px; margin-top: 10px; }
        .content ul { margin: 6px 0 6px 20px; }
        .firma { margin-top: 60px; font-size: 13px; }
        .firma-line { border-top: 1px solid #334155; width: 280px; padding-top: 4px; }
        @media print { body { margin: 20px; } }
      </style></head><body>
      <h1>Nota operatoria</h1>
      <div class="meta"><span class="label">Procedimiento:</span> ${estado.procedure || '—'}</div>
      <div class="meta"><span class="label">Paciente:</span> ${estado.patient_name || estado.patient || '—'}</div>
      <div class="meta"><span class="label">Fecha:</span> ${formatFecha(estado.fecha)} &nbsp;·&nbsp; <span class="label">Ojo:</span> ${estado.eye || '—'}</div>
      <div class="meta"><span class="label">Cirujano:</span> ${estado.surgeon || '—'} &nbsp;·&nbsp; <span class="label">Institución:</span> ${estado.institution || '—'}</div>
      <hr class="divider" />
      <div class="content">${contenido || '<em style="color:#94a3b8">(Sin contenido)</em>'}</div>
      <div class="firma"><div class="firma-line">${estado.surgeon || 'Firma del cirujano'}</div></div>
      </body></html>`);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 300);
  };

  const renderEstadoBadge = () => {
    if (estado.estado === 'cerrada') {
      return <Badge className="bg-red-100 text-red-700"><Lock className="mr-1 h-3 w-3" />Cerrada</Badge>;
    }
    if (estado.bloqueada) {
      return <Badge className="bg-amber-100 text-amber-700"><Lock className="mr-1 h-3 w-3" />Bloqueada por tiempo</Badge>;
    }
    return <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle2 className="mr-1 h-3 w-3" />Abierta</Badge>;
  };

  return (
    <div className="space-y-3" data-testid="nota-cirugia-editor">
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h4 className="text-sm font-semibold text-slate-800">{estado.procedure}</h4>
          <div className="flex items-center gap-2">
            {renderEstadoBadge()}
            <Button type="button" variant="outline" size="sm" onClick={imprimir} className="h-7 gap-1.5 text-xs" data-testid="nota-imprimir">
              <Printer className="h-3.5 w-3.5" />Imprimir
            </Button>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          {formatFecha(estado.fecha)} · {estado.eye} · {estado.surgeon} · {estado.institution}
        </p>
        {!estado.bloqueada && estado.estado !== 'cerrada' && (
          <p className="text-[11px] text-slate-400 mt-1">Se bloqueará automáticamente el {formatFecha(estado.bloqueo_fecha)}</p>
        )}
      </div>

      {/* Barra de formato */}
      {editable && (
        <div className="flex items-center gap-1 border-b border-slate-200 pb-2" data-testid="nota-toolbar">
          <Button type="button" variant="ghost" size="sm" onClick={() => exec('bold')} className="h-8 w-8 p-0" title="Negrita" data-testid="nota-bold"><Bold className="h-4 w-4" /></Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => exec('italic')} className="h-8 w-8 p-0" title="Cursiva" data-testid="nota-italic"><Italic className="h-4 w-4" /></Button>
          <Button type="button" variant="ghost" size="sm" onClick={() => exec('insertUnorderedList')} className="h-8 w-8 p-0" title="Lista" data-testid="nota-list"><List className="h-4 w-4" /></Button>
        </div>
      )}

      {/* Editor / solo lectura */}
      <div
        ref={editorRef}
        contentEditable={editable}
        suppressContentEditableWarning
        className={`min-h-[180px] rounded-lg border p-3 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#0F6E56]/40 ${editable ? 'bg-white border-slate-300' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
        data-testid="nota-contenido"
      />

      {!editable && (
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 p-2 text-xs text-amber-700" data-testid="nota-bloqueo-aviso">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          {estado.motivo_bloqueo || 'Nota bloqueada'}. Solo el superadmin puede editarla.
        </div>
      )}

      {editable && (
        <div className="flex justify-end gap-2">
          <Button onClick={guardar} disabled={saving} variant="outline" className="gap-2" data-testid="nota-guardar">
            <Save className="h-4 w-4" />{saving ? 'Guardando…' : 'Guardar'}
          </Button>
          {estado.estado !== 'cerrada' && (
            <Button onClick={cerrar} disabled={saving} className="gap-2 bg-[#0F6E56] hover:bg-[#0c5a46]" data-testid="nota-cerrar">
              <Lock className="h-4 w-4" />Cerrar nota
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default NotaCirugia;
