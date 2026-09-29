# Documentación funcional — Vertical HES

**Sistema:** Hospital Escandón / Vertical HES  
**Fecha de levantamiento:** 23 de septiembre de 2026  
**Alcance:** documentación funcional, navegación, flujos, áreas, usuarios y permisos.  
**Restricción aplicada:** no se crearon, modificaron, firmaron, surtieron, cerraron ni eliminaron registros.

## 1. Resumen ejecutivo

Vertical HES es una plataforma hospitalaria modular. La operación se organiza alrededor de la **atención médica** del paciente y sus relaciones con:

- pacientes y expediente;
- urgencias, consulta externa y hospitalización;
- citas y programación de quirófanos;
- solicitudes, recursos hospitalarios y órdenes de venta;
- cargos, acuerdos, anticipos y estado de cuenta;
- registros médicos, recetas, dietas, estudios y firmas;
- catálogos, configuración, usuarios, reportes e indicadores;
- integración/cachés de ERP y controles técnicos.

La interfaz muestra menús y acciones comunes como **Agregar**, **Acciones**, **Informe/Reporte**, **Formatos**, **Procesos**, **Notificaciones**, búsqueda avanzada, filtros y exportaciones. La visibilidad de una acción en pantalla no sustituye la autorización del backend.

## 2. Módulos funcionales observados

### 2.1 Inicio y módulos operativos

| Módulo | Ruta observada | Función principal | Ramas visibles |
|---|---|---|---|
| Pacientes | `/pages/pt` | Búsqueda, consulta y administración de datos demográficos, identificación, contactos y datos administrativos | búsqueda avanzada, lista/cuadrícula/tarjetas/mapa |
| Censo de atención médica | `/pages/pc` | Consulta transversal de atenciones médicas | filtros por fecha/estatus, vistas de atención |
| Urgencias | `/pages/pn_er` | Gestión de atenciones de emergencia | abierto, altas, cerrado, todos, paquetes, grupos de artículos, usuarios, admisión exprés |
| Consultas médicas | `/pages/pn_mc` | Atención ambulatoria y seguimiento de consulta | abierto, altas, cerrado, todos, tipos de cita, paquetes, Treatment Plans, usuarios, admisión exprés |
| Hospitalización | `/pages/pn_ip` | Gestión de pacientes hospitalizados y su atención | abierto, altas, cerrado, todos, visitantes, paquetes, Treatment Plans, grupos de servicios externos, usuarios, admisión exprés |
| Solicitudes | `/pages/v_pcrq` | Seguimiento de solicitudes ligadas a una atención | solicitudes, devoluciones, cancelaciones, artículos confirmados |
| Órdenes de venta | `/pages/pn_so` | Control de órdenes pendientes/procesadas, importes, acuerdos y referencias de atención | pendiente, procesada, usuarios |
| Citas médicas | `/pages/pn_ap` | Agenda de citas y disponibilidad | profesionales, recurso/facilidad, próximas citas, calendario/lista |
| Programación de quirófanos | `/pages/pcor` | Programación de procedimientos y recursos quirúrgicos | lista/calendario, estatus, cirujano, anestesia y preanestesia |

### 2.2 Componentes complementarios

| Componente | Ruta observada | Propósito |
|---|---|---|
| Monitor de solicitudes pendientes | `/pages/m_nsrq` | Priorizar solicitudes por tiempo pendiente, estado, recurso, unidad de servicio y atención |
| Registros médicos | `/pages/mr` | Catálogo/configuración de formularios y registros clínicos |
| Recursos hospitalarios asignados | `/pages/pn_pcfr` | Ver recursos activos o históricos asignados a una atención |
| Indicadores clave de rendimiento | `/pages/kpds` | Definir conjuntos de datos, periodicidad, formato y umbrales de alerta |
| Tablero | `/pages/kpdb` | Consultar indicadores por año/mes: egresos, ventas por cama, cirugías, laboratorio, ingresos y ocupación |

### 2.3 Menús administrativos y de plataforma

- **Configuración:** unidades hospitalarias, unidades de servicio, recursos, quirófanos, personal, artículos/servicios, grupos, listas de materiales, acuerdos, cargos automáticos, precios, diagnósticos, procedimientos, especialidades, recetas, catálogos auxiliares, sitios, unidades de venta, impuestos y cachés ERP.
- **Datos Maestros:** geografía, DIS/medicamentos, formas, unidades, vías, efectos, indicaciones, contraindicaciones, interacciones, moléculas, alergias y mapeo de artículos/medicamentos.
- **Framework:** objetos, parámetros, conceptos, páginas, controladores, reglas de acceso, controladores de usuario, campos, vistas, acciones, reglas de negocio, workflow, localización e importación de datos.
- **Setup:** licencia, afiliación, contenido del sitio, restricciones de acceso del usuario, repositorio de metadatos, reportes definidos por usuario, integridad de configuración, servicios de base de datos, metadatos, parámetros, conexiones ERP y correo.
- **Honorarios:** hospitalización, pruebas cutáneas, órdenes de servicio, cuentas hospitalarias, consultas, consultas programadas, reportes de servicios, formatos, honorarios médicos, auditoría, catálogo y catálogo de procedimientos.
- **Estadísticos:** confirmación de pacientes; hospitalización y urgencias.
- **Más:** contabilidad, subrogados, reportes, citas, consulta del día, confirmación de pacientes, consultas programadas pagadas/pruebas, recursos humanos, reporte de honorarios y sistemas.

## 3. Flujo transversal de atención médica

```text
Paciente existente o nuevo
        |
        +--> Cita / consulta externa
        +--> Urgencias --> triage y admisión
        +--> Hospitalización --> cama/recurso
        +--> Quirófano --> programación y procedimiento
        |
        v
Atención médica
        |
        +--> Diagnóstico, notas, signos, alergias y antecedentes
        +--> Medicamentos, recetas, dietas y estudios
        +--> Solicitudes --> monitor --> recurso/unidad de servicio
        +--> Cargos, anticipos, acuerdos y orden de venta
        +--> Consentimientos, evoluciones y resumen clínico
        +--> Firma médica / firma asistida
        |
        v
Alta o cierre --> estado de cuenta --> reportes e indicadores
```

## 4. Flujos ramificados y áreas involucradas

### Flujo A — Alta/admisión de paciente

1. Admisión busca al paciente en **Pacientes**.
2. Si existe, se reutiliza el expediente; si no existe, se captura el registro demográfico.
3. Se selecciona el tipo de atención: consulta, urgencias u hospitalización.
4. Se vinculan médico, unidad hospitalaria, recurso, acuerdo/lista de precios y datos del responsable.
5. Se genera la atención médica y, cuando corresponde, cargos automáticos, anticipos u orden de venta.

**Intervienen:** Admisión/recepción, pacientes, caja/contabilidad, médico solicitante y Sistemas.  
**Afecta:** expediente, atención médica, cama/recurso, cargos, orden de venta y reportes.

### Flujo B — Urgencias

```text
Ingreso --> admisión exprés o alta normal --> triage --> atención clínica
                                      |                       |
                                      +--> solicitud/recurso  +--> receta/estudio/dieta
                                                              |
                                      alta médica <------------+
                                           |
                                      cierre/estado de cuenta
```

La pantalla expone estados **Abierto, Altas, Cerrado y Todos**, además de paquetes, grupos de servicios externos, usuarios, notificaciones y procesos.

**Intervienen:** admisión, enfermería, médico, laboratorio/servicios, caja/contabilidad y Sistemas.  
**Permisos sensibles:** alta, cierre, cargos, prescripción y firma.

### Flujo C — Consulta médica y cita

```text
Cita --> profesional/recurso --> consulta abierta --> expediente clínico
  |                                      |
  +--> confirmación/pago                 +--> receta, estudio, solicitud u orden
                                         |
                                      firma / cierre / alta
```

**Intervienen:** agenda, recepción, médico, enfermería, caja/contabilidad y paciente.  
**Afecta:** cita, atención, expediente, órdenes, cargos y disponibilidad del recurso.

### Flujo D — Hospitalización y camas

1. Se crea o vincula una atención de hospitalización.
2. Se asigna un recurso hospitalario/cama y unidad de servicio.
3. Enfermería registra cuidados y seguimiento; el médico registra evolución, diagnósticos y órdenes.
4. Se atienden solicitudes de servicios, medicamentos, estudios, dietas y cargos.
5. Se gestionan visitantes, paquetes, Treatment Plans y servicios externos.
6. Se registra el alta y se libera/actualiza el recurso; posteriormente se cierra la atención y se concilia la cuenta.

**Intervienen:** admisión, enfermería, médico, camas/operación, servicios auxiliares, caja/contabilidad y limpieza.  
**Afecta:** ocupación, recurso/cama, atención, expediente, solicitudes y estado de cuenta.

### Flujo E — Solicitudes, recursos y servicios

```text
Médico/enfermería genera solicitud
        |
        +--> Panel de Solicitudes: abierta, devolución, cancelación, artículos confirmados
        |
        +--> Monitor de pendientes: prioridad por tiempo/estatus
        |
        +--> Asignación de recurso o unidad de servicio
        |
        +--> Confirmación parcial/total --> orden/cargo --> atención
```

**Intervienen:** médico, enfermería, unidad solicitante, unidad ejecutora, almacén/servicios, farmacia si aplica y Sistemas.  
**Nota:** la documentación local describe un flujo de farmacia propuesto; durante el levantamiento no se confirmó un módulo/ruta funcional `/api/farmacia/*`. Debe tratarse como flujo por validar.

### Flujo F — Órdenes de venta y cuenta

1. Una atención o cita genera una orden de venta pendiente.
2. Se relacionan paciente, atención, unidad de servicio, médico, acuerdo, lista de precios, impuestos y referencias.
3. La orden pasa a procesada según el proceso operativo autorizado.
4. Los cargos, anticipos, cancelaciones y estado de cuenta se reflejan en la atención.

**Intervienen:** caja/contabilidad, admisión, unidad de servicio, médico solicitante, convenios/subrogados y Sistemas/ERP.  
**Afecta:** ingresos, facturación/conciliación, cargos clínicos y reportes.

### Flujo G — Quirófano

```text
Solicitud/procedimiento --> programación de quirófano
        |
        +--> paciente, atención, cirujano y recurso
        +--> procedimiento, tipo, fechas y anestesia
        +--> preanestesia/requisitos especiales
        +--> cargos automáticos y comentarios
        |
        +--> ejecución --> actualización de atención y cuenta
```

**Intervienen:** médico/cirujano, coordinación de quirófano, anestesia, enfermería, admisión y caja/contabilidad.  
**Afecta:** disponibilidad de quirófano, atención, cargos, expediente y agenda.

### Flujo H — Expediente y firma

El expediente puede reunir contacto, signos vitales, diagnósticos, alergias, patologías, procedimientos, medicamentos, exámenes, notas, recetas, dietas, consentimientos, historias clínicas, evoluciones, resumen médico y egreso/resumen clínico.

```text
Captura clínica --> revisión --> firma médica/FEA o firma asistida
                                  |
                                  +--> documento/PDF y auditoría
```

**Intervienen:** médico, ayudante autorizado, enfermería, Archivo/Registros Médicos y Sistemas.  
**Controles:** autenticación por rol, revalidación de rol en sesión, firma electrónica avanzada cuando aplica, biometría para el flujo configurado y auditoría append-only.

## 5. Usuarios, áreas y permisos

### 5.1 Perfiles funcionales

| Perfil | Responsabilidad funcional | Acceso/acciones relevantes |
|---|---|---|
| `admin` | gobierno operativo y configuración | acceso transversal; usuarios, catálogos, operación clínica, cierres/autorizaciones y administración |
| `sistemas` | operación técnica y soporte | configuración, integraciones, sincronizaciones, soporte de atención, usuarios y administración autorizada |
| `medico` | atención clínica | consulta de pacientes/atenciones, expediente, agenda, órdenes clínicas, recetas, dietas y firma médica según autorización |
| `ayudante` | apoyo clínico/firma asistida | lectura clínica y funciones de firma asistida dentro del alcance asignado |
| `enfermeria` | operación clínica y cuidados | pacientes, camas/recursos, solicitudes, captura de enfermería y lectura clínica autorizada |
| `rh` | personal y documentación laboral | personal, médicos, documentos/escaneos y funciones de RH |
| `limpieza` | disponibilidad operativa de camas | actualización del estado de limpieza de recursos/camas según permiso |

### 5.2 Matriz resumida de autorización backend

| Capacidad | Admin | Sistemas | Médico | Ayudante | Enfermería | RH | Limpieza |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Administración de usuarios | ✓ | ✓ | — | — | — | ✓ según función | — |
| Pacientes: operación | ✓ | ✓ | lectura clínica | lectura clínica | ✓ | — | — |
| Expediente y captura clínica | ✓ | ✓ según endpoint | ✓ | ✓ según endpoint | ✓ | — | — |
| Prescripción/firma médica | ✓ | —/soporte | ✓ | ✓ asistida | — | — | — |
| Camas y recursos | ✓ | ✓ | ✓ lectura/operación | — | ✓ | lectura según UI | ✓ limpieza |
| Solicitudes y recursos asignados | ✓ | ✓ | ✓ | ✓ según alcance | ✓ | — | — |
| Agenda/citas | ✓ | ✓ | ✓ | ✓ según endpoint | ✓ | lectura/UI según política | — |
| RH/documentos laborales | ✓ | ✓ | — | — | — | ✓ | — |
| Catálogos/configuración | ✓ | ✓ | — | — | — | — | — |
| Reportes/indicadores | ✓ | ✓ | lectura según permiso | lectura según permiso | lectura según permiso | lectura según permiso | — |

