/**
 * Schools dashboard modal interactions.
 * Uses HTMLDialogElement APIs to open/close forms.
 */
(function () {
  function init() {
    var triggers = document.querySelectorAll("[data-modal-target]");
    triggers.forEach(function (trigger) {
      trigger.addEventListener("click", function (evt) {
        evt.preventDefault();
        var targetId = trigger.getAttribute("data-modal-target");
        if (!targetId) return;
        var dialog = document.getElementById(targetId);
        if (dialog && typeof dialog.showModal === "function") {
          dialog.showModal();
        }
      });
    });

    var closers = document.querySelectorAll("dialog [data-modal-close]");
    closers.forEach(function (closeBtn) {
      closeBtn.addEventListener("click", function (evt) {
        evt.preventDefault();
        var dialog = closeBtn.closest("dialog");
        if (dialog) {
          dialog.close();
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
