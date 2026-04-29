import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

function ChatWindow({ sessionId, documentId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchChatHistory();
  }, [sessionId, documentId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchChatHistory = async () => {
    try {
      const response = await fetch(
        `http://localhost:8080/api/chat/history/${sessionId}/${documentId}`
      );
      const data = await response.json();
      setMessages(data);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8080/api/chat/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          documentId,
          message: userMessage,
        }),
      });

      const data = await response.json();
      setMessages(prev => [...prev, data]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-xl mb-2">💬 No messages yet</p>
              <p>Start by asking a question about the document</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="chat-message">
              {/* User Message */}
              <div className="flex justify-end mb-4">
                <div className="max-w-xs lg:max-w-md bg-blue-500 text-white p-3 rounded-lg rounded-br-none">
                  <p className="text-sm">{msg.userMessage}</p>
                </div>
              </div>

              {/* AI Response */}
              <div className="flex justify-start mb-4">
                <div className="max-w-xs lg:max-w-md bg-gray-100 text-gray-800 p-3 rounded-lg rounded-bl-none">
                  <p className="text-sm">{msg.aiResponse}</p>
                  
                  {/* Sources */}
                  {msg.sourceChunks && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer text-gray-600 font-medium">
                        📚 Sources
                      </summary>
                      <div className="mt-2 bg-gray-50 p-2 rounded text-gray-700 max-h-32 overflow-y-auto">
                        {msg.sourceChunks.split('---').map((chunk) => (
                          <p key={`${msg.id}-${chunk.trim().substring(0, 20)}`} className="mb-1 pb-1 border-b border-gray-200 last:border-0">
                            {chunk.trim().substring(0, 100)}...
                          </p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 p-3 rounded-lg">
              <div className="typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question... (Shift+Enter for new line)"
            className="flex-1 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:border-blue-500"
            rows="2"
            disabled={loading}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg transition font-medium"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;

ChatWindow.propTypes = {
  sessionId: PropTypes.string.isRequired,
  documentId: PropTypes.number,
};
