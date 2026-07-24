/**
 * Dashboard JS — vanilla JS + Chart.js for REST-driven admin pages.
 *
 * Uses wp-api-fetch (available via chatbotDashboard.root) for all REST calls.
 * Chart.js is loaded from CDN as a fallback if not enqueued.
 *
 * Why vanilla JS + Chart.js instead of React?
 *   1. Zero build step — no webpack/vite needed.
 *   2. Chart.js via CDN gives rich charts (pie, bar) with a single <canvas>.
 *   3. wp-api-fetch handles nonce headers automatically.
 *   4. Bundle stays small (~200 lines) — maintainable by any WordPress dev.
 *
 * @package Chatbot_Dashboard
 */

/* global chatbotDashboard, wp */

(function () {
  const { apiFetch } = wp;
  const ROOT = chatbotDashboard.root;

  // ── Helpers ──────────────────────────────────────────────────────────

  /** Fetch JSON from our REST namespace. */
  async function get(path) {
    return apiFetch({ url: ROOT + path });
  }

  /** PUT JSON. */
  async function put(path, body) {
    return apiFetch({
      url: ROOT + path,
      method: 'PUT',
      data: body,
    });
  }

  /** DELETE. */
  async function del(path) {
    return apiFetch({ url: ROOT + path, method: 'DELETE' });
  }

  /** Escape HTML for safe insertion. */
  function esc(str) {
    if (str === null || str === undefined) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  /** Pagination click handler. */
  function onPageClick(tableId, pagId, fetchFn) {
    return function (e) {
      e.preventDefault();
      const page = parseInt(e.target.dataset.page, 10);
      fetchFn(page);
    };
  }

  /** Render pagination links. */
  function renderPagination(pagId, current, total, per, fetchFn) {
    const pages = Math.ceil(total / per);
    let html = '';
    for (let i = 1; i <= pages; i++) {
      const active = i === current ? 'button-primary' : '';
      html +=
        '<button class="button ' +
        active +
        '" data-page="' +
        i +
        '" style="margin-right:4px">' +
        i +
        '</button>';
    }
    const el = document.getElementById(pagId);
    if (el) {
      el.innerHTML = html;
      el.querySelectorAll('[data-page]').forEach(function (btn) {
        btn.addEventListener('click', onPageClick(pagId, pagId, fetchFn));
      });
    }
  }

  // ── Overview Page ────────────────────────────────────────────────────

  function loadOverview() {
    get('/stats').then(function (data) {
      // Fill summary cards.
      document.querySelectorAll('[data-stat]').forEach(function (el) {
        var key = el.dataset.stat;
        var val = data[key];
        if (key === 'total_today') {
          el.textContent = val != null ? val : 0;
        } else if (key === 'avg_latency_ms') {
          el.textContent = val != null ? val + ' ms' : '—';
        } else if (key === 'error_rate') {
          el.textContent = val != null ? val + '%' : '—';
        }
      });

      // Recent conversations mini-table.
      get('/conversations?per=5').then(function (conv) {
        var tbody = document.getElementById('chatbot-recent-table');
        if (!tbody) return;
        if (!conv.items || conv.items.length === 0) {
          tbody.innerHTML =
            '<tr><td colspan="4">No conversations yet.</td></tr>';
          return;
        }
        tbody.innerHTML = conv.items
          .map(function (row) {
            var statusClass =
              row.status === 'error' ? 'status-error' : 'status-success';
            return (
              '<tr>' +
              '<td>' +
              esc(row.user_query).slice(0, 80) +
              '</td>' +
              '<td><code>' +
              esc(row.intent) +
              '</code></td>' +
              '<td>' +
              esc(row.latency_ms) +
              ' ms</td>' +
              '<td class="' +
              statusClass +
              '">' +
              esc(row.status) +
              '</td>' +
              '</tr>'
            );
          })
          .join('');
      });

      // Intent breakdown pie chart.
      drawIntentChart(data.intent_breakdown);
    });
  }

  function drawIntentChart(breakdown) {
    var canvas = document.getElementById('chatbot-intent-chart');
    if (!canvas || !breakdown || breakdown.length === 0) return;

    // Load Chart.js from CDN if not already loaded.
    if (typeof Chart === 'undefined') {
      var script = document.createElement('script');
      script.src =
        'https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js';
      script.onload = function () {
        buildChart(canvas, breakdown);
      };
      document.head.appendChild(script);
    } else {
      buildChart(canvas, breakdown);
    }
  }

  function buildChart(canvas, data) {
    var colors = [
      '#4f46e5',
      '#06b6d4',
      '#22c55e',
      '#eab308',
      '#ef4444',
    ];
    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: data.map(function (d) {
          return d.intent;
        }),
        datasets: [
          {
            data: data.map(function (d) {
              return parseInt(d.count, 10);
            }),
            backgroundColor: colors.slice(0, data.length),
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
        },
      },
    });
  }

  // ── Conversations Page ───────────────────────────────────────────────

  function loadConversations(page) {
    page = page || 1;
    var intent = document.getElementById('filter-intent')
      ? document.getElementById('filter-intent').value
      : '';
    var status = document.getElementById('filter-status')
      ? document.getElementById('filter-status').value
      : '';

    var params = '?page=' + page + '&per=15';
    if (intent) params += '&intent=' + encodeURIComponent(intent);
    if (status) params += '&status=' + encodeURIComponent(status);

    get('/conversations' + params).then(function (data) {
      var tbody = document.getElementById('chatbot-conv-table');
      if (!tbody) return;
      if (!data.items || data.items.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="9">No conversations found.</td></tr>';
        return;
      }
      tbody.innerHTML = data.items
        .map(function (row) {
          var statusClass =
            row.status === 'error' ? 'status-error' : 'status-success';
          return (
            '<tr>' +
            '<td>' +
            esc(row.id) +
            '</td>' +
            '<td><code>' +
            esc(row.session_id).slice(0, 12) +
            '</code></td>' +
            '<td>' +
            esc(row.user_query).slice(0, 60) +
            '</td>' +
            '<td><code>' +
            esc(row.intent) +
            '</code></td>' +
            '<td>' +
            esc(row.confidence_score) +
            '</td>' +
            '<td>' +
            esc(row.latency_ms) +
            ' ms</td>' +
            '<td class="' +
            statusClass +
            '">' +
            esc(row.status) +
            '</td>' +
            '<td>' +
            esc(row.created_at) +
            '</td>' +
            '<td><button class="button chatbot-delete-conv" data-id="' +
            esc(row.id) +
            '">Delete</button></td>' +
            '</tr>'
          );
        })
        .join('');

      // Bind delete buttons.
      tbody.querySelectorAll('.chatbot-delete-conv').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (!confirm('Delete this conversation?')) return;
          del('/conversations/' + btn.dataset.id).then(function () {
            loadConversations(page);
          });
        });
      });

      renderPagination(
        'chatbot-conv-pagination',
        page,
        data.total,
        15,
        loadConversations
      );
    });
  }

  // ── Documents Page ───────────────────────────────────────────────────

  function loadDocuments(page) {
    page = page || 1;
    get('/documents?page=' + page + '&per=15').then(function (data) {
      var tbody = document.getElementById('chatbot-doc-table');
      if (!tbody) return;
      if (!data.items || data.items.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="6">No documents uploaded yet.</td></tr>';
        return;
      }

      function formatSize(bytes) {
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
        if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return bytes + ' B';
      }

      tbody.innerHTML = data.items
        .map(function (row) {
          var statusClass = 'status-' + row.embedding_status;
          return (
            '<tr>' +
            '<td>' +
            esc(row.file_name) +
            '</td>' +
            '<td><code>' +
            esc(row.file_type) +
            '</code></td>' +
            '<td>' +
            formatSize(parseInt(row.file_size, 10)) +
            '</td>' +
            '<td>' +
            esc(row.chunk_count) +
            '</td>' +
            '<td class="' +
            statusClass +
            '">' +
            esc(row.embedding_status) +
            '</td>' +
            '<td>' +
            esc(row.created_at) +
            '</td>' +
            '</tr>'
          );
        })
        .join('');

      renderPagination(
        'chatbot-doc-pagination',
        page,
        data.total,
        15,
        loadDocuments
      );
    });
  }

  // ── A/B Testing Page ─────────────────────────────────────────────────

  function loadABVariants() {
    get('/ab-variants').then(function (data) {
      var tbody = document.getElementById('chatbot-ab-table');
      if (!tbody) return;

      var configs = {
        control:
          'confidence=0.45, chunk_size=512, top_k=5, rrf_k=60',
        'variant-a':
          'confidence=0.45, chunk_size=1024, top_k=5, rrf_k=60',
        'variant-b':
          'confidence=0.40, chunk_size=512, top_k=10, rrf_k=60',
        'variant-c':
          'confidence=0.45, chunk_size=512, top_k=5, rrf_k=100',
      };

      var descriptions = {
        control: 'Default RAG configuration',
        'variant-a': 'Double chunk size for richer context',
        'variant-b': 'Retrieve more chunks for broader coverage',
        'variant-c': 'Higher RRF weight for keyword matching',
      };

      tbody.innerHTML = Object.keys(data)
        .map(function (key) {
          var isActive = data[key];
          var config = configs[key] || '—';
          var desc = descriptions[key] || key;
          return (
            '<tr>' +
            '<td><code>' +
            esc(key) +
            '</code></td>' +
            '<td>' +
            esc(desc) +
            '</td>' +
            '<td><code>' +
            esc(config) +
            '</code></td>' +
            '<td class="' +
            (isActive ? 'status-success' : 'status-error') +
            '">' +
            (isActive ? 'Active' : 'Disabled') +
            '</td>' +
            '<td>' +
            '<button class="button chatbot-toggle-ab" data-variant="' +
            esc(key) +
            '" data-active="' +
            (isActive ? '1' : '0') +
            '">' +
            (isActive ? 'Disable' : 'Enable') +
            '</button>' +
            '</td>' +
            '</tr>'
          );
        })
        .join('');

      tbody.querySelectorAll('.chatbot-toggle-ab').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var variantId = btn.dataset.variant;
          var newActive = btn.dataset.active === '1' ? false : true;
          put('/ab-variants', {
            variant_id: variantId,
            active: newActive,
          }).then(function () {
            loadABVariants();
          });
        });
      });
    });
  }

  // ── Init ─────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    // Overview.
    if (document.getElementById('chatbot-stats-cards')) {
      loadOverview();
    }

    // Conversations.
    if (document.getElementById('chatbot-conv-table')) {
      loadConversations(1);
      var refreshBtn = document.getElementById('chatbot-refresh');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
          loadConversations(1);
        });
      }
      // Filter change triggers reload.
      ['filter-intent', 'filter-status'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) {
          el.addEventListener('change', function () {
            loadConversations(1);
          });
        }
      });
    }

    // Documents.
    if (document.getElementById('chatbot-doc-table')) {
      loadDocuments(1);
    }

    // A/B Testing.
    if (document.getElementById('chatbot-ab-table')) {
      loadABVariants();
    }
  });
})();
