import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaUserMd, FaUserAlt } from 'react-icons/fa';
import { getApiUrl } from '../api';

const CamasDashboard = () => {
  const [camas, setCamas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  
  // Timeline Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCama, setSelectedCama] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // Limpieza Modal State
  const [modalLimpiezaOpen, setModalLimpiezaOpen] = useState(false);
  const [estadoLimpieza, setEstadoLimpieza] = useState("Disponible");
  const [notasLimpieza, setNotasLimpieza] = useState("");
  const [savingLimpieza, setSavingLimpieza] = useState(false);

  const currentUserRole = localStorage.getItem('rol');
  const isLimpiezaRole = currentUserRole === 'Mantenimiento/Limpieza' || currentUserRole === 'limpieza';
  const isEnfermeriaRole = currentUserRole === 'enfermeria';
  
  const navigate = useNavigate();

  useEffect(() => {
    fetchCamas();
    const interval = setInterval(() => {
      fetchCamas();
    }, 30000); // Actualizar cada 30 segundos
    return () => clearInterval(interval);
  }, []);

  const fetchCamas = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${getApiUrl()}/camas`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Error al cargar camas');
      const data = await response.json();
      setCamas(Array.isArray(data) ? data : []);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleCamaClick = async (cama) => {
    if (isLimpiezaRole) {
      setSelectedCama(cama);
      setEstadoLimpieza(cama.estado_limpieza || "Disponible");
      setNotasLimpieza(cama.notas_limpieza || "");
      setModalLimpiezaOpen(true);
      return;
    }

    if (cama.PTNum) {
      setSelectedCama(cama);
      setModalOpen(true);
      setLoadingTimeline(true);
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${getApiUrl()}/camas/paciente/${cama.PTNum}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        setTimelineData(data);
      } catch (e) {
        console.error("Error fetching timeline:", e);
      }
      setLoadingTimeline(false);
    } else {
      proceedToCaptura(cama);
    }
  };

  const handleGuardarLimpieza = async () => {
    if ((estadoLimpieza === "En mantenimiento" || estadoLimpieza === "Fuera de servicio") && !notasLimpieza.trim()) {
      alert(`Debe escribir un motivo si el estado es '${estadoLimpieza}'`);
      return;
    }
    
    setSavingLimpieza(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${getApiUrl()}/camas/${selectedCama.RoomName}/limpieza`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          estado_limpieza: estadoLimpieza,
          notas_limpieza: notasLimpieza
        })
      });
      if (res.ok) {
        setModalLimpiezaOpen(false);
        fetchCamas(); // refrescar
      } else {
        alert("Error al actualizar estado");
      }
    } catch (e) {
      console.error(e);
      alert("Error de red");
    }
    setSavingLimpieza(false);
  };

  const proceedToCaptura = (cama) => {
    navigate('/captura', {
      state: {
        habitacion: cama.RoomName || cama.RoomCode,
        pacienteNombre: cama.PatientName || '',
        ptNum: cama.PTNum || '',
        medicoTratante: cama.DoctorName || '',
      }
    });
  };

  // Función para agrupar camas por piso o área
  const groupCamas = (camasList) => {
    const groups = {
      'PPB (Planta Baja)': [],
      'PPA (Planta Alta)': [],
      'Urgencias': [],
      'Quirófanos': [],
      'Corta Estancia': [],
      'Otras Áreas': [],
      'Camas Virtuales': []
    };

    camasList.forEach(cama => {
      const name = (cama.RoomName || '').toUpperCase();
      const code = (cama.RoomCode || '').toUpperCase();
      
      if (name.includes('VIRTUAL')) {
        groups['Camas Virtuales'].push(cama);
      } else if (name.includes('URGENCIA') || code.includes('URG')) {
        groups['Urgencias'].push(cama);
      } else if (name.includes('QUIR')) {
        groups['Quirófanos'].push(cama);
      } else if (name.includes('CORTA ESTANCIA') || name.includes('CE')) {
        groups['Corta Estancia'].push(cama);
      } else if (name.includes(' 10') || code.includes('PB') || code.includes('10')) {
        groups['PPB (Planta Baja)'].push(cama);
      } else if (name.includes(' 20') || code.includes('PA') || code.includes('20')) {
        groups['PPA (Planta Alta)'].push(cama);
      } else {
        groups['Otras Áreas'].push(cama);
      }
    });

    // Ordenar camas dentro de cada grupo por nombre
    for (const key in groups) {
      groups[key].sort((a, b) => (a.RoomName || '').localeCompare(b.RoomName || ''));
    }

    return groups;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[500px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const filteredCamas = camas.filter(c => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (c.RoomName && c.RoomName.toLowerCase().includes(term)) ||
      (c.RoomCode && c.RoomCode.toLowerCase().includes(term)) ||
      (c.PatientName && c.PatientName.toLowerCase().includes(term)) ||
      (c.PTNum && c.PTNum.toLowerCase().includes(term))
    );
  });

  const groupedCamas = groupCamas(filteredCamas);
  const totalCamas = camas.length;
  const libres = camas.filter(c => c.Estatus === 'Libre').length;
  const ocupadas = camas.filter(c => c.Estatus === 'Ocupada').length;
  const inhabilitadas = camas.filter(c => c.Estatus === 'Inhabilitada').length;

  const camasProblematicas = camas.filter(c => {
    if (!c.estado_limpieza) return false;
    const estado = c.estado_limpieza.toLowerCase();
    return c.Estatus === 'Ocupada' && estado !== 'disponible' && estado !== 'limpia';
  });

  return (
    <div className="w-full p-6 pb-10 bg-slate-50">
      {/* Header Metrics */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Ocupación de Camas</h1>
          <p className="text-sm text-gray-500 mt-1">
            Fuente: V_MRPT &amp; PC &nbsp;•&nbsp;
            <span className="text-green-600 font-medium">● Auto-refresh cada 30s</span>
            {lastUpdate && (
              <span className="ml-2 text-gray-400">
                · Actualizado: {lastUpdate.toLocaleTimeString('es-MX')}
              </span>
            )}
          </p>
        </div>
        
        <div className="flex flex-col md:flex-row items-end gap-4">
          <div className="relative w-full md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Buscar cama, paciente..."
              className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-full leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm transition-shadow shadow-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex gap-3 font-medium">
          <div className="bg-gray-200 text-gray-700 px-4 py-2 rounded-full shadow-sm">
            Total: {totalCamas}
          </div>
          <div className="bg-green-100 text-green-800 px-4 py-2 rounded-full shadow-sm">
            Libres: {libres}
          </div>
          <div className="bg-red-100 text-red-800 px-4 py-2 rounded-full shadow-sm">
            Ocupadas: {ocupadas}
          </div>
          {inhabilitadas > 0 && (
            <div className="bg-gray-300 text-gray-800 px-4 py-2 rounded-full shadow-sm">
              Inhabilitadas: {inhabilitadas}
            </div>
          )}
          </div>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 shadow-sm">
          {error}
        </div>
      )}

      {camasProblematicas.length > 0 && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-800 p-4 mb-6 shadow-sm flex items-center justify-between rounded-r">
          <div className="flex items-center">
            <span className="text-2xl mr-3">⚠️</span>
            <div>
              <p className="font-bold">Notificación de Mantenimiento / Limpieza</p>
              <p className="text-sm">Hay {camasProblematicas.length} cama(s) con paciente registrado cuyo estado de limpieza NO es "Disponible".</p>
            </div>
          </div>
        </div>
      )}

      {/* Bed Groups */}
      {Object.entries(groupedCamas).map(([groupName, groupCamasList]) => {
        if (groupCamasList.length === 0) return null;
        
        return (
          <div key={groupName} className="mb-10">
            <h2 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2 border-gray-200">
              {groupName} ({groupCamasList.length})
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {groupCamasList.map((cama, index) => {
                const isLibre = cama.Estatus === 'Libre';
                const isOcupada = cama.Estatus === 'Ocupada';
                const isInhabilitada = cama.Estatus === 'Inhabilitada';
                
                let borderColor = 'border-green-500';
                let statusBg = 'bg-green-100 text-green-800';
                
                if (isOcupada) {
                  borderColor = 'border-red-500';
                  statusBg = 'bg-red-100 text-red-800';
                } else if (isInhabilitada) {
                  borderColor = 'border-gray-500';
                  statusBg = 'bg-gray-200 text-gray-700';
                }

                const isCleanState = cama.estado_limpieza === 'Disponible' || cama.estado_limpieza?.toLowerCase() === 'limpia';
                
                let showBadge = false;
                let cardBg = 'bg-white';
                let cleaningBadgeColor = '';

                if (cama.estado_limpieza) {
                  const estadoLower = cama.estado_limpieza.toLowerCase();
                  if (estadoLower === 'sucia') {
                    cardBg = 'bg-orange-50';
                    cleaningBadgeColor = 'bg-orange-200 text-orange-800 border-orange-300';
                  } else if (estadoLower === 'en mantenimiento') {
                    cardBg = 'bg-yellow-50';
                    cleaningBadgeColor = 'bg-yellow-200 text-yellow-800 border-yellow-300';
                  } else if (estadoLower === 'fuera de servicio') {
                    cardBg = 'bg-gray-100 opacity-80';
                    cleaningBadgeColor = 'bg-gray-300 text-gray-800 border-gray-400';
                  } else if (estadoLower === 'disponible' || estadoLower === 'limpia') {
                    cleaningBadgeColor = 'bg-green-50 text-green-700 border-green-200';
                  } else {
                    cardBg = 'bg-yellow-50/50';
                    cleaningBadgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-200';
                  }

                  if (isCleanState) {
                    // Solo Enfermeria y Limpieza ven "Limpia/Disponible" si la cama NO está ocupada
                    if (!isOcupada && (isLimpiezaRole || isEnfermeriaRole)) {
                      showBadge = true;
                    }
                  } else {
                    // Todos ven otros estados (Sucia, Mantenimiento, etc.)
                    showBadge = true;
                  }
                }

                return (
                  <div 
                    key={index} 
                    onClick={() => handleCamaClick(cama)}
                    className={`${cardBg} rounded-lg shadow-sm border-t-4 ${borderColor} p-4 hover:shadow-md transition-all cursor-pointer flex flex-col h-full relative`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="text-sm font-bold text-gray-800 truncate pr-2">
                        {cama.RoomName}
                      </h3>
                      <div className="flex flex-col items-end gap-1">
                        <span className={`text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider ${statusBg}`}>
                          {cama.Estatus}
                        </span>
                        {showBadge && (
                           <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase border shadow-sm text-center ${cleaningBadgeColor}`}>
                             {cama.estado_limpieza}
                           </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex-grow flex flex-col justify-center">
                      {isOcupada ? (
                        <div className="space-y-2">
                          <div className="flex items-start gap-2 text-sm text-gray-800 font-semibold">
                            <FaUserAlt className="mt-1 flex-shrink-0 text-indigo-900" />
                            <span className="leading-tight">
                              {isLimpiezaRole ? "*** Paciente Oculto ***" : cama.PatientName}
                            </span>
                          </div>
                          {cama.DoctorName && !isLimpiezaRole && (
                            <div className="flex items-start gap-2 text-xs text-blue-600 font-medium">
                              <FaUserMd className="mt-0.5 flex-shrink-0" />
                              <span className="leading-tight">{cama.DoctorName}</span>
                            </div>
                          )}
                        </div>
                      ) : isInhabilitada ? (
                        <div className="flex items-center gap-2 text-sm text-gray-500 italic">
                          <span>⚠️ Cama no disponible</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
                          <span className="text-lg">✓</span> 
                          <span>Disponible para ingreso</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
      {modalOpen && selectedCama && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 bg-blue-800 text-white flex justify-between items-center">
              <h2 className="text-xl font-bold">{selectedCama.PatientName}</h2>
              <button onClick={() => setModalOpen(false)} className="text-white hover:text-blue-200 font-bold text-xl">&times;</button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1">
              {loadingTimeline ? (
                <div className="flex justify-center p-8"><div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full"></div></div>
              ) : (
                <div className="space-y-6">
                  {/* Ficha Rapida */}
                  {timelineData?.demographics && (
                    <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
                      <h3 className="font-semibold text-blue-900 mb-2">Ficha Rápida</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <p><span className="text-slate-500">Edad/Nac.:</span> {timelineData.demographics.BirthDate ? new Date(timelineData.demographics.BirthDate).toLocaleDateString() : 'N/D'}</p>
                        <p><span className="text-slate-500">Sexo:</span> {timelineData.demographics.Gender || 'N/D'}</p>
                        <p><span className="text-slate-500">Sangre:</span> <span className="font-bold text-red-600">{timelineData.demographics.BloodType || 'N/D'}</span></p>
                        <p><span className="text-slate-500">Religión:</span> {timelineData.demographics.Religion || 'N/D'}</p>
                      </div>
                    </div>
                  )}

                  {/* Timeline */}
                  {timelineData?.timeline && (
                    <div>
                      <h3 className="font-semibold text-slate-800 mb-4">Línea de Tiempo (Journey)</h3>
                      <div className="space-y-4 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-300 before:to-transparent">
                        {timelineData.timeline.map((item, idx) => (
                          <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                            <div className="flex items-center justify-center w-5 h-5 rounded-full border border-white bg-blue-500 text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10"></div>
                            <div className="w-[calc(100%-2.5rem)] md:w-[calc(50%-1.25rem)] bg-white p-3 rounded border border-slate-200 shadow-sm">
                              <div className="flex justify-between mb-1">
                                <div className="font-bold text-slate-700 text-sm">{item.RoomName}</div>
                              </div>
                              <div className="text-xs text-slate-500">
                                Entrada: {new Date(item.EntryDate).toLocaleString()}<br/>
                                Salida: {item.ExitDate ? new Date(item.ExitDate).toLocaleString() : 'Actual'}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 border-t bg-slate-50 flex justify-end gap-3">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg">Cerrar</button>
              <button onClick={() => proceedToCaptura(selectedCama)} className="px-4 py-2 bg-blue-600 text-white font-medium hover:bg-blue-700 rounded-lg shadow-sm">
                Continuar a Captura
              </button>
            </div>
          </div>
        </div>
      )}

      {modalLimpiezaOpen && selectedCama && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col">
            <div className="p-4 bg-yellow-500 text-white flex justify-between items-center">
              <h2 className="text-xl font-bold">Estado Limpieza: {selectedCama.RoomName}</h2>
              <button onClick={() => setModalLimpiezaOpen(false)} className="text-white hover:text-yellow-100 font-bold text-xl">&times;</button>
            </div>
            
            <div className="p-6">
              <label className="block text-sm font-bold text-gray-700 mb-2">Estado:</label>
              <select 
                value={estadoLimpieza}
                onChange={e => setEstadoLimpieza(e.target.value)}
                className="w-full border border-gray-300 rounded-lg p-3 mb-4 bg-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                <option value="Disponible">Disponible</option>
                <option value="Sucia">Sucia</option>
                <option value="En proceso de limpieza">En proceso de limpieza</option>
                <option value="En mantenimiento">En mantenimiento</option>
                <option value="Fuera de servicio">Fuera de servicio</option>
              </select>

              { (estadoLimpieza === 'En mantenimiento' || estadoLimpieza === 'Fuera de servicio') && (
                <div className="mb-4">
                  <label className="block text-sm font-bold text-gray-700 mb-2">Motivo ({estadoLimpieza}):</label>
                  <textarea 
                    value={notasLimpieza}
                    onChange={e => setNotasLimpieza(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-yellow-500"
                    rows="3"
                    placeholder="Escriba el motivo aquí..."
                  ></textarea>
                </div>
              )}
            </div>

            <div className="p-4 border-t bg-slate-50 flex justify-end gap-3">
              <button onClick={() => setModalLimpiezaOpen(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-lg">Cancelar</button>
              <button onClick={handleGuardarLimpieza} disabled={savingLimpieza} className="px-4 py-2 bg-yellow-600 text-white font-medium hover:bg-yellow-700 rounded-lg shadow-sm disabled:opacity-50">
                {savingLimpieza ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CamasDashboard;
