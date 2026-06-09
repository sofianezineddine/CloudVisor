// Stub for next/navigation
import { vi } from 'vitest';
export const useRouter = () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() });
export const usePathname = () => '/cspm';
export const useSearchParams = () => new URLSearchParams();
export const useParams = () => ({});
