//  LLMClient.swift
//  KWEngine — minimal chat-completion client for OpenAI-compatible and Anthropic APIs.
//  No silent fallback: HTTP errors and malformed model output throw with detail.

import Foundation

struct LLMError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
    init(_ message: String) { self.message = message }
}

struct LLMClient {
    let settings: LLMSettings
    let apiKey: String

    // MARK: - Core completion

    func complete(system: String, user: String, model: String) async throws -> String {
        guard let url = settings.endpointURL else {
            throw LLMError("API base URL is not set (open Settings)")
        }
        guard !model.isEmpty else {
            throw LLMError("Model id is not set (open Settings)")
        }

        var request = URLRequest(url: url, timeoutInterval: settings.timeout)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: Any]
        switch settings.protocolKind {
        case .openAICompatible:
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
            payload = [
                "model": model,
                "messages": [
                    ["role": "system", "content": system],
                    ["role": "user", "content": user],
                ],
                "temperature": settings.temperature,
                "max_tokens": settings.maxTokens,
                "stream": false,
            ]
        case .anthropic:
            request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
            request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
            payload = [
                "model": model,
                "max_tokens": settings.maxTokens,
                "temperature": settings.temperature,
                "system": system,
                "messages": [
                    ["role": "user", "content": user],
                ],
            ]
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw LLMError("Network request failed: \(error.localizedDescription)")
        }

        guard let http = response as? HTTPURLResponse else {
            throw LLMError("Invalid HTTP response")
        }
        let bodyText = String(data: data, encoding: .utf8) ?? ""
        guard (200..<300).contains(http.statusCode) else {
            throw LLMError("API returned HTTP \(http.statusCode): \(String(bodyText.prefix(600)))")
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LLMError("API response is not JSON: \(String(bodyText.prefix(300)))")
        }

        switch settings.protocolKind {
        case .openAICompatible:
            guard
                let choices = json["choices"] as? [[String: Any]],
                let first = choices.first,
                let message = first["message"] as? [String: Any],
                let content = message["content"] as? String,
                !content.isEmpty
            else {
                throw LLMError("Unexpected OpenAI-compatible response shape: \(String(bodyText.prefix(400)))")
            }
            return content
        case .anthropic:
            guard let blocks = json["content"] as? [[String: Any]] else {
                throw LLMError("Unexpected Anthropic response shape: \(String(bodyText.prefix(400)))")
            }
            let text = blocks
                .filter { ($0["type"] as? String) == "text" }
                .compactMap { $0["text"] as? String }
                .joined()
            guard !text.isEmpty else {
                throw LLMError("Anthropic response contained no text blocks: \(String(bodyText.prefix(400)))")
            }
            return text
        }
    }

    // MARK: - JSON-typed completion

    func completeJSON<T: Decodable>(_ type: T.Type, system: String, user: String, model: String) async throws -> T {
        let raw = try await complete(system: system, user: user, model: model)
        let data = try Self.extractJSONData(from: raw)
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw LLMError("Model output did not match the expected JSON schema (\(error.localizedDescription)). Raw output starts: \(String(raw.prefix(400)))")
        }
    }

    /// Pull the first JSON object/array out of a model reply (handles ``` fences).
    static func extractJSONData(from text: String) throws -> Data {
        // 1) Fenced blocks first.
        if text.contains("```") {
            let parts = text.components(separatedBy: "```")
            // parts alternate outside/inside fence
            var i = 1
            while i < parts.count {
                var candidate = parts[i]
                // Drop a language tag like "json" on the first line.
                if let newline = candidate.firstIndex(of: "\n") {
                    let firstLine = candidate[..<newline].trimmingCharacters(in: .whitespaces)
                    if firstLine.lowercased() == "json" || firstLine.isEmpty {
                        candidate = String(candidate[candidate.index(after: newline)...])
                    }
                }
                let trimmed = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
                if trimmed.hasPrefix("{") || trimmed.hasPrefix("[") {
                    if let data = validJSONData(trimmed) { return data }
                }
                i += 2
            }
        }
        // 2) First balanced object/array in the raw text.
        if let snippet = firstBalancedJSON(in: text), let data = validJSONData(snippet) {
            return data
        }
        throw LLMError("No valid JSON found in model output. Output starts: \(String(text.prefix(400)))")
    }

    private static func validJSONData(_ s: String) -> Data? {
        guard let data = s.data(using: .utf8) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) != nil ? data : nil
    }

    private static func firstBalancedJSON(in text: String) -> String? {
        guard let start = text.firstIndex(where: { $0 == "{" || $0 == "[" }) else { return nil }
        let openChar = text[start]
        let closeChar: Character = openChar == "{" ? "}" : "]"
        var depth = 0
        var inString = false
        var escaped = false
        var i = start
        while i < text.endIndex {
            let ch = text[i]
            if escaped {
                escaped = false
            } else if inString {
                if ch == "\\" { escaped = true }
                else if ch == "\"" { inString = false }
            } else {
                switch ch {
                case "\"": inString = true
                case openChar: depth += 1
                case closeChar:
                    depth -= 1
                    if depth == 0 {
                        return String(text[start...i])
                    }
                default: break
                }
            }
            i = text.index(after: i)
        }
        return nil
    }

    // MARK: - Connectivity test

    func testConnection(model: String) async throws -> String {
        let started = Date()
        let reply = try await complete(
            system: "You are a connectivity test. Reply with exactly: OK",
            user: "ping",
            model: model
        )
        let ms = Int(Date().timeIntervalSince(started) * 1000)
        return "\(ms) ms — \(String(reply.prefix(80)))"
    }
}

// MARK: - Lenient decoding helpers (string-or-array, string-or-number)

extension KeyedDecodingContainer {
    func flexString(_ key: Key) -> String {
        if let s = try? decode(String.self, forKey: key) { return s }
        if let i = try? decode(Int.self, forKey: key) { return String(i) }
        if let d = try? decode(Double.self, forKey: key) { return String(d) }
        if let b = try? decode(Bool.self, forKey: key) { return b ? "true" : "false" }
        return ""
    }

    func flexStringList(_ key: Key) -> [String] {
        if let arr = try? decode([String].self, forKey: key) {
            return arr.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
        }
        if let s = try? decode(String.self, forKey: key) {
            let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
            return t.isEmpty ? [] : [t]
        }
        return []
    }

    func flexInt(_ key: Key) -> Int? {
        if let i = try? decode(Int.self, forKey: key) { return i }
        if let s = try? decode(String.self, forKey: key) { return Int(s) }
        if let d = try? decode(Double.self, forKey: key) { return Int(d) }
        return nil
    }
}
