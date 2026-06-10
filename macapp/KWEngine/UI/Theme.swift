//  Theme.swift
//  KWEngine — design system: Pantone palette, minimal premium Apple style.
//
//  Principles: color is semantic (never decorative), generous whitespace,
//  hairline borders, SF Pro + rounded numerals, full light/dark support.

import SwiftUI
import AppKit

// MARK: - Pantone palette (hex from Pantone color bridge)

extension NSColor {
    convenience init(hex: String) {
        var v = UInt64(0)
        Scanner(string: hex.replacingOccurrences(of: "#", with: "")).scanHexInt64(&v)
        self.init(srgbRed: CGFloat((v >> 16) & 0xFF) / 255,
                  green: CGFloat((v >> 8) & 0xFF) / 255,
                  blue: CGFloat(v & 0xFF) / 255,
                  alpha: 1)
    }
}

extension Color {
    /// Dynamic color that follows the system appearance.
    init(lightHex: String, darkHex: String) {
        self.init(nsColor: NSColor(name: nil) { appearance in
            let isDark = appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
            return NSColor(hex: isDark ? darkHex : lightHex)
        })
    }
}

enum Theme {

    // Core brand
    /// PANTONE 19-4052 Classic Blue — primary accent.
    static let accent = Color(lightHex: "0F4C81", darkHex: "7AA5CC")
    /// PANTONE 533 C — deep navy, hero surfaces.
    static let navy = Color(lightHex: "1F2A44", darkHex: "27344F")

    // Ink (text)
    /// PANTONE Black 6 C / Bright White 11-0601.
    static let ink = Color(lightHex: "101820", darkHex: "F4F5F0")
    /// PANTONE Cool Gray 11 C / Cool Gray 4 C.
    static let inkSecondary = Color(lightHex: "53565A", darkHex: "A8AAAD")

    // Semantic
    /// PANTONE 17-5641 Emerald — success / distilled.
    static let emerald = Color(lightHex: "009473", darkHex: "2FBF96")
    /// PANTONE 1235 C Saffron — warnings / stale / incomplete.
    static let saffron = Color(lightHex: "E8A317", darkHex: "FFC64A")
    /// PANTONE 485 C Fiery Red — errors.
    static let fieryRed = Color(lightHex: "DA291C", darkHex: "F0564A")
    /// PANTONE 16-1546 Living Coral — Ask / highlights.
    static let coral = Color(lightHex: "E85D4E", darkHex: "FF8A7E")
    /// PANTONE 18-3838 Ultra Violet — math-basis tags.
    static let ultraViolet = Color(lightHex: "5F4B8B", darkHex: "9786BE")
    /// PANTONE 3262 C — data-regime tags.
    static let teal = Color(lightHex: "00897F", darkHex: "34D6C9")

    // Surfaces
    /// Canvas tint: PANTONE 11-0601 Bright White / near-black slate.
    static let canvas = Color(lightHex: "F4F5F0", darkHex: "17191D")
    /// Cards float one step above the canvas.
    static let card = Color(lightHex: "FFFFFF", darkHex: "212429")
    /// Hairline: PANTONE Cool Gray 1 C, translucent.
    static let hairline = Color(lightHex: "D9D9D6", darkHex: "3A3D42").opacity(0.8)
    /// Subtle fill for inset wells (notes, code).
    static let well = Color(lightHex: "EDEEE9", darkHex: "1B1E22")

    static func status(_ s: PaperStatus) -> Color {
        switch s {
        case .pending: return inkSecondary
        case .l1: return accent
        case .l2: return teal
        case .complete: return emerald
        case .incomplete: return saffron
        }
    }

    static func statusLabel(_ s: PaperStatus) -> String {
        switch s {
        case .pending: return tr("待读", "Pending")
        case .l1: return tr("已读 L1", "Read · L1")
        case .l2: return "L2"
        case .complete: return tr("已蒸馏", "Distilled")
        case .incomplete: return tr("不完整", "Incomplete")
        }
    }
}

// MARK: - Reusable styles

/// Uppercased, tracked section label — the quiet Apple-style eyebrow.
struct KWSectionLabel: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(size: 11, weight: .semibold))
            .tracking(0.8)
            .foregroundColor(Theme.inkSecondary)
            .textCase(.uppercase)
    }
}

/// Card surface: white/dark elevated panel with hairline border.
struct KWCard: ViewModifier {
    var padding: CGFloat = 14
    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Theme.card)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .strokeBorder(Theme.hairline, lineWidth: 1)
            )
    }
}

/// Inset well for body notes / long text.
struct KWWell: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Theme.well)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .strokeBorder(Theme.hairline, lineWidth: 1)
            )
    }
}

extension View {
    func kwSectionLabel() -> some View { modifier(KWSectionLabel()) }
    func kwCard(padding: CGFloat = 14) -> some View { modifier(KWCard(padding: padding)) }
    func kwWell() -> some View { modifier(KWWell()) }
}

/// Capsule tag chip — tinted fill, hairline ring, semantic color.
struct KWChip: View {
    let text: String
    var color: Color = Theme.accent

    var body: some View {
        Text(text)
            .font(.system(size: 12.5, weight: .medium))
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(Capsule(style: .continuous).fill(color.opacity(0.10)))
            .overlay(Capsule(style: .continuous).strokeBorder(color.opacity(0.28), lineWidth: 1))
            .textSelection(.enabled)
    }
}

/// The brand glyph: three layers distilling to an essence dot.
/// Mirrors the app icon — used on the welcome hero.
struct EngineGlyph: View {
    var tint: Color = .white
    var scale: CGFloat = 1

    var body: some View {
        VStack(spacing: 9 * scale) {
            Capsule().fill(tint.opacity(0.45)).frame(width: 86 * scale, height: 13 * scale)
            Capsule().fill(tint.opacity(0.70)).frame(width: 60 * scale, height: 13 * scale)
            Capsule().fill(tint).frame(width: 36 * scale, height: 13 * scale)
            Circle().fill(tint).frame(width: 13 * scale, height: 13 * scale)
        }
    }
}
