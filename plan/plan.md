# Plan: Elegir el calendario de Google para sincronizar (y corregir "no importa nada")

## Problema a resolver
Hoy, al conectar un médico, el sistema crea un calendario nuevo y VACÍO llamado
"NovaVision - Citas" y el botón "Actualizar" solo lee de ese calendario. Como las citas reales
del médico están en otro calendario (su principal o uno compartido), no se importa ningún
paciente. Además no hay forma de elegir el calendario de origen.

## Qué cambia (comportamiento nuevo)
1. **Selección de calendario por médico.** Después de conectar la cuenta de Google del médico,
   se muestra la lista de TODOS los calendarios a los que esa cuenta tiene acceso (propios y
   compartidos, incluido el principal). El SuperAdmin elige cuál usar para ese médico. Ese
   calendario pasa a ser el origen (lectura) y destino (escritura) de la sincronización.
2. **Se deja de forzar el calendario "NovaVision - Citas".** Se usa el calendario elegido. (El
   que se haya creado antes queda sin efecto; se puede ignorar o borrar manualmente en Google.)
3. **"Actualizar" importa de verdad.** Al sincronizar, se leen los eventos del calendario
   elegido **desde hoy en adelante** y **todos** se convierten en citas del sistema para ese
   médico (el título del evento se usa como nombre; sin ficha de paciente asociada, marcadas
   como "de Google"). Los cambios de fecha/hora y las cancelaciones hechas en Google se
   reflejan en las citas; las citas creadas en el sistema se envían a ese mismo calendario.
4. **Al cambiar de calendario** para un médico, la próxima sincronización parte de cero (vuelve
   a leer todo desde hoy) para el calendario recién elegido.
5. **Varias cuentas con el mismo Client ID/Secret.** Cada médico conecta su propia cuenta de
   Google (una distinta por médico) usando las mismas credenciales; para cada uno se elige su
   calendario. Esto ya es compatible; solo se agrega el paso de elegir calendario.

## Cómo se verá
En el diálogo "Google Calendar" de la Agenda, cada médico conectado mostrará un selector con
sus calendarios disponibles y el calendario actualmente elegido. Cambiarlo actualiza el origen
de la sincronización. Los médicos sin conectar siguen con el botón "Conectar".

## Decisiones ya confirmadas
- Elegir entre **cualquier** calendario accesible por la cuenta (propios + compartidos), incl.
  el principal del médico.
- Importar **todos** los eventos del calendario elegido.
- Rango: **desde hoy en adelante**.
- **Varias cuentas** distintas (una por médico) con el mismo Client ID/Secret.

## Consideraciones (para tu visto bueno)
- Como se importan TODOS los eventos, los eventos personales del médico (si el calendario
  elegido es su calendario personal) también aparecerán como citas en la Agenda. Si más
  adelante quieres filtrarlos (por palabra clave o etiqueta), se puede agregar; por ahora
  entran todos, según lo acordado.
- Estas citas importadas no tienen ficha de paciente (no hay forma de saber el paciente desde
  un evento de calendario); se muestran con el título del evento como nombre.

## Fuera de alcance
- Filtrar o clasificar automáticamente qué evento corresponde a qué paciente.
- Cambios en las credenciales de Google (siguen siendo las ya configuradas).
