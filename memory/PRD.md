# PRD - NovaVision ERP Oftalmológico

> Este archivo contiene el problema original y el alcance estático del producto.
> Historial detallado de cada sesión de desarrollo → `CHANGELOG.md`.
> Pendientes/backlog priorizado → `ROADMAP.md`.

## Descripción General
Sistema ERP completo para clínicas oftalmológicas con módulos de: Dashboard, Pacientes, Agenda, Evaluación Oftalmológica, Inventario FEFO, POS, Caja, Cierre del Día (diagnóstico/conciliación consolidado Clínica+Óptica con envío por correo, solo admin/superadmin), CRM Cirugías, Sala de Operaciones/Procedimientos de Anestesia, Óptica, gestión de NOG/unidades IGSS, y Laboratorio de Pruebas E2E.

## Arquitectura
- Frontend: React (`/app/frontend`), backend: FastAPI (`/app/backend`), base de datos: MongoDB.
- Rutas backend bajo `/api`. Frontend usa `REACT_APP_BACKEND_URL`.
- Producción: `https://admin.novavision.me` (acceso directo a su base de datos no disponible; cambios se prueban en preview y se despliegan).

## Usuarios / Roles del sistema
superadmin, admin, usuario, medico, administrador_igss, optica, anestesia — cada uno con menús y permisos configurables (`config/permissions.py`, con una matriz duplicada histórica en `server.py` que debe mantenerse sincronizada — ver nota en CHANGELOG sesión "rol usuario puede editar pacientes").

## Core Requirements (resumen vivo)
- **Pacientes**: alta/edición/listado, historial médico persistente (antecedentes, medicamentos, diagnósticos activos) entre consultas.
- **Evaluación Oftalmológica**: expediente por consulta con autoguardado, antecedentes/medicamentos/diagnósticos que persisten entre visitas, recetas, sellado a las 24h.
- **Agenda**: citas, integración Google Calendar.
- **Sala de Operaciones / Anestesia**: registro de cirugías, cierre mensual de anestesia con pago individual por procedimiento.
- **IGSS**: unidades, NOG, producción, órdenes. Libro de órdenes IGSS (`igss_ordenes_libro`, Fases 1-3 completas; Fase 4 paso A (simulación) y paso B (aplicar/deshacer por lote, solo superadmin, con respaldo <24 h y simulación <30 min) terminados y probados en preview; producción espera aprobación; "Revisar SPS" bloquea facturar hasta que un rol del libro lo confirme): 1 orden por No. SPS y unidad con número fijo ORD-XXXXXX; médico/recepción ven solo lectura (número, procedimiento, ingreso, avance, estado; solo reservadas y en curso; nunca SPS/NOG); "Confirmar dosis con la hoja" impide completa/cobro hasta confirmarse; fuente única de conteo (estados reservada / en curso / completa / histórica / cerrada sin completar / anulada; ocupan cupo reservadas+en curso+completas+históricas; cobrable = solo completas; nunca se cuentan dosis), libro exclusivo de superadmin/admin/administrador_igss (incluido el selector `nogs-activos`); INGRESO de órdenes también para usuario y óptica (ven SPS/NOG del paciente, cupo sin cifras, corrigen solo su orden reservada sin atenciones); No. SPS solo números y guiones para todos; interruptor "Usar solo el libro" (solo superadmin, apagado por defecto) que corta toda escritura a las colecciones legadas; catálogo admite Baja Cuantía sin número y entradas sin tope; listado oficial Excel 1 fila por orden completa (+ hoja "Históricas" solo de consulta).
- **Óptica / POS / Caja / Inventario FEFO**: ventas, inventario, conciliación.
- **FEL Digifact**: facturación electrónica (pausado, pendiente activación SAT/certificación — ver ROADMAP).

Para el detalle de cada feature implementada, fecha y verificación, consultar `CHANGELOG.md`.
