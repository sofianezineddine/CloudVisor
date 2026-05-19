'use client';

import Image from 'next/image';

interface DynamicImageProviderIconProps {
  providerType?: string;
  src?: string;
  alt?: string;
  width?: number;
  height?: number;
  className?: string;
  title?: string;
}

export function DynamicImageProviderIcon({
  providerType,
  src,
  alt,
  width = 24,
  height = 24,
  className = '',
  title,
}: DynamicImageProviderIconProps) {
  const imgSrc = src || `/icons/${providerType || 'unknown'}-icon.png`;
  const imgAlt = alt || providerType || 'provider';

  return (
    <Image
      src={imgSrc}
      alt={imgAlt}
      width={width}
      height={height}
      className={className}
      title={title || imgAlt}
      onError={(e) => {
        (e.target as HTMLImageElement).src = '/icons/unknown-icon.png';
      }}
      unoptimized
    />
  );
}

export default DynamicImageProviderIcon;
