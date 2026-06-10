//  Frontmatter.swift
//  KWEngine — YAML-frontmatter parsing/serialization for memory records.
//
//  Implements the YAML subset that kw-engine records actually use:
//  scalars (plain / 'single' / "double" / | > block), block & inline lists,
//  one-level nested maps (bib:), inline maps, null/int/bool, comments,
//  and PyYAML-style folded line wrapping of long plain scalars.
//
//  No silent fallback: malformed input throws with a message.

import Foundation

enum YamlValue {
    case null
    case string(String)
    case int(Int)
    case bool(Bool)
    case list([YamlValue])
    case map([String: YamlValue])

    var stringValue: String? {
        switch self {
        case .string(let s): return s
        case .int(let i): return String(i)
        case .bool(let b): return b ? "true" : "false"
        case .null: return nil
        default: return nil
        }
    }

    /// String coalescing null -> ""
    var stringOrEmpty: String { stringValue ?? "" }

    var intValue: Int? {
        switch self {
        case .int(let i): return i
        case .string(let s): return Int(s)
        default: return nil
        }
    }

    var stringList: [String] {
        switch self {
        case .list(let items): return items.compactMap { $0.stringValue }
        case .string(let s): return s.isEmpty ? [] : [s]
        case .null: return []
        default: return []
        }
    }

    var mapValue: [String: YamlValue]? {
        if case .map(let m) = self { return m }
        return nil
    }
}

enum Frontmatter {

    // MARK: - Document split (mirrors python text.split("---", 2))

    static func splitDocument(_ text: String) throws -> (yaml: String, body: String) {
        guard text.hasPrefix("---") else {
            throw StoreError("No YAML front-matter found")
        }
        let afterFirst = text.index(text.startIndex, offsetBy: 3)
        let rest = text[afterFirst...]
        guard let close = rest.range(of: "---") else {
            throw StoreError("Malformed front-matter (missing closing ---)")
        }
        let yaml = String(rest[..<close.lowerBound])
        let body = String(rest[close.upperBound...])
        return (yaml, body)
    }

    /// f"---\n{yaml}---\n{body}" — same shape ops.py renders.
    static func compose(yaml: String, body: String) -> String {
        var y = yaml
        if !y.hasSuffix("\n") { y += "\n" }
        return "---\n" + y + "---" + (body.hasPrefix("\n") ? body : "\n" + body)
    }

    // MARK: - Parser

    static func parse(_ yamlText: String) throws -> [String: YamlValue] {
        let rawLines = yamlText.components(separatedBy: "\n")
        var index = 0
        let result = try parseMapBlock(rawLines, &index, indent: 0)
        // Anything left that is not blank/comment is a structure we do not understand.
        while index < rawLines.count {
            let line = rawLines[index]
            let stripped = line.trimmingCharacters(in: .whitespaces)
            if !stripped.isEmpty && !stripped.hasPrefix("#") {
                throw StoreError("Unparsed YAML at line: \(stripped)")
            }
            index += 1
        }
        return result
    }

    private static func indentOf(_ line: String) -> Int {
        var n = 0
        for ch in line {
            if ch == " " { n += 1 } else { break }
        }
        return n
    }

    private static func isBlankOrComment(_ line: String) -> Bool {
        let stripped = line.trimmingCharacters(in: .whitespaces)
        return stripped.isEmpty || stripped.hasPrefix("#")
    }

    private static func nextSignificant(_ lines: [String], _ from: Int) -> Int? {
        var i = from
        while i < lines.count {
            if !isBlankOrComment(lines[i]) { return i }
            i += 1
        }
        return nil
    }

    /// Parse `key: value` entries at exactly `indent`. Stops when indentation decreases.
    private static func parseMapBlock(_ lines: [String], _ index: inout Int, indent: Int) throws -> [String: YamlValue] {
        var result: [String: YamlValue] = [:]
        while index < lines.count {
            let line = lines[index]
            if isBlankOrComment(line) { index += 1; continue }
            let lineIndent = indentOf(line)
            if lineIndent < indent { break }
            if lineIndent > indent {
                throw StoreError("Unexpected indentation in YAML: \(line.trimmingCharacters(in: .whitespaces))")
            }
            let content = String(line.dropFirst(indent))
            if content.hasPrefix("- ") || content == "-" {
                // A list item at map level — belongs to the *previous* key; handled there.
                break
            }
            guard let colon = findKeyColon(content) else {
                throw StoreError("Expected 'key:' in YAML line: \(content)")
            }
            let key = String(content[..<colon]).trimmingCharacters(in: .whitespaces)
            var rest = String(content[content.index(after: colon)...])
            rest = stripLeadingSpaces(rest)
            index += 1

            if rest.isEmpty || rest.hasPrefix("#") {
                // Value continues on following lines (list / nested map) or is null.
                result[key] = try parseBlockValue(lines, &index, keyIndent: indent)
            } else {
                result[key] = try parseFlowOrScalar(rest, lines, &index, keyIndent: indent)
            }
        }
        return result
    }

