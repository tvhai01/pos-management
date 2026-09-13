/**
 * Auto-format price fields (thousand separators) and suggest selling price
 * from cost price (+20%) in Django admin Product form.
 */
(function () {
  function formatNumber(value) {
    var digits = String(value).replace(/\D/g, "");
    if (!digits) return "";
    return Number(digits).toLocaleString("en-US");
  }

  function attachCurrencyInput(input) {
    if (!input || input.dataset.currencyBound === "1") return;
    input.dataset.currencyBound = "1";

    if (input.value) {
      input.value = formatNumber(input.value);
    }

    input.addEventListener("input", function () {
      var cursorPosition = this.selectionStart;
      var originalLength = this.value.length;
      var cleanValue = this.value.replace(/\D/g, "");

      if (!cleanValue) {
        this.value = "";
        return;
      }

      var formatted = formatNumber(cleanValue);
      this.value = formatted;

      var newLength = formatted.length;
      cursorPosition = cursorPosition + (newLength - originalLength);
      if (cursorPosition < 0) cursorPosition = 0;
      this.setSelectionRange(cursorPosition, cursorPosition);

      // When cost_price changes, auto-suggest selling_price = cost * 1.2
      if (this.name === "cost_price") {
        var sellingInput = document.getElementById("id_selling_price");
        if (sellingInput) {
          var suggested = Math.ceil(Number(cleanValue) * 1.2);
          sellingInput.value = formatNumber(suggested);
        }
      }
    });
  }

  function init() {
    attachCurrencyInput(document.getElementById("id_cost_price"));
    attachCurrencyInput(document.getElementById("id_selling_price"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
