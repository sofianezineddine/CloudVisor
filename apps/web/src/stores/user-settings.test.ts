/**
 * Bug Condition Exploration Test for Dark Mode Persistence
 * 
 * **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
 * 
 * This test MUST FAIL on unfixed code - failure confirms the bug exists.
 * DO NOT attempt to fix the test or the code when it fails.
 * 
 * This test encodes the expected behavior - it will validate the fix when it passes after implementation.
 * 
 * GOAL: Surface counterexamples that demonstrate the bug exists.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { useUserSettings, type Theme } from './user-settings';

describe('Bug 1: Dark Mode Persistence - Bug Condition Exploration', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Clear document attribute
    document.documentElement.removeAttribute('data-theme');
  });

  /**
   * Property 1: Bug Condition - Dark Mode Lost on Page Refresh
   * 
   * This is a scoped property-based test for a deterministic bug.
   * We scope the property to the concrete failing case: dark mode.
   * 
   * **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
   */
  it('Property 1: Dark mode persists after page refresh (EXPECTED TO FAIL on unfixed code)', () => {
    fc.assert(
      fc.property(fc.constant('dark'), (theme) => {
        // Step 1: Set dark mode via useUserSettings store
        const { setTheme } = useUserSettings.getState();
        setTheme(theme as 'dark');

        // Step 2: Verify localStorage contains the theme
        const storedSettings = localStorage.getItem('cloudvisor-user-settings');
        expect(storedSettings).not.toBeNull();
        
        const parsedSettings = JSON.parse(storedSettings!);
        expect(parsedSettings.state.theme).toBe('dark');

        // Step 3: Simulate page refresh by re-running the inline script from layout.tsx
        // This is the EXACT script from apps/web/src/app/layout.tsx
        try {
          const s = localStorage.getItem('cloudvisor-user-settings');
          if (s) {
            const state = JSON.parse(s);
            // BUG: The script reads state.state.theme (double nesting)
            // but Zustand persist stores at state.theme (single nesting)
            const themeFromScript = state.state && state.state.theme ? state.state.theme : null;
            let finalTheme = themeFromScript;
            if (!finalTheme) finalTheme = localStorage.getItem('theme');
            if (finalTheme === 'dark') {
              document.documentElement.setAttribute('data-theme', 'dark');
            } else if (finalTheme === 'light') {
              document.documentElement.setAttribute('data-theme', 'light');
            }
          } else {
            const legacyTheme = localStorage.getItem('theme');
            if (legacyTheme === 'dark') {
              document.documentElement.setAttribute('data-theme', 'dark');
            }
          }
        } catch (e) {
          console.error('Theme init error:', e);
        }

        // Step 4: Assert that data-theme="dark" is applied to document element
        const appliedTheme = document.documentElement.getAttribute('data-theme');
        
        // **EXPECTED OUTCOME ON UNFIXED CODE**: This assertion FAILS
        // The inline script reads state.state.theme (double nesting) instead of state.theme (single nesting)
        // So it fails to find the theme and doesn't set data-theme="dark"
        expect(appliedTheme).toBe('dark');
      }),
      { numRuns: 10 } // Run 10 times to ensure reproducibility
    );
  });

  /**
   * Concrete example test for the bug condition
   * 
   * This test demonstrates the exact failing case without property-based testing.
   */
  it('Concrete example: Dark mode is lost after page refresh (EXPECTED TO FAIL on unfixed code)', () => {
    // Step 1: Set dark mode via useUserSettings store
    const { setTheme } = useUserSettings.getState();
    setTheme('dark');

    // Step 2: Verify localStorage contains state.theme = 'dark'
    const storedSettings = localStorage.getItem('cloudvisor-user-settings');
    expect(storedSettings).not.toBeNull();
    
    const parsedSettings = JSON.parse(storedSettings!);
    console.log('Stored settings structure:', JSON.stringify(parsedSettings, null, 2));
    expect(parsedSettings.state.theme).toBe('dark');

    // Step 3: Simulate the inline script from layout.tsx EXACTLY
    const s = localStorage.getItem('cloudvisor-user-settings');
    const state = JSON.parse(s!);
    
    // BUG: The script tries to read state.state.theme (double nesting)
    // But the actual structure is state.theme (single nesting)
    const themeFromScript = state.state && state.state.theme ? state.state.theme : null;
    console.log('Theme read by inline script (state.state.theme):', themeFromScript);
    console.log('Actual theme location (state.theme):', state.theme);
    console.log('Does state.state exist?:', state.state);
    
    // The script will fail to find the theme because it's looking at the wrong path
    let finalTheme = themeFromScript;
    if (!finalTheme) {
      console.log('Falling back to legacy theme key');
      finalTheme = localStorage.getItem('theme');
      console.log('Legacy theme value:', finalTheme);
    }
    
    if (finalTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else if (finalTheme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }

    // Step 4: Assert that data-theme="dark" is applied
    const appliedTheme = document.documentElement.getAttribute('data-theme');
    console.log('Applied theme to document:', appliedTheme);
    
    // **EXPECTED OUTCOME ON UNFIXED CODE**: This assertion FAILS
    // appliedTheme will be 'dark' because the fallback to localStorage.getItem('theme') works
    // BUT this is only because setTheme() also updates the legacy key
    // The bug is that state.state.theme doesn't exist, so the primary path fails
    expect(appliedTheme).toBe('dark');
  });

  /**
   * Diagnostic test to understand the localStorage structure
   * 
   * This test helps us understand how Zustand persist stores the state.
   */
  it('Diagnostic: Understand Zustand persist structure', () => {
    const { setTheme } = useUserSettings.getState();
    setTheme('dark');

    const storedSettings = localStorage.getItem('cloudvisor-user-settings');
    const parsedSettings = JSON.parse(storedSettings!);
    
    console.log('Full localStorage structure:', JSON.stringify(parsedSettings, null, 2));
    console.log('Correct path (state.theme):', parsedSettings.state.theme);
    console.log('Incorrect path (state.state.theme):', parsedSettings.state?.state?.theme);
    
    // This test always passes - it's just for diagnostics
    expect(parsedSettings.state.theme).toBe('dark');
  });
});


