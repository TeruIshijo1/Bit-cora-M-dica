# Evidencia de inyección de fallas

Ejecución: 2026-09-17 sobre PostgreSQL TEST local y datos sintéticos. Resultado
global: incluido en la regresión `139 passed, 10 subtests passed`. Las fallas de
infraestructura se simularon de forma controlada; no se interrumpieron servicios
productivos.

| # | Escenario | Evidencia automatizada | Resultado comprobado |
|---:|---|---|---|
| 1 | PostgreSQL caído | `test_readiness_fails_closed_when_postgresql_is_down` | readiness 503, dependencia identificada, sin secreto ni éxito falso. |
| 2 | SQL Server caído | `test_timeout_is_retryable_and_never_synced` y subpruebas de adaptadores KH | Estado `RETRYABLE_ERROR`, operación durable y no `SYNCED`. |
| 3 | Biometría caída | `test_matcher_transport_failures_are_closed` | Flujo bloqueado sin mutar plantilla, firma ni identidad. |
| 4 | TSA caída | `test_24_tsa_outage_is_pending_not_verified` | `TSA_PENDIENTE`; ECDSA original preservada y nunca marcada verificada. |
| 5 | Timeout SQL Server | `test_nota_urgencias_ambiguous_timeout_requires_controlled_reconciliation`, `test_consent_timeout_never_reports_synced` | Resultado ambiguo queda pendiente/manual, sin confirmación falsa. |
| 6 | Reinicio backend durante operación | `test_restart_before_external_write_leaves_recoverable_pending` | Intención recuperable después de abrir una sesión nueva; sin write externo prematuro. |
| 7 | Pérdida de red | `test_retry_after_timeout_does_not_create_second_operation` | Reintento conserva `operation_id`, backoff y una sola intención. |
| 8 | Doble submit | `test_same_idempotency_key_creates_one_operation` | Una fila y una evidencia de operación. |
| 9 | 20 usuarios concurrentes | `test_twenty_simultaneous_consumers_exactly_one_wins` | 20 consumidores, exactamente uno usa el challenge. |
| 10 | 50 usuarios concurrentes | `test_fifty_concurrent_requests_create_one_intent` | 50 solicitudes, un `operation_id`, exactamente una creación. |
| 11 | Challenge concurrente | misma prueba de 20 consumidores | Consumo atómico PostgreSQL; 19 rechazos correctos. |
| 12 | Idempotency concurrente | misma prueba de 50 solicitudes | Restricción única y recuperación del registro ganador. |
| 13 | Disco sin espacio | `test_disk_failure_does_not_leave_partial_upload` | Excepción explícita y cero archivos parciales. |
| 14 | PDF no generable | `test_pdf_generation_failure_never_returns_a_document` | Se propaga el fallo y no se entrega/crea un PDF aparente. |
| 15 | Respuesta inesperada de Vertical | `test_unexpected_vertical_response_never_reports_success` | Respuesta sin confirmación explícita queda `RETRYABLE_ERROR`, valor nulo. |

La evidencia correlacionable se conserva según el tipo de flujo en
`clinical_sync_operations`/`clinical_sync_attempts`, estado consumido del
challenge, firma/TSA o auditoría append-only. Los tests verifican ausencia de
duplicado, mutación o éxito falso; el runbook de recuperación es
`CONTINGENCIA_OPERATIVA.md`.
