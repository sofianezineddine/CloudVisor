'use client';
import { redirect } from 'next/navigation';

export default function CICDAssetsPage() {
  redirect('/cicd?tab=assets');
}
