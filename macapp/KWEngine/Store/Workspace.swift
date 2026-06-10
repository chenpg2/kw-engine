//  Workspace.swift
//  KWEngine — deterministic storage substrate.
//  Swift port of kw_engine init.py / ops.py / markdown.py / json_proj.py.
//
//  Conventions (same as the kw CLI):
//  - Markdown is truth; index.json + .kw/index.db are derived.
//  - Paper id = PDF filename stem. Principle id = P-#### (zero-padded).
//  - No silent fallback: validation errors throw, never coerce.

import Foundation

struct PrincipleDraft {
    var title: String
    var abstractionLevel: String
    var problemSignature: [String]
    var mathBasis: [String]
    var mechanism: String
    var rationale: String
    var dataRegime: [String]
    var falsifiablePrediction: String
    var boundaries: String
    var provenance: [String]
    var links: [String]
    var bodyNotes: String?
}

struct StatusSummary {
    var papersTotal: Int
    var papersByStatus: [PaperStatus: Int]
    var principles: Int
    var pendingPapers: [String]      // status == pending (not yet read)
    var l1Papers: [String]           // status == L1 (read, awaiting distillation)
    var synthesisLastRun: String?
    var synthesisStale: Bool
    var newSinceSynthesis: Int
}

struct Workspace {
    let root: URL

    var memoryDir: URL { root.appendingPathComponent("memory") }
    var papersDir: URL { memoryDir.appendingPathComponent("papers") }
    var principlesDir: URL { memoryDir.appendingPathComponent("principles") }
    var synthesisDir: URL { memoryDir.appendingPathComponent("synthesis") }
    var pdfDir: URL { root.appendingPathComponent("paper") }
    var processDir: URL { root.appendingPathComponent("process") }
    var kwDir: URL { root.appendingPathComponent(".kw") }
    var indexPath: URL { memoryDir.appendingPathComponent("index.json") }
    var dbPath: URL { kwDir.appendingPathComponent("index.db") }

    // MARK: - Detection & scaffold (port of init_workspace)

    static func isWorkspace(_ root: URL) -> Bool {
        let fm = FileManager.default
        return fm.fileExists(atPath: root.appendingPathComponent("memory/index.json").path)
            || fm.fileExists(atPath: root.appendingPathComponent("memory/SCHEMA.md").path)
    }

    static func scaffold(at root: URL) throws {
        let fm = FileManager.default
        let dirs = [
            ".kw/logs", "memory/papers", "memory/principles", "memory/synthesis",
            "memory/golden", "paper", "process", "problems",
        ]
        for d in dirs {
            try fm.createDirectory(at: root.appendingPathComponent(d), withIntermediateDirectories: true)
        }
        let writeIfAbsent: (String, String) throws -> Void = { relPath, content in
            let url = root.appendingPathComponent(relPath)
            if !fm.fileExists(atPath: url.path) {
                try content.data(using: .utf8)!.write(to: url, options: .atomic)
            }
        }
        try writeIfAbsent(".kw/config.yaml", Templates.configYAML)
        try writeIfAbsent("memory/index.json", Templates.initialIndexJSON)
        try writeIfAbsent("memory/SCHEMA.md", Templates.schemaMD)
        try writeIfAbsent("process/extract-template.md", Templates.extractTemplateMD)
        try writeIfAbsent("process/distill-rubric.md", Templates.distillRubricMD)
    }

    // MARK: - index.json

    func readIndex() throws -> IndexFile {
        let data = try Data(contentsOf: indexPath)
        do {
            return try JSONDecoder().decode(IndexFile.self, from: data)
        } catch {
            throw StoreError("index.json is invalid: \(error.localizedDescription)")
        }
    }

    func writeIndexAtomic(_ idx: IndexFile) throws {
        let data = try idx.encodedJSON()
        try data.write(to: indexPath, options: .atomic)
    }

    private func writeTextAtomic(_ text: String, to url: URL) throws {
        try text.data(using: .utf8)!.write(to: url, options: .atomic)
    }

    // MARK: - Markdown record I/O (port of markdown.py)

    func paperPath(_ id: String) -> URL { papersDir.appendingPathComponent("\(id).md") }
    func principlePath(_ pid: String) -> URL { principlesDir.appendingPathComponent("\(pid).md") }

