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
      content: "Olá! Bem-vindo ao **Banco Ágil**. Sou seu assistente virtual. Para iniciarmos seu atendimento com segurança, por favor, me informe seu **CPF** e **Data de Nascimento**.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState("triage");
  const [clientInfo, setClientInfo] = useState(null);
  const [isFinished, setIsFinished] = useState(false);

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

      if (data.transition_occurred && data.previous_agent && data.active_agent && data.previous_agent !== data.active_agent) {
        currentList.push({
          type: "transition",
          from: data.previous_agent,
          to: data.active_agent,
          timestamp: botTime,
        });
      }

      currentList.push({
        type: "message",
        role: "assistant",
        agent: data.active_agent || activeAgent,
        content: data.response,
        timestamp: botTime,
      });

      setMessages(currentList);
      setActiveAgent(data.active_agent || "triage");

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
    setMessages([
      {
        type: "message",
        role: "assistant",
        agent: "triage",
        content: "Olá! Bem-vindo ao **Banco Ágil**. Sou seu assistente virtual. Para iniciarmos seu atendimento com segurança, por favor, me informe seu **CPF** e **Data de Nascimento**.",
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

  const currentAgentMeta = AGENT_CONFIGS[activeAgent] || AGENT_CONFIGS.triage;

  return (
    <div className="flex flex-col h-screen max-h-screen overflow-hidden bg-[#0a0e17]">
      {/* Top Header */}
      <header className="h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-lg px-6 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-agil-cyan flex items-center justify-center shadow-lg shadow-brand-500/20 font-bold text-white text-xl font-heading">
            Á
          </div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading font-bold text-lg text-white tracking-tight">Banco Ágil</h1>
            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30">
              AI
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
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
              if (item.type === "transition") {
                const fromMeta = AGENT_CONFIGS[item.from] || AGENT_CONFIGS.triage;
                const toMeta = AGENT_CONFIGS[item.to] || AGENT_CONFIGS.triage;
                return (
                  <div key={index} className="flex items-center justify-center my-4 animate-fade-in">
                    <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900 border border-brand-500/40 text-xs shadow-lg shadow-brand-500/10">
                      <i className="fa-solid fa-arrow-right-arrow-left text-brand-400 text-xs animate-pulse"></i>
                      <span className="text-slate-400">Transferência em tempo real:</span>
                      <span className="text-slate-300 font-medium">{fromMeta.name}</span>
                      <i className="fa-solid fa-arrow-right text-[10px] text-brand-400"></i>
                      <span className={`px-2 py-0.5 rounded font-bold ${toMeta.bg} ${toMeta.border} border text-[11px]`}>
                        {toMeta.name}
                      </span>
                    </div>
                  </div>
                );
              }

              const msg = item;
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
                        ? "glass-panel text-slate-200 rounded-tl-sm border-slate-800 shadow-md"
                        : "bg-gradient-to-r from-brand-600 to-brand-700 text-white rounded-tr-sm shadow-lg shadow-brand-600/10 font-medium"
                    }`}
                  >
                    <MarkdownContent content={msg.content} />
                  </div>

                  {!isBot && (
                    <span className="text-[10px] text-slate-500 mt-1 pr-1">{msg.timestamp}</span>
                  )}
                </div>
              );
            })}

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

          {/* Quick Actions Bar */}
          <div className="px-6 py-2 bg-slate-900/30 border-t border-slate-800/40 flex items-center gap-2 overflow-x-auto custom-scrollbar">
            <span className="text-[11px] font-medium text-slate-500 shrink-0">Sugestões rápidas:</span>
            <button
              onClick={() => handleSendMessage("Gostaria de consultar meu limite de crédito atual.")}
              className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              💳 Consultar Limite
            </button>
            <button
              onClick={() => handleSendMessage("Quero solicitar um aumento do meu limite de crédito para R$ 10.000,00.")}
              className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              📈 Solicitar Aumento
            </button>
            <button
              onClick={() => handleSendMessage("Qual a cotação do Dólar e do Euro hoje?")}
              className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              💱 Cotação do Dólar
            </button>
            <button
              onClick={() => handleSendMessage("Quero fazer a entrevista de crédito para atualizar meu score.")}
              className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              📝 Fazer Entrevista de Score
            </button>
            <button
              onClick={() => handleSendMessage("Muito obrigado pelo atendimento, quero finalizar a conversa.")}
              className="shrink-0 text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              👋 Encerrar
            </button>
          </div>

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
                <p className="text-xs text-slate-400">Informe seu CPF e data de nascimento no chat para liberar os dados cadastrais.</p>
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
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<BancoAgilApp />);
