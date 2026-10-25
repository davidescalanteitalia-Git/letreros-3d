# Letreros 3D Studio

Aplicación propia para diseño y futura fabricación de letreros corpóreos impresos en 3D.

## Estado actual
**Editor web v0.3 (`index.html`):** prototipo visual en español con texto, 10 fuentes, tipos de letrero simulados, medidas, guardar/abrir JSON. La web **no genera STL**.

**Motor de geometría M1 (`motor/`):** prototipo local en Python que genera el STL auténtico y validado de UNA letra maciza (Montserrat Bold, OFL). Sin caja hueca, LED ni división. Ver `motor/README.md` y `docs/05_INFORME_AUDITORIA.md`.

## Abrir localmente
Abre `index.html` en tu navegador para ver la demostración.

## Desplegar con Coolify
1. En Coolify: Projects → New Project → New Resource → Application.
2. Selecciona GitHub (con permisos al repositorio) o Public Repository si continúa público.
3. Repositorio: `davidescalanteitalia-Git/letreros-3d`; rama `main`.
4. Build pack: **Dockerfile**; Dockerfile path: `/Dockerfile`; puerto interno: `80`.
5. Desplegar y probar la URL temporal de Coolify.
6. En Cloudflare → DNS, crear un registro A para el subdominio deseado apuntando a la IP pública del servidor; empezar con DNS-only para comprobar HTTPS y enrutamiento.
7. En Coolify → Domains, establecer el dominio HTTPS y verificar certificado y respuesta antes de activar proxy de Cloudflare.
8. Añadir autenticación/restricción de acceso antes de cargar información privada. Nunca subir contraseñas ni tokens al repositorio.

**Precaución:** el sitio no incorpora login y será público si se publica con dominio accesible. Para un sitio estrictamente privado, proteger el acceso primero con Cloudflare Access u otra autenticación.

## Arquitectura futura
React + TypeScript + Three.js en frontend; FastAPI + motor CAD para export STL, bajo pruebas de medidas y validación de malla. Véase `docs/02_ESPECIFICACION_PROFESIONAL.md`.

## Pendiente
- Confirmar modelo exacto de impresora y volumen útil.
- Construir motor CAD y validar STL.
- Probar impresión y encajes.
- Configurar despliegue seguro.