    /// First ':' that terminates a plain key (followed by space, or end of line).
    private static func findKeyColon(_ s: String) -> String.Index? {
        var i = s.startIndex
        while i < s.endIndex {
            if s[i] == ":" {
                let next = s.index(after: i)
                if next == s.endIndex || s[next] == " " || s[next] == "\t" {
                    return i
                }
            }
            i = s.index(after: i)
        }
        return nil
    }

    private static func stripLeadingSpaces(_ s: String) -> String {
        String(s.drop(while: { $0 == " " || $0 == "\t" }))
    }

    /// After `key:` with nothing on the line: block list, nested map, or null.
    private static func parseBlockValue(_ lines: [String], _ index: inout Int, keyIndent: Int) throws -> YamlValue {
        guard let next = nextSignificant(lines, index) else { return .null }
        let line = lines[next]
        let nIndent = indentOf(line)
        let stripped = line.trimmingCharacters(in: .whitespaces)

        // Block list: items may sit at the SAME indent as the key (PyYAML style)
        // or deeper (hand-written style).
        if (stripped.hasPrefix("- ") || stripped == "-"), nIndent >= keyIndent {
            index = next
            return try parseListBlock(lines, &index, itemIndent: nIndent)
        }
        // Nested map: deeper-indented `key: ...` lines.
        if nIndent > keyIndent {
            index = next
            return .map(try parseMapBlock(lines, &index, indent: nIndent))
        }
        return .null
    }

    private static func parseListBlock(_ lines: [String], _ index: inout Int, itemIndent: Int) throws -> YamlValue {
        var items: [YamlValue] = []
        while index < lines.count {
            let line = lines[index]
            if isBlankOrComment(line) { index += 1; continue }
            let nIndent = indentOf(line)
            if nIndent != itemIndent { break }
            let stripped = String(line.dropFirst(nIndent))
            guard stripped.hasPrefix("- ") || stripped == "-" else { break }
            var itemText = stripped == "-" ? "" : String(stripped.dropFirst(2))
            itemText = stripLeadingSpaces(itemText)
            index += 1
            // Continuation lines of a wrapped item: deeper-indented, not new items.
            if itemText.hasPrefix("\"") || itemText.hasPrefix("'") {
                let quote = itemText.first!
                if !closesQuote(itemText, quote: quote) {
                    itemText = try consumeWrappedQuoted(itemText, quote: quote, lines, &index, minIndent: itemIndent + 1)
                }
                items.append(.string(try unquote(itemText)))
            } else {
                var value = stripTrailingComment(itemText)
                while index < lines.count, !isBlankOrComment(lines[index]),
                      indentOf(lines[index]) > itemIndent,
                      !lines[index].trimmingCharacters(in: .whitespaces).hasPrefix("- ") {
                    value += " " + lines[index].trimmingCharacters(in: .whitespaces)
                    index += 1
                }
                items.append(typedScalar(value))
            }
        }
        return .list(items)
    }

    /// Value present on the key line: inline list/map, block-scalar header, or scalar.
    private static func parseFlowOrScalar(_ rest: String, _ lines: [String], _ index: inout Int, keyIndent: Int) throws -> YamlValue {
        if rest.hasPrefix("[") {
            let flow = try consumeFlow(rest, open: "[", close: "]", lines, &index)
            return .list(try parseInlineList(flow))
        }
        if rest.hasPrefix("{") {
            let flow = try consumeFlow(rest, open: "{", close: "}", lines, &index)
            return .map(try parseInlineMap(flow))
        }
        if rest.hasPrefix("|") || rest.hasPrefix(">") {
            return .string(try parseBlockScalar(header: rest, lines, &index, keyIndent: keyIndent))
        }
        if rest.hasPrefix("\"") || rest.hasPrefix("'") {
            let quote = rest.first!
            var text = rest
            if !closesQuote(text, quote: quote) {
                text = try consumeWrappedQuoted(text, quote: quote, lines, &index, minIndent: keyIndent + 1)
            }
            return .string(try unquote(text))
        }
        // Plain scalar, possibly wrapped onto following more-indented lines (PyYAML width=80).
        // The key already has inline content, so it cannot also own a block list:
        // any more-indented following line is scalar continuation — even if it starts
        // with "- " (a wrapped word that happens to begin with a dash).
        var value = stripTrailingComment(rest)
        while index < lines.count, !isBlankOrComment(lines[index]) {
            let nIndent = indentOf(lines[index])
            let stripped = lines[index].trimmingCharacters(in: .whitespaces)
            if nIndent <= keyIndent { break }
            value += " " + stripTrailingComment(stripped)
            index += 1
        }
        return typedScalar(value)
    }

