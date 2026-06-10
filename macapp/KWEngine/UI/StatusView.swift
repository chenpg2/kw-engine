//  StatusView.swift
//  KWEngine — workspace dashboard: KPI cards, pipeline chart, pending work,
//  verify, reindex. Mirrors `kw status` + `kw verify` + `kw reindex`.

import SwiftUI
import Charts

struct StatusView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var pipeline: Pipeline

    @State private var verdicts: [Verdict]?
    @State private var reindexReport: String?

    private var summary: StatusSummary? {
        try? appState.workspace?.statusSummary()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(tr("知识库状态", "Knowledge Base"))
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundColor(Theme.ink)
                    Text(tr("蒸馏 → 抽象 → 综合 → 按结构检索", "distill → abstract → synthesize → search by structure"))
                        .font(.system(size: 12))
                        .foregroundColor(Theme.inkSecondary)
                }

                if let s = summary {
                    kpiRow(s)
                    if s.papersTotal > 0 {
                        pipelineChart(s)
                    }
                    pipelineHints(s)
                } else {
                    Label(tr("无法读取 index.json", "Cannot read index.json"), systemImage: "exclamationmark.triangle")
                        .foregroundColor(Theme.saffron)
                }

                maintenanceRow

                if let vs = verdicts {
                    verdictList(vs)
                }
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: KPI cards

    private func kpiRow(_ s: StatusSummary) -> some View {
        HStack(spacing: 12) {
            kpiCard(value: "\(s.papersTotal)", label: tr("论文", "Papers"),
                    icon: "doc.text", color: Theme.accent)
            kpiCard(value: "\(s.principles)", label: tr("原则", "Principles"),
                    icon: "lightbulb", color: Theme.emerald)
            kpiCard(value: s.synthesisLastRun ?? tr("从未", "never"),
                    label: tr("上次综合", "Last synthesis"),
                    icon: "square.grid.3x3.topleft.filled", color: Theme.ultraViolet,
                    sub: s.principles == 0 ? nil
                        : s.synthesisStale ? tr("过期 +\(s.newSinceSynthesis)", "stale +\(s.newSinceSynthesis)")
                        : tr("最新", "fresh"),
                    subColor: s.synthesisStale ? Theme.saffron : Theme.emerald)
            Spacer()
        }
    }

    private func kpiCard(value: String, label: String, icon: String, color: Color,
                         sub: String? = nil, subColor: Color = Theme.inkSecondary) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(color)
                Text(label).kwSectionLabel()
            }
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(value)
                    .font(.system(size: 26, weight: .semibold, design: .rounded))
                    .foregroundColor(Theme.ink)
                if let sub = sub {
                    Text(sub)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(subColor)
                }
            }
        }
        .frame(minWidth: 132, alignment: .leading)
        .kwCard()
    }

    // MARK: pipeline chart

    private struct StageDatum: Identifiable {
        let id: String
        let stage: String
        let count: Int
        let color: Color
    }

    private func pipelineChart(_ s: StatusSummary) -> some View {
        let data: [StageDatum] = [
            StageDatum(id: "pending", stage: tr("待读取", "Pending"),
                       count: s.papersByStatus[.pending] ?? 0, color: Theme.inkSecondary),
            StageDatum(id: "l1", stage: tr("已读 L1", "Read · L1"),
                       count: (s.papersByStatus[.l1] ?? 0) + (s.papersByStatus[.l2] ?? 0), color: Theme.accent),
            StageDatum(id: "complete", stage: tr("已蒸馏", "Distilled"),
                       count: s.papersByStatus[.complete] ?? 0, color: Theme.emerald),
            StageDatum(id: "incomplete", stage: tr("不完整", "Incomplete"),
                       count: s.papersByStatus[.incomplete] ?? 0, color: Theme.saffron),
        ]
        return VStack(alignment: .leading, spacing: 10) {
            Text(tr("论文流水线", "Paper pipeline")).kwSectionLabel()
            Chart(data) { d in
                BarMark(
                    x: .value("count", d.count),
                    y: .value("stage", d.stage)
                )
                .foregroundStyle(d.color.opacity(0.85))
                .cornerRadius(4)
                .annotation(position: .trailing, alignment: .leading) {
                    Text("\(d.count)")
                        .font(.system(size: 11, weight: .semibold, design: .rounded))
                        .foregroundColor(Theme.inkSecondary)
                }
            }
            .chartXAxis(.hidden)
            .chartYAxis {
                AxisMarks(preset: .aligned) {
                    AxisValueLabel()
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.inkSecondary)
                }
            }
            .frame(height: 132)
        }
        .frame(maxWidth: 520, alignment: .leading)
        .kwCard()
    }

    // MARK: next-step hints

    @ViewBuilder
    private func pipelineHints(_ s: StatusSummary) -> some View {
        if !s.pendingPapers.isEmpty {
            workList(title: tr("待读取 — 运行 L1", "Pending read — run L1"), ids: s.pendingPapers)
        }
        if !s.l1Papers.isEmpty {
            workList(title: tr("已读取，待蒸馏 — 运行 L2", "Read, awaiting distillation — run L2"), ids: s.l1Papers)
        }
        if s.papersTotal == 0 {
            VStack(alignment: .leading, spacing: 8) {
                Text(tr("开始使用", "Get started")).kwSectionLabel()
                Text(tr("从「论文」页导入一篇 PDF。流程：导入 → L1 忠实读取 → L2 蒸馏原则 → L3 综合 → 按结构检索。",
                        "Import a PDF in Papers. Flow: import → L1 faithful read → L2 distill principles → L3 synthesize → search by structure."))
                    .font(.system(size: 13))
                    .lineSpacing(3)
                    .foregroundColor(Theme.inkSecondary)
            }
            .frame(maxWidth: 520, alignment: .leading)
            .kwCard()
        }
    }

    private func workList(title: String, ids: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).kwSectionLabel()
            VStack(spacing: 1) {
                ForEach(ids, id: \.self) { id in
                    Button {
                        appState.showPaper(id)
                    } label: {
                        HStack {
                            Text(id).font(.system(size: 12.5, design: .monospaced))
                                .foregroundColor(Theme.ink)
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(Theme.inkSecondary)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    if id != ids.last { Divider().overlay(Theme.hairline) }
                }
            }
            .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Theme.card))
            .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Theme.hairline, lineWidth: 1))
        }
        .frame(maxWidth: 520, alignment: .leading)
    }

    // MARK: verify / reindex

    private var maintenanceRow: some View {
        HStack(spacing: 10) {
            Button {
                runVerify()
            } label: {
                Label(tr("校验完整性", "Verify invariants"), systemImage: "checkmark.shield")
            }
            .disabled(pipeline.isBusy)

            Button {
                runReindex()
            } label: {
                Label(tr("重建索引", "Rebuild index"), systemImage: "arrow.triangle.2.circlepath")
            }
            .disabled(pipeline.isBusy)
            .help(tr("从 markdown 重建 index.json 与 .kw/index.db（markdown 为真相）",
                     "Rebuild index.json and .kw/index.db from markdown (markdown is truth)"))

            if let report = reindexReport {
                Text(report)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(Theme.emerald)
            }
            Spacer()
        }
    }

    private func verdictList(_ vs: [Verdict]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(tr("校验结果", "Verification results")).kwSectionLabel()
            VStack(alignment: .leading, spacing: 6) {
                ForEach(vs) { v in
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Image(systemName: v.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(v.passed ? Theme.emerald : Theme.fieryRed)
                        Text(v.checkName)
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundColor(Theme.ink)
                        Text(v.message)
                            .font(.system(size: 12))
                            .foregroundColor(Theme.inkSecondary)
                            .textSelection(.enabled)
                        Spacer()
                    }
                }
            }
            .kwCard()
        }
        .frame(maxWidth: 640, alignment: .leading)
    }

    private func runVerify() {
        guard let ws = appState.workspace else { return }
        verdicts = Verifier.run(workspace: ws)
    }

    private func runReindex() {
        guard let ws = appState.workspace else { return }
        do {
            let (papers, principles) = try ws.reindex()
            reindexReport = tr("已重建：\(papers) 篇论文，\(principles) 条原则",
                               "Rebuilt: \(papers) papers, \(principles) principles")
            appState.reload()
        } catch {
            appState.present(error)
        }
    }
}
