import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatState {
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
      clearMessages: () => set({ messages: [] }),
    }),
    { name: 'Coding-chat-storage' }
  )
)
