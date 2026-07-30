const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function signup(email, password) {
  const res = await fetch(`${BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handle(res); // { access_token }
}

export async function login(email, password) {
  // FastAPI OAuth2PasswordRequestForm expects form-encoded username/password.
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  return handle(res); // { access_token }
}

export async function uploadDocument(token, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents`, {
    method: "POST",
    headers: authHeader(token),
    body: form,
  });
  return handle(res);
}

export async function listDocuments(token) {
  const res = await fetch(`${BASE}/documents`, { headers: authHeader(token) });
  return handle(res);
}

export async function chat(token, question, documentId = null) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ question, document_id: documentId }),
  });
  return handle(res); // { answer, citations }
}
