'use client';

import React from 'react';
import { ChatMessage as ChatMessageType } from '@/types/api';
import { formatRelativeTime } from '@/lib/utils';
import { User, Bot, Clock, FileText } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-3 p-4 ${isUser ? 'bg-blue-50' : 'bg-gray-50'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-blue-500 text-white' : 'bg-gray-600 text-white'
      }`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      
      <div className="flex-1 space-y-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span className="font-medium">{isUser ? 'You' : 'Kant'}</span>
          <Clock size={12} />
          <span>{formatRelativeTime(message.timestamp)}</span>
        </div>
        
        {message.isLoading ? (
          <div className="flex items-center gap-2 text-gray-600">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-blue-500"></div>
            <span>Searching knowledge base...</span>
          </div>
        ) : (
          <div className="prose max-w-none">
            <div className="whitespace-pre-wrap text-gray-800">{message.content}</div>
            
            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 space-y-2">
                <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <FileText size={16} />
                  Sources ({message.sources.length})
                </h4>
                <div className="space-y-2">
                  {message.sources.slice(0, 3).map((source, index) => (
                    <div key={`${source.document_id}-${source.chunk_index}`} 
                         className="bg-white border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-blue-600">
                          {source.document_title || source.file_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {Math.round(source.similarity_score * 100)}% match
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">
                        {source.content_preview}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Related Questions */}
            {message.relatedQuestions && message.relatedQuestions.length > 0 && (
              <div className="mt-4 space-y-2">
                <h4 className="text-sm font-semibold text-gray-700">Related Questions</h4>
                <div className="space-y-1">
                  {message.relatedQuestions.map((question, index) => (
                    <button
                      key={index}
                      className="block w-full text-left text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded"
                      onClick={() => {
                        // This will be handled by the parent component
                        const event = new CustomEvent('askQuestion', { 
                          detail: { question } 
                        });
                        window.dispatchEvent(event);
                      }}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 