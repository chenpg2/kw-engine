//  SQLiteIndex.swift
//  KWEngine — derived SQLite index (.kw/index.db), port of kw_engine/store/sqlite.py.
//  Rebuildable from markdown; incremental syncs are best-effort (JSON/markdown is truth).

import Foundation
import SQLite3

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

enum SQLiteIndex {

    static let schemaSQL = """
    CREATE TABLE IF NOT EXISTS papers (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        doi TEXT,
        title TEXT,
        bib_authors TEXT,
        bib_venue TEXT,
        bib_year INTEGER
    );
    CREATE TABLE IF NOT EXISTS principles (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        abstraction_level TEXT,
        mechanism TEXT,
        rationale TEXT,
        falsifiable_prediction TEXT,
        boundaries TEXT,
        rubric_version TEXT
    );
    CREATE TABLE IF NOT EXISTS principle_signatures (
        principle_id TEXT NOT NULL,
        signature TEXT NOT NULL,
        FOREIGN KEY (principle_id) REFERENCES principles(id)
    );
    CREATE TABLE IF NOT EXISTS principle_math_basis (
        principle_id TEXT NOT NULL,
        basis TEXT NOT NULL,
        FOREIGN KEY (principle_id) REFERENCES principles(id)
    );
    CREATE TABLE IF NOT EXISTS principle_provenance (
        principle_id TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        locator TEXT NOT NULL,
        FOREIGN KEY (principle_id) REFERENCES principles(id)
    );
    CREATE TABLE IF NOT EXISTS links (
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        link_type TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES principles(id)
    );
    CREATE TABLE IF NOT EXISTS paper_principles (
        paper_id TEXT NOT NULL,
        principle_id TEXT NOT NULL,
        FOREIGN KEY (paper_id) REFERENCES papers(id),
        FOREIGN KEY (principle_id) REFERENCES principles(id)
    );
    """

    // MARK: - Minimal connection wrapper

    final class DB {
        var handle: OpaquePointer?

        init(path: String) throws {
            if sqlite3_open(path, &handle) != SQLITE_OK {
                let msg = handle.map { String(cString: sqlite3_errmsg($0)) } ?? "unknown"
                sqlite3_close(handle)
                throw StoreError("Cannot open SQLite db: \(msg)")
            }
        }

        deinit { sqlite3_close(handle) }

        func execScript(_ sql: String) throws {
            var err: UnsafeMutablePointer<CChar>?
            if sqlite3_exec(handle, sql, nil, nil, &err) != SQLITE_OK {
                let msg = err.map { String(cString: $0) } ?? "unknown"
                sqlite3_free(err)
                throw StoreError("SQLite error: \(msg)")
            }
        }

        enum Param {
            case text(String)
            case nullableText(String?)
            case int(Int)
            case nullableInt(Int?)
        }

        func run(_ sql: String, _ params: [Param]) throws {
            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(handle, sql, -1, &stmt, nil) == SQLITE_OK else {
                throw StoreError("SQLite prepare failed: \(String(cString: sqlite3_errmsg(handle)))")
            }
            defer { sqlite3_finalize(stmt) }
            try bind(stmt, params)
            guard sqlite3_step(stmt) == SQLITE_DONE else {
                throw StoreError("SQLite step failed: \(String(cString: sqlite3_errmsg(handle)))")
            }
        }

        func queryStrings(_ sql: String, _ params: [Param], columns: Int) throws -> [[String]] {
            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(handle, sql, -1, &stmt, nil) == SQLITE_OK else {
                throw StoreError("SQLite prepare failed: \(String(cString: sqlite3_errmsg(handle)))")
            }
            defer { sqlite3_finalize(stmt) }
            try bind(stmt, params)
            var rows: [[String]] = []
            while sqlite3_step(stmt) == SQLITE_ROW {
                var row: [String] = []
                for col in 0..<Int32(columns) {
                    if let c = sqlite3_column_text(stmt, col) {
                        row.append(String(cString: c))
                    } else {
                        row.append("")
                    }
                }
                rows.append(row)
            }
            return rows
        }

        private func bind(_ stmt: OpaquePointer?, _ params: [Param]) throws {
            for (i, p) in params.enumerated() {
                let idx = Int32(i + 1)
                let rc: Int32
                switch p {
                case .text(let s):
                    rc = sqlite3_bind_text(stmt, idx, s, -1, SQLITE_TRANSIENT)
                case .nullableText(let s):
                    if let s = s {
                        rc = sqlite3_bind_text(stmt, idx, s, -1, SQLITE_TRANSIENT)
                    } else {
                        rc = sqlite3_bind_null(stmt, idx)
                    }
                case .int(let v):
                    rc = sqlite3_bind_int64(stmt, idx, Int64(v))
                case .nullableInt(let v):
                    if let v = v {
                        rc = sqlite3_bind_int64(stmt, idx, Int64(v))
                    } else {
                        rc = sqlite3_bind_null(stmt, idx)
                    }
                }
                guard rc == SQLITE_OK else {
                    throw StoreError("SQLite bind failed at \(idx)")
                }
            }
        }
    }

    // MARK: - Full rebuild (port of rebuild_index_db)

