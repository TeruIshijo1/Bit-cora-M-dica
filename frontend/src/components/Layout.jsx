import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { FiLogOut, FiUsers, FiClipboard, FiActivity, FiSettings, FiUser, FiEdit3, FiMenu, FiX, FiFileText, FiCalendar, FiSearch } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';
import PatientSearchModal from './PatientSearchModal';

const serverIP = window.location.hostname;

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const rol = localStorage.getItem('rol');
  
  // Atajo global Ctrl+K o Cmd+K para abrir buscador
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
  
  let medico = null;
  if (rol === 'medico') {
    try {
      medico = JSON.parse(localStorage.getItem('medico'));
    } catch(e){}
  }

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rol');
    localStorage.removeItem('medico');
    localStorage.removeItem('permisos_modulos');
    localStorage.removeItem('formatos_permitidos');
    navigate('/login');
  };

  const menuItems = [
    { path: '/admin', label: 'Dashboard Global', icon: <FiActivity />, roles: ['admin', 'sistemas'] },
    { path: '/rh', label: 'Recursos Humanos', icon: <FiUsers />, roles: ['admin', 'rh', 'sistemas'] },
    { path: '/agenda', label: 'Mi Agenda', icon: <FiCalendar />, roles: ['admin', 'medico', 'enfermeria', 'sistemas', 'rh'] },
    { path: '/camas', label: 'Pacientes (Camas)', icon: <MdLocalHospital />, roles: ['admin', 'sistemas', 'enfermeria', 'medico', 'rh'] },
    { path: '/ehr', label: 'Expediente Clínico', icon: <FiFileText />, roles: ['admin', 'medico', 'enfermeria', 'sistemas'] },
    { path: '/captura', label: 'Captura (Enfermería)', icon: <FiClipboard />, roles: ['admin', 'enfermeria', 'sistemas'] },
    { path: '/firma-express', label: 'Captura / Firmas', icon: <FiEdit3 />, roles: ['admin', 'medico', 'ayudante'] }
  ];

  let permisosModulos = {};
  try {
    const permsStr = localStorage.getItem('permisos_modulos');
    if (permsStr) permisosModulos = JSON.parse(permsStr);
  } catch (e) {}

  const visibleItems = menuItems.filter(item => {
    // If the user has specific module permissions defined, override role default
    if (item.path === '/admin' && typeof permisosModulos.admin !== 'undefined') return permisosModulos.admin;
    if (item.path === '/rh' && typeof permisosModulos.rh !== 'undefined') return permisosModulos.rh;
    if (item.path === '/camas' && typeof permisosModulos.camas !== 'undefined') return permisosModulos.camas;
    if (item.path === '/agenda' && typeof permisosModulos.agenda !== 'undefined') return permisosModulos.agenda;
    if (item.path === '/ehr' && typeof permisosModulos.ehr !== 'undefined') return permisosModulos.ehr;
    if (item.path === '/captura' && typeof permisosModulos.captura_enfermeria !== 'undefined') return permisosModulos.captura_enfermeria;
    if (item.path === '/firma-express' && typeof permisosModulos.captura_medica !== 'undefined') return permisosModulos.captura_medica;
    
    // Otherwise fallback to role based logic
    return item.roles.includes(rol);
  });

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top Header - Minimalist Style */}
      <header className="bg-hes-blue-main text-white shadow-sm z-20 flex flex-col relative border-b border-slate-700/50">
        <div className="flex justify-between items-center px-4 md:px-6 h-14 md:h-16">
          <div className="flex items-center gap-3">
            <button 
              className="md:hidden p-1.5 -ml-1.5 text-slate-300 hover:text-white rounded-md transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <FiX className="text-2xl" /> : <FiMenu className="text-2xl" />}
            </button>
            <div className="flex items-center justify-center h-8 bg-white rounded-md shadow-sm px-2">
              <img src="/logo.png?v=6" alt="Hospital Escandón" className="h-full w-auto object-contain" />
            </div>
            <span className="font-semibold text-lg tracking-wide hidden sm:block ml-1">Bitácora HE</span>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex flex-1 justify-center mx-4">
            <ul className="flex flex-row gap-1">
              {visibleItems.map(item => (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all font-medium text-sm ${
                      location.pathname === item.path 
                      ? 'bg-white/10 text-white shadow-sm' 
                      : 'text-slate-300 hover:text-white hover:bg-white/5'
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
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg text-xs font-medium border border-white/10 transition-all group"
              title="Buscar Paciente por Nombre, Folio (#5704) o CURP (Ctrl + K)"
            >
              <FiSearch className="text-sm opacity-70 group-hover:opacity-100 transition-opacity" />
              <span className="hidden sm:inline">Buscar</span>
              <kbd className="hidden md:inline-flex items-center justify-center bg-white/10 text-[10px] text-slate-300 px-1.5 rounded h-4 font-mono ml-1">
                Ctrl K
              </kbd>
            </button>

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
                onClick={() => navigate('/config-servidor')}
                className="text-slate-400 hover:text-white hover:bg-white/10 p-2 rounded-lg transition-colors flex items-center justify-center"
                title="Configuración de Servidor"
              >
                <FiSettings className="text-lg" />
              </button>
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
      <PatientSearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Main Content Area */}
      <main className="page-content-scroll">
        <Outlet />
      </main>
    </div>
  );
}
