/**
 * PostHog Analytics Integration (issue #38, #63)
 *
 * Previously this was a stub that only console.debug'd in dev and did nothing
 * in production. Now it dynamically loads the real PostHog SDK when a valid
 * PostHog API key is configured via VITE_POSTHOG_KEY / VITE_POSTHOG_HOST.
 *
 * Behavior:
 * - If VITE_POSTHOG_KEY is set: loads posthog-js, initializes it, and routes
 *   trackEvent/identifyUser to the real SDK.
 * - If VITE_POSTHOG_KEY is NOT set: falls back to a no-op (with a one-time
 *   dev-only console.info) so production builds do not spam the console.
 *
 * The console.debug calls that polluted production logs are removed (#63).
 */

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY as string | undefined;
const POSTHOG_HOST =
  (import.meta.env.VITE_POSTHOG_HOST as string | undefined) ||
  "https://app.posthog.com";

type PostHogClient = {
  capture: (event: string, properties?: Record<string, unknown>) => void;
  identify: (userId: string, properties?: Record<string, unknown>) => void;
  reset: () => void;
};

let _client: PostHogClient | null = null;
let _initAttempted = false;
let _warnedMissingKey = false;

/**
 * Lazily initialize the PostHog SDK. Returns null if the SDK is unavailable
 * or no API key is configured.
 */
async function _getClient(): Promise<PostHogClient | null> {
  if (_initAttempted) return _client;
  _initAttempted = true;

  if (!POSTHOG_KEY) {
    if (import.meta.env.DEV && !_warnedMissingKey) {
      _warnedMissingKey = true;
      console.info(
        "[PostHog] VITE_POSTHOG_KEY not set - analytics disabled. Set it to enable tracking.",
      );
    }
    return null;
  }

  try {
    const { default: posthog } = await import("posthog-js");
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      autocapture: false,
      disable_session_recording: !import.meta.env.PROD,
    });
    _client = posthog as unknown as PostHogClient;
    if (import.meta.env.DEV) {
      console.info("[PostHog] SDK initialized successfully.");
    }
  } catch (err) {
    console.warn("[PostHog] Failed to load SDK - analytics disabled.", err);
  }
  return _client;
}

// Kick off initialization eagerly so the first event is captured.
if (POSTHOG_KEY) {
  void _getClient();
}

export function trackEvent(event: string, properties?: Record<string, any>) {
  const client = _client;
  if (client) {
    client.capture(event, properties);
    return;
  }
  // SDK not yet loaded or not configured - fire-and-forget init then capture.
  void _getClient().then((c) => {
    c?.capture(event, properties);
  });
}

export function identifyUser(userId: string, properties?: Record<string, any>) {
  const client = _client;
  if (client) {
    client.identify(userId, properties);
    return;
  }
  void _getClient().then((c) => {
    c?.identify(userId, properties);
  });
}

export function resetUser() {
  _client?.reset();
}

export default { trackEvent, identifyUser, resetUser };
