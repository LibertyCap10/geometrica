<script>
  // Title screen + PWA install prompt
  import { onMount } from 'svelte';

  let canInstall = false;
  let isInstalled = false;
  let isIOS = false;
  let deferredPrompt = null;

  function detectInstalled() {
    // Chrome/Edge/Android
    const standaloneMatch = window.matchMedia?.('(display-mode: standalone)')?.matches;
    // iOS Safari
    const iosStandalone = (navigator).standalone === true;
    return !!standaloneMatch || !!iosStandalone;
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
  });
</script>

<div class="title-screen">
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
