import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://kbbctdxfzmkxustbeiwq.supabase.co';
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_T8MTVIi_oemhXFE0Vf2hsA_OnFN3Sd6';

export const supabase = createClient(supabaseUrl, supabaseKey);
