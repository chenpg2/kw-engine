//  Pipeline.swift
//  KWEngine — the reasoning pipeline: L1 read → L2 distill → L3 synthesize → Ask.
//  LLM does the reasoning; Workspace does the deterministic storage.
//  Invalid model output is surfaced (logged/thrown), never silently coerced.

import Foundation
import PDFKit

// MARK: - Typed model responses

struct L1Response: Decodable {
    var doi: String?
    var arxiv: String?
    var bibTitle = ""
    var bibAuthors = ""
    var bibVenue = ""
    var bibYear: Int?
    var problemAddressed = ""
    var methodSummary = ""
    var mathUsed = ""
    var claimedMechanism = ""
    var keyEvidence = ""
    var status = "complete"
    var notes = ""

    enum CodingKeys: String, CodingKey {
        case doi, arxiv, bib, status, notes
        case problemAddressed = "problem_addressed"
        case methodSummary = "method_summary"
        case mathUsed = "math_used"
        case claimedMechanism = "claimed_mechanism"
        case keyEvidence = "key_evidence"
    }
    enum BibKeys: String, CodingKey { case title, authors, venue, year }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        doi = (try? c.decodeIfPresent(String.self, forKey: .doi)).flatMap { $0 }
        arxiv = (try? c.decodeIfPresent(String.self, forKey: .arxiv)).flatMap { $0 }
        if let bib = try? c.nestedContainer(keyedBy: BibKeys.self, forKey: .bib) {
            bibTitle = bib.flexString(.title)
            bibAuthors = bib.flexString(.authors)
            bibVenue = bib.flexString(.venue)
            bibYear = bib.flexInt(.year)
        }
        problemAddressed = c.flexString(.problemAddressed)
        methodSummary = c.flexString(.methodSummary)
        mathUsed = c.flexString(.mathUsed)
        claimedMechanism = c.flexString(.claimedMechanism)
        keyEvidence = c.flexString(.keyEvidence)
        status = c.flexString(.status)
        notes = c.flexString(.notes)
    }
}

struct L2DraftResponse: Decodable {
    var title = ""
    var abstractionLevel = ""
    var problemSignature: [String] = []
    var mathBasis: [String] = []
    var mechanism = ""
    var rationale = ""
    var dataRegime: [String] = []
    var falsifiablePrediction = ""
    var boundaries = ""
    var provenance: [String] = []
    var links: [String] = []
    var notes = ""

    enum CodingKeys: String, CodingKey {
        case title, mechanism, rationale, boundaries, provenance, links, notes
        case abstractionLevel = "abstraction_level"
        case problemSignature = "problem_signature"
        case mathBasis = "math_basis"
        case dataRegime = "data_regime"
        case falsifiablePrediction = "falsifiable_prediction"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = c.flexString(.title)
        abstractionLevel = c.flexString(.abstractionLevel)
        problemSignature = c.flexStringList(.problemSignature)
        mathBasis = c.flexStringList(.mathBasis)
        mechanism = c.flexString(.mechanism)
        rationale = c.flexString(.rationale)
        dataRegime = c.flexStringList(.dataRegime)
        falsifiablePrediction = c.flexString(.falsifiablePrediction)
        boundaries = c.flexString(.boundaries)
        provenance = c.flexStringList(.provenance)
        links = c.flexStringList(.links)
        notes = c.flexString(.notes)
    }
}

struct L2Update: Decodable {
    var pid = ""
    var addProvenance: [String] = []
    var reason = ""

    enum CodingKeys: String, CodingKey {
        case pid, reason
        case addProvenance = "add_provenance"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        pid = c.flexString(.pid)
        addProvenance = c.flexStringList(.addProvenance)
        reason = c.flexString(.reason)
    }
}

struct L2Response: Decodable {
    var principles: [L2DraftResponse] = []
    var existingUpdates: [L2Update] = []
    var skipped: [String] = []

    enum CodingKeys: String, CodingKey {
        case principles, skipped
        case existingUpdates = "existing_updates"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        principles = (try? c.decodeIfPresent([L2DraftResponse].self, forKey: .principles)).flatMap { $0 } ?? []
        existingUpdates = (try? c.decodeIfPresent([L2Update].self, forKey: .existingUpdates)).flatMap { $0 } ?? []
        skipped = c.flexStringList(.skipped)
    }
}

