//  PapersView.swift
//  KWEngine — paper list (L1 records) + per-paper pipeline actions.

import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct PapersView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    private var papers: [PaperProj] { appState.index?.papers ?? [] }

    var body: some View {
        HSplitView {
            VStack(spacing: 0) {
                HStack {
                    Text(tr("论文", "Papers")).font(.headline)
                    Spacer()
                    Button {
                        importPDFs()
                    } label: {
                        Label(tr("导入 PDF…", "Import PDF…"), systemImage: "plus.circle.fill")
                    }
                    .disabled(pipeline.isBusy)
                }
                .padding(10)
                Divider()
                if papers.isEmpty {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "doc.badge.plus").font(.largeTitle).foregroundColor(.secondary)
                        Text(tr("导入一篇论文 PDF 开始", "Import a paper PDF to begin"))
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                } else {
                    List(selection: selectionBinding) {
                        ForEach(papers) { paper in
                            VStack(alignment: .leading, spacing: 3) {
                                HStack {
                                    Text(paper.id)
                                        .font(.system(.body, design: .monospaced))
                                        .lineLimit(1)
                                    Spacer()
                                    StatusBadge(status: paper.status)
                                }
                                if !paper.title.isEmpty {
                                    Text(paper.title)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                        .lineLimit(2)
                                }
                                if !paper.principles.isEmpty {
                                    Text(paper.principles.joined(separator: " "))
                                        .font(.system(.caption2, design: .monospaced))
                                        .foregroundColor(Theme.emerald)
                                        .lineLimit(1)
                                }
                            }
                            .padding(.vertical, 2)
                            .tag(paper.id)
                        }
                    }
                }
            }
            .frame(minWidth: 280, idealWidth: 320, maxWidth: 420)

            Group {
                if let id = appState.selectedPaper, papers.contains(where: { $0.id == id }) {
                    PaperDetailView(paperId: id)
                } else {
                    VStack {
                        Text(tr("选择一篇论文", "Select a paper")).foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(minWidth: 420, maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var selectionBinding: Binding<String?> {
        Binding(get: { appState.selectedPaper }, set: { appState.selectedPaper = $0 })
    }

    private func importPDFs() {
        guard let ws = appState.workspace else { return }
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [.pdf]
        panel.message = tr("选择论文 PDF（文件名将作为 paper id）", "Choose paper PDFs (the filename stem becomes the paper id)")
        guard panel.runModal() == .OK else { return }
        var firstId: String?
        for url in panel.urls {
            do {
                let id = try ws.importPDF(from: url)
                if firstId == nil { firstId = id }
            } catch {
                appState.present(error)
            }
        }
        appState.reload()
        if let id = firstId { appState.selectedPaper = id }
    }
}

// MARK: - Paper detail

struct PaperDetailView: View {
    let paperId: String
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    @State private var paper: PaperFull?
    @State private var bodyNotes: String = ""
    @State private var loadError: String?

    private var indexEntry: PaperProj? {
        appState.index?.papers.first(where: { $0.id == paperId })
    }

    private var refreshToken: String {
        "\(paperId)|\(indexEntry?.status.rawValue ?? "")|\(pipeline.isBusy)"
    }

    private var pdfExists: Bool {
        guard let ws = appState.workspace else { return false }
        return FileManager.default.fileExists(atPath: ws.pdfPath(for: paperId).path)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                actions
                Divider()
                if let error = loadError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                }
                if let p = paper {
                    record(p)
                } else if loadError == nil {
                    Text(tr("尚未读取（L1）。运行 L1 生成忠实记录。",
                            "Not read yet (L1). Run L1 to produce the faithful record."))
                        .foregroundColor(.secondary)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .task(id: refreshToken) { load() }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(paperId).font(.title2.monospaced().bold()).textSelection(.enabled)
                if let entry = indexEntry { StatusBadge(status: entry.status) }
                Spacer()
            }
            if let p = paper, !p.bib.title.isEmpty {
                Text(p.bib.title).font(.headline).textSelection(.enabled)
            }
            if let p = paper {
                HStack(spacing: 10) {
                    if !p.bib.authors.isEmpty { Text(p.bib.authors) }
                    if !p.bib.venue.isEmpty { Text(p.bib.venue).italic() }
                    if let year = p.bib.year { Text(String(year)) }
                    if let doi = p.doi { Text("doi:\(doi)").font(.caption.monospaced()) }
                }
                .font(.caption)
                .foregroundColor(.secondary)
            }
        }
    }

    private var actions: some View {
        HStack(spacing: 10) {
            Button {
                run { try await pipeline.runL1(workspace: $0, paperId: paperId) }
            } label: {
                Label(tr("读取 L1", "Read (L1)"), systemImage: "eye")
            }
            .disabled(pipeline.isBusy || !pdfExists)
            .help(tr("忠实抽取：PDF → memory/papers/", "Faithful extraction: PDF → memory/papers/"))

            Button {
                run { try await pipeline.runL2(workspace: $0, paperId: paperId) }
            } label: {
                Label(tr("蒸馏 L2", "Distill (L2)"), systemImage: "lightbulb")
            }
            .disabled(pipeline.isBusy || indexEntry?.status == .pending)
            .help(tr("抽象出可迁移原则 → memory/principles/", "Abstract transferable principles → memory/principles/"))

            Button {
                run {
                    try await pipeline.runL1(workspace: $0, paperId: paperId)
                    appState.reload()
                    try await pipeline.runL2(workspace: $0, paperId: paperId)
                }
            } label: {
                Label(tr("一键处理 (L1+L2)", "Process (L1+L2)"), systemImage: "wand.and.stars")
            }
            .disabled(pipeline.isBusy || !pdfExists)

            Spacer()

            Button {
                if let ws = appState.workspace { NSWorkspace.shared.open(ws.pdfPath(for: paperId)) }
            } label: {
                Label("PDF", systemImage: "doc.richtext")
            }
            .disabled(!pdfExists)

            Button {
                if let ws = appState.workspace {
                    NSWorkspace.shared.activateFileViewerSelecting([ws.paperPath(paperId)])
                }
            } label: {
                Label(tr("在访达中显示", "Reveal"), systemImage: "folder")
            }
        }
    }

    @ViewBuilder
    private func record(_ p: PaperFull) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            FieldRow(label: "problem_addressed", text: p.problemAddressed)
            FieldRow(label: "method_summary", text: p.methodSummary)
            FieldRow(label: "math_used", text: p.mathUsed)
            FieldRow(label: "claimed_mechanism", text: p.claimedMechanism)
            FieldRow(label: "key_evidence", text: p.keyEvidence)
        }
        .kwCard()

        if let entry = indexEntry, !entry.principles.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                Text(tr("蒸馏出的原则", "Distilled principles"))
                    .kwSectionLabel()
                HStack(spacing: 6) {
                    ForEach(entry.principles, id: \.self) { pid in
                        Button(pid) { appState.showPrinciple(pid) }
                            .buttonStyle(.bordered)
                            .font(.caption.monospaced())
                    }
                }
            }
        }

        if !bodyNotes.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                Text(tr("忠实笔记（正文）", "Faithful notes (body)"))
                    .kwSectionLabel()
                Text(bodyNotes)
                    .font(.system(size: 12.5))
                    .lineSpacing(3)
                    .textSelection(.enabled)
                    .kwWell()
            }
        }
    }

    private func load() {
        guard let ws = appState.workspace else { return }
        loadError = nil
        guard FileManager.default.fileExists(atPath: ws.paperPath(paperId).path) else {
            paper = nil
            bodyNotes = ""
            return
        }
        do {
            let (p, body) = try ws.readPaperFile(paperId)
            paper = p
            bodyNotes = body
                .replacingOccurrences(of: "<!-- Fill in faithful notes below. No abstraction. -->", with: "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
        } catch {
            paper = nil
            bodyNotes = ""
            loadError = error.localizedDescription
        }
    }

    private func run(_ work: @escaping (Workspace) async throws -> Void) {
        guard let ws = appState.workspace else { return }
        Task {
            do {
                try await work(ws)
            } catch {
                appState.present(error)
            }
            appState.reload()
        }
    }
}
