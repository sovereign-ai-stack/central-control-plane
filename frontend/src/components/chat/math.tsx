"use client";

import * as React from "react";

type MathSegment = {
  value: string;
  display: boolean;
  math: boolean;
};

type FormulaArgument = {
  value: string;
  next: number;
};

const symbols: Record<string, string> = {
  alpha: "α",
  beta: "β",
  chi: "χ",
  delta: "δ",
  epsilon: "ϵ",
  eta: "η",
  gamma: "γ",
  infty: "∞",
  lambda: "λ",
  leftrightarrow: "↔",
  leftarrow: "←",
  le: "≤",
  mu: "μ",
  nabla: "∇",
  neq: "≠",
  omega: "ω",
  partial: "∂",
  phi: "φ",
  pi: "π",
  pm: "±",
  propto: "∝",
  psi: "ψ",
  rho: "ρ",
  rightarrow: "→",
  sigma: "σ",
  sqrt: "√",
  sum: "∑",
  tau: "τ",
  theta: "θ",
  times: "×",
  to: "→",
  union: "∪",
  vee: "∨",
  wedge: "∧",
  xi: "ξ",
  zeta: "ζ",
  cdot: "·",
  div: "÷",
  ge: "≥",
  in: "∈",
  lnot: "¬",
  mid: "∣",
  odot: "⊙",
  otimes: "⊗",
};

const spacingCommands = new Set([
  ",",
  ";",
  ":",
  "!",
  "quad",
  "qquad",
  "enspace",
  "hspace",
]);

function findGroupEnd(source: string, start: number, open: string, close: string) {
  let depth = 0;

  for (let index = start; index < source.length; index += 1) {
    if (source[index] === "\\") {
      index += 1;
      continue;
    }

    if (source[index] === open) depth += 1;
    if (source[index] === close) {
      depth -= 1;
      if (depth === 0) return index;
    }
  }

  return -1;
}

function readDelimited(source: string, start: number, open: string, close: string): FormulaArgument | null {
  if (source[start] !== open) return null;

  const end = findGroupEnd(source, start, open, close);
  if (end < 0) return null;

  return {
    value: source.slice(start + 1, end),
    next: end + 1,
  };
}

function readArgument(source: string, start: number, optional = false): FormulaArgument | null {
  let index = start;
  while (/\s/.test(source[index] || "")) index += 1;

  const open = optional ? "[" : "{";
  const close = optional ? "]" : "}";
  const group = readDelimited(source, index, open, close);
  if (group) return group;

  if (source[index] === "\\") {
    const command = readCommand(source, index);
    return command ? { value: source.slice(index, command.next), next: command.next } : null;
  }

  if (index >= source.length) return null;
  return { value: source[index], next: index + 1 };
}

function readCommand(source: string, start: number) {
  if (source[start] !== "\\") return null;

  let next = start + 1;
  if (/[A-Za-z]/.test(source[next] || "")) {
    while (/[A-Za-z]/.test(source[next] || "")) next += 1;
  } else {
    next += 1;
  }

  return {
    name: source.slice(start + 1, next),
    next,
  };
}