La tabla es una vista funcional resumida. La autorización efectiva depende del endpoint, del rol vigente en base de datos y de la configuración `permisos_modulos`; el backend aplica denegación por defecto.

## 6. Ramificaciones de autorización que deben considerarse

1. **UI vs backend:** que un botón aparezca no garantiza que la operación esté autorizada. Validar siempre respuesta del endpoint y rol vigente.
2. **Rol más permisos por módulo:** la plataforma puede tener permisos específicos por módulo además del perfil general.
3. **Lectura vs escritura:** varios perfiles pueden consultar información clínica, pero sólo perfiles clínicos autorizados deben capturar, prescribir o firmar.
4. **Firma:** la preparación del registro y la firma son pasos separados; la firma debe quedar limitada al médico/ayudante autorizado y al mecanismo configurado.
5. **Cierre/alta:** cerrar una atención cambia disponibilidad, cargos, estado de cuenta y reportes; debe ser una operación controlada.
6. **ERP/contabilidad:** órdenes, cargos, acuerdos, precios e impuestos tienen impacto financiero y requieren segregación con caja/contabilidad y Sistemas.
7. **Datos sensibles:** pacientes, diagnósticos, teléfonos, identificaciones, expedientes y firmas requieren mínimo privilegio, trazabilidad y no exportación no autorizada.

## 7. Dependencias y afectaciones por proceso

| Proceso | Áreas primarias | Datos/objetos afectados | Consecuencia si falla |
|---|---|---|---|
| Admisión | recepción, pacientes, Sistemas | paciente, atención, responsable, recurso | atención duplicada o expediente incompleto |
| Urgencias | urgencias, médico, enfermería | triage, atención, cama, órdenes | retraso clínico y cuenta incompleta |
| Consulta/cita | agenda, médico, recepción | cita, atención, expediente | hueco de agenda o consulta sin trazabilidad |
| Hospitalización | admisión, camas, enfermería, médico | cama, atención, cuidados, alta | ocupación incorrecta y riesgo operativo |
| Solicitudes | unidad solicitante/ejecutora | solicitud, artículos, recurso | servicio no atendido o no cargado |
| Quirófano | cirugía, anestesia, enfermería | programación, procedimiento, recurso | choque de agenda o preparación incompleta |
| Expediente/firma | médico, enfermería, archivo, Sistemas | formularios, PDF, firma, auditoría | documento no válido o no disponible |
| Cuenta/orden | caja, contabilidad, convenios, ERP | orden, cargos, anticipos, precios | diferencias financieras |
| Indicadores | dirección, calidad, Sistemas | conjuntos de datos y KPIs | decisiones con datos incompletos |

## 8. Seguridad y trazabilidad

- La sesión usa autenticación por token y revalidación de rol contra la base de datos.
- Existe control de sesión inactiva y revocación de identificadores de sesión.
- La firma electrónica y la biometría deben operar con desafío temporal y sin registrar muestras biométricas, FMD ni tokens en logs.
- El historial de llaves FEA es append-only: una rotación desactiva la llave anterior e inserta la nueva; no se elimina historial.
- La auditoría debe conservar quién creó/modificó, cuándo, y el resultado de los procesos críticos.

## 9. Hallazgos y puntos a validar

- El levantamiento de interfaz confirma la existencia y navegación de los módulos descritos, pero no prueba que cada rol tenga acceso efectivo a cada botón.
- Debe hacerse una matriz de pruebas por rol con cuentas de prueba y datos no productivos.
- Se observan posibles diferencias entre controles visibles y políticas backend: firma exprés, acceso de Sistemas al expediente, agenda para RH y algunos endpoints administrativos. Requieren prueba controlada antes de documentarlos como permiso definitivo.
- El flujo de farmacia está descrito localmente como propuesta y no quedó confirmado como módulo operativo actual.
- No se incluyeron nombres, teléfonos, diagnósticos ni identificadores de pacientes observados en la sesión.

## 10. Procedimiento seguro para futuras validaciones

1. Usar cuenta de prueba por perfil.
2. Consultar únicamente registros anonimizados o sintéticos.
3. Probar navegación, lectura, filtros y reportes sin confirmar formularios.
4. Para cada operación de escritura, detenerse antes de **Guardar**, **Firmar**, **Procesar**, **Surtir**, **Cerrar**, **Borrar** o **Autorizar**.
5. Registrar endpoint, rol, resultado HTTP, pantalla y efecto esperado.
6. Separar permisos de interfaz, permisos de API y permisos de negocio.

## 11. Validación detallada con el caso de prueba indicado

Se consultó únicamente el paciente de prueba proporcionado por el usuario, sin capturar datos nuevos ni ejecutar botones de escritura. Los siguientes resultados son una fotografía funcional de la sesión del **23/09/2026** y pueden cambiar con la operación diaria.

### 11.1 Resumen de relaciones encontradas

| Relación consultada | Resultado observado | Función confirmada |
|---|---:|---|
| Atenciones médicas | 2 abiertas | La ficha del paciente concentra atenciones y permite entrar a sus procesos |
| Citas | 0 | La agenda se consulta desde la ficha, pero no había citas asociadas en ese momento |
| Registros médicos | catálogo visible de 37 tipos | La ficha puede mostrar formularios clínicos configurables |
| Signos vitales | 4 | Seguimiento seriado de fecha, estatus, edad, talla, peso, temperatura, pulso, presión, respiración y saturación |
| Alergias | 2 | Registro de estatus, alergia, fecha de inicio, notas, referencia y auditoría |
| Patologías | 0 | El submódulo existe, sin filas en esta ficha |
| Procedimientos | 0 | El submódulo existe, sin filas en esta ficha |
| Medicamentos | 0 | El submódulo existe, sin filas en esta ficha |
| Exámenes médicos | 1 | Registro de laboratorio con fecha, tipo, descripción, resultado y auditoría |
| Notas del paciente | 0 | El submódulo existe, sin filas en esta ficha |
| Recetas médicas | 0 | El submódulo existe, sin filas en esta ficha |
| Recursos hospitalarios asignados | 0 en el subpanel | La vista directa no devolvió filas durante la consulta |
| Órdenes de atención médica | 43 | Órdenes relacionadas con atención, unidad, recurso, proceso, médico, artículos, estatus y surtido parcial |
| Cargos en atención médica | 25 | Cargos relacionados con recurso, artículo, almacén, orden, cantidad, precio, devolución y auditoría |

### 11.2 Detalle de las atenciones

Las dos atenciones consultadas correspondían a **hospitalización** y estaban en estado **Abierto(a)**. La ficha expone, entre otros, los siguientes datos operativos:

- atención base/principal, cita y fecha;
- recurso hospitalario y unidad hospitalaria;
- alta médica y fechas de entrada/salida;
- evaluación de riesgos, estatus y acuerdos;
- estado de cuenta, anticipos, total y cargos cancelados;
- tipo de paciente, recurrente, diagnóstico, notas y datos del médico;
- responsable/contacto, cotización y auditoría.

Esto confirma que la atención médica es el objeto central que conecta clínica, cama/recurso, solicitudes, órdenes y cuenta.

### 11.3 Historia clínica de urgencias

La ficha mostró un registro clínico de urgencias en estado **Registrado**. El detalle se organiza en las secciones:

- General;
- Motivo de Urgencias;
- Antecedentes Heredofamiliares;
- Antecedentes Personales No Patológicos;
- Antecedentes Personales Patológicos;
- Antecedentes Gineco-obstétricos;
- Notas.

La sección general reutiliza datos de paciente, atención, unidad, recurso y médico. El formulario de motivo contiene campos de accidente/enfermedad/curación y un bloque de signos vitales. Los antecedentes se dividen por familia, hábitos/entorno, antecedentes médicos y gineco-obstétricos. El detalle también muestra auditoría, posibilidad de archivo escaneado y el botón **Firmar Registro**.

### 11.4 Historia clínica de hospitalización

La ficha mostró un registro clínico de hospitalización en estado **Registrado**, asociado a una cama/recurso. Sus secciones son:

- General;
- Antecedentes Heredofamiliares;
- Antecedentes Personales No Patológicos;
- Antecedentes Personales Patológicos;
- Antecedentes Gineco-obstétricos;
- Antecedentes Perinatales;
- Padecimiento Actual;
- Más.

En la lista aparecen **Agregar Borrador** y **Agregar**; en el detalle aparecen **Editar**, **Borrar**, **Cerrar** y **Firmar Registro**. Estas acciones representan estados distintos: borrador/captura, modificación, eliminación, cierre de pantalla y formalización clínica. Durante el levantamiento no se seleccionó ninguna.

### 11.5 Órdenes y cargos

La relación de órdenes contiene campos para:

- número de orden, unidad hospitalaria y atención;
- estatus de orden y de atención;
- recurso hospitalario, unidad de servicio y tipo de proceso;
- paquete y permiso de surtido parcial;
- médico solicitante/tratante, notas y artículos;
- total, documento, fechas de solicitud/toma de muestra y auditoría.

La relación de cargos contiene campos para:

- número de cargo y asignación de recurso;
- artículo, lote, serie, unidad, cantidad y precio;
- devolución y estatus del cargo;
- almacén, orden de atención y línea de orden;
- procedimiento, paquete, acuerdo y cotización;
- cargo automático, referencias y auditoría.

Se observaron órdenes en estados **Confirmado** y **Cancelado**, y cargos en estados **Cargado** y **Devuelto**. Esto confirma una rama de reversa/cancelación independiente de la captura original.

### 11.6 Controles de riesgo observados

En la ficha y en los registros clínicos aparecen controles de **Agregar**, **Agregar Borrador**, **Editar**, **Borrar**, **Cerrar** y **Firmar Registro**. Para mantener el alcance solicitado:

- no se abrió ningún formulario de edición;
- no se creó borrador;
- no se confirmó, canceló ni surtió ninguna orden;
- no se agregó ni devolvió ningún cargo;
- no se borró ni cerró ningún registro;
- no se firmó ningún registro ni se descargó documentación clínica.

### 11.7 Diferencia de consistencia a validar

El subpanel **Asignaciones de Recursos Hospitalarios** no mostró filas en la ficha, mientras que las órdenes y cargos sí contienen referencias a recurso hospitalario y a números de asignación. Esto puede deberse a filtros, alcance de la vista, relación histórica o una inconsistencia de datos. Debe validarse con una cuenta de prueba y una consulta controlada antes de concluir que exista una falla de operación.

## 12. Operación administrativa: cuentas, cargos, paquetes, configuración y Framework

Esta sección concentra el levantamiento solicitado para el área operativa. La fecha de observación de los conteos es **23/09/2026**; los conteos son informativos y no se modificó ningún registro.

### 12.1 Modelo operativo observado

La operación puede entenderse como una cadena de configuración y transacción:

```text
Unidades / servicios / personal
             |
Artículos, servicios, grupos, paquetes y precios
             |
Acuerdos, impuestos, reglas de cargo y recursos
             |
Atención médica -> solicitud -> orden de venta -> cargo
             |                         |
             +------ cuenta / honorarios / auditoría
```

Las áreas de configuración determinan qué puede solicitarse, dónde se presta, cómo se asigna un recurso, qué precio/impuesto/acuerdo aplica y qué información llega a cuenta, honorarios o ERP. La pantalla visible no debe confundirse con autorización real: el Framework, las restricciones por usuario y el backend deben evaluarse conjuntamente.

### 12.2 Cuentas, honorarios y conciliación

El menú **Honorarios** contiene los siguientes reportes operativos observados:

| Función | Ruta | Información/control observado |
|---|---|---|
| Órdenes de servicio | `/Pages/UDR_HON_ORDEN` | Fecha, especialidad, médico, total de consultas y total a pagar; filtros por fecha, especialidad y médico. |
| Cuentas hospitalarias | `/Pages/UDR_HON_Cuentas` | Artículo/servicio, médico, fecha de creación, paciente, cantidad, importe de línea y comisión. |
| Formato de pago médico | `/Pages/UDR_HON_PAGO` | Relación PC/SO, paciente, médico, especialidad, artículo, impuestos, ISR, subtotal, IVA, total, retención, neto y líneas sin tabulador. También verifica cita, orden de venta y coincidencia paciente-médico. |
| Auditoría de pago médico | `/Pages/UDR_HON_PAGO_Audit` | Elegibilidad del renglón, tipo de artículo, grupo de honorarios, inclusión, reglas de pago y motivo de exclusión. |
| Hospitalización | Menú visible, navegación no confirmada | La rama aparece en Honorarios, pero no abrió una vista navegable durante esta sesión; requiere validación específica. |

**Flujo de honorarios y cuenta:**