    /// Consume a flow collection that may span multiple lines, returning the
    /// full "[...]" / "{...}" text with newlines collapsed to spaces.
    private static func consumeFlow(_ first: String, open: Character, close: Character, _ lines: [String], _ index: inout Int) throws -> String {
        var text = first
        while !flowClosed(text, open: open, close: close) {
            guard index < lines.count else {
                throw StoreError("Unterminated '\(open)...\(close)' in YAML")
            }
            text += " " + lines[index].trimmingCharacters(in: .whitespaces)
            index += 1
        }
        return text
    }

    private static func flowClosed(_ s: String, open: Character, close: Character) -> Bool {
        var depth = 0
        var inSingle = false
        var inDouble = false
        var escaped = false
        for ch in s {
            if escaped { escaped = false; continue }
            if inDouble {
                if ch == "\\" { escaped = true } else if ch == "\"" { inDouble = false }
                continue
            }
            if inSingle {
                if ch == "'" { inSingle = false }
                continue
            }
            switch ch {
            case "\"": inDouble = true
            case "'": inSingle = true
            case open: depth += 1
            case close:
                depth -= 1
                if depth == 0 { return true }
            default: break
            }
        }
        return false
    }

    private static func parseInlineList(_ flow: String) throws -> [YamlValue] {
        let inner = String(flow.dropFirst().dropLast()).trimmingCharacters(in: .whitespaces)
        if inner.isEmpty { return [] }
        return try splitFlowItems(inner).map { item in
            let t = item.trimmingCharacters(in: .whitespaces)
            if t.hasPrefix("\"") || t.hasPrefix("'") { return .string(try unquote(t)) }
            return typedScalar(t)
        }
    }

    private static func parseInlineMap(_ flow: String) throws -> [String: YamlValue] {
        let inner = String(flow.dropFirst().dropLast()).trimmingCharacters(in: .whitespaces)
        var result: [String: YamlValue] = [:]
        if inner.isEmpty { return result }
        for item in try splitFlowItems(inner) {
            let t = item.trimmingCharacters(in: .whitespaces)
            guard let colon = findKeyColon(t) ?? t.firstIndex(of: ":") else {
                throw StoreError("Malformed inline map entry: \(t)")
            }
            let key = String(t[..<colon]).trimmingCharacters(in: .whitespaces)
                .trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
            let raw = stripLeadingSpaces(String(t[t.index(after: colon)...]))
            if raw.hasPrefix("\"") || raw.hasPrefix("'") {
                result[key] = .string(try unquote(raw))
            } else {
                result[key] = typedScalar(raw)
            }
        }
        return result
    }

    /// Split flow content on top-level commas (quotes and nesting respected).
    private static func splitFlowItems(_ s: String) throws -> [String] {
        var items: [String] = []
        var current = ""
        var depth = 0
        var inSingle = false
        var inDouble = false
        var escaped = false
        for ch in s {
            if escaped { current.append(ch); escaped = false; continue }
            if inDouble {
                if ch == "\\" { escaped = true }
                else if ch == "\"" { inDouble = false }
                current.append(ch)
                continue
            }
            if inSingle {
                if ch == "'" { inSingle = false }
                current.append(ch)
                continue
            }
            switch ch {
            case "\"": inDouble = true; current.append(ch)
            case "'": inSingle = true; current.append(ch)
            case "[", "{": depth += 1; current.append(ch)
            case "]", "}": depth -= 1; current.append(ch)
            case "," where depth == 0:
                items.append(current)
                current = ""
            default:
                current.append(ch)
            }
        }
        if !current.trimmingCharacters(in: .whitespaces).isEmpty { items.append(current) }
        return items
    }