    func readPaperFile(_ id: String) throws -> (paper: PaperFull, body: String) {
        let url = paperPath(id)
        let text = try String(contentsOf: url, encoding: .utf8)
        let (yaml, body) = try Frontmatter.splitDocument(text)
        let fm = try Frontmatter.parse(yaml)
        return (try Self.paperFromYaml(fm, file: url.lastPathComponent), body)
    }

    func readPrincipleFile(_ pid: String) throws -> (principle: Principle, body: String) {
        let url = principlePath(pid)
        let text = try String(contentsOf: url, encoding: .utf8)
        let (yaml, body) = try Frontmatter.splitDocument(text)
        let fm = try Frontmatter.parse(yaml)
        return (try Self.principleFromYaml(fm, file: url.lastPathComponent), body)
    }

    static func paperFromYaml(_ fm: [String: YamlValue], file: String) throws -> PaperFull {
        func require(_ key: String) throws -> YamlValue {
            guard let v = fm[key] else { throw StoreError("\(file): missing required field '\(key)'") }
            return v
        }
        guard let id = (try require("id")).stringValue, !id.isEmpty else {
            throw StoreError("\(file): 'id' must be a non-empty string")
        }
        let statusRaw = (try require("status")).stringOrEmpty
        guard let status = PaperStatus(rawValue: statusRaw) else {
            throw StoreError("\(file): invalid status '\(statusRaw)'")
        }
        var bib = Bib()
        if let bibMap = (try require("bib")).mapValue {
            bib.title = bibMap["title"]?.stringOrEmpty ?? ""
            bib.authors = bibMap["authors"]?.stringOrEmpty ?? ""
            bib.venue = bibMap["venue"]?.stringOrEmpty ?? ""
            bib.year = bibMap["year"]?.intValue
        } else {
            throw StoreError("\(file): 'bib' must be a mapping")
        }
        return PaperFull(
            id: id,
            doi: fm["doi"]?.stringValue,
            arxiv: fm["arxiv"]?.stringValue,
            bib: bib,
            problemAddressed: (try require("problem_addressed")).stringOrEmpty,
            methodSummary: (try require("method_summary")).stringOrEmpty,
            mathUsed: (try require("math_used")).stringOrEmpty,
            claimedMechanism: (try require("claimed_mechanism")).stringOrEmpty,
            keyEvidence: (try require("key_evidence")).stringOrEmpty,
            status: status,
            extractTemplateVersion: fm["extract_template_version"]?.stringOrEmpty ?? Templates.extractTemplateVersion
        )
    }

    static func principleFromYaml(_ fm: [String: YamlValue], file: String) throws -> Principle {
        func require(_ key: String) throws -> YamlValue {
            guard let v = fm[key] else { throw StoreError("\(file): missing required field '\(key)'") }
            return v
        }
        guard let id = (try require("id")).stringValue else {
            throw StoreError("\(file): 'id' must be a string")
        }
        try Principle.validateId(id)
        return Principle(
            id: id,
            title: (try require("title")).stringOrEmpty,
            abstractionLevel: (try require("abstraction_level")).stringOrEmpty,
            problemSignature: (try require("problem_signature")).stringList,
            mathBasis: (try require("math_basis")).stringList,
            mechanism: (try require("mechanism")).stringOrEmpty,
            rationale: (try require("rationale")).stringOrEmpty,
            dataRegime: (try require("data_regime")).stringList,
            falsifiablePrediction: (try require("falsifiable_prediction")).stringOrEmpty,
            boundaries: (try require("boundaries")).stringOrEmpty,
            provenance: (try require("provenance")).stringList,
            rubricVersion: fm["rubric_version"]?.stringOrEmpty ?? Templates.rubricVersion,
            links: fm["links"]?.stringList ?? []
        )
    }

