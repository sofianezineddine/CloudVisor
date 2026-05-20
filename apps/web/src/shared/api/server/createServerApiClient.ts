import { ApiClient } from "../ApiClient";

/**
 * CloudVisor shim — creates an API client for server-side usage.
 * In the CloudVisor integration, we don't use OAuth2Proxy headers.
 */
export async function createServerApiClient(): Promise<ApiClient> {
  const config = {
    AUTH_TYPE: 'NOAUTH',
    API_URL: process.env.API_URL || 'http://localhost:8007',
    API_URL_CLIENT: process.env.NEXT_PUBLIC_API_URL_CLIENT || 'http://localhost:8007',
    PUSHER_DISABLED: true,
    READ_ONLY: false,
    SENTRY_DISABLED: 'true',
  } as any;

  const session = {
    accessToken: 'server-side',
    tenantId: 'keep',
  } as any;

  return new ApiClient(session, config);
}
