//  ContentView.swift
//  KWEngine — main window: sidebar navigation + section content + pipeline log.

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline
    @State private var showLog = false

    var body: some View {
        Group {
            if appState.workspace == nil {
                WelcomeView()
            } else {
                mainSplit
            }
        }
        .alert(tr("出错了", "Error"), isPresented: errorBinding) {
            Button("OK", role: .cancel) { appState.lastError = nil }
        } message: {
            Text(appState.lastError ?? "")
        }
        .sheet(isPresented: $showLog) {
            LogView()
                .environmentObject(pipeline)
                .frame(minWidth: 640, minHeight: 400)
        }
    }

    private var errorBinding: Binding<Bool> {
        Binding(get: { appState.lastError != nil },
                set: { if !$0 { appState.lastError = nil } })
    }

    private var mainSplit: some View {
        NavigationSplitView {
            List(SidebarSection.allCases, selection: sectionBinding) { section in
                Label(section.label, systemImage: section.icon)
                    .tag(section)
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 180, ideal: 200, max: 260)
            .safeAreaInset(edge: .bottom) {
                workspaceFooter
            }
        } detail: {
            detailView
        }
        .toolbar {
            ToolbarItemGroup(placement: .automatic) {
                if pipeline.isBusy {
                    HStack(spacing: 6) {
                        ProgressView().controlSize(.small)
                        Text(pipeline.activity)
                            .font(.callout)
                            .foregroundColor(.secondary)
                    }
                }
                Button {
                    showLog = true
                } label: {
                    Label(tr("运行日志", "Run Log"), systemImage: "terminal")
                }
                .help(tr("查看流水线运行日志", "View pipeline run log"))
            }
        }
    }

    private var sectionBinding: Binding<SidebarSection?> {
        Binding(get: { appState.section },
                set: { if let s = $0 { appState.section = s } })
    }

    @ViewBuilder
    private var detailView: some View {
        Group {
            switch appState.section {
            case .status: StatusView()
            case .papers: PapersView()
            case .principles: PrinciplesView()
            case .search: SearchView()
            case .synthesis: SynthesisView()
            case .settings: SettingsView().frame(maxWidth: 640).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            }
        }
        .background(Theme.canvas)
    }

    private var workspaceFooter: some View {
        VStack(alignment: .leading, spacing: 4) {
            Divider()
            HStack(spacing: 6) {
                Image(systemName: "books.vertical")
                    .foregroundColor(.secondary)
                VStack(alignment: .leading, spacing: 1) {
                    Text(appState.workspace?.root.lastPathComponent ?? "")
                        .font(.caption.bold())
                        .lineLimit(1)
                    Text(tr("知识库", "Knowledge base"))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button {
                    appState.closeWorkspace()
                } label: {
                    Image(systemName: "rectangle.portrait.and.arrow.right")
                }
                .buttonStyle(.plain)
                .foregroundColor(.secondary)
                .help(tr("切换知识库", "Switch knowledge base"))
            }
            .padding(.horizontal, 10)
            .padding(.bottom, 8)
        }
    }
}

// MARK: - Pipeline log sheet

struct LogView: View {
    @EnvironmentObject var pipeline: Pipeline
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(tr("运行日志", "Pipeline Log")).font(.headline)
                Spacer()
                Button(tr("清空", "Clear")) { pipeline.clearLog() }
                Button(tr("关闭", "Close")) { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
            .padding()
            Divider()
            if pipeline.log.isEmpty {
                Spacer()
                Text(tr("还没有日志。运行 L1 / L2 / L3 或提问后这里会显示过程。",
                        "No log yet. Run L1 / L2 / L3 or Ask and progress will appear here."))
                    .foregroundColor(.secondary)
                Spacer()
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 3) {
                            ForEach(pipeline.log) { line in
                                HStack(alignment: .top, spacing: 8) {
                                    Text(Self.timeFormatter.string(from: line.time))
                                        .font(.system(.caption, design: .monospaced))
                                        .foregroundColor(.secondary)
                                    Text(line.text)
                                        .font(.system(.caption, design: .monospaced))
                                        .foregroundColor(color(for: line.level))
                                        .textSelection(.enabled)
                                }
                                .id(line.id)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                    }
                    .onChange(of: pipeline.log.count) { _ in
                        if let last = pipeline.log.last {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
        }
    }

    private func color(for level: Pipeline.LogLine.Level) -> Color {
        switch level {
        case .info: return Theme.ink
        case .warn: return Theme.saffron
        case .error: return Theme.fieryRed
        case .success: return Theme.emerald
        }
    }

    static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()
}

// MARK: - Shared small components

struct StatusBadge: View {
    let status: PaperStatus

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(Theme.status(status))
                .frame(width: 6, height: 6)
            Text(Theme.statusLabel(status))
                .font(.system(size: 11, weight: .semibold))
                .foregroundColor(Theme.status(status))
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(Capsule(style: .continuous).fill(Theme.status(status).opacity(0.10)))
        .overlay(Capsule(style: .continuous).strokeBorder(Theme.status(status).opacity(0.25), lineWidth: 1))
    }
}

struct FieldRow: View {
    let label: String
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).kwSectionLabel()
            Text(text.isEmpty ? "—" : text)
                .font(.system(size: 13))
                .lineSpacing(3)
                .foregroundColor(Theme.ink)
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct TagWrap: View {
    let label: String
    let tags: [String]
    var color: Color = Theme.accent

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).kwSectionLabel()
            if tags.isEmpty {
                Text("—").foregroundColor(Theme.inkSecondary)
            } else {
                FlowLayoutCompat(tags: tags, color: color)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// Simple wrapping tag display (works on macOS 13 without Layout protocol tricks).
struct FlowLayoutCompat: View {
    let tags: [String]
    var color: Color = Theme.accent

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(tags, id: \.self) { tag in
                KWChip(text: tag, color: color)
            }
        }
    }
}