    /// Scan memory/papers + memory/principles (strict: throws on the first invalid file).
    func scanMarkdown() throws -> (papers: [PaperFull], principles: [Principle]) {
        let fm = FileManager.default
        func mdFiles(in dir: URL) -> [URL] {
            guard let names = try? fm.contentsOfDirectory(atPath: dir.path) else { return [] }
            return names.filter { $0.hasSuffix(".md") }.sorted().map { dir.appendingPathComponent($0) }
        }
        var papers: [PaperFull] = []
        for url in mdFiles(in: papersDir) {
            let text = try String(contentsOf: url, encoding: .utf8)
            let (yaml, _) = try Frontmatter.splitDocument(text)
            papers.append(try Self.paperFromYaml(try Frontmatter.parse(yaml), file: url.lastPathComponent))
        }
        var principles: [Principle] = []
        for url in mdFiles(in: principlesDir) {
            let text = try String(contentsOf: url, encoding: .utf8)
            let (yaml, _) = try Frontmatter.splitDocument(text)
            principles.append(try Self.principleFromYaml(try Frontmatter.parse(yaml), file: url.lastPathComponent))
        }
        return (papers, principles)
    }

    // MARK: - add_paper (port of ops.add_paper)

    @discardableResult
    func addPaper(id: String, doi: String? = nil, title: String? = nil) throws -> URL {
        var idx = try readIndex()
        let mdPath = paperPath(id)
        if idx.papers.contains(where: { $0.id == id }) {
            return mdPath  // idempotent
        }
        let pairs: [(String, YamlValue)] = [
            ("id", .string(id)),
            ("doi", doi.map { .string($0) } ?? .null),
            ("bib", .map([
                "title": .string(title ?? ""),
                "authors": .string(""),
                "venue": .string(""),
                "year": .null,
            ])),
            ("problem_addressed", .string("")),
            ("method_summary", .string("")),
            ("math_used", .string("")),
            ("claimed_mechanism", .string("")),
            ("key_evidence", .string("")),
            ("status", .string("pending")),
            ("extract_template_version", .string(Templates.extractTemplateVersion)),
        ]
        let body = "\n<!-- Fill in faithful notes below. No abstraction. -->\n"
        try FileManager.default.createDirectory(at: papersDir, withIntermediateDirectories: true)
        try writeTextAtomic(Frontmatter.compose(yaml: Frontmatter.render(pairs), body: body), to: mdPath)

        idx.papers.append(PaperProj(id: id, status: .pending, doi: doi, title: title ?? "", principles: []))
        try writeIndexAtomic(idx)

        SQLiteIndex.syncPaperIfPresent(dbPath: dbPath, id: id, doi: doi, title: title ?? "")
        return mdPath
    }

    /// Import a local PDF into paper/<stem>.pdf and register it (idempotent).
    func importPDF(from source: URL) throws -> String {
        let fm = FileManager.default
        let stem = source.deletingPathExtension().lastPathComponent
        let id = Self.sanitizePaperId(stem)
        guard !id.isEmpty else { throw StoreError("Cannot derive a paper id from \(source.lastPathComponent)") }

        let data = try Data(contentsOf: source)
        guard data.count >= 5, data.prefix(5) == Data("%PDF-".utf8) else {
            throw StoreError("\(source.lastPathComponent) is not a valid PDF (missing %PDF- magic bytes)")
        }
        try fm.createDirectory(at: pdfDir, withIntermediateDirectories: true)
        let dest = pdfDir.appendingPathComponent("\(id).pdf")
        if !fm.fileExists(atPath: dest.path) {
            try data.write(to: dest, options: .atomic)
        }
        try addPaper(id: id)
        return id
    }

    static func sanitizePaperId(_ stem: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-"))
        let mapped = stem.trimmingCharacters(in: .whitespaces).map { ch -> Character in
            if let scalar = ch.unicodeScalars.first, ch.unicodeScalars.count == 1, allowed.contains(scalar) {
                return ch
            }
            return "-"
        }
        return String(mapped).trimmingCharacters(in: CharacterSet(charactersIn: "-"))
    }

    func pdfPath(for paperId: String) -> URL { pdfDir.appendingPathComponent("\(paperId).pdf") }

    // MARK: - L1 write (the kw-reader step: full faithful record)

