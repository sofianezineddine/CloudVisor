'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cspmAPI } from '@/lib/api/cspm';
import { useScopeStore } from '@/stores/scope';
import type { CSPMFinding, CSPMStats, CSPMPosture } from '@/lib/api/cspm';

// ─── Query keys ───────────────────────────────────────────────────────────────

export const cspmKeys = {
  all:            () => ['cspm'] as const,
  stats:          () => ['cspm', 'stats'] as const,
  posture:        () => ['cspm', 'posture'] as const,
  accountPosture: () => ['cspm', 'posture', 'accounts'] as const,
  postureTrend:   (days: number) => ['cspm', 'posture', 'trend', days] as const,
  findings:       () => ['cspm', 'findings'] as const,
  findingsList:   (p: Record<string, unknown>) => ['cspm', 'findings', 'list', p] as const,
  findingDetail:  (id: string) => ['cspm', 'findings', 'detail', id] as const,
  drift:          (p: Record<string, unknown>) => ['cspm', 'drift', p] as const,
  resources:      (p: Record<string, unknown>) => ['cspm', 'resources', p] as const,
  compliance:     () => ['cspm', 'compliance'] as const,
  framework:      (fw: string) => ['cspm', 'compliance', fw] as const,
  scans:          () => ['cspm', 'scans'] as const,
  scanResources:  (id: string) => ['cspm', 'scans', id, 'resources'] as const,
  rules:          () => ['cspm', 'rules'] as const,
  reports:        () => ['cspm', 'reports'] as const,
  report:         (id: string) => ['cspm', 'reports', id] as const,
};

// ─── Scope helpers ────────────────────────────────────────────────────────────

function useScopeAccountId(): string | undefined {
  return useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
}

function useScopeProvider(): string | undefined {
  return useScopeStore(s => s.mode === 'provider' ? s.provider : undefined);
}

/**
 * Client-side filter: keep only items that match the current scope.
 * Used when the backend doesn't enforce scope filtering.
 */
function filterByScope<T extends { account_id?: string; provider?: string }>(
  items: T[],
  accountIds: string[],
  accountId: string | undefined,
  provider: string | undefined,
): T[] {
  if (accountId) return items.filter(i => i.account_id === accountId);
  if (provider) return items.filter(i => i.provider === provider);
  if (accountIds.length > 0) return items.filter(i => i.account_id && accountIds.includes(i.account_id));
  return items;
}

/**
 * Recompute posture stats from a filtered set of findings.
 */
