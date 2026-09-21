export const shouldOmitAuthorization = (config) => {
  const url = String(config?.url || '');
  if (url.endsWith('/auth/login/admin') || url.endsWith('/auth/login/biometric')) return true;
  let data = config?.data;
  if (typeof data === 'string') {
    try { data = JSON.parse(data); } catch { return false; }
  }
  return url.endsWith('/biometrics/challenge') && data?.action === 'LOGIN';
};
