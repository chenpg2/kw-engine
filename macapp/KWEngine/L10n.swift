//  L10n.swift
//  KWEngine — bilingual (zh-Hans / en) strings, following the system language.

import Foundation

let isChineseUI: Bool = {
    guard let first = Locale.preferredLanguages.first else { return false }
    return first.lowercased().hasPrefix("zh")
}()

/// tr("中文", "English")
func tr(_ zh: String, _ en: String) -> String {
    isChineseUI ? zh : en
}
