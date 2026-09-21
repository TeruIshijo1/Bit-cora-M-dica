import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LoginDual from './pages/LoginDual';
import CapturaEnfermeria from './pages/CapturaEnfermeria';
import FirmaExpress from './pages/FirmaExpress';
import AdminDashboard from './pages/AdminDashboard';
import CamasDashboard from './pages/CamasDashboard';
import PatientDashboard from './pages/PatientDashboard';
import AgendaMedica from './pages/AgendaMedica';
import VerificarDocumento from './pages/VerificarDocumento';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import useAutoLogout from './hooks/useAutoLogout';

function AppContent() {
  useAutoLogout();

  return (
    <ErrorBoundary>
      <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginDual />} />
      <Route path="/verificar" element={<VerificarDocumento />} />
      <Route path="/verificar/documento" element={<VerificarDocumento />} />
      
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
          <Route path="/agenda" element={<AgendaMedica />} />
        </Route>
      </Route>
    </Routes>
    </ErrorBoundary>
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
