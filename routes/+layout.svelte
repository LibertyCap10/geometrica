<script>
  // Root layout — imports global styles for the entire app
  import '../app.css';
  import { onMount } from 'svelte';
  import { browser, dev } from '$app/environment';

  let showInstalledToast = false;
  let toastTimer;

  function isStandalone() {
    if (!browser) return false;
    // iOS Safari uses navigator.standalone
    // Other browsers support display-mode media query
    // @ts-expect-error - iOS-only property
    const iosStandalone = typeof navigator !== 'undefined' && navigator.standalone === true;
    const mqStandalone = typeof window !== 'undefined' && window.matchMedia?.('(display-mode: standalone)').matches;
    return !!iosStandalone || !!mqStandalone;
  }

  function maybeShowInstalledToast() {
    if (!browser) return;
    const key = 'pwa_just_installed';
    // Show only when running as installed PWA and the install flag exists
    if (isStandalone() && localStorage.getItem(key)) {
      localStorage.removeItem(key);
      showInstalledToast = true;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        showInstalledToast = false;
      }, 3200);
    }
  }

  onMount(() => {
    // Register service worker for PWA installability (skip during dev to avoid cache confusion)
    if (browser && !dev && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/service-worker.js').catch(() => {});
    }

    // When the browser reports a successful install, mark it.
    // The next time the app is launched in standalone mode we show a one-time toast.
    if (browser) {
      window.addEventListener('appinstalled', () => {
        try {
          localStorage.setItem('pwa_just_installed', '1');
        } catch {
          // ignore
        }
      });
    }

    maybeShowInstalledToast();
  });
</script>

{#if showInstalledToast}
  <div class="toast toast-installed" role="status" aria-live="polite">
    ✅ Installed successfully — added to your home screen.
  </div>
{/if}

<slot />
