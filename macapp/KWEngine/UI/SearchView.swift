//  SearchView.swift
//  KWEngine — the payoff: new problem → search by structure → matched mechanism
//  + rationale + when-it-breaks. Keyword mode is deterministic (port of kw search);
//  Ask mode adds LLM structure-extraction and answer composition.

import SwiftUI

struct SearchView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    enum Mode: String, CaseIterable, Identifiable {
        case keyword, ask
        var id: String { rawValue }
        var label: String {
            switch self {
            case .keyword: return tr("结构关键词", "Structure keywords")
            case .ask: return tr("描述问题（LLM）", "Describe a problem (LLM)")
            }
        }
    }

    @State private var mode: Mode = .keyword
    @State private var keyword = ""
    @State private var keywordHits: [SearchHit] = []
    @State private var searched = false

    @State private var question = ""
    @State private var askResult: AskResult?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Picker("", selection: $mode) {
                    ForEach(Mode.allCases) { m in Text(m.label).tag(m) }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
                .frame(maxWidth: 420)

                if mode == .keyword { keywordSection } else { askSection }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: keyword search (deterministic, port of `kw search`)

    private var keywordSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(tr("按问题结构检索：词元会与每条原则的 problem_signature 与 math_basis 做子串匹配。",
                    "Search by problem structure: tokens are substring-matched against each principle's problem_signature and math_basis."))
                .font(.caption)
                .foregroundColor(.secondary)
            HStack {
                TextField(tr("例如：unpaired marginal snapshots optimal transport",
                             "e.g. unpaired marginal snapshots optimal transport"), text: $keyword)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { runKeyword() }
                Button(tr("检索", "Search")) { runKeyword() }
                    .keyboardShortcut(.defaultAction)
                    .disabled(keyword.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            hitsList(keywordHits, emptyNote: searched
                     ? tr("没有匹配 — 这可能是知识库的空白", "No match — possibly a gap in the library")
                     : "")
        }
    }

    private func runKeyword() {
        guard let ws = appState.workspace else { return }
        keywordHits = SearchEngine.search(workspace: ws, query: keyword, topK: 20)
        searched = true
    }

    // MARK: ask (LLM)

    private var askSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(tr("用自然语言描述你的新问题。引擎先抽取问题的结构签名，再在库中检索，最后把命中的机制 + 理由 + 失效边界组织成答案。",
                    "Describe your new problem in natural language. The engine extracts its structural signature, searches the library, then composes the matched mechanism + rationale + boundaries into an answer."))
                .font(.caption)
                .foregroundColor(.secondary)
            TextEditor(text: $question)
                .font(.system(size: 13))
                .lineSpacing(3)
                .scrollContentBackground(.hidden)
                .padding(8)
                .frame(minHeight: 90, maxHeight: 160)
                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Theme.card))
                .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Theme.hairline, lineWidth: 1))
            HStack {
                Button {
                    runAsk()
                } label: {
                    Label(tr("提问", "Ask"), systemImage: "questionmark.bubble")
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(pipeline.isBusy || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if pipeline.isBusy {
                    ProgressView().controlSize(.small)
                    Text(pipeline.activity).font(.caption).foregroundColor(.secondary)
                }
            }

            if let result = askResult {
                Divider()
                TagWrap(label: tr("抽取的问题签名", "Extracted problem signature"),
                        tags: result.signature, color: Theme.accent)
                if !result.mathBasis.isEmpty {
                    TagWrap(label: tr("候选数学机制", "Candidate math machinery"),
                            tags: result.mathBasis, color: Theme.ultraViolet)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text(tr("回答", "Answer"))
                        .kwSectionLabel()
                    Text(result.answer)
                        .font(.system(size: 13))
                        .lineSpacing(4)
                        .foregroundColor(Theme.ink)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .fill(Theme.accent.opacity(0.06))
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .strokeBorder(Theme.accent.opacity(0.20), lineWidth: 1)
                        )
                }
                hitsList(result.hits, emptyNote: "")
            }
        }
    }

    private func runAsk() {
        guard let ws = appState.workspace else { return }
        let q = question
        Task {
            do {
                askResult = try await pipeline.ask(workspace: ws, question: q)
            } catch {
                appState.present(error)
            }
        }
    }

    // MARK: shared hit list

    @ViewBuilder
    private func hitsList(_ hits: [SearchHit], emptyNote: String) -> some View {
        if hits.isEmpty {
            if !emptyNote.isEmpty {
                Label(emptyNote, systemImage: "circle.dashed")
                    .foregroundColor(.secondary)
            }
        } else {
            VStack(alignment: .leading, spacing: 4) {
                Text(tr("命中原则", "Matched principles"))
                    .kwSectionLabel()
                ForEach(hits) { hit in
                    Button {
                        appState.showPrinciple(hit.id)
                    } label: {
                        HStack(spacing: 10) {
                            Text(hit.id)
                                .font(.system(size: 12.5, weight: .medium, design: .monospaced))
                                .foregroundColor(Theme.accent)
                            Text(hit.title)
                                .font(.system(size: 12.5))
                                .foregroundColor(Theme.ink)
                                .lineLimit(1)
                            Spacer()
                            Text(tr("分数 \(hit.score)", "score \(hit.score)"))
                                .font(.system(size: 11, weight: .semibold, design: .rounded))
                                .foregroundColor(Theme.inkSecondary)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 9)
                        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Theme.card))
                        .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Theme.hairline, lineWidth: 1))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}
