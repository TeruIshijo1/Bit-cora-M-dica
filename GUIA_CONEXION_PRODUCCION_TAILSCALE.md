# 🔒 Guía de Conexión a Base de Datos en Producción (Tailscale Mesh VPN)

Esta guía detalla la arquitectura de red y los pasos exactos para configurar y desplegar la conexión segura entre el **Servidor de Producción (Backend Bitácora HES)** y el **Servidor Central de Base de Datos SQL Server (`KH_HE` en AWS)**.

---

## 📌 1. Arquitectura de Red (Reemplazo de Bore)

Anteriormente se utilizaba **Bore** (`bore.pub`), el cual presentaba riesgos de seguridad (relay público), caídas de túnel y puertos dinámicos que cambiaban en cada reinicio.

El sistema ahora opera mediante una **Red Mesh Privada Cifrada con Tailscale (WireGuard)**:

```mermaid
graph LR
    subgraph Servidor Produccion [🖥️ Servidor Web / Producción HES]
        App[Backend FastAPI / Python] -->|TDS Protocol| TailscaleProd[Tailscale Client]
    end

    subgraph Tailscale Network [🌐 Red Privada Segura - WireGuard 256-bit]
        TailscaleProd <===>|Túnel Directo Punto a Punto| TailscaleAWS[Tailscale Node]
    end

    subgraph AWS EC2 [☁️ Servidor Base de Datos AWS]
        TailscaleAWS -->|100.121.115.8:1433| SQLServer[(🏥 SQL Server KH_HE)]
    end
```

### 💎 Beneficios en Producción:
* **IP Fija Permanente:** El servidor SQL Server siempre responde en `100.121.115.8:1433`.
* **Cero Puertos Públicos Expuestos:** No requiere abrir puertos hacia internet en AWS ni en routers.
* **Cifrado Extremo a Extremo:** Cumplimiento con estándares de protección de datos clínicos y normativas de salud.
* **Operación 24/7 Desatendida:** El servicio se ejecuta a nivel de sistema operativo y se recupera automáticamente tras cualquier reinicio.

---

## 🚀 2. Configuración en el Servidor de Producción

Cuando despliegues el backend en el servidor de producción (sea Windows Server o Linux):

### Caso A: Si Producción corre en Windows Server
1. Descarga e instala Tailscale desde: [tailscale.com/download/windows](https://tailscale.com/download/windows).
2. Abre PowerShell como Administrador y ejecuta:
   ```powershell
   & "C:\Program Files\Tailscale\tailscale.exe" up --unattended
   ```
3. Inicia sesión con la cuenta de sistemas: **`sistem01.he@gmail.com`**.
4. Haz clic en **Connect** en la ventana del navegador.

### Caso B: Si Producción corre en Linux (Ubuntu / Debian / Docker)
1. Instala el repositorio y cliente oficial:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```
2. Levanta el servicio en segundo plano autenticándolo en la red:
   ```bash
   sudo tailscale up --ssh --accept-routes
   ```
3. Autentica con la cuenta **`sistem01.he@gmail.com`**.

---

## ⚙️ 3. Variables de Entorno en Producción (`.env`)

En el archivo `.env` del backend en producción, configura las siguientes variables:

```env
# Conexión Directa a SQL Server (KH_HE) vía Tailscale
KH_SERVER=100.121.115.8,1433
KH_DATABASE=KH_HE
KH_USERNAME=escandon_bi_user
KH_PASSWORD=Bi_Escandon_2026!#

# Base de datos PostgreSQL Principal
DATABASE_URL=postgresql://usuario_prod:password_prod@localhost:5432/hospital_escandon_db
```

---

## 🌐 4. Publicación Web y Acceso Remoto (Tailscale Funnel)

Para acceder a las plataformas desde tablets, celulares o fuera del hospital sin instalar clientes VPN:

### URLs Oficiales del Hospital:
* 🩺 **Bitácora Médica / Expediente HES:**  
  👉 **`https://portalhes.tail0c0f17.ts.net/`** *(Mapeado al puerto `8000`)*
* 📊 **Escandón BI / Plataforma BI:**  
  👉 **`https://portalhes.tail0c0f17.ts.net:8443/`** *(Mapeado al puerto `5173`)*

### Comandos de Activación en `SERVIDORCALIDAD`:
```powershell
# Levantar Funnel de Bitácora Médica (Puerto 8000)
& "C:\Program Files\Tailscale\tailscale.exe" funnel --bg 8000

# Levantar Funnel de Escandón BI (Puerto 5173 en HTTPS 8443)
& "C:\Program Files\Tailscale\tailscale.exe" funnel --bg --https=8443 5173
```

---

## 🧪 5. Verificación de la Conexión en Producción

Para comprobar que el servidor de producción tiene visibilidad inmediata con SQL Server:

### Prueba de Red TCP:
* **En Windows (PowerShell):**
  ```powershell
  Test-NetConnection -ComputerName 100.121.115.8 -Port 1433
  ```
  *Debe retornar: `TcpTestSucceeded : True`.*

* **En Linux (Bash):**
  ```bash
  nc -zv 100.121.115.8 1433
  ```
  *Debe retornar: `Connection to 100.121.115.8 1433 port [tcp/ms-sql-s] succeeded!`.*

### Prueba Rápida con Python:
Ejecuta desde la raíz del backend:
```bash
python -c "import sys, os; sys.path.append('.'); from kh_database import get_kh_connection, fetch_camas; conn = get_kh_connection(); print('SQL Server Conectado:', conn is not None); print('Camas detectadas:', len(fetch_camas())); conn.close() if conn else None;"
```

---

## 🛠️ 6. Mantenimiento y Troubleshooting

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| **`Timeout al conectar`** | El nodo de Tailscale en AWS se detuvo o no está en modo desatendido. | En el servidor AWS, verificar que Tailscale esté en `Connected` y con `Run unattended` activo. |
| **`Driver ODBC no encontrado`** | El servidor no tiene el driver de SQL Server instalado. | Instalar `ODBC Driver 18 for SQL Server` o `ODBC Driver 17 for SQL Server` de Microsoft. |
| **`Nodo Offline en Tailscale`** | El servicio de Tailscale se pausó al cerrar la sesión de usuario. | Ejecutar `tailscale up --unattended` en el servidor correspondiente. |
| **`Error 0x80072f0d al instalar en Windows Server`** | El instalador web falla por certificados de Windows Server. | Usar el instalador MSI sin conexión: `https://pkgs.tailscale.com/stable/tailscale-setup-1.102.3-amd64.msi`. |
| **`x509: certificate signed by unknown authority (Grandstream / Firewall)`** | El firewall/router del hospital hace inspección SSL profunda. | En Grandstream: **Firewall -> Proxy SSL -> Lista de exención**, agregar la IP del servidor o los dominios `*.tailscale.com`. |
