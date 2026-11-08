# Paciente rápido desde Registrar Cirugía

Al registrar una cirugía, si el paciente aún no está en el sistema, se podrá crear al instante escribiendo solo su nombre, sin llenar el resto del formulario. Cuando el paciente se presenta a la cirugía, admisión lo encuentra en Pacientes y completa el resto de su expediente.

## Para quién es

- Personal que agenda/registra cirugías antes de que el paciente pase por admisión (coordinación, médicos, anestesia, y cualquier otro rol con permiso para crear pacientes).
- Admisión/recepción, que completa el expediente cuando el paciente llega físicamente a la cirugía.

## Funcionalidad principal y experiencia

- En "Registrar cirugía", el buscador de paciente sigue funcionando igual: si el nombre coincide con alguien ya registrado, se elige de la lista como hoy.
- Si no hay coincidencia, aparece una opción para crear un paciente nuevo con ese nombre tal cual se escribió, sin pedir ningún otro dato.
- Ese paciente queda creado de verdad en el sistema (no es un texto suelto): aparece en Pacientes y se puede volver a buscar y usar en cualquier otra cirugía o pantalla, igual que cualquier otro paciente.
- En el listado de Pacientes, ese registro muestra una etiqueta "Datos incompletos" hasta que se le complete género, fecha de nacimiento, teléfono e institución referente.
- Se agrega un filtro en Pacientes para ver únicamente los pacientes con "Datos incompletos", para que admisión los ubique rápido.
- Completar esos datos se hace con la pantalla de edición de pacientes de siempre; al guardar con esos campos llenos, la etiqueta desaparece sola.
- Esta forma de crear pacientes solo con el nombre está disponible únicamente desde "Registrar cirugía", y solo para quienes ya tienen permiso de crear pacientes. En el resto del sistema (Pacientes, Agenda, etc.) seguirá pidiéndose el formulario completo como hasta ahora.

## Flujo de uso

1. El usuario abre "Registrar cirugía" y escribe el nombre del paciente.
2. Si el paciente ya existe, lo selecciona de la lista como hoy.
3. Si no existe, ve la opción de crear un paciente nuevo con ese nombre y la selecciona.
4. La cirugía queda registrada y vinculada a ese paciente recién creado.
5. Cuando el paciente llega a la cirugía, admisión entra a Pacientes, filtra por "Datos incompletos", busca al paciente por nombre y completa género, fecha de nacimiento, teléfono, institución referente, etc. con la pantalla de edición normal.
6. Al guardar, la etiqueta "Datos incompletos" desaparece.

## Aspecto e interacción

No se introduce ninguna pantalla ni estilo nuevo: es una opción adicional dentro del mismo buscador de paciente de "Registrar cirugía", y una etiqueta más un filtro dentro de la tabla de Pacientes que ya existen. Todo respeta el aspecto actual de esas dos pantallas.

## Fases de implementación

**Fase 1 (MVP — se construye ahora)**
- Opción de crear paciente solo con el nombre dentro del buscador de "Registrar cirugía".
- El paciente queda creado de verdad, vinculado a la cirugía y disponible de inmediato en el resto del sistema.
- Etiqueta "Datos incompletos" visible en Pacientes para esos registros, más un filtro para listarlos.
- La etiqueta desaparece sola al completar género, fecha de nacimiento, teléfono e institución referente desde la edición normal de pacientes.

**Fase 2 (futuro)**
- Aviso para coordinación listando pacientes con cirugía próxima cuyo expediente sigue incompleto, para que no se pase ninguno antes de la fecha.
- Sugerencia de fusión con un paciente parecido ya existente al momento de crear, para evitar duplicados por error de tipeo.

**Fase 3 (futuro)**
- Llevar esta misma excepción de "crear solo con el nombre" a otros puntos de alta rápida del sistema (por ejemplo, Agenda), una vez validado el uso diario de la Fase 1.

## Supuestos

- El nombre escrito se separa en nombre/apellido por el primer espacio (la primera palabra como nombre, el resto como apellido); si se escribe una sola palabra, el apellido queda vacío hasta completarse.
- El paciente creado así recibe un número de expediente normal, asignado automáticamente igual que cualquier paciente nuevo.
- "Datos incompletos" significa que falta género, fecha de nacimiento, teléfono o institución referente. DPI, dirección, email, profesión y contacto de emergencia siguen siendo opcionales como ya lo son hoy.
- La detección de posibles duplicados (mismo nombre/DPI/fecha de nacimiento) no bloquea esta creación rápida, ya que la fecha de nacimiento aún no se conoce en ese momento; se aplicará normalmente la primera vez que alguien complete el expediente.
- No se exige ningún paso de aprobación adicional ni se fuerza una nota clínica al momento de la creación; las notas clínicas siguen funcionando igual que hoy para un paciente vinculado a una cirugía.
