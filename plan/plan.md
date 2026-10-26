# Expediente oftalmológico: una sola evaluación por paciente por día

Al abrir el expediente de un paciente, el sistema debe continuar la evaluación que ya se inició hoy para ese paciente en lugar de crear una nueva cada vez. Así se mantiene una única "sesión" de evaluación por paciente durante todo el día.

## Para quién es
Médicos oftalmólogos y personal con acceso a evaluaciones (incluye el rol Administrador IGSS) que abren el expediente del mismo paciente varias veces en un día.

## Problema actual
Hoy, cada vez que se abre el expediente de un paciente y se empieza a escribir (o se autollena el motivo), se crea un registro de evaluación nuevo. Resultado: múltiples evaluaciones duplicadas del mismo paciente en el mismo día.

## Qué cambia (experiencia)
- Al abrir el expediente de un paciente, si ya existe una evaluación de ese paciente con fecha de **hoy**, el expediente la abre y la continúa (misma nota, se sigue editando sobre ella).
- La evaluación del día es **compartida**: si otro médico la inició hoy, al abrir el expediente se continúa esa misma evaluación (no se crea una por médico).
- Si el paciente **no** tiene ninguna evaluación de hoy, se abre una evaluación en blanco que pasa a ser "la del día" al guardarse por primera vez.
- Se conserva el botón **"Nueva evaluación"** para los casos en que a propósito se necesite crear una evaluación adicional el mismo día (p. ej. una segunda consulta). Es una acción manual y explícita; el comportamiento por defecto sigue siendo continuar la del día.
- El historial del paciente sigue mostrando las evaluaciones de días anteriores y se pueden abrir para revisión, igual que hoy.

## Flujo del usuario
1. El usuario abre el expediente de un paciente (desde Pacientes, Agenda o el menú).
2. El sistema busca si ese paciente ya tiene una evaluación con fecha de hoy.
3. Si existe → la abre y se continúa editando sobre esa misma evaluación.
4. Si no existe → se muestra una evaluación en blanco; al escribir y guardarse por primera vez, queda registrada como la evaluación de hoy.
5. Si el usuario necesita una evaluación extra el mismo día, pulsa "Nueva evaluación" de forma explícita.

## Definición de "hoy"
El día se calcula con la zona horaria de Guatemala (la misma que ya usa el sistema). Si por datos previos existieran varias evaluaciones de hoy para un paciente, se continúa la más reciente del día.

## Sobre Google Calendar
Consulta respondida: actualmente la aplicación **no** tiene integración ni tarea programada (cron) con Google Calendar. No se realiza ningún trabajo al respecto en esta corrección.

## Fases de implementación

### Fase 1 (MVP, se construye ahora)
- Al abrir el expediente de un paciente, continuar automáticamente la evaluación de hoy de ese paciente si existe; si no, iniciar una en blanco que se registra como la del día al primer guardado.
- Reutilización compartida entre médicos (una evaluación del día por paciente, sin importar quién la creó).
- Mantener el botón "Nueva evaluación" como acción manual para crear una evaluación adicional el mismo día.
- Evitar que al reabrir el expediente se generen registros nuevos/duplicados del mismo día.

### Fase 2 (futuro)
- Aviso visible cuando la evaluación del día ya fue iniciada por otro médico (para dar contexto de quién la abrió).
- Resolución de posibles duplicados ya existentes de días pasados (herramienta para fusionar o limpiar duplicados del mismo día).

### Fase 3 (futuro)
- Control de edición simultánea (si dos personas abren la misma evaluación del día a la vez), para evitar que se sobreescriban cambios.

## Supuestos
- "Mismo día" = día calendario en zona horaria de Guatemala.
- La reutilización aplica cada vez que el expediente se abre para un paciente concreto, sin importar el punto de entrada (Pacientes, Agenda o menú).
- Si hoy ya hay varias evaluaciones del paciente (por duplicados previos), se continúa la más reciente del día; no se eliminan automáticamente las otras en esta fase.
- Las evaluaciones de días anteriores no se modifican: siguen disponibles solo para revisión en el historial.
- El botón "Nueva evaluación" sigue disponible para todos los roles que ya pueden crear/editar evaluaciones.
- No se toca el sellado manual ni ninguna otra lógica del expediente fuera de la apertura/continuación de la evaluación del día.
