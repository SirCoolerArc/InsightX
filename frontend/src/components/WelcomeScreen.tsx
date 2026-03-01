'use client';

import { motion } from 'framer-motion';

export default function WelcomeScreen({ onExampleClick }: { onExampleClick: (q: string) => void }) {
    const examples = [
        "Which transaction type has the highest failure rate?",
        "What is the average transaction amount for bill payments?",
        "How do failure rates compare between Android and iOS users?",
        "What percentage of high-value transactions are flagged for review?"
    ];

    return (
        <div className="flex flex-col items-center justify-center h-full max-w-3xl mx-auto px-6 pt-12 pb-24 text-center">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="h-20 w-20 mx-auto bg-white shadow-xl shadow-indigo-100 rounded-3xl flex items-center justify-center mb-6">
                    <span className="text-4xl">⚡</span>
                </div>
                <h1 className="text-4xl font-bold text-slate-800 tracking-tight mb-4">
                    Leadership Analytics
                </h1>
                <p className="text-lg text-slate-500 mb-12 max-w-xl mx-auto">
                    Ask questions about your digital payment transactions in natural language and receive data-backed insights instantly.
                </p>
            </motion.div>

            <motion.div
                className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
            >
                {examples.map((example, i) => (
                    <button
                        key={i}
                        onClick={() => onExampleClick(example)}
                        className="flex flex-col text-left p-4 rounded-2xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-md hover:shadow-indigo-50 transition-all duration-200 group"
                    >
                        <span className="text-sm text-indigo-500 font-semibold mb-1 group-hover:text-indigo-600">Try asking</span>
                        <span className="text-slate-700 leading-snug">{example}</span>
                    </button>
                ))}
            </motion.div>
        </div>
    );
}
