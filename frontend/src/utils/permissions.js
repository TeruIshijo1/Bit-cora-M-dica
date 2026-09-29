import catalog from '../../../backend/access_catalog.json' with { type: 'json' };

export const accessCatalog = catalog;
export const modules = catalog.modules;
export const adminModules = modules.filter(item => item.tab);

export function parsePermissionValue(value, fallback) {
  if (value == null) return fallback;
  try { return typeof value === 'string' ? JSON.parse(value) : value; } catch { return fallback; }
}

export function roleCanAccess(role, item) {
  const limit = catalog.role_limits[role];
  return (!limit || limit.includes(item.id)) && (!item.roles || item.roles.includes(role));
}

export function effectiveModules(user = {}) {
  const role = user?.rol === 'Mantenimiento/Limpieza' ? 'limpieza' : user?.rol;
  const explicit = user?.permisos_modulos != null;
  const parsed = parsePermissionValue(user?.permisos_modulos, {});
  const permissions = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  return Object.fromEntries(modules.map(item => {
    const value = permissions[item.id];
    let enabled = explicit
      ? (Object.hasOwn(permissions, item.id) ? [true, 'lectura', 'escritura'].includes(value)
        : Object.entries(catalog.legacy_groups).some(([key, children]) => permissions[key] === true && children.includes(item.id)))
      : item.defaults.includes(role);
    if (item.id === 'firmas_area' && !Object.hasOwn(permissions, item.id)) {
      const signing = parsePermissionValue(user?.formatos_firma_permitidos, []);
      enabled = Array.isArray(signing) && signing.length > 0;
    }
    return [item.id, Boolean(enabled && roleCanAccess(role, item))];
  }));
}

export function canAccessPath(user, path) {
  const grants = effectiveModules(user);
  if (path === '/sin-acceso') return true;
  if (path === '/ehr/visor-pdf' && grants.firmas_area) return true;
  if (path === '/admin' || path === '/rh') return adminModules.some(item => grants[item.id]);
  return modules.some(item => !item.tab && grants[item.id] && (path === item.path || path.startsWith(`${item.path}/`)));
}

export function landingRoute(user) {
  const grants = effectiveModules(user);
  if (adminModules.some(item => grants[item.id])) return user?.rol === 'rh' ? '/rh' : '/admin';
  const order = ['captura_medica', 'captura_enfermeria', 'ehr', 'agenda', 'camas'];
  const preferred = order.find(key => grants[key]);
  return (modules.find(item => item.id === preferred) || modules.find(item => !item.tab && grants[item.id]))?.path || '/sin-acceso';
}

export const passwordHelp = 'Mínimo 8 caracteres, mayúscula, minúscula, número y símbolo.';
export const validPassword = value => value.length >= 8 && /[A-Z]/.test(value) && /[a-z]/.test(value) && /\d/.test(value) && /[^A-Za-z0-9\s]/.test(value);
