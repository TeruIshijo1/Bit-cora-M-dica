import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, Image } from 'react-native';
import { useRouter } from 'expo-router';
import { useServer } from '../contexts/ServerContext';

export default function ServerSetupScreen() {
  const [urlInput, setUrlInput] = useState('');
  const [error, setError] = useState('');
  const { updateServerUrl } = useServer();
  const router = useRouter();

  const handleSave = async () => {
    if (!urlInput) {
      setError('Por favor, ingresa la URL del servidor.');
      return;
    }
    
    // Validar formato de URL básico
    if (!urlInput.startsWith('http://') && !urlInput.startsWith('https://')) {
      setError('La URL debe empezar con http:// o https://');
      return;
    }

    try {
      await updateServerUrl(urlInput);
      router.replace('/login');
    } catch (err) {
      setError('Error al guardar la configuración.');
    }
  };

  return (
    <KeyboardAvoidingView 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1 bg-slate-50 justify-center px-6"
    >
      <View className="bg-white p-8 rounded-2xl shadow-lg border border-slate-100">
        <View className="items-center mb-8">
          <Text className="text-2xl font-bold text-hes-blue-main mb-2">Configuración Inicial</Text>
          <Text className="text-slate-500 text-center text-base">
            Ingresa la dirección del servidor de Bitácora HES para conectar la aplicación.
          </Text>
        </View>

        <View className="mb-6">
          <Text className="text-sm font-semibold text-slate-700 mb-2">URL del Servidor</Text>
          <TextInput
            className={`w-full border ${error ? 'border-red-500' : 'border-slate-300'} rounded-lg p-4 text-slate-800 bg-slate-50 focus:border-hes-blue-light focus:bg-white`}
            placeholder="Ej: https://tunel-ngrok.app o http://192.168..."
            value={urlInput}
            onChangeText={(text) => {
              setUrlInput(text);
              setError('');
            }}
            autoCapitalize="none"
            keyboardType="url"
            autoCorrect={false}
          />
          {error ? <Text className="text-red-500 text-xs mt-2">{error}</Text> : null}
        </View>

        <TouchableOpacity 
          className="w-full bg-hes-blue-main py-4 rounded-lg items-center active:bg-hes-blue-cross"
          onPress={handleSave}
        >
          <Text className="text-white font-bold text-lg">Guardar y Continuar</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}