1. Se configura el artículo/procedimiento, su grupo, precio, impuestos y reglas.
2. Una atención o solicitud genera una orden y, cuando corresponde, cargos.
3. La cuenta hospitalaria concentra renglones, médico, artículo, cantidad, importe y comisión.
4. El reporte de pago cruza la cuenta/PC contra la orden/SO, cita, paciente, médico y tabulador.
5. Auditoría clasifica el renglón como elegible o excluido y conserva el motivo.
6. Cualquier diferencia debe resolverse en configuración, captura u origen operativo antes del pago; no debe corregirse directamente en el reporte.

### 12.3 Órdenes de venta, cargos y reversas

En `/pages/pn_so` se observó el **Panel de Órdenes de Venta**, con pestañas **Pendiente**, **Procesada** y **Usuarios**. La vista pendiente reportó 190 registros al momento de la consulta. Sus campos relacionan número y estatus de la orden, atención médica, unidad hospitalaria, unidad de servicio, médico, paciente, acuerdo, lista de precios, subtotal, impuestos, total, vigencia, cita, receta, factura y auditoría.

La rama operativa se divide así:

- **Captura:** se seleccionan atención, paciente, servicio/artículo, acuerdo y precio.
- **Validación:** se revisan disponibilidad, cita, autorización, vigencia, impuestos y reglas de la unidad.
- **Procesamiento:** la orden pasa de borrador/pendiente a procesada según el flujo configurado.
- **Cargo:** el artículo o servicio se refleja en cuenta, con cantidad, unidad, precio, lote/serie cuando aplica y referencia de orden.
- **Reversa:** cancelación de orden o devolución de cargo; debe conservar relación con el origen y auditoría.
- **Conciliación:** cuenta, honorarios, factura y ERP deben coincidir en importe, impuesto, paciente, médico y convenio.

No se ejecutaron confirmaciones, cancelaciones, surtidos, devoluciones, facturación ni acciones masivas.

### 12.4 Paquetes, artículos y servicios

El catálogo `/pages/v_it` mostró **5,237 artículos y servicios** y las pestañas **Artículos incluidos**, **Artículos excluidos** y **Grupos de artículos similares**. Los campos observados cubren código/descripción, grupo, tipo, unidad de medida, costo, moneda, banderas de compra/venta/inventario, lotes, series, ensamble, alias de servicio, impuestos, CPT y habilitación.

El catálogo `/pages/itgr` mostró **37 grupos de artículos**. Incluye banderas que cambian la operación: grupo de prescripción, procedimiento quirúrgico y estudio de laboratorio. Por tanto, un artículo puede ramificarse a farmacia/receta, quirófano, laboratorio, inventario, cuenta o honorarios según su grupo y sus banderas.

La pantalla `/pages/bm` (**Lista de materiales**) existe como punto de configuración de listas de materiales/paquetes, pero sus columnas no cargaron en la consulta. Se documenta como dependencia confirmada, no como una estructura de paquete ya validada. La pantalla `/pages/pn_ac` muestra ramas de cargos automáticos, entre ellas **Reglas de Atención Médica**, **Reglas para Totales de Cuenta**, **Reglas de Artículos**, **Reglas de Artículos Recurrentes**, **Cargos Referenciados**, **Artículos no facturables**, **Cargos de Recursos**, **Cargos Extraordinarios** y **Días Festivos**. Las ramas de totales y paquetes no cambiaron de vista mediante navegación de consulta, por lo que su ruta/perfil efectivo debe validarse con el responsable de configuración.

### 12.5 Recursos, camas, quirófanos y cargos automáticos

`/pages/pn_fr` mostró **189 recursos hospitalarios** y `/pages/pn_or` **5 quirófanos**. Estos módulos concentran:

- unidad hospitalaria, recurso, tipo, estado y capacidad;
- asignación automática o manual, exclusividad y disponibilidad;
- cama/UCI/quirófano, unidad de servicio y almacén;
- médico, citas, tipo de cita y ventanas de horario;
- tipo de cargo, cortesía, tolerancias del primer/último cargo y cargos recurrentes;
- proyecto y segmentos de costo 1 a 5;
- kits de cirugía y usuarios en la configuración de quirófanos.

`/pages/pcfr` mostró **54 recursos activos** en asignaciones. La asignación relaciona atención, paciente, recurso, unidad solicitante, procedimiento, fechas, estado, capacidad, cargos automáticos, cancelación automática, comentarios y auditoría.

**Ramas de impacto:**

- recurso asignado + cargo automático habilitado -> puede generar cargos por uso o permanencia;
- recurso con cortesía/tolerancias -> cambia el importe o el momento del cargo;
- capacidad/ventana/cita -> afecta agenda, orden y disponibilidad;
- quirófano + kit + grupo quirúrgico -> afecta programación, materiales y cuenta;
- almacén/lote/serie -> afecta surtido, inventario y trazabilidad.

### 12.6 Acuerdos, precios, impuestos y unidades operativas

`/pages/ag` mostró **48 acuerdos** con pestañas **Acuerdos**, **Reglas de Cargo** y **Usuarios**. Los campos observados cubren socio de negocios, lista de precios, impuesto, modo de cargo, cargos administrativos, descuentos, factor de precio, deducible, copago, autorización expresa, mínimo base, documento, estado y relaciones con atención y orden de venta.

Los catálogos complementarios observados son:

| Catálogo | Ruta | Impacto operativo |
|---|---|---|
| Unidades hospitalarias | `/pages/fc` | Define sitio, unidad de venta, impuestos por defecto, series, proyecto, segmentos de costo, servicio/personal/paciente por defecto y capacidad. |
| Unidades de servicio | `/pages/su` | Define almacenes, impuestos de facturación, selección de lote, solicitudes, cargos permitidos, unidad solicitante, series y segmentos de costo. Se observaron 11. |
| Unidades de venta | `/pages/slun` | Punto de configuración existente; no mostró registros en esta consulta. |
| Impuestos auxiliares | `/pages/tx` | Catálogo existente; no mostró registros en esta consulta. |
| Reglas de impuestos por sucursal | `/pages/brtx` | Punto de aplicación fiscal por sucursal; no mostró registros en esta consulta. |
| Precios especiales | `/pages/bpsp` | Punto de reglas de precio especial; la vista no expuso renglones en esta consulta. |
| Personal | `/pages/pr` | Mostró 262 personas y relaciona médico, especialidad, usuario, recurso, citas, recetas, socio de negocios, tipo de médico, ISR e IVA. |

El flujo operativo esperado es: unidad hospitalaria y servicio determinan contexto; acuerdo/lista de precios determina precio y participación del paciente; artículo y regla determinan impuesto/cargo; personal y recurso determinan responsable y disponibilidad; la atención/orden lleva los valores a cuenta y reportes.

### 12.7 Framework: control de metadatos, reglas y permisos

El menú **Framework** funciona como plano de control de la aplicación, no como un catálogo clínico. Se observaron estas familias:

- **Modelo:** `MD_DBObjects`, `MD_Parameters`, `MD_Concepts`, `MD_Pages`.
- **Controladores:** `MD_Controllers`, `MD_UControllers`, comandos, campos, vistas, categorías y lookups.
- **Acciones y reglas:** `MD_UControllerActions`, `MD_UControllerBusinessRules`, grupos de acción, acciones y reglas de negocio.
- **Seguridad:** `MD_ControllerAccessRules`, `MD_AccessControlRules`, registro de controladores y restricciones de acceso.
- **Extensibilidad:** campos/tablas definidas por usuario, reportes, etiquetas, localización y plantillas de importación.
- **Procesos:** `WF` (**Workflow Manager**) con campos de estado, reglas y grupos.

`MD_UControllerActions` mostró 8 definiciones con comando, validación, atajo, datos, confirmación, clase CSS y roles. `MD_UControllerBusinessRules` mostró 7 reglas con tipo, fase, script y habilitación. Estos registros explican por qué una acción puede aparecer, pedir confirmación, validar condiciones o quedar oculta; no deben editarse durante una revisión funcional.

### 12.8 Setup: operación de plataforma e integraciones

En **Setup** se observaron los siguientes controles:

- `/pages/khun` **User Access Restrictions**: capa de restricciones específicas por usuario.
- `/pages/v_kh_integrity` **Configuration Integrity Check**: revisión de integridad/consistencia de configuración.
- `/pages/pn_db` **Database Services Panel**: SQL Server Agent en estado **Running** y **2 jobs activos**, con historial de inicio, fin, duración y mensaje.
- `/Pages/Parameters` **Parameters**: 8 parámetros globales con identificador y valor.
- `/Pages/ERPConnections` **ERP Connections**: 1 conexión configurada, con campos de sesión, servidor, base, tipo de base y credenciales. La pantalla expone etiquetas de contraseña; no se leyeron, exportaron ni modificaron valores.
- `/Pages/MD`, `/Pages/MD_Views` y `/Pages/MD_Messages`: administración de metadatos, vistas y mensajes.
- Licencia, afiliación, contenido del sitio, repositorio de metadatos, UDR y servicios de correo: componentes transversales de plataforma.

**Permiso operativo recomendado:** Setup, Framework, conexión ERP, parámetros, jobs y reglas de cargos deben limitarse a Sistemas/administración de plataforma. Los operadores pueden consultar sus módulos y reportes, pero no deberían editar el plano de control sin control de cambios, respaldo, revisión y trazabilidad.

### 12.9 Matriz operativa de áreas y permisos

| Proceso | Áreas que intervienen | Permisos que debe comprobarse que intervienen | Efectos aguas abajo |
|---|---|---|---|
| Catálogo de artículos/servicios | Compras, almacén, facturación, clínica | Alta/edición de catálogo; consulta operativa | Solicitudes, órdenes, inventario, impuestos, cuenta y honorarios. |
| Paquete/kit/lista de materiales | Quirófano, almacén, facturación, configuración | Configurar estructura; surtir; devolver; consultar | Consumo de materiales, cargos, recursos y cuenta. |
| Acuerdo/precio/impuesto | Convenios, caja, facturación, administración | Configurar acuerdo/regla; aplicar; autorizar excepciones | Precio, copago, deducible, impuestos, factura y cobranza. |
| Recurso/cama/quirófano | Admisión, enfermería, quirófano, agenda | Asignar/cancelar; definir cargos automáticos; consultar | Capacidad, agenda, estancia, cargos recurrentes y expediente. |
| Orden de venta | Médico/solicitante, unidad de servicio, almacén, caja | Capturar; validar; procesar/cancelar; surtir | Cargo, inventario, cita, receta, cuenta y auditoría. |
| Honorarios | Finanzas, cuentas por pagar, médicos, auditoría | Consultar, conciliar, auditar y autorizar pago | Pago bruto, impuestos, retenciones, neto y exclusiones. |
| Usuarios y acceso | Sistemas, RH, responsables de área | Crear/editar usuario, rol, restricción y módulo | Visibilidad de menús, acciones permitidas y datos accesibles. |
| Framework/Setup | Sistemas/administración técnica | Cambiar metadatos, reglas, workflows, jobs o ERP | Puede alterar transversalmente todos los módulos. |

### 12.10 Hallazgos y pendientes operativos

1. Hay una separación clara entre configuración maestra, operación transaccional y reportes de conciliación.
2. El reporte de pago médico contiene controles de trazabilidad suficientemente detallados para detectar diferencias entre cuenta, orden, cita, médico, impuestos y tabulador.
3. La existencia de cargos automáticos, recurrentes, de recursos, extraordinarios y no facturables indica que la cuenta no depende únicamente de la captura manual.
4. Paquetes/listas de materiales y reglas de cargos están visibles, pero no se pudo confirmar su detalle desde navegación de consulta en esta sesión; no se debe inferir su comportamiento definitivo sin un perfil de configuración autorizado.
5. La presencia de credenciales en los campos de ERP exige revisión de segregación de funciones, enmascaramiento y gestión de secretos.
6. Los conteos y estados observados son una fotografía de la sesión; para una matriz formal de permisos se requiere repetir la navegación con usuarios representativos de Sistemas, RH, caja/cuentas, almacén, enfermería, médico, quirófano y auditoría.
7. Debe validarse por rol si las acciones de pantalla coinciden con la autorización del backend; la visibilidad de un botón no prueba que la operación esté autorizada.

### 12.11 Cómo interpretar nombres de pantalla, controladores y tablas

Se identificaron cuatro niveles de nombres. Mantenerlos separados evita confundir una pantalla con una tabla física:

| Nivel | Ejemplo | Qué significa |
|---|---|---|
| Nombre visible | **Artículos y Servicios** | Etiqueta funcional para el usuario. |
| Ruta de pantalla | `/pages/v_it` | Identificador de navegación/página. |
| Controlador o vista | `IT`, `AG`, `AGPK`, `V_PCRQ`, `UDR_HON_PAGO` | Entidad de Framework, vista operativa o reporte. |
| Objeto de datos | `VERP_IT`, `CERP_IT`, `ERP_IT`, `OITM` | Vista/cache o tabla fuente; sólo se considera confirmado cuando aparece en metadatos o definición SQL. |

