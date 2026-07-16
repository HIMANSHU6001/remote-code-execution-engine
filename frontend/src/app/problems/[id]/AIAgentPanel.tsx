import React, { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/store/chatStore";
import { Button } from "@/components/ui/button";
import { Brain, Send, Loader2, Sparkles, X, RotateCcw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface AICodingPanelProps {
  code: string;
  editor: any;
  onClose?: () => void;
  latestJobId?: string | null;
}

export function AICodingPanel({ code, editor, onClose, latestJobId }: AICodingPanelProps) {
  const { messages, addMessage, clearMessages } = useChatStore();
  const [input, setInput] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [streamingText, setStreamingText] = useState("");
  const decorationRef = useRef<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string>("");
  const fullResponseRef = useRef<string>("");
  const currentHashRef = useRef<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    sessionIdRef.current = "user_" + Math.random().toString(36).substring(7);
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      const wsUrl = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/ws/analyze") + "/" + sessionIdRef.current;
      console.log("Connecting to WebSocket:", wsUrl);

      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log("WebSocket connection established");
      };

      socket.onmessage = (event) => {
        console.log("event recieved from websocket: ", event)
        try {
          const data = JSON.parse(event.data);
          if (data.t === "text") {
            fullResponseRef.current += data.v;
            setStreamingText(fullResponseRef.current);
          } else if (data.t === "cmd") {
            console.log("cmd recieved from websocket: ", data)
            // Always highlight regardless of hash since Lamatic LLM doesn't have the hash
            highlightMonacoLine(data.v.line, data.v.msg);
          } else if (data.t === "guardrail") {
            setIsAnalyzing(false);
            addMessage({
              role: "assistant",
              content: `**Input Blocked**: ${data.message || "Request ignored by guardrail."}`
            });
          } else if (data.t === "error") {
            setIsAnalyzing(false);
            setStreamingText("");
            addMessage({
              role: "assistant",
              content: `**Error**: ${data.message || "An unexpected error occurred."}`
            });
          } else if (data.t === "sys" && data.action === "GENERATION_COMPLETE") {
            setIsAnalyzing(false);
            if (fullResponseRef.current) {
              addMessage({ role: "assistant", content: fullResponseRef.current });
              fullResponseRef.current = "";
              setStreamingText("");
            }
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err, event.data);
        }
      };

      socket.onclose = (event) => {
        wsRef.current = null;
        setIsAnalyzing(false);
        setStreamingText("");
        if (!event.wasClean) {
          console.warn(`WebSocket closed unexpectedly: ${event.code} ${event.reason}`);
          reconnectTimeout = setTimeout(connect, 2000);
        } else {
          console.log("WebSocket closed cleanly");
        }
      };

      socket.onerror = (err) => {
        console.error("WebSocket encountered an error:", err);
      };
    };

    connect();

    return () => {
      const socket = wsRef.current;
      if (socket) {
        // Disable onclose handler before closing to prevent reconnection loop
        socket.onclose = null;
        socket.onerror = null;
        socket.close(1000, "Component unmounting");
      }
      clearTimeout(reconnectTimeout);
    };
  }, []);

  useEffect(() => {
    if (editor && decorationRef.current.length > 0) {
      editor.deltaDecorations(decorationRef.current, []);
      decorationRef.current = [];
    }
  }, [code, editor]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const generateHash = async (str: string) => {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  };

  const highlightMonacoLine = (line: number, message: string) => {
    if (!editor) return;
    const newDecorations = editor.deltaDecorations(decorationRef.current, [
      {
        range: { startLineNumber: line, startColumn: 1, endLineNumber: line, endColumn: 1 },
        options: {
          isWholeLine: true,
          className: "monaco-line-error",
          glyphMarginClassName: "monaco-glyph-error",
          hoverMessage: { value: message },
        },
      },
    ]);
    decorationRef.current = newDecorations;
  };

  const handleAnalyze = async (userPrompt?: string) => {
    const currentHash = await generateHash(code);
    currentHashRef.current = currentHash;
    const promptToSend = userPrompt || "Please analyze my code.";
    if (!userPrompt) {
      addMessage({ role: "user", content: promptToSend });
    }

    const history = useChatStore.getState().messages;

    setIsAnalyzing(true);
    setStreamingText("");
    fullResponseRef.current = "";

    try {
      const response = await fetch('/lamatic-proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chatMessage: promptToSend,
          code: code,
          session_id: sessionIdRef.current,
          run_id: latestJobId || "",
          chatHistory: history
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Attempt to extract the reply based on typical Lamatic GraphQL/SDK structures
      let reply = "";
      if (data?.data?.executeWorkflow?.result?.reply) {
        reply = data.data.executeWorkflow.result.reply;
      } else if (data?.data?.executeFlow?.result?.reply) {
        reply = data.data.executeFlow.result.reply;
      } else if (data?.result?.reply) {
        reply = data.result.reply;
      } else if (data?.reply) {
        reply = data.reply;
      }

      if (reply) {
        addMessage({ role: "assistant", content: reply });
      } else {
        // Fallback if the structure is unexpected
        console.warn("Unexpected Lamatic response structure:", data);
        addMessage({ role: "assistant", content: "Response received, but couldn't parse the reply field. Check console for structure." });
      }
    } catch (error: any) {
      console.error("Failed to call Lamatic:", error);
      addMessage({ role: "assistant", content: `**Error**: ${error.message || "An unexpected error occurred."}` });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSend = () => {
    if (!input.trim() || isAnalyzing) return;
    const msg = input.trim();
    addMessage({ role: "user", content: msg });
    setInput("");
    handleAnalyze(msg);
  };

  const hasContent = messages.length > 0 || !!streamingText;

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--surface-secondary)" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 shrink-0 border-b"
        style={{
          height: "41px",
          borderColor: "var(--border-subtle)",
          background: "var(--panel-header-tint)",
        }}
      >
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center w-5 h-5">
            <div className="absolute inset-0 rounded-full bg-emerald-500/20 blur-sm" />
            <Brain className="h-3.5 w-3.5 text-emerald-400 relative z-10" />
          </div>
          <span className="text-[11px] font-bold tracking-[0.12em] uppercase text-text-tertiary">
            Coding Guide
          </span>
        </div>

        <div className="flex items-center gap-1">
          {hasContent && (
            <button
              onClick={clearMessages}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium text-text-muted hover:text-text-tertiary hover:bg-[var(--hover-bg)] transition-all"
            >
              <RotateCcw className="h-3 w-3" />
              Clear
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="w-6 h-6 flex items-center justify-center rounded-md text-text-muted hover:text-text-tertiary hover:bg-[var(--hover-bg)] transition-all"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-4 space-y-4 no-scrollbar bg-background">
        {!hasContent && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-5 py-12">
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-emerald-500/10 blur-xl scale-150" />
              <div className="relative w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-emerald-400/70" />
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-semibold text-text-secondary">Ask for guidance</p>
              <p className="text-xs text-text-muted leading-relaxed max-w-[180px]">
                I'll surface bugs and guide you through fixes with questions.
              </p>
            </div>
            <button
              onClick={() => handleAnalyze()}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-emerald-400 border border-emerald-500/25 bg-emerald-500/5 hover:bg-emerald-500/10 hover:border-emerald-500/40 transition-all"
            >
              Analyze my code
            </button>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role !== "user" && (
              <div className="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
                <Brain className="h-3 w-3 text-emerald-400" />
              </div>
            )}
            <div
              className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${msg.role === "user"
                ? "text-white rounded-tr-sm"
                : "text-text-secondary rounded-tl-sm border"
                }`}
              style={
                msg.role === "user"
                  ? { background: "linear-gradient(135deg, #059669 0%, #047857 100%)" }
                  : { background: "var(--hover-bg)", borderColor: "var(--border-subtle)" }
              }
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: ({ children, className }) => (
                    <code
                      className={className}
                      style={{
                        background: "rgba(16,185,129,0.08)",
                        color: "#6ee7b7",
                        padding: "1px 5px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontFamily: "var(--font-mono, monospace)",
                      }}
                    >
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre
                      style={{
                        background: "var(--code-bg)",
                        border: "1px solid var(--code-border)",
                        borderRadius: "8px",
                        padding: "10px 12px",
                        overflow: "auto",
                        fontSize: "12px",
                        margin: "6px 0",
                        fontFamily: "var(--font-mono, monospace)",
                      }}
                    >
                      {children}
                    </pre>
                  ),
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {streamingText && (
          <div className="flex gap-2.5 justify-start">
            <div className="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <Loader2 className="h-3 w-3 text-emerald-400 animate-spin" />
            </div>
            <div
              className="max-w-[88%] rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-[13px] leading-relaxed text-text-secondary border"
              style={{ background: "var(--hover-bg)", borderColor: "var(--border-subtle)" }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div
        className="px-3 pb-3 pt-2 shrink-0 border-t no-scrollbar"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div
          className="flex items-end gap-2 rounded-xl border px-3 py-2 focus-within:border-emerald-500/40 transition-colors"
          style={{
            background: "var(--hover-bg)",
            borderColor: "var(--border-subtle)",
          }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask about your code…"
            className="flex-1 bg-transparent text-[13px] text-text-secondary placeholder-text-muted focus:outline-none resize-none leading-relaxed"
            style={{ minHeight: "20px", maxHeight: "120px" }}
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={isAnalyzing || !input.trim()}
            className="w-7 h-7 rounded-lg flex items-center justify-center transition-all shrink-0 mb-0.5"
            style={{
              background: input.trim() && !isAnalyzing
                ? "linear-gradient(135deg, #059669, #047857)"
                : "var(--hover-bg)",
            }}
          >
            {isAnalyzing ? (
              <Loader2 className="h-3.5 w-3.5 text-text-muted animate-spin" />
            ) : (
              <Send className={`h-3.5 w-3.5 ${input.trim() ? "text-white" : "text-text-muted"}`} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}