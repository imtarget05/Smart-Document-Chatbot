/**
 * PostHog analytics stub - replaces actual PostHog dependency
 * In production, replace with actual PostHog SDK import
 */

export function trackEvent(event: string, properties?: Record<string, any>) {
  if (import.meta.env.DEV) {
    console.debug(`[PostHog] ${event}`, properties);
  }
  // In production: posthog.capture(event, properties)
}

export function identifyUser(userId: string, properties?: Record<string, any>) {
  if (import.meta.env.DEV) {
    console.debug(`[PostHog] identify: ${userId}`, properties);
  }
}

export default { trackEvent, identifyUser };