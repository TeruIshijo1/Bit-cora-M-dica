# Frontend

El Frontend del proyecto es responsable de la interfaz gráfica hospitalaria, la interacción en tiempo real y la captura biométrica fluida.

## Tecnologías Principales
- **Framework:** React 18.
- **Empaquetador:** Vite (con Rolldown engine).
- **Caché y Estado Asíncrono:** `@tanstack/react-query` (TanStack Query) con políticas *stale-while-revalidate* para transiciones instantáneas de pantalla (`useQueries.js`).
- **Estado Global:** `AuthContext.jsx` con persistencia de sesión JWT, detección de rol y permisos por módulo.
- **Estilos y UI Kit:** Tailwind CSS con componentes atómicos (`Button.jsx` con estados de carga y `AlertBanner.jsx` para caídas de servicio).
- **Biometría:** `@digitalpersona/devices` (`useDigitalPersona.js`) comunicándose por loopback local con el lector USB.

## Arquitectura por Features
- `src/features/ehr/modals/`: Subcomponentes modulares de expediente clínico (ej. `AllergiesModal.jsx`).
- `src/features/admin/`: Paneles administrativos de trazabilidad (`AuditLogsTab.jsx`) y gestión de usuarios (`UsersManagerTab.jsx`).
- `src/features/biometrics/`: Modales aislados de firma biométrica (`BiometricSignModal.jsx`).

## Relaciones en el Proyecto
- Consume exclusivamente los endpoints autenticados provistos por el [[Backend]].
- Empaqueta sus assets de producción en `dist/` para ser distribuidos en la fase de [[Pase_a_Produccion]].
