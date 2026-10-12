document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("transactionSearch");
  const table = document.getElementById("transactionsTable");
  if (search && table) {
    search.addEventListener("input", () => {
      const term = search.value.toLowerCase().trim();
      table.querySelectorAll("tbody tr").forEach(row => {
        row.hidden = !row.innerText.toLowerCase().includes(term);
      });
    });
  }
  document.querySelectorAll(".delete-form").forEach(form => {
    form.addEventListener("submit", event => {
      if (!confirm("Are you sure you want to delete this transaction?")) {
        event.preventDefault();
      }
    });
  });
});