    /// `indexStatus` lets the index track the pipeline stage (e.g. L1) while the
    /// markdown record keeps its faithful-completeness status (complete/incomplete).
    func writePaperRecord(_ paper: PaperFull, bodyNotes: String, indexStatus: PaperStatus? = nil) throws {
        var pairs: [(String, YamlValue)] = [
            ("id", .string(paper.id)),
            ("doi", paper.doi.map { .string($0) } ?? .null),
        ]
        if let arxiv = paper.arxiv {
            pairs.append(("arxiv", .string(arxiv)))
        }
        pairs.append(contentsOf: [
            ("bib", .map([
                "title": .string(paper.bib.title),
                "authors": .string(paper.bib.authors),
                "venue": .string(paper.bib.venue),
                "year": paper.bib.year.map { .int($0) } ?? .null,
            ])),
            ("problem_addressed", .string(paper.problemAddressed)),
            ("method_summary", .string(paper.methodSummary)),
            ("math_used", .string(paper.mathUsed)),
            ("claimed_mechanism", .string(paper.claimedMechanism)),
            ("key_evidence", .string(paper.keyEvidence)),
            ("status", .string(paper.status.rawValue)),
            ("extract_template_version", .string(paper.extractTemplateVersion)),
        ])
        let body = bodyNotes.hasPrefix("\n") ? bodyNotes : "\n" + bodyNotes
        try writeTextAtomic(Frontmatter.compose(yaml: Frontmatter.render(pairs), body: body), to: paperPath(paper.id))

        let projStatus = indexStatus ?? paper.status
        var idx = try readIndex()
        if let i = idx.papers.firstIndex(where: { $0.id == paper.id }) {
            idx.papers[i].status = projStatus
            idx.papers[i].title = paper.bib.title
            idx.papers[i].doi = paper.doi
        } else {
            idx.papers.append(PaperProj(id: paper.id, status: projStatus, doi: paper.doi,
                                        title: paper.bib.title, principles: []))
        }
        try writeIndexAtomic(idx)
    }

    /// Update a paper's status (and optionally its principle list) in markdown + index.
    func setPaperStatus(_ id: String, status: PaperStatus, addPrinciples: [String] = []) throws {
        let url = paperPath(id)
        let text = try String(contentsOf: url, encoding: .utf8)
        let (yaml, body) = try Frontmatter.splitDocument(text)
        // Targeted line edit on `status:` to preserve the rest of the file verbatim.
        var lines = yaml.components(separatedBy: "\n")
        var replaced = false
        for i in lines.indices {
            if lines[i].hasPrefix("status:") {
                lines[i] = "status: \(status.rawValue)"
                replaced = true
                break
            }
        }
        guard replaced else { throw StoreError("\(id).md: no 'status:' field found") }
        try writeTextAtomic(Frontmatter.compose(yaml: lines.joined(separator: "\n"), body: body), to: url)

        var idx = try readIndex()
        if let i = idx.papers.firstIndex(where: { $0.id == id }) {
            idx.papers[i].status = status
            for pid in addPrinciples where !idx.papers[i].principles.contains(pid) {
                idx.papers[i].principles.append(pid)
            }
            idx.papers[i].principles.sort()
        }
        try writeIndexAtomic(idx)
    }

    // MARK: - add_principle (port of ops.add_principle)

    func allocatePrinciple(_ draft: PrincipleDraft) throws -> String {
        var idx = try readIndex()
        let newCounter = idx.counters.principle + 1
        let pid = String(format: "P-%04d", newCounter)

        let pairs: [(String, YamlValue)] = [
            ("id", .string(pid)),
            ("title", .string(draft.title)),
            ("abstraction_level", .string(draft.abstractionLevel)),
            ("problem_signature", .list(draft.problemSignature.map { .string($0) })),
            ("math_basis", .list(draft.mathBasis.map { .string($0) })),
            ("mechanism", .string(draft.mechanism)),
            ("rationale", .string(draft.rationale)),
            ("data_regime", .list(draft.dataRegime.map { .string($0) })),
            ("falsifiable_prediction", .string(draft.falsifiablePrediction)),
            ("boundaries", .string(draft.boundaries)),
            ("provenance", .list(draft.provenance.map { .string($0) })),
            ("rubric_version", .string(Templates.rubricVersion)),
            ("links", .list(draft.links.map { .string($0) })),
        ]
        var body = "\n<!-- Derivation, evidence quotes, transfer notes. -->\n"
        if let notes = draft.bodyNotes, !notes.isEmpty {
            body = "\n" + notes + "\n"
        }
        try FileManager.default.createDirectory(at: principlesDir, withIntermediateDirectories: true)
        try writeTextAtomic(Frontmatter.compose(yaml: Frontmatter.render(pairs), body: body), to: principlePath(pid))

        idx.counters.principle = newCounter
        idx.principles.append(PrincipleProj(
            id: pid, title: draft.title,
            problemSignature: draft.problemSignature, mathBasis: draft.mathBasis,
            provenance: draft.provenance, rubricVersion: Templates.rubricVersion, links: draft.links))
        try writeIndexAtomic(idx)

        SQLiteIndex.syncPrincipleIfPresent(dbPath: dbPath, pid: pid, draft: draft)
        return pid
    }

