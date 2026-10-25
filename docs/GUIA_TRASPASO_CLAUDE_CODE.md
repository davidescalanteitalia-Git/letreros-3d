# GUÍA COMPLETA DE TRASPASO — LETREROS 3D STUDIO
Estado verificado del repositorio: 25 de octubre de 2026.

## 1. Enlaces y accesos
- **Repositorio GitHub (origen del código):** https://github.com/davidescalanteitalia-Git/letreros-3d
- **Rama actual:** main.
- **Visibilidad al verificar:** PUBLIC. Cambiar a private tras configurar acceso desde Coolify (GitHub App/deploy key) o podrá fallar el siguiente deploy.
- **Web publicada (observada en captura del usuario):** https://letreros.d4digitalstudio.it
- **Coolify (administración):** https://coolify.tiendaonline.it/
- **Proveedor de servidores:** Hetzner: https://console.hetzner.com/
- **DNS:** Cloudflare: https://dash.cloudflare.com/
- **Servidor de destino en Coolify:** localhost, donde se ejecuta Coolify.
- **Proyecto de Coolify:** Letreros 3D → production → letreros-3d-studio.
- **Build:** Dockerfile desde GitHub, branch main, base directory /, Dockerfile /Dockerfile, Nginx puerto interno 80.
- **Dominio:** https://letreros.d4digitalstudio.it ; registro A en d4digitalstudio.it a 91.99.230.7, DNS only, según captura de Cloudflare. Confirmar IP en servidores antes de rehacer DNS.
- **API Coolify:** una Action de verificación de solo lectura consultó /api/v1/projects y terminó verde tras corregir formato del token. Esto NO prueba permiso para crear/desplegar recursos.

## 2. En qué lugar está cada cosa
- Código fuente y documentación: GitHub. Es la fuente de verdad y NO estaba clonado en PC al cerrarse las instrucciones previas.
- Despliegue: imágenes/contenedores Docker en el servidor Hetzner gestionados por Coolify. No editar directamente archivos dentro del contenedor: los redeploys los reemplazan.
- PC Windows: clonar repositorio a C:\Proyectos\letreros-3d (ruta sugerida, no creada por ChatGPT).
- Cloudflare: exclusivamente DNS y posterior control de acceso.
- Supabase: disponible para el usuario, PERO NO integrado al proyecto.
- n8n: disponible para el usuario, PERO NO integrado al proyecto.

## 3. Archivos efectivamente existentes
```text
letreros-3d/
├── index.html                  # editor web monolítico, HTML/CSS/JS v0.3
├── Dockerfile                  # nginx:1.27-alpine + healthcheck, puerto 80
├── README.md                   # instrucciones iniciales; puede estar desactualizado
├── CLAUDE.md                   # instrucciones para el agente de programación
├── config/
│   └── PERFIL_A2L_PETG.md      # perfil de impresora y hipótesis de calibración
├── docs/
│   ├── PLAN_DEL_PROYECTO.md
│   ├── 01_ANALISIS_COMPETITIVO.md
│   ├── 02_ESPECIFICACION_PROFESIONAL.md
│   ├── 03_HOJA_DE_RUTA.md
│   ├── 04_CATALOGO_FUNCIONAL.md
│   └── GUIA_TRASPASO_CLAUDE_CODE.md
└── .github/
    └── workflows/
        └── verificar-coolify.yml
```
Este árbol muestra archivos conocidos y la incorporación de estos documentos; ejecutar `git ls-files` para una lista completa si aparecen otros.

## 4. Qué está listo y qué NO
**Sí existe:** sitio desplegable, editor de texto, selectores de tipografía (10 Google Fonts), tipos de iluminación simulados, parámetros mm, modos de letras individuales/unidas/base (declarativos), guardar/cargar JSON, boceto SVG (texto editable), Dockerfile, docs.

**No existe todavía:** exportación STL auténtica, motor CAD, geometría sólida, cámaras LED, letras huecas imprimibles, tapas ensamblables, división automática, uniones reales, gestión de clientes, cuentas, base de datos, integración con Bambu Studio, export 3MF/DXF industrial, cálculos fiables de costes, backend API. No confundir las funciones descritas en documentación con funciones implementadas.

## 5. Modalidades solicitadas y capacidades objetivo
Letras caja; corpóreas sin luz; frontal iluminada; retroiluminada halo; doble luz frontal + posterior; neón flex; frente opaco con cuerpo luminoso; letras unidas y divididas por cama; letras sobre base; logotipo SVG. Componentes: cuerpo, tapa, fondo, rebajes, difusor, LED, separadores, cableados, conectores, tornillos/imanes, plantillas. Impresora Bambu Lab A2L, boquilla 0.4 mm, PETG, volumen nominal 330x320x325 mm. Medidas útiles conservadoras y holguras son hipótesis hasta fabricar probetas.

## 6. Diez fuentes implementadas en la interfaz
Montserrat, Poppins, Roboto, Oswald, Bebas Neue, Playfair Display, Lobster, Pacifico, Dancing Script y Great Vibes. En CAD hay que obtener y versionar legalmente las fuentes para convertir a curvas y asegurar la misma tipografía usada en la vista. La versión de navegador carga Google Fonts por Internet.

## 7. Instalación de Claude Code en Windows
Prerequisitos: cuenta de GitHub con acceso de lectura/escritura; Git for Windows; opcional VS Code; acceso a Claude Code con plan o configuración compatible.
Documentación oficial: https://code.claude.com/docs/en/overview y https://github.com/anthropics/claude-code .

