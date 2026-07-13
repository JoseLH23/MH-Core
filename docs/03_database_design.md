# MH Core - Diseño de Base de Datos

## Objetivo

La base de datos será el repositorio central de toda la información del ecosistema MH Core.

Todas las aplicaciones utilizarán la misma base de datos mediante la API del Core.

---

# Principios

* Una sola fuente de información.
* Evitar duplicar datos.
* Relaciones claras entre entidades.
* Escalable para nuevos módulos.
* Seguridad desde el diseño.

---

# Entidades principales

## Usuarios

Responsabilidad:

* Registro
* Inicio de sesión
* Perfil
* Roles

Campos principales:

* id
* nombre
* correo
* contraseña_hash
* rol
* estado
* fecha_creacion

---

## Roles

Campos:

* id
* nombre
* descripcion

Ejemplos:

* Administrador
* Operador
* Cliente
* Visitante

---

## Aplicaciones

Permite registrar las aplicaciones conectadas al Core.

Ejemplos:

* MindHigh
* EjiXhole

Campos:

* id
* nombre
* version
* estado

---

## Reservaciones (EjiXhole)

Campos:

* id
* usuario_id
* fecha
* personas
* servicio
* estado

---

## Servicios (EjiXhole)

Campos:

* id
* nombre
* descripcion
* precio
* disponible

---

## Contenido (MindHigh)

Campos:

* id
* titulo
* categoria
* guion
* estado
* fecha

---

## Tendencias (MindHigh)

Campos:

* id
* plataforma
* tema
* puntuacion
* fecha

---

## Archivos

Campos:

* id
* nombre
* tipo
* ruta
* tamaño
* fecha

---

# Relaciones

Usuario
│
├── Reservaciones
├── Contenido
└── Archivos

Aplicaciones
│
├── MindHigh
└── EjiXhole

---

# Tecnologías

Durante el desarrollo:

* SQLite

En producción:

* PostgreSQL

---

# Objetivo de la primera versión

La primera versión solo implementará:

* Usuarios
* Roles
* Aplicaciones

El resto de las tablas se desarrollará conforme se construyan los módulos correspondientes.
