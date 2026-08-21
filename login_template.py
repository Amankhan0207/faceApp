def get_login_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FaceSort - Login / Register</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
:root {
  --ink: #101318;
  --panel: #171b22;
  --raise: #1e232c;
  --line: #2a303b;
  --text: #e6e9ee;
  --dim: #7d8695;
  --faint: #545c6a;
  --amber: #f5a524;
  --red: #e5484d;
  --green: #3fbf7f;
  --radius: 8px;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--sans);
  background: radial-gradient(circle at center, rgba(16, 19, 24, 0.45) 0%, rgba(16, 19, 24, 0.92) 100%), url("/static/login_bg.jpg") no-repeat center center fixed;
  background-size: cover;
  color: var(--text);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
  position: relative;
}

.login-container {
  width: 100%;
  max-width: 420px;
  background: rgba(23, 27, 34, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 36px 30px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
  transform: translateY(20px);
}

.brand {
  text-align: center;
  margin-bottom: 26px;
}
.brand h1 {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}
.brand h1 span {
  color: var(--amber);
}
.brand p {
  font-size: 13px;
  color: var(--dim);
}

.form-group {
  margin-bottom: 20px;
}
.form-group label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--dim);
  margin-bottom: 8px;
}
.form-group input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(16, 19, 24, 0.7);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.form-group input:focus {
  outline: none;
  border-color: var(--amber);
  box-shadow: 0 0 0 3px rgba(245, 165, 36, 0.15);
}