La pantalla **MD DB Objects** mostró 113 objetos y, en la parte operativa visible, vistas `VERP_*` que se definen sobre objetos `CERP_*`. Las definiciones ERP también muestran fuentes `ERP_*` y, para listas de materiales, `OITT`, `ITT1` y `OITM`. Esto confirma la existencia del puente técnico hacia ERP, pero no implica que todas las pantallas administrativas escriban directamente en esas tablas.

### 12.12 Matriz de correspondencia funcional-técnica

La siguiente matriz junta el nombre que ve el usuario con el identificador que aparece en la plataforma y el objeto de datos que pudo confirmarse o relacionarse. **“Probable”** indica una relación por ruta/controlador/campo; **“no confirmado”** significa que no se afirmó una tabla física sin verla en metadatos o SQL.

| Área visible | Ruta | Controlador/reporte observado | Objeto o fuente de datos | Áreas y módulos afectados |
|---|---|---|---|---|
| Pacientes | `/pages/pt` | `PT` | Entidad/controlador PT; tabla física Vertical no confirmada en MD DB Objects | Admisión, expediente, atención, citas, cuenta y facturación. |
| Censo / atención | `/pages/pc` | `PC` | Entidad/controlador PC; las acciones usan `PC_ST` | Admisión, alta, atención, cuenta y honorarios. |
| Personal | `/pages/pr` | `PR` | Entidad/controlador PR; reglas normalizan nombre y validan datos | RH, médicos, agenda, recetas y honorarios. |
| Citas | `/pages/pn_ap` | `PRSC`, `V_PRSC`, `PCAP` | Vistas/controladores de cita; reglas usan `PCAP_ST` y procedimiento `_KH_PCAP_AT` | Agenda, caja, médico, paciente y atención. |
| Solicitudes | `/pages/v_pcrq` | `V_PCRQ` | Vista/proceso `PCRQ`; regla llama `_KH_PCPR_PR` | Unidades de servicio, almacén, médico, atención y cargos. |
| Órdenes de venta | `/pages/pn_so` | `SO`, `DLG_WF_SO` | Capa de orden de venta; relación ERP documental por validar con `VERP_DC`/`VERP_DCLN` | Médico, servicio, almacén, caja, cuenta, factura y honorarios. |
| Cargos automáticos | `/pages/pn_ac` | Familias `AC*`/`ACT*` visibles en MD Controllers | Reglas de aplicación; objeto físico no confirmado | Atención, recursos, cuenta, paquetes, días festivos y facturación. |
| Acuerdos | `/pages/ag` | `AG` (`Agreements`) | Controlador AG; hijos `AGITEX`, `AGITGR`, `AGITIN`, `AGPK`, `AGPL`, `AGPR` | Convenios, precios, copagos, deducibles, impuestos y órdenes. |
| Paquetes de acuerdos | Rama en `/pages/ag` | `AGPK`, `AGPKITEX`, `AGPKITGR`, `AGPKITIN` | Controladores de paquete y artículos de paquete; tabla física no confirmada | Convenios, paquetes, artículos incluidos/excluidos y cuenta. |
| Artículos y servicios | `/pages/v_it` | `IT` | `VERP_IT` / `CERP_IT`; fuente ERP `ERP_IT` | Catálogo, inventario, cargos, recetas, laboratorio y quirófano. |
| Grupos de artículos | `/pages/itgr` | `ITGR` | `VERP_ITGR` / `CERP_ITGR`; fuente `ERP_ITGR` | Prescripción, cirugía, laboratorio, inventario y honorarios. |
| Lista de materiales | `/pages/bm` | `BM` | `VERP_BM` / `CERP_BM`; fuente ERP `OITT`, `ITT1`, `OITM` | Paquetes/ensambles, almacén, quirófano, cargos e inventario. |
| Precios especiales | `/pages/bpsp` | `BPSP` | `VERP_BPSP` / `CERP_BPSP`; fuente `ERP_BPSP` | Convenios, socios de negocio, listas de precios y cuenta. |
| Listas de precios | Referenciada por `/pages/ag` y artículos | `PL`, `ITPL` | `VERP_PL`/`CERP_PL` y `VERP_ITPL`/`CERP_ITPL`; fuentes `ERP_PL`/`ERP_ITPL` | Precio base, factor, moneda, impuestos y venta. |
| Unidades hospitalarias | `/pages/fc` | `FC` por identificador de ruta | Datos operativos de sitio/unidad; tabla física no confirmada | Contexto de atención, ventas, series, impuestos, capacidad y costos. |
| Unidades de servicio | `/pages/su` | `SU` por identificador de ruta | Datos operativos de servicio; tabla física no confirmada | Solicitudes, cargos, almacenes, lotes, impuestos y costos. |
| Recursos hospitalarios | `/pages/pn_fr` | Familia `FR`/recursos; nombre exacto por controlador pendiente | Datos operativos de recursos; tabla física no confirmada | Cama, UCI, quirófano, citas, capacidad y cargos recurrentes. |
| Asignaciones de recursos | `/pages/pcfr` | Familia `PCFR` probable | Asignación de atención/recurso; tabla física no confirmada | Paciente, atención, recurso, cargos automáticos y auditoría. |
| Quirófanos | `/pages/pn_or` | Familia `OR` probable | Configuración de quirófano/kit; tabla física no confirmada | Cirugía, agenda, recursos, paquetes, almacén y cuenta. |
| Impuestos | `/pages/tx`, `/pages/brtx` | `TX`, reglas de sucursal | `VERP_TX`/`CERP_TX`, `VERP_TXDT`/`CERP_TXDT`; fuentes `ERP_TX`/`ERP_TXDT` | Venta, compra, cuenta, IVA, retenciones y facturación. |
| Sucursales | `/pages/fc`, `/pages/brtx` | `BR` | `VERP_BR`/`CERP_BR`; fuente `ERP_BR` | Impuesto, unidad de venta, series y operación por sitio. |
| Almacenes y ubicaciones | Configuración/ERP cache | `WH`, `WHBN` | `VERP_WH`/`CERP_WH`, `VERP_WHBN`/`CERP_WHBN`; fuentes `ERP_WH`/`ERP_WHBN` | Surtido, lotes, series, paquetes, devoluciones y costo. |
| Socios de negocio | Acuerdos/ERP cache | `BP`, `BPGR` | `VERP_BP`/`CERP_BP`, `VERP_BPGR`/`CERP_BPGR`; fuentes `ERP_BP`/`ERP_BPGR` | Pacientes pagadores, convenios, crédito, precio e impuestos. |
| Series documentales | ERP cache | `SR` | `VERP_SR`/`CERP_SR`; fuente `ERP_SR` | Series de órdenes, cargos, documentos y trazabilidad. |
| Proyecto y centros de costo | Recursos/unidades | `PJ`, `CC` | `VERP_PJ`/`CERP_PJ`, `VERP_CC`/`CERP_CC`; fuentes `ERP_PJ`/`ERP_CC` | Contabilidad, costos, recursos, unidades y reportes. |
| Documentos ERP | Operación/ERP | `DC`, `DCLN` | `VERP_DC`/`CERP_DC`, `VERP_DCLN`/`CERP_DCLN`; fuentes `ERP_DC`/`ERP_DCLN` | Entradas/salidas, transferencias, líneas, inventario y costos. |
| Honorarios | Menú Honorarios | `UDR_HON_ORDEN`, `UDR_HON_CUENTAS`, `UDR_HON_PAGO`, `UDR_HON_PAGO_Audit` | UDR/reportes y campos PC/SO; no son tablas físicas por sí mismos | Médicos, cuentas por pagar, auditoría, impuestos y contabilidad. |
| Framework | `/Pages/MD_*` | `MD_Controllers`, `MD_UControllerActions`, `MD_UControllerBusinessRules` | Metadatos del Framework; no equivale a una sola tabla operativa | Todas las áreas, según controlador, vista, acción y regla. |

### 12.13 Objetos ERP/cache confirmados en MD DB Objects

El catálogo técnico mostró estas familias. El prefijo `VERP_` es la vista que la plataforma genera/consulta; `CERP_` aparece como objeto cacheado o de integración; `ERP_*` aparece como fuente ERP en definiciones de sincronización. La lectura de estas definiciones fue únicamente informativa.

| Vista `VERP_*` | Fuente/cache asociada | Alcance funcional |
|---|---|---|
| `VERP_BM` | `CERP_BM`; ERP `OITT`/`ITT1`/`OITM` | Ensambles y lista de materiales. |
| `VERP_BP`, `VERP_BPGR` | `CERP_BP`, `CERP_BPGR` | Socios de negocio y grupos. |
| `VERP_BPSP` | `CERP_BPSP` | Precios especiales por socio/artículo. |
| `VERP_BR` | `CERP_BR` | Sucursales. |
| `VERP_CC`, `VERP_PJ` | `CERP_CC`, `CERP_PJ` | Centros de costo y proyectos. |
| `VERP_CO` | `CERP_CO` | Compañía, moneda e impuestos por defecto. |
| `VERP_CU`, `VERP_CUXR` | `CERP_CU`, `CERP_CUXR` | Monedas y tipos de cambio. |
| `VERP_IT`, `VERP_ITBC`, `VERP_ITGR` | `CERP_IT`, `CERP_ITBC`, `CERP_ITGR` | Artículos, códigos de barras y grupos. |
| `VERP_ITPL`, `VERP_PL` | `CERP_ITPL`, `CERP_PL` | Precios por artículo y listas de precios. |
| `VERP_SR` | `CERP_SR` | Series documentales. |
| `VERP_TX`, `VERP_TXDT` | `CERP_TX`, `CERP_TXDT` | Impuestos y reglas/detalle fiscal. |
| `VERP_WH`, `VERP_WHBN` | `CERP_WH`, `CERP_WHBN` | Almacenes y ubicaciones. |
| `VERP_DC`, `VERP_DCLN` | `CERP_DC`, `CERP_DCLN` | Tipos de documento y líneas de documento. |

Estos objetos explican la conexión entre **artículo → grupo → almacén → precio → impuesto → documento → costo**. La conexión ERP se administra desde Setup y sus credenciales no deben ser visibles para operadores funcionales.

### 12.14 Permisos observados en Framework y backend local

El Framework expuso evidencia de permisos más específica que un simple menú:

- `MD_Controllers` mostró 769 controladores con columnas **Controller Name**, **Label**, **In DB** y **System Controller**.
- `MD_UControllerActions` mostró 8 acciones con condición, confirmación, comando y campo **Roles**.
- La acción `PC_OP / Cancelar Alta Paciente` tiene condición `AllowChanges != false && PC_ST == 'PD'` y roles `Administrators,cierre_cuentas`.
- La acción `PTMT_CA / Cancelar Registro` tiene roles `Administrators,Permisos`.
- La acción `DLG_WF_SO / Generar Cita` muestra confirmación y condición relacionada con factura pagada.
- Algunas acciones de cita aparecen como **Deactivated**, por lo que no deben considerarse disponibles aunque sigan registradas en metadatos.
- `MD_UControllerBusinessRules` mostró reglas JavaScript/SQL asociadas a pacientes, médicos, solicitudes, citas y anticipos; varias invocan procedimientos `dbo._KH_*`. No se ejecutaron.
- `User Access Restrictions` (`/pages/khun`) añade una capa de restricción individual.
- `MD_ControllerAccessRules` y `MD_AccessControlRules` existen, pero no mostraron filas en la consulta; eso no demuestra que no existan reglas efectivas en otra capa.

El código local del proyecto Bitácora HES aporta una segunda matriz de autorización, que debe mantenerse separada de los nombres de rol del Framework Vertical:

| Rol del backend local | Alcance documentado |
|---|---|
| `admin`, `sistemas` | Administración técnica, usuarios, permisos, reconciliación, autorizaciones y configuración sensible. |
| `admin`, `rh`, `sistemas` | Personal/médicos, catálogos administrativos y operaciones de RH. |
| `admin`, `sistemas`, `enfermeria` | Alta/actualización/sincronización de pacientes y operaciones de atención. |
| `admin`, `sistemas`, `medico`, `ayudante`, `enfermeria` | Lectura clínica y registros clínicos según ruta. |
| `admin`, `medico`, `ayudante` | Prescripción, firma médica y acciones exclusivas del personal médico. |
| `admin`, `sistemas`, `limpieza` | Limpieza/estado de camas. |
| `admin`, `rh` | Escaneos y documentación de RH. |
| `cierre_cuentas`, `Administrators`, `Permisos` | Roles observados en acciones del Framework Vertical; no se debe asumir equivalencia automática con `admin`, `sistemas` o `rh`. |

### 12.15 Alcance por área y puntos de control

