# MH Core - Arquitectura

# Arquitectura General

MH Core está diseñado utilizando una arquitectura modular.

Cada módulo tiene una responsabilidad específica.

Los módulos se comunican mediante APIs internas y servicios compartidos.

Ningún módulo debe depender directamente de otro módulo de aplicación.

Todos deben depender únicamente del Core.

---

# Diagrama General

```
                     MH CORE

        ┌────────────────────────────┐
        │      CORE PLATFORM         │
        └────────────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
 Authentication Database    API Gateway
      │           │           │
      ├───────────┼───────────┤
      │           │           │
 Storage     Notifications  AI Engine
      │
      │
 ┌────┴─────────────────────────────┐
 │                                  │
MindHigh                       EjiXhole
 │                                  │
 └──────────────┬───────────────────┘
                │
             Usuarios
```

---

# Módulos del Core

## Authentication

Responsable de:

* Login
* Logout
* Registro
* Recuperación de contraseña
* Tokens
* Sesiones

---

## Users

Responsable de:

* Usuarios
* Roles
* Permisos
* Perfil

---

## Database

Responsable de:

* Conexión
* Consultas
* Migraciones
* Modelos

---

## API Gateway

Responsable de:

* Recibir peticiones
* Validar solicitudes
* Enviar respuestas
* Conectar módulos

---

## Storage

Responsable de:

* Imágenes
* Videos
* Documentos
* Archivos

---

## Notifications

Responsable de:

* Correos
* WhatsApp
* Push Notifications
* Alertas

---

## AI Engine

Responsable de:

* IA
* Tendencias
* Automatización
* Recomendaciones

---

# Aplicaciones

## MindHigh

Utilizará:

* AI Engine
* Storage
* API
* Database
* Authentication

Funciones:

* Investigación
* IA
* Videos
* Contenido
* Automatización

---

## EjiXhole

Utilizará:

* Database
* API
* Storage
* Authentication

Funciones:

* Reservaciones
* Clientes
* Servicios
* Finanzas
* Administración

---

# Flujo General

Usuario

↓

Aplicación

↓

API Gateway

↓

Autenticación

↓

Servicio correspondiente

↓

Base de datos

↓

Respuesta

↓

Usuario

---

# Regla Arquitectónica

Las aplicaciones nunca accederán directamente a la base de datos.

Siempre deberán comunicarse mediante la API del Core.

Esto garantiza seguridad, escalabilidad y facilidad de mantenimiento.
