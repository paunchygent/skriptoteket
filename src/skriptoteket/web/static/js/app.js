// Skriptoteket frontend helpers (HTMX + small page initializers)
(function () {
  var CODEMIRROR_CSS_URL = "/static/vendor/codemirror/codemirror.min.css";
  var CODEMIRROR_CORE_URL = "/static/vendor/codemirror/codemirror.min.js";
  var CODEMIRROR_PYTHON_MODE_URL = "/static/vendor/codemirror/mode/python/python.min.js";

  /** @type {Map<string, Promise<void>>} */
  var stylesheetPromises = new Map();
  /** @type {Map<string, Promise<void>>} */
  var scriptPromises = new Map();

  function ensureStylesheet(href) {
    var existing = document.querySelector('link[rel="stylesheet"][href="' + href + '"]');
    if (existing) return Promise.resolve();

    if (stylesheetPromises.has(href)) return stylesheetPromises.get(href);

    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    var promise = new Promise(function (resolve) {
      link.addEventListener("load", function () {
        link.dataset.huleeduLoaded = "true";
        resolve();
      });
      link.addEventListener("error", function () {
        // Fail open: CSS is helpful but should never block the page.
        resolve();
      });
    });
    stylesheetPromises.set(href, promise);
    document.head.appendChild(link);
    return promise;
  }

  function loadScript(src) {
    if (scriptPromises.has(src)) return scriptPromises.get(src);

    var existing = document.querySelector('script[src="' + src + '"]');
    if (existing) {
      var alreadyLoaded = existing.dataset && existing.dataset.huleeduLoaded === "true";
      if (alreadyLoaded) return Promise.resolve();

      var existingPromise = new Promise(function (resolve, reject) {
        existing.addEventListener("load", function () {
          existing.dataset.huleeduLoaded = "true";
          resolve();
        });
        existing.addEventListener("error", function () {
          reject(new Error("Failed to load script: " + src));
        });
      });
      scriptPromises.set(src, existingPromise);
      return existingPromise;
    }

    var script = document.createElement("script");
    script.src = src;
    var promise = new Promise(function (resolve, reject) {
      script.addEventListener("load", function () {
        script.dataset.huleeduLoaded = "true";
        resolve();
      });
      script.addEventListener("error", function () {
        reject(new Error("Failed to load script: " + src));
      });
    });
    scriptPromises.set(src, promise);
    document.head.appendChild(script);
    return promise;
  }

  /** @type {Promise<void> | null} */
  var codeMirrorAssetsPromise = null;

  /** @type {Set<any>} */
  var activeCodeMirrorEditors = new Set();
  var resizeRefreshAnimationFrame = null;
  /** @type {ResizeObserver | null} */
  var codeMirrorResizeObserver = null;

  function ensureCodeMirrorAssets() {
    if (window.CodeMirror) return Promise.resolve();
    if (codeMirrorAssetsPromise) return codeMirrorAssetsPromise;

    codeMirrorAssetsPromise = ensureStylesheet(CODEMIRROR_CSS_URL)
      .then(function () { return loadScript(CODEMIRROR_CORE_URL); })
      .then(function () { return loadScript(CODEMIRROR_PYTHON_MODE_URL); });

    return codeMirrorAssetsPromise;
  }

  function initFileInputs(root) {
    var inputs = root.querySelectorAll('input[type="file"][data-huleedu-file-name-target]');
    inputs.forEach(function (input) {
      if (input.dataset.huleeduInitialized === "true") return;
      input.dataset.huleeduInitialized = "true";

      var targetId = input.dataset.huleeduFileNameTarget;
      if (!targetId) return;
      var target = document.getElementById(targetId);
      if (!target) return;

      var emptyLabel = target.textContent || "Ingen fil vald";
      input.addEventListener("change", function () {
        var fileName = input.files && input.files[0] ? input.files[0].name : "";
        target.textContent = fileName || emptyLabel;
      });
    });
  }

  var COPY_FEEDBACK_MS = 2000;

  function initCopyButtons(root) {
    var buttons = root.querySelectorAll("[data-huleedu-copy-target]");
    buttons.forEach(function (button) {
      if (button.dataset.huleeduCopyInitialized === "true") return;
      button.dataset.huleeduCopyInitialized = "true";

      var targetId = button.dataset.huleeduCopyTarget;
      if (!targetId) return;

      button.addEventListener("click", function (evt) {
        evt.preventDefault();
        var target = document.getElementById(targetId);
        if (!target) return;

        var text = target.value !== undefined ? target.value : target.textContent;
        if (!text) return;

        navigator.clipboard.writeText(text).then(function () {
          var originalText = button.textContent;
          var successText = button.dataset.huleeduCopySuccess || "✓ Kopierat!";
          button.textContent = successText;
          button.classList.add("btn-success");
          button.classList.remove("btn-primary");

          setTimeout(function () {
            button.textContent = originalText;
            button.classList.remove("btn-success");
            button.classList.add("btn-primary");
          }, COPY_FEEDBACK_MS);
        });
      });
    });
  }

  var TOAST_DEFAULT_AUTO_DISMISS_MS = 12000;
  var TOAST_EXIT_ANIMATION_MS = 300;

  /** @type {number | null} */
  var toastReplaceTimeoutId = null;
  /** @type {Element | null} */
  var pendingToastReplaceNode = null;

  function dismissToast(toast) {
    if (!toast || !toast.classList) return;
    if (toast.dataset.huleeduToastDismissing === "true") return;
    toast.dataset.huleeduToastDismissing = "true";

    toast.classList.add("huleedu-toast-dismiss-out");
    setTimeout(function () {
      if (document.contains(toast)) toast.remove();
    }, TOAST_EXIT_ANIMATION_MS);
  }

  function scheduleToastAutoDismiss(toast) {
    if (!toast || toast.dataset.dismissScheduled) return;
    toast.dataset.dismissScheduled = "true";

    var delay = parseInt(toast.dataset.autoDismiss, 10);
    if (!isFinite(delay) || delay <= 0) delay = TOAST_DEFAULT_AUTO_DISMISS_MS;

    setTimeout(function () {
      if (!document.contains(toast)) return;
      dismissToast(toast);
    }, delay);
  }

  function initToasts() {
    document.querySelectorAll("[data-auto-dismiss]").forEach(function (toast) {
      scheduleToastAutoDismiss(toast);
    });
  }

  function extractToastNode(fragment) {
    if (!fragment) return null;
    if (fragment.nodeType === Node.DOCUMENT_FRAGMENT_NODE) return fragment.firstElementChild;
    if (fragment.nodeType === Node.ELEMENT_NODE) return fragment;
    return null;
  }

  function stripOobAttributes(node) {
    if (!node || !node.removeAttribute) return;
    node.removeAttribute("hx-swap-oob");
    node.removeAttribute("data-hx-swap-oob");
  }

  function replaceToastWithFade(toastNode) {
    var container = document.getElementById("toast-container");
    if (!container || !toastNode) return;

    pendingToastReplaceNode = toastNode;

    if (toastReplaceTimeoutId) {
      clearTimeout(toastReplaceTimeoutId);
      toastReplaceTimeoutId = null;
    }

    var existing = container.querySelector(".huleedu-toast");
    if (existing) {
      dismissToast(existing);

      toastReplaceTimeoutId = setTimeout(function () {
        toastReplaceTimeoutId = null;

        var liveContainer = document.getElementById("toast-container");
        if (!liveContainer) return;

        liveContainer.replaceChildren();

        var node = pendingToastReplaceNode;
        pendingToastReplaceNode = null;
        if (!node) return;

        stripOobAttributes(node);
        liveContainer.appendChild(node);
        scheduleToastAutoDismiss(node);
      }, TOAST_EXIT_ANIMATION_MS);
      return;
    }

    container.replaceChildren();
    pendingToastReplaceNode = null;
    stripOobAttributes(toastNode);
    container.appendChild(toastNode);
    scheduleToastAutoDismiss(toastNode);
  }

  function ensureCodeMirrorResizeObserver() {
    if (codeMirrorResizeObserver) return;
    if (!window.ResizeObserver) return;

    codeMirrorResizeObserver = new ResizeObserver(function () {
      scheduleAllEditorsRefresh();
    });
  }

  function observeCodeMirrorEditor(editor) {
    if (!editor || typeof editor.getWrapperElement !== "function") return;
    ensureCodeMirrorResizeObserver();
    if (!codeMirrorResizeObserver) return;

    var wrapper = editor.getWrapperElement();
    if (!wrapper) return;
    if (wrapper.dataset && wrapper.dataset.huleeduResizeObserved === "true") return;
    if (wrapper.dataset) wrapper.dataset.huleeduResizeObserved = "true";

    codeMirrorResizeObserver.observe(wrapper);
  }

  function scheduleAllEditorsRefresh() {
    if (resizeRefreshAnimationFrame) cancelAnimationFrame(resizeRefreshAnimationFrame);
    resizeRefreshAnimationFrame = requestAnimationFrame(function () {
      resizeRefreshAnimationFrame = null;
      activeCodeMirrorEditors.forEach(function (editor) {
        if (!editor || typeof editor.getWrapperElement !== "function") return;
        var wrapper = editor.getWrapperElement();
        if (!wrapper || !document.contains(wrapper)) {
          activeCodeMirrorEditors.delete(editor);
          if (codeMirrorResizeObserver && wrapper) {
            codeMirrorResizeObserver.unobserve(wrapper);
          }
          return;
        }
        editor.refresh();
      });
    });
  }

  function cleanupCodeMirrorEditors() {
    activeCodeMirrorEditors.forEach(function (editor) {
      if (!editor || typeof editor.getWrapperElement !== "function") return;
      var wrapper = editor.getWrapperElement();
      if (!wrapper || !document.contains(wrapper)) {
        activeCodeMirrorEditors.delete(editor);
        if (codeMirrorResizeObserver && wrapper) codeMirrorResizeObserver.unobserve(wrapper);
      }
    });
  }

  function getCodeMirrorTextarea(editor) {
    if (!editor || typeof editor.getTextArea !== "function") return null;
    return editor.getTextArea();
  }

  function saveAllEditors() {
    cleanupCodeMirrorEditors();
    activeCodeMirrorEditors.forEach(function (editor) {
      if (!editor || typeof editor.save !== "function") return;
      editor.save();
    });
  }

  function initCodeMirrorEditors(root) {
    var textareas = root.querySelectorAll("textarea[data-huleedu-codemirror]");
    if (!textareas.length) return;

    ensureCodeMirrorAssets()
      .then(function () {
        textareas.forEach(function (textarea) {
          if (!document.contains(textarea)) return;
          if (textarea.dataset.huleeduCodemirrorInitialized === "true") return;
          if (!window.CodeMirror) return;

          var mode = textarea.dataset.huleeduCodemirror || "python";
          var editor = window.CodeMirror.fromTextArea(textarea, {
            lineNumbers: true,
            mode: mode,
            indentUnit: 4,
            tabSize: 4,
          });

          editor.setSize("100%", "100%");
          requestAnimationFrame(function () { editor.refresh(); });

          var explicitFormId = textarea.getAttribute("form");
          var closestForm = textarea.closest ? textarea.closest("form") : null;
          var formId = explicitFormId || (closestForm && closestForm.id ? closestForm.id : null);
          var form = formId ? document.getElementById(formId) : closestForm;
          if (form) {
            form.addEventListener("submit", function () {
              editor.save();
            });
          }

          activeCodeMirrorEditors.add(editor);
          observeCodeMirrorEditor(editor);

          textarea.dataset.huleeduCodemirrorInitialized = "true";
        });
      })
      .catch(function (err) {
        // Fail open: keep textarea usable even if assets fail.
        console.error(err);
      });
  }

  function init(root) {
    cleanupCodeMirrorEditors();
    initToasts();
    initFileInputs(root);
    initCopyButtons(root);
    initCodeMirrorEditors(root);
  }

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.body.addEventListener("htmx:load", function (evt) {
    init(evt.target || document);
  });

  document.body.addEventListener("htmx:oobBeforeSwap", function (evt) {
    if (!evt || !evt.detail) return;

    var target = evt.detail.target || evt.target;
    if (!target || target.id !== "toast-container") return;

    var toastNode = extractToastNode(evt.detail.fragment);
    if (!toastNode) return;

    // HTMX will otherwise replace the toast immediately (no fade-out). We take over the swap to
    // enforce a single toast with a small replacement animation.
    evt.detail.shouldSwap = false;
    replaceToastWithFade(toastNode);
  });

  document.body.addEventListener("htmx:afterSwap", function () {
    initToasts();
    scheduleAllEditorsRefresh();
  });

  document.body.addEventListener("htmx:afterSettle", function () {
    scheduleAllEditorsRefresh();
  });

  window.addEventListener("resize", scheduleAllEditorsRefresh);

  document.addEventListener("click", function (evt) {
    if (!evt || !evt.target) return;
    if (!evt.target.closest) return;

    var dismissButton = evt.target.closest(".huleedu-toast-dismiss");
    if (!dismissButton) return;

    var toast = dismissButton.closest ? dismissButton.closest(".huleedu-toast") : null;
    if (!toast) return;

    evt.preventDefault();
    dismissToast(toast);
  });

  // Hamburger menu toggle
  document.addEventListener("click", function (evt) {
    if (!evt || !evt.target) return;

    var btn = evt.target.closest(".huleedu-hamburger");
    if (!btn) return;

    var navId = btn.getAttribute("aria-controls");
    if (!navId) return;

    var nav = document.getElementById(navId);
    if (!nav) return;

    var expanded = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", !expanded);
    nav.hidden = expanded;
  });

  // Keep underlying <textarea> values in sync for both native submits and HTMX-boosted requests.
  document.addEventListener(
    "submit",
    function () {
      saveAllEditors();
    },
    true
  );

  document.body.addEventListener("htmx:configRequest", function (evt) {
    // HTMX captures form values before sending; ensure CodeMirror values are included.
    if (!evt || !evt.detail) return;
    if (!evt.detail.parameters) {
      saveAllEditors();
      return;
    }

    var trigger = evt.detail.elt || null;
    var form = null;
    if (trigger) {
      var tagName = trigger.tagName ? trigger.tagName.toLowerCase() : "";
      if (tagName === "form") form = trigger;
      else if (trigger.form) form = trigger.form;
      else form = trigger.closest ? trigger.closest("form") : null;
    }

    if (!form) {
      // Not a form submission (e.g. hx-get button); nothing to sync.
      return;
    }

    cleanupCodeMirrorEditors();
    activeCodeMirrorEditors.forEach(function (editor) {
      if (!editor || typeof editor.save !== "function") return;
      editor.save();

      var textarea = getCodeMirrorTextarea(editor);
      if (!textarea || !textarea.name) return;
      if (form && textarea.form && textarea.form !== form) return;

      evt.detail.parameters[textarea.name] = textarea.value;
    });
  });
})();
