# Sitemap y usabilidad MVP

## Rutas

| Ruta | Propósito | Estado |
| --- | --- | --- |
| `/` | Inicio y selección de experiencia | Inicial |
| `/tarot` | Entrada a una lectura de tarot | Preparada |
| `/suenos` | Entrada a una interpretación de sueños | Preparada |
| `/historial` | Conversaciones guardadas del usuario | Pendiente de autenticación |
| `/dev` | Pruebas técnicas de API, S3, RAG y chat | Conservada |

## Flujo principal

```text
Inicio → Tarot o Sueños → Consulta → Orquestador → Respuesta → Historial
```

La autenticación se añadirá antes de guardar y mostrar contenido personal.
El área `/dev` permanecerá separada de la experiencia de producto.

## Criterios de usabilidad

- La pantalla inicial ofrece dos acciones principales y reconocibles.
- El sidebar permite volver siempre a Inicio, Tarot, Sueños e Historial.
- Las pantallas de Tarot y Sueños explican el propósito antes de solicitar datos.
- El historial informa de que será privado y requiere autenticación.
- Las herramientas técnicas no interfieren con el flujo de producto y están en `/dev`.
