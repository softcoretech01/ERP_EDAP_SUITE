import React from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

interface ChartProps {
  type: 'bar' | 'line' | 'pie' | 'table' | 'kpi';
  data: any;
}

const COLORS = ['#10a37f', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'];

export const ChartRenderer: React.FC<ChartProps> = ({ type, data }) => {
  if (!data || !data.labels || !data.datasets || data.datasets.length === 0) {
    return <div className="text-slate-400 italic">No chart data available.</div>;
  }

  // Handle KPI rendering
  if (type === 'kpi') {
    const value = data.datasets[0].formattedValue || data.datasets[0].data[0];
    const label = data.labels[0] || data.datasets[0].label;
    
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-gradient-to-br from-[#f9f9f9] to-white border border-[#e5e5e5] rounded-3xl shadow-sm min-h-[250px]">
        <div className="w-12 h-12 bg-[#10a37f]/10 rounded-2xl flex items-center justify-center mb-6">
          <TrendingUp className="w-6 h-6 text-[#10a37f]" />
        </div>
        <div className="text-4xl md:text-5xl font-bold text-[#0d0d0d] tracking-tight mb-2">
          {value}
        </div>
        <div className="text-sm font-medium text-[#6b6b6b] uppercase tracking-wider">
          {label}
        </div>
      </div>
    );
  }

  const chartData = data.labels.map((label: string, index: number) => {
    const item: any = { name: label };
    data.datasets.forEach((dataset: any, dsIndex: number) => {
      item[dataset.label || `Series ${dsIndex+1}`] = dataset.data[index];
    });
    return item;
  });

  const seriesNames = data.datasets.map((d: any, i: number) => d.label || `Series ${i+1}`);

  if (type === 'table') {
    return (
      <div className="overflow-x-auto rounded-xl border border-[#e5e5e5]">
        <table className="w-full text-sm text-left text-[#0d0d0d]">
          <thead className="text-xs uppercase bg-[#f4f4f4] text-[#6b6b6b] border-b border-[#e5e5e5]">
            <tr>
              <th className="px-4 py-3">Label</th>
              {seriesNames.map((name: string) => <th key={name} className="px-4 py-3">{name}</th>)}
            </tr>
          </thead>
          <tbody>
            {chartData.map((row: any, i: number) => (
              <tr key={i} className="border-b border-[#e5e5e5] hover:bg-[#f9f9f9] transition-colors">
                <td className="px-4 py-3 font-medium">{row.name}</td>
                {seriesNames.map((name: string) => <td key={name} className="px-4 py-3">{row[name]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="h-[350px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        {type === 'bar' ? (
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
            <defs>
              <linearGradient id="colorBar" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10a37f" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#10a37f" stopOpacity={0.4}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
            <XAxis dataKey="name" stroke="#6b6b6b" tick={{ fill: '#6b6b6b', fontSize: 12 }} tickLine={false} axisLine={{ stroke: '#e5e5e5' }} />
            <YAxis stroke="#6b6b6b" tick={{ fill: '#6b6b6b', fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e5e5e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} 
              itemStyle={{ color: '#0d0d0d', fontWeight: 600 }}
              labelStyle={{ color: '#6b6b6b', marginBottom: '4px' }}
              cursor={{ fill: '#f4f4f4' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {seriesNames.map((name: string, _i: number) => (
              <Bar key={name} dataKey={name} fill={`url(#colorBar)`} radius={[6, 6, 0, 0]} barSize={40} />
            ))}
          </BarChart>
        ) : type === 'line' ? (
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
            <defs>
              <linearGradient id="colorLine" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" vertical={false} />
            <XAxis dataKey="name" stroke="#6b6b6b" tick={{ fill: '#6b6b6b', fontSize: 12 }} tickLine={false} axisLine={{ stroke: '#e5e5e5' }} />
            <YAxis stroke="#6b6b6b" tick={{ fill: '#6b6b6b', fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e5e5e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} 
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {seriesNames.map((name: string, _i: number) => (
              <Line key={name} type="monotone" dataKey={name} stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, fill: '#3b82f6', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
            ))}
          </LineChart>
        ) : type === 'pie' ? (
          <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            <Tooltip 
              contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e5e5e5', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} 
              itemStyle={{ color: '#0d0d0d', fontWeight: 600 }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            <Pie data={chartData} dataKey={seriesNames[0]} nameKey="name" cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={2} label={false}>
              {chartData.map((_: any, index: number) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="none" />
              ))}
            </Pie>
          </PieChart>
        ) : <div/>}
      </ResponsiveContainer>
    </div>
  );
};
