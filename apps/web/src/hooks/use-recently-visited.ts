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
    console.log('useRecentlyVisited: Setting up subscription');
    
    // Subscribe to changes from the global tracker
    const unsubscribe = subscribeToChanges((newItems) => {
      console.log('useRecentlyVisited: Received items update:', newItems);
      setItems(newItems);
    });

    return unsubscribe;
  }, []);

  const manualTrackVisit = (pathname: string) => {
    console.log('useRecentlyVisited: Manual track visit:', pathname);
    trackVisit(pathname);
  };

  const clearAll = () => {
    console.log('useRecentlyVisited: Clearing all items');
    clearRecentlyVisited();
  };

  return {
    items,
    clearRecentlyVisited: clearAll,
    manualTrackVisit,
  };
}