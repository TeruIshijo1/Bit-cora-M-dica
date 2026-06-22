import React from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { FiLogOut, FiUsers, FiClipboard, FiActivity, FiSettings, FiUser, FiEdit3 } from 'react-icons/fi';
import { MdLocalHospital } from 'react-icons/md';

const serverIP = window.location.hostname;

export default function Layout() {
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
    { path: '/rh', label: 'Recursos Humanos', icon: <FiUsers />, roles: ['admin', 'rh'] },
    { path: '/captura', label: 'Captura (Enfermería)', icon: <FiClipboard />, roles: ['admin', 'enfermeria'] },
    { path: '/firma-express', label: 'Firma Express (Médico)', icon: <FiEdit3 />, roles: ['admin', 'medico'] }
  ];

  const visibleItems = menuItems.filter(item => item.roles.includes(rol));

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top Header - Medis365 Style */}
      <header className="bg-hes-blue-main text-white shadow-md z-20 flex flex-col">
        {/* Upper tier: Logo and User Info */}
        <div className="flex justify-between items-center px-6 py-2 border-b border-[#003870]">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Hospital Escandón" className="h-14 object-contain bg-white rounded p-1" />
            <span className="font-bold text-xl tracking-wide hidden sm:block">Bitácora HES</span>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="text-sm font-medium flex flex-col items-end leading-tight text-slate-200">
              <span>Sesión activa</span>
              <span className="uppercase text-hes-green font-bold tracking-wider">{rol}</span>
            </div>
            {medico ? (
              <div className="flex items-center gap-3 bg-[#003870] py-1 px-3 rounded-full border border-[#002b5e]">
                {medico.foto_url ? (
                  <img src={`http://${serverIP}:8000${medico.foto_url}`} alt="Perfil" className="w-8 h-8 rounded-full object-cover shadow-sm" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-hes-blue-main text-white flex items-center justify-center border border-slate-400">
                    <FiUser />
                  </div>
                )}
                <div className="text-sm font-medium pr-2">
                  {medico.nombre_completo}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-300 text-slate-700">
                <FiUser />
              </div>
            )}
            <button 
              onClick={handleLogout}
              className="text-red-300 hover:text-red-400 p-2 rounded-full transition-colors flex items-center gap-2 text-sm"
              title="Cerrar Sesión"
            >
              <FiLogOut className="text-xl" /> <span className="hidden sm:block">Salir</span>
            </button>
          </div>
        </div>

        {/* Lower tier: Horizontal Navigation */}
        <nav className="px-4">
          <ul className="flex flex-wrap gap-2 py-2">
            {visibleItems.map(item => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center gap-2 px-4 py-2 rounded-t-md transition-all font-semibold ${
                    location.pathname === item.path ? 'bg-slate-50 text-hes-blue-main shadow-inner' : 'hover:bg-[#003870] text-slate-200'
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

      {/* Main Content Area (This will now hold the 2-column layout inside each page) */}
      <main className="flex-1 overflow-hidden flex">
        <Outlet />
      </main>
    </div>
  );
}
