import type { TtsPlayer } from './tts';

/** Web only: retain the actual play promise, which expo-audio currently discards.
 * Reuse the same element between clips so Safari retains user-granted playback.
 */
export function createBrowserTtsPlayer(audio: HTMLAudioElement, uri: string): TtsPlayer {
  let disposed = false;
  let finish: (() => void) | undefined;
  let guard: ReturnType<typeof setTimeout> | undefined;
  const onEnded = () => { if (!disposed) finish?.(); };
  audio.src = uri;
  audio.preload = 'auto';
  audio.addEventListener('ended', onEnded);

  return {
    play: async () => {
      if (disposed) return;
      // NotAllowedError and AbortError propagate to ChunkedSpeaker's local catch.
      await audio.play();
      if (!disposed) {
        clearTimeout(guard);
        guard = setTimeout(onEnded, 90_000);
      }
    },
    remove: () => {
      disposed = true;
      clearTimeout(guard);
      audio.removeEventListener('ended', onEnded);
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    },
    setPlaybackRate: rate => { audio.playbackRate = rate; },
    onFinish: callback => { finish = callback; },
  };
}