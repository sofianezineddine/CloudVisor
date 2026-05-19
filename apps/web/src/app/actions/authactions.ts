'use server';

export async function authenticate(username: string, password: string) {
  return { success: true };
}

export async function revalidateAfterAuth() {
  return;
}
