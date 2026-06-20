document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy], [data-copy-target]");
  if (!button) return;

  let text = button.dataset.copy || "";
  if (button.dataset.copyTarget) {
    const target = document.getElementById(button.dataset.copyTarget);
    text = target ? target.value : "";
  }

  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    const original = button.textContent;
    button.textContent = "コピーしました";
    window.setTimeout(() => {
      button.textContent = original;
    }, 1400);
  } catch {
    window.prompt("コピーしてください", text);
  }
});
