import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { canAccessPath, landingRoute } from '../utils/permissions';
import AlertBanner from './ui/AlertBanner';

export default function ProtectedRoute() {
  const { isAuthenticated, user, loading, accessError, refreshAccess } = useAuth();
  const { pathname } = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (loading) return <p className="p-6">Comprobando accesos…</p>;
  if (accessError) return <AlertBanner message="No se pudieron comprobar sus accesos." onRetry={refreshAccess} />;
  if (user?.must_change_password) return <Navigate to="/login" replace />;
  if (!canAccessPath(user, pathname)) return <Navigate to={landingRoute(user)} replace />;
  return <Outlet />;
}
