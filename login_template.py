def get_login_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FaceSort - Login</title>
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
  margin-bottom: 30px;
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
    <p>Sign in to manage your workspace</p>
  </div>
  
  <div class="error-note" id="errorBlock"></div>
  
  <form id="loginForm">
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
</div>

<script>
const form = document.getElementById("loginForm");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const spinner = document.getElementById("spinner");
const errorBlock = document.getElementById("errorBlock");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  // Reset state
  errorBlock.style.display = "none";
  submitBtn.disabled = true;
  spinner.style.display = "block";
  btnText.textContent = "Signing In...";
  
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    
    if (res.ok) {
      window.location.reload();
    } else {
      let detail = "Invalid username or password";
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
    btnText.textContent = "Sign In";
  }
});
</script>
</body>
</html>
"""
