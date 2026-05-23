(() => {
  const input = document.querySelector("#file");
  const preview = document.querySelector("#image-preview");
  const placeholder = document.querySelector("#preview-placeholder");
  const uploadPreview = document.querySelector(".upload-preview");
  const result = document.querySelector("#result");
  const loadingResult = document.querySelector(".loading-results");
  const analyzeForm = document.querySelector('form[hx-post="/ui/analyze"]');
  let previewUrl = null;

  function resetPreview() {
    preview.hidden = true;
    preview.removeAttribute("src");
    placeholder.hidden = false;
    uploadPreview?.classList.remove("has-preview");
  }

  function showPreview(file) {
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    placeholder.hidden = true;
    uploadPreview?.classList.add("has-preview");
  }

  function showLoadingState() {
    result?.classList.add("is-loading");
    loadingResult?.classList.add("is-active");
  }

  function hideLoadingState() {
    result?.classList.remove("is-loading");
    loadingResult?.classList.remove("is-active");
  }

  if (input && preview && placeholder) {
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];

      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      }

      if (!file || !file.type.startsWith("image/")) {
        resetPreview();
        return;
      }

      showPreview(file);
    });
  }

  if (analyzeForm) {
    analyzeForm.addEventListener("htmx:beforeRequest", showLoadingState);
    analyzeForm.addEventListener("htmx:afterRequest", hideLoadingState);
    analyzeForm.addEventListener("htmx:responseError", hideLoadingState);
    analyzeForm.addEventListener("htmx:sendError", hideLoadingState);
  }
})();
