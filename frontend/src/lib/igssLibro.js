// Roles con acceso exclusivo al Libro de órdenes IGSS (debe coincidir con el backend)
export const LIBRO_IGSS_ROLES = ['superadmin', 'admin', 'administrador_igss'];

export const puedeVerLibroIgss = (user) => LIBRO_IGSS_ROLES.includes(user?.role);

// Pueden ingresar órdenes desde la ficha (y corregir las suyas reservadas y sin atenciones)
export const INGRESO_ORDEN_ROLES = [...LIBRO_IGSS_ROLES, 'usuario', 'optica'];
export const puedeIngresarOrdenIgss = (user) => INGRESO_ORDEN_ROLES.includes(user?.role);

// Misma regla que el backend: solo números y guiones
export const spsValido = (v) => /^[0-9]+(-[0-9]+)*$/.test(String(v || '').trim()) && String(v || '').trim().length <= 40;

export const esTextoBajaCuantia = (numero) => (numero || '')
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '')
  .includes('bajacuantia');

export const etiquetaCatalogo = (n) => (n?.numero || '').trim() || `Baja cuantía — ${n?.nombre_servicio || ''}`;

export const descargarBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const limpio = (t) => String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9_-]+/g, '_');
export const nombreListado = (nombre, { desde, hasta } = {}) =>
  `Listado_oficial_${[nombre, desde, hasta].filter(Boolean).map(limpio).join('_')}.xlsx`;
