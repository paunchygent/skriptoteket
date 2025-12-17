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

  function initToasts() {
    document.querySelectorAll("[data-auto-dismiss]").forEach(function (toast) {
      if (toast.dataset.dismissScheduled) return;
      toast.dataset.dismissScheduled = "true";

      var delay = parseInt(toast.dataset.autoDismiss, 10) || 5000;
      setTimeout(function () {
        if (!document.contains(toast)) return;
        toast.classList.add("huleedu-toast-dismiss-out");
        setTimeout(function () {
          if (document.contains(toast)) toast.remove();
        }, 300);
      }, delay);
    });
  }

  function ensureToastObserver() {
    var container = document.getElementById("toast-container");
    if (!container) return;
    if (container.dataset.huleeduToastObserverInitialized === "true") return;
    container.dataset.huleeduToastObserverInitialized = "true";

    if (!window.MutationObserver) return;
    var observer = new MutationObserver(function () {
      initToasts();
    });
    observer.observe(container, { childList: true });
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
    ensureToastObserver();
    initToasts();
    initFileInputs(root);
    initCodeMirrorEditors(root);
  }

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  document.body.addEventListener("htmx:load", function (evt) {
    init(evt.target || document);
  });

  document.body.addEventListener("htmx:afterSwap", function () {
    initToasts();
    scheduleAllEditorsRefresh();
  });

  document.body.addEventListener("htmx:oobAfterSwap", function () {
    initToasts();
  });

  document.body.addEventListener("htmx:afterSettle", function () {
    scheduleAllEditorsRefresh();
  });

  window.addEventListener("resize", scheduleAllEditorsRefresh);

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
