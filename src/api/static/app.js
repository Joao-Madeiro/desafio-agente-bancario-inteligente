const { useState, useEffect, useRef } = React;

const AGENT_CONFIGS = {
  triage: {
    name: "Agente de Triagem",
    badge: "Triagem & Autenticação",
    shortName: "Triagem",
    color: "from-blue-600 to-cyan-600",
    border: "border-cyan-500/40",
    bg: "bg-cyan-950/50 text-cyan-300",
    icon: "fa-shield-halved",
    desc: "Autenticação e triagem de demandas",
  },
  credit: {
    name: "Agente de Crédito",
    badge: "Crédito & Limites",
    shortName: "Crédito",
    color: "from-emerald-600 to-teal-600",
    border: "border-emerald-500/40",
    bg: "bg-emerald-950/50 text-emerald-300",
    icon: "fa-credit-card",
    desc: "Consulta e solicitações de aumento de limite",
  },
  interview: {
    name: "Agente de Entrevista",
    badge: "Entrevista Financeira",
    shortName: "Entrevista",
    color: "from-purple-600 to-indigo-600",
    border: "border-purple-500/40",
    bg: "bg-purple-950/50 text-purple-300",
    icon: "fa-clipboard-question",
    desc: "Entrevista e recálculo de score",
  },
  exchange: {
    name: "Agente de Câmbio",
    badge: "Câmbio & Moedas",
    shortName: "Câmbio",
    color: "from-amber-600 to-orange-600",
    border: "border-amber-500/40",
    bg: "bg-amber-950/50 text-amber-300",
    icon: "fa-coins",
    desc: "Cotações de moedas em tempo real",
  },
  ended: {
    name: "Atendimento Finalizado",
    badge: "Encerrado",
    shortName: "Encerrado",
    color: "from-slate-700 to-gray-800",
    border: "border-slate-600/40",
    bg: "bg-slate-800 text-slate-400",
    icon: "fa-circle-check",
    desc: "Sessão finalizada",
  },
};

const AGENT_PIPELINE = ["triage", "credit", "interview", "exchange"];

function ReactIcon({ name, size = 15 }) {
  const icons = {
    creditCard: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <path d="M2 10h20" />
        <path d="M6 15h4" />
      </>
    ),
    trendingUp: (
      <>
        <path d="m3 17 6-6 4 4 8-8" />
        <path d="M15 7h6v6" />
      </>
    ),
    coins: (
      <>
        <circle cx="9" cy="9" r="6" />
        <path d="M15 9.5A6 6 0 0 1 9.5 15" />
        <path d="M15 9h1a6 6 0 0 1 0 12H9a6 6 0 0 1-5.65-4" />
      </>
    ),
    clipboard: (
      <>
        <rect x="5" y="4" width="14" height="17" rx="2" />
        <path d="M9 4V2h6v2" />
        <path d="M9 10h6M9 14h6M9 18h3" />
      </>
    ),
    logOut: (
      <>
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <path d="m16 17 5-5-5-5" />
        <path d="M21 12H9" />
      </>
    ),
    zap: (
      <path d="M13 2 3 14h9l-1 8 10-12h-9z" />
    ),
    chevronDown: (
      <path d="m6 9 6 6 6-6" />
    ),
    chevronUp: (
      <path d="m18 15-6-6-6 6" />
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </>
    ),
    moon: (
      <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5z" />
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {icons[name]}
    </svg>
  );
}

