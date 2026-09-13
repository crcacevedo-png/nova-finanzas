# Plan: Mejorar la búsqueda de pacientes por nombre

## Problema actual
Al buscar pacientes por nombre:
- Si se escribe el nombre y el apellido juntos (por ejemplo "Juan Pérez"), NO encuentra
  al paciente. Hoy el sistema busca la frase completa dentro de un solo campo (el nombre
  por un lado, o el apellido por otro), y como ningún campo contiene "Juan Pérez" completo,
  no hay coincidencia.
- Consecuencia: pacientes que sí existen no aparecen cuando se combina nombre + apellido,
  y da la sensación de que "no encuentra a todos".
- (Nota: hoy la búsqueda ya ignora mayúsculas/minúsculas y acentos. Ese comportamiento se
  mantiene y se deja verificado.)

## Comportamiento nuevo
- El texto de búsqueda se separa en palabras. Cada palabra debe aparecer en el nombre o en
  el apellido del paciente, en cualquier orden. Ejemplos:
  - "juan" → lista TODOS los pacientes cuyo nombre o apellido contenga "juan".
  - "juan perez" → lista todos los que tengan "juan" Y "perez" en su nombre/apellido
    (por ejemplo "Juan Pérez", "Juan Carlos Pérez López", etc.).
  - "perez juan" → mismo resultado (el orden no importa).
- No distingue mayúsculas/minúsculas ni acentos: María = maria = MARIA = MARÍA.
- Se mantiene la posibilidad de buscar también por número de expediente, DPI y teléfono.
- Lista TODOS los coincidentes: en el listado de Pacientes con su paginación normal, y en
  el autocompletado (usado en otras pantallas) ampliando el tope para no cortar resultados.

## Decisiones asumidas (avisar si se prefiere distinto)
- Con varias palabras se exige que aparezcan TODAS (búsqueda más precisa para encontrar a
  una persona concreta), en lugar de traer cualquiera que tenga al menos una palabra.
- La mejora se aplica en los dos buscadores para que se comporten igual:
  (a) el buscador del listado de Pacientes y
  (b) el autocompletado de pacientes usado en Punto de Venta, Agenda y demás pantallas.
- El autocompletado, que hoy corta en 10 resultados, se amplía (hasta 50) para "listar
  todos los posibles" sin recortar de más.

## Fuera de alcance
- No se agregan campos nuevos de "segundo nombre" / "segundo apellido". El sistema guarda
  el nombre y los apellidos en dos campos existentes; la mejora trabaja sobre esos campos
  (cada uno puede contener varias palabras).
