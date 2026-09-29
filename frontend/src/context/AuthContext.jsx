import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { purgeBiometrics } from '../hooks/useDigitalPersona';
import { api } from '../api';
import { useQueryClient } from '@tanstack/react-query';
import { useSessionPermissionsQuery } from '../hooks/useQueries';
import { effectiveModules, parsePermissionValue } from '../utils/permissions';

const AuthContext = createContext(null);

/**
 * Proveedor Global de Autenticación y Sesión de Usuario.
 * Sincroniza de forma reactiva el estado de autenticación y roles con localStorage.
 */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(() => {
    const savedToken = localStorage.getItem('token');
    if (!savedToken) return null;
    return {
      rol: localStorage.getItem('rol') || '',
      username: localStorage.getItem('usuario') || '',
      permisos_modulos: localStorage.getItem('permisos_modulos'),
      formatos_permitidos: localStorage.getItem('formatos_permitidos'),
      medicoId: localStorage.getItem('medico_id') || null,
      medico: localStorage.getItem('medico') ? JSON.parse(localStorage.getItem('medico')) : null
    };
  });
  const sessionAccess = useSessionPermissionsQuery(token);
  useEffect(() => {
    if (!sessionAccess.data || !token) return;
    const fresh = sessionAccess.data;
    for (const key of ['rol', 'permisos_modulos', 'formatos_permitidos']) {
      if (fresh[key] == null) localStorage.removeItem(key);
      else localStorage.setItem(key, fresh[key]);
    }
    setUser(previous => ({ ...previous, ...fresh }));
  }, [sessionAccess.data, token]);

  // Sincronizar cambios en token
  useEffect(() => {
    if (token) {
      setUser({
        rol: localStorage.getItem('rol') || '',
        username: localStorage.getItem('usuario') || '',
        permisos_modulos: localStorage.getItem('permisos_modulos'),
        formatos_permitidos: localStorage.getItem('formatos_permitidos'),
        medicoId: localStorage.getItem('medico_id') || null,
        medico: localStorage.getItem('medico') ? JSON.parse(localStorage.getItem('medico')) : null
      });
    } else {
      setUser(null);
    }
  }, [token]);

  /**
   * Registra la sesión y actualiza el estado global reactivo.
   * @param {string} authToken Token JWT
   * @param {string|object} userData Rol en string u objeto con detalles del usuario/médico
   */
  const login = useCallback((authToken, userData) => {
    queryClient.clear();
    ['token','rol','usuario','medico','medico_id','nombre_completo','permisos_modulos','formatos_permitidos'].forEach(key=>localStorage.removeItem(key));
    localStorage.setItem('token', authToken);
    localStorage.setItem('hes_last_activity_at', String(Date.now()));
    
    let userObj = {};
    if (typeof userData === 'string') {
      localStorage.setItem('rol', userData);
      userObj = { rol: userData, username: '', medicoId: null, medico: null };
    } else if (userData && typeof userData === 'object') {
      if (userData.rol) localStorage.setItem('rol', userData.rol);
      if (userData.username) localStorage.setItem('usuario', userData.username);
      if (userData.medico_id) localStorage.setItem('medico_id', userData.medico_id);
      if (userData.medico) localStorage.setItem('medico', JSON.stringify(userData.medico));
      for (const key of ['permisos_modulos', 'formatos_permitidos']) {
        if (userData[key] != null) localStorage.setItem(key, userData[key]);
      }
      userObj = {
        permisos_modulos: userData.permisos_modulos ?? null,
        formatos_permitidos: userData.formatos_permitidos ?? null,
        rol: userData.rol || localStorage.getItem('rol') || '',
        username: userData.username || localStorage.getItem('usuario') || '',
        medicoId: userData.medico_id || localStorage.getItem('medico_id') || null,
        medico: userData.medico || (localStorage.getItem('medico') ? JSON.parse(localStorage.getItem('medico')) : null)
      };
    }

    setToken(authToken);
    setUser(userObj);
  }, [queryClient]);

  /**
   * Cierra la sesión activa y purga el almacenamiento local y biométrico.
   */
  const logout = useCallback(async () => {
    try {
      if (localStorage.getItem('token')) await api.post('/auth/logout', null, { timeout: 5000 });
    } catch {
      // Local cleanup is mandatory even when the server is unreachable.
    } finally {
      purgeBiometrics();
      localStorage.removeItem('token');
      localStorage.removeItem('rol');
      localStorage.removeItem('usuario');
      localStorage.removeItem('medico');
      localStorage.removeItem('medico_id');
      localStorage.removeItem('nombre_completo');
      localStorage.removeItem('permisos_modulos');
      localStorage.removeItem('formatos_permitidos');
      localStorage.removeItem('hes_last_activity_at');
      sessionStorage.clear();
      queryClient.clear();
      setToken(null);
      setUser(null);
    }
  }, [queryClient]);

  /**
   * Verifica si el usuario actual posee alguno de los roles autorizados.
   * @param  {...string|string[]} allowedRoles Lista o array de roles permitidos
   * @returns {boolean}
   */
  const hasRole = useCallback((...allowedRoles) => {
    if (!user || !user.rol) return false;
    const flattened = allowedRoles.flat();
    return flattened.includes(user.rol);
  }, [user]);

  const value = {
    token,
    user: user ? { ...user, ...sessionAccess.data } : null,
    isAuthenticated: !!token,
    loading: Boolean(token && sessionAccess.isPending),
    accessError: sessionAccess.isError,
    refreshAccess: sessionAccess.refetch,
    hasModule: (...keys) => keys.some(key => effectiveModules(user)[key]),
    hasFormat: code => {
      if (user?.formatos_permitidos == null) return true;
      const formats = parsePermissionValue(user.formatos_permitidos, []);
      return Array.isArray(formats) && formats.includes(code);
    },
    login,
    logout,
    hasRole
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook para consumir el estado global de autenticación en cualquier componente.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe ser utilizado dentro de un AuthProvider');
  }
  return context;
}

export default AuthContext;
