# Acceso clínico configurable para el rol Médico

Permite que una cuenta de médico entre al sistema y trabaje su día: ver sus propias citas, atender pacientes y dejar registrada la consulta.
Además, deja que el administrador controle, desde una sola pantalla, qué puede y qué no puede hacer el médico (y cualquier otro rol).

## Para quién es
Clínica NovaVisión en Guatemala: los médicos que atienden consulta y cirugía, y el administrador que gestiona los usuarios y decide qué ve cada rol.

## Qué se corrige y cómo se verá

Hoy la cuenta de médico solo puede entrar a "Pacientes". Con este cambio, el administrador podrá
otorgarle (y quitarle) accesos clínicos, y el rol "médico" quedará listo para trabajar.

### 1. Permisos clínicos que se podrán activar/desactivar por rol
En la pantalla de Roles aparecerá una nueva sección "Clínica" con interruptores para:
- **Agenda** (ver y gestionar citas).
- **Evaluación Oftalmológica** (ver y editar la evaluación del paciente).
- **Recetas** (médicas y de lentes) dentro de la evaluación.
- **Sala de Operaciones** (ver y editar la evaluación/registro quirúrgico).
- **Pacientes**: crear y editar (sin eliminar).

El administrador podrá combinarlos libremente para el rol médico o para cualquier rol que cree.

### 2. El rol "Médico" queda listo de una vez
El rol médico quedará configurado con todos estos accesos activados: su Agenda del día,
edición de pacientes (sin borrarlos), evaluaciones oftalmológicas, sala de operaciones y recetas.
El administrador podrá seguir ajustándolo cuando quiera.

### 3. La Agenda del médico muestra solo lo suyo
Cuando entra un médico, la Agenda abre en "su agenda del día": verá únicamente las citas
asignadas a él, no las de toda la clínica.

### 4. Cada cuenta de médico se liga a su ficha de médico
En Gestión de Usuarios, al crear o editar una cuenta de médico, se podrá elegir a qué médico
(ficha/doctor del sistema) corresponde esa cuenta. Ese vínculo es lo que permite mostrarle
"sus propias citas". Si una cuenta de médico aún no tiene médico asignado, la Agenda se lo
indicará con un mensaje claro en lugar de mostrar algo incorrecto.

## Flujo de uso

**Administrador**
1. Entra a Gestión de Usuarios → Roles y ve la nueva sección "Clínica" con los interruptores.
2. El rol médico ya viene con los accesos activados; puede dejarlos así o ajustarlos.
3. En Usuarios, al crear/editar una cuenta de médico, elige la ficha de médico que le corresponde.

**Médico**
1. Inicia sesión y en el menú ve: Pacientes, Agenda, Evaluación Oftalmológica y Sala de Operaciones.
2. Abre la Agenda y ve solo sus citas del día.
3. Abre un paciente, lo edita si hace falta, registra la evaluación oftalmológica o de sala de
   operaciones y emite recetas médicas o de lentes.
4. No puede eliminar pacientes ni entrar a las áreas que el administrador no le haya activado.

## UI/UX feel
Sin rediseño. Se reutiliza la pantalla actual de Roles (se añade la sección "Clínica") y la de
Usuarios (se añade el selector de médico). Mensajes claros cuando falte un acceso o el vínculo
con la ficha de médico. El médico ve un menú corto y enfocado en lo clínico.

## Fases de implementación

**Fase 1 (lo que se construye ahora):**
- Nuevos permisos clínicos activables por rol: Agenda, Evaluación Oftalmológica, Recetas,
  Sala de Operaciones y edición de Pacientes (sin eliminar).
- El rol "médico" queda configurado con todos esos accesos y con su menú clínico visible.
- Agenda del médico filtrada a sus propias citas del día.
- Selector de "médico asignado" en la cuenta de usuario, con aviso cuando no esté asignado.

**Fase 2 (después):**
- Que el médico pueda ver sus citas de días anteriores/siguientes (no solo el día actual) y un
  resumen semanal propio.
- Permisos clínicos más finos (por ejemplo, ver evaluación sin poder editarla).

**Fase 3 (futuro):**
- Que cada médico vea únicamente los expedientes de sus propios pacientes.
- Firma del médico en recetas y registro de quién editó cada evaluación.

## Supuestos
- "Eliminar" el acceso del médico a pacientes queda fuera: el médico crea y edita, pero no borra
  expedientes.
- "Agenda del día" = solo las citas del propio médico, del día en curso (hora de Guatemala).
- Las recetas médicas y de lentes forman parte de la Evaluación Oftalmológica (se emiten desde ahí).
- Cada cuenta de médico se vincula a una ficha de médico existente mediante un selector en
  Gestión de Usuarios; si no está vinculada, la Agenda lo avisa en lugar de fallar.
- El rol médico se deja preconfigurado con los accesos solicitados, pero todo sigue siendo editable
  por el administrador desde la pantalla de Roles.
- Estos nuevos permisos quedan disponibles para cualquier rol, no solo para el médico.
- No se modifican los accesos de los roles existentes (superadmin, administrador, usuario, óptica).
