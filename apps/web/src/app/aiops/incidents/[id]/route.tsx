import { redirect } from "next/navigation";

// This is just a redirect from legacy route
export async function GET(
  request: Request,
  props: { params: { id: string } }
) {
  redirect(`/incidents/${props.params.id}/alerts`);
}
