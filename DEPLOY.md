# Deploy AutoNegocio

## Backend — Railway

1. Crear cuenta en [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Seleccionar el repositorio AutoNegocio
4. Railway detectará el Dockerfile automáticamente
5. Configurar variables de entorno:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/autonegocio
SECRET_KEY=tu-clave-secreta-segura-cambiar-en-produccion
ANTHROPIC_API_KEY=sk-ant-... (opcional, para agentes IA)
```

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

Crear usuario admin:
```bash
# En Railway, abrir shell o ejecutar localmente apuntando a la DB de producción
python -m scripts.create_admin
```

## Dominios Personalizados

- Backend: Configurar en Railway → Settings → Domains
- Frontend: Configurar en Vercel → Settings → Domains
- Ejemplo: `api.autonegocio.co` y `www.autonegocio.co`
