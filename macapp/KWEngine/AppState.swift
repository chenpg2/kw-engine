//  AppState.swift
//  KWEngine — top-level observable state: current workspace, derived index, navigation.

import Foundation
import SwiftUI

enum SidebarSection: String, CaseIterable, Identifiable {
    case status, papers, principles, search, synthesis, settings

    var id: String { rawValue }

    var label: String {
        switch self {
        case .status: return tr("状态", "Status")
        case .papers: return tr("论文", "Papers")
        case .principles: return tr("原则", "Principles")
        case .search: return tr("检索 / 提问", "Search / Ask")
        case .synthesis: return tr("综合", "Synthesis")
        case .settings: return tr("设置", "Settings")
        }
    }

    var icon: String {
        switch self {
        case .status: return "gauge.with.dots.needle.bottom.50percent"
        case .papers: return "doc.text"
        case .principles: return "lightbulb"
        case .search: return "magnifyingglass"
        case .synthesis: return "square.grid.3x3.topleft.filled"
        case .settings: return "gearshape"
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    @Published var workspace: Workspace?
    @Published var index: IndexFile?
    @Published var lastError: String?

    // Navigation
    @Published var section: SidebarSection = .status
    @Published var selectedPaper: String?
    @Published var selectedPrinciple: String?

    let pipeline = Pipeline()

    init() {
        restoreLastWorkspace()
    }

    func restoreLastWorkspace() {
        guard let path = UserDefaults.standard.string(forKey: SettingsKeys.workspacePath) else { return }
        let url = URL(fileURLWithPath: path)
        if Workspace.isWorkspace(url) {
            workspace = Workspace(root: url)
            reload()
        }
    }

    func openWorkspace(_ url: URL) {
        guard Workspace.isWorkspace(url) else {
            lastError = tr(
                "该文件夹不是 kw 知识库（缺少 memory/index.json）。请选择已有知识库，或使用「新建知识库」。",
                "That folder is not a kw workspace (no memory/index.json). Pick an existing one or use “Create Workspace”."
            )
            return
        }
        workspace = Workspace(root: url)
        UserDefaults.standard.set(url.path, forKey: SettingsKeys.workspacePath)
        selectedPaper = nil
        selectedPrinciple = nil
        reload()
    }

    func createWorkspace(at url: URL) {
        do {
            try Workspace.scaffold(at: url)
            workspace = Workspace(root: url)
            UserDefaults.standard.set(url.path, forKey: SettingsKeys.workspacePath)
            selectedPaper = nil
            selectedPrinciple = nil
            reload()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func closeWorkspace() {
        workspace = nil
        index = nil
        selectedPaper = nil
        selectedPrinciple = nil
        UserDefaults.standard.removeObject(forKey: SettingsKeys.workspacePath)
    }

    func reload() {
        guard let ws = workspace else { return }
        do {
            index = try ws.readIndex()
        } catch {
            index = nil
            lastError = error.localizedDescription
        }
    }

    func present(_ error: Error) {
        lastError = error.localizedDescription
    }

    /// Jump to a principle's detail from anywhere.
    func showPrinciple(_ pid: String) {
        selectedPrinciple = pid
        section = .principles
    }

    func showPaper(_ id: String) {
        selectedPaper = id
        section = .papers
    }
}
