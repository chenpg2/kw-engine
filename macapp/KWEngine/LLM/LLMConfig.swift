//  LLMConfig.swift
//  KWEngine — user-configurable LLM provider settings.
//  Base URL / model ids / parameters live in UserDefaults; the API key lives in the Keychain.

import Foundation
import Security

enum APIProtocolKind: String, CaseIterable, Identifiable {
    case openAICompatible = "openai"
    case anthropic = "anthropic"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .openAICompatible: return "OpenAI-compatible (/chat/completions)"
        case .anthropic: return "Anthropic (/v1/messages)"
        }
    }
}

enum SettingsKeys {
    static let protocolKind = "llm.protocol"
    static let baseURL = "llm.baseURL"
    static let strongModel = "llm.strongModel"
    static let fastModel = "llm.fastModel"
    static let maxTokens = "llm.maxTokens"
    static let temperature = "llm.temperature"
    static let timeout = "llm.timeout"
    static let maxPDFChars = "llm.maxPDFChars"
    static let workspacePath = "workspace.path"
}

struct LLMSettings {
    var protocolKind: APIProtocolKind
    var baseURL: String
    var strongModel: String
    var fastModel: String
    var maxTokens: Int
    var temperature: Double
    var timeout: Double
    var maxPDFChars: Int

    /// Reader/extraction model: falls back to the strong model when unset
    /// (mirrors the read-cheap / distill-strong routing of the CLI plugin).
    var fastModelEffective: String { fastModel.isEmpty ? strongModel : fastModel }

    static func load() -> LLMSettings {
        let d = UserDefaults.standard
        return LLMSettings(
            protocolKind: APIProtocolKind(rawValue: d.string(forKey: SettingsKeys.protocolKind) ?? "") ?? .openAICompatible,
            baseURL: d.string(forKey: SettingsKeys.baseURL) ?? "",
            strongModel: d.string(forKey: SettingsKeys.strongModel) ?? "",
            fastModel: d.string(forKey: SettingsKeys.fastModel) ?? "",
            maxTokens: d.object(forKey: SettingsKeys.maxTokens) as? Int ?? 8192,
            temperature: d.object(forKey: SettingsKeys.temperature) as? Double ?? 0.2,
            timeout: d.object(forKey: SettingsKeys.timeout) as? Double ?? 600,
            maxPDFChars: d.object(forKey: SettingsKeys.maxPDFChars) as? Int ?? 120_000
        )
    }

    /// Deterministic endpoint derivation — previewed live in Settings, never guessed silently.
    static func endpointString(protocolKind: APIProtocolKind, baseURL: String) -> String {
        var base = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        while base.hasSuffix("/") { base.removeLast() }
        guard !base.isEmpty else { return "" }
        switch protocolKind {
        case .openAICompatible:
            if base.hasSuffix("/chat/completions") { return base }
            return base + "/chat/completions"
        case .anthropic:
            if base.hasSuffix("/messages") { return base }
            if base.hasSuffix("/v1") { return base + "/messages" }
            return base + "/v1/messages"
        }
    }

    var endpointURL: URL? {
        let s = Self.endpointString(protocolKind: protocolKind, baseURL: baseURL)
        return s.isEmpty ? nil : URL(string: s)
    }
}

// MARK: - Keychain storage for the API key

enum KeychainStore {
    private static let service = "com.kwengine.app"
    private static let account = "llm-api-key"

    private static func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    static func saveAPIKey(_ key: String) {
        deleteAPIKey()
        guard !key.isEmpty else { return }
        var query = baseQuery()
        query[kSecValueData as String] = Data(key.utf8)
        SecItemAdd(query as CFDictionary, nil)
    }

    static func loadAPIKey() -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func deleteAPIKey() {
        SecItemDelete(baseQuery() as CFDictionary)
    }
}
