import AlertsPage from "./ui/alerts";

type PageProps = {
  params: { id: string };
  searchParams: { [key: string]: string | string[] | undefined };
};

export default function Page({ params }: PageProps) {
  return <AlertsPage presetName={params.id} initialFacets={[]} />;
}

// metadata removed for dynamic rendering
