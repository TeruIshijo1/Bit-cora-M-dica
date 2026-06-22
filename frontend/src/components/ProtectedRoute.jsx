import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

export default function ProtectedRoute({ allowedRoles }) {
  const token = localStorage.getItem('token');
  const rol = localStorage.getItem('rol');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Admin always has access to everything
  if (rol === 'admin') {
    return <Outlet />;
  }

  if (allowedRoles && !allowedRoles.includes(rol)) {
    return <Navigate to="/login" replace />; // Or to a generic "Not authorized" page
  }

  return <Outlet />;
}