.btn {
  width: 100%;
  padding: 12px;
  background: var(--amber);
  border: none;
  border-radius: var(--radius);
  color: #1a1204;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}
.btn:hover {
  background: #ffb838;
}
.btn:active {
  transform: scale(0.98);
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #1a1204;
  border-bottom-color: transparent;
  border-radius: 50%;
  animation: rotation 0.8s linear infinite;
  display: none;
}

.error-note {
  background: rgba(229, 72, 77, 0.1);
  border: 1px solid rgba(229, 72, 77, 0.3);
  color: #f5a3a5;
  padding: 10px 12px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-bottom: 20px;
  display: none;
  animation: fadeIn 0.3s ease;
}

.success-note {
  background: rgba(63, 191, 127, 0.1);
  border: 1px solid rgba(63, 191, 127, 0.35);
  color: #8fdcb4;
  padding: 10px 12px;
  border-radius: var(--radius);
  font-size: 13px;
  margin-bottom: 20px;
  display: none;
  animation: fadeIn 0.3s ease;
}

.toggle-mode {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: var(--dim);
}
.toggle-mode a {
  color: var(--amber);
  text-decoration: none;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.15s;
}
.toggle-mode a:hover {
  color: #ffb838;
  text-decoration: underline;
}

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes rotation {
  to { transform: rotate(360deg); }
}
</style>
</head>
<body>

<div class="login-container">
  <div class="brand">
    <h1>Face<span>Sort</span></h1>
    <p id="brandText">Sign in to manage your workspace</p>
  </div>
  
  <div class="error-note" id="errorBlock"></div>
  <div class="success-note" id="successBlock"></div>
  
  <form id="authForm">
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" required autocomplete="username" autofocus>
    </div>
    
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" required autocomplete="current-password">
    </div>

    <!-- Registration Fields -->

    <div class="form-group register-only" style="display: none;">
      <label for="email">Email</label>
      <input type="email" id="email" autocomplete="email">
    </div>

    <div class="form-group register-only" style="display: none;">
      <label for="mobile">Mobile No</label>
      <input type="text" id="mobile" autocomplete="tel">
    </div>

    <!-- OTP Field -->
    <div class="form-group otp-only" style="display: none;">
      <label for="otp" style="color: var(--amber);">Enter OTP Verification Code</label>
      <input type="text" id="otp" placeholder="Enter 6-digit code..." style="border-color: var(--amber);">
    </div>

    <!-- CAPTCHA Field -->
    <div class="form-group" style="margin-top: 15px;">
      <label for="captchaInput">Security Verification</label>
      <div style="display: flex; gap: 10px; align-items: center;">
        <img id="captchaImage" src="/api/auth/captcha" alt="CAPTCHA" style="border-radius: 6px; height: 42px; width: 120px; cursor: pointer; border: 1px solid var(--line);" title="Click to refresh CAPTCHA">
        <input type="text" id="captchaInput" required placeholder="Enter code..." autocomplete="off" style="flex: 1; padding: 10px; border-radius: 6px; background: var(--ink); border: 1px solid var(--line); color: var(--text); font-family: monospace; font-size: 16px; letter-spacing: 2px; text-transform: uppercase;">
      </div>
      <div style="font-size: 11px; color: var(--dim); margin-top: 4px;">Click image to generate new code.</div>
    </div>
    
    <button type="submit" class="btn" id="submitBtn">
      <span class="spinner" id="spinner"></span>
      <span id="btnText">Sign In</span>
    </button>
  </form>
  
  <div class="toggle-mode">
    <span id="toggleText">Don't have an account? </span><a id="toggleBtn">Create one</a>
  </div>

  <!-- Google Auth Button Container -->
  <div id="googleAuthSection" style="display: none; margin-top: 15px; border-top: 1px solid var(--line); padding-top: 20px;">
    <div id="g_id_onload"
         data-client_id="{{GOOGLE_CLIENT_ID}}"
         data-context="signin"
         data-ux_mode="popup"
         data-callback="handleCredentialResponse"
         data-auto_prompt="false">
    </div>
    <div class="g_id_signin"
         data-type="standard"
         data-shape="rectangular"
         data-theme="dark"
         data-text="signin_with"
         data-size="large"
         data-logo_alignment="left"
         style="width: 100%; display: flex; justify-content: center;">
    </div>
  </div>
</div>

<script>
const form = document.getElementById("authForm");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const spinner = document.getElementById("spinner");
const errorBlock = document.getElementById("errorBlock");
const successBlock = document.getElementById("successBlock");
const brandText = document.getElementById("brandText");
const toggleText = document.getElementById("toggleText");
const toggleBtn = document.getElementById("toggleBtn");
const registerFields = document.querySelectorAll(".register-only");
const googleAuthSection = document.getElementById("googleAuthSection");
const otpOnlyField = document.querySelector(".otp-only");
const otpInput = document.getElementById("otp");

let isLoginMode = true;
let otpSent = false;
const captchaImage = document.getElementById("captchaImage");
const captchaInput = document.getElementById("captchaInput");

function refreshCaptcha() {
  captchaInput.value = "";
  captchaImage.src = "/api/auth/captcha?t=" + Date.now();
}

captchaImage.addEventListener("click", refreshCaptcha);
const isSmtpConfigured = {{IS_SMTP_CONFIGURED}};

// Show Google sign-in if client ID is configured
const gClientId = "{{GOOGLE_CLIENT_ID}}";
if (gClientId && gClientId.trim() !== "" && gClientId.indexOf("{{") === -1) {
  googleAuthSection.style.display = "block";
}

function setMode(loginMode) {
  isLoginMode = loginMode;
  otpSent = false;
  
  // Clear any existing alerts
  errorBlock.style.display = "none";
  if (!isLoginMode) {
    successBlock.style.display = "none";
    googleAuthSection.style.display = "none"; // Hide Google button in Register mode
  } else {
    // Show Google button in Login mode if configured
    if (gClientId && gClientId.trim() !== "" && gClientId.indexOf("{{") === -1) {
      googleAuthSection.style.display = "block";
    }
  }
  
  // Hide OTP field
  otpOnlyField.style.display = "none";
  otpInput.required = false;
  otpInput.value = "";
  
  // Show or hide register-only fields
  registerFields.forEach(field => {
    field.style.display = isLoginMode ? "none" : "block";
    const input = field.querySelector("input");
    if (input) {
      input.required = !isLoginMode;
    }
  });
  
  if (isLoginMode) {
    brandText.textContent = "Sign in to manage your workspace";
    btnText.textContent = "Sign In";
    toggleText.textContent = "Don't have an account? ";
    toggleBtn.textContent = "Create one";
  } else {
    brandText.textContent = "Create a new account to get started";
    btnText.textContent = "Send OTP";
    toggleText.textContent = "Already have an account? ";
    toggleBtn.textContent = "Sign in";
  }
  
  document.getElementById("username").focus();
  refreshCaptcha();
}

toggleBtn.addEventListener("click", () => {
  setMode(!isLoginMode);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  errorBlock.style.display = "none";
  successBlock.style.display = "none";
  
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  
  if (isLoginMode) {
    // Login flow
    submitBtn.disabled = true;
    spinner.style.display = "block";
    btnText.textContent = "Signing In...";
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, captcha: captchaInput.value })
      });
      if (res.ok) {
        window.location.reload();
      } else {
        let detail = "Invalid username or password";
        try { detail = (await res.json()).detail || detail; } catch(e) {}
        throw new Error(detail);
      }
    } catch (err) {
      errorBlock.textContent = err.message;
      errorBlock.style.display = "block";
      submitBtn.disabled = false;
      spinner.style.display = "none";
      btnText.textContent = "Sign In";
      refreshCaptcha();
    }
  } else {
    // Register flow
    const email = document.getElementById("email").value;
    const mobile = document.getElementById("mobile").value;
    
    // Password strength check
    const hasUpper = /[A-Z]/.test(password);
    const hasDigit = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    if (password.length < 8 || !hasUpper || !hasDigit || !hasSpecial) {
      errorBlock.textContent = "Password must be at least 8 characters long and contain at least one capital letter (A-Z), one number (0-9), and one special character (e.g. @, #, $, %).";
      errorBlock.style.display = "block";
      return;
    }
    
    if (!otpSent) {
      // Step 1: Send OTP
      submitBtn.disabled = true;
      spinner.style.display = "block";
      btnText.textContent = "Sending OTP...";
      try {
        const res = await fetch("/api/register/send-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email })
        });
        if (res.ok) {
          otpSent = true;
          if (isSmtpConfigured) {
            successBlock.textContent = "Verification code sent to your email. Check your inbox!";
          } else {
            successBlock.innerHTML = "Verification code generated! <br><span style='color:var(--amber); font-weight:600;'>Check your server console terminal</span> to copy the OTP.";
          }
          successBlock.style.display = "block";
          otpOnlyField.style.display = "block";
          otpInput.required = true;
          otpInput.focus();
          btnText.textContent = "Verify & Register";
        } else {
          let detail = "Failed to send OTP";
          try { detail = (await res.json()).detail || detail; } catch(e) {}
          throw new Error(detail);
        }
      } catch (err) {
        errorBlock.textContent = err.message;
        errorBlock.style.display = "block";
      } finally {
        submitBtn.disabled = false;
        spinner.style.display = "none";
      }
    } else {
      // Step 2: Verify & Register
      const otp = otpInput.value;
      submitBtn.disabled = true;
      spinner.style.display = "block";
      btnText.textContent = "Verifying...";
      try {
        const res = await fetch("/api/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, name: "", email, mobile, otp, captcha: captchaInput.value })
        });
        if (res.ok) {
          // Success!
          successBlock.textContent = "Account created successfully! You can now sign in.";
          successBlock.style.display = "block";
          
          // Clear inputs
          document.getElementById("password").value = "";
          document.getElementById("email").value = "";
          document.getElementById("mobile").value = "";
          otpInput.value = "";
          
          setMode(true);
        } else {
          let detail = "Registration failed";
          try { detail = (await res.json()).detail || detail; } catch(e) {}
          throw new Error(detail);
        }
      } catch (err) {
        errorBlock.textContent = err.message;
        errorBlock.style.display = "block";
        refreshCaptcha();
      } finally {
        submitBtn.disabled = false;
        spinner.style.display = "none";
        btnText.textContent = "Verify & Register";
      }
    }
  }
});

async function handleCredentialResponse(response) {
  submitBtn.disabled = true;
  spinner.style.display = "block";
  btnText.textContent = "Signing In...";
  errorBlock.style.display = "none";
  successBlock.style.display = "none";
  
  try {
    const res = await fetch("/api/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: response.credential })
    });
    if (res.ok) {
      window.location.reload();
    } else {
      let detail = "Google authentication failed";
      try { detail = (await res.json()).detail || detail; } catch(e) {}
      throw new Error(detail);
    }
  } catch (err) {
    errorBlock.textContent = err.message;
    errorBlock.style.display = "block";
    submitBtn.disabled = false;
    spinner.style.display = "none";
    btnText.textContent = isLoginMode ? "Sign In" : "Register";
  }
}
window.handleCredentialResponse = handleCredentialResponse;
</script>
</body>
</html>
"""
