import { useCallback, useEffect, useState } from 'react';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { db } from '../firebase';
import { useAuth } from './useAuth';

interface ProgressState {
  watched: Set<number>;
  loading: boolean;
  markWatched: (lessonId: number) => Promise<void>;
  unmarkWatched: (lessonId: number) => Promise<void>;
}

export function useProgress(): ProgressState {
  const { user } = useAuth();
  const [watched, setWatched]   = useState<Set<number>>(new Set());
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    if (!user) { setWatched(new Set()); setLoading(false); return; }

    const ref = doc(db, 'userProgress', user.uid);
    getDoc(ref)
      .then((snap) => {
        const ids: number[] = snap.exists() ? (snap.data().watchedLessons ?? []) : [];
        setWatched(new Set(ids));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user]);

  const markWatched = useCallback(async (lessonId: number) => {
    if (!user) return;
    setWatched((prev) => new Set([...prev, lessonId]));
    const ref = doc(db, 'userProgress', user.uid);
    const snap = await getDoc(ref);
    const current: number[] = snap.exists() ? (snap.data().watchedLessons ?? []) : [];
    if (!current.includes(lessonId)) {
      await setDoc(ref, { watchedLessons: [...current, lessonId] }, { merge: true });
    }
  }, [user]);

  const unmarkWatched = useCallback(async (lessonId: number) => {
    if (!user) return;
    setWatched((prev) => { const s = new Set(prev); s.delete(lessonId); return s; });
    const ref = doc(db, 'userProgress', user.uid);
    const snap = await getDoc(ref);
    const current: number[] = snap.exists() ? (snap.data().watchedLessons ?? []) : [];
    await setDoc(ref, { watchedLessons: current.filter((id) => id !== lessonId) }, { merge: true });
  }, [user]);

  return { watched, loading, markWatched, unmarkWatched };
}
