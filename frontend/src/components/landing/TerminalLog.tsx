import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'C5-REAL' | 'EDG' | 'SYSTEM' | 'REPLAY';
  message: string;
}

export function TerminalLog({ logs }: { logs: LogEntry[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-500';
      case 'WARN': return 'text-yellow-500';
      case 'C5-REAL': return 'text-[#CCFF00] font-bold';
      case 'EDG': return 'text-[#2B3BE5] font-bold';
      case 'REPLAY': return 'text-[#10B981] font-bold';
      case 'SYSTEM': return 'text-gray-400';
      default: return 'text-[#10B981]';
    }
  };

  return (
    <div className="bg-[#050505] rounded-lg p-4 font-mono text-xs sm:text-sm border border-white/10 h-80 overflow-y-auto w-full shadow-inner">
      <div className="text-gray-500 mb-4 border-b border-white/5 pb-2 flex justify-between">
        <span><span className="text-[#CCFF00]">MOSKV-1 APEX KERNEL</span> :: LEDGER TELEMETRY TERMINAL</span>
        <span className="text-xs">v10.0-C5</span>
      </div>
      <div className="flex flex-col gap-1">
        {logs.map((log) => (
          <motion.div 
            key={log.id}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className={`whitespace-pre-wrap ${getColor(log.level)}`}
          >
            <span className="opacity-50 text-gray-500">[{log.timestamp}]</span> [{log.level}] {log.message}
          </motion.div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
