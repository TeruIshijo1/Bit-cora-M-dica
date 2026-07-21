import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import api from '../api';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';

export default function CapturaEnfermeriaScreen() {
  const router = useRouter();
  const { pacienteId, camaNumero } = useLocalSearchParams();
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [paciente, setPaciente] = useState(null);
  
  // Catálogos
  const [medicos, setMedicos] = useState([]);
  const [tiposAtencion, setTiposAtencion] = useState([]);
  const [areas, setAreas] = useState([]);
  
  // Formulario
  const [medicoId, setMedicoId] = useState('');
  const [tipoAtencion, setTipoAtencion] = useState('');
  const [areaHospitalaria, setAreaHospitalaria] = useState('');
  const [nombreProcedimiento, setNombreProcedimiento] = useState('');
  const [procedimientoDetalle, setProcedimientoDetalle] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resP, resM, resT, resA] = await Promise.all([
          api.get(`/api/pacientes`),
          api.get(`/api/medicos`),
          api.get(`/api/catalogos/tipos`),
          api.get(`/api/catalogos/areas`)
        ]);
        
        const pacienteEncontrado = resP.data.find(p => p.id === parseInt(pacienteId));
        setPaciente(pacienteEncontrado);
        
        setMedicos(resM.data);
        setTiposAtencion(resT.data);
        setAreas(resA.data);
        
        if (resA.data.length > 0) {
          const hosp = resA.data.find(a => a.nombre.toLowerCase().includes('hosp'));
          setAreaHospitalaria(hosp ? hosp.nombre : resA.data[0].nombre);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        Alert.alert('Error', 'No se pudieron cargar los datos del sistema.');
      } finally {
        setLoading(false);
      }
    };
    
    if (pacienteId) {
      fetchData();
    } else {
      setLoading(false);
    }
  }, [pacienteId]);

  const handleSave = async () => {
    if (!medicoId || !tipoAtencion || !nombreProcedimiento) {
      Alert.alert('Faltan datos', 'Por favor completa Médico, Tipo de Atención y Procedimiento.');
      return;
    }

    setSubmitting(true);
    try {
      const now = new Date();
      // Formato YYYY-MM-DDTHH:mm:00
      const fechaRealizacion = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}T${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:00`;

      await api.post('/api/atenciones/pre-captura', {
        paciente_id: parseInt(pacienteId),
        medico_id: parseInt(medicoId),
        area_hospitalaria: areaHospitalaria,
        tipo_atencion: tipoAtencion,
        nombre_procedimiento: nombreProcedimiento,
        fecha_realizacion: fechaRealizacion,
        procedimiento_detalle: procedimientoDetalle || ""
      });

      Alert.alert('Éxito', 'Captura registrada correctamente.', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } catch (error) {
      console.error('Error al guardar:', error);
      Alert.alert('Error', 'No se pudo guardar la captura.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View className="flex-1 justify-center items-center bg-slate-50">
        <ActivityIndicator size="large" color="#004687" />
        <Text className="mt-4 text-slate-500 font-medium">Cargando datos...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView 
      className="flex-1 bg-slate-50"
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View className="bg-hes-blue-main pt-12 pb-4 px-4 flex-row items-center shadow-sm">
        <TouchableOpacity onPress={() => router.back()} className="p-2 mr-2">
          <Ionicons name="arrow-back" size={24} color="white" />
        </TouchableOpacity>
        <Text className="text-white font-bold text-xl flex-1">Captura de Enfermería</Text>
      </View>

      <ScrollView className="flex-1 p-4">
        {paciente ? (
          <View className="bg-white p-4 rounded-xl border border-slate-200 mb-6 flex-row items-center">
            <View className="bg-emerald-100 w-12 h-12 rounded-full justify-center items-center mr-4">
              <Text className="text-emerald-800 font-bold text-lg">{camaNumero}</Text>
            </View>
            <View className="flex-1">
              <Text className="font-bold text-slate-800 text-lg">{paciente.nombre_completo}</Text>
              <Text className="text-slate-500 text-sm">Cama {camaNumero} • {paciente.area_hospitalaria}</Text>
            </View>
          </View>
        ) : (
          <View className="bg-red-50 p-4 rounded-xl border border-red-200 mb-6">
            <Text className="text-red-600">No se encontró el paciente.</Text>
          </View>
        )}

        {/* Formulario */}
        <View className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 mb-8">
          
          <Text className="text-slate-700 font-semibold mb-2">Médico Tratante / Solicitante *</Text>
          <View className="border border-slate-300 rounded-lg mb-4 bg-slate-50">
            <Picker
              selectedValue={medicoId}
              onValueChange={(itemValue) => setMedicoId(itemValue)}
            >
              <Picker.Item label="Selecciona un médico..." value="" color="#94a3b8" />
              {medicos.map(m => (
                <Picker.Item key={m.id} label={`${m.nombres} ${m.apellidos}`} value={m.id} />
              ))}
            </Picker>
          </View>

          <Text className="text-slate-700 font-semibold mb-2">Tipo de Atención *</Text>
          <View className="border border-slate-300 rounded-lg mb-4 bg-slate-50">
            <Picker
              selectedValue={tipoAtencion}
              onValueChange={(itemValue) => setTipoAtencion(itemValue)}
            >
              <Picker.Item label="Selecciona tipo..." value="" color="#94a3b8" />
              {tiposAtencion.map(t => (
                <Picker.Item key={t.id} label={t.nombre} value={t.nombre} />
              ))}
            </Picker>
          </View>

          <Text className="text-slate-700 font-semibold mb-2">Procedimiento (Resumen) *</Text>
          <TextInput
            className="border border-slate-300 rounded-lg p-3 mb-4 bg-slate-50 text-slate-800"
            placeholder="Ej. Toma de signos vitales, Aplicación de medicamento..."
            value={nombreProcedimiento}
            onChangeText={setNombreProcedimiento}
          />

          <Text className="text-slate-700 font-semibold mb-2">Detalles Adicionales (Opcional)</Text>
          <TextInput
            className="border border-slate-300 rounded-lg p-3 mb-4 bg-slate-50 text-slate-800"
            placeholder="Notas de enfermería, observaciones..."
            value={procedimientoDetalle}
            onChangeText={setProcedimientoDetalle}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />

          <TouchableOpacity 
            className={`w-full py-4 rounded-xl items-center flex-row justify-center shadow-sm mt-4 ${submitting ? 'bg-slate-400' : 'bg-hes-green'}`}
            onPress={handleSave}
            disabled={submitting || !paciente}
          >
            {submitting ? (
              <ActivityIndicator color="white" />
            ) : (
              <>
                <Ionicons name="save-outline" size={20} color="white" style={{ marginRight: 8 }} />
                <Text className="text-white font-bold text-lg">Guardar Captura</Text>
              </>
            )}
          </TouchableOpacity>

        </View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}
