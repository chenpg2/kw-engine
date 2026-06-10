//  PrinciplesView.swift
//  KWEngine — browse Layer-2 principles: signature ↔ mechanism ↔ rationale.

import SwiftUI
import AppKit

struct PrinciplesView: View {
    @EnvironmentObject var appState: AppState
    @State private var filter = ""

    private var principles: [PrincipleProj] {
        let all = appState.index?.principles ?? []
        let f = filter.trimmingCharacters(in: .whitespaces).lowercased()
        guard !f.isEmpty else { return all }
        return all.filter {
            $0.id.lowercased().contains(f)
                || $0.title.lowercased().contains(f)
                || $0.problemSignature.joined(separator: " ").lowercased().contains(f)
                || $0.mathBasis.joined(separator: " ").lowercased().contains(f)
        }
    }

    var body: some View {
        HSplitView {
            VStack(spacing: 0) {
                HStack {
                    Text(tr("原则", "Principles")).font(.headline)
                    Spacer()
                    Text("\(appState.index?.principles.count ?? 0)")
                        .foregroundColor(.secondary)
                }
                .padding(10)
                TextField(tr("过滤：id / 标题 / 签名 / 数学", "Filter: id / title / signature / math"), text: $filter)
                    .textFieldStyle(.roundedBorder)
                    .padding(.horizontal, 10)
                    .padding(.bottom, 8)
                Divider()
                if principles.isEmpty {
                    Spacer()
                    Text(tr("还没有原则 — 先对论文运行 L2 蒸馏",
                            "No principles yet — run L2 distillation on a paper"))
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding()
                    Spacer()
                } else {
                    List(selection: selectionBinding) {
                        ForEach(principles) { p in
                            VStack(alignment: .leading, spacing: 3) {
                                HStack {
                                    Text(p.id).font(.system(.body, design: .monospaced))
                                    Spacer()
                                    if !p.links.isEmpty {
                                        Image(systemName: "link").font(.caption2).foregroundColor(.secondary)
                                    }
                                }
                                Text(p.title).font(.caption).foregroundColor(.secondary).lineLimit(2)
                            }
                            .padding(.vertical, 2)
                            .tag(p.id)
                        }
                    }
                }
            }
            .frame(minWidth: 280, idealWidth: 320, maxWidth: 420)

            Group {
                if let pid = appState.selectedPrinciple,
                   appState.index?.principles.contains(where: { $0.id == pid }) == true {
                    PrincipleDetailView(pid: pid)
                } else {
                    VStack {
                        Text(tr("选择一条原则", "Select a principle")).foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(minWidth: 420, maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var selectionBinding: Binding<String?> {
        Binding(get: { appState.selectedPrinciple }, set: { appState.selectedPrinciple = $0 })
    }
}

// MARK: - Principle detail

struct PrincipleDetailView: View {
    let pid: String
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    @State private var principle: Principle?
    @State private var bodyNotes = ""
    @State private var loadError: String?

    private var refreshToken: String { "\(pid)|\(pipeline.isBusy)" }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let error = loadError {
                    Label(error, systemImage: "exclamationmark.triangle").foregroundColor(.orange)
                }
                if let p = principle {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(p.id).font(.title2.monospaced().bold()).textSelection(.enabled)
                            Spacer()
                            Text(p.rubricVersion).font(.caption).foregroundColor(.secondary)
                            Button {
                                if let ws = appState.workspace {
                                    NSWorkspace.shared.activateFileViewerSelecting([ws.principlePath(pid)])
                                }
                            } label: {
                                Image(systemName: "folder")
                            }
                            .help(tr("在访达中显示", "Reveal in Finder"))
                        }
                        Text(p.title).font(.headline).textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    // The mapping: WHEN ↔ WHAT ↔ WHY — the load-bearing core.
                    VStack(alignment: .leading, spacing: 14) {
                        FieldRow(label: tr("抽象表述 (abstraction_level)", "abstraction_level"), text: p.abstractionLevel)
                        TagWrap(label: tr("问题签名 — 何时适用 (problem_signature)", "problem_signature — WHEN it applies"),
                                tags: p.problemSignature, color: Theme.accent)
                        TagWrap(label: tr("数学基础 (math_basis)", "math_basis"), tags: p.mathBasis, color: Theme.ultraViolet)
                        FieldRow(label: tr("机制 — 做什么 (mechanism)", "mechanism — WHAT to do"), text: p.mechanism)
                        FieldRow(label: tr("理由 — 为何成立 (rationale)", "rationale — WHY it holds"), text: p.rationale)
                    }
                    .kwCard()

                    // Limits & testability.
                    VStack(alignment: .leading, spacing: 14) {
                        TagWrap(label: tr("数据条件 (data_regime)", "data_regime"), tags: p.dataRegime, color: Theme.teal)
                        FieldRow(label: tr("可证伪预测 (falsifiable_prediction)", "falsifiable_prediction"), text: p.falsifiablePrediction)
                        FieldRow(label: tr("边界 — 何时失效 (boundaries)", "boundaries — when it breaks"), text: p.boundaries)
                    }
                    .kwCard()

                    provenanceSection(p)
                    linksSection(p)

                    if !bodyNotes.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(tr("推导与迁移笔记（正文）", "Derivation & transfer notes (body)"))
                                .kwSectionLabel()
                            Text(bodyNotes)
                                .font(.system(size: 12.5))
                                .lineSpacing(3)
                                .textSelection(.enabled)
                                .kwWell()
                        }
                    }
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .task(id: refreshToken) { load() }
    }

    @ViewBuilder
    private func provenanceSection(_ p: Principle) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(tr("出处 (provenance)", "provenance"))
                .kwSectionLabel()
            ForEach(p.provenance, id: \.self) { prov in
                HStack(spacing: 6) {
                    Button(paperIdFromProvenance(prov)) {
                        appState.showPaper(paperIdFromProvenance(prov))
                    }
                    .buttonStyle(LinkButtonStyle())
                    .font(.callout.monospaced())
                    Text(SQLiteIndex.locatorFromProvenance(prov))
                        .font(.callout)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    @ViewBuilder
    private func linksSection(_ p: Principle) -> some View {
        if !p.links.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                Text(tr("关联 (links)", "links"))
                    .kwSectionLabel()
                ForEach(p.links, id: \.self) { link in
                    if let le = LinkEntry(fromString: link) {
                        HStack(spacing: 6) {
                            KWChip(text: le.linkType, color: Theme.coral)
                            Button(le.target) { appState.showPrinciple(le.target) }
                                .buttonStyle(LinkButtonStyle())
                                .font(.callout.monospaced())
                        }
                    }
                }
            }
        }
    }

    private func load() {
        guard let ws = appState.workspace else { return }
        loadError = nil
        do {
            let (p, body) = try ws.readPrincipleFile(pid)
            principle = p
            bodyNotes = body
                .replacingOccurrences(of: "<!-- Derivation, evidence quotes, transfer notes. -->", with: "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
        } catch {
            principle = nil
            bodyNotes = ""
            loadError = error.localizedDescription
        }
    }
}
