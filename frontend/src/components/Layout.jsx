import React, { useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { FiLogOut, FiUsers, FiClipboard, FiActivity, FiSettings, FiUser, FiEdit3, FiMenu, FiX } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';

const serverIP = window.location.hostname;

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const rol = localStorage.getItem('rol');
  
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
    navigate('/login');
  };

  const menuItems = [
    { path: '/admin', label: 'Dashboard Global', icon: <FiActivity />, roles: ['admin', 'sistemas'] },
    { path: '/rh', label: 'Recursos Humanos', icon: <FiUsers />, roles: ['admin', 'rh', 'sistemas'] },
    { path: '/captura', label: 'Captura (Enfermería)', icon: <FiClipboard />, roles: ['admin', 'enfermeria', 'sistemas'] },
    { path: '/firma-express', label: 'Firma Express (Médico)', icon: <FiEdit3 />, roles: ['admin', 'medico', 'ayudante'] },
    { path: '/camas', label: 'Camas', icon: <MdLocalHospital />, roles: ['admin', 'sistemas', 'enfermeria', 'medico', 'rh'] }
  ];

  const visibleItems = menuItems.filter(item => item.roles.includes(rol));

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top Header - Medis365 Style */}
      <header className="bg-hes-blue-main text-white shadow-md z-20 flex flex-col relative">
        {/* Upper tier: Logo and User Info */}
        <div className="flex justify-between items-center px-4 md:px-6 py-2 border-b border-[#003870]">
          <div className="flex items-center gap-2 md:gap-3">
            <button 
              className="md:hidden p-2 -ml-2 text-white hover:bg-[#003870] rounded-md transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <FiX className="text-2xl" /> : <FiMenu className="text-2xl" />}
            </button>
            <img src="/logo.png" alt="Hospital Escandón" className="h-10 md:h-14 object-contain bg-white rounded p-1" />
            <span className="font-bold text-lg md:text-xl tracking-wide hidden sm:block">Bitácora HES</span>
          </div>
          
          <div className="flex items-center gap-3 md:gap-6">
            <div className="hidden md:flex text-sm font-medium flex-col items-end leading-tight text-slate-200">
              <span>Sesión activa</span>
              <span className="uppercase text-hes-green font-bold tracking-wider">{rol}</span>
            </div>
            {medico ? (
              <div className="flex items-center gap-2 md:gap-3 bg-[#003870] md:py-1 px-2 md:px-3 rounded-full border border-[#002b5e]">
                {medico.foto_url ? (
                  <img src={`${medico.foto_url}`} alt="Perfil" className="w-7 h-7 md:w-8 md:h-8 rounded-full object-cover shadow-sm" />
                ) : (
                  <div className="w-7 h-7 md:w-8 md:h-8 rounded-full bg-hes-blue-main text-white flex items-center justify-center border border-slate-400">
                    <FiUser />
                  </div>
                )}
                <div className="text-xs md:text-sm font-medium pr-1 md:pr-2 hidden sm:block truncate max-w-[120px] md:max-w-xs">
                  {medico.nombre_completo}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center w-7 h-7 md:w-8 md:h-8 rounded-full bg-slate-300 text-slate-700">
                <FiUser />
              </div>
            )}
            <button 
              onClick={handleLogout}
              className="text-red-300 hover:bg-[#003870] hover:text-red-400 p-2 rounded-md md:rounded-full transition-colors flex items-center gap-2 text-sm"
              title="Cerrar Sesión"
            >
              <FiLogOut className="text-xl" /> <span className="hidden sm:block">Salir</span>
            </button>
          </div>
        </div>

        {/* Lower tier: Horizontal Navigation (Desktop) / Dropdown (Mobile) */}
        <nav className={`${mobileMenuOpen ? 'block' : 'hidden'} md:block px-4 absolute md:relative top-full left-0 w-full md:w-auto bg-hes-blue-main md:bg-transparent shadow-lg md:shadow-none z-50 md:z-auto`}>
          <ul className="flex flex-col md:flex-row flex-wrap md:gap-2 py-2 md:py-2">
            {visibleItems.map(item => (
              <li key={item.path} className="w-full md:w-auto border-b border-[#003870] md:border-none">
                <Link
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 md:gap-2 px-4 py-3 md:py-2 md:rounded-t-md transition-all font-semibold ${
                    location.pathname === item.path 
                    ? 'bg-slate-50 text-hes-blue-main shadow-inner' 
                    : 'hover:bg-[#003870] text-slate-200'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="page-content-scroll">
        <Outlet />
      </main>
    </div>
  );
}
