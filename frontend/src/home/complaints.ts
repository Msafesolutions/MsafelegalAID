import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { API_BASE, useAuth } from '../auth';

export type Complaint = {
  session_id: string; stage: string; status: string; incident_types?: string[];
  updated_at?: string; created_at?: string; draft?: string;
};
export const isDraftReady = (item: Complaint) => item.stage === 'completed' || item.status === 'completed';
export const complaintTitle = (item: Complaint) => item.incident_types?.length
  ? item.incident_types.map(s => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())).join(' · ')
  : 'Complaint draft';
const STAGES = ['safety_gate', 'free_narrative', 'probe', 'section_suggest', 'read_back', 'completed'];
const LABELS: Record<string, string> = {
  safety_gate: 'Safety check', free_narrative: 'Your account of events', probe: 'Incident details',
  gps_confirm: 'Confirming the location', section_suggest: 'Review legal sections',
  read_back: 'Review your statement', draft: 'Preparing your draft', completed: 'Draft ready',
};
export function complaintProgress(item: Complaint) {
  const index = STAGES.indexOf(item.stage);
  return { label: LABELS[item.stage] || 'Interview in progress', step: isDraftReady(item) ? 6 : item.stage === 'gps_confirm' ? 3 : Math.max(1, index + 1), total: 6 };
}

export function useComplaints() {
  const { user, token } = useAuth();
  const [items, setItems] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useFocusEffect(useCallback(() => {
    if (!user?.id || !token) { setItems([]); setLoading(false); return; }
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    setLoading(true); setError(false);
    void fetch(`${API_BASE}/api/fir/sessions/${encodeURIComponent(user.id)}`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    }).then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        if (!Array.isArray(data)) throw new Error();
        if (active) setItems(data.filter(item => item.status !== 'cancelled'));
      }).catch(() => { if (active) setError(true); })
      .finally(() => { clearTimeout(timer); if (active) setLoading(false); });
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  // Retry deliberately changes the callback identity to restart the focused request.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, token, attempt]));
  return { items, loading, error, retry: () => setAttempt(v => v + 1) };
}