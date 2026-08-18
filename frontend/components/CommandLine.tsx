"use client";

import { useState } from "react";

const VALID = ["btc", "eth", "sol", "bnb", "xrp"];

interface CommandLineProps {
  onPredict: (ticker: string) => void;
}

export default function CommandLine({ onPredict }: CommandLineProps) {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState<string[]>([
    "Type HELP for commands. e.g. > PRED SOL",
  ]);

  const run = (raw: string) => {
    const line = raw.trim();
    if (!line) return;

    const parts = line.toUpperCase().split(/\s+/);
    const cmd = parts[0];
    const arg = parts[1]?.toLowerCase();

    if (cmd === "CLEAR") {
      setOutput([]);
      setInput("");
      return;
    }

    let reply = "";
    if (cmd === "PRED") {
      if (arg && VALID.includes(arg)) {
        reply = `Running prediction for ${arg.toUpperCase()}…`;
        onPredict(arg);
      } else {
        reply = `Unknown ticker. Available: ${VALID.join(", ").toUpperCase()}`;
      }
    } else if (cmd === "HELP") {
      reply = "Commands: PRED <ticker> · TICKERS · CLEAR";
    } else if (cmd === "TICKERS") {
      reply = `Available: ${VALID.join(", ").toUpperCase()}`;
    } else {
      reply = `Unknown command '${cmd}'. Type HELP.`;
    }

    setOutput((prev) =>
      [...prev.slice(-4), `> ${line}`, reply].filter(Boolean),
    );
    setInput("");
  };

  return (
    <div className="border-t border-noir-line bg-black">
      {output.length > 0 && (
        <div className="max-h-20 overflow-y-auto px-3 pt-1 font-mono text-[10px] leading-tight text-noir-muted">
          {output.map((line, i) => (
            <div
              key={i}
              className={line.startsWith(">") ? "text-noir-amber" : undefined}
            >
              {line}
            </div>
          ))}
        </div>
      )}
      <form
        className="flex items-center gap-2 px-3 py-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          run(input);
        }}
      >
        <span className="font-mono text-xs font-bold text-noir-amber">&gt;</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="PRED SOL"
          autoComplete="off"
          spellCheck={false}
          className="flex-1 bg-transparent font-mono text-xs text-noir-text placeholder-noir-dim focus:outline-none"
        />
        <span className="hidden text-[9px] uppercase tracking-wider text-noir-dim sm:inline">
          type a command
        </span>
      </form>
    </div>
  );
}
