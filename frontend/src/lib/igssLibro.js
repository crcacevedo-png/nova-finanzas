// Roles con acceso exclusivo al Libro de órdenes IGSS (debe coincidir con el backend)
export const LIBRO_IGSS_ROLES = ['superadmin', 'admin', 'administrador_igss'];

export const puedeVerLibroIgss = (user) => LIBRO_IGSS_ROLES.includes(user?.role);

export const esTextoBajaCuantia = (numero) => (numero || '')
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '')
  .includes('bajacuantia');

export const etiquetaCatalogo = (n) => (n?.numero || '').trim() || `Baja cuantía — ${n?.nombre_servicio || ''}`;
