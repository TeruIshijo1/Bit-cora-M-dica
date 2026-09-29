import test from 'node:test';
import assert from 'node:assert/strict';
import { effectiveModules, canAccessPath, landingRoute, validPassword } from '../src/utils/permissions.js';

test('RH only sees the five requested areas, including with old broad permissions', () => {
  for (const permisos_modulos of [null, '{"admin":true,"rh":true,"ehr":true,"usuarios":true}']) {
    const user = { rol: 'rh', permisos_modulos };
    assert.deepEqual(Object.entries(effectiveModules(user)).filter(([, value]) => value).map(([key]) => key), ['dashboard', 'historial', 'alta', 'directorio', 'escaneos']);
    for (const route of ['/ehr/5704', '/agenda', '/camas', '/captura', '/firma-express']) assert.equal(canAccessPath(user, route), false);
    assert.equal(landingRoute(user), '/rh');
  }
});

test('explicit grants control navigation regardless of default role; no grants has a landing page', () => {
  assert.equal(landingRoute({ rol: 'laboratorio', permisos_modulos: '{"agenda":true}' }), '/agenda');
  assert.equal(landingRoute({ rol: 'admin', permisos_modulos: '{}' }), '/sin-acceso');
  for (const value of ['{}', 'invalid', '["ehr"]', '{"ehr":"false"}']) assert.equal(canAccessPath({ rol: 'admin', permisos_modulos: value }, '/ehr'), false);
});

test('passwords accept eight characters and retain every complexity requirement', () => {
  assert.equal(validPassword('Abcdef1!'), true);
  for (const value of ['Abcd1!', 'abcdefgh1!', 'ABCDEFGH1!', 'Abcdefgh!', 'Abcdefg1', 'Abcdef1 ']) assert.equal(validPassword(value), false);
});

test('area signers land in shared queue without general patient access', () => {
  const user = { rol: 'banco_sangre', permisos_modulos: '{}', formatos_firma_permitidos: '["HE-DIRMED-CONSUL-PLT-09"]' };
  assert.equal(landingRoute(user), '/firmas-area');
  assert.equal(canAccessPath(user, '/firmas-area'), true);
  assert.equal(canAccessPath(user, '/ehr/visor-pdf'), true);
  for (const route of ['/ehr', '/ehr/5704', '/admin', '/firma-express']) assert.equal(canAccessPath(user, route), false);
  assert.equal(landingRoute({ ...user, formatos_firma_permitidos: '[]' }), '/sin-acceso');
  assert.equal(landingRoute({ ...user, permisos_modulos: '{"firmas_area":false}' }), '/sin-acceso');
});
