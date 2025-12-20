<script>
  // Title screen + PWA install prompt
  import { onMount } from 'svelte';

  let canInstall = false;
  let isInstalled = false;
  let isIOS = false;
  let deferredPrompt = null;

  let isTouchLike = false;
  let isPortrait = false;
  let rotateDismissed = false;
  let rotateError = '';

  function detectInstalled() {
    // Chrome/Edge/Android
    const standaloneMatch = window.matchMedia?.('(display-mode: standalone)')?.matches;
    // iOS Safari
    const iosStandalone = (navigator).standalone === true;
    return !!standaloneMatch || !!iosStandalone;
  }


  function detectTouchLike() {
    return (
      (typeof window !== 'undefined' &&
        (window.matchMedia?.('(pointer: coarse)').matches ||
          window.matchMedia?.('(hover: none)').matches)) ||
      (typeof navigator !== 'undefined' &&
        (navigator.maxTouchPoints || navigator.msMaxTouchPoints))
    );
  }

  function updateOrientation() {
    if (typeof window === 'undefined') return;
    isTouchLike = detectTouchLike();
    isPortrait = window.matchMedia?.('(orientation: portrait)')?.matches ?? (window.innerHeight > window.innerWidth);
    if (!isTouchLike) {
      rotateDismissed = true;
    }
  }

  async function requestLandscapeLock() {
    rotateError = '';
    try {
      if (screen?.orientation?.lock) {
        await screen.orientation.lock('landscape');
      } else {
        rotateError = 'Landscape lock is not supported on this browser.';
      }
    } catch (e) {
      rotateError = 'Could not lock orientation. Please rotate your phone manually.';
    }
  }


  async function promptInstall() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    try {
      const choice = await deferredPrompt.userChoice;
      // hide either way once the prompt is used
      canInstall = false;
      deferredPrompt = null;
    } catch {
      // ignore
    }
  }

  onMount(() => {
    isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    isInstalled = detectInstalled();
    updateOrientation();

    window.addEventListener('resize', updateOrientation);
    window.addEventListener('orientationchange', updateOrientation);

    window.addEventListener('appinstalled', () => {
      isInstalled = true;
      canInstall = false;
      deferredPrompt = null;
    });

    window.addEventListener('beforeinstallprompt', (e) => {
      // Chrome/Edge install prompt
      e.preventDefault();
      deferredPrompt = e;
      canInstall = true;
    });
    return () => {
      window.removeEventListener('resize', updateOrientation);
      window.removeEventListener('orientationchange', updateOrientation);
    };
  });
</script>

<div class="title-screen">

  {#if isTouchLike && isPortrait && !rotateDismissed}
    <div class="rotate-overlay" role="dialog" aria-modal="true">
      <div class="rotate-card">
        <div class="rotate-title">Rotate to Landscape</div>
        <div class="rotate-desc">
          Geometrica plays best in <b>horizontal</b> mode. Please rotate your phone.
        </div>
        <div class="rotate-actions">
          <button class="btn primary" on:click={requestLandscapeLock}>Lock Landscape</button>
          <button class="btn" on:click={() => (rotateDismissed = true)}>Continue</button>
        </div>
        {#if rotateError}
          <div class="rotate-error">{rotateError}</div>
        {/if}
      </div>
    </div>
  {/if}

  <div class="title-wrap">
    <h1 class="main-title">GEOMETRICA</h1>

    <div class="menu">
      <a class="btn primary" href="/game">Start</a>
      <a class="btn" href="/how-to-play">How To Play</a>
      <a class="btn" href="/leaderboard">Leaderboard</a>
    </div>

    {#if !isInstalled}
      <div class="pwa-card">
        <div class="pwa-title">Install Geometrica</div>
        <div class="pwa-desc">
          Get the full-screen arcade experience — add it to your home screen.
        </div>

        {#if canInstall}
          <button class="btn primary" on:click={promptInstall}>Install App</button>
        {:else if isIOS}
          <div class="pwa-ios">
            <span>On iPhone/iPad:</span>
            <span><b>Share</b> → <b>Add to Home Screen</b></span>
          </div>
        {:else}
          <div class="pwa-ios" style="opacity:0.9;">
            Your browser may not support one-tap install. You can still bookmark the site.
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>
