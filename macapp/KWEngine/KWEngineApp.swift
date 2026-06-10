//  KWEngineApp.swift
//  KWEngine — a native macOS app built on the kw-engine design:
//  distill → abstract → synthesize → search by problem structure.
//  Markdown is truth; index.json + SQLite are derived; the LLM provider is user-configured.

import SwiftUI

@main
struct KWEngineApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(appState.pipeline)
                .frame(minWidth: 980, minHeight: 620)
        }

        Settings {
            SettingsView()
                .frame(width: 560)
                .padding(.bottom, 12)
        }
    }
}
