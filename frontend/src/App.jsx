import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LoginDual from './pages/LoginDual';
import CapturaEnfermeria from './pages/CapturaEnfermeria';
import FirmaExpress from './pages/FirmaExpress';
import FirmasArea from './pages/FirmasArea';
import AdminDashboard from './pages/AdminDashboard';
import CamasDashboard from './pages/CamasDashboard';
import PatientDashboard from './pages/PatientDashboard';
import AgendaMedica from './pages/AgendaMedica';
import VerificarDocumento from './pages/VerificarDocumento';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import useAutoLogout from './hooks/useAutoLogout';
import NotificationCenter from './components/ui/NotificationCenter';
import { useAuth } from './context/AuthContext';

const PdfPreviewPage = lazy(() => import('./pages/PdfPreviewPage'));

function AppContent() {
  const { isAuthenticated } = useAuth();
  useAutoLogout(isAuthenticated);

  return (
    <ErrorBoundary>
      <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginDual />} />
      <Route path="/verificar" element={<VerificarDocumento />} />
      <Route path="/verificar/documento" element={<VerificarDocumento />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/ehr/visor-pdf" element={<Suspense fallback={<p>Cargando visor PDF…</p>}><PdfPreviewPage /></Suspense>} />
      </Route>
      
      {/* Protected Routes wrapped in Layout */}
      <Route element={<Layout />}>
        <Route element={<ProtectedRoute />}><Route path="/sin-acceso" element={<p className="p-8">Su cuenta no tiene áreas asignadas. Solicite acceso al administrador.</p>} /></Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/rh" element={<AdminDashboard />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/camas" element={<CamasDashboard />} />
        </Route>
        
        <Route element={<ProtectedRoute />}>
          <Route path="/captura" element={<CapturaEnfermeria />} />
        </Route>
        
        <Route element={<ProtectedRoute />}>
          <Route path="/firma-express" element={<FirmaExpress />} />
          <Route path="/firmas-area" element={<FirmasArea />} />
        </Route>
        
        <Route element={<ProtectedRoute />}>
          <Route path="/ehr" element={<PatientDashboard />} />
          <Route path="/ehr/:pt_num" element={<PatientDashboard />} />
          <Route path="/agenda" element={<AgendaMedica />} />
        </Route>
      </Route>
      </Routes>
      <NotificationCenter />
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