| Área responsable | Puede intervenir en | Debe controlar especialmente | Afecta a |
|---|---|---|---|
| Sistemas / administración técnica | Framework, Setup, usuarios, restricciones, ERP, jobs, integridad y reglas | Segregación de funciones, secretos, respaldos, cambios y auditoría | Toda la plataforma. |
| RH | Personal, médicos, usuarios relacionados, documentos RH y datos fiscales del personal | Identidad, estatus activo, especialidad, tipo de médico, ISR/IVA y permisos | Agenda, recetas, honorarios, firmas y reportes. |
| Admisión / recepción | Paciente, atención, cita, unidad y alta administrativa | Identidad, acuerdo, pagador, cita, recurso y estado de atención | Expediente, orden, cuenta y capacidad. |
| Enfermería | Paciente, cama/recurso, signos y registros de atención | Asignación, disponibilidad, cambios de cama y datos clínicos | Hospitalización, cargos de recurso, expediente y egreso. |
| Médico / ayudante | Solicitudes, órdenes, agenda, expediente y firma según rol | Médico solicitante, indicación, cita, firma, paciente y autorización | Laboratorio, farmacia, quirófano, cuenta y honorarios. |
| Unidades de servicio | Solicitudes, surtido/proceso, artículos y cargos | Lote, serie, disponibilidad, unidad solicitante y devolución | Inventario, cargos, cuenta y orden. |
| Almacén / farmacia | Artículos, lotes, series, paquetes, surtido y devolución | Existencias, almacén, unidad de medida y trazabilidad | Órdenes, cargos, costos y cuenta. |
| Quirófano | Programación, recursos, kits y procedimientos | Capacidad, kit, paquete, consumo y cargos automáticos | Agenda, inventario, cuenta y honorarios. |
| Convenios / caja / cuentas | Acuerdos, listas, copagos, deducibles, precios y cuenta | Precio aplicado, impuestos, autorización, factura y saldo | Paciente, orden, cargos, contabilidad y cobranza. |
| Finanzas / honorarios | Conciliación, auditoría y pago médico | PC/SO, tabulador, IVA, ISR, exclusiones y neto | Médicos, cuentas por pagar y contabilidad. |
| Auditoría | Revisión de estados, exclusiones, cancelaciones, devoluciones y trazas | Motivo, usuario, fecha, origen y reversa | Todas las áreas con operación transaccional. |

### 12.16 Flujos ramificados con permiso y efecto

1. **Configuración:** Sistemas define unidad, servicio, artículo, grupo, paquete, acuerdo, impuesto y recurso. Si falla un catálogo, la operación clínica puede continuar visualmente, pero la orden/cuenta puede quedar sin precio, impuesto, almacén o cargo correcto.
2. **Solicitud:** médico o unidad solicitante selecciona servicio/artículo y contexto de atención. La solicitud puede activar reglas de autorización, cita, disponibilidad o surtido.
3. **Orden:** la orden se crea como pendiente/borrador, se valida y puede procesarse, cancelarse o quedar sin surtir. Cada rama afecta cargos, inventario, cuenta y auditoría.
4. **Cargo:** puede ser manual, automático, recurrente, de recurso, extraordinario, referenciado o no facturable. La regla aplicada determina si aparece en cuenta y honorarios.
5. **Paquete:** un acuerdo puede incluir/excluir artículos o un kit puede descomponerse en materiales; esto modifica consumos, existencias y renglones de cuenta.
6. **Cuenta:** se consolidan artículos, servicios, médico, acuerdo, impuestos, descuentos, copagos y pagos. La corrección debe hacerse en el origen autorizado, no editando el reporte final.
7. **Honorarios:** se cruza cuenta/PC con orden/SO, cita, médico, tabulador y retenciones. El renglón puede ser elegible o excluido con motivo de auditoría.
8. **ERP/contabilidad:** documento, líneas, almacén, impuestos, proyecto y costos se envían/consultan según integración. Una falla de ERP debe quedar como incidencia/reconciliación, no resolverse con cambios manuales no auditados.

### 12.17 Límites de confirmación y siguiente nivel de precisión

Quedaron confirmados por interfaz y metadatos los nombres de rutas, reportes, controladores y familias ERP anteriores. Todavía no se debe afirmar el nombre físico de las tablas internas de **acuerdos, cargos automáticos, recursos, asignaciones, cuentas hospitalarias y honorarios**, porque sus pantallas no expusieron una definición SQL directa en la consulta realizada. Los reportes `UDR_HON_*` son reportes/vistas de usuario, no tablas por sí mismos.

Para cerrar una matriz con certeza de base de datos se necesita una consulta de sólo lectura al catálogo técnico completo del Framework/SQL Server, relacionando cada controlador con su objeto `MD DB Object`, vista y tabla fuente. Para cerrar la matriz de permisos efectiva se necesita repetir la navegación con cuentas representativas de Sistemas, RH, cuentas/caja, almacén, enfermería, médico, quirófano y auditoría. La sesión actual sólo demuestra el alcance visible del usuario autenticado y las reglas consultadas; no sustituye esa prueba por rol.

## 13. Cómo extender el formulario de Atención Médica

### 13.1 Qué formulario es el de la imagen

La pantalla mostrada corresponde al controlador **PC** (Patient Care/Atención Médica), específicamente a las vistas:

- `PCcreateForm1` — formulario **New Patient Care**;
- `PCeditForm1` — formulario **Review Patient Care**;
- `PCgrid1` — listado de atenciones;
- `PCgrid_IP` — listado de hospitalización;
- `PCgrid_ER` — listado de urgencias.

La configuración de `MD_UControllerViews` confirma que el formulario de atención maneja, entre otros, `PTNum`, `FCCode`, `PCNum`, `PCNumRef`, `PTName`, `AllergiesMessage`, `Age`, `PatientType`, `Recurring`, `Assessment`, `TriageLevel`, `DXCode` y varios campos `UDF_*`.

En la pantalla de la imagen se observan campos de tres clases:

1. **Datos base de la atención:** unidad hospitalaria, número de atención, paciente, edad, tipo de paciente, recurso y alta.
2. **Datos operativos de la atención:** cita, evaluación de riesgos, cargos automáticos de recursos y estado de cuenta.
3. **Campos definidos por usuario:** diagnóstico presuntivo, motivo de ingreso, accidente, aviso al Ministerio Público, fechas y datos adicionales.

### 13.2 Mecanismos disponibles para agregar información

| Necesidad | Mecanismo correcto | Resultado |
|---|---|---|
| Un dato simple por atención | `MD_UDF` con controlador `PC` | Crea un campo persistente de atención, por ejemplo texto, fecha, booleano, entero, decimal o firma. |
| Mostrar el campo en alta/edición | `MD_UControllerViews` + `MD_UControllerViewFields` | Agrega el campo a `PCcreateForm1`, `PCeditForm1` o ambos, define alias, orden, visibilidad y comportamiento. |
| Crear una sección visual | `MD_UControllerViewCategories` | Agrupa campos en una pestaña/sección del formulario; debe ligarse a la vista y categoría correcta. |
| Lista de opciones controlada | `MD_Concepts` + `MD_FieldLookups` o configuración de lookup del campo | Evita texto libre y permite catálogo, búsqueda, validación y valores consistentes. |
| Dato repetible o varias líneas | `MD_UController`/`User Defined Tables` (`/Pages/UT`) | Crea un detalle relacionado con la atención; es preferible para múltiples contactos, eventos o registros. |
| Valor calculado o validación | `MD_UControllerBusinessRules` | Calcula, normaliza, bloquea o valida en fases como Before, After, Execute o Calculate. |
| Acción adicional | `MD_UControllerActions` + comandos | Agrega un botón/proceso, con confirmación, condición y roles; no debe usarse sólo para simular un campo. |
| Seguridad por área | `Roles`, `Write Roles`, `MD_ControllerAccessRules`, `MD_AccessControlRules`, `User Access Restrictions` | Separa quién ve, captura, edita, autoriza o sólo consulta el dato. |
| Mostrarlo en reportes o PDF | UDR, vistas de reporte o formato correspondiente | El dato del formulario no aparece automáticamente en reportes, honorarios, cuenta o PDF. |

### 13.3 Campos PC ya definidos por usuario

`MD_UDF` mostró 38 campos definidos por usuario. En el controlador `PC` ya existen, entre otros:

| Campo | Etiqueta | Tipo observado | Uso/condición observada |
|---|---|---|---|
| `UDF_DIAGNOSTICO_PRESUNTIVO` | Diagnóstico Presuntivo | String | Captura diagnóstica de la atención. |
| `UDF_MOTIVO_INGRESO` | Motivo de Ingreso | String | Controla condiciones de otros campos. |
| `UDF_LUGAR_ACCIDENTE` | Lugar del Accidente | String | Se muestra para ciertos motivos de ingreso. |
| `UDF_DIRECCION_ACCIDENTE` | Dirección del Accidente | String | Se muestra para ciertos motivos de ingreso. |
| `UDF_FECHA_ACCIDENTE` | Fecha del Accidente | DateTime | Se muestra para ciertos motivos de ingreso. |
| `UDF_AVISO_MINISTERIO` | Aviso al Ministerio Público | Boolean | Activa campos relacionados con la fecha de aviso. |
| `UDF_FECHA_AVISO_MINISTERIO` | Fecha de Aviso al Ministerio Público | DateTime | Visible cuando el aviso está activo. |
| `UDF_DOMICILIO_RESP` | Domicilio Responsable | String | Información operativa del responsable. |
| `UDF_IDENT_RESPONSABLE` | Identificación Responsable | String | Identificación del responsable. |
| `UDF_NAMEDR` | Nombre del Médico | String | Médico relacionado con la atención. |
| `UDF_FYH_DE_INGRESO` | Fecha y Hora de Ingreso | DateTime | En la vista se observa como campo requerido. |
| `UDF_FYH_DE_EGRESO` | Fecha y Hora de Egreso | DateTime | Fecha de salida/egreso. |

En `MD_UControllerViewFields` ya existen condiciones de visibilidad del tipo:

```text
$row.UDF_MOTIVO_INGRESO == 'AC'
$row.UDF_MOTIVO_INGRESO == 'AC' && $row.UDF_AVISO_MINISTERIO == true
```

Esto demuestra que el formulario admite comportamiento condicional por campo. Un campo adicional no debe agregarse sólo a la definición `MD_UDF`; si no se incluye en la vista y sus metadatos visuales, puede existir en el modelo pero no aparecer en el formulario.

### 13.4 Procedimiento técnico propuesto para un nuevo campo

El flujo seguro para agregar un campo nuevo a Atención Médica sería:

1. **Definir la necesidad funcional:** nombre, propósito, quién lo captura, quién lo consulta, si es por atención o por paciente, si admite múltiples valores y si afecta cargos/ERP.
2. **Elegir el lugar correcto:** `PC` si pertenece a una atención; `PT` si pertenece al paciente; `SO` si pertenece a una orden; `PCAP` si pertenece a una cita; una tabla definida por usuario si se repite.
3. **Registrar el UDF:** crear el campo en `MD_UDF` para `PC`, con tipo, longitud, nulabilidad, lectura, formato y si requiere persistencia en DB.
4. **Sincronizar metadatos:** utilizar la función de sincronización de UDF sólo con autorización de Sistemas y respaldo/ventana de cambio. No se ejecutó durante esta revisión.
5. **Incluirlo en las vistas:** agregarlo a `PCcreateForm1`, `PCeditForm1` y, si corresponde, `PCgrid1`, `PCgrid_IP`, `PCgrid_ER` o reportes.
6. **Configurar la presentación:** en `MD_UControllerViewFields` definir alias, orden, columnas/filas, modo de texto, visible/read-only/hidden y condiciones `Hide When` o `Read Only When`.
7. **Crear categoría si procede:** utilizar `MD_UControllerViewCategories` para no saturar la sección principal de Atención Médica.
8. **Definir catálogo o lookup:** no capturar manualmente valores que deban ser consistentes entre áreas.
9. **Definir validación/regla:** usar `MD_UControllerBusinessRules` para obligatoriedad contextual, consistencia o cálculo; no confiar sólo en ocultar el campo.
10. **Asignar permisos:** establecer roles de lectura/escritura del campo y revisar restricciones por usuario.
11. **Actualizar reportes y documentos:** incluir el dato en UDR, cuenta, honorarios, formatos o PDF si tiene impacto administrativo, clínico o legal.
12. **Probar por estados y perfiles:** nueva atención, edición, urgencias, hospitalización, cierre/alta, usuario médico, enfermería, admisión, cuentas, auditoría y sólo lectura.

### 13.5 Qué puede agregarse sin alterar el modelo principal

Para un dato único, de baja complejidad y propio de la atención, el mecanismo recomendado es un `UDF` de `PC`. Ejemplos posibles —sujetos a definición del área— serían:

- responsable operativo de la atención;
- origen o canal de ingreso;
- clasificación administrativa interna;
- indicador de autorización recibida;
- folio externo de aseguradora o convenio;
- observación operativa no clínica;
- fecha de revisión de cuenta;
- responsable de validar cargos.

Estos ejemplos no deben agregarse automáticamente: primero se debe decidir si el dato es clínico, administrativo, financiero, de paciente, de orden o de cita.

### 13.6 Cuándo no conviene agregar un UDF a PC

No conviene agregarlo directamente a Atención Médica cuando:

- puede tener varios renglones por atención;
- necesita historial o auditoría independiente;
- lo capturan áreas distintas con estados distintos;
- tiene catálogo amplio o relaciones con otros registros;
- genera cargos, movimientos de inventario, facturación o integración ERP;
- contiene información clínica sensible que requiere firma o control separado;
- pertenece al paciente y no al episodio de atención.

