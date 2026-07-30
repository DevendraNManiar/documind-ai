import { useEffect, useState } from "react";
import * as api from "./api.js";

function AuthPanel({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const fn = mode === "login" ? api.login : api.signup;
      const { access_token } = await fn(email, password);
      onAuthed(access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card auth" onSubmit={submit}>
      <h2>{mode === "login" ? "Log in" : "Create account"}</h2>
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password (min 8 chars)" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
      {error && <p className="error">{error}</p>}
      <button disabled={busy}>{busy ? "…" : mode === "login" ? "Log in" : "Sign up"}</button>
      <p className="muted">
        {mode === "login" ? "No account?" : "Have an account?"}{" "}
        <a onClick={() => setMode(mode === "login" ? "signup" : "login")}>
          {mode === "login" ? "Sign up" : "Log in"}
        </a>
      </p>
    </form>
  );
}

function Documents({ token }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setDocs(await api.listDocuments(token));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000); // poll ingest status
    return () => clearInterval(id);
  }, []);

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadDocument(token, file);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="card">
      <h3>Your documents</h3>
      <label className="upload">
        {uploading ? "Uploading…" : "＋ Upload PDF / TXT / MD"}
        <input type="file" accept=".pdf,.txt,.md" onChange={onUpload} hidden />
      </label>
      {error && <p className="error">{error}</p>}
      <ul className="doclist">
        {docs.length === 0 && <li className="muted">No documents yet.</li>}
        {docs.map((d) => (
          <li key={d.id}>
            <span>{d.filename}</span>
            <span className={`badge ${d.status}`}>{d.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Chat({ token }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await api.chat(token, question));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>Ask your documents</h3>
      <form onSubmit={ask} className="chatbar">
        <input placeholder="e.g. What is the approved budget?" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button disabled={busy}>{busy ? "Thinking…" : "Ask"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="answer">
          <p>{result.answer}</p>
          {result.citations?.length > 0 && (
            <div className="citations">
              <h4>Sources</h4>
              {result.citations.map((c, i) => (
                <div className="citation" key={i}>
                  <span className="cite-index">[{i + 1}]</span>
                  <span className="cite-file">{c.filename}</span>
                  <p className="cite-snippet">{c.snippet}…</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("documind_token") || "");

  function setAuth(t) {
    localStorage.setItem("documind_token", t);
    setToken(t);
  }
  function logout() {
    localStorage.removeItem("documind_token");
    setToken("");
  }

  return (
    <div className="app">
      <header>
        <h1>📄 DocuMind AI</h1>
        {token && <button className="ghost" onClick={logout}>Log out</button>}
      </header>
      {!token ? (
        <AuthPanel onAuthed={setAuth} />
      ) : (
        <main className="grid">
          <Documents token={token} />
          <Chat token={token} />
        </main>
      )}
    </div>
  );
}