    // MARK: - add_link (port of ops.add_link, incl. raw-text insertion)

    func addLink(from fromPid: String, to toPid: String, type: String) throws {
        let linkStr = "\(type):\(toPid)"
        let url = principlePath(fromPid)
        let text = try String(contentsOf: url, encoding: .utf8)
        let (yaml, _) = try Frontmatter.splitDocument(text)
        let fm = try Frontmatter.parse(yaml)
        let existing = fm["links"]?.stringList ?? []
        if !existing.contains(linkStr) {
            let newText = Self.insertLinkInText(text, linkStr: linkStr)
            try writeTextAtomic(newText, to: url)
        }
        var idx = try readIndex()
        if let i = idx.principles.firstIndex(where: { $0.id == fromPid }) {
            if !idx.principles[i].links.contains(linkStr) {
                idx.principles[i].links.append(linkStr)
                try writeIndexAtomic(idx)
            }
        }
        SQLiteIndex.syncLinkIfPresent(dbPath: dbPath, from: fromPid, to: toPid, type: type)
    }

    /// Port of ops._insert_link_in_text — raw edit preserving formatting.
    static func insertLinkInText(_ text: String, linkStr: String) -> String {
        // Case 1: links: []  (empty inline list)
        if let regex = try? NSRegularExpression(pattern: #"(links:\s*)\[\]"#),
           let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) {
            let mutable = NSMutableString(string: text)
            regex.replaceMatches(in: mutable, range: match.range, withTemplate: "$1\n  - \"\(linkStr)\"")
            return mutable as String
        }
        // Case 2: links already has items — append after the last "  - " entry.
        var lines = text.components(separatedBy: "\n")
        var lastLinkIdx = -1
        var inLinks = false
        for (i, line) in lines.enumerated() {
            if line.hasPrefix("links:") { inLinks = true; continue }
            if inLinks {
                if line.hasPrefix("  - ") || line.hasPrefix("- ") {
                    lastLinkIdx = i
                } else if !line.isEmpty && !line.hasPrefix(" ") {
                    break
                }
            }
        }
        if lastLinkIdx >= 0 {
            let indent = lines[lastLinkIdx].hasPrefix("  - ") ? "  " : ""
            lines.insert("\(indent)- \"\(linkStr)\"", at: lastLinkIdx + 1)
            return lines.joined(separator: "\n")
        }
        // Fallback: append a links block before the closing ---.
        if let (yaml, body) = try? Frontmatter.splitDocument(text) {
            var y = yaml
            while y.hasSuffix("\n") || y.hasSuffix(" ") { y.removeLast() }
            y += "\nlinks:\n  - \"\(linkStr)\"\n"
            return Frontmatter.compose(yaml: y, body: body)
        }
        return text
    }

    /// Add provenance entries to an existing principle (dedup-and-link merge ⊕).
    func appendProvenance(to pid: String, entries: [String]) throws {
        let (principle, body) = try readPrincipleFile(pid)
        var p = principle
        var added: [String] = []
        for e in entries where !p.provenance.contains(e) {
            p.provenance.append(e)
            added.append(e)
        }
        guard !added.isEmpty else { return }
        try writePrincipleRecord(p, body: body)

        var idx = try readIndex()
        if let i = idx.principles.firstIndex(where: { $0.id == pid }) {
            idx.principles[i].provenance = p.provenance
            try writeIndexAtomic(idx)
        }
        SQLiteIndex.syncProvenanceIfPresent(dbPath: dbPath, pid: pid, entries: added)
    }

