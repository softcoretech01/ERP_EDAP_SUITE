import { Menu, Database, ChevronDown } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

export const Navbar = () => {
  const { toggleSidebar, activeConnection } = useAppStore();

  return (
    <header className="h-16 glass border-b border-slate-700 flex items-center justify-between px-4 z-10 sticky top-0">
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleSidebar}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="font-semibold text-lg">
          Dashboard
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-sm">
          <Database className="w-4 h-4 text-brand-400" />
          <span className="text-slate-300">
            {activeConnection ? activeConnection.name : "No DB Selected"}
          </span>
          <ChevronDown className="w-4 h-4 text-slate-500 ml-2" />
        </div>
      </div>
    </header>
  );
};
