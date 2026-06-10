//  SettingsView.swift
//  KWEngine — user-configurable LLM provider: protocol, base URL, API key, model ids.

import SwiftUI

struct SettingsView: View {
    @AppStorage(SettingsKeys.protocolKind) private var protocolRaw = APIProtocolKind.openAICompatible.rawValue
    @AppStorage(SettingsKeys.baseURL) private var baseURL = ""
    @AppStorage(SettingsKeys.strongModel) private var strongModel = ""
    @AppStorage(SettingsKeys.fastModel) private var fastModel = ""
    @AppStorage(SettingsKeys.maxTokens) private var maxTokens = 8192
    @AppStorage(SettingsKeys.temperature) private var temperature = 0.2
    @AppStorage(SettingsKeys.timeout) private var timeout = 600.0
    @AppStorage(SettingsKeys.maxPDFChars) private var maxPDFChars = 120_000

    @State private var apiKey = ""
    @State private var keyLoaded = false
    @State private var keySavedNote = ""
    @State private var testing = false
    @State private var testResult = ""
    @State private var testFailed = false

    private var protocolKind: APIProtocolKind {
        APIProtocolKind(rawValue: protocolRaw) ?? .openAICompatible
    }

    private var endpointPreview: String {
        LLMSettings.endpointString(protocolKind: protocolKind, baseURL: baseURL)
    }

    var body: some View {
        Form {
            Section {
                Picker(tr("协议", "Protocol"), selection: $protocolRaw) {
                    ForEach(APIProtocolKind.allCases) { kind in
                        Text(kind.displayName).tag(kind.rawValue)
                    }
                }

                TextField(tr("API 地址 (Base URL)", "API Base URL"), text: $baseURL, prompt: Text("https://api.deepseek.com"))
                    .autocorrectionDisabled()

                LabeledContent(tr("实际请求端点", "Resolved endpoint")) {
                    Text(endpointPreview.isEmpty ? "—" : endpointPreview)
                        .font(.caption.monospaced())
                        .foregroundColor(.secondary)
                        .textSelection(.enabled)
                }

                HStack {
                    SecureField("API Key", text: $apiKey, prompt: Text("sk-…"))
                    Button(tr("保存", "Save")) {
                        KeychainStore.saveAPIKey(apiKey)
                        keySavedNote = tr("已存入钥匙串", "Saved to Keychain")
                    }
                    .disabled(apiKey.isEmpty)
                }
                if !keySavedNote.isEmpty {
                    Text(keySavedNote).font(.caption).foregroundColor(.green)
                }
            } header: {
                Text(tr("LLM 提供方", "LLM Provider"))
            } footer: {
                Text(tr(
                    "示例 — DeepSeek: https://api.deepseek.com · Kimi: https://api.moonshot.cn/v1 · 本地 Ollama: http://localhost:11434/v1 · Anthropic 协议: https://api.anthropic.com",
                    "Examples — DeepSeek: https://api.deepseek.com · Kimi: https://api.moonshot.cn/v1 · local Ollama: http://localhost:11434/v1 · Anthropic protocol: https://api.anthropic.com"))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Section {
                TextField(tr("强模型（蒸馏 / 综合 / 回答）", "Strong model (distill / synthesize / answer)"),
                          text: $strongModel, prompt: Text("deepseek-reasoner / claude-sonnet-4-6 / …"))
                    .autocorrectionDisabled()
                TextField(tr("快模型（读取 / 结构抽取，可留空=用强模型）", "Fast model (read / extract; empty = strong model)"),
                          text: $fastModel, prompt: Text("deepseek-chat / claude-haiku-4-5 / …"))
                    .autocorrectionDisabled()
            } header: {
                Text(tr("模型", "Models"))
            } footer: {
                Text(tr("沿用 kw-engine 的「读取用便宜模型、蒸馏用强模型」路由。",
                        "Mirrors kw-engine's read-cheap / distill-strong model routing."))
                    .font(.caption).foregroundColor(.secondary)
            }

            Section(tr("参数", "Parameters")) {
                TextField(tr("max_tokens（单次回复上限）", "max_tokens (per response)"),
                          value: $maxTokens, formatter: NumberFormatter())
                TextField(tr("temperature", "temperature"),
                          value: $temperature, formatter: Self.decimalFormatter)
                TextField(tr("请求超时（秒）", "Request timeout (s)"),
                          value: $timeout, formatter: Self.decimalFormatter)
                TextField(tr("PDF 文本上限（字符）", "Max PDF text (chars)"),
                          value: $maxPDFChars, formatter: NumberFormatter())
            }

            Section {
                HStack {
                    Button {
                        runTest()
                    } label: {
                        if testing {
                            HStack(spacing: 6) { ProgressView().controlSize(.small); Text(tr("测试中…", "Testing…")) }
                        } else {
                            Label(tr("测试连接", "Test Connection"), systemImage: "bolt")
                        }
                    }
                    .disabled(testing || baseURL.isEmpty || strongModel.isEmpty || (apiKey.isEmpty && KeychainStore.loadAPIKey() == nil))
                    if !testResult.isEmpty {
                        Text(testResult)
                            .font(.caption)
                            .foregroundColor(testFailed ? .red : .green)
                            .textSelection(.enabled)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .onAppear {
            if !keyLoaded {
                apiKey = KeychainStore.loadAPIKey() ?? ""
                keyLoaded = true
            }
        }
    }

    private func runTest() {
        let key = apiKey.isEmpty ? (KeychainStore.loadAPIKey() ?? "") : apiKey
        if !apiKey.isEmpty {
            KeychainStore.saveAPIKey(apiKey)
            keySavedNote = tr("已存入钥匙串", "Saved to Keychain")
        }
        let settings = LLMSettings(
            protocolKind: protocolKind,
            baseURL: baseURL,
            strongModel: strongModel,
            fastModel: fastModel,
            maxTokens: 64,
            temperature: 0,
            timeout: min(timeout, 60),
            maxPDFChars: maxPDFChars
        )
        let client = LLMClient(settings: settings, apiKey: key)
        testing = true
        testResult = ""
        Task {
            do {
                let r = try await client.testConnection(model: strongModel)
                testResult = "✓ \(r)"
                testFailed = false
            } catch {
                testResult = error.localizedDescription
                testFailed = true
            }
            testing = false
        }
    }

    private static let decimalFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.maximumFractionDigits = 2
        return f
    }()
}
