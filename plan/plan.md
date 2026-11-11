# Autoguardado Confiable en Evaluaciones Oftalmológicas

Hoy, al llenar una Evaluación Oftalmológica, algunos médicos y usuarios pierden información porque el autoguardado o el guardado manual fallan sin ningún aviso en pantalla. Este plan corrige esa causa de fondo y agrega una protección para que, aunque algo vuelva a fallar, el trabajo del médico nunca se pierda.

## Para quién es

- Todo médico o usuario que llena una Evaluación Oftalmológica (no es un caso aislado de una sola persona; se reportó en varios).
- Indirectamente, los pacientes: una evaluación incompleta o perdida puede afectar su atención y el historial clínico.

## Funcionalidad principal y experiencia

- **Guardado que no se pierde en silencio**: cada vez que el sistema intenta guardar (autoguardado o botón manual) y falla, ya no queda en silencio — se reintenta automáticamente unas cuantas veces de forma invisible para el médico.
- **Respaldo mientras escribe**: mientras el médico completa la evaluación, lo que va escribiendo se respalda en su propio navegador. Si el guardado contra el servidor falla repetidamente (ej. se cae la conexión), al volver a abrir esa misma evaluación el sistema le ofrece recuperar lo que tenía escrito, en vez de empezar de cero.
- **Estado de guardado siempre visible**: un indicador pequeño y constante ("Guardando...", "Guardado", "Reintentando...", "Sin guardar — revisa tu conexión") para que el médico sepa en todo momento si su información está a salvo, sin tener que adivinar.
- **Corrección de la causa real**: se investiga y corrige por qué el guardado falla hoy para varios usuarios (no es algo nuevo del último despliegue; viene pasando desde hace tiempo), de modo que en condiciones normales ni siquiera se necesite el reintento.

## Flujo de uso

1. El médico abre la Evaluación Oftalmológica de un paciente y empieza a llenar los campos.
2. El sistema autoguarda en segundo plano según ya lo hace hoy; el indicador de estado muestra "Guardando..." y luego "Guardado".
3. Si un guardado falla (ej. problema de red momentáneo), el sistema reintenta solo; el indicador muestra "Reintentando..." sin interrumpir al médico.
4. Si el guardado sigue sin poder completarse, el indicador avisa claramente ("Sin guardar") y lo escrito queda respaldado en el navegador.
5. Si el médico cierra o recarga esa evaluación sin que se haya confirmado el guardado, al volver a abrirla el sistema le ofrece recuperar el respaldo local antes de perderlo.

## Estilo de la experiencia

- Discreto y no intrusivo: el indicador de estado vive en una esquina fija de la pantalla de evaluación, con colores claros (ej. verde "Guardado", ámbar "Reintentando", rojo "Sin guardar") siguiendo la paleta ya usada en el resto del sistema.
- Ningún bloqueo de pantalla ni ventanas emergentes molestas durante el llenado normal; solo se interrumpe al médico con un aviso explícito si realmente hay datos en riesgo de perderse.

## Fases de implementación

**Fase 1 — MVP (se construye ahora)**
- Diagnóstico y corrección de la causa raíz del guardado/autoguardado fallido en Evaluación Oftalmológica para todos los roles que la usan.
- Reintento automático ante fallos de guardado.
- Respaldo local del borrador mientras se escribe, con opción de recuperarlo si el guardado no se completó.
- Indicador visible de estado de guardado (Guardando / Guardado / Reintentando / Sin guardar).

**Fase 2 — Resiliencia ampliada**
- Manejo de edición simultánea de una misma evaluación desde dos sesiones o dispositivos distintos (evitar que uno sobrescriba al otro).
- Aviso a superadmin/admin cuando se detectan fallos de guardado recurrentes, para actuar antes de que un médico lo reporte.

**Fase 3 — Extender el mismo estándar de guardado confiable**
- Aplicar el mismo mecanismo de reintento + respaldo local + indicador de estado a otras pantallas de captura de datos largos del sistema (ej. notas de cirugía, otras fichas clínicas extensas), para que ningún formulario del ERP pierda información silenciosamente.

## Supuestos

- El problema afecta a varios médicos/usuarios de forma general (no es un dato puntual de un solo paciente o un solo usuario que haya que corregir manualmente).
- El problema es anterior a los últimos despliegues; no se asume que lo causó un cambio reciente, por lo que la corrección se enfoca en el mecanismo de guardado existente, no en revertir algo puntual.
- "Respaldo en el navegador" significa que el borrador no guardado se conserva temporalmente en ese navegador (no es una copia adicional permanente en la base de datos ni se sincroniza entre dispositivos); si el médico cambia de computadora antes de que el guardado se complete, ese respaldo local no estará disponible ahí.
- El indicador de estado y el respaldo se construyen primero para la pantalla de Evaluación Oftalmológica, que es donde se reportó el problema; no se asume que se necesite en otras pantallas en esta primera fase.
- No se requiere ninguna integración de terceros nueva; es una mejora interna de confiabilidad sobre el guardado que ya existe.
- El trabajo se construye y se verifica primero en el ambiente de pruebas (preview) antes de desplegarse a producción, siguiendo el mismo proceso ya usado para cambios anteriores.