function renderFormula(source: string, keyPrefix = "formula"): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let index = 0;

  while (index < source.length) {
    const character = source[index];

    if (character === "^" || character === "_") {
      const argument = readArgument(source, index + 1);
      if (!argument) {
        nodes.push(character);
        index += 1;
        continue;
      }

      const previous = nodes.pop();
      const script = character === "^" ? (
        <sup key={`${keyPrefix}-sup-${index}`}>
          {renderFormula(argument.value, `${keyPrefix}-sup-${index}`)}
        </sup>
      ) : (
        <sub key={`${keyPrefix}-sub-${index}`}>
          {renderFormula(argument.value, `${keyPrefix}-sub-${index}`)}
        </sub>
      );

      if (previous === undefined) {
        nodes.push(script);
      } else {
        nodes.push(
          <span className="math-scripted" key={`${keyPrefix}-script-${index}`}>
            <span className="math-base">{previous}</span>
            {script}
          </span>
        );
      }

      index = argument.next;
      continue;
    }

    if (character === "{") {
      const argument = readDelimited(source, index, "{", "}");
      if (argument) {
        nodes.push(
          <React.Fragment key={`${keyPrefix}-group-${index}`}>
            {renderFormula(argument.value, `${keyPrefix}-group-${index}`)}
          </React.Fragment>
        );
        index = argument.next;
        continue;
      }
    }

    if (character === "\\") {
      const command = readCommand(source, index);
      if (!command) {
        nodes.push(character);
        index += 1;
        continue;
      }

      if (command.name === "frac" || command.name === "dfrac" || command.name === "tfrac") {
        const numerator = readArgument(source, command.next);
        const denominator = numerator ? readArgument(source, numerator.next) : null;
        if (numerator && denominator) {
          nodes.push(
            <span className="math-fraction" key={`${keyPrefix}-fraction-${index}`}>
              <span className="math-numerator">
                {renderFormula(numerator.value, `${keyPrefix}-numerator-${index}`)}
              </span>
              <span className="math-denominator">
                {renderFormula(denominator.value, `${keyPrefix}-denominator-${index}`)}
              </span>
            </span>
          );
          index = denominator.next;
          continue;
        }
      }

      if (command.name === "sqrt") {
        const optionalIndex = readArgument(source, command.next, true);
        const argument = readArgument(source, optionalIndex?.next ?? command.next);
        if (argument) {
          nodes.push(
            <span className="math-root" key={`${keyPrefix}-sqrt-${index}`}>
              <span className="math-root-symbol">√</span>
              <span className="math-root-content">
                {renderFormula(argument.value, `${keyPrefix}-sqrt-${index}`)}
              </span>
            </span>
          );
          index = argument.next;
          continue;
        }
      }

      if (["mathbf", "boldsymbol", "bm"].includes(command.name)) {
        const argument = readArgument(source, command.next);
        if (argument) {
          nodes.push(
            <span className="math-bold" key={`${keyPrefix}-bold-${index}`}>
              {renderFormula(argument.value, `${keyPrefix}-bold-${index}`)}
            </span>
          );
          index = argument.next;
          continue;
        }
      }

      if (["mathbb", "mathfrak", "mathcal", "mathrm", "operatorname"].includes(command.name)) {
        const argument = readArgument(source, command.next);
        if (argument) {
          nodes.push(
            <span
              className={
                command.name === "mathbb"
                  ? "math-blackboard"
                  : command.name === "mathrm" || command.name === "operatorname"
                    ? "math-roman"
                    : "math-script"
              }
              key={`${keyPrefix}-${command.name}-${index}`}
            >
              {renderFormula(argument.value, `${keyPrefix}-${command.name}-${index}`)}
            </span>
          );
          index = argument.next;
          continue;
        }
      }

      if (["text", "textnormal", "mbox"].includes(command.name)) {
        const argument = readArgument(source, command.next);
        if (argument) {
          nodes.push(
            <span className="math-text" key={`${keyPrefix}-text-${index}`}>
              {argument.value}
            </span>
          );
          index = argument.next;
          continue;
        }
      }

      if (["hat", "widehat", "bar", "overline", "vec", "tilde"].includes(command.name)) {
        const argument = readArgument(source, command.next);
        if (argument) {
          const mark = command.name === "vec" ? "→" : command.name === "tilde" ? "˜" : "¯";
          nodes.push(
            <span className="math-accent" key={`${keyPrefix}-accent-${index}`}>
              <span className="math-accent-mark">{mark}</span>
              <span>{renderFormula(argument.value, `${keyPrefix}-accent-${index}`)}</span>
            </span>
          );
          index = argument.next;
          continue;
        }
      }

      if (command.name === "left" || command.name === "right") {
        let delimiterIndex = command.next;
        while (/\s/.test(source[delimiterIndex] || "")) delimiterIndex += 1;
        if (source[delimiterIndex] === "\\") {
          const delimiterCommand = readCommand(source, delimiterIndex);
          if (delimiterCommand) delimiterIndex = delimiterCommand.next;
        } else if (delimiterIndex < source.length) {
          delimiterIndex += 1;
        }

        const delimiter = source.slice(command.next, delimiterIndex).replace(/\s/g, "");
        nodes.push(delimiter === "." ? "" : delimiter.replace(/^\\/, ""));
        index = delimiterIndex;
        continue;
      }

      if (command.name === "begin" || command.name === "end") {
        const argument = readArgument(source, command.next);
        index = argument?.next ?? command.next;
        continue;
      }

      if (spacingCommands.has(command.name)) {
        nodes.push(" ");
        index = command.next;
        continue;
      }

      if (command.name === "\\") {
        nodes.push(" ");
        index = command.next;
        continue;
      }

      nodes.push(symbols[command.name] ?? command.name);
      index = command.next;
      continue;
    }

    if (character === "~") {
      nodes.push("\u00a0");
      index += 1;
      continue;
    }

    if (character === "&") {
      nodes.push(" ");
      index += 1;
      continue;
    }

    nodes.push(character === "\n" ? " " : character);
    index += 1;
  }

  return nodes;
}

