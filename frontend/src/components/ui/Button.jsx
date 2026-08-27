import React from 'react';

/**
 * Componente atómico Button con soporte de variantes, tamaños y estado de carga (isLoading).
 * 
 * @param {string} variant - 'primary' | 'secondary' | 'danger' | 'outline' | 'success' | 'ghost'
 * @param {string} size - 'sm' | 'md' | 'lg'
 * @param {boolean} isLoading - Muestra un spinner animado y deshabilita el botón
 * @param {React.ReactNode} icon - Icono opcional a la izquierda
 * @param {React.ReactNode} children - Contenido del botón
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  icon = null,
  type = 'button',
  className = '',
  ...rest
}) {
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none select-none';

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2.5 gap-2',
    lg: 'text-base px-6 py-3 gap-2.5'
  };

  const variantStyles = {
    primary: 'bg-hes-blue-main text-white hover:bg-[#00386c] active:bg-[#002d57] focus:ring-hes-blue-light shadow-sm hover:shadow',
    secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 active:bg-slate-300 focus:ring-slate-400 border border-slate-200/80',
    danger: 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus:ring-red-500 shadow-sm hover:shadow',
    outline: 'bg-transparent text-slate-700 hover:bg-slate-50 active:bg-slate-100 border border-slate-300 focus:ring-hes-blue-light',
    success: 'bg-hes-green text-white hover:bg-[#007f3e] active:bg-[#006933] focus:ring-emerald-500 shadow-sm hover:shadow',
    ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 active:bg-slate-200 focus:ring-slate-300'
  };

  const selectedSize = sizeStyles[size] || sizeStyles.md;
  const selectedVariant = variantStyles[variant] || variantStyles.primary;
  const isButtonDisabled = disabled || isLoading;

  return (
    <button
      type={type}
      disabled={isButtonDisabled}
      className={`${baseStyles} ${selectedSize} ${selectedVariant} ${className}`}
      {...rest}
    >
      {isLoading ? (
        <>
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Cargando...</span>
        </>
      ) : (
        <>
          {icon && <span className="flex-shrink-0 text-lg">{icon}</span>}
          {children}
        </>
      )}
    </button>
  );
}
