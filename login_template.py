def get_login_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FaceSort - Login / Register</title>
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
  background: var(--ink);
  color: var(--text);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: hidden;
  position: relative;
}

/* Background animated glow */
body::before {
  content: "";
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245,165,36,0.15) 0%, rgba(245,165,36,0) 70%);
  top: -50px;
  right: -50px;
  z-index: -1;
  animation: float glow1 10s infinite alternate;
}
body::after {
  content: "";
  position: absolute;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245,165,36,0.1) 0%, rgba(245,165,36,0) 70%);
  bottom: -100px;
  left: -100px;
  z-index: -1;
}

.login-container {
  width: 100%;
  max-width: 400px;
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
    
    <button type="submit" class="btn" id="submitBtn">
      <span class="spinner" id="spinner"></span>
      <span id="btnText">Sign In</span>
    </button>
  </form>
  
  <div class="toggle-mode">
    <span id="toggleText">Don't have an account? </span><a id="toggleBtn">Create one</a>
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

let isLoginMode = true;

function setMode(loginMode) {
  isLoginMode = loginMode;
  
  // Clear any existing alerts
  errorBlock.style.display = "none";
  if (!isLoginMode) {
    successBlock.style.display = "none";
  }
  
  if (isLoginMode) {
    brandText.textContent = "Sign in to manage your workspace";
    btnText.textContent = "Sign In";
    toggleText.textContent = "Don't have an account? ";
    toggleBtn.textContent = "Create one";
  } else {
    brandText.textContent = "Create a new account to get started";
    btnText.textContent = "Register";
    toggleText.textContent = "Already have an account? ";
    toggleBtn.textContent = "Sign in";
  }
  
  document.getElementById("username").focus();
}

toggleBtn.addEventListener("click", () => {
  setMode(!isLoginMode);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  // Reset alerts & submit button state
  errorBlock.style.display = "none";
  successBlock.style.display = "none";
  submitBtn.disabled = true;
  spinner.style.display = "block";
  btnText.textContent = isLoginMode ? "Signing In..." : "Creating Account...";
  
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  
  const endpoint = isLoginMode ? "/api/login" : "/api/register";
  
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    
    if (res.ok) {
      if (isLoginMode) {
        window.location.reload();
      } else {
        // Registration success
        successBlock.textContent = "Account created successfully! You can now sign in.";
        successBlock.style.display = "block";
        
        // Reset form password
        document.getElementById("password").value = "";
        
        // Go back to login mode automatically
        setMode(true);
        
        submitBtn.disabled = false;
        spinner.style.display = "none";
      }
    } else {
      let detail = isLoginMode ? "Invalid username or password" : "Failed to create account";
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch(e) {}
      throw new Error(detail);
    }
  } catch (err) {
    errorBlock.textContent = err.message;
    errorBlock.style.display = "block";
    submitBtn.disabled = false;
    spinner.style.display = "none";
    btnText.textContent = isLoginMode ? "Sign In" : "Register";
  }
});
</script>
</body>
</html>
"""
