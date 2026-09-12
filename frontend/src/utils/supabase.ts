import { createClient, type Session, type User as SupabaseUser } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  'placeholder-anon-key';

export const supabase = createClient(supabaseUrl, supabaseKey);

/**
 * Trigger Google OAuth sign-in via Supabase.
 * Redirects to Google's consent screen, then back to the app.
 */
export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin,
    },
  });
  if (error) throw error;
  return data;
}

/**
 * Sign out from Supabase (clears session + tokens).
 */
export async function signOutSupabase() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

/**
 * Subscribe to auth state changes.
 * Returns the unsubscribe function.
 */
export function onAuthStateChange(
  callback: (session: Session | null, user: SupabaseUser | null) => void,
) {
  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session, session?.user ?? null);
  });
  return subscription.unsubscribe;
}

export type { Session, SupabaseUser };
