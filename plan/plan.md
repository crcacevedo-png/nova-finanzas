# NovaVisión — Ajustes de Roles, Cirugías y Ficha de Paciente

Cuatro mejoras puntuales sobre el ERP: control del módulo Sala de Operaciones por rol, un médico ayudante en las cirugías, un formulario de paciente más ancho y un nuevo dato para pacientes del IGSS.

## Para quién es
Personal de la clínica NovaVisión (Guatemala): administradores que configuran accesos, personal que agenda y registra cirugías, y recepción que registra pacientes.

## Funcionalidades y experiencia

**1. Sala de Operaciones configurable por rol**
Hoy el acceso a "Sala de Operaciones" no se puede conceder o quitar de forma confiable a cualquier rol desde la configuración. Con el cambio, Sala de Operaciones quedará como una opción más que se activa o desactiva por rol (sistema y personalizados) desde la pantalla de configuración de roles/menús. Al activarla para un rol, los usuarios de ese rol verán el módulo en el menú y podrán entrar; al desactivarla, desaparece del menú y se bloquea el acceso.

**2. Médico ayudante en la cirugía**
Al agregar o editar una cirugía, además del "Cirujano" habrá un campo "Ayudante", justo debajo. El ayudante es otro médico que se elige de la lista de médicos ya registrados. Es un solo ayudante y es opcional (puede quedar vacío). El ayudante se guarda con la cirugía y se muestra junto al cirujano al ver el detalle y en la impresión/exportación de la cirugía.

**3. Modal de "Agregar/Editar Paciente" más ancho**
La ventana para registrar o editar un paciente se mostrará más ancha, para que los campos se vean con más holgura y menos apretados. Mismo contenido y campos; solo cambia el ancho.

**4. "Tipo de Paciente" para pacientes del IGSS**
Cuando la institución del paciente sea IGSS, aparecerá un campo adicional "Tipo de Paciente" (además de los datos IGSS que ya se piden). Es texto libre y opcional. Se guarda en la ficha del paciente y se muestra al ver o editar el paciente. Solo aparece cuando la institución es IGSS.

## Flujo de uso
- Un administrador abre la configuración de roles, activa "Sala de Operaciones" para el rol que quiera; los usuarios de ese rol pasan a ver y usar el módulo.
- Al registrar una cirugía, se elige el cirujano y, si aplica, el ayudante desde la lista de médicos.
- Al registrar un paciente, el formulario aparece más ancho; si se marca IGSS, se muestra y captura el "Tipo de Paciente".

## Sensación de la interfaz
Se mantiene el estilo actual del sistema (mismos colores, componentes y disposición). Los campos nuevos reutilizan los mismos controles ya usados (selector de médicos para el ayudante, campo de texto para "Tipo de Paciente"), para que todo se vea nativo y consistente.

## Fases de implementación

**Fase 1 (MVP, se construye ahora)**
- Sala de Operaciones activable/desactivable por rol, con efecto real en menú y acceso.
- Campo "Ayudante" (un médico, opcional) en alta y edición de cirugía, visible en detalle e impresión.
- Modal de agregar/editar paciente más ancho.
- Campo "Tipo de Paciente" (texto libre, opcional) para pacientes IGSS.

**Fase 2 (futuro)**
- Mostrar cirujano y ayudante en los reportes y listados de cirugías, y permitir filtrar por médico.
- Reportes/estadísticas que incluyan el "Tipo de Paciente" IGSS.

**Fase 3 (futuro)**
- Autocompletado de datos de pacientes IGSS recurrentes (quedó fuera por decisión del usuario; se podría retomar).

## Supuestos
- "Configurar en los roles" (punto 1) se resuelve dentro de la pantalla de configuración de roles/menús ya existente; no se crea una pantalla nueva.
- El "Ayudante" es un solo médico, opcional, elegido de la lista de médicos registrados; se guarda en el registro de la cirugía y aparece donde hoy aparece el cirujano.
- "Tipo de Paciente" es texto libre, opcional, y solo se muestra cuando la institución del paciente es IGSS.
- El punto 3 (autocompletar datos de pacientes IGSS previamente almacenados) queda excluido de este trabajo por indicación del usuario.
- El idioma de toda la interfaz y los textos se mantiene en español.
