import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { createServerApiClient } from "@/shared/api/server";

export default async function InstallFromOAuth(props: {
  params: { providerType: string };
  searchparams: { [key: string]: string };
}) {
  const searchParams = props.searchParams;
  const params = props.params;
  const api = await createServerApiClient();
  const cookieStore = await cookies();
  const verifier = cookieStore.get("verifier");
  const installWebhook = cookieStore.get("oauth2_install_webhook");
  const pullingEnabled = cookieStore.get("oauth2_pulling_enabled");

  try {
    await api.post(
      `/providers/install/oauth2/${params.providerType}`,
      {
        ...searchParams,
        redirect_uri: `${process.env.NEXTAUTH_URL}/providers/oauth2/${params.providerType}`,
        verifier: verifier ? verifier.value : null,
        install_webhook: installWebhook ? installWebhook.value : false,
        pulling_enabled: pullingEnabled ? pullingEnabled.value : false,
      },
      {
        cache: "no-store",
      }
    );
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    redirect(
      `/providers?oauth=failure&reason=${encodeURIComponent(errorMessage)}`
    );
  }
  redirect("/providers?oauth=success");
}