function computePostureFromFindings(findings: CSPMFinding[]): CSPMPosture {
  const open = findings.filter(f => f.status === 'open' || f.status === 'suppressed' || f.status === 'accepted_risk');
  const critical = open.filter(f => f.severity === 'CRITICAL').length;
  const high = open.filter(f => f.severity === 'HIGH').length;
  const medium = open.filter(f => f.severity === 'MEDIUM').length;
  const low = open.filter(f => f.severity === 'LOW').length;
  const penalty = Math.min(critical * 15 + high * 5 + medium * 2, 95);
  const posture_score = open.length === 0 ? 100 : Math.max(100 - penalty, 5);
  return {
    organization_id: '',
    posture_score,
    total_open_findings: open.length,
    critical,
    high,
    medium,
    low,
    resources_evaluated: 0,
    compliance_percentage: posture_score,
  };
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useCSPMStats() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.stats(), accountIds],
    queryFn: async (): Promise<CSPMStats> => {
      // Try the real stats endpoint first
      try {
        const data = await cspmAPI.getStats(accountId, provider);
        // If backend returned scoped data, trust it
        if (data && (data.total_resources > 0 || data.total_findings > 0)) {
          return data;
        }
      } catch {
        // Fall through to client-side computation
      }

      // Fallback: compute from scoped findings
      try {
        const findingsData = await cspmAPI.listFindings({
          account_id: accountId,
          provider: !accountId ? provider : undefined,
          page_size: 500,
        });
        const items = findingsData?.items ?? [];
        const scoped = filterByScope(items, accountIds, accountId, provider);
        const open = scoped.filter(f => f.status === 'open');
        const bySeverity: Record<string, number> = {};
        for (const f of open) {
          bySeverity[f.severity] = (bySeverity[f.severity] ?? 0) + 1;
        }
        return {
          organization_id: '',
          total_findings: scoped.length,
          open_findings: open.length,
          critical: bySeverity['CRITICAL'] ?? 0,
          high: bySeverity['HIGH'] ?? 0,
          medium: bySeverity['MEDIUM'] ?? 0,
          low: bySeverity['LOW'] ?? 0,
          total_resources: 0,
          avg_risk_score: 0,
          posture_score: 0,
          last_scan_at: '',
          last_scan_status: '',
        };
      } catch {
        return {
          organization_id: '',
          total_findings: 0,
          open_findings: 0,
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          total_resources: 0,
          avg_risk_score: 0,
          posture_score: 0,
          last_scan_at: '',
          last_scan_status: '',
        };
      }
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMPosture() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.posture(), accountIds],
    queryFn: async (): Promise<CSPMPosture> => {
      // Try the real posture endpoint first — it's the fastest path
      try {
        const data = await cspmAPI.getPosture(accountId, provider);
        // If backend returned scoped data (has resources_evaluated > 0 or findings), trust it
        if (data && (data.resources_evaluated > 0 || data.total_open_findings > 0)) {
          return data;
        }
      } catch {
        // Fall through to client-side computation
      }

      // Fallback: compute posture client-side from scoped findings
      try {
        const findingsData = await cspmAPI.listFindings({
          account_id: accountId,
          provider: !accountId ? provider : undefined,
          page_size: 500,
        });
        const items = findingsData?.items ?? [];
        const scoped = filterByScope(items, accountIds, accountId, provider);
        const posture = computePostureFromFindings(scoped);

        // Try to get resource count separately — non-critical, don't fail if it errors
        let resourceCount = 0;
        try {
          const resourcesData = await cspmAPI.listResources({
            account_id: accountId,
            provider: !accountId ? provider : undefined,
            page_size: 200,
          });
          resourceCount = Array.isArray(resourcesData) ? resourcesData.length : 0;
        } catch {
          // resource count is optional — posture still works without it
        }

        return { ...posture, resources_evaluated: resourceCount };
      } catch (e) {
        // Last resort: return a zero posture rather than crashing
        return {
          organization_id: '',
          posture_score: 0,
          total_open_findings: 0,
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          resources_evaluated: 0,
          compliance_percentage: 0,
        };
      }
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMAccountPosture() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.accountPosture(), accountIds],
    queryFn: async () => {
      const all = await cspmAPI.getAccountPosture();
      if (accountId) return all.filter(a => a.account_id === accountId);
      if (provider) return all.filter(a => a.provider === provider);
      return all;
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMPostureTrend(days = 30) {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.postureTrend(days), accountIds],
    queryFn: () => cspmAPI.getPostureTrend(days, accountId, provider),
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMFindings(params: {
  severity?: string;
  status?: string;
  account_id?: string;
  page?: number;
  page_size?: number;
}) {
  const accountIds = useScopeStore(s => s.accountIds);
  const scopeAccountId = useScopeAccountId();
  const scopeProvider = useScopeProvider();
  const effectiveAccountId = params.account_id ?? scopeAccountId;
  const effectiveParams = {
    ...params,
    account_id: effectiveAccountId,
    ...(scopeProvider && !effectiveAccountId ? { provider: scopeProvider } : {}),
  };
  return useQuery({
    queryKey: cspmKeys.findingsList({ ...effectiveParams, _scope: accountIds } as Record<string, unknown>),
    queryFn: async () => {
      const data = await cspmAPI.listFindings(effectiveParams);
      const items = data?.items ?? [];
      const filtered = filterByScope(items, accountIds, effectiveAccountId, scopeProvider);
      return { ...data, items: filtered, total: filtered.length };
    },
    staleTime: 20_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMFinding(id: string | null) {
  return useQuery({
    queryKey: cspmKeys.findingDetail(id ?? ''),
    queryFn: () => cspmAPI.getFinding(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useCSPMDriftFindings(page = 1, pageSize = 20) {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: cspmKeys.drift({ page, pageSize, _scope: accountIds }),
    queryFn: async () => {
      const data = await cspmAPI.getDriftFindings(page, pageSize, accountId, provider);
      const items = data?.items ?? [];
      const filtered = filterByScope(items, accountIds, accountId, provider);
      return { ...data, items: filtered, total: filtered.length };
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMResources(params: {
  page?: number;
  page_size?: number;
}) {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  const effectiveParams = {
    ...params,
    account_id: accountId || undefined,
    provider: !accountId ? provider : undefined,
  };
  return useQuery({
    queryKey: cspmKeys.resources({ ...effectiveParams, _scope: accountIds } as Record<string, unknown>),
    queryFn: async () => {
      const data = await cspmAPI.listResources(effectiveParams);
      const items = Array.isArray(data) ? data : [];
      return filterByScope(items, accountIds, accountId, provider);
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMCompliance() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.compliance(), accountIds],
    queryFn: () => cspmAPI.getCompliance(accountId, provider),
    staleTime: 60_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMFramework(framework: string | null) {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  return useQuery({
    queryKey: [...cspmKeys.framework(framework ?? ''), accountIds],
    queryFn: () => cspmAPI.getFramework(framework!, accountId, provider),
    enabled: !!framework && accountIds.length > 0,
    staleTime: 60_000,
  });
}

export function useCSPMScans() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  const accountIdsParam = !accountId && accountIds.length > 0 ? accountIds.join(',') : undefined;
  return useQuery({
    queryKey: [...cspmKeys.scans(), accountIds],
    queryFn: async () => {
      const data = await cspmAPI.listScans(accountId, accountIdsParam);
      const items = Array.isArray(data) ? data : [];
      return items.filter(s => {
        if (!s.account_id) return true;
        if (accountId) return s.account_id === accountId;
        if (provider) return accountIds.includes(s.account_id);
        return true;
      });
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMScanResources(scanId: string | null) {
  return useQuery({
    queryKey: cspmKeys.scanResources(scanId ?? ''),
    queryFn: () => cspmAPI.getScanResources(scanId!),
    enabled: !!scanId,
    staleTime: 60_000,
  });
}

export function useCSPMRules() {
  const provider = useScopeProvider();
  const accountId = useScopeAccountId();
  const accounts = useScopeStore(s => s.accounts);
  const effectiveProvider = provider ?? (accountId ? accounts.find(a => a.account_id === accountId)?.provider : undefined);

  return useQuery({
    queryKey: [...cspmKeys.rules(), effectiveProvider],
    queryFn: async () => {
      const data = await cspmAPI.listRules();
      const rules = data?.rules ?? [];
      if (effectiveProvider) {
        const filtered = rules.filter(r =>
          !r.provider || r.provider.toLowerCase() === effectiveProvider.toLowerCase()
        );
        return { ...data, rules: filtered, total: filtered.length };
      }
      return data;
    },
    staleTime: 60_000,
  });
}

export function useCSPMReports() {
  const accountIds = useScopeStore(s => s.accountIds);
  const accountId = useScopeAccountId();
  const provider = useScopeProvider();
  const accounts = useScopeStore(s => s.accounts);
  return useQuery({
    queryKey: [...cspmKeys.reports(), accountIds],
    queryFn: async () => {
      const data = await cspmAPI.listReports();
      const items = Array.isArray(data) ? data : [];
      if (!accountId && !provider) return items;
      const providerFrameworks: Record<string, string[]> = {
        aws: ['CISAWS', 'SOC2', 'PCIDSS', 'HIPAA', 'NIST'],
        azure: ['CISAZURE', 'SOC2', 'PCIDSS'],
        gcp: ['CISGCP', 'SOC2'],
        oci: ['CISOCI', 'SOC2'],
      };
      const effectiveProvider = provider ?? accounts.find(a => a.account_id === accountId)?.provider;
      if (!effectiveProvider) return items;
      return items.filter(r =>
        !r.framework ||
        (providerFrameworks[effectiveProvider] ?? []).some(fw =>
          (r.framework ?? '').toUpperCase().replace(/[-\s]/g, '').includes(fw)
        ) ||
        r.report_type === 'findings_export' ||
        r.report_type === 'posture'
      );
    },
    staleTime: 30_000,
    enabled: accountIds.length > 0,
  });
}

export function useCSPMReport(id: string | null) {
  return useQuery({
    queryKey: cspmKeys.report(id ?? ''),
    queryFn: () => cspmAPI.getReport(id!),
    enabled: !!id,
    staleTime: 10_000,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      return data?.status === 'generating' || data?.status === 'pending' ? 3_000 : false;
    },
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useUpdateFindingStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      cspmAPI.updateFindingStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cspmKeys.findings() });
    },
  });
}

export function useTriggerScan() {
  const queryClient = useQueryClient();
  const accountId = useScopeStore(s => s.mode === 'account' ? s.accountId : undefined);
  return useMutation({
    mutationFn: ({ accountId: overrideId }: { accountId?: string } = {}) =>
      cspmAPI.triggerScan(overrideId ?? accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cspmKeys.scans() });
      queryClient.invalidateQueries({ queryKey: cspmKeys.stats() });
    },
  });
}

export function useToggleRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, enable, reason }: { ruleId: string; enable: boolean; reason?: string }) =>
      enable
        ? cspmAPI.enableRule(ruleId)
        : cspmAPI.disableRule(ruleId, reason ?? 'Disabled by user'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cspmKeys.rules() });
    },
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();
  const accountIds = useScopeStore(s => s.accountIds);
  return useMutation({
    mutationFn: (params: {
      report_type: string;
      framework?: string;
      format?: string;
      date_from?: string;
      date_to?: string;
      account_ids?: string[];
    }) => cspmAPI.createReport({
      ...params,
      account_ids: params.account_ids ?? accountIds,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cspmKeys.reports() });
    },
  });
}

export function useCSPMRemediation(findingId: string | null) {
  return useQuery({
    queryKey: ['cspm', 'remediation', findingId ?? ''],
    queryFn: () => cspmAPI.getRemediation(findingId!),
    enabled: !!findingId,
    staleTime: 300_000,
  });
}
