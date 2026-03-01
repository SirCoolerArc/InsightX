"use client";

import React from 'react';
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface ChartConfig {
    type: 'line' | 'bar' | 'pie';
    data: any[];
    xKey: string;
    yKey: string;
    title?: string;
}

const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e', '#6366f1'];

interface ChartRendererProps {
    config: ChartConfig;
}

export default function ChartRenderer({ config }: ChartRendererProps) {
    if (!config || !config.data || config.data.length === 0) return null;

    const { type, data, xKey, yKey, title } = config;

    const renderChart = () => {
        switch (type) {
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                            <XAxis
                                dataKey={xKey}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                dy={10}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                dx={-10}
                            />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                            />
                            <Legend wrapperStyle={{ paddingTop: '20px' }} />
                            <Line type="monotone" dataKey={yKey} stroke="#0ea5e9" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 40 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                            <XAxis
                                dataKey={xKey}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#6b7280', fontSize: 11 }}
                                dy={15}
                                angle={-35}
                                textAnchor="end"
                                interval={0}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                dx={-10}
                            />
                            <Tooltip
                                cursor={{ fill: '#f3f4f6' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                            />
                            <Legend wrapperStyle={{ paddingTop: '20px' }} />
                            <Bar dataKey={yKey} fill="#8b5cf6" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                    </ResponsiveContainer>
                );
            case 'pie':
                return (
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                            />
                            <Legend layout="vertical" verticalAlign="middle" align="right" />
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                outerRadius={80}
                                dataKey={yKey}
                                nameKey={xKey}
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                        </PieChart>
                    </ResponsiveContainer>
                );
            default:
                return null;
        }
    };

    return (
        <div className="w-full bg-white border border-gray-100 rounded-xl p-4 my-4 shadow-sm overflow-hidden">
            {title && <h4 className="text-sm font-semibold text-gray-700 mb-4">{title}</h4>}
            {renderChart()}
        </div>
    );
}
