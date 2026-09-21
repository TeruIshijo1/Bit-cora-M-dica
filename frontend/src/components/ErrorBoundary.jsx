import React from 'react';
import {
  dynamicImportFailureId,
  shouldReloadForDynamicImportFailure,
} from '../utils/dynamicImportRecovery';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    if (shouldReloadForDynamicImportFailure(error, window.sessionStorage)) {
      window.location.reload();
      return;
    }

    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      const staleFrontend = Boolean(dynamicImportFailureId(this.state.error));

      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl border border-red-100 max-w-2xl w-full p-8 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-2xl font-bold">
              ⚠️
            </div>
            <h2 className="text-xl font-bold text-slate-800">
              {staleFrontend ? 'La aplicación se actualizó' : 'Se produjo un error al renderizar la vista'}
            </h2>
            <p className="text-sm text-slate-600">
              {staleFrontend
                ? 'La versión que estaba abierta ya no está disponible. Recarga la página para usar la versión actual.'
                : 'Ocurrió un error inesperado al procesar el expediente clínico.'}
            </p>
            <div className="bg-slate-900 text-red-400 p-4 rounded-xl text-xs font-mono overflow-auto max-h-60 whitespace-pre-wrap">
              {this.state.error && this.state.error.toString()}
              {"\n\n"}
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  this.setState({ hasError: false, error: null, errorInfo: null });
                  window.location.reload();
                }}
                className="px-5 py-2.5 bg-hes-blue-main text-white text-xs font-bold rounded-xl shadow hover:bg-hes-blue-dark transition-all"
              >
                Recargar Página
              </button>
              <button
                type="button"
                onClick={() => window.location.href = '/camas'}
                className="px-5 py-2.5 bg-slate-200 text-slate-700 text-xs font-bold rounded-xl hover:bg-slate-300 transition-all"
              >
                Ir al Dashboard de Camas
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
