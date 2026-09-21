import React, { createContext, useState, useEffect, useContext, type ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { useRouter } from 'expo-router';

interface ServerContextValue {
  serverUrl: string | null;
  updateServerUrl: (url: string | null) => Promise<void>;
  isReady: boolean;
}

export const ServerContext = createContext<ServerContextValue | null>(null);

export const ServerProvider = ({ children }: { children: ReactNode }) => {
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const loadServerUrl = async () => {
      try {
        const url = await SecureStore.getItemAsync('server_url');
        if (url) {
          setServerUrl(url);
        }
      } catch (error) {
        console.error('Failed to load server URL:', error);
      } finally {
        setIsReady(true);
      }
    };
    
    loadServerUrl();
  }, []);

  const updateServerUrl = async (url: string | null) => {
    try {
      if (!url) {
        await SecureStore.deleteItemAsync('server_url');
        setServerUrl(null);
      } else {
        // Formato básico para asegurar que no termine en barra
        const cleanUrl = url.trim().replace(/\/$/, '');
        await SecureStore.setItemAsync('server_url', cleanUrl);
        setServerUrl(cleanUrl);
      }
    } catch (error) {
      console.error('Failed to save server URL:', error);
      throw error;
    }
  };

  return (
    <ServerContext.Provider value={{ serverUrl, updateServerUrl, isReady }}>
      {children}
    </ServerContext.Provider>
  );
};

export const useServer = () => {
  const context = useContext(ServerContext);
  if (!context) {
    throw new Error('useServer must be used within a ServerProvider');
  }
  return context;
};
