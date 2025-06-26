'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage } from './chat-message';
import { ChatInput } from './chat-input';
import { ChatMessage as ChatMessageType } from '@/types/api';
import { apiClient } from '@/lib/api';
import { v4 as uuidv4 } from 'uuid';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

const EXAMPLE_QUESTIONS = [
  "What is the relationship between reason and experience in human knowledge?",
  "How does the categorical imperative guide moral action?",
  "What are the conditions that make synthetic a priori judgments possible?",
  "How does pure reason differ from practical reason?",
  "What is the nature of space and time in human perception?",
];

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check backend connection on mount
  useEffect(() => {
    checkConnection();
  }, []);

  // Handle custom question events from related questions
  useEffect(() => {
    const handleAskQuestion = (event: any) => {
      if (event.detail?.question) {
        handleSendMessage(event.detail.question);
      }
    };

    window.addEventListener('askQuestion', handleAskQuestion);
    return () => {
      window.removeEventListener('askQuestion', handleAskQuestion);
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkConnection = async () => {
    try {
      await apiClient.healthCheck();
      setIsConnected(true);
      setError(null);
    } catch (err) {
      setIsConnected(false);
      setError('Cannot connect to backend. Make sure the FastAPI server is running on http://localhost:8000');
    }
  };

  const handleSendMessage = async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage: ChatMessageType = {
      id: uuidv4(),
      type: 'user',
      content: messageText,
      timestamp: new Date(),
    };

    const loadingMessage: ChatMessageType = {
      id: uuidv4(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.search({
        query: messageText,
        k: 5,
        include_related_questions: true,
      });

      const assistantMessage: ChatMessageType = {
        id: uuidv4(),
        type: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        sources: response.sources,
        relatedQuestions: response.related_questions,
      };

      // Replace loading message with actual response
      setMessages(prev => prev.slice(0, -1).concat(assistantMessage));
    } catch (err) {
      const errorMessage: ChatMessageType = {
        id: uuidv4(),
        type: 'assistant',
        content: `I apologize, but I encountered an error while processing your request: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date(),
      };

      setMessages(prev => prev.slice(0, -1).concat(errorMessage));
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleQuestion = (question: string) => {
    handleSendMessage(question);
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  if (!isConnected) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8 bg-white rounded-lg border border-gray-200 max-w-md">
          <AlertCircle className="mx-auto mb-4 text-red-500" size={48} />
          <h2 className="text-xl font-semibold mb-2">Backend Connection Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Button onClick={checkConnection} className="gap-2">
            <RefreshCw size={16} />
            Retry Connection
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">Philosophical Inquiry with Immanuel Kant</h1>
            <p className="text-sm text-gray-600">Explore the depths of critical philosophy</p>
          </div>
          {messages.length > 0 && (
            <Button variant="outline" onClick={clearChat} size="sm">
              Clear Chat
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-8 max-w-2xl">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800">
                Greetings, Fellow Seeker of Wisdom! 🧠
              </h2>
              <p className="text-gray-600 mb-6">
                I am Immanuel Kant, ready to engage in philosophical discourse with you. Ask me about reason, morality, knowledge, or any matter that concerns the human condition and our understanding of the world.
              </p>
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700 mb-3">Consider these fundamental philosophical inquiries:</p>
                <div className="grid gap-2">
                  {EXAMPLE_QUESTIONS.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleQuestion(question)}
                      className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors text-sm text-gray-700"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-0">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
} 