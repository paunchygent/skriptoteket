"""Shared-link PDF download action chrome for Klassrumskartan shares.

Purpose:
    Render the public share-page `Ladda ner PDF` action with stable spinner,
    disabled/busy affordance, and the scoped download controller.

Relationships:
    - Used by `share_renderer.py` for grouping and seating share headers.
    - Reuses the owned PDF href chrome slot from the share artifact contract.
    - Does not call public APIs, poll PDF state, or hydrate the share page.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
)

DOWNLOAD_ACTION_CONTROLLER_MARKER = 'data-skriptoteket-share-pdf-download-controller="owned"'

DOWNLOAD_ACTION_CSS = """
.share-download-pdf {
  align-items: center;
  border: 1px solid var(--navy);
  display: inline-flex;
  font-size: var(--text-sm);
  font-weight: 700;
  gap: 8px;
  justify-content: center;
  line-height: 1;
  padding: 10px 12px;
}
.share-download-pdf__label {
  min-width: 0;
}
.share-download-pdf__spinner {
  align-items: center;
  block-size: 12px;
  display: inline-flex;
  flex: 0 0 12px;
  inline-size: 12px;
  justify-content: center;
  opacity: 0;
  visibility: hidden;
}
.share-download-pdf__spinner svg {
  animation: share-download-pdf-spin 0.8s linear infinite;
  block-size: 12px;
  display: block;
  inline-size: 12px;
}
.share-download-pdf[data-skriptoteket-share-pdf-download-state="busy"]
  .share-download-pdf__spinner {
  opacity: 1;
  visibility: visible;
}
.share-download-pdf[data-skriptoteket-share-pdf-download-state="busy"] {
  background: var(--navy-05);
  border-color: var(--navy-40);
  color: var(--navy-70);
  cursor: progress;
}
@keyframes share-download-pdf-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .share-download-pdf__spinner svg {
    animation: none;
  }
}
""".strip()

DOWNLOAD_ACTION_CONTROLLER_SCRIPT = f"""
<script {DOWNLOAD_ACTION_CONTROLLER_MARKER}>
(function () {{
  var selector = '[data-skriptoteket-share-pdf-download="owned"]';
  var busyTimers = new WeakMap();
  var downloadHrefs = new WeakMap();
  var browserHandoffGuardMs = 1800;
  var minimumFocusRecoveryMs = 1000;
  function restoreLabel(action) {{
    var idleLabel = action.getAttribute('data-skriptoteket-share-pdf-idle-label');
    if (idleLabel === null || idleLabel === '') {{
      action.removeAttribute('aria-label');
      return;
    }}
    action.setAttribute('aria-label', idleLabel);
  }}
  function clearBusy(action) {{
    var timer = busyTimers.get(action);
    if (timer !== undefined) {{
      window.clearTimeout(timer);
      busyTimers.delete(action);
    }}
    action.setAttribute('data-skriptoteket-share-pdf-download-state', 'idle');
    action.removeAttribute('aria-busy');
    action.removeAttribute('aria-disabled');
    action.removeAttribute('data-skriptoteket-share-pdf-busy-started-at');
    if (downloadHrefs.has(action)) {{
      action.setAttribute('href', downloadHrefs.get(action));
      downloadHrefs.delete(action);
    }}
    restoreLabel(action);
  }}
  function clearAllBusy() {{
    document.querySelectorAll(selector).forEach(function (action) {{
      clearBusy(action);
    }});
  }}
  function clearRecoveredBusy() {{
    var now = Date.now();
    document.querySelectorAll(selector).forEach(function (action) {{
      var busyStartedAt = Number(
        action.getAttribute('data-skriptoteket-share-pdf-busy-started-at') || 0
      );
      if (now - busyStartedAt >= minimumFocusRecoveryMs) {{
        clearBusy(action);
      }}
    }});
  }}
  function setBusy(action) {{
    if (!action.hasAttribute('data-skriptoteket-share-pdf-idle-label')) {{
      action.setAttribute(
        'data-skriptoteket-share-pdf-idle-label',
        action.getAttribute('aria-label') || ''
      );
    }}
    if (!downloadHrefs.has(action)) {{
      downloadHrefs.set(action, action.getAttribute('href') || '');
    }}
    action.setAttribute('aria-busy', 'true');
    action.setAttribute('aria-disabled', 'true');
    action.setAttribute('data-skriptoteket-share-pdf-download-state', 'busy');
    action.setAttribute('data-skriptoteket-share-pdf-busy-started-at', String(Date.now()));
    action.setAttribute(
      'aria-label',
      action.getAttribute('data-skriptoteket-share-pdf-busy-label') || 'Förbereder PDF'
    );
    var previousTimer = busyTimers.get(action);
    if (previousTimer !== undefined) {{
      window.clearTimeout(previousTimer);
    }}
    busyTimers.set(action, window.setTimeout(function () {{
      clearBusy(action);
    }}, browserHandoffGuardMs));
    window.setTimeout(function () {{
      if (action.getAttribute('data-skriptoteket-share-pdf-download-state') === 'busy') {{
        action.removeAttribute('href');
      }}
    }}, 0);
  }}
  document.addEventListener(
    'click',
    function (event) {{
      var eventTarget = event.target;
      if (!(eventTarget instanceof Element)) {{
        return;
      }}
      var action = eventTarget.closest(selector);
      if (!(action instanceof HTMLAnchorElement)) {{
        return;
      }}
      if (
        event.defaultPrevented ||
        (event instanceof MouseEvent &&
          (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey))
      ) {{
        return;
      }}
      if (action.getAttribute('data-skriptoteket-share-pdf-download-state') === 'busy') {{
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }}
      setBusy(action);
    }},
    true
  );
  window.addEventListener('pageshow', clearAllBusy);
  window.addEventListener('focus', clearRecoveredBusy);
  document.addEventListener('visibilitychange', function () {{
    if (!document.hidden) {{
      clearRecoveredBusy();
    }}
  }});
}})();
</script>
""".strip()


def render_pdf_download_action() -> str:
    """Render the owned shared-link PDF download action."""

    return (
        '<a class="share-download-pdf" '
        f"{SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT} "
        'data-skriptoteket-share-pdf-download-state="idle" '
        'data-skriptoteket-share-pdf-busy-label="Förbereder PDF" '
        "download>"
        '<span class="share-download-pdf__label">Ladda ner PDF</span>'
        '<span class="share-download-pdf__spinner" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12a9 9 0 1 1-6.219-8.56"></path>'
        "</svg>"
        "</span>"
        "</a>"
    )
