import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import { useServer } from '../contexts/ServerContext';
import { Feather } from '@expo/vector-icons';

export default function DashboardScreen() {
  const router = useRouter();
  const { serverUrl } = useServer();
  const [rol, setRol] = useState('');

  useEffect(() => {
    const fetchRol = async () => {
      const storedRol = await SecureStore.getItemAsync('rol');
      if (storedRol) setRol(storedRol);
    };
    fetchRol();
  }, []);

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('token');
    await SecureStore.deleteItemAsync('rol');
    router.replace('/login');
  };

  return (
    <View className="flex-1 bg-slate-50">
      {/* Header */}
      <View className="bg-hes-blue-main pt-12 pb-4 px-6 flex-row justify-between items-center shadow-md">
        <View>
          <Text className="text-white font-bold text-xl">Bitácora HES</Text>
          <Text className="text-blue-200 text-xs mt-1">App Móvil</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} className="p-2 bg-hes-blue-cross rounded-full">
          <Text className="text-white text-xs font-bold px-2">Cerrar Sesión</Text>
        </TouchableOpacity>
      </View>

      <View className="p-6 flex-1 justify-center items-center">
        <Text className="text-2xl font-bold text-slate-700 mb-2">¡Bienvenido!</Text>
        <Text className="text-slate-500 mb-6 text-center">
          Has iniciado sesión con el rol: <Text className="font-bold text-hes-blue-main uppercase">{rol}</Text>
        </Text>

        <View className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 w-full mb-6">
          <Text className="font-semibold text-slate-700 mb-2">Estado de Conexión</Text>
          <Text className="text-sm text-slate-500">Servidor Activo:</Text>
          <Text className="text-sm font-medium text-hes-green mt-1">{serverUrl}</Text>
        </View>

        <TouchableOpacity 
          className="w-full bg-hes-blue-main py-4 rounded-xl items-center flex-row justify-center active:bg-hes-blue-cross shadow-sm"
          onPress={() => router.push('/camas')}
        >
          <Feather name="log-out" size={20} color="white" style={{ marginRight: 8, transform: [{ rotate: '180deg' }] }} />
          <Text className="text-white font-bold text-lg">Ver Panel de Camas</Text>
        </TouchableOpacity>

        <Text className="text-slate-400 text-center text-sm px-4 mt-8">
          Toca el botón superior para acceder al listado de camas y registrar la captura de enfermería.
        </Text>
      </View>
    </View>
  );
}
