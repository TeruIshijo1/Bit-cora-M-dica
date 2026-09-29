import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { FiLogOut, FiUsers, FiClipboard, FiActivity, FiSettings, FiUser, FiEdit3, FiMenu, FiX, FiFileText, FiCalendar, FiSearch } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';
import PatientSearchModal from './PatientSearchModal';
import { useAuth } from '../context/AuthContext';
import { canAccessPath, modules } from '../utils/permissions';


export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, hasModule, logout } = useAuth();
  const rol = user?.rol;
  const canSearch = hasModule('ehr');
  
  // Atajo global Ctrl+K o Cmd+K para abrir buscador
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (canSearch && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [canSearch]);
  
  let medico = null;
  if (rol === 'medico') {
    try {
      medico = JSON.parse(localStorage.getItem('medico'));
    } catch(e){}
  }

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const navIcons = { agenda: <FiCalendar />, camas: <MdLocalHospital />, ehr: <FiFileText />, captura_enfermeria: <FiClipboard />, captura_medica: <FiEdit3 /> };
  const navLabels = { agenda: 'Agenda', camas: 'Camas y pacientes', ehr: 'Expedientes', captura_enfermeria: 'Registro de enfermería', captura_medica: 'Firmas pendientes' };
  const menuItems = [
    { path: rol === 'rh' ? '/rh' : '/admin', label: rol === 'rh' ? 'Personal' : 'Inicio', icon: <FiActivity /> },
    ...modules.filter(item => !item.tab).map(item => ({ path: item.path, label: navLabels[item.id] || item.label, icon: navIcons[item.id] || <FiFileText /> }))
  ];
  const visibleItems = menuItems.filter(item => canAccessPath(user, item.path));

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top Header - Minimalist Style */}
      <header className="he-global-header text-white shadow-sm z-20 flex flex-col relative border-b border-slate-700/50">
        <div className="flex justify-between items-center px-4 md:px-6 h-14 md:h-16">
          <div className="flex items-center gap-3">
            <button 
              className="md:hidden p-1.5 -ml-1.5 text-slate-300 hover:text-white rounded-md transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <FiX className="text-2xl" /> : <FiMenu className="text-2xl" />}
            </button>
              <div className="flex items-center justify-center h-9 bg-white rounded-xl shadow-md px-2.5 border border-white/60">
              <img src="/logo.png?v=6" alt="Hospital Escandón" className="h-full w-auto object-contain" />
            </div>
            <div className="flex flex-col leading-none ml-1">
              <span className="font-black text-[17px] tracking-tight hidden sm:block">Bitácora HE</span>
              <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-300 hidden sm:block">Sistema clínico</span>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex flex-1 justify-center mx-4">
            <ul className="flex flex-row gap-1">
              {visibleItems.map(item => (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all font-semibold text-[13px] border border-transparent ${
                      location.pathname === item.path 
                      ? 'he-nav-active text-white shadow-sm' 
                      : 'text-slate-300 hover:text-white hover:bg-white/10 hover:border-white/10'
                    }`}
                  >
                    <span className="text-base opacity-80">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          
          <div className="flex items-center gap-3">
            {/* Botón Buscador Universal de Pacientes */}
            {canSearch && <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg text-xs font-medium border border-white/10 transition-all group"
              title="Buscar paciente por nombre, folio o CURP"
            >
              <FiSearch className="text-sm opacity-70 group-hover:opacity-100 transition-opacity" />
              <span className="hidden sm:inline">Buscar</span>
              <kbd className="hidden md:inline-flex items-center justify-center bg-white/10 text-[10px] text-slate-300 px-1.5 rounded h-4 font-mono ml-1">
                Ctrl K
              </kbd>
            </button>}

            <div className="h-5 w-px bg-white/20 hidden md:block mx-1"></div>

            {/* User Area */}
            {medico ? (
              <div className="flex items-center gap-2">
                {medico.foto_url ? (
                  <img src={`${medico.foto_url}`} alt="Perfil" className="w-8 h-8 rounded-full object-cover border border-white/20" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-white/10 text-slate-200 flex items-center justify-center border border-white/20">
                    <FiUser className="text-sm" />
                  </div>
                )}
                <div className="hidden sm:flex flex-col leading-tight max-w-[120px] md:max-w-[150px]">
                  <span className="text-xs font-medium text-white truncate">{medico.nombre_completo}</span>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider truncate">{rol}</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white/10 text-slate-200 border border-white/20">
                  <FiUser className="text-sm" />
                </div>
                <div className="hidden sm:flex flex-col leading-tight">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider">{rol}</span>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-1">
              <button 
                onClick={handleLogout}
                className="text-slate-400 hover:text-red-400 hover:bg-red-400/10 p-2 rounded-lg transition-colors flex items-center justify-center"
                title="Cerrar Sesión"
              >
                <FiLogOut className="text-lg" />
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        <nav className={`${mobileMenuOpen ? 'block' : 'hidden'} lg:hidden w-full z-50 bg-hes-blue-main border-t border-white/10 shadow-lg absolute top-full left-0`}>
          <ul className="flex flex-col p-2 gap-1">
            {visibleItems.map(item => (
              <li key={item.path} className="w-full">
                <Link
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all font-medium text-sm ${
                    location.pathname === item.path 
                    ? 'bg-white/10 text-white' 
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span className="text-lg opacity-80">{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      {/* Modal de Búsqueda Global de Pacientes */}
      {canSearch && <PatientSearchModal key={searchOpen ? 'open' : 'closed'} isOpen={searchOpen} onClose={() => setSearchOpen(false)} />}

      {/* Main Content Area */}
      <main className="page-content-scroll flex-1 flex flex-col justify-between">
        <div className="flex-1">
          <Outlet />
        </div>
        <footer className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-4 px-6 bg-transparent text-[11px] text-slate-400 font-mono select-none">
          <a
            href="https://github.com/TeruIshijo1"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Autor: Ing. Alberto García Mendoza. Abrir GitHub en una pestaña nueva"
            className="text-left transition-colors hover:text-hes-blue-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-hes-blue-main/40 focus-visible:ring-offset-2 rounded"
          >
            Autor: Ing. Alberto García Mendoza
          </a>
          <span className="ml-auto text-right">Uso interno · Hospital Escandón</span>
        </footer>
      </main>
    </div>
  );
}
