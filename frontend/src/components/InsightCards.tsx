import React from 'react';
import { Target, CheckCircle2, AlertCircle, Info, ChevronRight } from 'lucide-react';

const CardContainer = ({ children, title }: { children: React.ReactNode; title?: string }) => (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all hover:border-slate-300 w-full">
        {title && (
            <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2 shrink-0">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                <h4 className="text-xs font-semibold tracking-widest text-slate-600 uppercase">{title}</h4>
            </div>
        )}
        <div className="p-4">
            {children}
        </div>
    </div>
);

export const ExecutiveSummaryBox = ({ summary }: { summary: string }) => {
    if (!summary) return null;
    return (
        <div className="relative mb-6 p-[0.5px] rounded-xl bg-gradient-to-r from-indigo-200 via-purple-200 to-indigo-200 shadow-sm">
            <div className="bg-white rounded-xl p-5 relative overflow-hidden h-full">
                <div className="absolute -top-4 -right-4 p-4 opacity-[0.03]">
                    <Target className="w-32 h-32 text-indigo-600" />
                </div>
                <div className="relative z-10 flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-indigo-50 border border-indigo-100/50 rounded-md">
                            <Target className="w-4 h-4 text-indigo-600" />
                        </div>
                        <h3 className="text-[11px] font-bold tracking-widest text-indigo-600 uppercase">Executive Summary</h3>
                    </div>
                    <p className="text-slate-700 text-[15px] leading-relaxed font-medium">{summary}</p>
                </div>
            </div>
        </div>
    );
};

export const MetricGroupCard = ({ card }: { card: any }) => {
    return (
        <CardContainer title={card.title}>
            <div className="flex flex-wrap gap-6">
                {card.metrics?.map((m: any, idx: number) => (
                    <div key={idx} className="flex flex-col min-w-[120px]">
                        <span className="text-slate-500 flex items-center gap-1.5 text-xs font-medium mb-1.5 uppercase tracking-wider">
                            {m.status === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                            {m.status === 'warning' && <AlertCircle className="w-3.5 h-3.5 text-amber-500" />}
                            {m.status === 'error' && <AlertCircle className="w-3.5 h-3.5 text-rose-500" />}
                            {(m.status === 'none' || m.status === 'neutral' || !m.status) && <Info className="w-3.5 h-3.5 text-slate-400" />}
                            {m.label}
                        </span>
                        <div className="flex items-baseline gap-2">
                            <span className="text-3xl font-mono tracking-tight text-slate-800">{m.value}</span>
                        </div>
                    </div>
                ))}
            </div>
        </CardContainer>
    );
};

export const InsightListCard = ({ card }: { card: any }) => {
    return (
        <CardContainer title={card.title}>
            <div className="flex flex-col gap-3">
                {card.items?.map((item: any, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                        <div className="mt-0.5">
                            {item.status === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> :
                                item.status === 'warning' ? <AlertCircle className="w-4 h-4 text-amber-500" /> :
                                    item.status === 'error' ? <AlertCircle className="w-4 h-4 text-rose-500" /> :
                                        <ChevronRight className="w-4 h-4 text-indigo-500" />}
                        </div>
                        <div className="flex flex-col gap-1">
                            <span className="text-sm font-semibold text-slate-800">{item.title}</span>
                            <span className="text-xs text-slate-600 leading-snug">{item.description}</span>
                        </div>
                    </div>
                ))}
            </div>
        </CardContainer>
    );
};

export const KeyValueCard = ({ card }: { card: any }) => {
    return (
        <CardContainer title={card.title}>
            <div className="flex flex-col gap-6">
                {card.sections?.map((section: any, idx: number) => (
                    <div key={idx} className="flex flex-col gap-2">
                        {section.title && <h5 className="text-xs font-medium text-indigo-600 uppercase tracking-widest mb-1">{section.title}</h5>}
                        <div className="flex flex-col gap-y-2">
                            {section.items?.map((item: any, itemIdx: number) => (
                                <div key={itemIdx} className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-2 border-b border-slate-100 gap-1 sm:gap-4 last:border-0">
                                    <span className="text-sm text-slate-600 font-medium">{item.label}</span>
                                    <span className="text-sm font-mono font-medium text-slate-700 bg-slate-100 px-2.5 py-1 rounded w-fit">{item.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </CardContainer>
    );
};

export const InsightCardRenderer = ({ cards }: { cards: any[] }) => {
    if (!cards || cards.length === 0) return null;

    return (
        <div className="columns-1 md:columns-2 gap-4 mb-6">
            {cards.map((card, idx) => (
                <div key={idx} className="break-inside-avoid mb-4 w-full">
                    <div className="w-full">
                        {card.type === 'metric_group' && <MetricGroupCard card={card} />}
                        {card.type === 'insight_list' && <InsightListCard card={card} />}
                        {card.type === 'key_value' && <KeyValueCard card={card} />}
                    </div>
                </div>
            ))}
        </div>
    );
};
