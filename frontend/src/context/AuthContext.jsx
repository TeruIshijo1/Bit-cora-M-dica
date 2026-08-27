import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

/**
 * Proveedor Global de Autenticación y Sesión de Usuario.
 * Sincroniza de forma reactiva el estado de autenticación y roles con localStorage.
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(() => {
    const savedToken = localStorage.getItem('token');
    if (!savedToken) return null;
    return {
      rol: localStorage.getItem('rol') || '',
      username: localStorage.getItem('usuario') || '',
      medicoId: localStorage.getItem('medico_id') || null,
      medico: localStorage.getItem('medico') ? JSON.parse(localStorage.getItem('medico')) : null
    };
  });
  const [loading, setLoading] = useState(false);

  // Sincronizar cambios en token
  useEffect(() => {
    if (token) {
      setUser({
        rol: localStorage.getItem('rol') || '',
        username: localStorage.getItem('usuario') || '',
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
    localStorage.setItem('token', authToken);
    
    let userObj = {};
    if (typeof userData === 'string') {
      localStorage.setItem('rol', userData);
      userObj = { rol: userData, username: '', medicoId: null, medico: null };
    } else if (userData && typeof userData === 'object') {
      if (userData.rol) localStorage.setItem('rol', userData.rol);
      if (userData.username) localStorage.setItem('usuario', userData.username);
      if (userData.medico_id) localStorage.setItem('medico_id', userData.medico_id);
      if (userData.medico) localStorage.setItem('medico', JSON.stringify(userData.medico));
      userObj = {
        rol: userData.rol || localStorage.getItem('rol') || '',
        username: userData.username || localStorage.getItem('usuario') || '',
        medicoId: userData.medico_id || localStorage.getItem('medico_id') || null,
        medico: userData.medico || (localStorage.getItem('medico') ? JSON.parse(localStorage.getItem('medico')) : null)
      };
    }

    setToken(authToken);
    setUser(userObj);
  }, []);

  /**
   * Cierra la sesión activa y purga el almacenamiento local.
   */
  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('rol');
    localStorage.removeItem('usuario');
    localStorage.removeItem('medico');
    localStorage.removeItem('medico_id');
    setToken(null);
    setUser(null);
  }, []);

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
    user,
    isAuthenticated: !!token,
    loading,
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
