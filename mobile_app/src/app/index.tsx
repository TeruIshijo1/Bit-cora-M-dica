import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Redirect } from 'expo-router';
import { useServer } from '../contexts/ServerContext';
import * as SecureStore from 'expo-secure-store';

export default function EntryScreen() {
  const { serverUrl, isReady } = useServer();
  const [targetRoute, setTargetRoute] = useState(null);

  useEffect(() => {
    if (!isReady) return;

    const checkState = async () => {
      if (!serverUrl) {
        setTargetRoute('/server-setup');
        return;
      }

      const token = await SecureStore.getItemAsync('token');
      if (token) {
        setTargetRoute('/dashboard');
      } else {
        setTargetRoute('/login');
      }
    };

    checkState();
  }, [isReady, serverUrl]);

  if (targetRoute) {
    return <Redirect href={targetRoute} />;
  }

  return (
    <View className="flex-1 justify-center items-center bg-slate-50">
      <ActivityIndicator size="large" color="#004687" />
    </View>
  );
}
