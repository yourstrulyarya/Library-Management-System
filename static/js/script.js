// script.js — small progressive-enhancement touches. The app works fully
// without JS (every action is a real form submission); this adds the
// theme switcher, the collapsible sidebar, and a couple of UX niceties.

function toggleTheme() {
  var current = document.documentElement.getAttribute('data-theme') || 'dark';
  var next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('lms-theme', next); } catch (e) {}
  updateThemeIcon();
}

function toggleSidebar() {
  var hidden = document.documentElement.getAttribute('data-sidebar') === 'hidden';
  if (hidden) {
    document.documentElement.removeAttribute('data-sidebar');
    try { localStorage.setItem('lms-sidebar-hidden', 'false'); } catch (e) {}
  } else {
    document.documentElement.setAttribute('data-sidebar', 'hidden');
    try { localStorage.setItem('lms-sidebar-hidden', 'true'); } catch (e) {}
  }
}

function updateThemeIcon() {
  var theme = document.documentElement.getAttribute('data-theme') || 'dark';
  var icon = theme === 'dark' ? '\u263E' : '\u2600'; // moon / sun
  document.querySelectorAll('#theme-toggle-icon').forEach(function (el) {
    el.textContent = icon;
  });
}

document.addEventListener("DOMContentLoaded", () => {
  updateThemeIcon();

  // Auto-dismiss flash messages after a few seconds.
  document.querySelectorAll(".flash").forEach((el, i) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 450);
    }, 5000 + i * 300);
  });

  // For <input list="..."> fields used as "search-then-pick-an-ID" combo
  // boxes: if what the user typed exactly matches a visible option's label,
  // swap the input's value for that option's actual value (the ID) on blur,
  // so librarians can type a title/name instead of memorizing IDs.
  document.querySelectorAll("input[list]").forEach((input) => {
    const listId = input.getAttribute("list");
    const datalist = document.getElementById(listId);
    if (!datalist) return;

    input.addEventListener("change", () => {
      const typed = input.value.trim();
      const options = Array.from(datalist.options);
      const exact = options.find((o) => o.value === typed);
      if (exact) return; // already a valid ID

      const byLabel = options.find(
        (o) => o.textContent.trim().toLowerCase() === typed.toLowerCase()
      );
      if (byLabel) {
        input.value = byLabel.value;
      }
    });
  });
});
