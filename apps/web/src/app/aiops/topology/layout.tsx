import { TopologySearchProvider } from "@/app/aiops/topology/TopologySearchContext";

export default function Layout({ children }: { children: any }) {
  return <TopologySearchProvider>{children}</TopologySearchProvider>;
}
