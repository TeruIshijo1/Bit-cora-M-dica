import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginDual from './pages/LoginDual';
import CapturaEnfermeria from './pages/CapturaEnfermeria';
import FirmaExpress from './pages/FirmaExpress';
import AdminDashboard from './pages/AdminDashboard';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import useAutoLogout from './hooks/useAutoLogout';

function AppContent() {
  useAutoLogout();

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginDual />} />
      
      {/* Protected Routes wrapped in Layout */}
      <Route element={<Layout />}>
        <Route element={<ProtectedRoute allowedRoles={['admin', 'rh']} />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/rh" element={<AdminDashboard />} />
        </Route>
        
        <Route element={<ProtectedRoute allowedRoles={['admin', 'enfermeria']} />}>
          <Route path="/captura" element={<CapturaEnfermeria />} />
        </Route>
        
        <Route element={<ProtectedRoute allowedRoles={['admin', 'medico']} />}>
          <Route path="/firma-express" element={<FirmaExpress />} />
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