// Função de segurança no cliente para extrair texto limpo
function cleanMessageText(text) {
  if (!text) return "";
  if (typeof text !== "string") return String(text);

  let trimmed = text.trim();
  const looksLikeCollection =
    (trimmed.startsWith("[") && trimmed.endsWith("]")) ||
    (trimmed.startsWith("{") && trimmed.endsWith("}"));

  if (!looksLikeCollection) return text;

  // 1) JSON válido (aspas duplas)
  try {
    const parsed = JSON.parse(trimmed);
    const cleaned = extractTextFromValue(parsed);
    if (cleaned) return cleaned;
  } catch (e) {}

  // 2) Representação Python (aspas simples): captura todos os campos 'text'
  const singleQuoted = [...trimmed.matchAll(/'text'\s*:\s*'((?:\\'|[^'])*)'/g)];
  if (singleQuoted.length) {
    return singleQuoted
      .map((m) => m[1].replace(/\\n/g, "\n").replace(/\\'/g, "'").replace(/\\\\/g, "\\"))
      .join("");
  }

  // 3) Campos "text" com aspas duplas
  const doubleQuoted = [...trimmed.matchAll(/"text"\s*:\s*"((?:\\"|[^"])*)"/g)];
  if (doubleQuoted.length) {
    return doubleQuoted
      .map((m) => m[1].replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, "\\"))
      .join("");
  }

  return text;
}

function extractTextFromValue(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map(extractTextFromValue).filter(Boolean).join("\n");
  }
  if (typeof value === "object") {
    if (typeof value.text === "string") return value.text;
    if (typeof value.content === "string") return value.content;
    return "";
  }
  return String(value);
}

// Componente para renderizar Markdown de forma segura
function MarkdownContent({ content }) {
  const cleanText = cleanMessageText(content || "");

  const getHtml = () => {
    if (window.marked && window.DOMPurify) {
      try {
        window.marked.setOptions({ breaks: true, gfm: true });
        const rawHtml = window.marked.parse(cleanText);
        return { __html: window.DOMPurify.sanitize(rawHtml) };
      } catch (err) {
        console.error("Erro no parser marked:", err);
      }
    }

    return { __html: renderMarkdown(cleanText) };
  };

  return <div className="markdown-content text-sm leading-relaxed" dangerouslySetInnerHTML={getHtml()} />;
}

function TypingMarkdownContent({ content }) {
  const fullText = cleanMessageText(content || "");
  const [visibleText, setVisibleText] = useState(fullText);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    let position = 0;
    const charactersPerTick = 2;
    const tickInterval = 14;

    setVisibleText("");
    setIsTyping(Boolean(fullText));

    if (!fullText) return undefined;

    const timer = window.setInterval(() => {
      position = Math.min(position + charactersPerTick, fullText.length);
      setVisibleText(fullText.slice(0, position));

      if (position >= fullText.length) {
        window.clearInterval(timer);
        setIsTyping(false);
      }
    }, tickInterval);

    return () => window.clearInterval(timer);
  }, [fullText]);

  return (
    <div>
      <MarkdownContent content={visibleText} />
      {isTyping && <span className="typing-cursor" aria-hidden="true">|</span>}
    </div>
  );
}