function findClosingDelimiter(text: string, start: number, delimiter: string) {
  for (let index = start; index < text.length; index += 1) {
    if (text[index] !== delimiter[0]) continue;
    if (delimiter.length > 1 && text.slice(index, index + delimiter.length) !== delimiter) continue;
    if (text[index - 1] === "\\") continue;
    return index;
  }

  return -1;
}

function splitMath(text: string): MathSegment[] {
  const segments: MathSegment[] = [];
  let plainStart = 0;
  let index = 0;

  const appendPlain = (end: number) => {
    if (end > plainStart) {
      segments.push({ value: text.slice(plainStart, end), display: false, math: false });
    }
  };

  while (index < text.length) {
    let opening = "";
    let closing = "";
    let display = false;

    if (text.startsWith("$$", index)) {
      opening = "$$";
      closing = "$$";
      display = true;
    } else if (text.startsWith("\\[", index)) {
      opening = "\\[";
      closing = "\\]";
      display = true;
    } else if (text.startsWith("\\(", index)) {
      opening = "\\(";
      closing = "\\)";
    } else if (text[index] === "$" && text[index + 1] !== "$" && text[index - 1] !== "\\") {
      opening = "$";
      closing = "$";
    }

    if (!opening) {
      index += 1;
      continue;
    }

    const closeStart = findClosingDelimiter(text, index + opening.length, closing);
    if (closeStart < 0 || (!display && text.slice(index + opening.length, closeStart).includes("\n"))) {
      index += opening.length;
      continue;
    }

    appendPlain(index);
    segments.push({
      value: text.slice(index + opening.length, closeStart).trim(),
      display,
      math: true,
    });
    index = closeStart + closing.length;
    plainStart = index;
  }

  appendPlain(text.length);
  return segments.length ? segments : [{ value: text, display: false, math: false }];
}

export function MathFormula({ source, display = false }: { source: string; display?: boolean }) {
  return (
    <span
      dir="ltr"
      role="math"
      aria-label={`Formula: ${source}`}
      className={display ? "math-display" : "math-inline"}
    >
      {renderFormula(source)}
    </span>
  );
}

export function MathText({ children }: { children?: React.ReactNode }) {
  if (typeof children !== "string") return children;

  return (
    <>
      {splitMath(children).map((segment, index) =>
        segment.math ? (
          <MathFormula key={`math-${index}`} source={segment.value} display={segment.display} />
        ) : (
          <React.Fragment key={`text-${index}`}>{segment.value}</React.Fragment>
        )
      )}
    </>
  );
}
