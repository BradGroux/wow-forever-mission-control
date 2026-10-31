"""Parse WoW SavedVariables (a Lua table literal) without running Lua."""
import re


class LuaParser:
    """Tiny recursive-descent parser for the subset WoW writes to SavedVariables."""
    ESC = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
           "\\": "\\", '"': '"', "'": "'", "\n": "\n"}
    NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    LONG = re.compile(r"\[(=*)\[")
    NUM = re.compile(r"-?\s*(0[xX][0-9a-fA-F]+|(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?|inf|nan)")

    def __init__(self, s):
        self.s, self.i = s, 0

    def err(self, msg):
        raise ValueError(f"{msg} at line {self.s.count(chr(10), 0, self.i) + 1}")

    def ws(self):
        s = self.s
        while self.i < len(s):
            c = s[self.i]
            if c.isspace():
                self.i += 1
            elif s.startswith("--", self.i):
                m = re.compile(r"--\[(=*)\[").match(s, self.i)
                if m:
                    end = s.find("]" + m.group(1) + "]", m.end())
                    self.i = len(s) if end < 0 else end + len(m.group(1)) + 2
                else:
                    nl = s.find("\n", self.i)
                    self.i = len(s) if nl < 0 else nl + 1
            else:
                break

    def peek(self):
        self.ws()
        return self.s[self.i] if self.i < len(self.s) else ""

    def expect(self, ch):
        if self.peek() != ch:
            self.err(f"expected {ch!r}")
        self.i += 1

    def document(self):
        out = {}
        while self.peek():
            m = self.NAME.match(self.s, self.i)
            if not m:
                self.err("expected global name")
            self.i = m.end()
            self.expect("=")
            out[m.group(0)] = self.value()
            if self.peek() == ";":
                self.i += 1
        return out

    def value(self):
        c = self.peek()
        if c == "{":
            return self.table()
        if c in "\"'":
            return self.string()
        if c == "[" and self.LONG.match(self.s, self.i):
            return self.long_string()
        m = re.compile(r"(true|false|nil)\b").match(self.s, self.i)
        if m:
            self.i = m.end()
            return {"true": True, "false": False, "nil": None}[m.group(1)]
        m = self.NUM.match(self.s, self.i)
        if m:
            self.i = m.end()
            t = m.group(0).replace(" ", "")
            neg, body = t.startswith("-"), t.lstrip("-")
            if body.lower().startswith("0x"):
                v = int(body, 16)
            elif body in ("inf", "nan"):
                v = float(body)
            elif re.fullmatch(r"\d+", body):
                v = int(body)
            else:
                v = float(body)
            return -v if neg else v
        self.err(f"unexpected {c!r}")

    def string(self):
        q, s = self.s[self.i], self.s
        self.i += 1
        buf = []
        while True:
            if self.i >= len(s):
                self.err("unterminated string")
            c = s[self.i]
            if c == q:
                self.i += 1
                return "".join(buf)
            if c == "\\":
                n = s[self.i + 1]
                if n.isdigit():
                    m = re.compile(r"\d{1,3}").match(s, self.i + 1)
                    buf.append(chr(int(m.group(0))))
                    self.i = m.end()
                    continue
                buf.append(self.ESC.get(n, n))
                self.i += 2
                continue
            buf.append(c)
            self.i += 1

    def long_string(self):
        m = re.compile(r"\[(=*)\[\n?").match(self.s, self.i)
        close = "]" + m.group(1) + "]"
        end = self.s.find(close, m.end())
        if end < 0:
            self.err("unterminated long string")
        self.i = end + len(close)
        return self.s[m.end():end]

    def table(self):
        self.expect("{")
        d, n = {}, 1
        while True:
            c = self.peek()
            if c == "}":
                self.i += 1
                break
            if c == "[" and not self.LONG.match(self.s, self.i):
                self.i += 1
                k = self.value()
                self.expect("]")
                self.expect("=")
                d[k] = self.value()
            else:
                m = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)").match(self.s, self.i)
                if m:
                    self.i = m.end()
                    d[m.group(1)] = self.value()
                else:
                    d[n] = self.value()
                    n += 1
            if self.peek() in (",", ";"):
                self.i += 1
        return d


def parse(text):
    return LuaParser(text).document()