// Renderizador Markdown autônomo (fallback): suporta negrito (**), itálico (*),
// títulos (#/##/###), listas (- / 1.) e quebras de linha.
function renderMarkdown(text) {
  const lines = String(text).split(/\r?\n/);
  let inList = false;
  let listType = null;
  let html = "";

  const inline = (s) => {
    let out = s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    out = out.replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-white">$1</strong>');
    out = out.replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em class="italic text-slate-300">$2</em>');
    return out;
  };

  const closeList = () => {
    if (inList) {
      html += listType === "ul" ? "</ul>" : "</ol>";
      inList = false;
      listType = null;
    }
  };

  for (const line of lines) {
    if (/^###\s+/.test(line)) {
      closeList();
      html += `<h3 class="font-bold text-base text-white mt-2 mb-1">${inline(line.replace(/^###\s+/, ""))}</h3>`;
    } else if (/^##\s+/.test(line)) {
      closeList();
      html += `<h2 class="font-bold text-lg text-white mt-2 mb-1">${inline(line.replace(/^##\s+/, ""))}</h2>`;
    } else if (/^#\s+/.test(line)) {
      closeList();
      html += `<h1 class="font-bold text-xl text-white mt-2 mb-1">${inline(line.replace(/^#\s+/, ""))}</h1>`;
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (!inList || listType !== "ul") {
        closeList();
        html += "<ul>";
        inList = true;
        listType = "ul";
      }
      html += `<li class="ml-4 list-disc">${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`;
    } else if (/^\s*\d+[.)]\s+/.test(line)) {
      if (!inList || listType !== "ol") {
        closeList();
        html += "<ol>";
        inList = true;
        listType = "ol";
      }
      html += `<li class="ml-4 list-decimal">${inline(line.replace(/^\s*\d+[.)]\s+/, ""))}</li>`;
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p class="mb-1">${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function BancoAgilApp() {
  const [sessionId, setSessionId] = useState(() => "sess_" + Math.random().toString(36).substr(2, 9));
  
  const [messages, setMessages] = useState([
    {
      type: "message",
      role: "assistant",
      agent: "triage",
      content: "Olá! Bem-vindo ao **Madeiro Bank**. Sou seu assistente virtual. Envie uma mensagem para iniciarmos seu atendimento.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState("triage");
  const [clientInfo, setClientInfo] = useState(null);
  const [isFinished, setIsFinished] = useState(false);
  const [isLightTheme, setIsLightTheme] = useState(() => (
    window.localStorage.getItem("madeiro-theme") === "light"
  ));
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showAuthButton, setShowAuthButton] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalCpf, setAuthModalCpf] = useState("");
  const [authModalDob, setAuthModalDob] = useState("");
  const [authModalError, setAuthModalError] = useState("");

  const [activeTab, setActiveTab] = useState("clients");
  const [clientsData, setClientsData] = useState([]);
  const [requestsData, setRequestsData] = useState([]);
  const [scoreRulesData, setScoreRulesData] = useState([]);
  const [ratesData, setRatesData] = useState({});
  const [isRefreshingData, setIsRefreshingData] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    document.body.classList.toggle("theme-light-body", isLightTheme);
    window.localStorage.setItem("madeiro-theme", isLightTheme ? "light" : "dark");
  }, [isLightTheme]);

  const loadAllData = async () => {
    setIsRefreshingData(true);
    try {
      const [resClients, resReqs, resRules, resRates] = await Promise.all([
        fetch("/api/clients").then(r => r.json()),
        fetch("/api/requests").then(r => r.json()),
        fetch("/api/score-rules").then(r => r.json()),
        fetch("/api/exchange-rates").then(r => r.json()),
      ]);
      setClientsData(resClients.clients || []);
      setRequestsData(resReqs.requests || []);
      setScoreRulesData(resRules.rules || []);
      setRatesData(resRates.quotes || {});
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
    } finally {
      setIsRefreshingData(false);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 12000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (textToSend) => {
    const text = textToSend || inputMessage;
    if (!text.trim() || isLoading) return;

    const userTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMsgList = [...messages, { type: "message", role: "user", content: text, timestamp: userTime }];
    setMessages(newMsgList);
    setInputMessage("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Falha na comunicação com o servidor.");
      }

      const data = await res.json();
      const botTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const currentList = [...newMsgList];

      currentList.push({
        type: "message",
        role: "assistant",
        agent: data.active_agent || activeAgent,
        content: data.response,
        timestamp: botTime,
      });

      setMessages(currentList);
      setActiveAgent(data.active_agent || "triage");

      if (data.request_auth_modal !== undefined) {
        const shouldShowAuthButton = !!data.request_auth_modal;
        setShowAuthButton(shouldShowAuthButton);
        if (!shouldShowAuthButton) setIsAuthModalOpen(false);
      }
      if (data.client_info) {
        setClientInfo(data.client_info);
      }
      if (data.is_finished) {
        setIsFinished(true);
      }

      loadAllData();
    } catch (err) {
      setMessages([
        ...newMsgList,
        {
          type: "message",
          role: "assistant",
          agent: activeAgent,
          content: `⚠️ **Atenção:** Ocorreu um erro no processamento: ${err.message}. Por favor, tente novamente.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetSession = async () => {
    const newId = "sess_" + Math.random().toString(36).substr(2, 9);
    setSessionId(newId);
    setActiveAgent("triage");
    setClientInfo(null);
    setIsFinished(false);
    setShowQuickActions(false);
    setShowAuthButton(false);
    setIsAuthModalOpen(false);
    setAuthModalCpf("");
    setAuthModalDob("");
    setAuthModalError("");
    setMessages([
      {
        type: "message",
        role: "assistant",
        agent: "triage",
        content: "Olá! Bem-vindo ao **Madeiro Bank**. Envie uma mensagem para iniciarmos seu atendimento.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    try {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: newId }),
      });
    } catch (e) {}
    loadAllData();
  };

  const handleQuickClientSelect = (client) => {
    const dateFormatted = client.data_nascimento.split("-").reverse().join("/");
    const promptText = `Meu CPF é ${client.cpf} e minha data de nascimento é ${dateFormatted}`;
    handleSendMessage(promptText);
  };

  const formatAuthDate = (value) => {
    const trimmed = String(value || "").trim();
    const isoMatch = trimmed.match(/^(\d{4})[-/](\d{2})[-/](\d{2})$/);
    if (isoMatch) return `${isoMatch[3]}/${isoMatch[2]}/${isoMatch[1]}`;

    const digits = trimmed.replace(/\D/g, "").slice(0, 8);
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
  };

  const formatAuthCpf = (value) => {
    const digits = String(value || "").replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
    if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
  };

  const handleAuthModalSubmit = (e) => {
    e.preventDefault();
    const cpf = authModalCpf.replace(/\D/g, "");
    const dob = formatAuthDate(authModalDob);
    if (!cpf || !dob || isLoading || isFinished) return;
    if (cpf.length !== 11) {
      setAuthModalError("Informe um CPF válido com 11 dígitos.");
      return;
    }
    setAuthModalCpf("");
    setAuthModalDob("");
    setAuthModalError("");
    setIsAuthModalOpen(false);
    setShowAuthButton(false);
    handleSendMessage(`Meu CPF é ${formatAuthCpf(cpf)} e minha data de nascimento é ${dob}`);
  };

  const currentAgentMeta = AGENT_CONFIGS[activeAgent] || AGENT_CONFIGS.triage;

  return (
    <div className={`flex flex-col h-screen max-h-screen overflow-hidden bg-[#0a0e17] ${isLightTheme ? "theme-light" : ""}`}>
      {/* Top Header */}
      <header className="h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-lg px-6 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-agil-cyan flex items-center justify-center shadow-lg shadow-brand-500/20 font-bold text-white text-xl font-heading">
            J
          </div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading font-bold text-lg text-white tracking-tight">Madeiro Bank</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIsLightTheme((light) => !light)}
            aria-label={isLightTheme ? "Ativar tema escuro" : "Ativar tema claro"}
            title={isLightTheme ? "Ativar tema escuro" : "Ativar tema claro"}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
          >
            <ReactIcon name={isLightTheme ? "moon" : "sun"} size={15} />
            <span className="hidden md:inline text-xs">{isLightTheme ? "Escuro" : "Claro"}</span>
          </button>
          <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${currentAgentMeta.bg} ${currentAgentMeta.border}`}>
            <i className={`fa-solid ${currentAgentMeta.icon}`}></i>
            <span>Especialista: <strong>{currentAgentMeta.name}</strong></span>
          </div>

          <button
            onClick={handleResetSession}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/60 hover:text-rose-300 hover:border-rose-700/50 text-xs font-medium text-slate-300 transition-all border border-slate-700"
            title="Reiniciar Sessão"
          >
            <i className="fa-solid fa-rotate-left"></i>
            <span className="hidden md:inline">Novo Atendimento</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Chat Area */}
        <div className="flex-1 flex flex-col h-full bg-[#0a0e17] border-r border-slate-800/80">
          
          {/* Real-Time Agent Pipeline Tracker */}
          <div className="px-6 py-2 bg-slate-900/50 border-b border-slate-800/60 flex items-center justify-between overflow-x-auto custom-scrollbar">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mr-1">Especialistas:</span>
              {AGENT_PIPELINE.map((agentKey, idx) => {
                const conf = AGENT_CONFIGS[agentKey];
                const isActive = activeAgent === agentKey;
                return (
                  <React.Fragment key={agentKey}>
                    <div
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-all ${
                        isActive
                          ? `${conf.bg} ${conf.border} border font-bold shadow-md shadow-brand-500/10 scale-105`
                          : "text-slate-500 hover:text-slate-400 bg-slate-800/30"
                      }`}
                    >
                      <i className={`fa-solid ${conf.icon} text-[10px]`}></i>
                      <span>{conf.shortName}</span>
                      {isActive && (
                        <span className="text-[9px] px-1 py-0.2 rounded bg-white/10 font-mono ml-0.5">ATIVO</span>
                      )}
                    </div>
                    {idx < AGENT_PIPELINE.length - 1 && (
                      <i className="fa-solid fa-chevron-right text-[9px] text-slate-700"></i>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            {clientInfo && (
              <div className="flex items-center gap-2 text-xs text-slate-300 ml-4 shrink-0">
                <i className="fa-solid fa-user-check text-emerald-400"></i>
                <span className="font-semibold text-white">{clientInfo.nome}</span>
                <span className="text-slate-500">(CPF: ***.{clientInfo.cpf.slice(3,6)}.{clientInfo.cpf.slice(6,9)}-**)</span>
              </div>
            )}
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
            {messages.map((item, index) => {
              const msg = item;
              if (msg.type === "transition") return null;
              const isBot = msg.role === "assistant";
              const agentMeta = AGENT_CONFIGS[msg.agent] || AGENT_CONFIGS.triage;

              return (
                <div
                  key={index}
                  className={`flex flex-col ${isBot ? "items-start" : "items-end"} max-w-3xl ${isBot ? "mr-auto" : "ml-auto"}`}
                >
                  {isBot && (
                    <div className="flex items-center gap-2 mb-1 pl-1">
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${agentMeta.bg} ${agentMeta.border} flex items-center gap-1.5`}>
                        <i className={`fa-solid ${agentMeta.icon}`}></i>
                        {agentMeta.badge}
                      </span>
                      <span className="text-[10px] text-slate-500">{msg.timestamp}</span>
                    </div>
                  )}

                  <div
                    className={`p-4 rounded-2xl text-sm leading-relaxed ${
                      isBot
                        ? "message-assistant glass-panel text-slate-200 rounded-tl-sm border-slate-800 shadow-md"
                        : "message-user bg-gradient-to-r from-brand-600 to-brand-700 text-white rounded-tr-sm shadow-lg shadow-brand-600/10 font-medium"
                    }`}
                  >
                    {isBot ? (
                      <TypingMarkdownContent content={msg.content} />
                    ) : (
                      <MarkdownContent content={msg.content} />
                    )}
                  </div>

                  {!isBot && (
                    <span className="text-[10px] text-slate-500 mt-1 pr-1">{msg.timestamp}</span>
                  )}
                </div>
              );
            })}

            {showAuthButton && !clientInfo && !isFinished && (
              <div className="flex flex-col items-start mr-auto max-w-xl animate-fade-in">
                <div className="glass-panel p-4 rounded-2xl rounded-tl-sm border-cyan-800/50 shadow-md">
                  <div className="flex items-center gap-2 text-xs text-slate-300 mb-3">
                    <i className="fa-solid fa-shield-halved text-cyan-400"></i>
                    <span>Para continuar com segurança, informe seus dados cadastrais.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalError("");
                      setIsAuthModalOpen(true);
                    }}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all"
                  >
                    <i className="fa-solid fa-lock-open text-xs"></i>
                    <span>Preencher dados de autenticação</span>
                  </button>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="flex flex-col items-start mr-auto max-w-xl">
                <div className="flex items-center gap-2 mb-1 pl-1">
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${currentAgentMeta.bg} ${currentAgentMeta.border} flex items-center gap-1.5`}>
                    <i className={`fa-solid ${currentAgentMeta.icon}`}></i>
                    {currentAgentMeta.badge}
                  </span>
                  <span className="text-[10px] text-slate-500">Digitando...</span>
                </div>
                <div className="glass-panel p-4 rounded-2xl rounded-tl-sm border-slate-800 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce"></div>
                  <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.2s]"></div>
                  <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.4s]"></div>
                  <span className="text-xs text-slate-400 ml-2">Processando com {currentAgentMeta.name}...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions Toggle */}
          <div className="px-6 py-2 bg-slate-900/30 border-t border-slate-800/40 flex justify-end">
            <button
              type="button"
              onClick={() => setShowQuickActions((visible) => !visible)}
              aria-expanded={showQuickActions}
              className="inline-flex items-center gap-2 text-[11px] font-medium text-slate-400 hover:text-white transition-colors"
            >
              <ReactIcon name="zap" size={14} />
              <span>Sugestões rápidas</span>
              <ReactIcon name={showQuickActions ? "chevronDown" : "chevronUp"} size={13} />
            </button>
          </div>

          {showQuickActions && (
            <div className="px-6 py-2 bg-slate-900/50 border-t border-slate-800/40 flex items-center gap-2 overflow-x-auto custom-scrollbar animate-fade-in">
              <button
                onClick={() => handleSendMessage("Gostaria de consultar meu limite de crédito atual.")}
                className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              >
                <span className="inline-flex items-center gap-1.5"><ReactIcon name="creditCard" />Consultar Limite</span>
              </button>
              <button
                onClick={() => handleSendMessage("Quero solicitar um aumento do meu limite de crédito para R$ 10.000,00.")}
                className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              >
                <span className="inline-flex items-center gap-1.5"><ReactIcon name="trendingUp" />Solicitar Aumento</span>
              </button>
              <button
                onClick={() => handleSendMessage("Qual a cotação do Dólar e do Euro hoje?")}
                className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              >
                <span className="inline-flex items-center gap-1.5"><ReactIcon name="coins" />Cotação do Dólar</span>
              </button>
              <button
                onClick={() => handleSendMessage("Quero fazer a entrevista de crédito para atualizar meu score.")}
                className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              >
                <span className="inline-flex items-center gap-1.5"><ReactIcon name="clipboard" />Fazer Entrevista de Score</span>
              </button>
              <button
                onClick={() => handleSendMessage("Muito obrigado pelo atendimento, quero finalizar a conversa.")}
                className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              >
                <span className="inline-flex items-center gap-1.5"><ReactIcon name="logOut" />Encerrar</span>
              </button>
            </div>
          )}

          {/* Chat Input Bar */}
          <div className="p-4 bg-slate-900/60 border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                disabled={isLoading || isFinished}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  isFinished
                    ? "Atendimento finalizado. Clique em 'Novo Atendimento' para reiniciar."
                    : "Digite sua mensagem aqui..."
                }
                className="flex-1 bg-slate-800/80 text-white placeholder-slate-500 text-sm rounded-xl px-4 py-3 border border-slate-700 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              />
              <button
                type="submit"
                disabled={isLoading || !inputMessage.trim() || isFinished}
                className="px-5 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-500 hover:to-brand-600 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-brand-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <span>Enviar</span>
                <i className="fa-solid fa-paper-plane text-xs"></i>
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Banking Hub & Live Inspector */}
        <div className="w-96 flex flex-col h-full bg-slate-900/30 overflow-hidden shrink-0 hidden lg:flex">
          {/* User Account Summary Card */}
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
              <span>Conta & Perfil</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${clientInfo ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-amber-500/20 text-amber-400 border border-amber-500/30"}`}>
                {clientInfo ? "Autenticado" : "Não Identificado"}
              </span>
            </h2>

            {clientInfo ? (
              <div className="glass-panel p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-white">{clientInfo.nome}</div>
                    <div className="text-xs text-slate-400">CPF: {clientInfo.cpf}</div>
                  </div>
                  <div className="w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                    <i className="fa-solid fa-user-check"></i>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2">
                  <div className="bg-slate-800/50 p-2.5 rounded-lg">
                    <div className="text-[10px] text-slate-400">Limite de Crédito</div>
                    <div className="text-sm font-bold text-emerald-400">
                      R$ {clientInfo.limite_credito.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="bg-slate-800/50 p-2.5 rounded-lg">
                    <div className="text-[10px] text-slate-400">Score de Crédito</div>
                    <div className="text-sm font-bold text-brand-400">
                      {clientInfo.score_credito} <span className="text-[10px] text-slate-400 font-normal">/ 1000</span>
                    </div>
                  </div>
                </div>

                {/* Score Bar */}
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-500 via-brand-500 to-emerald-500 transition-all duration-500"
                    style={{ width: `${Math.min(100, (clientInfo.score_credito / 1000) * 100)}%` }}
                  ></div>
                </div>
              </div>
            ) : (
              <div className="glass-panel p-4 rounded-xl text-center py-6">
                <i className="fa-solid fa-lock text-2xl text-slate-600 mb-2"></i>
                 <p className="text-xs text-slate-400">Use o botão de autenticação no chat para informar seus dados e liberar o cadastro.</p>
              </div>
            )}
          </div>

          {/* Quick Rates Ticker */}
          <div className="px-4 py-3 border-b border-slate-800 bg-slate-950/30">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              <span>Cotações Rápidas</span>
              <i className="fa-solid fa-arrow-trend-up text-agil-cyan"></i>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-medium">USD / Dólar</div>
                <div className="font-bold text-white">R$ 5,75</div>
              </div>
              <div className="bg-slate-800/40 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400 font-medium">EUR / Euro</div>
                <div className="font-bold text-white">R$ 6,22</div>
              </div>
            </div>
          </div>

          {/* Live CSV Inspector Tabs */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-4 pt-3 pb-2 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <i className="fa-solid fa-database text-brand-400"></i>
                <span>Bases de Dados (CSV)</span>
              </h2>
              <button
                onClick={loadAllData}
                disabled={isRefreshingData}
                className="text-xs text-slate-400 hover:text-white transition-colors"
                title="Atualizar dados CSV"
              >
                <i className={`fa-solid fa-arrows-rotate ${isRefreshingData ? 'animate-spin' : ''}`}></i>
              </button>
            </div>

            {/* Tab Headers */}
            <div className="flex border-b border-slate-800 px-4 gap-1">
              <button
                onClick={() => setActiveTab("clients")}
                className={`text-xs py-2 px-3 border-b-2 font-medium transition-all ${
                  activeTab === "clients"
                    ? "border-brand-500 text-brand-300 font-bold"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Clientes ({clientsData.length})
              </button>
              <button
                onClick={() => setActiveTab("requests")}
                className={`text-xs py-2 px-3 border-b-2 font-medium transition-all ${
                  activeTab === "requests"
                    ? "border-brand-500 text-brand-300 font-bold"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Pedidos ({requestsData.length})
              </button>
              <button
                onClick={() => setActiveTab("rules")}
                className={`text-xs py-2 px-3 border-b-2 font-medium transition-all ${
                  activeTab === "rules"
                    ? "border-brand-500 text-brand-300 font-bold"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Regras Score
              </button>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {activeTab === "clients" && (
                <div className="space-y-2">
                  <div className="text-[11px] text-slate-500 mb-2">
                    💡 Clique em <strong>Testar</strong> para preencher o chat automaticamente:
                  </div>
                  {clientsData.map((c, i) => (
                    <div key={i} className="glass-card p-3 rounded-lg text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">{c.nome}</span>
                        <button
                          onClick={() => handleQuickClientSelect(c)}
                          className="px-2 py-0.5 rounded bg-brand-600/30 hover:bg-brand-600 text-brand-200 hover:text-white border border-brand-500/40 text-[10px] font-semibold transition-colors"
                        >
                          Testar
                        </button>
                      </div>
                      <div className="text-slate-400 grid grid-cols-2 gap-1 text-[11px]">
                        <div>CPF: <span className="text-slate-300">{c.cpf}</span></div>
                        <div>Nasc: <span className="text-slate-300">{c.data_nascimento}</span></div>
                        <div>Limite: <span className="text-emerald-400 font-medium">R$ {c.limite_credito.toFixed(2)}</span></div>
                        <div>Score: <span className="text-brand-300 font-medium">{c.score_credito} pts</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "requests" && (
                <div className="space-y-2">
                  {requestsData.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-500">
                      Nenhuma solicitação de aumento registrada ainda.
                    </div>
                  ) : (
                    requestsData.map((req, i) => (
                      <div key={i} className="glass-card p-3 rounded-lg text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-white font-mono">{req.cpf_cliente}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                            req.status_pedido === 'aprovado'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}>
                            {req.status_pedido}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          De R$ {req.limite_atual.toFixed(2)} para <strong className="text-white">R$ {req.novo_limite_solicitado.toFixed(2)}</strong>
                        </div>
                        <div className="text-[9px] text-slate-500">{new Date(req.data_hora_solicitacao).toLocaleString('pt-BR')}</div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "rules" && (
                <div className="space-y-2">
                  {scoreRulesData.map((rule, i) => (
                    <div key={i} className="glass-card p-2.5 rounded-lg text-xs">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-brand-300">{rule.score_min} a {rule.score_max} pts</span>
                        <span className="text-emerald-400 font-bold">Máx R$ {rule.limite_maximo_permitido.toFixed(2)}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1">{rule.descricao_faixa}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Auth Modal: CPF + Data de Nascimento */}
      {isAuthModalOpen && showAuthButton && !clientInfo && !isFinished && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="auth-modal-card w-full max-w-md glass-panel rounded-2xl border border-cyan-800/60 shadow-2xl shadow-cyan-500/10 overflow-hidden">
            <div className="auth-modal-header px-6 py-4 bg-gradient-to-r from-cyan-950/80 to-blue-950/80 border-b border-cyan-800/40 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <i className="fa-solid fa-shield-halved text-white"></i>
              </div>
              <div>
                <h2 className="font-heading font-bold text-white text-lg leading-tight">Autenticação do Cliente</h2>
                <p className="text-[11px] text-cyan-300/80">Madeiro Bank · Atendimento seguro</p>
              </div>
            </div>

            <form onSubmit={handleAuthModalSubmit} className="p-6 space-y-4">
                <p className="text-xs text-slate-400 leading-relaxed">
                Para iniciarmos seu atendimento com segurança, informe seus dados cadastrais.
                Use um CPF cadastrado na base de teste:
                </p>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-cyan-400 mb-1.5">
                  <i className="fa-solid fa-id-card mr-1.5"></i>CPF
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={14}
                  value={authModalCpf}
                  disabled={isLoading || isFinished}
                  onChange={(e) => setAuthModalCpf(formatAuthCpf(e.target.value))}
                  placeholder="000.000.000-00"
                  className="w-full bg-slate-800/80 text-white placeholder-slate-500 text-sm rounded-xl px-4 py-3 border border-slate-700 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 disabled:opacity-50 transition-all"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-cyan-400 mb-1.5">
                  <i className="fa-solid fa-calendar mr-1.5"></i>Data de Nascimento
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={10}
                  value={authModalDob}
                  disabled={isLoading || isFinished}
                  onChange={(e) => setAuthModalDob(formatAuthDate(e.target.value))}
                  placeholder="DD/MM/AAAA"
                  className="w-full bg-slate-800/80 text-white placeholder-slate-500 text-sm rounded-xl px-4 py-3 border border-slate-700 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 disabled:opacity-50 transition-all"
                />
              </div>

              {authModalError && (
                <p className="text-xs text-rose-400" role="alert">{authModalError}</p>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="submit"
                  disabled={isLoading || isFinished || !authModalCpf.trim() || !authModalDob.trim()}
                  className="flex-1 px-5 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <i className="fa-solid fa-lock-open text-xs"></i>
                  <span>Autenticar</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsAuthModalOpen(false)}
                  className="px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm border border-slate-700 transition-colors"
                  title="Fechar"
                >
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<BancoAgilApp />);
