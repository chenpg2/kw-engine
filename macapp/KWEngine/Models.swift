//  Models.swift
//  KWEngine — Swift mirror of kw_engine/models.py (SCHEMA §1–§5).
//  Markdown is truth; index.json + SQLite are derived.

import Foundation

// MARK: - Enums

enum PaperStatus: String, Codable, CaseIterable {
    case pending
    case l1 = "L1"
    case l2 = "L2"
    case complete
    case incomplete
}

enum LinkType: String, Codable, CaseIterable {
    case generalizes
    case specializes
    case composes
    case composedBy = "composed-by"
    case contrasts
    case contradicts
    case appliesTo = "applies_to"
}

/// Extract paper id from provenance like "gkaf1205 §3.2" or "ao-decomposition[Ao2003] §II".
func paperIdFromProvenance(_ prov: String) -> String {
    let token = prov.split(whereSeparator: { $0 == " " || $0 == "\t" || $0 == "\n" }).first.map(String.init) ?? prov
    if let bracket = token.firstIndex(of: "[") {
        return String(token[..<bracket])
    }
    return token
}

struct StoreError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
    init(_ message: String) { self.message = message }
}

// MARK: - Layer-1 / Layer-2 full records (markdown frontmatter)

struct Bib: Equatable {
    var title: String = ""
    var authors: String = ""
    var venue: String = ""
    var year: Int?
}

struct PaperFull: Identifiable {
    var id: String
    var doi: String?
    var arxiv: String?
    var bib: Bib
    var problemAddressed: String
    var methodSummary: String
    var mathUsed: String
    var claimedMechanism: String
    var keyEvidence: String
    var status: PaperStatus
    var extractTemplateVersion: String = "extract-template@v1"
}

struct Principle: Identifiable {
    var id: String
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
    var rubricVersion: String = "distill-rubric@v1"
    var links: [String] = []

    static func validateId(_ v: String) throws {
        let digits = v.dropFirst(2)
        guard v.hasPrefix("P-"), v.count == 6, digits.allSatisfy({ $0.isNumber }) else {
            throw StoreError("Principle id must be P-#### format, got: \(v)")
        }
    }
}

struct LinkEntry {
    var linkType: String
    var target: String

    init?(fromString s: String) {
        guard let colon = s.firstIndex(of: ":") else { return nil }
        linkType = String(s[..<colon])
        target = String(s[s.index(after: colon)...])
    }

    var asString: String { "\(linkType):\(target)" }
}

// MARK: - index.json projections (kw_engine SCHEMA §5)

struct PaperProj: Identifiable, Codable {
    var id: String
    var status: PaperStatus
    var doi: String?
    var title: String
    var principles: [String]

    enum CodingKeys: String, CodingKey { case id, status, doi, title, principles }

    init(id: String, status: PaperStatus, doi: String?, title: String, principles: [String]) {
        self.id = id
        self.status = status
        self.doi = doi
        self.title = title
        self.principles = principles
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        status = try c.decode(PaperStatus.self, forKey: .status)
        doi = try c.decodeIfPresent(String.self, forKey: .doi)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        principles = try c.decodeIfPresent([String].self, forKey: .principles) ?? []
    }

    // Explicit null for doi, matching Python json.dumps of None.
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(status, forKey: .status)
        if let doi = doi { try c.encode(doi, forKey: .doi) } else { try c.encodeNil(forKey: .doi) }
        try c.encode(title, forKey: .title)
        try c.encode(principles, forKey: .principles)
    }
}

struct PrincipleProj: Identifiable, Codable {
    var id: String
    var title: String
    var problemSignature: [String]
    var mathBasis: [String]
    var provenance: [String]
    var rubricVersion: String
    var links: [String]

    enum CodingKeys: String, CodingKey {
        case id, title
        case problemSignature = "problem_signature"
        case mathBasis = "math_basis"
        case provenance
        case rubricVersion = "rubric_version"
        case links
    }

    init(id: String, title: String, problemSignature: [String], mathBasis: [String],
         provenance: [String], rubricVersion: String, links: [String]) {
        self.id = id
        self.title = title
        self.problemSignature = problemSignature
        self.mathBasis = mathBasis
        self.provenance = provenance
        self.rubricVersion = rubricVersion
        self.links = links
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        problemSignature = try c.decodeIfPresent([String].self, forKey: .problemSignature) ?? []
        mathBasis = try c.decodeIfPresent([String].self, forKey: .mathBasis) ?? []
        provenance = try c.decodeIfPresent([String].self, forKey: .provenance) ?? []
        rubricVersion = try c.decodeIfPresent(String.self, forKey: .rubricVersion) ?? ""
        links = try c.decodeIfPresent([String].self, forKey: .links) ?? []
    }
}

struct SynthesisState: Codable {
    var lastRun: String?
    var nPrinciplesAtLastRun: Int

    enum CodingKeys: String, CodingKey {
        case lastRun = "last_run"
        case nPrinciplesAtLastRun = "n_principles_at_last_run"
    }

    init(lastRun: String?, nPrinciplesAtLastRun: Int) {
        self.lastRun = lastRun
        self.nPrinciplesAtLastRun = nPrinciplesAtLastRun
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        lastRun = try c.decodeIfPresent(String.self, forKey: .lastRun)
        nPrinciplesAtLastRun = try c.decodeIfPresent(Int.self, forKey: .nPrinciplesAtLastRun) ?? 0
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        if let lastRun = lastRun { try c.encode(lastRun, forKey: .lastRun) } else { try c.encodeNil(forKey: .lastRun) }
        try c.encode(nPrinciplesAtLastRun, forKey: .nPrinciplesAtLastRun)
    }
}

struct Counters: Codable {
    var principle: Int
}

struct IndexFile: Codable {
    var version: Int
    var counters: Counters
    var papers: [PaperProj]
    var principles: [PrincipleProj]
    var synthesis: SynthesisState

    enum CodingKeys: String, CodingKey { case version, counters, papers, principles, synthesis }

    static var empty: IndexFile {
        IndexFile(version: 1,
                  counters: Counters(principle: 0),
                  papers: [],
                  principles: [],
                  synthesis: SynthesisState(lastRun: nil, nPrinciplesAtLastRun: 0))
    }

    func encodedJSON() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
        return try encoder.encode(self)
    }
}
