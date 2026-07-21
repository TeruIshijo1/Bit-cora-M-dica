import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator, RefreshControl, Alert, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import api from '../api';
import { Ionicons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';

export default function CamasDashboardScreen() {
  const [camas, setCamas] = useState([]);
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rol, setRol] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const router = useRouter();

  const fetchData = async () => {
    try {
      const [resCamas, resPacientes] = await Promise.all([
        api.get('/api/camas'),
        api.get('/api/pacientes')
      ]);
      setCamas(resCamas.data);
      setPacientes(resPacientes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    SecureStore.getItemAsync('rol').then(r => setRol(r || ''));
    fetchData();
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, []);

  // Helper to find patient assigned to a bed
  const getPacienteEnCama = (camaId) => {
    return pacientes.find(p => p.cama_id === camaId && p.estado === 'Activo');
  };

  const getEstadoStyles = (estado) => {
    const e = estado ? estado.toUpperCase() : 'DESCONOCIDA';
    switch (e) {
      case 'DISPONIBLE': return 'bg-emerald-100 border-emerald-300 text-emerald-800';
      case 'OCUPADA': return 'bg-rose-100 border-rose-300 text-rose-800';
      case 'MANTENIMIENTO': return 'bg-amber-100 border-amber-300 text-amber-800';
      case 'SUCIA': return 'bg-orange-100 border-orange-300 text-orange-800';
      case 'BLOQUEADA': return 'bg-slate-300 border-slate-400 text-slate-800';
      default: return 'bg-slate-100 border-slate-300 text-slate-800';
    }
  };

  const getIconForEstado = (estado) => {
    const e = estado ? estado.toUpperCase() : 'DESCONOCIDA';
    switch (e) {
      case 'DISPONIBLE': return <Ionicons name="bed-outline" size={32} color="#059669" />;
      case 'OCUPADA': return <Ionicons name="bed" size={32} color="#e11d48" />;
      case 'MANTENIMIENTO': return <Ionicons name="build-outline" size={32} color="#d97706" />;
      case 'SUCIA': return <Ionicons name="trash-outline" size={32} color="#ea580c" />;
      case 'BLOQUEADA': return <Ionicons name="lock-closed-outline" size={32} color="#475569" />;
      default: return <Ionicons name="help-outline" size={32} color="#64748b" />;
    }
  };

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('token');
    await SecureStore.deleteItemAsync('rol');
    router.replace('/');
  };

  const cambiarEstadoLimpieza = async (numeroCama, nuevoEstado) => {
    try {
      setLoading(true);
      await api.put(`/api/camas/${numeroCama}/limpieza`, { estado_limpieza: nuevoEstado });
      await fetchData();
    } catch (error) {
      console.error('Error al cambiar estado de limpieza:', error);
      Alert.alert("Error", "No se pudo actualizar el estado de la cama.");
      setLoading(false);
    }
  };

  if (loading && !refreshing) {
    return (
      <View className="flex-1 justify-center items-center bg-slate-50">
        <ActivityIndicator size="large" color="#004687" />
        <Text className="mt-4 text-slate-500 font-medium">Cargando camas...</Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-50">
      <View className="bg-hes-blue-main pt-12 pb-4 px-4 flex-row items-center shadow-sm">
        <TouchableOpacity onPress={handleLogout} className="p-2 mr-2">
          <Ionicons name="log-out-outline" size={24} color="white" style={{ transform: [{ rotate: '180deg' }] }} />
        </TouchableOpacity>
        <Text className="text-white font-bold text-xl flex-1">Panel de Camas</Text>
        <TouchableOpacity onPress={onRefresh} className="p-2">
          <Ionicons name="refresh" size={24} color="white" />
        </TouchableOpacity>
      </View>

      <View className="px-4 pt-4 pb-2">
        <View className="bg-white flex-row items-center rounded-xl px-3 py-2 shadow-sm border border-slate-200">
          <Ionicons name="search" size={20} color="#94a3b8" />
          <TextInput
            className="flex-1 ml-2 text-slate-700 h-8"
            placeholder="Buscar por nombre de cama..."
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={20} color="#94a3b8" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      <ScrollView 
        className="flex-1 p-4 pt-2"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#004687']} />}
      >
        <View className="flex-row flex-wrap justify-between">
          {camas.filter(cama => {
            const numero = cama.RoomName || cama.numero_cama || cama.numero || '';
            return numero.toLowerCase().includes(searchQuery.toLowerCase());
          }).map(cama => {
            const paciente = getPacienteEnCama(cama.id);
            const numero = cama.RoomName || cama.numero_cama || cama.numero || '?';
            
            let estadoActual = cama.Estatus || cama.estado || 'DISPONIBLE';
            if (estadoActual.toUpperCase() === 'LIBRE') estadoActual = 'DISPONIBLE';
            
            if (estadoActual.toUpperCase() !== 'OCUPADA') {
              const limpiezaUpper = cama.estado_limpieza?.toUpperCase();
              if (limpiezaUpper === 'SUCIA') estadoActual = 'SUCIA';
              else if (limpiezaUpper === 'EN MANTENIMIENTO' || limpiezaUpper === 'MANTENIMIENTO') estadoActual = 'MANTENIMIENTO';
            }
            
            const styleClasses = getEstadoStyles(estadoActual);
            
            return (
              <TouchableOpacity
                key={cama.RoomCode || cama.id || Math.random().toString()}
                className={`w-[48%] mb-4 p-4 rounded-2xl border ${styleClasses} shadow-sm active:opacity-70`}
                onPress={() => {
                  const pacienteId = paciente ? paciente.id : cama.PTNum;
                  const normalizedRol = (rol || '').toLowerCase();
                  
                  if (normalizedRol === 'enfermeria' && estadoActual?.toUpperCase() === 'OCUPADA' && pacienteId) {
                    router.push(`/captura-enfermeria?pacienteId=${pacienteId}&camaNumero=${numero}`);
                  } else if (normalizedRol === 'limpieza' || normalizedRol === 'mantenimiento/limpieza' || normalizedRol === 'admin' || normalizedRol === 'sistemas') {
                    Alert.alert(
                      "Cambiar Estado",
                      `¿Qué deseas hacer con la cama ${numero}?`,
                      [
                        { text: "Marcar Disponible", onPress: () => cambiarEstadoLimpieza(numero, "Disponible") },
                        { text: "Marcar Sucia", onPress: () => cambiarEstadoLimpieza(numero, "Sucia") },
                        { text: "Marcar Mantenimiento", onPress: () => cambiarEstadoLimpieza(numero, "En Mantenimiento") },
                        { text: "Cancelar", style: "cancel" }
                      ]
                    );
                  }
                }}
              >
                <View className="flex-row justify-between items-start mb-2">
                  <View className="bg-white/50 rounded-lg px-2 py-1 justify-center items-center max-w-[70%]">
                    <Text className="font-bold text-xs" numberOfLines={2}>{numero}</Text>
                  </View>
                  {getIconForEstado(estadoActual)}
                </View>
                
                <Text className="font-bold mt-1 uppercase text-xs opacity-80">{estadoActual}</Text>
                
                {estadoActual.toUpperCase() === 'OCUPADA' ? (
                  <View className="mt-2 bg-white/40 p-2 rounded-lg">
                    <Text className="text-xs font-semibold italic opacity-80">Paciente Asignado</Text>
                  </View>
                ) : (
                  <View className="mt-2 p-2 h-12 justify-center">
                    <Text className="text-xs italic opacity-60">Sin paciente asignado</Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
        <View className="h-10" />
      </ScrollView>
    </View>
  );
}
