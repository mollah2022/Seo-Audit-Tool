/**
 * Small, dependency-free progressive enhancements:
 *  - a loading state on the scan form (the audit runs synchronously
 *    server-side and can take several seconds, so give clear feedback)
 *  - respects prefers-reduced-motion throughout
 */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("scan-form");
    if (!form) return;

    const button = form.querySelector(".btn-scan");
    const label = form.querySelector(".btn-scan-label");
    const inputWrap = form.querySelector(".scan-input-wrap");

    form.addEventListener("submit", () => {
        if (!button) return;
        // Guard against double-submit while the audit is running.
        if (button.classList.contains("is-loading")) return;

        button.classList.add("is-loading");
        button.disabled = true;
        if (label) label.textContent = "Scanning\u2026";
        if (inputWrap) inputWrap.classList.add("is-loading");
    });
});

/**
 * Results page category tabs: clicking a channel (On-Page, Technical,
 * Social, Links, Performance) swaps which panel of checks is visible,
 * instead of showing every check stacked in one long page.
 */
document.addEventListener("DOMContentLoaded", () => {
    const tabs = Array.from(document.querySelectorAll(".report-tab"));
    if (!tabs.length) return;

    const panels = Array.from(document.querySelectorAll(".report-channel"));

    const activate = (tab, opts) => {
        const focusTab = opts && opts.focus;

        tabs.forEach((t) => t.setAttribute("aria-selected", t === tab ? "true" : "false"));

        panels.forEach((panel) => {
            const isMatch = panel.id === tab.dataset.target;
            panel.hidden = !isMatch;
            if (isMatch) {
                panel.classList.remove("panel-enter");
                // Re-trigger the fade-in each time a panel is shown.
                // eslint-disable-next-line no-unused-expressions
                panel.offsetHeight;
                panel.classList.add("panel-enter");
            }
        });

        if (focusTab) tab.focus();

        if (history.replaceState) {
            history.replaceState(null, "", `#${tab.dataset.target}`);
        }
    };

    tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab));

        tab.addEventListener("keydown", (event) => {
            if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
            event.preventDefault();
            const direction = event.key === "ArrowRight" ? 1 : -1;
            const next = tabs[(index + direction + tabs.length) % tabs.length];
            activate(next, { focus: true });
        });
    });

    const initialTab =
        tabs.find((t) => `#${t.dataset.target}` === window.location.hash) || tabs[0];
    activate(initialTab);
});
