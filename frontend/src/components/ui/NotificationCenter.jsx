import React, { useEffect, useState } from 'react';
import {
  FiAlertCircle,
  FiAlertTriangle,
  FiCheckCircle,
  FiInfo,
  FiX,
} from 'react-icons/fi';
import { notify, subscribeToNotifications } from '../../utils/notifications';

const notificationStyles = {
  success: {
    accent: 'hes-notification-success',
    icon: <FiCheckCircle aria-hidden="true" />,
    defaultTitle: 'Guardado correctamente',
  },
  error: {
    accent: 'hes-notification-error',
    icon: <FiAlertCircle aria-hidden="true" />,
    defaultTitle: 'No se pudo completar',
  },
  warning: {
    accent: 'hes-notification-warning',
    icon: <FiAlertTriangle aria-hidden="true" />,
    defaultTitle: 'Revisa esta información',
  },
  info: {
    accent: 'hes-notification-info',
    icon: <FiInfo aria-hidden="true" />,
    defaultTitle: 'Información',
  },
};

const makeMedicalMessage = (message) => {
  let value = String(message || '').trim();

  // Los nombres técnicos de la base de datos no ayudan en el flujo clínico.
  value = value
    .replace(/^¡|!$/g, '')
    .replace(/\s*en el expediente SQL Server\.?/gi, ' en el expediente clínico.')
    .replace(/\s*en SQL Server\.?/gi, ' en el expediente clínico.')
    .replace(/guardado con éxito/gi, 'se guardó correctamente')
    .replace(/guardado correctamente/gi, 'se guardó correctamente')
    .replace(/registrado correctamente/gi, 'se registró correctamente')
    .replace(/actualizado correctamente/gi, 'se actualizó correctamente')
    .replace(/(\.|!)+$/g, '.');

  // La respuesta original comienza con el nombre del documento; al cambiar
  // "guardado" por "se guardó", queda una oración natural para la interfaz.
  return value;
};

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    const nativeAlert = window.alert.bind(window);
    window.alert = (message) => notify(message);

    const unsubscribe = subscribeToNotifications((notification) => {
      setNotifications((current) => [...current, notification].slice(-4));

      window.setTimeout(() => {
        setNotifications((current) => current.filter(({ id }) => id !== notification.id));
      }, notification.duration);
    });

    return () => {
      window.alert = nativeAlert;
      unsubscribe();
    };
  }, []);

  const dismiss = (id) => {
    setNotifications((current) => current.filter((notification) => notification.id !== id));
  };

  if (!notifications.length) return null;

  return (
    <div className="hes-notification-stack" aria-live="polite" aria-atomic="false">
      {notifications.map((notification) => {
        const style = notificationStyles[notification.type] || notificationStyles.info;
        return (
          <div
            key={notification.id}
            className={`hes-notification ${style.accent}`}
            role={notification.type === 'error' ? 'alert' : 'status'}
          >
            <div className="hes-notification-icon">{style.icon}</div>
            <div className="hes-notification-content">
              <p className="hes-notification-title">
                {notification.title || style.defaultTitle}
              </p>
              <p className="hes-notification-message">{makeMedicalMessage(notification.message)}</p>
            </div>
            <button
              type="button"
              className="hes-notification-close"
              onClick={() => dismiss(notification.id)}
              aria-label="Cerrar aviso"
              title="Cerrar aviso"
            >
              <FiX aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