struct L3Link: Decodable {
    var from = ""
    var to = ""
    var type = ""

    enum CodingKeys: String, CodingKey { case from, to, type }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        from = c.flexString(.from)
        to = c.flexString(.to)
        type = c.flexString(.type)
    }
}

struct L3Response: Decodable {
    var designSpace = ""
    var contradictions = ""
    var gaps = ""
    var links: [L3Link] = []
    var topGaps: [String] = []

    enum CodingKeys: String, CodingKey {
        case contradictions, gaps, links
        case designSpace = "design_space"
        case topGaps = "top_gaps"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        designSpace = c.flexString(.designSpace)
        contradictions = c.flexString(.contradictions)
        gaps = c.flexString(.gaps)
        links = (try? c.decodeIfPresent([L3Link].self, forKey: .links)).flatMap { $0 } ?? []
        topGaps = c.flexStringList(.topGaps)
    }
}

struct AskExtractResponse: Decodable {
    var problemSignature: [String] = []
    var mathBasis: [String] = []
    var query = ""

    enum CodingKeys: String, CodingKey {
        case query
        case problemSignature = "problem_signature"
        case mathBasis = "math_basis"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        problemSignature = c.flexStringList(.problemSignature)
        mathBasis = c.flexStringList(.mathBasis)
        query = c.flexString(.query)
    }
}

struct AskResult {
    var signature: [String]
    var mathBasis: [String]
    var answer: String
    var hits: [SearchHit]
}

// MARK: - Pipeline

@MainActor
final class Pipeline: ObservableObject {

    struct LogLine: Identifiable {
        enum Level { case info, warn, error, success }
        let id = UUID()
        let time = Date()
        let level: Level
        let text: String
    }

    @Published var isBusy = false
    @Published var activity = ""
    @Published var log: [LogLine] = []

    func clearLog() { log = [] }
    private func info(_ s: String) { log.append(LogLine(level: .info, text: s)) }
    private func warn(_ s: String) { log.append(LogLine(level: .warn, text: s)) }
    private func errorLine(_ s: String) { log.append(LogLine(level: .error, text: s)) }
    private func success(_ s: String) { log.append(LogLine(level: .success, text: s)) }

    func makeClient() throws -> LLMClient {
        let settings = LLMSettings.load()
        guard !settings.baseURL.isEmpty else {
            throw LLMError(tr("尚未配置 API 地址 — 请打开设置填写 Base URL", "API base URL not configured — open Settings"))
        }
        guard !settings.strongModel.isEmpty else {
            throw LLMError(tr("尚未配置模型 ID — 请打开设置", "Model id not configured — open Settings"))
        }
        guard let key = KeychainStore.loadAPIKey(), !key.isEmpty else {
            throw LLMError(tr("尚未配置 API Key — 请打开设置", "API key not configured — open Settings"))
        }
        return LLMClient(settings: settings, apiKey: key)
    }

    private func beginRun(_ what: String) throws {
        guard !isBusy else { throw LLMError(tr("已有任务在运行", "A pipeline run is already in progress")) }
        isBusy = true
        activity = what
    }

    private func endRun() {
        isBusy = false
        activity = ""
    }

