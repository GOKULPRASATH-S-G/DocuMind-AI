import React from 'react';
import { AlertCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled React Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
    if (this.props.onRetry) {
      this.props.onRetry();
    } else {
      window.location.reload();
    }
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-6 shadow-2xl space-y-4 my-4 max-w-4xl mx-auto text-slate-100">
          <div className="flex items-center gap-3 text-amber-400">
            <AlertCircle className="w-6 h-6 flex-shrink-0" />
            <h3 className="text-base font-bold text-slate-100">
              Something went wrong while displaying the processing result.
            </h3>
          </div>

          <p className="text-xs text-slate-300">
            An unexpected interface error occurred. You can retry processing or inspect the technical details below.
          </p>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={this.handleRetry}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-sky-600/20"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Processing
            </button>

            <button
              onClick={this.toggleDetails}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all border border-slate-700"
            >
              {this.state.showDetails ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" /> Hide Details
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" /> View Details
                </>
              )}
            </button>
          </div>

          {this.state.showDetails && (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-[11px] text-red-400 space-y-2 overflow-x-auto max-h-60 mt-3">
              <div>
                <strong>Error:</strong> {this.state.error?.toString() || 'Unknown React Exception'}
              </div>
              {this.state.errorInfo?.componentStack && (
                <div>
                  <strong>Component Stack:</strong>
                  <pre className="text-slate-400 mt-1 whitespace-pre-wrap text-[10px]">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
