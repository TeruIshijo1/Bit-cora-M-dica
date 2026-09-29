import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheckCircle, FiFileText, FiRefreshCw } from 'react-icons/fi';
import Button from '../components/ui/Button';
import AlertBanner from '../components/ui/AlertBanner';
import AuthenticatedPdfButton from '../components/AuthenticatedPdfButton';
import SpecialSignerBiometricSignModal from '../features/biometrics/SpecialSignerBiometricSignModal';
import { useAreaSignaturesQuery, useAreaSignatureDocumentQuery } from '../hooks/useQueries';
import { useAuth } from '../context/AuthContext';

const dateLabel = value => value ? new Date(value).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) : 'Fecha no registrada';

export default function FirmasArea() {
  const { user } = useAuth();
  const client = useQueryClient();
  const [state, setState] = useState('pendientes');
  const [selected, setSelected] = useState(null);
  const [signing, setSigning] = useState(false);
  const queue = useAreaSignaturesQuery(state);
  const detail = useAreaSignatureDocumentQuery(selected);
  const data = detail.data;
  const rows = [...new Map((queue.data?.pages.flatMap(page => page.items) || []).map(item => [`${item.codigo_formato}:${item.pt_num}:${item.slot}`, item])).values()];
  const area = queue.data?.pages[0]?.area || 'Su área';
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['area-signatures'] }),
      client.invalidateQueries({ queryKey: ['area-signature-document'] }),
      client.invalidateQueries({ queryKey: ['document-signatures'] }),
    ]);
  };

  return <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="mb-1 text-sm text-slate-500">{area}</p><h1 className="text-2xl font-semibold text-slate-900">Firmas del área</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">Los pendientes se comparten con el personal autorizado. Una sola firma completa la tarea y registra quién la realizó.</p></div>
      <Button variant="outline" icon={<FiRefreshCw />} disabled={queue.isFetching} onClick={refresh}>Actualizar</Button>
    </header>
    {selected ? <>
      <Button variant="ghost" icon={<FiArrowLeft />} onClick={() => { setSelected(null); setSigning(false); }}>Volver a la bandeja</Button>
      {detail.isPending && <p role="status">Cargando documento…</p>}
      {detail.isError && <AlertBanner title="No se pudo comprobar el formato" message={detail.error?.response?.data?.detail || 'Reintente para ver su estado actual.'} onRetry={detail.refetch} />}
      {data && <section className="overflow-hidden rounded-xl border border-slate-300 bg-white">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5 sm:p-6">
          <div className="min-w-0 flex-1"><h2 className="text-lg font-semibold text-slate-900">{data.titulo}</h2>
            <p className="mt-2 text-sm text-slate-600">{data.paciente || selected.paciente} · PT-{data.pt_num} · Registro {data.slot}</p></div>
          <div className="flex flex-wrap gap-2">
            <AuthenticatedPdfButton endpoint={data.pdf_url} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Ver formato PDF</AuthenticatedPdfButton>
            {!data.firma && <Button disabled={detail.isError || detail.isFetching || !user?.id} onClick={() => setSigning(true)}>Firmar con mi huella</Button>}
          </div>
        </header>
        <div className="space-y-5 p-5 sm:p-6">
          {data.firma && <AlertBanner type="success" title="Firma del área completada" message={`${data.firma.firmante} · ${dateLabel(data.firma.fecha)}`} />}
          <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2">{data.campos.map((field, index) => <div key={`${field.label}:${index}`} className="min-w-0 border-b border-slate-200 pb-4"><dt className="text-xs text-slate-500">{field.label}</dt><dd className="mt-2 whitespace-pre-wrap break-words text-sm text-slate-900">{field.value}</dd></div>)}</dl>
          {!!data.historial.length && <details open={Boolean(data.firma)} className="rounded-lg border border-slate-200 p-4">
            <summary className="cursor-pointer text-sm font-semibold">Historial de firmas del área</summary>
            <ul className="mt-3 space-y-3">{data.historial.map(signature => <li key={signature.id} className="text-sm text-slate-700"><strong>{signature.firmante}</strong> · {dateLabel(signature.fecha)}<span className="ml-2 text-xs text-slate-500">{signature.vigente ? 'Vigente' : 'Versión anterior'}</span></li>)}</ul>
          </details>}
        </div>
      </section>}
      {signing && data && <SpecialSignerBiometricSignModal open patientId={data.pt_num} selfSignerId={user.id}
        documentInfo={{ codigo_formato: data.codigo_formato, slot: data.slot, rol_firmante: data.rol_firmante, areaLabel: data.area, title: data.titulo }}
        onClose={() => setSigning(false)} onSaved={refresh} />}
    </> : <>
      <div role="tablist" aria-label="Estado de firmas" className="flex gap-2 border-b border-slate-200 pb-3">
        {[['pendientes', 'Pendientes'], ['historial', 'Historial del área']].map(([key, label]) => <Button key={key} role="tab" aria-selected={state === key} variant={state === key ? 'primary' : 'ghost'} onClick={() => setState(key)}>{label}</Button>)}
      </div>
      {queue.isError && <AlertBanner title="No se pudo actualizar la bandeja" message={queue.error?.response?.data?.detail || 'La información no se ha podido confirmar. Reintente.'} onRetry={queue.refetch} />}
      {queue.isPending && <p role="status">Buscando formatos del área…</p>}
      {!queue.isPending && !queue.isError && !rows.length && <div className="rounded-xl border border-slate-300 bg-white p-10 text-center"><FiCheckCircle className="mx-auto mb-3 text-2xl text-slate-400" /><p className="text-slate-700">{queue.hasNextPage ? 'Sin resultados en este grupo de registros. Continúe la búsqueda.' : state === 'pendientes' ? 'No hay formatos pendientes en la bandeja.' : 'Aún no hay firmas registradas para el área.'}</p></div>}
      {!!rows.length && <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-300 bg-white">
        {rows.map(item => <li key={`${item.codigo_formato}:${item.pt_num}:${item.slot}`} className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="min-w-0 flex-1"><h2 className="font-semibold text-slate-900">{item.paciente}</h2><p className="mt-1 text-sm text-slate-700">{item.titulo}</p>
            <p className="mt-2 text-xs text-slate-500">PT-{item.pt_num} · Registro {item.slot} · Creado {dateLabel(item.creado)}</p>
            {(item.firma || item.historial[0]) && <p className="mt-2 text-sm text-emerald-800">{item.firma ? 'Firmado por' : 'Firma anterior de'} {(item.firma || item.historial[0]).firmante} · {dateLabel((item.firma || item.historial[0]).fecha)}</p>}</div>
          <Button variant="outline" icon={<FiFileText />} onClick={() => setSelected(item)}>Ver formato</Button>
        </li>)}
      </ul>}
      {queue.hasNextPage && <Button variant="outline" isLoading={queue.isFetchingNextPage} onClick={() => queue.fetchNextPage()}>Cargar más registros</Button>}
      <p className="text-xs text-slate-500">La bandeja se actualiza automáticamente cada 20 segundos.</p>
    </>}
  </main>;
}
