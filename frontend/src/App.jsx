import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import LoginDual from './pages/LoginDual';
import CapturaEnfermeria from './pages/CapturaEnfermeria';
import FirmaExpress from './pages/FirmaExpress';
import AdminDashboard from './pages/AdminDashboard';
import CamasDashboard from './pages/CamasDashboard';
import ServerConfig from './pages/ServerConfig';
import PatientDashboard from './pages/PatientDashboard';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import useAutoLogout from './hooks/useAutoLogout';

function AppContent() {
  useAutoLogout();
  const location = useLocation();
  let serverUrl = localStorage.getItem('server_url');

  if (serverUrl === null || serverUrl !== 'default') {
    localStorage.setItem('server_url', 'default');
    serverUrl = 'default';
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/config-servidor" element={<ServerConfig />} />
      <Route path="/login" element={<LoginDual />} />
      
      {/* Protected Routes wrapped in Layout */}
      <Route element={<Layout />}>
        <Route element={<ProtectedRoute allowedRoles={['admin', 'rh', 'sistemas']} />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/rh" element={<AdminDashboard />} />
        </Route>

        <Route element={<ProtectedRoute allowedRoles={['admin', 'sistemas', 'enfermeria', 'medico', 'rh', 'Mantenimiento/Limpieza', 'limpieza']} />}>
          <Route path="/camas" element={<CamasDashboard />} />
        </Route>
        
        <Route element={<ProtectedRoute allowedRoles={['admin', 'enfermeria', 'sistemas', 'medico']} />}>
          <Route path="/captura" element={<CapturaEnfermeria />} />
        </Route>
        
        <Route element={<ProtectedRoute allowedRoles={['admin', 'medico', 'ayudante']} />}>
          <Route path="/firma-express" element={<FirmaExpress />} />
        </Route>
        
        <Route element={<ProtectedRoute allowedRoles={['admin', 'medico', 'enfermeria', 'sistemas']} />}>
          <Route path="/ehr" element={<PatientDashboard />} />
          <Route path="/ehr/:pt_num" element={<PatientDashboard />} />
        </Route>
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
