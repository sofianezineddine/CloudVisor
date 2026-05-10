'use client';

import { useState, useEffect } from 'react';
import { 
  RecentlyVisitedItem, 
  getRecentlyVisited, 
  clearRecentlyVisited, 
  trackVisit, 
  subscribeToChanges 
} from '@/lib/recently-visited-tracker';

export function useRecentlyVisited() {
  const [items, setItems] = useState<RecentlyVisitedItem[]>([]);

  useEffect(() => {
    // Subscribe to changes from the global tracker
    const unsubscribe = subscribeToChanges((newItems) => {
      setItems(newItems);
    });

    return unsubscribe;
  }, []);

  const manualTrackVisit = (pathname: string) => {
    trackVisit(pathname);
  };

  const clearAll = () => {
    clearRecentlyVisited();
  };

  return {
    items,
    clearRecentlyVisited: clearAll,
    manualTrackVisit,
  };
}