//  SearchEngine.swift
//  KWEngine — structure-indexed principle search, port of kw_engine/store/search.py.
//
//  Scores each principle by counting how many query tokens appear as substrings
//  in its problem_signature or math_basis (case-insensitive).
//  Strategy: SQLite (.kw/index.db) first, index.json fallback.

import Foundation

struct SearchHit: Identifiable {
    var id: String        // principle id
    var title: String
    var score: Int
}

enum SearchEngine {

    /// Split text into lowercase tokens on whitespace and hyphens.
    static func tokenize(_ text: String) -> [String] {
        text.lowercased()
            .split(whereSeparator: { $0 == "-" || $0.isWhitespace || $0 == "\n" })
            .map(String.init)
            .filter { !$0.isEmpty }
    }

    static func search(workspace: Workspace, query: String, topK: Int = 10) -> [SearchHit] {
        let tokens = tokenize(query)
        if tokens.isEmpty { return [] }
        if let hits = searchViaSQLite(dbPath: workspace.dbPath, tokens: tokens, topK: topK) {
            return hits
        }
        return searchViaIndex(workspace: workspace, tokens: tokens, topK: topK)
    }

    private static func searchViaSQLite(dbPath: URL, tokens: [String], topK: Int) -> [SearchHit]? {
        guard FileManager.default.fileExists(atPath: dbPath.path) else { return nil }
        guard let db = try? SQLiteIndex.DB(path: dbPath.path) else { return nil }

        var hitCounts: [String: Int] = [:]
        for token in tokens {
            let pattern = "%\(token)%"
            guard let rows = try? db.queryStrings(
                """
                SELECT DISTINCT principle_id FROM principle_signatures WHERE signature LIKE ?
                UNION
                SELECT DISTINCT principle_id FROM principle_math_basis WHERE basis LIKE ?
                """,
                [.text(pattern), .text(pattern)], columns: 1
            ) else { return nil }
            for row in rows {
                hitCounts[row[0], default: 0] += 1
            }
        }
        if hitCounts.isEmpty { return [] }

        let placeholders = Array(repeating: "?", count: hitCounts.count).joined(separator: ",")
        let ids = Array(hitCounts.keys)
        guard let titleRows = try? db.queryStrings(
            "SELECT id, title FROM principles WHERE id IN (\(placeholders))",
            ids.map { .text($0) }, columns: 2
        ) else { return nil }
        var idToTitle: [String: String] = [:]
        for row in titleRows { idToTitle[row[0]] = row[1] }

        let scored = hitCounts.map { (pid, count) in
            SearchHit(id: pid, title: idToTitle[pid] ?? "", score: count)
        }
        return Array(scored.sorted { $0.score == $1.score ? $0.id < $1.id : $0.score > $1.score }.prefix(topK))
    }

    private static func searchViaIndex(workspace: Workspace, tokens: [String], topK: Int) -> [SearchHit] {
        guard let idx = try? workspace.readIndex() else { return [] }
        var scored: [SearchHit] = []
        for principle in idx.principles {
            let haystack = (principle.problemSignature + principle.mathBasis).joined(separator: " ").lowercased()
            let score = tokens.reduce(0) { $0 + (haystack.contains($1) ? 1 : 0) }
            if score > 0 {
                scored.append(SearchHit(id: principle.id, title: principle.title, score: score))
            }
        }
        return Array(scored.sorted { $0.score == $1.score ? $0.id < $1.id : $0.score > $1.score }.prefix(topK))
    }
}