En esos casos es preferible un controlador relacionado, una **User Defined Table**, un catálogo con lookup o un proceso formal. Agregarlo como texto en `PC` produciría duplicidad, falta de trazabilidad y dificultad para reportar.

### 13.7 Permisos y alcance del cambio

| Participante | Alcance recomendado sobre un nuevo campo de PC |
|---|---|
| Sistemas / Administrators | Crear UDF, vistas, categorías, reglas, sincronización y permisos; aprobar despliegue. |
| Admisión | Capturar datos administrativos iniciales si el campo está habilitado para su rol. |
| Enfermería | Consultar o capturar datos operativos de atención sólo cuando corresponda a su proceso. |
| Médico / ayudante | Consultar o capturar datos clínicos; no debería editar campos de cuenta o configuración. |
| Caja / cuentas / `cierre_cuentas` | Capturar o validar datos financieros y de cierre; no modificar diagnóstico clínico. |
| Convenios | Consultar/aplicar convenio, autorización o referencia externa; no cambiar datos clínicos. |
| Almacén / unidades de servicio | Consultar sólo si el campo afecta solicitud, surtido, cargo o recurso. |
| Auditoría | Lectura, revisión de historial, reglas y motivo de cambios; sin edición ordinaria. |
| Usuario sólo lectura | Ver el campo si la restricción lo permite, sin escritura. |

La acción de Framework observada `PC_OP / Cancelar Alta Paciente` usa roles `Administrators,cierre_cuentas` y una condición de estado. Esto demuestra que las operaciones de atención pueden depender simultáneamente de **rol + estado del registro + condición de negocio**. Un nuevo campo con impacto financiero o de alta no debe quedar protegido sólo por el menú.

### 13.8 Impactos que deben revisarse antes de aprobarlo

| Capa | Pregunta de impacto |
|---|---|
| Atención `PC` | ¿Se guarda por episodio y se conserva al editar/cerrar? |
| Paciente `PT` | ¿Se está almacenando un dato que realmente pertenece a la persona? |
| Cita `PCAP` | ¿Debe copiarse o sincronizarse con la agenda? |
| Orden `SO` | ¿Debe viajar a la orden o afectar su procesamiento? |
| Cuenta/cargos | ¿Cambia precio, autorización, cargo automático, devolución o cierre? |
| Honorarios | ¿Debe aparecer en conciliación o auditoría de pago? |
| ERP | ¿Debe mapearse a `ERP_*`, `CERP_*` o una vista `VERP_*`? |
| Seguridad | ¿Contiene información clínica, financiera, legal o personal? |
| Reportes/PDF | ¿Debe aparecer en reportes, cuenta, honorarios o documentos firmados? |
| Auditoría | ¿Se necesita historial de cambios, usuario, fecha y motivo? |

### 13.9 Conclusión para el formulario de la imagen

La plataforma sí tiene una ruta formal para agregar elementos al formulario de Atención Médica sin modificar manualmente una tabla: **UDF + vista PC + campos de vista + categoría/lookup/regla + permisos**. Sin embargo, para un dato complejo o con impacto operativo, la solución correcta no es añadir otra caja de texto a `PC`, sino crear una entidad relacionada y conectar el flujo.

En esta revisión únicamente se inspeccionaron los metadatos y las vistas. No se creó UDF, no se sincronizaron campos, no se modificó la vista, no se ejecutó ninguna regla y no se alteró ningún registro de atención o paciente.

## 14. Inventario completo del Framework

### 14.1 Modelo de metadatos y control de aplicación

| Opción del menú | Ruta | Alcance y opciones observadas | Resultado de la revisión |
|---|---|---|---|
| MD DBObjects | `/Pages/MD_DBObjects` | Objetos ERP/metadatos con `MDDB Object Name`, DROP, CREATE, BODY, END, precedencia, cache view e índices; incluye **Generate All Objects**. | 113 objetos. Es el punto más sensible para vistas/cache SQL; no se ejecutó generación. |
| MD Parameters | `/Pages/MD_Parameters` | Parámetros globales con Id, descripción y valor por defecto; incluye ERP, cache, precios, idioma, atención, agenda, LIS y KPI. | 71 parámetros. Cambiarlos puede modificar el comportamiento transversal. |
| MD Concepts | `/Pages/MD_Concepts` | Catálogos conceptuales, tipo de lookup, permitir nulos/nuevos datos, vista de datos, opciones, notas, ruta de acceso y autocompletado. | 41 conceptos. Es la base para listas controladas y validaciones de catálogo. |
| MD Pages | `/Pages/MD_Pages` | Registro de páginas y navegación de metadatos. | Sin filas visibles en esta consulta. |
| MD Controllers | `/Pages/MD_Controllers` | Nombre del controlador, etiqueta, si está en DB y si es de sistema; acciones de sincronización de localización y sitemap. | 769 controladores. Se identificaron familias `AG`, `AGPK`, `IT`, `PC`, `PT`, `SO`, `PR`, `V_PCRQ`, entre otras. |
| MD Controller Access Rules | `/Pages/MD_ControllerAccessRules` | Reglas de acceso por controlador. | Sin filas visibles; la capa existe aunque no haya registros expuestos en la vista. |

### 14.2 Controladores, campos y vistas

| Opción del menú | Ruta | Qué administra | Resultado |
|---|---|---|---|
| MD UControllers | `/Pages/MD_UControllers` | Controladores definidos por usuario, detección de conflictos, etiqueta, conexión REST, plugin, handler, barra de estado, configuración del adaptador, valores ingresados, upsert y cantidad máxima. | 1 controlador visible: `UDR_TICKET_FR`. |
| MD UController Commands | `/Pages/MD_UControllerCommands` | Comandos reutilizables de controladores. | Sin filas visibles. |
| MD UController Fields | `/Pages/MD_UControllerFields` | Tipo, longitud, nulabilidad, llave, virtual/calculado, fórmula SQL, cálculo bajo demanda, label, solo lectura, editor, lookup, data controller/view, campos de valor/texto, roles y Write Roles. | 25 campos. Es una de las capas principales para agregar campos funcionales y protegerlos. |
| MD Field Lookups | `/Pages/MD_FieldLookups` | Lookup del campo: tipo, controlador/vista de consulta, campo valor/texto, vista nueva, contexto y habilitación. | 13 lookups. Incluye motivos de ingreso, disponibilidad/citas y fechas. |
| MD UController Views | `/Pages/MD_UControllerViews` | Vista por controlador, id, tipo, acceso, comando, etiqueta, selector, encabezado, reporte, orden, filtro, categoría y campos. | 15 vistas. Incluye `PCcreateForm1`, `PCeditForm1`, `PCgrid_IP`, `PCgrid_ER`, pacientes, órdenes y honorarios. |
| MD UController View Categories | `/Pages/MD_UControllerViewCategories` | Categorías/secciones dentro de una vista; orden, pestaña, wizard, floating, colapsado y condición de visibilidad. | 1 categoría visible, en `PCPR`. |
| MD UController View Fields | `/Pages/MD_UControllerViewFields` | Campo por vista: alias, columnas/filas, texto, tooltip, watermark, formato, hyperlink, ocultar, mostrar, solo lectura, condición y agregación. | 73 definiciones. Controla cómo aparece cada dato, no sólo si existe en DB. |
| MD XController Fields | `/Pages/MD_XControllerFields` | Campos de controladores extendidos/externalizados, con lookups, filtros, roles y Write Roles. | 30 campos. |
| MD XController Views | `/Pages/MD_XControllerViews` | Vistas de controladores extendidos. | Sin filas visibles. |
| MD XController View Categories | `/Pages/MD_XControllerViewCategories` | Categorías para vistas extendidas, con condición de visibilidad. | 1 categoría visible, relacionada con `PCPR`. |
| MD XController View Fields | `/Pages/MD_XControllerViewFields` | Presentación de campos extendidos por vista/categoría. | 91 definiciones. |

### 14.3 Acciones, reglas y seguridad

| Opción del menú | Ruta | Qué administra | Resultado |
|---|---|---|---|
| MD UController Action Groups | `/Pages/MD_UControllerActionGroups` | Agrupación de acciones de usuario. | Sin filas visibles. |
| MD UController Actions | `/Pages/MD_UControllerActions` | Comando, argumento, encabezado, validación, atajo, datos, confirmación, script, CSS y roles. | 8 acciones. Se observaron roles `Administrators`, `cierre_cuentas` y `Permisos`, además de acciones desactivadas. |
| MD UController BusinessRules | `/Pages/MD_UControllerBusinessRules` | Reglas por controlador, tipo, fase, comando, vista, script y habilitación. | 7 reglas. Puede modificar valores o detener una operación. |
| MD Access Control Rules | `/Pages/MD_AccessControlRules` | Reglas generales de control de acceso. | Sin filas visibles. |
| MD Controller Registry | `/Pages/MD_ControllerRegistry` | Registro de controladores y resolución de metadatos. | Sin filas visibles. |
| MD Tags | `/Pages/MD_Tags` | Etiquetas visuales por condición, color y vistas. | 5 etiquetas visibles para estados de solicitudes: abierta, en proceso, procesada, comprometida y cancelada/denegada. |
| User Access Restrictions | `/pages/khun` | Restricción adicional por usuario. | Existe como capa de seguridad independiente de roles y menús. |

### 14.4 Extensibilidad, reportes, workflow y localización

| Opción del menú | Ruta | Qué administra | Resultado |
|---|---|---|---|
| User Defined Fields | `/Pages/MD_UDF` | Campo, prompt, tipo, DB, lectura, nulabilidad, longitud, precisión, dimensiones, formato, ocultamiento y expresión SQL. | 38 campos; incluye los UDF de `PC`, `PT`, `SO`, `PR`, `PCAP`, `PCPR` y `MR`. Tiene acción **Sync All User Defined Fields**. |
| User Defined Tables | `/Pages/UT` | Tablas auxiliares definidas por usuario. | 3 tablas: `APIT` Artículos para citas, `Honorarios` y `Procedimientos`. |
| User Defined Reports | `/Pages/UDR` | Código, nombre, posición, cache, roles, query, campos y visibilidad avanzada. | 34 reportes. Es la capa de reportes operativos y de honorarios; no equivale a una tabla. |
| Workflow Manager | `/Pages/WF` | State Fields, Rules y Groups para estados y transiciones. | La interfaz no mostró filas visibles en la consulta. |
| MD Business Rules | `/Pages/MD_BusinessRules` | Reglas SQL/C#, controlador, comando, vista, fase, campos de cálculo, librería y habilitación; incluye **Build CSharp Business Rules Library**. | 16 reglas. Contiene reglas de citas, órdenes, atención, pacientes, recursos, pagos y solicitudes. No se ejecutó Build ni regla. |
| MD Root Localization Files | `/Pages/MD_LocalizationFiles` | Archivos de idioma generales. | 50 archivos visibles. |
| MD Controller Localization Files | `/Pages/MD_LocalizationFiles?Path=Controllers` | Traducciones por controlador. | 2,095 archivos visibles. |
| MD Page Localization Files | `/Pages/MD_LocalizationFiles?Path=Pages` | Traducciones por página. | 1,240 archivos visibles. |
| MD Data Import Templates | `/Pages/MD_DataImportTemplates` | Plantillas de importación de datos. | Sin filas visibles. No se importó nada. |

### 14.5 Parámetros operativos importantes observados

En `MD Parameters` se identificaron parámetros que pueden cambiar el comportamiento del sistema completo, entre ellos:

- `AG_FACTOR_CUSTOM`: aplicación de factores de acuerdos a precios personalizados.
- `CERP_CACHEPRICELISTS`, `CERP_ITPR_ISCACHED`, `CERP_ITPR_KEEPZEROES`: cache y listas de precios.
- `ERP`, `ERP_CACHE`, `ERP_DB`, `ERP_DBMASTER`: tipo, conexión, base y papel maestro del ERP.
- `FW_DEFAULTLANGUAGE`, `FW_URLHASHENABLED`: idioma y comportamiento de URL.
- `PC_DEFAULTDOCUMENT`: documento por defecto al cerrar atención.
- `PC_ITEMPRICINGMODE`: precio dinámico, estático u opcional.
- `PC_LINECOLLATION`: nivel de agrupación de líneas de atención.
- `KH_ENFORCEPRICELIST`: exigencia de lista de precios.
- `LIS_REQUESTCODE_PREFIX`, `LIS_SESSIONID`: integración de laboratorio.
- `KPI_LANGUAGE`, `KPI_SU_LAB`, `KPI_SU_RX`: indicadores y unidades de laboratorio/RX.

`Setup > Parameters` es una capa adicional con 8 parámetros actualmente visibles, incluyendo cache de precios, cache ERP, país por defecto, administración de stock de atención, posición del recurso, último precio de cargo, validación de transacción de cargos y fuerza de búsqueda de homónimos. No deben modificarse sin una matriz de impacto y prueba posterior.

## 15. Inventario completo de Setup

