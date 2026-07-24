/**
 * PageSpeed Insights API Integration
 *
 * Cho JD1: Kiểm tra định kỳ hiệu năng PageSpeed
 * Xử lý SEO Technical và tối ưu loading
 */

const PAGESPEED_API =
  "https://www.googleapis.com/pagespeedonline/v5/runPagespeed";

export interface PageSpeedResult {
  performance: number;
  seo: number;
  accessibility: number;
  bestPractices: number;
  metrics: {
    fcp?: number; // First Contentful Paint (ms)
    lcp?: number; // Largest Contentful Paint (ms)
    tti?: number; // Time to Interactive (ms)
    tbt?: number; // Total Blocking Time (ms)
    cls?: number; // Cumulative Layout Shift
    si?: number; // Speed Index (ms)
  };
  diagnostics: string[];
  opportunities: { title: string; description: string; impact: string }[];
}

export async function checkPageSpeed(
  url: string,
  strategy: "mobile" | "desktop" = "mobile",
): Promise<PageSpeedResult | null> {
  const apiKey = import.meta.env.VITE_PAGESPEED_API_KEY || "";

  const params = new URLSearchParams({
    url,
    strategy,
    key: apiKey,
    category: ["performance", "accessibility", "seo", "best-practices"].join(
      ",",
    ),
  });

  try {
    const response = await fetch(`${PAGESPEED_API}?${params}`);
    if (!response.ok) {
      console.warn(`[PageSpeed] API returned ${response.status}`);
      return null;
    }

    const data = await response.json();
    const lhr = data.lighthouseResult;

    // Extract diagnostics and opportunities
    const diagnostics: string[] = [];
    const opportunities: {
      title: string;
      description: string;
      impact: string;
    }[] = [];

    if (lhr?.audits) {
      Object.entries(lhr.audits).forEach(([, audit]: [string, any]) => {
        if (audit.scoreDisplayMode === "diagnostic" && audit.details?.items) {
          diagnostics.push(audit.title);
        }
        if (
          audit.scoreDisplayMode === "opportunistic" &&
          audit.details?.items
        ) {
          opportunities.push({
            title: audit.title,
            description: audit.description || "",
            impact: audit.score !== null ? `Score: ${audit.score}` : "N/A",
          });
        }
      });
    }

    return {
      performance: Math.round((lhr?.categories?.performance?.score || 0) * 100),
      seo: Math.round((lhr?.categories?.seo?.score || 0) * 100),
      accessibility: Math.round(
        (lhr?.categories?.accessibility?.score || 0) * 100,
      ),
      bestPractices: Math.round(
        (lhr?.categories?.["best-practices"]?.score || 0) * 100,
      ),
      metrics: {
        fcp: lhr?.audits?.["first-contentful-paint"]?.numericValue,
        lcp: lhr?.audits?.["largest-contentful-paint"]?.numericValue,
        tti: lhr?.audits?.["interactive"]?.numericValue,
        tbt: lhr?.audits?.["total-blocking-time"]?.numericValue,
        cls: lhr?.audits?.["cumulative-layout-shift"]?.numericValue,
        si: lhr?.audits?.["speed-index"]?.numericValue,
      },
      diagnostics,
      opportunities,
    };
  } catch (error) {
    console.error("[PageSpeed] Check failed:", error);
    return null;
  }
}

/**
 * Frontend Performance Monitoring
 * Tracks Web Vitals and performance metrics
 */
export function initPerformanceMonitoring() {
  if (typeof window === "undefined") return;

  // Observe Largest Contentful Paint
  if ("PerformanceObserver" in window) {
    try {
      // LCP
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length > 0) {
          const lcp = entries[entries.length - 1];
          console.debug(`[Perf] LCP: ${lcp.startTime}ms`);
          // Track to analytics
          window.dispatchEvent(
            new CustomEvent("web-vital", {
              detail: {
                name: "LCP",
                value: lcp.startTime,
                rating:
                  lcp.startTime < 2500
                    ? "good"
                    : lcp.startTime < 4000
                      ? "needs-improvement"
                      : "poor",
              },
            }),
          );
        }
      }).observe({ type: "largest-contentful-paint", buffered: true });

      // FID / TBT
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          console.debug(`[Perf] TBT: ${(entry as any).duration}ms`);
        }
      }).observe({ type: "first-input", buffered: true });

      // CLS
      new PerformanceObserver((list) => {
        let cls = 0;
        for (const entry of list.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            cls += (entry as any).value;
          }
        }
        console.debug(`[Perf] CLS: ${cls}`);
        window.dispatchEvent(
          new CustomEvent("web-vital", {
            detail: {
              name: "CLS",
              value: cls,
              rating:
                cls < 0.1 ? "good" : cls < 0.25 ? "needs-improvement" : "poor",
            },
          }),
        );
      }).observe({ type: "layout-shift", buffered: true });
    } catch (e) {
      console.warn("[Perf] PerformanceObserver not fully supported");
    }
  }

  // Track page load timing
  if (window.performance?.timing) {
    const timing = window.performance.timing;
    const domReady = timing.domContentLoadedEventEnd - timing.navigationStart;
    const loadTime = timing.loadEventEnd - timing.navigationStart;

    console.debug(`[Perf] DOM Ready: ${domReady}ms, Load: ${loadTime}ms`);
  }
}

/**
 * Image optimization helper
 */
export function getOptimizedImageUrl(url: string): string {
  // In production, this would call an image CDN with width parameter
  // For now, return the original URL
  return url;
}

/**
 * Lazy load images
 */
export function lazyLoadImage(imgElement: HTMLImageElement, src: string) {
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            imgElement.src = src;
            imgElement.classList.add("loaded");
            observer.unobserve(imgElement);
          }
        });
      },
      { rootMargin: "200px" },
    );
    observer.observe(imgElement);
  } else {
    imgElement.src = src;
  }
}

export default {
  checkPageSpeed,
  initPerformanceMonitoring,
  getOptimizedImageUrl,
  lazyLoadImage,
};