    private static func parseBlockScalar(header: String, _ lines: [String], _ index: inout Int, keyIndent: Int) throws -> String {
        let style = header.first!  // | or >
        let chompStrip = header.contains("-")
        var collected: [String] = []
        var blockIndent: Int? = nil
        while index < lines.count {
            let line = lines[index]
            let stripped = line.trimmingCharacters(in: .whitespaces)
            if stripped.isEmpty {
                collected.append("")
                index += 1
                continue
            }
            let nIndent = indentOf(line)
            if nIndent <= keyIndent { break }
            if blockIndent == nil { blockIndent = nIndent }
            let bi = blockIndent!
            let content = line.count > bi ? String(line.dropFirst(bi)) : ""
            collected.append(content)
            index += 1
        }
        // Trim trailing blank lines
        while let last = collected.last, last.isEmpty { collected.removeLast() }
        var text: String
        if style == "|" {
            text = collected.joined(separator: "\n")
        } else {
            // Folded: blank line -> newline, otherwise join with space.
            var paragraphs: [String] = []
            var current: [String] = []
            for l in collected {
                if l.isEmpty {
                    paragraphs.append(current.joined(separator: " "))
                    current = []
                } else {
                    current.append(l)
                }
            }
            paragraphs.append(current.joined(separator: " "))
            text = paragraphs.joined(separator: "\n")
        }
        if !chompStrip { text += "\n" }
        return text
    }

    private static func closesQuote(_ s: String, quote: Character) -> Bool {
        if quote == "\"" {
            var escaped = false
            var count = 0
            for ch in s {
                if escaped { escaped = false; continue }
                if ch == "\\" { escaped = true; continue }
                if ch == "\"" { count += 1 }
            }
            return count >= 2
        } else {
            // Single-quoted: '' is an escaped quote; an odd number of quotes means closed.
            let count = s.filter { $0 == "'" }.count
            return count >= 2 && count % 2 == 0
        }
    }

    private static func consumeWrappedQuoted(_ first: String, quote: Character, _ lines: [String], _ index: inout Int, minIndent: Int) throws -> String {
        var text = first
        while !closesQuote(text, quote: quote) {
            guard index < lines.count else {
                throw StoreError("Unterminated quoted scalar in YAML")
            }
            let line = lines[index]
            index += 1
            let stripped = line.trimmingCharacters(in: .whitespaces)
            // PyYAML folds wrapped quoted scalars; a blank line means a literal newline.
            if stripped.isEmpty { text += "\n" } else { text += " " + stripped }
        }
        return text
    }

    private static func unquote(_ s: String) throws -> String {
        let t = s.trimmingCharacters(in: .whitespaces)
        guard let first = t.first else { return "" }
        if first == "\"" {
            var out = ""
            var i = t.index(after: t.startIndex)
            var escaped = false
            while i < t.endIndex {
                let ch = t[i]
                if escaped {
                    switch ch {
                    case "n": out.append("\n")
                    case "t": out.append("\t")
                    case "r": out.append("\r")
                    case "\\": out.append("\\")
                    case "\"": out.append("\"")
                    case "0": out.append("\0")
                    default: out.append(ch)
                    }
                    escaped = false
                } else if ch == "\\" {
                    escaped = true
                } else if ch == "\"" {
                    break  // closing quote; ignore any trailing comment
                } else {
                    out.append(ch)
                }
                i = t.index(after: i)
            }
            return out
        }
        if first == "'" {
            var out = ""
            var i = t.index(after: t.startIndex)
            while i < t.endIndex {
                let ch = t[i]
                if ch == "'" {
                    let next = t.index(after: i)
                    if next < t.endIndex && t[next] == "'" {
                        out.append("'")
                        i = t.index(after: next)
                        continue
                    }
                    break  // closing quote
                }
                out.append(ch)
                i = t.index(after: i)
            }
            return out
        }
        return t
    }

    /// YAML: in a plain scalar, ' #' starts a comment.
    private static func stripTrailingComment(_ s: String) -> String {
        var prev: Character? = nil
        var i = s.startIndex
        while i < s.endIndex {
            if s[i] == "#", let p = prev, p == " " || p == "\t" {
                return String(s[..<i]).trimmingCharacters(in: .whitespaces)
            }
            prev = s[i]
            i = s.index(after: i)
        }
        return s.trimmingCharacters(in: .whitespaces)
    }

    private static func typedScalar(_ raw: String) -> YamlValue {
        let t = raw.trimmingCharacters(in: .whitespaces)
        if t.isEmpty || t == "null" || t == "~" || t == "Null" || t == "NULL" { return .null }
        if t == "true" || t == "True" { return .bool(true) }
        if t == "false" || t == "False" { return .bool(false) }
        // Only coerce to Int when it round-trips canonically, matching PyYAML
        // (e.g. "08"/"007" stay strings; "2023"/"-5" become ints).
        if let i = Int(t), String(i) == t { return .int(i) }
        return .string(t)
    }

