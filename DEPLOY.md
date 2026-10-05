# Despliegue a producción — Supabase + Vercel

```
                ┌──────────────────────────┐
  clientes ───► │ Vercel: autonegocio-web  │  Next.js (carpeta frontend/)
                └────────────┬─────────────┘
                             │ NEXT_PUBLIC_API_URL
                ┌────────────▼─────────────┐
                │ Vercel: autonegocio-api  │  FastAPI serverless (api/index.py)
                │  + Vercel Cron (scraping)│
                └──────┬───────────┬───────┘
                       │           │
              Postgres │           │ Storage (fotos)
                ┌──────▼───────────▼───────┐
                │        Supabase          │
                └──────────────────────────┘
```

Ambos proyectos de Vercel salen del **mismo repositorio de GitHub** y se
redespliegan solos en cada `git push` a `main`.

---

## 1. Supabase (base de datos + fotos)

1. Crea un proyecto en [supabase.com](https://supabase.com) → **New project**.
   - Región: **East US (North Virginia)** (la más cercana a Vercel `iad1` y a Colombia).
   - Guarda la contraseña de la base de datos en un gestor de contraseñas.
2. Copia estos valores (los usarás en los pasos 2 y 3):
   - **Project Settings → Database → Connection string → "Transaction pooler"** (puerto **6543**).
     Reemplaza `[YOUR-PASSWORD]` por tu contraseña → este es `DATABASE_URL`.
   - **Project Settings → API**: `Project URL` → `SUPABASE_URL`, y la clave
     **service_role** → `SUPABASE_SERVICE_ROLE_KEY`.
     ⚠️ La `service_role` salta todos los permisos: solo va en el backend, nunca en el frontend.

## 2. Inicializar la base de datos (una sola vez, desde tu PC)

En la raíz del proyecto, en PowerShell:

```powershell
$env:DATABASE_URL="<connection string del pooler>"
$env:SUPABASE_URL="https://XXXX.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="<service_role>"
$env:ADMIN_USERNAME="miguel"
$env:ADMIN_EMAIL="tu@correo.com"
$env:ADMIN_PASSWORD="<una contraseña larga>"
python -m scripts.init_prod
```

Crea las tablas, el bucket público `fotos` y tu usuario administrador.
Es seguro ejecutarlo varias veces.

## 3. Vercel — API (proyecto `autonegocio-api`)

1. [vercel.com/new](https://vercel.com/new) → importa `PROYECTO_VEHICULOS_BOGOTA`.
2. **Root Directory**: `./` (la raíz). Framework: **Other**.
3. **Environment Variables** (ver `.env.example`):

| Variable | Valor |
|---|---|
| `DATABASE_URL` | connection string del pooler (paso 1) |
| `SUPABASE_URL` | `https://XXXX.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | clave service_role |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CRON_SECRET` | otro valor aleatorio (mismo comando) |
| `DEBUG` | `false` |
| `CORS_ORIGINS` | URL del frontend (paso 4), ej. `https://autonegocio-web.vercel.app` |
| `ANTHROPIC_API_KEY` | opcional, para los agentes IA |

4. **Deploy**. Comprueba `https://<tu-api>.vercel.app/health` → `{"status":"ok"}`.

El scraping corre con **Vercel Cron** una vez al día (6:00 a. m. hora de Bogotá,
ver `vercel.json`). En el plan Hobby es el máximo; con Pro puedes cambiar
`schedule` a por ejemplo `0 */2 * * *` (cada 2 horas). También puedes lanzarlo
desde el panel → *Ejecutar Scraping*.

## 4. Vercel — Web (proyecto `autonegocio-web`)

1. [vercel.com/new](https://vercel.com/new) → importa **el mismo repositorio** otra vez.
2. **Root Directory**: `frontend`. Framework: Next.js (auto).
3. **Environment Variables** (ver `frontend/.env.example`):

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL de la API (paso 3), sin `/` final |
| `NEXT_PUBLIC_WHATSAPP` | tu WhatsApp con indicativo, ej. `573001234567` |
| `NEXT_PUBLIC_TELEFONO` | opcional |
| `NEXT_PUBLIC_EMAIL` | correo de contacto |
| `NEXT_PUBLIC_DIRECCION` | dirección real o `Bogotá, Colombia` |
| `NEXT_PUBLIC_HORARIO` | ej. `Lun - Sáb: 8:00 AM - 6:00 PM` |

4. **Deploy**. Luego vuelve al proyecto de la API y ajusta `CORS_ORIGINS` con la
   URL final del frontend (y tu dominio, si tienes) → **Redeploy**.

## 5. Dominio propio (opcional)

- Web: Vercel → `autonegocio-web` → Settings → Domains → `www.tudominio.co`
- API: Vercel → `autonegocio-api` → Settings → Domains → `api.tudominio.co`
- Actualiza `NEXT_PUBLIC_API_URL` y `CORS_ORIGINS` y redespliega ambos.

## 6. Verificación

- [ ] `/health` de la API responde `ok`
- [ ] Login en `/login` con el admin del paso 2
- [ ] Crear un vehículo en **Inventario**, subir una foto y verlo en `/catalogo`
- [ ] Enviar el formulario **Vender** y verlo en **Leads**
- [ ] **Oportunidades → Buscar ahora** trae anuncios

## Seguridad de la API

Público (sin login): `GET /vehiculos/catalogo`, `GET /vehiculos/catalogo/{id}`,
`POST /clientes` (formularios *Vender* y *Contacto*), `POST /auth/login`.
Todo lo demás requiere token de administrador. `/scraping/cron` exige `CRON_SECRET`.

## Desarrollo local

Sin variables de Supabase, el backend usa SQLite (`autonegocio.db`) y guarda
las fotos en `uploads/`:

```bash
python -m uvicorn backend.main:app --reload --port 8000
npm --prefix frontend run dev
```
