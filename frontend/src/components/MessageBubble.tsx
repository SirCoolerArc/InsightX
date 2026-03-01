'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Code, CheckCircle, AlertTriangle, FileText, BarChart3, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { Message } from '@/types';
import ChartRenderer from './ChartRenderer';
import { ExecutiveSummaryBox, InsightCardRenderer } from './InsightCards';

export default function MessageBubble({ message }: { message: Message }) {
    const isUser = message.role === 'user';
    const [showCode, setShowCode] = React.useState(false);
    const [showSteps, setShowSteps] = React.useState(false);

    console.log("Verdict Debug:", message.id, message.verdict);

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex w-full mb-8 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-4`}>
                {/* Avatar */}
                <div className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center shadow-sm ${isUser
                    ? 'bg-gradient-to-br from-slate-700 to-slate-900 border-2 border-white'
                    : 'bg-gradient-to-br from-indigo-500 to-violet-600 border-2 border-white'
                    }`}>
                    {isUser ? <User className="text-white w-5 h-5" /> : <Bot className="text-white w-5 h-5" />}
                </div>

                {/* Content Container */}
                <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} min-w-0`}>
                    <>
                        {/* Main Message Bubble */}
                        <div
                            className={`px-5 py-4 shadow-sm ${isUser
                                ? 'bg-slate-800 text-white rounded-2xl rounded-tr-sm'
                                : 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-sm prose prose-slate prose-p:leading-relaxed prose-a:text-indigo-600 max-w-none'
                                }`}
                        >
                            {isUser ? (
                                <p className="whitespace-pre-wrap">{message.content}</p>
                            ) : (
                                <div className="flex flex-col">
                                    {/* 1. Executive Summary Box */}
                                    {message.insight_summary && (
                                        <ExecutiveSummaryBox summary={message.insight_summary} />
                                    )}

                                    {/* 2. Insight Cards Grid */}
                                    {message.cards && message.cards.length > 0 && (
                                        <InsightCardRenderer cards={message.cards} />
                                    )}

                                    {/* 3. Render Chart if present */}
                                    {message.result?.raw_output?.chart && !message.isLoading && (
                                        <div className="mb-6">
                                            <ChartRenderer config={message.result.raw_output.chart} />
                                        </div>
                                    )}

                                    {/* 4. Full Narrative Text */}
                                    {message.content ? (
                                        <div className="mt-2 text-[15px] leading-relaxed text-slate-700">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {message.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : null}

                                    {message.isLoading && (
                                        <div className="flex flex-col mt-3 space-y-3 w-full max-w-sm">
                                            {message.completedProcesses?.map((proc, idx) => (
                                                <div key={`proc-${idx}-${proc}`} className="flex items-center text-sm text-slate-500">
                                                    <CheckCircle className="w-4 h-4 mr-2 text-emerald-500 shrink-0" />
                                                    <span className="truncate">{proc}</span>
                                                </div>
                                            ))}
                                            {message.activeProcess && (
                                                <div className="flex items-center text-sm text-indigo-600 font-medium">
                                                    <Loader2 className="w-4 h-4 mr-2 animate-spin text-indigo-500 shrink-0" />
                                                    <span className="truncate">{message.activeProcess}</span>
                                                    <div className="flex space-x-1 items-center ml-2 h-4 shrink-0">
                                                        <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                                        <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                                        <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
                                                    </div>
                                                </div>
                                            )}
                                            {!message.activeProcess && (
                                                <div className="flex space-x-2 items-center h-5 mt-2">
                                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Extras for Assistant (Code, Verification, Followups) */}
                        {!isUser && (
                            <div className="flex flex-col w-full mt-3 gap-3">

                                {/* Verification Badge */}
                                {message.verdict && message.verdict.judge_ran && (
                                    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium w-max border ${message.verdict.severity === 'high' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                        message.verdict.severity === 'medium' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                            'bg-emerald-50 text-emerald-700 border-emerald-200'
                                        }`}>
                                        {message.verdict.severity === 'high' ? <AlertTriangle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                                        Quality Verification: {message.verdict.severity === 'none' ? 'Passed' : 'Adjusted'}
                                    </div>
                                )}

                                {/* Expandable Meta Info (Code & Steps) */}
                                {(message.code || (message.steps && message.steps.length > 0)) && (
                                    <div className="flex flex-wrap gap-2 items-center">
                                        {message.code && (
                                            <button
                                                onClick={() => setShowCode(!showCode)}
                                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors text-xs font-medium border border-slate-200"
                                            >
                                                <Code className="w-3.5 h-3.5" />
                                                {showCode ? 'Hide Code' : 'View Code'}
                                                {showCode ? <ChevronDown className="w-3.5 h-3.5 ml-1" /> : <ChevronRight className="w-3.5 h-3.5 ml-1" />}
                                            </button>
                                        )}

                                        {message.steps && message.steps.length > 0 && (
                                            <button
                                                onClick={() => setShowSteps(!showSteps)}
                                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors text-xs font-medium border border-slate-200"
                                            >
                                                <FileText className="w-3.5 h-3.5" />
                                                Execution Trace ({message.steps.length})
                                                {showSteps ? <ChevronDown className="w-3.5 h-3.5 ml-1" /> : <ChevronRight className="w-3.5 h-3.5 ml-1" />}
                                            </button>
                                        )}
                                    </div>
                                )}


                                <AnimatePresence>
                                    {showCode && message.code && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="bg-slate-900 rounded-xl p-4 mt-1 border border-slate-700 w-full overflow-x-auto text-sm">
                                                <pre><code className="text-emerald-400">{message.code}</code></pre>
                                            </div>
                                        </motion.div>
                                    )}
                                    {showSteps && message.steps && message.steps.length > 0 && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="bg-slate-50 rounded-xl p-4 mt-1 border border-slate-200 w-full text-sm overflow-x-auto overflow-y-auto max-h-96 space-y-4">
                                                {message.steps.map((step, idx) => (
                                                    <div key={idx} className="border-b border-slate-200 last:border-0 pb-4 last:pb-0">
                                                        <div className="flex items-center gap-2 mb-2">
                                                            <span className="font-semibold text-slate-700">Iteration {step.iteration || (idx + 1)}</span>
                                                            <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${step.phase === 'success' ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' :
                                                                step.phase === 'error' ? 'bg-red-100 text-red-700 border border-red-200' :
                                                                    step.phase === 'execute' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                                                                        step.phase === 'fix' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                                                                            'bg-slate-200 text-slate-700 border border-slate-300'
                                                                }`}>
                                                                {step.phase || 'unknown'}
                                                            </span>
                                                        </div>
                                                        {step.code && (
                                                            <div className="bg-slate-900 p-3 rounded-lg border border-slate-700 mb-2 overflow-x-auto">
                                                                <pre><code className="text-xs text-emerald-400">{step.code}</code></pre>
                                                            </div>
                                                        )}
                                                        {step.error && (
                                                            <div className="text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200 overflow-x-auto whitespace-pre-wrap">
                                                                {step.error}
                                                            </div>
                                                        )}
                                                        {step.result && (
                                                            <div className="text-xs text-slate-800 bg-white p-3 rounded-lg border border-slate-200 overflow-x-auto">
                                                                <pre>{typeof step.result === 'object' ? JSON.stringify(step.result, null, 2) : String(step.result)}</pre>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        )}

                        {/* Always Visible Confidence Score (At the very bottom) */}
                        {!isUser && message.verdict?.confidence && (
                            <div className="flex w-full mt-2">
                                <div className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-500">
                                    Confidence: <span className="text-slate-700 font-semibold capitalize">{message.verdict.confidence}</span>
                                </div>
                            </div>
                        )}
                    </>
                </div>
            </div>
        </motion.div>
    );
}
