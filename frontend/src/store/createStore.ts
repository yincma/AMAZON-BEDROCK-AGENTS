import { create, StateCreator } from 'zustand';
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// Helper type for creating slices
export type SliceCreator<T> = StateCreator<
  T,
  [
    ['zustand/devtools', never],
    ['zustand/persist', T],
    ['zustand/immer', never],
    ['zustand/subscribeWithSelector', never]
  ],
  [],
  T
>;

// Create store with middleware
export function createStore<T>(
  name: string,
  initializer: SliceCreator<T>,
  options?: {
    persist?: boolean;
    persistOptions?: {
      partialize?: (state: T) => any;
      storage?: any;
    };
  }
) {
  let store: StateCreator<T, [], [], T> = initializer;

  // Apply immer middleware for immutable updates
  store = immer(store) as StateCreator<T, [], [], T>;

  // Apply subscribeWithSelector middleware
  store = subscribeWithSelector(store) as StateCreator<T, [], [], T>;

  // Apply persist middleware if requested
  if (options?.persist) {
    store = persist(store, {
      name: `ppt-assistant-${name}`,
      ...options.persistOptions,
    }) as StateCreator<T, [], [], T>;
  }

  // Apply devtools middleware in development
  if (import.meta.env.DEV) {
    store = devtools(store, {
      name: `PPT Assistant - ${name}`,
    }) as StateCreator<T, [], [], T>;
  }

  return create<T>()(store);
}

// Combine multiple slices into a single store
export function combineSlices<T extends Record<string, any>>(
  slices: { [K in keyof T]: () => T[K] }
): () => T {
  return () => {
    const combined = {} as T;
    
    for (const key in slices) {
      const slice = slices[key]();
      Object.assign(combined, slice);
    }
    
    return combined;
  };
}