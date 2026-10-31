# Curator guide

One page for curators and reviewers. Your rights come from your role in each scope
(curator, reviewer, admin, viewer), not from your account. An invitation grants nothing until
you accept it.

## Your work

**My work** splits your items into *Needs you* (assignments and reviews waiting for you, with
due dates), *Waiting* and *Done*. **Review Queue** lists every item you may review. The
**Gene Catalogue** shows the active calls of all scopes side by side; reorder its scope columns by drag or the arrow buttons, or
pick the *With results* preset. Your column choice is saved to your account.

## Curate a gene

1. **Precuration.** Open the gene in your scope and start a precuration. Pick the workflow
   (only the ones your scope allows are listed), then define the disease entity (MONDO, mode of
   inheritance, lumping or splitting). One open precuration per gene, scope and disease entity.
2. **Curation.** Enter evidence in the form. Fields show errors only after you edit or submit;
   the score panel updates as you type. Evidence tables cite their sources (PMID, DOI, ClinVar,
   ClinGen, URL, database) and say whether a row supports, disputes or is neutral.
   A case-level variant is HGVS, an rsID or a coordinate; a CNV or a repeat-region insertion
   the paper describes only in words counts when the text names its extent ("deletion of exons
   2-29", "whole-gene deletion", "C insertion in the VNTR"). Vague text ("large deletion")
   scores 0. A save warns when a row scores 0 because a field its rule needs (such as
   `evidence_quote`) is blank.
3. **Submit for review** and pick a reviewer. A save that clashes with someone else's newer
   save is refused; reload, then re-apply your change.

To revise an active curation, create a new curation of the entity: it starts empty (re-enter or
copy the rows you keep) and is pinned to the latest version of its methodology, which can be
newer than the active one's. The active curation stays published until the new one is approved.

The curation's History panel shows who added or changed each evidence row, including an AI
agent working through MCP on someone's behalf.

## Review (4-eyes)

Nobody approves their own work, admins included; a disease corrector or the admin who moved a
curation to a new methodology version cannot review it either. As a reviewer, check the
evidence, the score trace and any reviewer flags (they warn, they never block), then approve or
send back with a comment. Approval makes the curation the scope's active call for that gene and
entity; the previous active one is archived.

## Adopt a ClinGen classification

For genes ClinGen already curated, adopt instead of re-scoring: send the entity and the
GeneFoundry `clingen_get_gene_validity` record to `POST /api/v1/curations/clingen-adoptions`
(MCP `adopt_clingen_classifications`, dry run first). The curation enters review with the
ClinGen class and a comment that point values must be re-scored manually; another reviewer
confirms it. It shows an *Adopted from ClinGen* badge. Gene Curator never fetches ClinGen,
PubMed or ClinVar records itself: use GeneFoundry and record what it returns. Details in the
[README](../README.md#adopting-a-clingen-classification).

## Working with an AI agent

Connect Claude or another MCP client with a personal access token or OAuth
([docs/MCP_CONNECTION_GUIDE.md](MCP_CONNECTION_GUIDE.md)). The agent acts as you, with your
scope roles and the 4-eyes rule; its evidence writes record the agent beside your name.
