"""
Stream Buffer Parser.
Parses SSE text chunks in real-time and tracks <think>...</think> boundaries,
emitting structured ("thinking", text) and ("delta", text) events.
"""

from typing import List, Tuple


class StreamBufferParser:
    """Stateful stream buffer that detects and extracts <think>...</think> tags on the fly."""

    def __init__(self):
        self.buffer = ""
        self.in_think = False
        self.seen_think_start = False
        self.accumulated_thinking = ""
        self.accumulated_answer = ""

    def feed(self, chunk: str) -> List[Tuple[str, str]]:
        events: List[Tuple[str, str]] = []
        if not chunk:
            return events
        self.buffer += chunk

        while True:
            if not self.in_think:
                if not self.seen_think_start:
                    if "<think>" in self.buffer:
                        before, after = self.buffer.split("<think>", 1)
                        if before:
                            self.accumulated_answer += before
                            events.append(("delta", before))
                        self.in_think = True
                        self.seen_think_start = True
                        self.buffer = after
                        continue
                    elif "<" in self.buffer:
                        idx = self.buffer.rfind("<")
                        prefix = self.buffer[:idx]
                        potential = self.buffer[idx:]
                        if "<think>".startswith(potential):
                            if prefix:
                                self.accumulated_answer += prefix
                                events.append(("delta", prefix))
                            self.buffer = potential
                            break
                        else:
                            self.accumulated_answer += self.buffer
                            events.append(("delta", self.buffer))
                            self.buffer = ""
                            break
                    else:
                        if self.buffer:
                            self.accumulated_answer += self.buffer
                            events.append(("delta", self.buffer))
                            self.buffer = ""
                        break
                else:
                    clean_b = self.buffer.replace("</think>", "").replace("<think>", "")
                    if clean_b:
                        self.accumulated_answer += clean_b
                        events.append(("delta", clean_b))
                    self.buffer = ""
                    break
            else:
                if "</think>" in self.buffer:
                    think_part, after = self.buffer.split("</think>", 1)
                    if think_part:
                        self.accumulated_thinking += think_part
                        events.append(("thinking", think_part))
                    self.in_think = False
                    self.buffer = after
                    continue
                elif "</" in self.buffer or "<" in self.buffer:
                    idx = self.buffer.rfind("<")
                    potential = self.buffer[idx:]
                    if "</think>".startswith(potential):
                        prefix = self.buffer[:idx]
                        if prefix:
                            self.accumulated_thinking += prefix
                            events.append(("thinking", prefix))
                        self.buffer = potential
                        break
                    else:
                        self.accumulated_thinking += self.buffer
                        events.append(("thinking", self.buffer))
                        self.buffer = ""
                        break
                else:
                    if self.buffer:
                        self.accumulated_thinking += self.buffer
                        events.append(("thinking", self.buffer))
                        self.buffer = ""
                    break

        return events

    def finalize(self) -> List[Tuple[str, str]]:
        events: List[Tuple[str, str]] = []
        if self.buffer:
            if self.in_think:
                self.accumulated_thinking += self.buffer
                events.append(("thinking", self.buffer))
            else:
                clean = self.buffer.replace("</think>", "").replace("<think>", "")
                if clean:
                    self.accumulated_answer += clean
                    events.append(("delta", clean))
            self.buffer = ""
        return events
