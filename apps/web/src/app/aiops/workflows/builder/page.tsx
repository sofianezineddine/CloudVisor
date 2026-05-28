"use client";

import { WorkflowBuilderWidget } from "@/widgets/workflow-builder";
import { Component, ErrorInfo, ReactNode } from "react";

class BuilderErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null; errorInfo: ErrorInfo | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[BuilderErrorBoundary] Caught error:", error.message);
    console.error("[BuilderErrorBoundary] Stack:", error.stack);
    console.error("[BuilderErrorBoundary] Component stack:", errorInfo.componentStack);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
          <h2 style={{ color: 'red' }}>Builder Error</h2>
          <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: '1rem', borderRadius: '8px' }}>
            {this.state.error?.message}
            {"\n\n"}
            --- Stack Trace ---
            {"\n"}
            {this.state.error?.stack}
            {"\n\n"}
            --- Component Stack ---
            {"\n"}
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function WorkflowBuilderPage() {
  return (
    <BuilderErrorBoundary>
      <WorkflowBuilderWidget
        workflowRaw={undefined}
        workflowId={undefined}
        standalone={true}
      />
    </BuilderErrorBoundary>
  );
}
