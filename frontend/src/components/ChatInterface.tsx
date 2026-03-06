'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Message } from '@/types';
import MessageBubble from './MessageBubble';
import WelcomeScreen from './WelcomeScreen';

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e?: React.FormEvent, presetInput?: string) => {
        e?.preventDefault();
        const query = presetInput || input;
        if (!query.trim() || isLoading) return;

        const userMsg: Message = {
            id: crypto.randomUUID(),
            role: 'user',
            content: query.trim(),
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        const tempId = crypto.randomUUID();
        setMessages(prev => [...prev, {
            id: tempId,
            role: 'assistant',
            content: '',
            isLoading: true,
            activeProcess: 'Warming up code interpreter...',
            completedProcesses: []
        }]);

        try {
            const response = await fetch('http://localhost:8080/api/query_stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query.trim(),
                    session_id: 'default-session'
                }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder('utf-8');

            if (!reader) {
                throw new Error('No reader available');
            }

            let done = false;
            let currentStepMessage = "Warming up code interpreter...";
            let processes: string[] = [];
            let buffer = '';

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;

                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    
                    // SSE events are separated by double newline
                    const parts = buffer.split('\n\n');
                    
                    // The last part might be incomplete, so keep it in the buffer
                    buffer = parts.pop() || '';

                    for (const eventBlock of parts) {
                        const lines = eventBlock.split('\n');
                        let dataStr = '';
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                dataStr += line.replace('data: ', '');
                            }
                        }

                        if (!dataStr.trim()) continue;

                        try {
                            const event = JSON.parse(dataStr);
                            if (event.type === 'status') {
                                if (currentStepMessage && currentStepMessage !== event.data.message) {
                                    processes = [...processes, currentStepMessage];
                                }
                                currentStepMessage = event.data.message;

                                setMessages(prev => prev.map(msg =>
                                    msg.id === tempId
                                        ? {
                                            ...msg,
                                            content: '',
                                            activeProcess: currentStepMessage,
                                            completedProcesses: processes,
                                            isLoading: true
                                        }
                                        : msg
                                ));
                            } else if (event.type === 'final') {
                                const { response: botText, insight_summary, cards, result, code, steps, verdict, followups } = event.data;

                                setMessages(prev => prev.map(msg =>
                                    msg.id === tempId
                                        ? {
                                            ...msg,
                                            content: botText,
                                            insight_summary,
                                            cards,
                                            result,
                                            code,
                                            steps,
                                            verdict,
                                            followups,
                                            isLoading: false
                                        }
                                        : msg
                                ));
                            } else if (event.type === 'error') {
                                setMessages(prev => prev.map(msg =>
                                    msg.id === tempId
                                        ? {
                                            ...msg,
                                            content: event.data.message,
                                            isLoading: false
                                        }
                                        : msg
                                ));
                            }
                        } catch (e) {
                            console.error("Error parsing SSE event data:", e, dataStr);
                        }
                    }
                }
            }

        } catch (error) {
            console.error(error);
            setMessages(prev => prev.map(msg =>
                msg.id === tempId
                    ? {
                        ...msg,
                        content: "I encountered an error connecting to the backend. Please ensure the FastAPI server is running.",
                        isLoading: false
                    }
                    : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-slate-50/50">
            <div className="flex-1 overflow-y-auto w-full scroll-smooth">
                {messages.length === 0 ? (
                    <WelcomeScreen onExampleClick={(q) => handleSubmit(undefined, q)} />
                ) : (
                    <div className="max-w-4xl mx-auto px-4 py-8 md:px-6">
                        {messages.map((msg) => (
                            <React.Fragment key={msg.id}>
                                <MessageBubble message={msg} />

                                {msg.role === 'assistant' && msg.followups && msg.followups.length > 0 && !msg.isLoading && (
                                    <div className="flex flex-wrap gap-2 mt-2 mb-8 ml-0 sm:ml-14">
                                        {msg.followups.map((f, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSubmit(undefined, f)}
                                                className="px-4 py-2 text-sm text-indigo-700 bg-indigo-50/80 hover:bg-indigo-100 rounded-full border border-indigo-100 transition-colors text-left"
                                            >
                                                {f}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </React.Fragment>
                        ))}
                        <div ref={bottomRef} className="h-[2px]" />
                    </div>
                )}
            </div>

            <div className="w-full bg-gradient-to-t from-slate-50 to-transparent relative pb-6 pt-6 px-4 md:px-0">
                <form
                    onSubmit={handleSubmit}
                    className="max-w-4xl mx-auto relative group"
                >
                    <div className="absolute inset-0 bg-indigo-500/10 rounded-[28px] blur-xl group-hover:bg-indigo-500/15 transition-colors duration-500" />
                    <div className="relative flex items-end w-full bg-white rounded-3xl border border-slate-200 shadow-sm focus-within:border-indigo-400 focus-within:ring-[3px] focus-within:ring-indigo-100 transition-all overflow-hidden pl-5 pr-2 py-2 text-base">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                            placeholder="Ask anything about the transaction data..."
                            className="w-full min-h-[48px] max-h-48 bg-transparent resize-none outline-none py-3 text-slate-800 placeholder:text-slate-400 font-sans leading-relaxed"
                            rows={input.split('\n').length > 1 ? Math.min(input.split('\n').length, 5) : 1}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading}
                            className="ml-2 mb-1.5 inline-flex items-center justify-center min-w-[44px] h-[44px] rounded-2xl bg-indigo-600 text-white disabled:bg-slate-100 disabled:text-slate-400 hover:bg-indigo-700 transition-colors shadow-sm"
                        >
                            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                        </button>
                    </div>
                    <div className="text-center mt-3 text-xs text-slate-400 font-medium tracking-wide">
                        BRAIN-DS can make mistakes. Consider verifying important metrics.
                    </div>
                </form>
            </div>
        </div>
    );
}