    // MARK: - Emitter (PyYAML default_flow_style=False, sort_keys=False style)

    static func render(_ pairs: [(String, YamlValue)]) -> String {
        var out = ""
        for (key, value) in pairs {
            out += renderEntry(key: key, value: value, indent: 0)
        }
        return out
    }

    private static func renderEntry(key: String, value: YamlValue, indent: Int) -> String {
        let pad = String(repeating: " ", count: indent)
        switch value {
        case .null:
            return "\(pad)\(key): null\n"
        case .bool(let b):
            return "\(pad)\(key): \(b ? "true" : "false")\n"
        case .int(let i):
            return "\(pad)\(key): \(i)\n"
        case .string(let s):
            return "\(pad)\(key): \(renderScalar(s))\n"
        case .list(let items):
            if items.isEmpty { return "\(pad)\(key): []\n" }
            var out = "\(pad)\(key):\n"
            for item in items {
                let text: String
                switch item {
                case .string(let s): text = renderScalar(s)
                case .int(let i): text = String(i)
                case .bool(let b): text = b ? "true" : "false"
                case .null: text = "null"
                default: text = "''"
                }
                out += "\(pad)- \(text)\n"  // PyYAML indentless block sequence
            }
            return out
        case .map(let m):
            var out = "\(pad)\(key):\n"
            // Stable well-known order for bib; alphabetical otherwise.
            let order = ["title", "authors", "venue", "year"]
            let keys = m.keys.sorted { a, b in
                let ia = order.firstIndex(of: a) ?? Int.max
                let ib = order.firstIndex(of: b) ?? Int.max
                return ia == ib ? a < b : ia < ib
            }
            for k in keys {
                out += renderEntry(key: k, value: m[k]!, indent: indent + 2)
            }
            return out
        }
    }

    static func renderScalar(_ s: String) -> String {
        if s.isEmpty { return "''" }
        if isPlainSafe(s) { return s }
        if !s.contains("\n") && !s.contains("\\") {
            return "'" + s.replacingOccurrences(of: "'", with: "''") + "'"
        }
        var out = "\""
        for ch in s {
            switch ch {
            case "\\": out += "\\\\"
            case "\"": out += "\\\""
            case "\n": out += "\\n"
            case "\t": out += "\\t"
            case "\r": out += "\\r"
            default: out.append(ch)
            }
        }
        out += "\""
        return out
    }

    /// Numeric-implicit-resolver pattern (YAML 1.1 superset). Any match is force-quoted,
    /// which is harmless: PyYAML and our parser both read a quoted scalar back verbatim.
    private static let numberPattern = try! NSRegularExpression(
        pattern: #"^[-+]?(\.inf|\.nan|0x[0-9a-fA-F_]+|0o?[0-7_]+|0b[01_]+|[0-9][0-9_]*(\.[0-9_]*)?([eE][-+]?[0-9]+)?|\.[0-9_]+([eE][-+]?[0-9]+)?|[0-9][0-9_]*(:[0-5]?[0-9])+(\.[0-9_]*)?)$"#
    )

    /// Whether `s` can be emitted as a plain (unquoted) YAML scalar. Conservative: when in
    /// doubt we return false and the caller quotes. Matches PyYAML's implicit resolvers
    /// for null/bool/number/merge/value plus indicator-led and structurally-risky scalars.
    private static func isPlainSafe(_ s: String) -> Bool {
        guard let first = s.first else { return false }
        if s != s.trimmingCharacters(in: .whitespaces) { return false }
        if s.contains("\n") || s.contains("\t") { return false }
        if "-?:#&*!|>'\"%@`[]{},=".contains(first) || first == "<" { return false }
        if s == "=" || s == "<<" || s == ">>" || s == "~" { return false }  // YAML-reserved tokens
        if s.contains(": ") || s.hasSuffix(":") { return false }
        if s.contains(" #") { return false }
        let lowered = s.lowercased()
        if ["null", "~", "true", "false", "yes", "no", "on", "off",
            ".inf", "-.inf", "+.inf", ".nan"].contains(lowered) { return false }
        let range = NSRange(s.startIndex..., in: s)
        if numberPattern.firstMatch(in: s, range: range) != nil { return false }
        return true
    }
}
