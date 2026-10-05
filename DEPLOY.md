# Deploy AutoNegocio

## Backend — Railway

1. Crear cuenta en [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Seleccionar el repositorio AutoNegocio
4. Railway detectará el Dockerfile automáticamente
5. Configurar variables de entorno:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/autonegocio
SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_urlsafe(48))">
CORS_ORIGINS=https://tu-frontend.vercel.app,https://www.autonegocio.co
DEBUG=false
ANTHROPIC_API_KEY=sk-ant-... (opcional, para agentes IA)
```

> ⚠️ `SECRET_KEY` y `CORS_ORIGINS` son obligatorios en producción: el valor por
> defecto de `SECRET_KEY` está en el repositorio y permitiría falsificar sesiones.

> ⚠️ Las fotos se guardan en `uploads/` dentro del contenedor. En Railway, monta un
> **Volume** en `/app/uploads` o se perderán en cada deploy.

6. Railway auto-deploya en cada push

## Frontend — Vercel

1. Crear cuenta en [vercel.com](https://vercel.com)
2. New Project → Import GitHub repo
3. **Root Directory**: `frontend`
4. Framework: Next.js (auto-detectado)
5. Configurar variable de entorno:

```
NEXT_PUBLIC_API_URL=https://tu-backend.railway.app
```

6. Deploy

## Post-Deploy

Crear usuario admin (elige una opción):

- **Desde la web**: entra a `/login` → pestaña *Registrarse*. Solo la **primera**
  cuenta se puede crear así; después, el registro exige estar logueado como admin.
- **Por script** (en el shell de Railway o local apuntando a la DB de producción):

```bash
ADMIN_USERNAME=miguel ADMIN_PASSWORD='una-clave-larga' python -m scripts.create_admin
```

## Seguridad de la API

Público (sin login): `GET /vehiculos/catalogo`, `GET /vehiculos/catalogo/{id}`,
`POST /clientes` (formulario *Vender*), `POST /auth/login`.
Todo lo demás (inventario, precios de compra, clientes, transacciones,
oportunidades, mercado, agentes IA, scraping) requiere token de administrador.

## Dominios Personalizados

- Backend: Configurar en Railway → Settings → Domains
- Frontend: Configurar en Vercel → Settings → Domains
- Ejemplo: `api.autonegocio.co` y `www.autonegocio.co`
