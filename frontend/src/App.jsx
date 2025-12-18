import { useEffect, useMemo, useState } from "react";
import "./App.css";

const SUGGESTIONS = [
  "Je veux joindre la scolarité à Paris",
  "J'ai un problème avec mon emploi du temps",
  "Comment récupérer mon certificat de scolarité ?",
  "Je n'arrive pas à me connecter à l'ENT",
];

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export default function App() {
  const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";

  const [userId, setUserId] = useState(() => {
    const key = "av_user_id";
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const v = `web-${uid()}`;
    localStorage.setItem(key, v);
    return v;
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // messages: { role: 'user'|'bot', text: string, meta?: {...} }
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem("av_messages");
    return saved ? JSON.parse(saved) : [];
  });

  const lastBot = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "bot") return messages[i];
    }
    return null;
  }, [messages]);

  useEffect(() => {
    localStorage.setItem("av_messages", JSON.stringify(messages));
  }, [messages]);

  function resetConversation() {
    setMessages([]);
    localStorage.removeItem("av_messages");
  }

  async function sendMessage(text) {
    const msg = text.trim();
    if (!msg || loading) return;

    setMessages((m) => [...m, { role: "user", text: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          message: msg,
          channel: "web",
        }),
      });

      if (!res.ok) {
        const errTxt = await res.text();
        throw new Error(`HTTP ${res.status} - ${errTxt}`);
      }

      const data = await res.json();
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: data.answer,
          meta: {
            intent: data.intent,
            confidence: data.confidence,
            entities: data.entities,
            sources: data.sources || [],
            // si plus tard tu retournes chat_event_id dans /chat, mets-le ici
            chat_event_id: data.chat_event_id,
          },
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text:
            "Erreur : impossible de contacter l’API. Vérifie que le backend tourne et que VITE_API_BASE est correct.",
          meta: { error: String(e?.message || e) },
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback({ rating, comment }) {
    // Idéal: envoyer chat_event_id. Si tu ne le retournes pas encore,
    // on ne peut pas associer proprement. Je te donne juste après le mini patch backend.
    const chatEventId = lastBot?.meta?.chat_event_id;
    if (!chatEventId) {
      alert(
        "Le backend ne renvoie pas encore chat_event_id. Ajoute-le dans /chat pour activer le feedback UI."
      );
      return;
    }

    const res = await fetch(`${apiBase}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_event_id: chatEventId,
        rating,
        comment: comment || null,
      }),
    });

    if (!res.ok) {
      const t = await res.text();
      alert(`Feedback failed: ${res.status} - ${t}`);
      return;
    }
    alert("Merci ! Feedback enregistré.");
  }

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>Assistant Virtuel Campus</h1>
          <p className="subtitle">Chat web (React) connecté à l’API FastAPI</p>
        </div>

        <div className="header-actions">
          <button className="btn" onClick={resetConversation} disabled={loading}>
            Reset
          </button>
        </div>
      </header>

      <section className="panel">
        <div className="row">
          <label className="label">User ID</label>
          <input
            className="input"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="web-xxxx"
          />
          <button
            className="btn"
            onClick={() => {
              localStorage.setItem("av_user_id", userId);
              alert("User ID sauvegardé.");
            }}
          >
            Sauver
          </button>
        </div>

        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="chip"
              onClick={() => sendMessage(s)}
              disabled={loading}
              title="Envoyer cette question"
            >
              {s}
            </button>
          ))}
        </div>
      </section>

      <main className="chat">
        {messages.length === 0 ? (
          <div className="empty">
            <p>Pose une question ou clique sur une suggestion.</p>
          </div>
        ) : (
          <div className="messages">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`bubble ${m.role === "user" ? "user" : "bot"}`}
              >
                <div className="text">{m.text}</div>

                {m.role === "bot" && m.meta && (
                  <div className="meta">
                    {m.meta.intent && (
                      <span className="tag">intent: {m.meta.intent}</span>
                    )}
                    {typeof m.meta.confidence === "number" && (
                      <span className="tag">
                        conf: {m.meta.confidence.toFixed(3)}
                      </span>
                    )}
                    {Array.isArray(m.meta.sources) && m.meta.sources.length > 0 && (
                      <div className="sources">
                        <div className="sources-title">Sources</div>
                        <ul>
                          {m.meta.sources.map((s, i) => (
                            <li key={i}>
                              <strong>{s.type}</strong> — {s.title} (id: {s.id})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="composer">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="composer-form"
        >
          <input
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Écris ta question…"
            disabled={loading}
          />
          <button className="btn primary" disabled={loading}>
            {loading ? "Envoi…" : "Envoyer"}
          </button>
        </form>

        <div className="feedback">
          <div className="feedback-title">Feedback (sur la dernière réponse)</div>
          <div className="feedback-row">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                className="btn"
                onClick={() => sendFeedback({ rating: n })}
                disabled={loading}
                type="button"
              >
                {n}
              </button>
            ))}
          </div>
          <small className="hint">
            Pour activer le feedback, le backend doit renvoyer <code>chat_event_id</code> dans <code>/chat</code>.
          </small>
        </div>
      </footer>
    </div>
  );
}
console.log("API BASE =", import.meta.env.VITE_API_BASE);
