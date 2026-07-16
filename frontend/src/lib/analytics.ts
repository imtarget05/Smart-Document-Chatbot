/**
 * GA4 & GTM Analytics Integration
 * 
 * Cho JD1: Thực Tập Sinh IT Biết Dùng AI
 * - Google Analytics 4 event tracking
 * - Google Tag Manager dataLayer integration
 * - Omnichannel tracking (Facebook, TikTok, LinkedIn)
 * - PageSpeed monitoring
 * - User interaction tracking
 */

import { trackEvent as posthogTrack } from './posthog';

// ============================================================================
// Environment
// ============================================================================

const GA_MEASUREMENT_ID = import.meta.env.VITE_GA4_MEASUREMENT_ID || 'G-XXXXXXXXXX';
const GTM_CONTAINER_ID = import.meta.env.VITE_GTM_CONTAINER_ID || 'GTM-XXXXXXX';

// ============================================================================
// Type Declarations for Global Objects
// ============================================================================

declare global {
  interface Window {
    dataLayer: Record<string, any>[];
    gtag: (...args: any[]) => void;
    fbq: (event: string, name: string, params?: Record<string, any>) => void;
    ttq?: { track: (event: string, params?: Record<string, any>) => void };
  }
}

// ============================================================================
// Google Tag Manager
// ============================================================================

export function initGTM() {
  if (typeof window === 'undefined' || import.meta.env.DEV) return;

  window.dataLayer = window.dataLayer || [];

  // GTM Script
  const script = document.createElement('script');
  script.innerHTML = `
    (function(w,d,s,l,i){
      w[l]=w[l]||[];w[l].push({'gtm.start': new Date().getTime(),event:'gtm.js'});
      var f=d.getElementsByTagName(s)[0],
          j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';
      j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;
      f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','${GTM_CONTAINER_ID}');
  `;
  document.head.appendChild(script);

  // GTM noscript iframe
  const noscript = document.createElement('noscript');
  const iframe = document.createElement('iframe');
  iframe.src = `https://www.googletagmanager.com/ns.html?id=${GTM_CONTAINER_ID}`;
  iframe.height = '0';
  iframe.width = '0';
  iframe.style.display = 'none';
  iframe.style.visibility = 'hidden';
  noscript.appendChild(iframe);
  document.body.appendChild(noscript);

  console.log('[Analytics] GTM initialized:', GTM_CONTAINER_ID);
}

// ============================================================================
// GA4 - Page View Tracking
// ============================================================================

export function trackPageView(pageTitle: string, pagePath: string) {
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('config', GA_MEASUREMENT_ID, {
      page_title: pageTitle,
      page_path: pagePath,
    });
  }

  // Also push to PostHog for redundancy
  posthogTrack('page_view', { page_title: pageTitle, page_path: pagePath });
}

// ============================================================================
// GA4 - Custom Event Tracking
// ============================================================================

export function trackEvent(
  eventName: string,
  eventParams?: Record<string, any>
) {
  // Push to GA4
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('event', eventName, eventParams);
  }

  // Push to dataLayer for GTM
  pushToDataLayer({
    event: eventName,
    ...eventParams,
  });

  // Push to PostHog for internal analytics
  posthogTrack(eventName, eventParams);
}

// ============================================================================
// GTM DataLayer
// ============================================================================

export function pushToDataLayer(data: Record<string, any>) {
  if (typeof window !== 'undefined') {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(data);
  }
}

// ============================================================================
// Chat-Specific Events (Quan trọng nhất cho AI Chatbot)
// ============================================================================

export function trackChatQuery(query: string, documentCount: number) {
  trackEvent('chat_query', {
    query_length: query.length,
    document_count: documentCount,
    search_type: 'rag',
  });
}

export function trackAIResponse(
  responseTimeMs: number,
  confidenceScore: number,
  strategyUsed: string,
  tokenCount?: number,
) {
  trackEvent('ai_response', {
    response_time_ms: responseTimeMs,
    confidence_score: confidenceScore,
    rag_strategy: strategyUsed,
    token_count: tokenCount || 0,
  });
}

export function trackDocumentUpload(fileType: string, fileSize: number, status: 'success' | 'failed' = 'success') {
  trackEvent('document_upload', {
    file_type: fileType,
    file_size_bytes: fileSize,
    upload_status: status,
  });
}

export function trackDocumentDelete(documentId: number) {
  trackEvent('document_delete', {
    document_id: documentId,
  });
}

// ============================================================================
// User Interaction Events
// ============================================================================

export function trackLogin(method: string = 'email') {
  trackEvent('login', { method });
}

export function trackLogout() {
  trackEvent('logout');
}

export function trackError(errorType: string, errorMessage: string, componentName?: string) {
  trackEvent('app_error', {
    error_type: errorType,
    error_message: errorMessage.substring(0, 200),
    component: componentName || 'unknown',
  });
}

export function trackFeatureUsed(featureName: string, action: string) {
  trackEvent('feature_used', {
    feature: featureName,
    action,
  });
}

// ============================================================================
// Performance Monitoring
// ============================================================================

export function trackPerformance(metricName: string, value: number, unit: string = 'ms') {
  trackEvent('performance_metric', {
    metric_name: metricName,
    metric_value: value,
    metric_unit: unit,
  });
}

// Web Vitals tracking
export function trackWebVital(name: string, value: number, rating: 'good' | 'needs-improvement' | 'poor') {
  trackEvent('web_vital', {
    vital_name: name,
    vital_value: value,
    vital_rating: rating,
  });
}

// ============================================================================
// Omnichannel Tracking
// ============================================================================

export function trackFacebookPixelEvent(eventName: string, params?: Record<string, any>) {
  if (typeof window !== 'undefined' && typeof window.fbq === 'function') {
    window.fbq('track', eventName, params);
  }
}

export function trackTikTokEvent(eventName: string, params?: Record<string, any>) {
  if (typeof window !== 'undefined' && window.ttq && typeof window.ttq.track === 'function') {
    window.ttq.track(eventName, params);
  }
}

// ============================================================================
// Session Recording
// ============================================================================

export function trackUserSession(sessionId: string, durationSec: number) {
  trackEvent('session_ended', {
    session_id: sessionId,
    duration_seconds: durationSec,
  });
}

export default {
  initGTM,
  trackPageView,
  trackEvent,
  trackChatQuery,
  trackAIResponse,
  trackDocumentUpload,
  trackLogin,
  trackError,
  pushToDataLayer,
};