| Opción de Setup | Ruta | Función | Riesgo/alcance |
|---|---|---|---|
| Información de licencia | `/Pages/LicenseInformation` | Usuarios activos, sesiones y detalle de licenciamiento. | Puede exponer sesiones activas; sólo administración/Sistemas. |
| Afiliación | `/pages/membership` | Usuarios suscritos, aprobación, bloqueo y último acceso. | Identidad y acceso; requiere segregación de funciones. |
| Contenido del Sitio | `/pages/site-content` | Sitemap, páginas, archivos, roles, excepciones y programación. | Cambia navegación y exposición de módulos. |
| Restricciones de acceso del usuario | `/pages/khun` | Restricciones individuales. | Puede ampliar o reducir acceso aunque el rol sea el mismo. |
| Repositorio de Metadatos | `/pages/md_repository` | Concepto, código, traducciones, notas, habilitación y Access Route. | 7,382 metadatos; afecta etiquetas, catálogos y navegación. |
| Informes definidos por el usuario | `/pages/udr` | Reportes, SQL, roles, cache y campos. | 34 reportes; puede exponer información sensible o afectar resultados. |
| Comprobación de integridad | `/pages/v_kh_integrity` | Revisión de consistencia de configuración. | Sin filas visibles; debe ejecutarse/controlarse en procedimiento separado. |
| Panel de servicios de base de datos | `/pages/pn_db` | Jobs activos, fechas, duración, mensajes y estado de SQL Server Agent. | Se observaron 2 jobs; ejecutar/procesar jobs puede afectar datos y procesos. |
| Metadata | `/Pages/MD` | Administración general del metamodelo. | Sin filas visibles. Capa transversal. |
| MD Messages | `/Pages/MD_Messages` | Mensajes por idioma y traducción. | 1,340 mensajes; cambia mensajes, validaciones y experiencia de usuario. |
| MD Views | `/Pages/MD_Views` | Vistas de metadatos. | Sin filas visibles; no confundir con UController Views. |
| Parameters | `/Pages/Parameters` | Parámetros operativos globales. | 8 parámetros; afecta cache, cargos, precios, recursos y homónimos. |
| ERP Connections | `/Pages/ERPConnections` | Sesión, servidor, base, usuario, tipo y licencia del ERP. | 1 conexión. La vista muestra etiquetas de credenciales; no se leyeron ni exportaron valores. |
| ML Servers | `/Pages/ML_Servers` | Servidores de correo/mailing. | Sin filas visibles. |
| ML EMail Alerts | `/Pages/ML_EMailAlerts` | Alertas de correo, destinatarios y reglas. | Sin filas visibles; si se habilita, puede enviar información a terceros. |

## 16. Inventario completo de Configuración

### 16.1 Estructura operativa, cargos y recursos

| Opción | Ruta | Resultado observado y alcance |
|---|---|---|
| Unidades Hospitalarias | `/pages/fc` | Unidad, sitio, unidad de venta, series, impuestos, proyecto, segmentos de costo, servicio/personal/paciente por defecto y capacidad. |
| Reglas de impuestos de ventas de sucursales | `/pages/brtx` | Reglas fiscales por sucursal; sin registros visibles. |
| Unidades de Servicio | `/pages/su` | Almacén, pacientes, socio de negocios, impuesto, cargos, lotes, solicitudes, unidad solicitante, laboratorio, series y costos. Se observaron 11. |
| Panel de Recursos Hospitalarios | `/pages/pn_fr` | Camas, habitaciones, UCI, quirófanos, capacidad, asignación, citas, cargos y costos. Se observaron 189 recursos. |
| Panel de Configuración de Quirófanos | `/pages/pn_or` | Quirófanos, kits, usuarios, recursos, citas y cargos. Se observaron 5 quirófanos. |
| Personal | `/pages/pr` | Médicos/personal, usuarios, especialidades, recursos, citas, recetas, socio de negocios, honorarios e impuestos. Se observaron 262 personas. |
| Grupos de Artículos | `/pages/itgr` | Grupos, alias y banderas de receta, cirugía y laboratorio. Se observaron 37 grupos. |
| Lista de materiales | `/pages/bm` | Punto de paquetes/ensambles/BOM; sin registros visibles. |
| Artículos y Servicios | `/pages/v_it` | Catálogo, inventario, almacenes, lotes, series, impuestos, ensambles y habilitación. Se observaron 5,237 artículos/servicios. |
| Asignaciones de Recursos Hospitalarios | `/pages/pcfr` | Recurso, paciente, atención, procedimiento, fechas, cargos automáticos, cancelación y auditoría. Se observaron 54 activos. |
| Acuerdos | `/pages/ag` | Convenios, precios, impuestos, cargos administrativos, descuentos, copagos, deducibles, autorizaciones y usuarios. Se observaron 48. |
| Panel de Cargos Automáticos | `/pages/pn_ac` | Atención, totales de cuenta, artículos, recurrentes, referenciados, no facturables, recursos, extraordinarios y festivos. |
| Precios especiales | `/pages/bpsp` | Precios especiales por socio/artículo; sin registros visibles. |

### 16.2 Catálogos clínicos y auxiliares

| Opción | Ruta | Resultado observado y alcance |
|---|---|---|
| Códigos de Diagnóstico | `/pages/dx` | 12,423 códigos, descripción ES/EN, tipo de diagnóstico y patología. |
| Procedimientos Médicos | `/pages/cp` | 536 procedimientos con código y nombre. |
| Especialidades Médicas | `/pages/ms` | 66 especialidades/códigos. |
| Panel de Configuración de Recetas Médicas | `/pages/pn_pcrx` | Grupos de artículos y reglas de dosificación; sin registros visibles en la vista inicial. |
| Catálogos auxiliares | `/pages/auxiliary-catalogs` | Índice de las pantallas de configuración. |
| Sitios | `/pages/si` | Sitios; sin registros visibles. |
| Unidades de venta | `/pages/slun` | Unidades de venta; sin registros visibles. |
| Códigos de impuestos auxiliares | `/pages/tx` | Catálogo fiscal auxiliar; sin registros visibles. |
| Artículos para citas | `/Pages/UT_APIT` | Tabla definida por usuario para artículos habilitados en citas. Se observaron 92 registros. |

### 16.3 Caches ERP

| Opción | Ruta | Alcance observado |
|---|---|---|
| Caché de Centros de Costo | `/pages/cerp_cc` | Costos; sin registros visibles. |
| Caché de socios comerciales | `/pages/cerp_bp` | Socios, crédito, moneda, impuestos y datos de contacto. |
| Caché de Artículos | `/pages/cerp_it` | Artículos, grupos, UOM, costos, venta/compra/inventario, lotes y series. |
| Caché de artículos de unidad de ventas | `/pages/cerp_slit` | Artículos por unidad de venta; sin registros visibles. |
| Caché de Grupos de Artículos | `/pages/cerp_itgr` | Grupos ERP; 42 registros paginados. |
| Caché de códigos de barras de elementos | `/pages/cerp_itbc` | Código de barras y artículo. |
| Caché de precios de socios comerciales | `/pages/cerp_bpit` | Precios por socio; sin registros visibles. |
| Caché de listas de precios | `/pages/cerp_pl` | 24 listas, factor e indicador de precio bruto. |
| Artículos de lista de precios (bajo demanda) | `/pages/cerp_itpr` | 37,971 renglones de artículo/precio/impuesto. |
| Caché de Almacenes | `/pages/cerp_wh` | Sitio, almacén y nombre de almacén. |
| Taxes Cache | `/pages/cerp_tx` | 5 códigos/tasas de impuesto. |

## 17. Bitácora de esta exploración y resultado

| Acción realizada | Resultado |
|---|---|
| Abrir Framework y obtener todas sus opciones del menú | Se identificaron 32 entradas, incluyendo metadatos, controladores, vistas, campos, reglas, seguridad, UDF, tablas, reportes, workflow, localización e importación. |
| Consultar cada página de Framework | Se registraron rutas, conteos, columnas, acciones y capas sin abrir formularios de alta. |
| Consultar Setup completo | Se documentaron licencia, membresía, contenido, restricciones, repositorio, integridad, jobs, metadatos, mensajes, parámetros, ERP y correo. |
| Consultar Configuración completa | Se documentaron 33 entradas: unidades, recursos, quirófanos, personal, artículos, acuerdos, cargos, catálogos y caches ERP. |
| Consultar páginas con acciones potencialmente mutantes | No se ejecutaron Agregar, Editar, Borrar, Sync, Generate, Build, Import, Process, jobs ni cambios de permisos. |
| Revisar la sesión actual | La navegación regresó a Inicio. No se modificó ningún registro ni configuración. |
| Ambiente de pruebas | Aún no se aplicaron cambios porque la URL visible no identifica inequívocamente el sitio de pruebas. Queda pendiente confirmar que la pestaña conectada corresponde al ambiente de prueba antes de hacer cambios controlados. |

### 17.1 Qué reforzar primero cuando esté confirmado el ambiente de pruebas

1. Probar la creación de un UDF no clínico en `PC` y documentar si aparece en alta, edición y listado.
2. Probar una categoría/sección independiente para evitar saturar **Atención Médica**.
3. Validar un lookup controlado para `PC` sin texto libre.
4. Validar una regla de visibilidad y una regla de solo lectura con datos ficticios.
5. Confirmar cómo se reflejan los nuevos campos en UDR, cuenta, cargos y PDF.
6. Confirmar roles separados para Sistemas, admisión, enfermería, médico, cuentas y auditoría.
7. Ejecutar la comprobación de integridad después de cada cambio y registrar evidencia antes/después.
8. Revertir o deshabilitar las pruebas una vez documentado el resultado, sin tocar datos productivos.

## 18. Alcances prácticos y ejemplos de uso

Esta sección traduce cada bloque técnico a ejemplos de negocio. Los ejemplos son propuestas de uso; no significa que se hayan ejecutado ni que todos estén licenciados o habilitados en Hospital Escandón.

### 18.1 Framework: qué se puede hacer

| Bloque | Alcance | Ejemplo práctico |
|---|---|---|
| MD DBObjects | Crear o mantener vistas/cache SQL que exponen información de ERP o de la aplicación al Framework. | Exponer artículos, precios, impuestos o almacenes mediante `VERP_IT`, `VERP_ITPL`, `VERP_TX` o `VERP_WH` para que una pantalla consulte datos actualizados. Requiere control de cambios SQL y respaldo. |
| MD Parameters | Cambiar comportamiento global sin modificar cada pantalla. | En pruebas, comparar atención con precio dinámico contra precio estático usando `PC_ITEMPRICINGMODE`; medir efecto en órdenes, cargos y cuenta. |
| MD Concepts | Definir catálogos simples y reutilizables. | Crear un catálogo de “Origen de solicitud” con valores Hospitalización, Consulta, Urgencias y Convenio, reutilizable en varias vistas. |
| MD Controllers | Registrar, etiquetar y clasificar entidades/pantallas del sistema. | Etiquetar `PC` como Atención Médica, verificar que está en DB y que es controlador de sistema; sincronizar localización. |
| MD Controller Access Rules | Autorizar el acceso a controladores completos. | Permitir que sólo cuentas/cierre consulte una pantalla de cierre de cuenta, aunque el menú general sea visible para otros usuarios. |
| MD UControllers | Crear una entidad basada en una API/REST o controlador definido por usuario. | Conectar un servicio externo de tickets o disponibilidad y mostrarlo como lista consultable sin convertirlo en una tabla clínica. |
| MD UController Fields | Definir comportamiento de cada campo: tipo, cálculo, editor, lookup, roles y escritura. | Un campo “Médico responsable” con lookup a `PR`, lectura para enfermería y escritura sólo para admisión/supervisión. |
| MD Field Lookups | Relacionar un campo con una lista, vista o controlador de búsqueda. | Que “Motivo de ingreso” muestre opciones válidas y almacene un código estable, no el texto escrito a mano. |
| MD UController Views | Definir vistas de alta, edición, grid, reportes y filtros. | Agregar un campo administrativo a `PCeditForm1`, mostrarlo también en `PCgrid_IP` y excluirlo del grid de urgencias si no aplica. |
| MD UController View Categories | Organizar campos en pestañas/secciones. | Crear la sección “Datos administrativos” separada de “Datos clínicos” en Atención Médica. |
| MD UController View Fields | Ajustar etiqueta, orden, visibilidad, read-only, formato y condiciones. | Mostrar “Folio de aseguradora” sólo cuando el tipo de paciente sea aseguradora; hacerlo sólo lectura después de autorizar la cuenta. |
| MD XController | Añadir campos/vistas a controladores extendidos o externos sin alterar la entidad base. | Mostrar disponibilidad de un recurso externo o datos de una agenda integrada en una vista auxiliar. |
| MD UController Actions | Crear acciones y botones con condición, confirmación y roles. | Acción “Solicitar autorización” visible sólo a cuentas; acción “Generar cita” condicionada a factura pagada y disponibilidad. |
| MD UController Action Groups | Agrupar acciones relacionadas. | Grupo “Cierre de cuenta” con validar, autorizar, generar documento y consultar auditoría. Actualmente no mostró registros. |
| MD UController BusinessRules | Validar o calcular durante eventos de un controlador. | Impedir cierre si faltan cargos obligatorios; calcular una fecha de vencimiento; normalizar datos capturados. |
| MD BusinessRules | Ejecutar reglas SQL/C#/servidor sobre procesos más complejos. | Al reservar un servicio, validar médico, consultorio, fechas y factura; al procesar una solicitud, sincronizar el documento al ERP. |
| MD Access Control Rules | Controlar acceso transversal por regla. | Restringir una vista o acción cuando la unidad hospitalaria del usuario no coincide con la del registro. |
| MD Controller Registry | Registrar/resolver controladores para que el Framework los encuentre. | Incorporar un controlador nuevo sin romper la resolución de vistas y comandos. Actualmente no mostró registros. |
| MD Tags | Colorear o etiquetar estados según condiciones. | Semáforo de solicitudes: abierta, en proceso, procesada, comprometida y cancelada. |
| MD UDF | Agregar datos simples persistentes a una entidad. | `PC.UDF_FOLIO_ASEGURADORA`, `PC.UDF_AUTORIZACION_CUENTA` o `SO.UDF_REFERENCIA_EXTERNA`, con permisos y validación. |
| User Defined Tables | Crear detalles con varias filas o estructura propia. | Registrar varias autorizaciones, documentos recibidos o componentes de un paquete relacionados con una atención. |
| User Defined Reports | Crear consultas/reportes con roles, cache y campos. | Reporte de cargos sin acuerdo, órdenes pendientes de surtir o líneas de honorarios excluidas por motivo. |
| Workflow Manager | Modelar estados y transiciones. | Solicitud: Capturada → Validada → Autorizada → Surtida → Cerrada; cada transición con rol y condición. |
| MD Localization Files / Repository | Traducir etiquetas, mensajes, páginas y controladores. | Cambiar “Patient Care” a “Atención Médica” sin modificar la lógica. |
| MD Data Import Templates | Definir cargas masivas controladas. | Importar un catálogo de artículos en un ambiente de prueba con validación previa; actualmente no mostró plantillas. |

