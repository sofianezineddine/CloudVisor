'use client';
import { redirect } from 'next/navigation';

// Route /cspm/incidents → /cspm?tab=incidents
export default function CSPMIncidentsPage() {
  redirect('/cspm?tab=incidents');
}
