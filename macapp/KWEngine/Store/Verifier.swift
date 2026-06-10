//  Verifier.swift
//  KWEngine — SCHEMA §6 invariant checks, port of kw_engine/verify.py.
//  Review lane only: reports PASS/FAIL with evidence, never fixes records.

import Foundation

struct Verdict: Identifiable {
    let id = UUID()
    var checkName: String
    var passed: Bool
    var message: String
}

enum Verifier {

    static func run(workspace: Workspace) -> [Verdict] {
        var verdicts: [Verdict] = []

        let papers: [PaperFull]
        let principles: [Principle]
        do {
            (papers, principles) = try workspace.scanMarkdown()
        } catch {
            return [Verdict(checkName: "parse", passed: false, message: error.localizedDescription)]
        }

        let paperIds = Set(papers.map { $0.id })
        let principleIds = Set(principles.map { $0.id })

        // Counter invariant: counters.principle == number of principle records.
        if let idx = try? workspace.readIndex() {
            if idx.counters.principle == principles.count {
                verdicts.append(Verdict(checkName: "counter_invariant", passed: true,
                                        message: "counters.principle == \(principles.count)"))
            } else {
                verdicts.append(Verdict(checkName: "counter_invariant", passed: false,
                                        message: "counters.principle = \(idx.counters.principle), but \(principles.count) principle records exist"))
            }
        } else {
            verdicts.append(Verdict(checkName: "counter_invariant", passed: false,
                                    message: "index.json missing or unreadable"))
        }

        // Provenance resolves.
        var provOK = true
        for pr in principles {
            for prov in pr.provenance {
                let refId = paperIdFromProvenance(prov)
                if !paperIds.contains(refId) {
                    provOK = false
                    verdicts.append(Verdict(checkName: "provenance_resolves", passed: false,
                                            message: "\(pr.id) cites '\(refId)' which is not in papers"))
                }
            }
        }
        if provOK {
            verdicts.append(Verdict(checkName: "provenance_resolves", passed: true,
                                    message: "all provenance resolves"))
        }

        // Link integrity.
        var linkOK = true
        for pr in principles {
            for linkStr in pr.links {
                guard let le = LinkEntry(fromString: linkStr) else {
                    linkOK = false
                    verdicts.append(Verdict(checkName: "link_integrity", passed: false,
                                            message: "\(pr.id) has malformed link '\(linkStr)'"))
                    continue
                }
                if !principleIds.contains(le.target) {
                    linkOK = false
                    verdicts.append(Verdict(checkName: "link_integrity", passed: false,
                                            message: "\(pr.id) links to \(le.target) which does not exist"))
                }
            }
        }
        if linkOK {
            verdicts.append(Verdict(checkName: "link_integrity", passed: true,
                                    message: "all link targets exist"))
        }

        // L2 load-bearing fields non-empty.
        var l2OK = true
        for pr in principles {
            let fields: [(String, Bool)] = [
                ("problem_signature", pr.problemSignature.isEmpty),
                ("mechanism", pr.mechanism.isEmpty),
                ("rationale", pr.rationale.isEmpty),
                ("falsifiable_prediction", pr.falsifiablePrediction.isEmpty),
            ]
            for (name, isEmpty) in fields where isEmpty {
                l2OK = false
                verdicts.append(Verdict(checkName: "l2_fields_nonempty", passed: false,
                                        message: "\(pr.id).\(name) is empty"))
            }
        }
        if l2OK {
            verdicts.append(Verdict(checkName: "l2_fields_nonempty", passed: true,
                                    message: "all L2 load-bearing fields filled"))
        }

        return verdicts
    }
}
