# Contingencia operativa técnica

Este runbook cubre recuperación técnica. No sustituye protocolos clínicos,
formatos manuales, responsables, autorizaciones ni tiempos institucionales;
esas decisiones están marcadas `REQUIERE_PROCEDIMIENTO_HOSPITAL`.

## Regla inicial

1. Confirmar `/health` y `/readiness`; conservar `request_id`, hora y componente.
2. No reintentar manualmente una escritura si existe una operación
   `PROCESSING`, `RETRYABLE_ERROR` o `REQUIRES_RECONCILIATION` sin consultar su
   `operation_id`.
3. No cambiar estados directamente en base de datos. Conservar logs y auditoría.
4. Tras recuperar, ejecutar readiness, reconciliación controlada y comprobar que
   no existan duplicados antes de liberar el flujo.

| Falla | Disponible / bloqueado | Recuperación y comprobación |
|---|---|---|
| Backend | Todo flujo digital queda bloqueado. | `systemd` reinicia automáticamente. Revisar `journalctl -u hes-api`, `/health` y `/readiness`; confirmar migración y que no haya operaciones `PROCESSING` huérfanas. `REQUIERE_PROCEDIMIENTO_HOSPITAL` para continuidad clínica manual. |
| PostgreSQL | Bloquear autenticación, expediente, firma, auditoría y toda escritura. SQL Server no debe usarse por separado. | Recuperar servicio/almacenamiento, validar integridad, migración y backup; ejecutar readiness y conteos. Restaurar sólo con autorización operativa. |
| SQL Server | PostgreSQL, consulta local y evidencia local pueden seguir disponibles; bloquear o dejar pendiente toda función que requiera escritura ERP. Nunca mostrar éxito externo. | Recuperar conectividad, probar STAGING cuando corresponda y ejecutar `backend/scripts/reconcile_clinical_sync.py` en modo controlado. Revisar `PENDING`, `RETRYABLE_ERROR` y `REQUIRES_RECONCILIATION`. |
| Biometría | Bloquear login/firma/enrolamiento biométricos. No aceptar muestras previas ni bypass. | Reiniciar `biometric-service`, comprobar su `/health`, lector y DigitalPersona; emitir challenge nuevo. `REQUIERE_PROCEDIMIENTO_HOSPITAL` para alternativa clínica autorizada. |
| TSA | Firma ECDSA puede quedar `TSA_PENDIENTE`; no presentarla como sello verificado. | Recuperar red/TSA, reintentar sellado sin modificar firma ni payload originales y verificar CMS, cadena, EKU, nonce e imprint. |
| Red | Sesiones y dependencias remotas pueden quedar indisponibles; no asumir que una respuesta perdida equivale a fallo o éxito. | Restablecer red; consultar la operación por idempotency key/`operation_id` antes de reintentar. `REQUIERE_PROCEDIMIENTO_HOSPITAL` para operación desconectada. |
| Cola clinical_sync | Consultas locales no dependientes pueden continuar; bloquear confirmación de efectos ERP y reintentos ambiguos. | Medir estados en `/api/operational/metrics`; reconciliar sólo operaciones seguras. Las ambiguas permanecen `REQUIRES_RECONCILIATION` hasta revisión humana. |
| Disco/capacidad | Bloquear uploads, PDFs, logs y backups que no puedan persistirse de forma atómica. | Liberar capacidad conforme a política, verificar que no existan archivos `.tmp`, repetir únicamente con idempotencia y comprobar hash/registro. |

## Cierre de incidente

- `/readiness` debe estar listo para los componentes obligatorios.
- Confirmar que `clinical_sync_operations` no contiene duplicados y que cada
  operación pendiente conserva un estado recuperable.
- Verificar auditoría append-only, firmas CANONICAL_V2 y hashes de archivos
  afectados.
- Documentar periodo, impacto y decisiones institucionales sin copiar PHI a los
  logs del incidente.
