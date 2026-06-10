//  SynthesisView.swift
//  KWEngine — Layer-3 artifacts: design-space map, contradictions, gaps.

import SwiftUI

struct SynthesisView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    enum Doc: String, CaseIterable, Identifiable {
        case designSpace, contradictions, gaps
        var id: String { rawValue }
        var filename: String {
            switch self {
            case .designSpace: return "design-space.md"
            case .contradictions: return "contradictions.md"
            case .gaps: return "gaps.md"
            }
        }
        var label: String {
            switch self {
            case .designSpace: return tr("设计空间", "Design space")
            case .contradictions: return tr("矛盾", "Contradictions")
            case .gaps: return tr("空白", "Gaps")
            }
        }
    }

    @State private var doc: Doc = .designSpace
    @State private var content: String?

    private var synthesis: SynthesisState? { appState.index?.synthesis }
    private var principleCount: Int { appState.index?.principles.count ?? 0 }
    private var stale: Bool {
        guard let s = synthesis else { return principleCount > 0 }
        return principleCount > s.nPrinciplesAtLastRun
    }

    private var refreshToken: String {
        "\(doc.rawValue)|\(synthesis?.lastRun ?? "never")|\(pipeline.isBusy)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 12) {
                Picker("", selection: $doc) {
                    ForEach(Doc.allCases) { d in Text(d.label).tag(d) }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
                .frame(maxWidth: 380)

                Spacer()

                if let lastRun = synthesis?.lastRun {
                    Text(tr("上次综合：\(lastRun)（覆盖 \(synthesis?.nPrinciplesAtLastRun ?? 0) 条原则）",
                            "Last run: \(lastRun) (over \(synthesis?.nPrinciplesAtLastRun ?? 0) principles)"))
                        .font(.system(size: 11.5))
                        .foregroundColor(Theme.inkSecondary)
                }

                Button {
                    runL3()
                } label: {
                    Label(tr("运行综合 (L3)", "Synthesize (L3)"), systemImage: "square.grid.3x3.topleft.filled")
                }
                .disabled(pipeline.isBusy || principleCount == 0)
            }
            .padding(12)

            if stale && principleCount > 0 {
                HStack(spacing: 7) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 11))
                        .foregroundColor(Theme.saffron)
                    Text(tr("综合已过期：自上次综合以来新增了 \(principleCount - (synthesis?.nPrinciplesAtLastRun ?? 0)) 条原则。",
                            "Synthesis is stale: \(principleCount - (synthesis?.nPrinciplesAtLastRun ?? 0)) principles added since the last run."))
                        .font(.system(size: 12))
                        .foregroundColor(Theme.ink)
                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Theme.saffron.opacity(0.10)))
                .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Theme.saffron.opacity(0.30), lineWidth: 1))
                .padding(.horizontal, 12)
                .padding(.bottom, 10)
            }

            Divider()

            ScrollView {
                if let text = content {
                    Text(text)
                        .font(.system(size: 13))
                        .lineSpacing(4)
                        .foregroundColor(Theme.ink)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .kwCard(padding: 18)
                        .padding(16)
                } else {
                    VStack(spacing: 10) {
                        Image(systemName: "square.grid.3x3.topleft.filled")
                            .font(.system(size: 30))
                            .foregroundColor(Theme.inkSecondary.opacity(0.6))
                        Text(tr("还没有综合产物。积累若干原则后运行 L3。",
                                "No synthesis artifacts yet. Accumulate some principles, then run L3."))
                            .font(.system(size: 13))
                            .foregroundColor(Theme.inkSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 80)
                }
            }
        }
        .task(id: refreshToken) { load() }
    }

    private func load() {
        content = appState.workspace?.readSynthesisDoc(doc.filename)
    }

    private func runL3() {
        guard let ws = appState.workspace else { return }
        Task {
            do {
                try await pipeline.runL3(workspace: ws)
            } catch {
                appState.present(error)
            }
            appState.reload()
        }
    }
}
