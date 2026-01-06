// ===============================
// Organization Voting Portal JS
// ===============================

// Prevent double form submission
document.addEventListener("DOMContentLoaded", () => {
    const forms = document.querySelectorAll("form");

    forms.forEach(form => {
        form.addEventListener("submit", () => {
            const btn = form.querySelector("button");
            if (btn) {
                btn.disabled = true;
                btn.innerText = "Processing...";
            }
        });
    });
});

// Optional: confirm vote submission
const voteForm = document.querySelector("form");
if (voteForm && window.location.pathname.includes("/vote")) {
    voteForm.addEventListener("submit", function (e) {
        const confirmed = confirm(
            "Are you sure you want to cast your vote? This action cannot be undone."
        );
        if (!confirmed) {
            e.preventDefault();
            const btn = voteForm.querySelector("button");
            if (btn) {
                btn.disabled = false;
                btn.innerText = "Confirm & Cast Vote";
            }
        }
    });
}

console.log("Organization Voting Portal – Static JS Loaded");