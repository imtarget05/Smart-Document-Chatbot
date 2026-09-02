import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface MessageBubbleProps {
  content: string;
  role: "user" | "assistant";
  isStreaming?: boolean;
}

/* Smart Document logo icon (Material style) */
function AssistantAvatar() {
  return (
    <div className="w-8 h-8 rounded-material-full bg-google-blue shrink-0 flex items-center justify-center">
      <svg width="16" height="16" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="white" opacity="0.3" />
        <polyline points="14 2 14 8 20 8" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" />
        <line x1="16" y1="13" x2="8" y2="13" stroke="white" strokeWidth="2" strokeLinecap="round" />
        <line x1="16" y1="17" x2="8" y2="17" stroke="white" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </div>
  );
}

/* Typing indicator dots */
function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-2" role="status" aria-label="Đang trả lời">
      <span className="w-2 h-2 rounded-full bg-google-blue/50 animate-bounce" style={{ animationDelay: "0ms" }} />
      <span className="w-2 h-2 rounded-full bg-google-blue/50 animate-bounce" style={{ animationDelay: "150ms" }} />
      <span className="w-2 h-2 rounded-full bg-google-blue/50 animate-bounce" style={{ animationDelay: "300ms" }} />
    </div>
  );
}

/* User avatar (colored circle) */
function UserAvatar() {
  return (
    <div className="w-8 h-8 rounded-material-full bg-surface-containerHigh shrink-0 flex items-center justify-center">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-onsurface-variant">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>
  );
}

export default function MessageBubble({ content, role, isStreaming }: MessageBubbleProps) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-2xl bg-google-blue text-white px-4 py-2.5 rounded-material-lg rounded-br-md shadow-material-btn">
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
        <UserAvatar />
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-3">
      <AssistantAvatar />
      <div className="max-w-2xl w-full">
        {content ? (
          <div className="bg-surface border border-outline rounded-material-lg rounded-bl-md px-4 py-3 shadow-material-1">
            <div
              className="leading-relaxed text-sm text-onsurface markdown-body"
              aria-live={isStreaming ? "polite" : undefined}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
                components={{
                  a({ href, children }) {
                    return (
                      <a href={href} target="_blank" rel="noopener noreferrer" className="text-google-blue underline">
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <TypingDots />
        )}
      </div>
    </div>
  );
}
