# Despliegue del runtime Marketing en Render

## Objetivo

Operar únicamente la generación gobernada de campañas que necesita el panel
administrativo de EjiXhole. Este servicio no expone investigación, agentes,
automatización, video, publicación, analítica completa ni búsqueda libre del
conocimiento.

## Superficie permitida

Pública y sin datos internos:

- `GET /health/live`
- `GET /health/ready`

Privada, con `X-Service-ID: ejixhole-backend` y `X-API-Key`:

- `GET /mindhigh/marketing/status`
- `POST /mindhigh/marketing/campaigns/draft`

En producción Swagger, ReDoc y OpenAPI quedan deshabilitados.

## Bundle aprobado

La fuente es el artefacto privado generado por el workflow de `MH-Knowledge`.
Debe extraerse únicamente el archivo:

```text
approved-bundle.json
```

En Render se registra como Secret File con ese mismo nombre. Render lo monta en:

```text
/etc/secrets/approved-bundle.json
```

`render.yaml` ya configura `MH_KNOWLEDGE_BUNDLE_PATH` con esa ruta. El servicio
queda `unavailable` si el archivo falta, fue alterado, contiene conocimiento
vencido o no incluye los documentos esenciales de marketing.

## Credencial de EjiXhole

Generar una clave aleatoria de 48 bytes o más. El mismo valor se configura en:

- MH-Core Marketing: `MH_CORE_EJIXHOLE_KEY`
- C-Ejixhole-Backend: `MH_CORE_EJIXHOLE_KEY`

No reutilizar `MH_CORE_SERVICE_KEY`: esa credencial protege la dirección
contraria, de MH-Core hacia el backend de EjiXhole.

El backend también necesita:

```text
MH_CORE_URL=https://DOMINIO-REAL-DEL-SERVICIO
```

## Creación mediante Blueprint

1. Crear un Blueprint desde este repositorio privado.
2. Render detecta `render.yaml`.
3. Confirmar el servicio `mh-core-marketing`.
4. Registrar `MH_CORE_EJIXHOLE_KEY` cuando Render la solicite.
5. Agregar el Secret File `approved-bundle.json`.
6. Desplegar.

El comando de arranque usa un solo worker. La versión inicial no necesita
PostgreSQL, Gemini, Groq, YouTube ni un worker de trabajos, porque la generación
de borradores es determinista y no conserva estado.

## Verificación

1. `/health/live` debe responder `200` con `{"status":"ok"}`.
2. `/health/ready` debe responder `200` con `{"status":"ready"}`.
3. Sin encabezados privados, `/mindhigh/marketing/status` debe responder `401`.
4. El panel EjiXhole debe cambiar de `conexión pendiente` a `Marketing listo`.
5. Generar una campaña de prueba sin precio, promoción, horario ni disponibilidad.
6. Confirmar cuatro citas de MH-Knowledge y `requires_human_approval: true`.

## Rotación del conocimiento

Cuando MH-Knowledge publique un bundle nuevo:

1. descargar el artefacto del commit aprobado;
2. reemplazar el Secret File;
3. desplegar nuevamente;
4. verificar `/health/ready`;
5. confirmar la nueva versión desde el panel.

MH-Core valida nuevamente el bundle. No se debe copiar el repositorio completo,
dar acceso a borradores ni guardar tokens de GitHub en el servicio.

## Reversión

Si el runtime deja de estar listo:

1. conservar el bundle anterior;
2. restaurarlo como Secret File;
3. volver al despliegue anterior;
4. comprobar salud y versión;
5. mantener el panel en modo no disponible hasta recuperar una fuente válida.