**A. Clonar el proyecto** — abre PowerShell y ejecuta:
```powershell
git --version
New-Item -ItemType Directory -Force C:\Proyectos
cd C:\Proyectos
git clone https://github.com/davidescalanteitalia-Git/letreros-3d.git
cd letreros-3d
git status
git ls-files
```
Autentícate con tu cuenta GitHub si solicita acceso. Si ya existe una carpeta clonada, no repitas clone; entra en ella y usa `git pull` tras comprobar cambios locales.

**B. Instalar Claude Code** (PowerShell; documentación oficial actual):
```powershell
irm https://claude.ai/install.ps1 | iex
claude --version
cd C:\Proyectos\letreros-3d
claude
```
Antes de ejecutar un instalador remoto, verificar que procede del dominio oficial de Anthropic. Claude Code solicitará inicio de sesión; no pegar contraseñas o API keys en chat. Alternativa `winget install Anthropic.ClaudeCode`, si está disponible. Si se usa VS Code: `code .` desde la carpeta o File → Open Folder.

**C. Preparación inicial segura:**
```powershell
git switch -c feat/motor-cad-inicial
git status
```
Iniciar Claude Code dentro de esa carpeta. Leer CLAUDE.md y la guía. Pedir primero auditoría y propuesta, después cambios pequeños en nueva rama.

## 8. Primer prompt recomendado para Claude Code
```text
Lee CLAUDE.md y todos los documentos de docs/, config/, README.md, Dockerfile e index.html. Audita el estado real del proyecto y distingue lo implementado de lo planificado. Nuestra meta es un generador propio de letras corpóreas para Bambu Lab A2L (boquilla 0,4 mm, PETG). Primero presenta arquitectura mínima y riesgos. Después crea en una rama feat/* un prototipo local, con pruebas, que tome una letra y medidas en milímetros y produzca STL auténtico, manifold, comprobable en Bambu Studio. No cambies DNS, Coolify, Hetzner, secretos, producción ni branch main. No copies código propietario de competidores. Pide aprobación antes de acciones externas/despliegues. Documenta comandos de instalación y validación.
```

## 9. Flujo de desarrollo recomendado
1. `git status` y `git pull`; crea rama `feat/...`.
2. Claude Code inspecciona archivos; propone tareas pequeñas con tests y aceptación.
3. Implementa y prueba localmente; inspecciona diff con `git diff`.
4. Test con STL abierto en Bambu Studio y pieza física de calibración.
5. `git add .`; `git commit -m "feat: ..."`; `git push -u origin feat/...`.
6. Crear Pull Request en GitHub, revisar y fusionar a main solo cuando las pruebas pasen.
7. Coolify usa main: desplegar voluntariamente tras validar; comprobar logs, healthcheck y dominio.
8. Rollback en Coolify si despliegue falla. No exponer aplicaciones sin autenticación cuando contengan proyectos privados.

## 10. Próxima arquitectura sugerida (no implementada)
- Editor: React + TypeScript + Three.js / viewer de geometría real.
- API: FastAPI Python y motor paramétrico CadQuery / OpenCascade.
- Mallas: export STL, chequeo manifold y dimensiones; considerar trimesh como validador.
- Jobs grandes: cola después de medir consumos.
- Guardado: JSON por proyecto primero; Supabase opcional en fase posterior.
- Infra: frontend y backend en recursos Docker separados en Coolify, proxy HTTPS con Cloudflare.
- CI: pruebas unitarias, lint, evaluación de licencias, artefactos de prueba; no dejar secretos en el repositorio.

## 11. Seguridad y permisos
Se compartieron anteriormente claves API de Coolify y Hetzner en mensajes de chat. Considerarlas comprometidas: revocar TODAS las claves expuestas y generar otras, sin pegarlas en chats. Guardarlas exclusivamente como secretos de GitHub Actions, variables seguras de Coolify u otro gestor. Dar permisos mínimos para tareas concretas. La Action existente solo necesita acceso de lectura. Un token de escritura o deploy no debería reutilizarse para diagnósticos.

El repositorio estaba PUBLIC al verificarlo; cambiar a PRIVATE en GitHub Settings si no se desea publicar el código. Antes de hacerlo, configurar GitHub App o deploy key en Coolify y comprobar acceso al código. No dar permisos de administrador del servidor a Claude Code como primera etapa.

## 12. Problemas conocidos / alertas
- README puede describir v0.1, mientras index.html ya es v0.3.
- UI está en un solo HTML: se debe refactorizar gradualmente, no destruir el despliegue que funciona.
- Vista preliminar basada en SVG/estilos no equivale a CAD. Texto SVG exportado no son curvas de corte.
- Diez fuentes cargadas desde Google Fonts no aportan directamente contornos CAD.
- La infraestructura probada solo sirvió contenido estático; un motor OCC puede necesitar recursos adicionales.
- Una pantalla del usuario mostró la web operativa, pero no confirma que la última versión de GitHub esté ya publicada. Comprobar antes de afirmar sincronización.
- Realizar siempre pruebas de tolerancia PETG e iluminación segura.

## 13. Referencias y documentación
Referencias funcionales en `docs/01_ANALISIS_COMPETITIVO.md` (PROLED3D, LumiSign 3D, Volucore, LetraMaker, Cartelito, SignFlex3D, etc.).
Guía Claude Code: https://code.claude.com/docs/en/overview
Despliegues: https://coolify.io/docs/core/build-deployment-model
GitHub sources: https://coolify.io/docs/applications/sources/github/overview