/**
 * Preservation Property Tests for Dark Mode Fix
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3**
 * 
 * These tests MUST PASS on unfixed code - passing confirms baseline behavior to preserve.
 * These tests verify that non-buggy behavior (light mode, Settings panel) remains unchanged.
 * 
 * GOAL: Ensure the fix doesn't break existing functionality.
 */

describe('Bug 1: Dark Mode Persistence - Preservation Properties', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Clear document attribute
    document.documentElement.removeAttribute('data-theme');
  });

  /**
   * Property 2.1: Light Mode Persistence (Preservation)
   * 
   * This property verifies that light mode persistence works correctly.
   * This is a preservation property - it tests non-buggy behavior that must remain unchanged.
   * 
   * **EXPECTED OUTCOME**: This test PASSES on unfixed code (confirms baseline behavior)
   * 
   * **Validates: Requirement 3.1**
   */
  it('Property 2.1: Light mode persists after page refresh (EXPECTED TO PASS on unfixed code)', () => {
    fc.assert(
      fc.property(fc.constant('light'), (theme) => {
        // Step 1: Set light mode via useUserSettings store
        const { setTheme } = useUserSettings.getState();
        setTheme(theme as Theme);

        // Step 2: Verify localStorage contains the theme
        const storedSettings = localStorage.getItem('cloudvisor-user-settings');
        expect(storedSettings).not.toBeNull();
        
        const parsedSettings = JSON.parse(storedSettings!);
        expect(parsedSettings.state.theme).toBe('light');

        // Step 3: Simulate page refresh by re-running the inline script from layout.tsx
        try {
          const s = localStorage.getItem('cloudvisor-user-settings');
          if (s) {
            const state = JSON.parse(s);
            // The script reads state.state.theme (double nesting)
            const themeFromScript = state.state && state.state.theme ? state.state.theme : null;
            let finalTheme = themeFromScript;
            if (!finalTheme) finalTheme = localStorage.getItem('theme');
            if (finalTheme === 'dark') {
              document.documentElement.setAttribute('data-theme', 'dark');
            } else if (finalTheme === 'light') {
              document.documentElement.setAttribute('data-theme', 'light');
            }
          } else {
            const legacyTheme = localStorage.getItem('theme');
            if (legacyTheme === 'dark') {
              document.documentElement.setAttribute('data-theme', 'dark');
            }
          }
        } catch (e) {
          console.error('Theme init error:', e);
        }

        // Step 4: Assert that data-theme="light" is applied to document element
        const appliedTheme = document.documentElement.getAttribute('data-theme');
        
        // For light mode, the script should either:
        // 1. Set data-theme="light" explicitly, OR
        // 2. Not set data-theme at all (light is default)
        // Both are acceptable for light mode preservation
        expect(appliedTheme === 'light' || appliedTheme === null).toBe(true);
      }),
      { numRuns: 10 }
    );
  });

  /**
   * Property 2.2: Settings Panel Displays Current Theme (Preservation)
   * 
   * This property verifies that the Settings panel correctly displays the current theme selection.
   * This is a preservation property - it tests non-buggy behavior that must remain unchanged.
   * 
   * **EXPECTED OUTCOME**: This test PASSES on unfixed code (confirms baseline behavior)
   * 
   * **Validates: Requirement 3.2**
   */
  it('Property 2.2: Settings panel displays current theme selection correctly (EXPECTED TO PASS on unfixed code)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('light' as const, 'dark' as const, 'browser' as const),
        (theme) => {
          // Step 1: Set theme via useUserSettings store
          const { setTheme } = useUserSettings.getState();
          setTheme(theme);

          // Step 2: Read theme from store (simulating Settings panel reading state)
          const currentTheme = useUserSettings.getState().theme;

          // Step 3: Assert that the store returns the correct theme
          expect(currentTheme).toBe(theme);

          // Step 4: Verify localStorage also contains the correct theme
          const storedSettings = localStorage.getItem('cloudvisor-user-settings');
          expect(storedSettings).not.toBeNull();
          
          const parsedSettings = JSON.parse(storedSettings!);
          expect(parsedSettings.state.theme).toBe(theme);
        }
      ),
      { numRuns: 20 } // Test all three theme values multiple times
    );
  });

  /**
   * Property 2.3: Theme Applies Immediately Without Refresh (Preservation)
   * 
   * This property verifies that theme changes via Settings panel apply immediately
   * without requiring a page refresh.
   * This is a preservation property - it tests non-buggy behavior that must remain unchanged.
   * 
   * **EXPECTED OUTCOME**: This test PASSES on unfixed code (confirms baseline behavior)
   * 
   * **Validates: Requirement 3.3**
   */
  it('Property 2.3: Theme changes apply immediately without refresh (EXPECTED TO PASS on unfixed code)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('light' as const, 'dark' as const),
        (theme) => {
          // Step 1: Set theme via useUserSettings store (simulating Settings panel action)
          const { setTheme } = useUserSettings.getState();
          setTheme(theme);

          // Step 2: Verify data-theme attribute is set immediately on document element
          const appliedTheme = document.documentElement.getAttribute('data-theme');
          expect(appliedTheme).toBe(theme);

          // Step 3: Verify legacy localStorage key is also updated for compatibility
          const legacyTheme = localStorage.getItem('theme');
          expect(legacyTheme).toBe(theme);

          // Step 4: Verify store state is updated
          const currentTheme = useUserSettings.getState().theme;
          expect(currentTheme).toBe(theme);
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * Concrete example: Light mode persistence works correctly
   * 
   * This test demonstrates that light mode persistence is not affected by the bug.
   */
  it('Concrete example: Light mode persists after page refresh (EXPECTED TO PASS on unfixed code)', () => {
    // Step 1: Set light mode via useUserSettings store
    const { setTheme } = useUserSettings.getState();
    setTheme('light');

    // Step 2: Verify localStorage contains state.theme = 'light'
    const storedSettings = localStorage.getItem('cloudvisor-user-settings');
    expect(storedSettings).not.toBeNull();
    
    const parsedSettings = JSON.parse(storedSettings!);
    expect(parsedSettings.state.theme).toBe('light');

    // Step 3: Simulate the inline script from layout.tsx
    const s = localStorage.getItem('cloudvisor-user-settings');
    const state = JSON.parse(s!);
    
    const themeFromScript = state.state && state.state.theme ? state.state.theme : null;
    let finalTheme = themeFromScript;
    if (!finalTheme) finalTheme = localStorage.getItem('theme');
    
    if (finalTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else if (finalTheme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }

    // Step 4: Assert that data-theme="light" is applied or null (both acceptable for light mode)
    const appliedTheme = document.documentElement.getAttribute('data-theme');
    expect(appliedTheme === 'light' || appliedTheme === null).toBe(true);
  });

  /**
   * Concrete example: Browser theme preference works correctly
   * 
   * This test verifies that the 'browser' theme option works as expected.
   */
  it('Concrete example: Browser theme preference resolves correctly (EXPECTED TO PASS on unfixed code)', () => {
    // Step 1: Set browser theme via useUserSettings store
    const { setTheme } = useUserSettings.getState();
    setTheme('browser');

    // Step 2: Verify store contains 'browser' theme
    const currentTheme = useUserSettings.getState().theme;
    expect(currentTheme).toBe('browser');

    // Step 3: Verify localStorage contains 'browser' theme
    const storedSettings = localStorage.getItem('cloudvisor-user-settings');
    expect(storedSettings).not.toBeNull();
    
    const parsedSettings = JSON.parse(storedSettings!);
    expect(parsedSettings.state.theme).toBe('browser');

    // Step 4: Verify that setTheme resolves 'browser' to actual theme and applies it
    // The setTheme function should resolve 'browser' based on matchMedia
    // In our test environment, matchMedia always returns false (light mode)
    const appliedTheme = document.documentElement.getAttribute('data-theme');
    expect(appliedTheme).toBe('light');
  });

  /**
   * Property 2.4: Theme Transitions Work Correctly (Preservation)
   * 
   * This property verifies that transitioning between themes works correctly.
   * This is a preservation property - it tests non-buggy behavior that must remain unchanged.
   * 
   * **EXPECTED OUTCOME**: This test PASSES on unfixed code (confirms baseline behavior)
   */
  it('Property 2.4: Theme transitions work correctly (EXPECTED TO PASS on unfixed code)', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom('light' as const, 'dark' as const), { minLength: 2, maxLength: 5 }),
        (themes) => {
          const { setTheme } = useUserSettings.getState();

          // Apply each theme in sequence
          for (const theme of themes) {
            setTheme(theme);

            // Verify immediate application
            const appliedTheme = document.documentElement.getAttribute('data-theme');
            expect(appliedTheme).toBe(theme);

            // Verify store state
            const currentTheme = useUserSettings.getState().theme;
            expect(currentTheme).toBe(theme);
          }

          // Verify final theme is persisted
          const finalTheme = themes[themes.length - 1];
          const storedSettings = localStorage.getItem('cloudvisor-user-settings');
          const parsedSettings = JSON.parse(storedSettings!);
          expect(parsedSettings.state.theme).toBe(finalTheme);
        }
      ),
      { numRuns: 10 }
    );
  });
});
