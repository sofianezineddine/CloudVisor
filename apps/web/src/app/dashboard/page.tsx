import { redirect } from 'next/navigation';

// Backwards compatibility redirect
export default function DashboardRedirect() {
  redirect('/console');
}
