'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface RiskScoreProps {
  score: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  animated?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--critical)';
  if (score >= 60) return 'var(--high)';
  if (score >= 40) return 'var(--medium)';
  if (score >= 20) return 'var(--low)';
  return 'var(--success)';
}

function getScoreColorClass(score: number): string {
  if (score >= 80) return 'var(--critical)';
  if (score >= 60) return 'var(--high)';
  if (score >= 40) return 'var(--medium)';
  if (score >= 20) return 'var(--low)';
  return 'var(--success)';
}

export function RiskScore({ score, size = 'md', className, animated = true }: RiskScoreProps) {
  const [displayScore, setDisplayScore] = React.useState(animated ? 0 : score);
  const color = getScoreColor(score);
  const colorClass = getScoreColorClass(score);

  React.useEffect(() => {
    if (!animated) return;
    
    const duration = 800;
    const steps = 60;
    const increment = score / steps;
    let current = 0;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setDisplayScore(score);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(current));
      }
    }, duration / steps);
    
    return () => clearInterval(timer);
  }, [score, animated]);

  // Size configurations
  const sizeConfig = {
    sm: { diameter: 64, strokeWidth: 6, fontSize: 'text-lg' },
    md: { diameter: 80, strokeWidth: 8, fontSize: 'text-2xl' },
    lg: { diameter: 120, strokeWidth: 8, fontSize: 'text-4xl' },
  };

  const config = sizeConfig[size];
  const radius = (config.diameter - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (displayScore / 100) * circumference;

  if (size === 'sm') {
    // Small inline format - just colored number
    return (
      <span className="font-mono text-md font-bold" style={{ color: colorClass, fontFamily: 'var(--font-mono)' }}>
        {Math.round(displayScore)}
      </span>
    );
  }

  // Large format - circular gauge
  return (
    <div className={cn('inline-flex flex-col items-center gap-1', className)}>
      <svg
        width={config.diameter}
        height={config.diameter}
        className={animated ? 'transition-all duration-300' : ''}
      >
        {/* Background circle */}
        <circle
          cx={config.diameter / 2}
          cy={config.diameter / 2}
          r={radius}
          fill="none"
          stroke="var(--border-default)"
          strokeWidth={config.strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={config.diameter / 2}
          cy={config.diameter / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={config.strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${config.diameter / 2} ${config.diameter / 2})`}
          style={{
            transition: animated ? 'stroke-dashoffset 800ms ease-out' : 'none',
          }}
        />
        {/* Score text */}
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="middle"
          fill={colorClass}
          style={{ fontSize: size === 'lg' ? '32px' : '24px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}
        >
          {Math.round(displayScore)}
        </text>
      </svg>
      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Risk Score</span>
    </div>
  );
}