### 18.2 Setup: qué se puede hacer

| Bloque | Alcance | Ejemplo práctico |
|---|---|---|
| License Information | Revisar usuarios activos, sesiones y licencia. | Detectar sesiones abiertas de cuentas inactivas antes de una auditoría. |
| Membership | Administrar usuarios suscritos, aprobación y bloqueo. | Crear una cuenta de prueba de “Cuentas” con acceso temporal y revocarla al terminar. |
| Site Content | Definir sitemap, páginas visibles, roles, excepciones y programación. | Mostrar un reporte operativo sólo a cuentas y ocultarlo para médicos. |
| User Access Restrictions | Aplicar restricciones individuales adicionales al rol. | Limitar a un usuario de admisión a una unidad hospitalaria concreta. |
| Metadata Repository | Mantener conceptos, nombres, traducciones y rutas de acceso. | Corregir la etiqueta de un concepto o habilitar una ruta que ya existe en metadatos. |
| User Defined Reports | Administrar reportes con consulta, campos, cache y roles. | Crear un reporte de diferencias entre orden, cargo y factura. |
| Configuration Integrity Check | Revisar consistencia de metadatos, reglas y referencias. | Ejecutarlo después de agregar un campo/vista y documentar errores antes de liberar. |
| Database Services Panel | Supervisar SQL Server Agent, jobs y mensajes. | Confirmar que el job KPI terminó y revisar duración/error sin ejecutarlo manualmente. |
| Metadata / MD Views | Administrar metamodelo y vistas de metadatos. | Revisar una vista que no aparece en una pantalla antes de cambiar el controlador. |
| MD Messages | Mantener mensajes por idioma. | Cambiar un mensaje técnico de validación a una instrucción entendible para enfermería. |
| Parameters | Administrar valores globales de operación. | En pruebas, activar cache de precios y medir tiempo/actualización; no cambiarlo en producción sin ventana. |
| ERP Connections | Configurar conexión y tipo de ERP. | Validar conectividad con un ERP de prueba; nunca exponer credenciales ni probar con una cuenta productiva sin autorización. |
| ML Servers / EMail Alerts | Configurar correo y alertas. | Enviar una alerta de orden pendiente sólo a la unidad responsable, con datos mínimos. |

### 18.3 Configuración: qué se puede hacer

| Bloque | Alcance | Ejemplo práctico |
|---|---|---|
| Unidades Hospitalarias | Separar operación por sede/unidad, defaults, series, impuestos y costos. | Crear una unidad de pruebas con lista de precios y almacén propios. |
| Reglas de impuesto por sucursal | Aplicar impuestos según sucursal y operación. | Validar que una venta de laboratorio use el código fiscal correcto. |
| Unidades de Servicio | Definir quién solicita, almacén, cargos, lotes y servicios. | Configurar laboratorio para permitir solicitudes y selección de lote. |
| Recursos Hospitalarios | Modelar camas, habitaciones, UCI, quirófanos, capacidad, citas y cargos. | Definir una cama de prueba con capacidad 1 y cargo diario controlado. |
| Quirófanos | Configurar quirófano, kits, usuarios y programación. | Asociar un kit quirúrgico a un tipo de procedimiento y verificar los materiales esperados. |
| Personal | Relacionar médicos/personas con especialidad, usuario, recurso, receta, cita y honorarios. | Permitir citas a un médico y asociarlo a un consultorio sin otorgarle permisos administrativos. |
| Grupos de Artículos | Clasificar artículos como receta, cirugía, laboratorio o servicio. | Marcar un grupo como quirúrgico para que aparezca en el flujo de quirófano. |
| Lista de Materiales | Componer paquetes/ensambles. | Un paquete quirúrgico desglosa guantes, suturas y material de consumo para inventario/cuenta. |
| Artículos y Servicios | Definir venta, compra, inventario, lotes, series, impuestos, unidad y habilitación. | Un estudio de laboratorio genera orden y cargo, pero no se administra como medicamento. |
| Asignaciones de Recursos | Relacionar paciente/atención con cama, sala, recurso y fechas. | Asignar una cama y activar/cancelar cargos automáticos según estancia. |
| Acuerdos | Definir convenio, lista, descuento, copago, deducible, impuesto y autorización. | Para una aseguradora, calcular copago y limitar cargos no cubiertos. |
| Cargos Automáticos | Automatizar cargos de atención, recurso, recurrentes, extraordinarios, festivos o no facturables. | Generar cargo diario de habitación y excluirlo en cortesía o durante una suspensión autorizada. |
| Precios Especiales | Aplicar precio por socio/artículo. | Dar una tarifa pactada para un estudio a un convenio específico. |
| Diagnósticos, procedimientos y especialidades | Mantener catálogos clínicos normalizados. | Vincular procedimiento quirúrgico con especialidad y código diagnóstico. |
| Configuración de Recetas | Definir grupos y dosificación. | Validar frecuencia/unidad de una receta según el grupo de medicamento. |
| Catálogos auxiliares, Sitios y Unidades de venta | Mantener referencias administrativas y comerciales. | Separar la unidad de venta de la unidad hospitalaria sin duplicar pacientes. |
| Caches ERP | Sincronizar/consultar socios, artículos, precios, almacenes, impuestos y costos. | Actualizar precios desde ERP y comprobar que una orden usa la versión vigente. |
| Artículos para citas | Definir qué servicios pueden reservarse. | Habilitar sólo estudios o consultas con duración y recurso disponibles. |

### 18.4 Ejemplos de proyectos que podrían construirse con estas opciones

1. **Control de autorización de aseguradoras:** UDF en `PC`/`SO`, lookup de convenio, regla de obligatoriedad, acción para solicitar autorización, UDR de pendientes y permisos para cuentas.
2. **Paquetes quirúrgicos:** grupo quirúrgico, lista de materiales, recurso de quirófano, reglas de cargos, surtido de almacén y reporte de diferencias entre kit y consumo.
3. **Control de cargos de hospitalización:** recurso/cama, cargo recurrente, días festivos, cortesías, suspensión por autorización, cuenta y auditoría.
4. **Ciclo de laboratorio:** grupo de laboratorio, artículo/servicio, unidad de servicio, solicitud, orden, fechas de toma, resultado externo, cuenta y reporte de pendientes.
5. **Cierre administrativo de atención:** workflow de cuenta, roles `cierre_cuentas`, validación de pendientes, documento ERP, honorarios y reporte de conciliación.
6. **Formulario clínico especializado:** UDF, categorías, lookups, reglas, roles y formatos; debe conservar separación entre datos clínicos, administrativos y financieros.

## 19. Soporte de contenido DICOM

### 19.1 Resultado de la revisión

La respuesta corta es: **VRTCL/Vertical declara capacidad de integración con DICOM, pero en la instancia HOSPITAL ESCANDON revisada no quedó demostrado que DICOM esté configurado o habilitado como módulo operativo.**

La documentación pública oficial de VRTCL indica que su **VRTCL Medical Suite Integration Service** puede integrar sistemas DICOM, HL7, XRPC, SOAP, REST y ODATA, y que el cliente puede definir el estándar/protocolo de integración. Esto confirma capacidad de interoperabilidad del producto, no la activación concreta en esta instalación. Véase [Ventajas competitivas de VRTCL Medical Suite](https://www.vrtclfw.com/about-7) y [VRTCL Framework](https://www.vrtclfw.com/inicio).

En la revisión de la instancia no se encontró una opción visible denominada **DICOM**, **PACS**, **Modalidad**, **RIS**, **DICOMweb**, **C-STORE**, **C-FIND**, **C-MOVE**, **QIDO**, **WADO** o **STOW** en los menús de Framework, Setup y Configuración consultados. Tampoco apareció un controlador, parámetro, conexión o reporte con esos términos en los listados revisados. Esto puede significar que:

- la integración vive en el middleware **VRTCL Integration Service** y no en una pantalla funcional;
- la configuración DICOM está en otro servidor/servicio y no en esta aplicación;
- el componente no está licenciado o habilitado en Hospital Escandón;
- se usa un nombre interno distinto al término DICOM;
- la función está disponible sólo mediante proyecto de integración o proveedor externo.

### 19.2 Qué significaría soportar DICOM realmente

Para afirmar soporte operativo completo, habría que comprobar al menos:

| Capacidad | Qué debe verificarse |
|---|---|
| Recepción | Que una modalidad pueda enviar un estudio mediante DICOM C-STORE o DICOMweb STOW-RS. |
| Consulta | Que el sistema pueda localizar paciente/estudio/serie mediante C-FIND o QIDO-RS. |
| Recuperación | Que pueda recuperar imágenes mediante C-MOVE/C-GET o WADO-RS. |
| Identidad | Que Patient ID/Accession Number se relacionen correctamente con paciente, atención y orden. |
| Visualización | Que exista visor o enlace seguro a PACS; guardar sólo un PDF no equivale a soportar DICOM. |
| Metadatos | Que se conserven Study UID, Series UID, SOP Instance UID, modalidad y fecha. |
| Seguridad | TLS, autenticación, autorización por unidad/rol y auditoría de acceso. |
| Operación | Reintentos, colas, errores, duplicados, estudios incompletos y reconciliación. |
| Privacidad | Desidentificación para pruebas y control de datos sensibles en logs/reportes. |

### 19.3 Escenario de integración posible

```text
Modalidad / PACS / RIS
          |
 DICOM DIMSE o DICOMweb
          |
VRTCL Integration Service
          |
Paciente + Atención + Orden + Estudio
          |
Expediente / resultado / cuenta / auditoría
```

Un escenario funcional podría ser: crear una orden de imagen en `SO` o solicitudes, enviar la orden al RIS/PACS, recibir el estudio DICOM, asociarlo por Patient ID/Accession Number con `PT` y `PC`, mostrar un enlace seguro al visor y conservar en el expediente sólo los metadatos/resultados autorizados. Los cargos, acuerdos y facturación seguirían dependiendo de artículos, unidades, precios e impuestos de Vertical.

### 19.4 Prueba recomendada en ambiente de pruebas

Cuando se confirme el sitio de pruebas, la validación debe utilizar un paciente y estudio sintéticos, nunca datos clínicos reales:

1. Confirmar si existe Integration Service, PACS/RIS y endpoint DICOM/DICOMweb.
2. Solicitar el DICOM Conformance Statement del componente que se conectará.
3. Ejecutar C-ECHO o una comprobación equivalente sin enviar imágenes.
4. Enviar un estudio de prueba desidentificado.
5. Validar asociación con paciente, atención, orden y unidad de servicio.
6. Recuperar el estudio y comprobar visor/enlace, metadatos y permisos.
7. Probar error, reintento, duplicado y desconexión.
8. Revisar auditoría y que no se registren imágenes, credenciales o tokens en texto plano.
9. Documentar qué parte corresponde a Vertical y cuál al PACS/RIS/middleware.

Hasta realizar esa prueba, la conclusión correcta es **“capacidad de integración DICOM declarada por el producto; soporte configurado en esta instalación pendiente de confirmar”**, no “DICOM habilitado” ni “DICOM no soportado”.

## Fuentes del levantamiento

- Interfaz autenticada de Vertical HES en Chrome, sesión proporcionada por el usuario.
- Código local de autorización y rutas del proyecto Bitácora HES.
- Notas funcionales y de seguridad de `docs/`.