    /// Full re-render of a principle record (normalizes YAML formatting; values preserved).
    func writePrincipleRecord(_ p: Principle, body: String) throws {
        let pairs: [(String, YamlValue)] = [
            ("id", .string(p.id)),
            ("title", .string(p.title)),
            ("abstraction_level", .string(p.abstractionLevel)),
            ("problem_signature", .list(p.problemSignature.map { .string($0) })),
            ("math_basis", .list(p.mathBasis.map { .string($0) })),
            ("mechanism", .string(p.mechanism)),
            ("rationale", .string(p.rationale)),
            ("data_regime", .list(p.dataRegime.map { .string($0) })),
            ("falsifiable_prediction", .string(p.falsifiablePrediction)),
            ("boundaries", .string(p.boundaries)),
            ("provenance", .list(p.provenance.map { .string($0) })),
            ("rubric_version", .string(p.rubricVersion)),
            ("links", .list(p.links.map { .string($0) })),
        ]
        try writeTextAtomic(Frontmatter.compose(yaml: Frontmatter.render(pairs), body: body), to: principlePath(p.id))
    }

    // MARK: - reindex (port of cli.reindex + json_proj.build_index_json)

    @discardableResult
    func reindex() throws -> (papers: Int, principles: Int) {
        let (papers, principles) = try scanMarkdown()

        // Derive paper -> principles from provenance.
        var paperToPrinciples: [String: [String]] = [:]
        for p in papers { paperToPrinciples[p.id] = [] }
        for pr in principles {
            for prov in pr.provenance {
                let pid = paperIdFromProvenance(prov)
                if paperToPrinciples[pid] != nil, !(paperToPrinciples[pid]!.contains(pr.id)) {
                    paperToPrinciples[pid]!.append(pr.id)
                }
            }
        }

        // Preserve synthesis state from the existing index.
        let oldSynthesis = (try? readIndex())?.synthesis ?? SynthesisState(lastRun: nil, nPrinciplesAtLastRun: 0)

        let idx = IndexFile(
            version: 1,
            counters: Counters(principle: principles.count),
            papers: papers.map {
                PaperProj(id: $0.id, status: $0.status, doi: $0.doi, title: $0.bib.title,
                          principles: (paperToPrinciples[$0.id] ?? []).sorted())
            },
            principles: principles.map {
                PrincipleProj(id: $0.id, title: $0.title,
                              problemSignature: $0.problemSignature, mathBasis: $0.mathBasis,
                              provenance: $0.provenance, rubricVersion: $0.rubricVersion, links: $0.links)
            },
            synthesis: oldSynthesis
        )
        try writeIndexAtomic(idx)

        try FileManager.default.createDirectory(at: kwDir, withIntermediateDirectories: true)
        try SQLiteIndex.rebuild(dbPath: dbPath, papers: papers, principles: principles)
        return (papers.count, principles.count)
    }

    // MARK: - Synthesis artifacts

    func readSynthesisDoc(_ name: String) -> String? {
        try? String(contentsOf: synthesisDir.appendingPathComponent(name), encoding: .utf8)
    }

    func writeSynthesisDocs(designSpace: String, contradictions: String, gaps: String, date: String) throws {
        try FileManager.default.createDirectory(at: synthesisDir, withIntermediateDirectories: true)
        try writeTextAtomic(designSpace, to: synthesisDir.appendingPathComponent("design-space.md"))
        try writeTextAtomic(contradictions, to: synthesisDir.appendingPathComponent("contradictions.md"))
        try writeTextAtomic(gaps, to: synthesisDir.appendingPathComponent("gaps.md"))

        var idx = try readIndex()
        idx.synthesis.lastRun = date
        idx.synthesis.nPrinciplesAtLastRun = idx.principles.count
        try writeIndexAtomic(idx)
    }

    // MARK: - Status (mirror of `kw status`)

    func statusSummary() throws -> StatusSummary {
        let idx = try readIndex()
        var byStatus: [PaperStatus: Int] = [:]
        for p in idx.papers { byStatus[p.status, default: 0] += 1 }
        let n = idx.principles.count
        let nAtLast = idx.synthesis.nPrinciplesAtLastRun
        return StatusSummary(
            papersTotal: idx.papers.count,
            papersByStatus: byStatus,
            principles: n,
            pendingPapers: idx.papers.filter { $0.status == .pending }.map { $0.id },
            l1Papers: idx.papers.filter { $0.status == .l1 }.map { $0.id },
            synthesisLastRun: idx.synthesis.lastRun,
            synthesisStale: n > nAtLast,
            newSinceSynthesis: max(0, n - nAtLast)
        )
    }
}
