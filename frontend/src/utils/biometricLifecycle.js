let purgeHandler = () => {};

export const registerBiometricPurge = handler => {
  purgeHandler = typeof handler === 'function' ? handler : () => {};
};

export const purgeRegisteredBiometrics = () => purgeHandler();
