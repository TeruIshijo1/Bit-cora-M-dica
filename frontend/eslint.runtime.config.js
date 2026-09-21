import globals from 'globals';

export default [
  {
    ignores: ['dist/**', 'public/**'],
  },
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      'no-unreachable': 'error',
      'no-undef': 'error',
    },
  },
];
