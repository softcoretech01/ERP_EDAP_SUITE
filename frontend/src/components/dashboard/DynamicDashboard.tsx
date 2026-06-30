import React from 'react';
import { ChartRenderer } from '../ChartRenderer';

interface DynamicDashboardProps {
  result: {
    title?: string;
    chartType: 'bar' | 'line' | 'pie' | 'table' | 'kpi';
    summary?: string;
    data: {
      labels: string[];
      datasets: {
        label: string;
        data: number[];
        formattedValue?: string;
      }[];
    };
  } | null;
}

const ErrorCard = ({ message }: { message: string }) => (
  <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm flex items-center gap-2 shadow-sm">
    <span>⚠️</span> {message}
  </div>
);

export const DynamicDashboard: React.FC<DynamicDashboardProps> = ({ result }) => {
  if (!result) return null;

  if (!result?.data?.labels || !result?.data?.datasets) {
    return <ErrorCard message="Invalid dashboard data received from AI." />;
  }

  return (
    <div className="space-y-4">
      {result.title && result.chartType !== 'kpi' && (
        <div className="text-lg font-semibold text-[#0d0d0d] mb-4">
          {result.title}
        </div>
      )}
      <ChartRenderer type={result.chartType} data={result.data} />
      {result.summary && result.chartType !== 'kpi' && (
        <div className="text-sm text-[#6b6b6b] mt-4 border-t border-[#e5e5e5] pt-3 italic">
          {result.summary}
        </div>
      )}
    </div>
  );
};
