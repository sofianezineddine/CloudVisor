// Stub for next/link
import React from 'react';
const Link = ({ children, href, ...rest }: any) => React.createElement('a', { href, ...rest }, children);
export default Link;
