//  WelcomeView.swift
//  KWEngine — open or create a knowledge-base workspace.

import SwiftUI
import AppKit

struct WelcomeView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            // Brand mark — mirrors the app icon.
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [Color(lightHex: "175894", darkHex: "1B5C97"),
                                 Color(lightHex: "093A66", darkHex: "0B3D6B")],
                        startPoint: .top, endPoint: .bottom
                    )
                )
                .frame(width: 116, height: 116)
                .overlay(EngineGlyph(tint: Color(lightHex: "F4F5F0", darkHex: "F4F5F0"), scale: 0.78))
                .shadow(color: Theme.navy.opacity(0.28), radius: 18, y: 8)
                .padding(.bottom, 22)

            Text("KW Engine")
                .font(.system(size: 30, weight: .semibold))
                .foregroundColor(Theme.ink)
            Text(tr("方法论进化引擎", "Methodology evolution engine"))
                .font(.system(size: 14))
                .foregroundColor(Theme.inkSecondary)
                .padding(.top, 4)

            HStack(spacing: 7) {
                ForEach([tr("蒸馏", "Distill"), tr("抽象", "Abstract"),
                         tr("综合", "Synthesize"), tr("按结构检索", "Search by structure")], id: \.self) { step in
                    Text(step)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(Theme.accent)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 3.5)
                        .background(Capsule(style: .continuous).fill(Theme.accent.opacity(0.08)))
                        .overlay(Capsule(style: .continuous).strokeBorder(Theme.accent.opacity(0.22), lineWidth: 1))
                }
            }
            .padding(.top, 14)

            HStack(spacing: 12) {
                Button {
                    pickFolder(create: false)
                } label: {
                    Text(tr("打开知识库…", "Open Workspace…")).frame(width: 168)
                }
                .controlSize(.large)
                .buttonStyle(.borderedProminent)
                .keyboardShortcut("o")

                Button {
                    pickFolder(create: true)
                } label: {
                    Text(tr("新建知识库…", "Create Workspace…")).frame(width: 168)
                }
                .controlSize(.large)
                .buttonStyle(.bordered)
            }
            .padding(.top, 30)

            Spacer()

            VStack(spacing: 5) {
                Text(tr("知识库与 kw CLI / Claude Code 插件完全互通 — markdown 为真相，索引为派生。",
                        "Workspaces interoperate with the kw CLI / Claude Code plugin — markdown is truth, indexes are derived."))
                Text(tr("首次使用请先在「设置」（⌘,）中配置 LLM API。",
                        "First time? Configure your LLM API in Settings (⌘,)."))
            }
            .font(.system(size: 11.5))
            .foregroundColor(Theme.inkSecondary)
            .multilineTextAlignment(.center)
            .frame(maxWidth: 480)
            .padding(.bottom, 26)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.canvas)
    }

    private func pickFolder(create: Bool) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = create ? tr("在此新建", "Create Here") : tr("打开", "Open")
        panel.message = create
            ? tr("选择一个文件夹，将在其中创建知识库结构（memory/、paper/ 等）",
                 "Choose a folder; the workspace structure (memory/, paper/, …) will be created inside it")
            : tr("选择一个已有的 kw 知识库文件夹（包含 memory/）",
                 "Choose an existing kw workspace folder (containing memory/)")
        guard panel.runModal() == .OK, let url = panel.url else { return }
        if create {
            appState.createWorkspace(at: url)
        } else {
            appState.openWorkspace(url)
        }
    }
}
