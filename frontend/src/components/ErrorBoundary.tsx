import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  declare public props: Readonly<Props>;

  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-surface-dim font-sans h-full min-h-[300px]">
          <div className="w-full max-w-md bg-surface border border-outline rounded-material-2xl p-8 shadow-material-3 text-center animate-fade-in">
            <div className="w-14 h-14 mx-auto rounded-material-full bg-[#fce8e6] flex items-center justify-center mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="#d93025">
                <path d="M12 2L1 21h22L12 2zm0 14a1 1 0 110 2 1 1 0 010-2zm1-8h-2v6h2V8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-onsurface mt-2">
              Đã có lỗi xảy ra
            </h3>
            <p className="text-sm text-onsurface-muted mt-1.5 max-w-xs mx-auto leading-relaxed">
              Lỗi không mong muốn trong component visual này.
            </p>
            {this.state.error && (
              <pre className="mt-3.5 p-3 bg-surface-container rounded-material-lg text-[10px] font-mono text-[#a50e0e] overflow-x-auto text-left max-h-32 border border-outline">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="mt-5 w-full py-2.5 bg-google-blue hover:bg-google-blueDark text-white font-medium text-sm rounded-material-full shadow-material-btn hover:shadow-material-btn-hover transition-all duration-200"
            >
              Tải lại Component
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
