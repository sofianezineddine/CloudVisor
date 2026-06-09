// Stub for next/dynamic — returns the loader component directly in tests
import React from 'react';
const dynamic = (_loader: any, _opts?: any): React.ComponentType<any> => {
  const Stub = () => null;
  Stub.displayName = 'DynamicStub';
  return Stub;
};
export default dynamic;
