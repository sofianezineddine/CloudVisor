'use client';

import * as React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { AIOpsAlertTrendPoint } from '@/hooks/use-aiops-dashboard';

interface AlertTrendChartProps {
  data: AIOpsAlertTrendPoint[] | undefined;
  isLoading: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'var(--critical)',
  warning: 'var(--medium)',
  info: 'var(--info)',
  low: 'var(--success)',
};

/**
 * Alert trend line chart for the AIOps overview dashboard.
 * Shows alert count per day over the last 7 days with one series per severity.
 * Uses Recharts and CloudVisor design tokens.
 */
export function AlertTrendChart({ data, isLoading }: AlertTrendChartProps) {
  if (isLoading) {
    return (
      <div className="cv-container p-4">
        <div className="widget-header !px-0 !pt-0 !border-0 mb-3">
          <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Alert Trend (7 days)
          </h3>
        </div>
        <div
          className="flex items-center justify-center"
          style={{ height: 260 }}
        >
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Loading chart data…
          </span>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="cv-container p-4">
        <div className="mb-3">
          <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Alert Trend (7 days)
          </h3>
        </div>
        <div
          className="flex items-center justify-center rounded border"
          style={{
            height: 260,
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-elevated)',
          }}
        >
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            No alert trend data available
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="cv-container p-4">
      <div className="mb-3">
        <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
          Alert Trend (7 days)
        </h3>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border-default)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
            axisLine={{ stroke: 'var(--border-default)' }}
            tickLine={false}
            tickFormatter={(value: string) => {
              const d = new Date(value);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
            axisLine={{ stroke: 'var(--border-default)' }}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              fontSize: 12,
              color: 'var(--text-primary)',
            }}
            labelStyle={{ color: 'var(--text-secondary)', marginBottom: 4 }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
          />
          <Line
            type="monotone"
            dataKey="critical"
            name="Critical"
            stroke={SEVERITY_COLORS.critical}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="warning"
            name="Warning"
            stroke={SEVERITY_COLORS.warning}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="info"
            name="Info"
            stroke={SEVERITY_COLORS.info}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="low"
            name="Low"
            stroke={SEVERITY_COLORS.low}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
