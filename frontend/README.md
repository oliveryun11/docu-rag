# DocuRAG Frontend - Next.js Chat Interface

A modern, responsive chat interface for the DocuRAG system built with Next.js, TypeScript, and Tailwind CSS.

## 🚀 Features

- **Modern Chat Interface**: Clean, intuitive design similar to ChatGPT
- **Real-time Search**: Instant responses from your RAG backend
- **Source Attribution**: View documents and chunks used to generate answers
- **Related Questions**: AI-generated follow-up questions
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Error Handling**: Graceful handling of connection and API errors
- **Loading States**: Visual feedback during search operations

## 🛠️ Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **State Management**: React hooks (useState, useEffect)

## 📦 Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
npm start
```

## 🔧 Configuration

Create a `.env.local` file in the frontend directory:

```env
# Backend API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## 🎯 Usage

### Starting the Application

1. **Start the Backend**: Make sure your FastAPI backend is running on `http://localhost:8000`
2. **Start the Frontend**: Run `npm run dev` and open `http://localhost:3000`

### Chat Interface Features

#### **Welcome Screen**
- Example questions to get started
- Clean, inviting interface
- Helpful prompts for new users

#### **Chat Messages**
- User messages displayed on the right with blue styling
- Assistant responses on the left with source citations
- Timestamps and loading indicators

#### **Source Attribution**
Every assistant response includes:
- Document names and similarity scores
- Content previews from relevant chunks
- Visual indicators for source quality

#### **Related Questions**
- AI-generated follow-up questions
- Click to automatically ask related questions
- Contextual suggestions based on current topic

#### **Error Handling**
- Connection status monitoring
- Graceful error messages
- Retry mechanisms for failed requests

## 🔌 API Integration

The frontend communicates with the backend through:

### **RAG Search Endpoint**
```typescript
POST /api/v1/search/
{
  "query": "How do I create a Next.js app?",
  "k": 5,
  "include_related_questions": true
}
```

### **Health Check**
```typescript
GET /health
```

### **API Client**
The `apiClient` in `src/lib/api.ts` handles all backend communication with:
- Automatic error handling
- Type-safe requests and responses
- Configurable endpoints

## 📱 Components

### **Core Components**

- **`ChatInterface`**: Main container managing chat state
- **`ChatMessage`**: Individual message display with sources
- **`ChatInput`**: Message input with send functionality
- **`Button`**: Reusable UI component

### **Component Structure**
```
src/
├── components/
│   ├── chat/
│   │   ├── chat-interface.tsx    # Main chat container
│   │   ├── chat-message.tsx      # Message display
│   │   └── chat-input.tsx        # Input component
│   └── ui/
│       └── button.tsx            # Reusable button
├── lib/
│   ├── api.ts                    # API client
│   └── utils.ts                  # Utility functions
└── types/
    └── api.ts                    # TypeScript interfaces
```

## 🎨 Styling

### **Tailwind CSS**
- Utility-first CSS framework
- Custom components with consistent design
- Responsive design patterns
- Dark mode ready (not implemented yet)

### **Custom Styles**
- Line clamping for text truncation
- Custom scrollbars for better UX
- Prose styling for formatted content
- Loading animations and transitions

## 🔍 Features in Detail

### **Message Flow**
1. User types question
2. Message appears immediately
3. Loading indicator shows
4. API request sent to backend
5. Response with sources and related questions
6. Auto-scroll to latest message

### **Error States**
- **Backend Disconnected**: Full-screen error with retry button
- **API Errors**: Inline error messages with context
- **Network Issues**: Graceful degradation with user feedback

### **Performance**
- Optimistic UI updates
- Efficient re-renders with React keys
- Lazy loading of components
- Minimal bundle size

## 🚀 Deployment

### **Build**
```bash
npm run build
```

### **Deploy to Vercel**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### **Environment Variables**
Set `NEXT_PUBLIC_API_BASE_URL` in your deployment environment.

## 🐛 Troubleshooting

### **Common Issues**

**"Cannot connect to backend"**
- Ensure FastAPI server is running on port 8000
- Check `.env.local` has correct API URL
- Verify CORS settings in backend

**"Module not found errors"**
- Run `npm install` to install dependencies
- Check import paths are correct
- Ensure TypeScript configuration is valid

**"Build errors"**
- Run `npm run lint` to check for linting issues
- Ensure all TypeScript types are properly defined
- Check for unused imports

### **Debug Mode**
Open browser dev tools and check:
- Network tab for API requests
- Console for JavaScript errors
- Application tab for local storage

## 🔮 Future Enhancements

### **Planned Features**
- [ ] Dark mode toggle
- [ ] Chat history persistence
- [ ] Export chat conversations
- [ ] Voice input/output
- [ ] File upload for document analysis
- [ ] User authentication
- [ ] Conversation branching
- [ ] Search within chat history

### **Technical Improvements**
- [ ] PWA capabilities
- [ ] Offline support
- [ ] Performance monitoring
- [ ] Automated testing
- [ ] Storybook component library

## 🤝 Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Include responsive design considerations
4. Test on multiple browsers and devices
5. Update this README for new features

---

🎉 **Happy Chatting!** Your Next.js documentation is now accessible through an intuitive chat interface.
