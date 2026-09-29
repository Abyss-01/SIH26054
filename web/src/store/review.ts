import { create } from "zustand";

// Review store — holds the Gemini markdown review (from the Supabase Edge
// Function) and the local-fallback summary. In production, the key is sent
// only to the Edge Function (server-side), never to the browser bundle.

export interface ReviewPayload {
  markdown: string;
  live: boolean; // true = from the live Edge Function; false = local fallback
}

interface ReviewState {
  review: ReviewPayload | null;
  live: boolean;
  loading: boolean;
  error: string | null;
  setReview: (review: ReviewPayload | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearReview: () => void;
}

export const useReviewStore = create<ReviewState>((set) => ({
  review: null,
  live: false,
  loading: false,
  error: null,
  setReview: (review) => set({ review }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearReview: () => set({ review: null, live: false, error: null }),
}));
