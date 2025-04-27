document.addEventListener("DOMContentLoaded", function () {
    let forgotPasswordForm = document.getElementById("forgot-password-form");
    let resetPasswordForm = document.getElementById("reset-password-form");

    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener("submit", function (event) {
            event.preventDefault();
            checkEmail();
        });
    }

    if (resetPasswordForm) {
        resetPasswordForm.addEventListener("submit", function (event) {
            event.preventDefault();
            resetPassword();
        });
    }
});

function showMessage(type, message) {
    let messageBox = document.getElementById("message-box");
    messageBox.style.display = "block";

    if (type === "success") {
        messageBox.style.color = "green";
        messageBox.style.backgroundColor = "#e6ffe6";
        messageBox.style.border = "1px solid #4CAF50";
    } else {
        messageBox.style.color = "red";
        messageBox.style.backgroundColor = "#ffe6e6";
        messageBox.style.border = "1px solid #ff4d4d";
    }

    messageBox.textContent = message;
}

function checkEmail() {
    let email = document.getElementById("email").value;

    fetch("/check-email", {   
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            showMessage("success", "Email found! Proceeding to reset password...");
            sessionStorage.setItem("resetEmail", email);
            setTimeout(() => {
                window.location.href = "/resetpass";  
            }, 2000);
        } else {
            showMessage("error", "Email not found!");
        }
    })
    .catch(error => {
        showMessage("error", "An error occurred! Please try again later.");
        console.error("Error:", error);
    });
}

function resetPassword() {
    let email = sessionStorage.getItem("resetEmail");
    let newPassword = document.getElementById("new-password").value;
    let confirmPassword = document.getElementById("confirm-password").value;

    if (!email) {
        showMessage("error", "Session expired. Please start the process again.");
        setTimeout(() => {
            window.location.href = "/forgotpass";  
        }, 2000);
        return;
    }

    if (newPassword !== confirmPassword) {
        showMessage("error", "Passwords do not match!");
        return;
    }

    fetch("/reset-password", {   
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, new_password: newPassword })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            showMessage("success", "Password reset successful! Redirecting to login...");
            setTimeout(() => {
                window.location.href = "/login";  
            }, 2000);
        } else {
            showMessage("error", "Something went wrong! Please try again.");
        }
    })
    .catch(error => {
        showMessage("error", "An error occurred! Please try again later.");
        console.error("Error:", error);
    });
}
