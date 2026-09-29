import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePublicDocumentVerificationQuery } from '../hooks/useQueries';
import { 
  FiShield, FiFileText, FiUser, FiCheckCircle, FiExternalLink, 
  FiAlertTriangle, FiXCircle, FiClock, FiUsers, FiGlobe 
} from 'react-icons/fi';
import { FaFacebookF, FaInstagram, FaTiktok, FaYoutube } from 'react-icons/fa';
import { FaXTwitter } from 'react-icons/fa6';

export default function VerificarDocumento() {
  const [searchParams] = useSearchParams();
  const docId = searchParams.get('id') || searchParams.get('doc_uuid') || '';
  const verification = usePublicDocumentVerificationQuery(docId);
  const verifData = verification.data;
  const loading = Boolean(docId && verification.isPending);
  const isError = !docId || verification.isError;

  const effectiveDocId = verifData?.doc_uuid || verifData?.id || docId;
  const pdfUrl = effectiveDocId
    ? `/api/verificar/pdf/documento?id=${encodeURIComponent(effectiveDocId)}`
    : null;

  const estado = verifData?.estado || 'SIN_FIRMA';
  const isValido = verifData?.valido === true;
  const isVerifiedCopy = estado === 'COPIA_INTEGRA_VERIFICADA';

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center p-4 sm:p-6">
      <div className="w-full max-w-lg space-y-4">
        
        {/* Header Institucional con Logo Oficial */}
        <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-5 text-center shadow-xl">
          <div className="flex items-center justify-center mb-2">
            <div className="bg-white p-2 rounded-xl shadow-md inline-block">
              <img src="/logo.png?v=6" alt="Hospital Escandón" className="h-10 w-auto object-contain" />
            </div>
          </div>
          <p className="text-xs text-blue-400 font-medium uppercase tracking-wider">
            Fundación María Ana Mier de Escandón, I.A.P.
          </p>
          <div className="block mt-2">
            <span className="inline-block px-2.5 py-0.5 bg-blue-950/60 border border-blue-500/30 text-blue-300 text-[10px] font-semibold rounded-full">
              NOM-004-SSA3-2012 • NOM-024-SSA3-2012
            </span>
          </div>
        </div>

        {/* Dynamic Badge de Verificación Criptográfica */}
        {loading ? (
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 text-center animate-pulse">
            <div className="text-sm font-bold text-slate-400">Verificando firma criptográfica en ECE...</div>
          </div>
        ) : isError ? (
          <div className="bg-rose-950/60 border-2 border-rose-500/70 rounded-2xl p-5 text-center">
            <FiAlertTriangle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
            <h2 className="font-bold text-rose-300">QR no disponible</h2>
            <p className="text-xs text-rose-200/90 mt-1">No se encontró un documento verificable para este código.</p>
          </div>
        ) : isValido ? (
          <div className="bg-emerald-950/50 border-2 border-emerald-500/50 rounded-2xl p-5 text-center shadow-lg shadow-emerald-950/30 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-emerald-500 text-slate-950 rounded-full mb-3 shadow-md">
              <FiCheckCircle className="w-7 h-7 stroke-[2.5]" />
            </div>
            <h2 className="text-base font-extrabold text-emerald-400 uppercase tracking-wide">
              {isVerifiedCopy ? 'Copia del expediente íntegra' : 'Documento firmado y verificado'}
            </h2>
            <p className="text-xs text-emerald-200/90 mt-1.5 leading-relaxed">
              {verifData?.mensaje}
            </p>
          </div>
        ) : estado === 'REVOCADA' ? (
          <div className="bg-amber-950/50 border-2 border-amber-500/60 rounded-2xl p-5 text-center shadow-lg shadow-amber-950/30 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-amber-500 text-slate-950 rounded-full mb-3 shadow-md">
              <FiAlertTriangle className="w-7 h-7 stroke-[2.5]" />
            </div>
            <h2 className="text-base font-extrabold text-amber-400 uppercase tracking-wide">
              Firma Revocada / No Vigente
            </h2>
            <p className="text-xs text-amber-200/90 mt-1.5 leading-relaxed">
              {verifData?.mensaje || 'Este documento fue formalmente sustituido o re-firmado en el expediente clínico.'}
            </p>
          </div>
        ) : estado === 'INTEGRIDAD_COMPROMETIDA' ? (
          <div className="bg-rose-950/60 border-2 border-rose-500/70 rounded-2xl p-5 text-center shadow-lg shadow-rose-950/40 animate-fadeIn">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-rose-500 text-white rounded-full mb-3 shadow-md">
              <FiXCircle className="w-7 h-7 stroke-[2.5]" />
            </div>
            <h2 className="text-base font-extrabold text-rose-400 uppercase tracking-wide">
              ¡Alerta de Seguridad! Integridad Comprometida
            </h2>
            <p className="text-xs text-rose-200 mt-1.5 leading-relaxed">
              {verifData?.mensaje || 'El contenido no coincide con el registro resguardado.'}
            </p>
          </div>
        ) : estado === 'RECURSO_NO_DISPONIBLE' ? (
          <div className="bg-slate-800/80 border-2 border-slate-600 rounded-2xl p-5 text-center shadow-lg">
            <FiAlertTriangle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <h2 className="font-bold text-slate-200">Copia no disponible</h2>
            <p className="text-xs text-slate-400 mt-1">{verifData?.mensaje}</p>
          </div>
        ) : (
          <div className="bg-slate-800/80 border-2 border-slate-600 rounded-2xl p-5 text-center shadow-lg animate-fadeIn">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-slate-700 text-slate-300 rounded-full mb-3 shadow-md">
              <FiClock className="w-7 h-7 stroke-[2.5]" />
            </div>
            <h2 className="text-base font-extrabold text-slate-300 uppercase tracking-wide">
              Documento Pendiente de Firma
            </h2>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Este formato aún no cuenta con firma electrónica o biométrica asentada en el Expediente Clínico Electrónico.
            </p>
          </div>
        )}

        {verifData && <>
        {/* 1. Datos del Paciente */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
            <FiUser className="w-4 h-4" /> Datos de Identificación del Paciente
          </div>
          <div>
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Nombre Completo</div>
            <div className="text-sm font-bold text-white mt-0.5">{verifData?.paciente || 'Nombre no disponible'}</div>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Expediente / Folio</div>
              <div className="text-sm font-bold text-blue-400 mt-0.5">{verifData?.folio || 'No disponible'}</div>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Edad Registrada</div>
              <div className="text-sm font-bold text-white mt-0.5">{verifData?.edad || 'Consultar en ECE'}</div>
            </div>
          </div>
        </div>

        {/* 2. Formato Clínico */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
            <FiFileText className="w-4 h-4" /> Acto Médico / Consentimiento
          </div>
          <div>
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Formato Oficial</div>
            <div className="text-sm font-bold text-white mt-0.5">{verifData?.formato || 'Documento Clínico Oficial'}</div>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Código Normado</div>
              <div className="inline-block text-xs font-mono font-bold bg-blue-950/80 text-blue-300 border border-blue-800/50 px-2 py-0.5 rounded mt-0.5">
                {verifData?.codigo || '—'}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Estado en ECE</div>
              <div className={`text-xs font-extrabold mt-1 ${
                isValido ? 'text-emerald-400' :
                estado === 'REVOCADA' ? 'text-amber-400' :
                estado === 'INTEGRIDAD_COMPROMETIDA' ? 'text-rose-400' : 'text-slate-400'
              }`}>
                {isVerifiedCopy ? '✓ COPIA ÍNTEGRA VERIFICADA' :
                 isValido ? '✓ AUTORIZADO Y FIRMADO' :
                 estado === 'REVOCADA' ? '⚠ FIRMA REVOCADA' :
                 estado === 'INTEGRIDAD_COMPROMETIDA' ? '✕ ALTERACIÓN DETECTADA' :
                 estado === 'RECURSO_NO_DISPONIBLE' ? 'COPIA NO DISPONIBLE' : 'PENDIENTE DE FIRMA'}
              </div>
            </div>
          </div>
        </div>

        {verifData?.codigo === 'HE-DIRMED-EXPEDIENTE-COMPLETO' && (
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
              <FiFileText className="w-4 h-4" /> Integridad de la copia institucional
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Fecha de generación</div>
              <div className="text-sm font-bold text-white mt-0.5">{verifData.fecha_generacion || '—'}</div>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Huella SHA-256 del PDF resguardado</div>
              <div className="font-mono text-[10px] text-cyan-300 bg-slate-950 p-2 rounded-lg border border-slate-800 break-all mt-1">
                {verifData.hash_sha256 || '—'}
              </div>
            </div>
            <p className="text-xs text-slate-300">Este cotejo no constituye una firma FEA del expediente compilado. Las firmas de cada formato se conservan en el PDF.</p>
          </div>
        )}

        {/* 3. Firma Médica FEA de un formato individual */}
        {isValido && !isVerifiedCopy && verifData?.medico?.nombre && (
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
              <FiShield className="w-4 h-4" /> Atribución Criptográfica y Firma Médica FEA
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Médico Tratante / Firmante</div>
              <div className="text-sm font-bold text-white mt-0.5">{verifData.medico.nombre}</div>
            </div>
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Cédula Profesional</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">{verifData.medico.cedula || '—'}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Fecha y Hora de Firma</div>
                <div className="text-xs font-bold text-slate-200 mt-0.5">{verifData.medico.fecha || verifData.fecha_hora_firma || '—'}</div>
              </div>
            </div>
            <div className="pt-2">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Método de Autenticación</div>
              <div className="text-xs font-semibold text-teal-300 mt-0.5">
                ✓ Firma Electrónica Avanzada (FEA ECDSA P-256 / NOM-024-SSA3)
              </div>
            </div>
            {verifData.medico.hash_sha256 && (
              <div className="pt-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Huella Digital SHA-256</div>
                <div className="font-mono text-[10px] text-cyan-300 bg-slate-950 p-2 rounded-lg border border-slate-800 break-all mt-1">
                  {verifData.medico.hash_sha256}
                </div>
              </div>
            )}
            {verifData.medico.sello_digital && (
              <div className="pt-1">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Sello Digital FEA</div>
                <div className="font-mono text-[10px] text-emerald-400 bg-slate-950 p-2 rounded-lg border border-slate-800 break-all mt-1">
                  {verifData.medico.sello_digital}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 4. Firma Presencial: Tutor / Representante Legal / Paciente */}
        {verifData?.firmante?.nombre && (
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
              <FiUsers className="w-4 h-4" /> Firma Presencial: Tutor / Titular
            </div>
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Nombre del Firmante</div>
              <div className="text-sm font-bold text-white mt-0.5">{verifData.firmante.nombre}</div>
            </div>
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Parentesco / Rol</div>
                <div className="text-sm font-bold text-slate-200 mt-0.5">{verifData.firmante.parentesco || verifData.firmante.rol}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Fecha y Hora</div>
                <div className="text-xs font-bold text-slate-200 mt-0.5">{verifData.firmante.fecha || '—'}</div>
              </div>
            </div>
            <div className="pt-2">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Método de Autenticación</div>
              <div className="text-xs font-semibold text-teal-300 mt-0.5">
                ✓ Biometría Dactilar Presencial (DigitalPersona ANSI/NIST 378 / NOM-004-SSA3)
              </div>
            </div>
            {verifData.firmante.sello_digital && (
              <div className="pt-1">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Sello Biométrico</div>
                <div className="font-mono text-[10px] text-cyan-300 bg-slate-950 p-2 rounded-lg border border-slate-800 break-all mt-1">
                  {verifData.firmante.sello_digital}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 5. Testigos Presenciales */}
        {verifData?.testigos && verifData.testigos.length > 0 && (
          <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase tracking-wider pb-2 border-b border-slate-700/50">
              <FiUsers className="w-4 h-4" /> Testigos Presenciales ({verifData.testigos.length})
            </div>
            <div className="space-y-2">
              {verifData.testigos.map((t, idx) => (
                <div key={idx} className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-700/60 text-xs">
                  <div className="font-bold text-white uppercase">{t.nombre}</div>
                  <div className="text-slate-400 text-[11px] mt-0.5">
                    {t.parentesco} • {t.fecha}
                  </div>
                  {t.sello_digital && (
                    <div className="font-mono text-[9px] text-purple-300 bg-slate-950 p-1.5 rounded mt-1 break-all">
                      {t.sello_digital}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Botón Ver PDF */}
        {pdfUrl && estado !== 'RECURSO_NO_DISPONIBLE' && estado !== 'INTEGRIDAD_COMPROMETIDA' && <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 px-4 rounded-xl shadow-lg shadow-blue-600/20 transition-all text-sm"
        >
          <FiFileText className="w-4 h-4" /> Abrir Documento PDF Oficial <FiExternalLink className="w-4 h-4" />
        </a>}
        </>}

        {/* Redes Sociales y Canales Oficiales */}
        <div className="bg-slate-800/80 border border-slate-700/70 rounded-2xl p-4 text-center shadow-sm">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
            🌐 Redes y Canales Oficiales • Hospital Escandón
          </div>
          <div className="flex items-center justify-center gap-2.5 flex-wrap">
            <a
              href="https://www.facebook.com/hospitalescandoniap"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-[#1877F2] text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-lg"
              title="Facebook"
            >
              <FaFacebookF />
            </a>
            <a
              href="https://www.instagram.com/hospital_escandon"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-gradient-to-tr from-yellow-500 via-pink-600 to-purple-700 text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-lg"
              title="Instagram"
            >
              <FaInstagram />
            </a>
            <a
              href="https://www.tiktok.com/@hospitalescandon"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-black text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-lg border border-slate-700"
              title="TikTok"
            >
              <FaTiktok />
            </a>
            <a
              href="https://x.com/hospescandon"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-[#0f1419] text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-base border border-slate-700"
              title="X (Twitter)"
            >
              <FaXTwitter />
            </a>
            <a
              href="https://www.youtube.com/@hospitalescandoniap"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-[#FF0000] text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-lg"
              title="YouTube"
            >
              <FaYoutube />
            </a>
            <a
              href="https://hospitalescandon.org/contacto.html"
              target="_blank"
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-md hover:opacity-90 transition-all text-lg"
              title="Sitio Web y Contacto"
            >
              <FiGlobe />
            </a>
          </div>
        </div>

        {/* Footer Institucional */}
        <div className="text-center text-[11px] text-slate-400 pt-3 pb-8 leading-relaxed">
          <strong className="text-slate-300">Hospital Escandón • Calidad Médica a tu Alcance</strong><br />
          Gral. Salvador Alvarado 7, Col. Escandón, Miguel Hidalgo, CDMX<br />
          Tels. 55-5516-8020 / 55-5515-8167 • Licencia Sanitaria No. 07 AM 09 011 163<br />
          <span className="text-[10px] text-slate-400 mt-1 block">
            Cotejo en tiempo real procesado por el Servidor Seguro de Bitácora HES.
          </span>
          <a
            href="https://github.com/TeruIshijo1"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-slate-400/80 font-mono mt-3 inline-block select-none hover:text-cyan-400 transition-colors opacity-70 hover:opacity-100"
          >
            Autor: Ing. Alberto García M.
          </a>
        </div>

      </div>
    </div>
  );
}
