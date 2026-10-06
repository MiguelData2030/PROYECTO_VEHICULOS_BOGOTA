# Despliegue a producción — Supabase + Render

```
  clientes ──► Render static site  (frontend/, Next.js exportado)  gratis, siempre activo
                     │ NEXT_PUBLIC_API_URL
               Render web service  (FastAPI, plan free)
                     │                      ▲ ping cada 10 min (GitHub Actions)
               Supabase  (PostgreSQL + Storage de fotos)
```

Todo se crea con `render.yaml` (Blueprint) y se redespliega solo con cada
`git push` a `main`.

## Paso 1 — Supabase (2 datos)

En el proyecto `VEHICULOS_BOGOTA`:

1. **Connect** (botón verde arriba) → **Connection String** → **Transaction pooler**
   (puerto 6543). Cambia `[YOUR-PASSWORD]` por la contraseña de la base de datos
   (si no la recuerdas: Project Settings → Database → *Reset database password*).
   → este es `DATABASE_URL`.
2. **Project Settings → API Keys → Secret keys → New secret key** (`sb_secret_...`).
   → este es `SUPABASE_SERVICE_ROLE_KEY`.

## Paso 2 — Render (clics)

1. Entra a [render.com](https://render.com) → **Get Started** → **GitHub**.
2. **New +** → **Blueprint** → elige `PROYECTO_VEHICULOS_BOGOTA` → **Connect**.
3. Render muestra los 2 servicios y pide los valores marcados:
   - `DATABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` (paso 1)
   - `NEXT_PUBLIC_WHATSAPP` (ej. `573001234567`), `NEXT_PUBLIC_EMAIL`, `NEXT_PUBLIC_TELEFONO` (opcional)
   - `ANTHROPIC_API_KEY` (opcional; déjalo vacío si no usas los agentes IA)
4. **Apply**. En ~5 minutos quedan:
   - Web: `https://autonegocio-web.onrender.com`
   - API: `https://autonegocio-api.onrender.com/health` → `{"status":"ok"}`

Las tablas y el bucket de fotos se crean solos. `SECRET_KEY` la genera Render.

> Si Render le agrega un sufijo a algún nombre (ej. `autonegocio-api-x1y2`),
> actualiza `NEXT_PUBLIC_API_URL` en el servicio web y la URL de
> `.github/workflows/keepalive.yml`.

## Paso 3 — Tu usuario administrador

Abre `https://autonegocio-web.onrender.com/login` → **Registrarse**.
Solo la **primera** cuenta se puede crear así; después el registro queda cerrado.

## Cómo funciona en el plan gratis

- La **web** es estática: siempre rápida, sin límite de "dormir".
- La **API** se duerme tras 15 min sin uso. `.github/workflows/keepalive.yml`
  la despierta cada 10 min de 6:00 a 22:59 (hora Bogotá). De noche la primera
  visita puede tardar ~1 minuto.
- Mientras está despierta, la API ejecuta el scraping cada 6 horas
  (`SCRAPING_INTERVAL_MINUTES`). También: panel → *Ejecutar Scraping*.
- Para que nunca se duerma: plan **Starter** de Render (USD 7/mes) en el servicio API.

## Verificación

- [ ] `/health` de la API responde `ok`
- [ ] Login en `/login`
- [ ] Crear un vehículo en **Inventario**, subir una foto y verlo en `/catalogo`
- [ ] Enviar el formulario **Vender** y verlo en **Leads**
- [ ] **Oportunidades → Buscar ahora** trae anuncios

## Seguridad de la API

Público (sin login): `GET /vehiculos/catalogo`, `GET /vehiculos/catalogo/{id}`,
`POST /clientes` (formularios *Vender* y *Contacto*), `POST /auth/login`.
Todo lo demás requiere token de administrador.

## Desarrollo local

Sin variables de Supabase, el backend usa SQLite (`autonegocio.db`) y guarda
las fotos en `uploads/`:

```bash
python -m uvicorn backend.main:app --reload --port 8000
npm --prefix frontend run dev
```