    static func rebuild(dbPath: URL, papers: [PaperFull], principles: [Principle]) throws {
        let fm = FileManager.default
        if fm.fileExists(atPath: dbPath.path) {
            try fm.removeItem(at: dbPath)
        }
        let db = try DB(path: dbPath.path)
        try db.execScript(schemaSQL)
        try db.execScript("BEGIN;")

        for p in papers {
            try db.run(
                "INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)",
                [.text(p.id), .text(p.status.rawValue), .nullableText(p.doi), .text(p.bib.title),
                 .text(p.bib.authors), .text(p.bib.venue), .nullableInt(p.bib.year)])
        }

        var paperToPrinciples: [String: [String]] = [:]
        for p in papers { paperToPrinciples[p.id] = [] }

        for pr in principles {
            try db.run(
                "INSERT INTO principles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [.text(pr.id), .text(pr.title), .text(pr.abstractionLevel), .text(pr.mechanism),
                 .text(pr.rationale), .text(pr.falsifiablePrediction), .text(pr.boundaries),
                 .text(pr.rubricVersion)])
            for sig in pr.problemSignature {
                try db.run("INSERT INTO principle_signatures VALUES (?, ?)", [.text(pr.id), .text(sig)])
            }
            for basis in pr.mathBasis {
                try db.run("INSERT INTO principle_math_basis VALUES (?, ?)", [.text(pr.id), .text(basis)])
            }
            for prov in pr.provenance {
                let paperId = paperIdFromProvenance(prov)
                let locator = locatorFromProvenance(prov)
                try db.run("INSERT INTO principle_provenance VALUES (?, ?, ?)",
                           [.text(pr.id), .text(paperId), .text(locator)])
                if paperToPrinciples[paperId] != nil, !(paperToPrinciples[paperId]!.contains(pr.id)) {
                    paperToPrinciples[paperId]!.append(pr.id)
                }
            }
            for linkStr in pr.links {
                if let le = LinkEntry(fromString: linkStr) {
                    try db.run("INSERT INTO links VALUES (?, ?, ?)",
                               [.text(pr.id), .text(le.target), .text(le.linkType)])
                }
            }
        }

        for (paperId, pids) in paperToPrinciples {
            for pid in pids {
                try db.run("INSERT INTO paper_principles VALUES (?, ?)", [.text(paperId), .text(pid)])
            }
        }
        try db.execScript("COMMIT;")
    }

    static func locatorFromProvenance(_ prov: String) -> String {
        let parts = prov.split(maxSplits: 1, whereSeparator: { $0 == " " || $0 == "\t" })
        return parts.count > 1 ? String(parts[1]) : ""
    }

    // MARK: - Best-effort incremental syncs (mirror ops.py: silent if db absent/broken)

    static func syncPaperIfPresent(dbPath: URL, id: String, doi: String?, title: String) {
        guard FileManager.default.fileExists(atPath: dbPath.path) else { return }
        guard let db = try? DB(path: dbPath.path) else { return }
        try? db.run(
            "INSERT OR IGNORE INTO papers (id, status, doi, title, bib_authors, bib_venue, bib_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [.text(id), .text("pending"), .nullableText(doi), .text(title), .text(""), .text(""), .nullableInt(nil)])
    }

    static func syncPrincipleIfPresent(dbPath: URL, pid: String, draft: PrincipleDraft) {
        guard FileManager.default.fileExists(atPath: dbPath.path) else { return }
        guard let db = try? DB(path: dbPath.path) else { return }
        try? db.run(
            "INSERT OR IGNORE INTO principles (id, title, abstraction_level, mechanism, rationale, falsifiable_prediction, boundaries, rubric_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [.text(pid), .text(draft.title), .text(draft.abstractionLevel), .text(draft.mechanism),
             .text(draft.rationale), .text(draft.falsifiablePrediction), .text(draft.boundaries),
             .text(Templates.rubricVersion)])
        for sig in draft.problemSignature {
            try? db.run("INSERT INTO principle_signatures (principle_id, signature) VALUES (?, ?)",
                        [.text(pid), .text(sig)])
        }
        for basis in draft.mathBasis {
            try? db.run("INSERT INTO principle_math_basis (principle_id, basis) VALUES (?, ?)",
                        [.text(pid), .text(basis)])
        }
        for prov in draft.provenance {
            let paperId = paperIdFromProvenance(prov)
            try? db.run("INSERT INTO principle_provenance (principle_id, paper_id, locator) VALUES (?, ?, ?)",
                        [.text(pid), .text(paperId), .text(locatorFromProvenance(prov))])
            try? db.run("INSERT OR IGNORE INTO paper_principles (paper_id, principle_id) VALUES (?, ?)",
                        [.text(paperId), .text(pid)])
        }
        for linkStr in draft.links {
            if let le = LinkEntry(fromString: linkStr) {
                try? db.run("INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                            [.text(pid), .text(le.target), .text(le.linkType)])
            }
        }
    }

    static func syncLinkIfPresent(dbPath: URL, from: String, to: String, type: String) {
        guard FileManager.default.fileExists(atPath: dbPath.path) else { return }
        guard let db = try? DB(path: dbPath.path) else { return }
        try? db.run("INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                    [.text(from), .text(to), .text(type)])
    }

    static func syncProvenanceIfPresent(dbPath: URL, pid: String, entries: [String]) {
        guard FileManager.default.fileExists(atPath: dbPath.path) else { return }
        guard let db = try? DB(path: dbPath.path) else { return }
        for prov in entries {
            let paperId = paperIdFromProvenance(prov)
            try? db.run("INSERT INTO principle_provenance (principle_id, paper_id, locator) VALUES (?, ?, ?)",
                        [.text(pid), .text(paperId), .text(locatorFromProvenance(prov))])
            try? db.run("INSERT OR IGNORE INTO paper_principles (paper_id, principle_id) VALUES (?, ?)",
                        [.text(paperId), .text(pid)])
        }
    }
}
