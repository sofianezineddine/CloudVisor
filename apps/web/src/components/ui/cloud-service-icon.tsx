'use client';

import * as React from 'react';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import {
  Database, Server, HardDrive, Lock, Cloud, Network,
  Container, Code, FileText, Shield, Key, Users,
  Activity, Zap, Globe, Box, Layers, Settings,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type CloudProvider = 'aws' | 'azure' | 'gcp' | 'oci';

export interface CloudServiceIconProps {
  provider: CloudProvider;
  service: string;
  size?: number;
  className?: string;
  fallbackToLucide?: boolean;
}

// ─── Service Icon Mapping ─────────────────────────────────────────────────────

/**
 * Maps service names to their icon paths or Lucide icon components.
 * 
 * Icon paths should be relative to /public directory.
 * Example: '/icons/aws/s3.svg'
 * 
 * For now, we use Lucide icons as fallbacks. Replace with actual SVG paths
 * when official cloud provider icons are downloaded.
 */
const SERVICE_ICON_MAP: Record<CloudProvider, Record<string, string | React.ComponentType<any>>> = {
  aws: {
    // Storage
    's3': HardDrive,
    'ebs': HardDrive,
    'efs': HardDrive,
    'glacier': Database,
    
    // Compute
    'ec2': Server,
    'lambda': Zap,
    'ecs': Container,
    'eks': Container,
    'fargate': Container,
    
    // Database
    'rds': Database,
    'dynamodb': Database,
    'aurora': Database,
    'redshift': Database,
    'elasticache': Database,
    
    // Security
    'iam': Key,
    'kms': Lock,
    'secrets-manager': Shield,
    'waf': Shield,
    'guardduty': Shield,
    'security-hub': Shield,
    
    // Network
    'vpc': Network,
    'cloudfront': Globe,
    'route53': Globe,
    'elb': Network,
    'alb': Network,
    'nlb': Network,
    
    // Other
    'cloudwatch': Activity,
    'cloudtrail': FileText,
    'sns': Activity,
    'sqs': Box,
    'api-gateway': Code,
  },
  
  azure: {
    // Storage
    'storage': HardDrive,
    'blob': HardDrive,
    'files': HardDrive,
    'disk': HardDrive,
    
    // Compute
    'vm': Server,
    'functions': Zap,
    'aks': Container,
    'container-instances': Container,
    
    // Database
    'sql': Database,
    'cosmos': Database,
    'mysql': Database,
    'postgresql': Database,
    
    // Security
    'active-directory': Users,
    'key-vault': Lock,
    'security-center': Shield,
    
    // Network
    'vnet': Network,
    'cdn': Globe,
    'load-balancer': Network,
    'application-gateway': Network,
    
    // Other
    'monitor': Activity,
    'log-analytics': FileText,
  },
  
  gcp: {
    // Storage
    'storage': HardDrive,
    'persistent-disk': HardDrive,
    'filestore': HardDrive,
    
    // Compute
    'compute': Server,
    'functions': Zap,
    'gke': Container,
    'cloud-run': Container,
    
    // Database
    'sql': Database,
    'firestore': Database,
    'bigtable': Database,
    'spanner': Database,
    
    // Security
    'iam': Key,
    'kms': Lock,
    'secret-manager': Shield,
    
    // Network
    'vpc': Network,
    'cdn': Globe,
    'load-balancing': Network,
    
    // Other
    'monitoring': Activity,
    'logging': FileText,
  },
  
  oci: {
    // Storage
    'object-storage': HardDrive,
    'block-volume': HardDrive,
    'file-storage': HardDrive,
    
    // Compute
    'compute': Server,
    'functions': Zap,
    'container-engine': Container,
    
    // Database
    'database': Database,
    'autonomous-database': Database,
    'mysql': Database,
    
    // Security
    'iam': Key,
    'vault': Lock,
    
    // Network
    'vcn': Network,
    'load-balancer': Network,
    
    // Other
    'monitoring': Activity,
    'logging': FileText,
  },
};

// ─── Fallback Icon ────────────────────────────────────────────────────────────

const FALLBACK_ICON = Cloud;

// ─── CloudServiceIcon Component ───────────────────────────────────────────────

export function CloudServiceIcon({
  provider,
  service,
  size = 20,
  className,
  fallbackToLucide = true,
}: CloudServiceIconProps) {
  const normalizedService = service.toLowerCase().replace(/[_\s]/g, '-');
  const iconOrPath = SERVICE_ICON_MAP[provider]?.[normalizedService];

  // If icon is a string (SVG path), render with Next.js Image
  if (typeof iconOrPath === 'string') {
    return (
      <Image
        src={iconOrPath}
        alt={`${provider} ${service}`}
        width={size}
        height={size}
        className={cn('object-contain', className)}
      />
    );
  }

  // If icon is a Lucide component, render it
  if (iconOrPath && fallbackToLucide) {
    const LucideIcon = iconOrPath as React.ComponentType<any>;
    return (
      <LucideIcon
        className={cn('text-[hsl(var(--text-secondary))]', className)}
        style={{ width: size, height: size }}
      />
    );
  }

  // Fallback to generic cloud icon
  const FallbackIcon = FALLBACK_ICON;
  return (
    <FallbackIcon
      className={cn('text-[hsl(var(--text-tertiary))]', className)}
      style={{ width: size, height: size }}
    />
  );
}

// ─── Provider Logo Component ──────────────────────────────────────────────────

export interface ProviderLogoProps {
  provider: CloudProvider;
  size?: number;
  className?: string;
}

/**
 * Renders the cloud provider's logo.
 * 
 * For now, uses text badges. Replace with actual logo SVGs when available.
 */
export function ProviderLogo({ provider, size = 24, className }: ProviderLogoProps) {
  const logoPath = `/icons/providers/${provider}.svg`;
  
  // TODO: Replace with actual logo images when available
  // For now, return a styled text badge
  const providerLabels: Record<CloudProvider, string> = {
    aws: 'AWS',
    azure: 'Azure',
    gcp: 'GCP',
    oci: 'OCI',
  };

  const providerColors: Record<CloudProvider, string> = {
    aws: 'bg-[#FF9900] text-white',
    azure: 'bg-[#0078D4] text-white',
    gcp: 'bg-[#4285F4] text-white',
    oci: 'bg-[#F80000] text-white',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded px-1.5 py-0.5 text-xs font-semibold',
        providerColors[provider],
        className
      )}
      style={{ minWidth: size * 2 }}
    >
      {providerLabels[provider]}
    </div>
  );
}

// ─── Utility: Get Service Display Name ───────────────────────────────────────

export function getServiceDisplayName(service: string): string {
  return service
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
