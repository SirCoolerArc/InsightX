export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    result?: any;
    code?: string;
    followups?: string[];
    steps?: any[];
    verdict?: any;
    insight_summary?: string;
    cards?: any[];
    isLoading?: boolean;
    activeProcess?: string;
    completedProcesses?: string[];
}
