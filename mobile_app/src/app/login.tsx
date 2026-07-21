import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import api from '../api';
import * as SecureStore from 'expo-secure-store';
import { useServer } from '../contexts/ServerContext';

export default function LoginScreen() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const router = useRouter();
  const { serverUrl } = useServer();

  const handleLogin = async () => {
    if (!username || !password) {
      setError('Por favor, ingresa usuario y contraseña');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await api.post('/api/auth/login/admin', {
        username,
        password
      });

      if (response.data.access_token) {
        await SecureStore.setItemAsync('token', response.data.access_token);
        await SecureStore.setItemAsync('rol', response.data.rol || 'USER');
        router.replace('/camas');
      } else {
        setError('Error en la autenticación');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error de conexión o credenciales inválidas');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1 bg-slate-50 justify-center px-6"
    >
      <View className="bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
        
        <View className="items-center mb-8">
          <Text className="text-3xl font-extrabold text-hes-blue-main mb-1">Bitácora HES</Text>
          <Text className="text-slate-500 font-medium">Inicia sesión en tu cuenta</Text>
          {serverUrl && (
            <Text className="text-xs text-slate-400 mt-2">Conectado a: {serverUrl}</Text>
          )}
        </View>

        <View className="mb-4">
          <Text className="text-sm font-semibold text-slate-700 mb-2">Usuario</Text>
          <TextInput
            className="w-full border border-slate-300 rounded-lg p-4 text-slate-800 bg-slate-50 focus:border-hes-blue-light focus:bg-white"
            placeholder="Ingresa tu usuario"
            value={username}
            onChangeText={(text) => {
              setUsername(text);
              setError('');
            }}
            autoCapitalize="none"
          />
        </View>

        <View className="mb-6">
          <Text className="text-sm font-semibold text-slate-700 mb-2">Contraseña</Text>
          <TextInput
            className="w-full border border-slate-300 rounded-lg p-4 text-slate-800 bg-slate-50 focus:border-hes-blue-light focus:bg-white"
            placeholder="Ingresa tu contraseña"
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              setError('');
            }}
            secureTextEntry
          />
          {error ? <Text className="text-red-500 text-xs mt-2">{error}</Text> : null}
        </View>

        <TouchableOpacity 
          className="w-full bg-hes-blue-main py-4 rounded-lg items-center flex-row justify-center active:bg-hes-blue-cross"
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" className="mr-2" />
          ) : null}
          <Text className="text-white font-bold text-lg">Ingresar</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          className="mt-6 p-2 items-center"
          onPress={() => router.push('/server-setup')}
        >
          <Text className="text-hes-blue-light text-sm font-medium">Cambiar Configuración de Servidor</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}
