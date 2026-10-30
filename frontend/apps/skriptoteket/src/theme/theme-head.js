/**
 * Purpose:
 *     Apply the stored HuleEdu theme before first paint.
 *
 * Relationships:
 *     - Shipped as theme-head.js and inlined verbatim in theme-sample.html.
 *     - themePreference.ts writes the huleedu_theme cookie this script reads.
 */
(function () {
  "use strict";
  var cookieName = "huleedu_theme";
  var value = "system";
  var cookies = document.cookie ? document.cookie.split(";") : [];
  for (var index = 0; index < cookies.length; index += 1) {
    var cookie = cookies[index].trim();
    if (cookie.indexOf(cookieName + "=") === 0) {
      value = cookie.slice(cookieName.length + 1);
      break;
    }
  }
  if (
    value !== "light" &&
    value !== "dark" &&
    value !== "midnight" &&
    value !== "system"
  ) {
    value = "system";
  }
  document.documentElement.dataset.theme = value;
})();