    private static var today: String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f.string(from: Date())
    }

    // MARK: PDF text extraction (PDFKit)

    nonisolated static func extractPDFText(url: URL, maxChars: Int) throws -> String {
        guard let doc = PDFDocument(url: url) else {
            throw StoreError("FAIL: cannot parse \(url.lastPathComponent)")
        }
        var out = ""
        for i in 0..<doc.pageCount {
            guard let page = doc.page(at: i) else { continue }
            out += "\n\n[page \(i + 1)]\n"
            out += page.string ?? ""
            if out.count > maxChars { break }
        }
        if out.count > maxChars {
            out = String(out.prefix(maxChars)) + "\n\n[TRUNCATED — remainder of the PDF omitted]"
        }
        let stripped = out.trimmingCharacters(in: .whitespacesAndNewlines)
        guard stripped.count > 100 else {
            throw StoreError("FAIL: no extractable text in \(url.lastPathComponent) (scanned PDF without OCR?)")
        }
        return out
    }

    // MARK: L1 — faithful read (kw-reader)

    func runL1(workspace: Workspace, paperId: String) async throws {
        try beginRun("L1 · \(paperId)")
        defer { endRun() }
        let client = try makeClient()
        let model = client.settings.fastModelEffective

        let pdfURL = workspace.pdfPath(for: paperId)
        guard FileManager.default.fileExists(atPath: pdfURL.path) else {
            throw StoreError(tr("找不到 paper/\(paperId).pdf — 请先导入 PDF", "paper/\(paperId).pdf not found — import the PDF first"))
        }
        info("[L1] extracting text from paper/\(paperId).pdf …")
        let maxChars = client.settings.maxPDFChars
        let text = try await Task.detached(priority: .userInitiated) {
            try Pipeline.extractPDFText(url: pdfURL, maxChars: maxChars)
        }.value
        info("[L1] \(text.count) chars → \(model)")

        let resp = try await client.completeJSON(
            L1Response.self,
            system: Prompts.l1System,
            user: Prompts.l1User(paperId: paperId, pdfText: text),
            model: model
        )

        let recordStatus: PaperStatus = resp.status.lowercased() == "incomplete" ? .incomplete : .complete
        let paper = PaperFull(
            id: paperId,
            doi: Self.normalizeOptional(resp.doi),
            arxiv: Self.normalizeOptional(resp.arxiv),
            bib: Bib(title: resp.bibTitle, authors: resp.bibAuthors, venue: resp.bibVenue, year: resp.bibYear),
            problemAddressed: resp.problemAddressed,
            methodSummary: resp.methodSummary,
            mathUsed: resp.mathUsed,
            claimedMechanism: resp.claimedMechanism,
            keyEvidence: resp.keyEvidence,
            status: recordStatus
        )
        // Record carries its faithful-completeness status; the index tracks pipeline stage L1.
        try workspace.writePaperRecord(paper, bodyNotes: resp.notes, indexStatus: .l1)

        let unknowns = [
            ("problem_addressed", resp.problemAddressed), ("method_summary", resp.methodSummary),
            ("math_used", resp.mathUsed), ("claimed_mechanism", resp.claimedMechanism),
            ("key_evidence", resp.keyEvidence),
        ].filter { $0.1.contains("UNKNOWN") || $0.1.isEmpty }.map { $0.0 }
        if !unknowns.isEmpty {
            warn("[L1] UNKNOWN/empty fields: \(unknowns.joined(separator: ", "))")
        }
        success("[L1] wrote memory/papers/\(paperId).md (record: \(recordStatus.rawValue), index: L1)")
    }

    // MARK: L2 — distill (kw-distiller)

    @discardableResult
    func runL2(workspace: Workspace, paperId: String) async throws -> [String] {
        try beginRun("L2 · \(paperId)")
        defer { endRun() }
        let client = try makeClient()
        let model = client.settings.strongModel

        let l1Text = try String(contentsOf: workspace.paperPath(paperId), encoding: .utf8)
        let idx = try workspace.readIndex()
        let knownPaperIds = Set(idx.papers.map { $0.id })
        var existingPids = Set(idx.principles.map { $0.id })

        let projections: [[String: Any]] = idx.principles.map {
            ["id": $0.id, "title": $0.title,
             "problem_signature": $0.problemSignature, "math_basis": $0.mathBasis]
        }
        let projData = try JSONSerialization.data(withJSONObject: projections, options: [.prettyPrinted])
        let projJSON = String(data: projData, encoding: .utf8) ?? "[]"

        info("[L2] distilling \(paperId) with \(model) (\(existingPids.count) existing principles for dedup)")
        let resp = try await client.completeJSON(
            L2Response.self,
            system: Prompts.l2System,
            user: Prompts.l2User(paperId: paperId, l1Markdown: l1Text, existingProjectionsJSON: projJSON),
            model: model
        )

        for reason in resp.skipped {
            info("[L2] model skipped an idea: \(reason)")
        }

        var createdPids: [String] = []
        for draft in resp.principles {
            // No silent fallback: incomplete load-bearing fields → reject, with the reason logged.
            var missing: [String] = []
            if draft.title.isEmpty { missing.append("title") }
            if draft.abstractionLevel.isEmpty { missing.append("abstraction_level") }
            if draft.problemSignature.isEmpty { missing.append("problem_signature") }
            if draft.mechanism.isEmpty { missing.append("mechanism") }
            if draft.rationale.isEmpty { missing.append("rationale") }
            if draft.falsifiablePrediction.isEmpty { missing.append("falsifiable_prediction") }
            guard missing.isEmpty else {
                errorLine("[L2] rejected draft '\(draft.title)': empty \(missing.joined(separator: ", "))")
                continue
            }
            let provenance = repairProvenance(draft.provenance, paperId: paperId, knownPaperIds: knownPaperIds)
            guard !provenance.isEmpty else {
                errorLine("[L2] rejected draft '\(draft.title)': no resolvable provenance")
                continue
            }
            var links: [String] = []
            for link in draft.links {
                if let le = LinkEntry(fromString: link),
                   existingPids.contains(le.target),
                   LinkType(rawValue: le.linkType) != nil {
                    links.append(link)
                } else {
                    warn("[L2] dropped link '\(link)' on '\(draft.title)' (unknown target or type)")
                }
            }
            let pid = try workspace.allocatePrinciple(PrincipleDraft(
                title: draft.title,
                abstractionLevel: draft.abstractionLevel,
                problemSignature: draft.problemSignature,
                mathBasis: draft.mathBasis,
                mechanism: draft.mechanism,
                rationale: draft.rationale,
                dataRegime: draft.dataRegime,
                falsifiablePrediction: draft.falsifiablePrediction,
                boundaries: draft.boundaries,
                provenance: provenance,
                links: links,
                bodyNotes: draft.notes.isEmpty ? nil : draft.notes
            ))
            existingPids.insert(pid)
            createdPids.append(pid)
            success("[L2] \(pid) — \(draft.title)")
        }

        for update in resp.existingUpdates {
            guard existingPids.contains(update.pid) else {
                warn("[L2] dropped update for unknown principle '\(update.pid)'")
                continue
            }
            let entries = repairProvenance(update.addProvenance, paperId: paperId, knownPaperIds: knownPaperIds)
            guard !entries.isEmpty else {
                warn("[L2] update for \(update.pid) had no resolvable provenance")
                continue
            }
            try workspace.appendProvenance(to: update.pid, entries: entries)
            success("[L2] \(update.pid) ← provenance \(entries.joined(separator: "; ")) (\(update.reason))")
        }

        // Paper is distilled: index status complete + principle list.
        var idx2 = try workspace.readIndex()
        if let i = idx2.papers.firstIndex(where: { $0.id == paperId }) {
            idx2.papers[i].status = .complete
            for pid in createdPids where !idx2.papers[i].principles.contains(pid) {
                idx2.papers[i].principles.append(pid)
            }
            idx2.papers[i].principles.sort()
            try workspace.writeIndexAtomic(idx2)
        }

        if createdPids.isEmpty && resp.existingUpdates.isEmpty {
            warn("[L2] no principles created for \(paperId)")
        }
        return createdPids
    }

    /// Provenance repair is deterministic and logged — entries that cannot resolve are dropped loudly.
    private func repairProvenance(_ entries: [String], paperId: String, knownPaperIds: Set<String>) -> [String] {
        var out: [String] = []
        for raw in entries {
            let e = raw.trimmingCharacters(in: .whitespaces)
            if e.isEmpty { continue }
            let refId = paperIdFromProvenance(e)
            if knownPaperIds.contains(refId) {
                out.append(e)
            } else if e.hasPrefix("§") || e.hasPrefix("Fig") || e.hasPrefix("fig") || e.hasPrefix("p.")
                        || e.hasPrefix("Table") || e.hasPrefix("Sec") {
                info("[L2] repaired locator-only provenance '\(e)' → '\(paperId) \(e)'")
                out.append("\(paperId) \(e)")
            } else {
                warn("[L2] dropped provenance '\(e)' (paper id '\(refId)' not in library)")
            }
        }
        return out
    }

    // MARK: L3 — synthesize (kw-synthesizer)

    func runL3(workspace: Workspace) async throws {
        try beginRun("L3 · synthesis")
        defer { endRun() }
        let client = try makeClient()
        let model = client.settings.strongModel

        let (_, principles) = try workspace.scanMarkdown()
        guard !principles.isEmpty else {
            throw StoreError(tr("库中还没有原则，先处理几篇论文", "No principles in the library yet — process some papers first"))
        }
        let dump: [[String: Any]] = principles.map { p in
            [
                "id": p.id, "title": p.title, "abstraction_level": p.abstractionLevel,
                "problem_signature": p.problemSignature, "math_basis": p.mathBasis,
                "mechanism": p.mechanism, "rationale": p.rationale,
                "data_regime": p.dataRegime, "falsifiable_prediction": p.falsifiablePrediction,
                "boundaries": p.boundaries, "provenance": p.provenance, "links": p.links,
            ]
        }
        let dumpData = try JSONSerialization.data(withJSONObject: dump, options: [.prettyPrinted])
        let dumpJSON = String(data: dumpData, encoding: .utf8) ?? "[]"

        info("[L3] synthesizing \(principles.count) principles with \(model)")
        let resp = try await client.completeJSON(
            L3Response.self,
            system: Prompts.l3System,
            user: Prompts.l3User(today: Self.today, principlesJSON: dumpJSON),
            model: model
        )

        guard !resp.designSpace.isEmpty, !resp.gaps.isEmpty else {
            throw LLMError("Model returned empty synthesis documents — nothing was written")
        }
        var contradictions = resp.contradictions
        if contradictions.isEmpty {
            warn("[L3] model returned empty contradictions document; writing an explicit 'none' record")
            contradictions = "# Contradictions\n\n_No contradictions identified in this synthesis run (\(Self.today))._\n"
        }

        let pids = Set(principles.map { $0.id })
        var applied = 0
        for link in resp.links {
            guard pids.contains(link.from), pids.contains(link.to), link.from != link.to,
                  LinkType(rawValue: link.type) != nil else {
                warn("[L3] dropped invalid link \(link.from) -\(link.type)-> \(link.to)")
                continue
            }
            try workspace.addLink(from: link.from, to: link.to, type: link.type)
            applied += 1
        }

        try workspace.writeSynthesisDocs(
            designSpace: resp.designSpace,
            contradictions: contradictions,
            gaps: resp.gaps,
            date: Self.today
        )
        success("[L3] wrote design-space.md, contradictions.md, gaps.md · \(applied) links applied")
        for (i, gap) in resp.topGaps.prefix(3).enumerated() {
            info("[L3] top gap \(i + 1): \(gap)")
        }
    }

    // MARK: Ask — new problem → structure search → matched mechanism

    func ask(workspace: Workspace, question: String) async throws -> AskResult {
        try beginRun("Ask")
        defer { endRun() }
        let client = try makeClient()

        info("[ask] extracting problem structure …")
        let extract = try await client.completeJSON(
            AskExtractResponse.self,
            system: Prompts.askExtractSystem,
            user: question,
            model: client.settings.fastModelEffective
        )
        let queryText = ([extract.query] + extract.problemSignature + extract.mathBasis).joined(separator: " ")
        info("[ask] signature: \(extract.problemSignature.joined(separator: " · "))")

        let hits = SearchEngine.search(workspace: workspace, query: queryText, topK: 10)
        guard !hits.isEmpty else {
            return AskResult(
                signature: extract.problemSignature,
                mathBasis: extract.mathBasis,
                answer: tr(
                    "库中没有与该问题结构匹配的原则 — 这是当前知识库的一个空白（gap）。可以围绕该结构补充文献后再试。",
                    "No principle in the library matches this problem structure — that is a gap in the current knowledge base. Acquire literature around this structure and try again."
                ),
                hits: []
            )
        }

        var records = ""
        for hit in hits.prefix(5) {
            if let text = try? String(contentsOf: workspace.principlePath(hit.id), encoding: .utf8) {
                records += "\n### \(hit.id) (score \(hit.score))\n\n\(text)\n"
            }
        }
        info("[ask] composing answer from \(min(5, hits.count)) matched principles …")
        let answer = try await client.complete(
            system: Prompts.askComposeSystem,
            user: Prompts.askComposeUser(question: question, records: records),
            model: client.settings.strongModel
        )
        success("[ask] done")
        return AskResult(signature: extract.problemSignature, mathBasis: extract.mathBasis, answer: answer, hits: hits)
    }

    private static func normalizeOptional(_ s: String?) -> String? {
        guard var v = s?.trimmingCharacters(in: .whitespacesAndNewlines), !v.isEmpty else { return nil }
        if v.lowercased() == "null" || v == "UNKNOWN" { return nil }
        if v.hasPrefix("https://doi.org/") { v = String(v.dropFirst("https://doi.org/".count)) }
        return v
    }
}
