import { useMemo, useState } from "react";
import "./App.css";


const API_URL = "http://127.0.0.1:8000/chat";


const demoSessions = [
  {
    id: "SESSION_01",
    label: "Avery Example",
  },
  {
    id: "SESSION_02",
    label: "Jordan Sample",
  },
  {
    id: "SESSION_03",
    label: "Morgan Fiction",
  },
  {
    id: "SESSION_04",
    label: "Riley Demo",
  },
  {
    id: "SESSION_05",
    label: "Casey Test",
  },
  {
    id: "SESSION_06",
    label: "Taylor Example",
  },
  {
    id: "SESSION_07",
    label: "Skyler Sample",
  },
  {
    id: "SESSION_08",
    label: "Quinn Fiction",
  },
  {
    id: "SESSION_09",
    label: "Cameron Demo",
  },
  {
    id: "SESSION_10",
    label: "Reese Test",
  },
];


function App() {
  const [sessionId, setSessionId] =
    useState("SESSION_01");

  const [message, setMessage] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [messages, setMessages] =
    useState([
      {
        role: "assistant",
        text:
          "Hi, I’m TT&T AI Support. I can help with billing, outages, " +
          "account policies, number porting, lost devices, and support tickets.",
        route: "system",
        agent: "support_agent",
        sources: [],
      },
    ]);


  const selectedSession = useMemo(
    () =>
      demoSessions.find(
        (session) =>
          session.id === sessionId
      ),
    [sessionId]
  );


  async function sendMessage() {
    const trimmed = message.trim();

    if (!trimmed || loading) {
      return;
    }

    const requestId =
      typeof crypto !== "undefined" &&
      crypto.randomUUID
        ? crypto.randomUUID()
        : `REQ_${Date.now()}`;

    const userMessage = {
      role: "user",
      text: trimmed,
      sources: [],
    };

    setMessages(
      (previous) => [
        ...previous,
        userMessage,
      ]
    );

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(
        API_URL,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            session_id: sessionId,
            message: trimmed,
            request_id: requestId,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "The TT&T support service returned an error."
        );
      }

      setMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text: data.answer,
            route: data.route,
            agent: data.agent,
            sources:
              data.sources || [],
          },
        ]
      );
    } catch (error) {
      setMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text:
              error.message ||
              "Unable to connect to the TT&T support service.",
            route: "error",
            agent: "system",
            sources: [],
          },
        ]
      );
    } finally {
      setLoading(false);
    }
  }


  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  }


  function clearChat() {
    setMessages([
      {
        role: "assistant",
        text:
          "Chat cleared. How can I help you with your TT&T service?",
        route: "system",
        agent: "support_agent",
        sources: [],
      },
    ]);
  }


  return (
    <div className="app-shell">

      {/* ================================================= */}
      {/* SIDEBAR */}
      {/* ================================================= */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            T
          </div>

          <div>
            <h1>TT&T AI</h1>

            <p>
              Customer Support
            </p>
          </div>

        </div>


        <div className="sidebar-section">

          <label htmlFor="session">
            Demo customer
          </label>

          <select
            id="session"
            value={sessionId}
            onChange={
              (event) =>
                setSessionId(
                  event.target.value
                )
            }
          >
            {demoSessions.map(
              (session) => (
                <option
                  key={session.id}
                  value={session.id}
                >
                  {session.label}
                </option>
              )
            )}
          </select>


          <div className="session-card">

            <span className="session-status" />

            <div>

              <strong>
                {
                  selectedSession?.label
                }
              </strong>

              <small>
                {sessionId}
              </small>

            </div>

          </div>

        </div>


        <div className="sidebar-section">

          <p className="section-title">
            Capabilities
          </p>

          <div className="capability-list">

            <span>
              Billing explanations
            </span>

            <span>
              Network outages
            </span>

            <span>
              Policies & FAQs
            </span>

            <span>
              Lost device support
            </span>

            <span>
              Support tickets
            </span>

          </div>

        </div>


        <div className="architecture-card">

          <span>CrewAI</span>
          <span>MCP</span>
          <span>RAG</span>
          <span>PostgreSQL</span>

        </div>


        <button
          className="clear-button"
          onClick={clearChat}
        >
          Clear conversation
        </button>

      </aside>


      {/* ================================================= */}
      {/* MAIN */}
      {/* ================================================= */}

      <main className="main-panel">

        <header className="topbar">

          <div>

            <h2>
              AI Support Assistant
            </h2>

            <p>
              Grounded telecom support
              with secure agent actions
            </p>

          </div>


          <div className="online-pill">

            <span />

            System online

          </div>

        </header>


        {/* ================================================= */}
        {/* CHAT */}
        {/* ================================================= */}

        <section className="chat-area">

          <div className="messages">

            {messages.map(
              (item, index) => (

                <div
                  key={`${item.role}-${index}`}
                  className={
                    `message-row ${
                      item.role === "user"
                        ? "message-row-user"
                        : ""
                    }`
                  }
                >

                  {item.role ===
                    "assistant" && (

                    <div className="avatar">
                      AI
                    </div>

                  )}


                  <div
                    className={
                      `message ${
                        item.role === "user"
                          ? "message-user"
                          : "message-assistant"
                      }`
                    }
                  >

                    <div className="message-text">
                      {item.text}
                    </div>


                    {/* ================================= */}
                    {/* ROUTE / AGENT */}
                    {/* ================================= */}

                    {item.role ===
                      "assistant" &&
                      item.route &&
                      item.route !==
                        "system" && (

                      <div className="message-meta">

                        <span>
                          {item.route}
                        </span>

                        <span>
                          {item.agent}
                        </span>

                      </div>

                    )}


                    {/* ================================= */}
                    {/* SOURCES */}
                    {/* ================================= */}

                    {item.role ===
                      "assistant" &&
                      item.sources &&
                      item.sources.length >
                        0 && (

                      <div className="source-list">

                        <span className="source-label">
                          Sources
                        </span>

                        {item.sources.map(
                          (source) => (

                            <span
                              key={source}
                              className="source-chip"
                            >
                              {source}
                            </span>

                          )
                        )}

                      </div>

                    )}

                  </div>

                </div>

              )
            )}


            {/* ======================================= */}
            {/* LOADING */}
            {/* ======================================= */}

            {loading && (

              <div className="message-row">

                <div className="avatar">
                  AI
                </div>

                <div className="message message-assistant">

                  <div className="typing">

                    <span />
                    <span />
                    <span />

                  </div>

                </div>

              </div>

            )}

          </div>

        </section>


        {/* ================================================= */}
        {/* COMPOSER */}
        {/* ================================================= */}

        <section className="composer-wrap">

          <div className="suggestions">

            <button
              onClick={
                () =>
                  setMessage(
                    "Why is my current bill higher than my previous bill?"
                  )
              }
            >
              Explain my bill
            </button>


            <button
              onClick={
                () =>
                  setMessage(
                    "My service is down. Is there an outage in my area?"
                  )
              }
            >
              Check outage
            </button>


            <button
              onClick={
                () =>
                  setMessage(
                    "How do I transfer my number to TT&T?"
                  )
              }
            >
              Number porting
            </button>


            <button
              onClick={
                () =>
                  setMessage(
                    "I lost my phone. What should I do?"
                  )
              }
            >
              Lost phone
            </button>


            <button
              onClick={
                () =>
                  setMessage(
                    "Please open a support ticket about my service."
                  )
              }
            >
              Open ticket
            </button>

          </div>


          <div className="composer">

            <textarea
              value={message}
              onChange={
                (event) =>
                  setMessage(
                    event.target.value
                  )
              }
              onKeyDown={
                handleKeyDown
              }
              placeholder="Ask about your TT&T service..."
              rows={1}
            />


            <button
              className="send-button"
              onClick={sendMessage}
              disabled={
                loading ||
                !message.trim()
              }
            >
              {
                loading
                  ? "Working..."
                  : "Send"
              }
            </button>

          </div>


          <p className="composer-note">
            Session-scoped access •
            MCP tools •
            Grounded RAG responses
          </p>

        </section>

      </main>

    </div>
  );
}


export default App;