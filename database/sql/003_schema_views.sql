-- Schema-Agnostic Views for Common Queries
-- Scope-Based Multi-Stage Workflow Analytics

-- ========================================
-- MULTI-STAGE WORKFLOW VIEWS
-- ========================================

-- Complete Multi-Stage Workflow Overview
CREATE VIEW workflow_complete_overview AS
SELECT 
    gsa.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    gsa.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    s.institution,
    
    -- Assignment details
    gsa.assigned_curator_id,
    curator.name as curator_name,
    gsa.workflow_pair_id,
    wp.name as workflow_pair_name,
    
    -- Precuration counts and status
    COUNT(DISTINCT p.id) as precuration_count,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'draft') as draft_precuration_count,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'submitted') as submitted_precuration_count,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'approved') as completed_precuration_count,
    
    -- Curation counts and status
    COUNT(DISTINCT c.id) as curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'draft') as draft_curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'submitted') as submitted_curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'in_review') as in_review_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'approved') as approved_curation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'rejected') as rejected_curation_count,
    
    -- Review status (4-eyes principle)
    COUNT(DISTINCT r.id) as review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'pending') as pending_review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'approved') as approved_review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'rejected') as rejected_review_count,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'needs_revision') as needs_revision_count,
    
    -- Active status
    ac.curation_id as active_curation_id,
    ac.activated_at as activated_at,
    active_curation.computed_verdict as active_verdict,
    active_curation.computed_summary as active_summary,
    
    -- Latest activity
    GREATEST(
        MAX(p.updated_at),
        MAX(c.updated_at),
        MAX(r.reviewed_at),
        ac.activated_at
    ) as last_activity_at
    
FROM gene_scope_assignments gsa
JOIN genes_new g ON gsa.gene_id = g.id
JOIN scopes s ON gsa.scope_id = s.id
LEFT JOIN users_new curator ON gsa.assigned_curator_id = curator.id
LEFT JOIN workflow_pairs wp ON gsa.workflow_pair_id = wp.id
LEFT JOIN precurations_new p ON p.gene_id = gsa.gene_id AND p.scope_id = gsa.scope_id
LEFT JOIN curations_new c ON c.gene_id = gsa.gene_id AND c.scope_id = gsa.scope_id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN active_curations ac ON ac.gene_id = gsa.gene_id AND ac.scope_id = gsa.scope_id AND ac.archived_at IS NULL
LEFT JOIN curations_new active_curation ON ac.curation_id = active_curation.id
WHERE gsa.is_active = true
GROUP BY 
    gsa.gene_id, g.approved_symbol, g.hgnc_id, gsa.scope_id, s.name, s.display_name, s.institution,
    gsa.assigned_curator_id, curator.name, gsa.workflow_pair_id, wp.name,
    ac.curation_id, ac.activated_at, active_curation.computed_verdict, active_curation.computed_summary;

-- Scope-Based Statistics and Performance Metrics
CREATE VIEW scope_statistics AS
SELECT 
    s.id as scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    s.institution,
    s.is_active,
    
    -- Gene assignments
    COUNT(DISTINCT gsa.gene_id) as total_genes_assigned,
    COUNT(DISTINCT gsa.gene_id) FILTER (WHERE gsa.assigned_curator_id IS NOT NULL) as genes_with_curator,
    
    -- Workflow stage distribution
    COUNT(DISTINCT p.id) as total_precurations,
    COUNT(DISTINCT c.id) as total_curations,
    COUNT(DISTINCT r.id) as total_reviews,
    COUNT(DISTINCT ac.id) as active_curations,
    
    -- Status breakdowns
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'draft') as draft_curations,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'submitted') as submitted_curations,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'in_review') as curations_in_review,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'approved') as approved_curations,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'rejected') as rejected_curations,
    
    -- Review metrics (4-eyes principle)
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'pending') as pending_reviews,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'approved') as approved_reviews,
    AVG(EXTRACT(days FROM (r.reviewed_at - r.assigned_at))) FILTER (WHERE r.reviewed_at IS NOT NULL) as avg_review_time_days,
    
    -- Team metrics
    COUNT(DISTINCT gsa.assigned_curator_id) as active_curators,
    COUNT(DISTINCT r.reviewer_id) as active_reviewers,
    
    -- Verdict distribution for active curations
    COUNT(DISTINCT ac.id) FILTER (WHERE active_c.computed_verdict = 'Definitive') as definitive_verdicts,
    COUNT(DISTINCT ac.id) FILTER (WHERE active_c.computed_verdict = 'Strong') as strong_verdicts,
    COUNT(DISTINCT ac.id) FILTER (WHERE active_c.computed_verdict = 'Moderate') as moderate_verdicts,
    COUNT(DISTINCT ac.id) FILTER (WHERE active_c.computed_verdict = 'Limited') as limited_verdicts,
    
    -- Productivity metrics
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_at >= NOW() - INTERVAL '30 days') as curations_last_30_days,
    COUNT(DISTINCT ac.id) FILTER (WHERE ac.activated_at >= NOW() - INTERVAL '30 days') as activations_last_30_days
    
FROM scopes s
LEFT JOIN gene_scope_assignments gsa ON s.id = gsa.scope_id AND gsa.is_active = true
LEFT JOIN precurations_new p ON p.scope_id = s.id
LEFT JOIN curations_new c ON c.scope_id = s.id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN active_curations ac ON ac.scope_id = s.id AND ac.archived_at IS NULL
LEFT JOIN curations_new active_c ON ac.curation_id = active_c.id
WHERE s.is_active = true
GROUP BY s.id, s.name, s.display_name, s.institution, s.is_active;

-- 4-Eyes Principle Compliance and Review Management
CREATE VIEW review_compliance_dashboard AS
SELECT 
    c.id as curation_id,
    c.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    c.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    
    -- Curation details
    c.status as curation_status,
    c.workflow_stage,
    c.created_by as curator_id,
    curator.name as curator_name,
    curator.email as curator_email,
    c.created_at as curation_created_at,
    c.submitted_at,
    
    -- Review assignment
    r.id as review_id,
    r.reviewer_id,
    reviewer.name as reviewer_name,
    reviewer.email as reviewer_email,
    r.status as review_status,
    r.assigned_at as review_assigned_at,
    r.reviewed_at,
    r.due_date as review_due_date,
    r.comments as review_comments,
    r.recommendation,
    
    -- 4-eyes compliance validation
    CASE 
        WHEN r.reviewer_id IS NULL THEN 'No Review Assigned'
        WHEN r.reviewer_id = c.created_by THEN 'VIOLATION: Same Person as Curator'
        WHEN r.status = 'approved' THEN 'Compliant: Approved by Different Reviewer'
        WHEN r.status = 'pending' AND r.due_date < NOW() THEN 'Overdue Review'
        WHEN r.status = 'pending' THEN 'Pending Review'
        WHEN r.status = 'rejected' THEN 'Review Rejected'
        WHEN r.status = 'needs_revision' THEN 'Needs Revision'
        ELSE 'Under Review'
    END as compliance_status,
    
    -- Time metrics
    EXTRACT(days FROM (NOW() - c.submitted_at)) as days_since_submission,
    EXTRACT(days FROM (r.reviewed_at - r.assigned_at)) as review_duration_days,
    EXTRACT(days FROM (NOW() - r.assigned_at)) as days_under_review,
    
    -- Urgency indicators
    CASE 
        WHEN r.due_date < NOW() THEN 'Overdue'
        WHEN r.due_date < NOW() + INTERVAL '3 days' THEN 'Due Soon'
        ELSE 'On Track'
    END as urgency_status
    
FROM curations_new c
JOIN genes_new g ON c.gene_id = g.id
JOIN scopes s ON c.scope_id = s.id
LEFT JOIN users_new curator ON c.created_by = curator.id
LEFT JOIN reviews r ON r.curation_id = c.id
LEFT JOIN users_new reviewer ON r.reviewer_id = reviewer.id
WHERE c.status IN ('submitted', 'in_review', 'approved', 'rejected')
ORDER BY 
    CASE 
        WHEN r.due_date < NOW() THEN 1
        WHEN r.due_date < NOW() + INTERVAL '3 days' THEN 2
        ELSE 3
    END,
    r.assigned_at DESC;

-- Schema Usage and Performance Analytics
CREATE VIEW schema_usage_analytics AS
SELECT 
    cs.id as schema_id,
    cs.name as schema_name,
    cs.version as schema_version,
    cs.schema_type,
    cs.institution,
    cs.is_active,
    
    -- Usage statistics
    COUNT(DISTINCT wp.id) as workflow_pairs_using_schema,
    COUNT(DISTINCT CASE WHEN cs.schema_type IN ('precuration', 'combined') THEN p.id END) as precurations_using_schema,
    COUNT(DISTINCT CASE WHEN cs.schema_type IN ('curation', 'combined') THEN c.id END) as curations_using_schema,
    
    -- Performance metrics
    AVG(EXTRACT(minutes FROM (c.submitted_at - c.created_at))) FILTER (WHERE c.submitted_at IS NOT NULL) as avg_curation_time_minutes,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'approved') as successful_curations,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'rejected') as rejected_curations,
    
    -- Scoring engine usage
    cs.scoring_configuration->>'engine' as scoring_engine,
    COUNT(DISTINCT c.computed_verdict) as unique_verdicts_produced,
    
    -- Recent activity
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_at >= NOW() - INTERVAL '30 days') as curations_last_30_days,
    MAX(c.created_at) as last_used_date
    
FROM curation_schemas cs
LEFT JOIN workflow_pairs wp ON (wp.precuration_schema_id = cs.id OR wp.curation_schema_id = cs.id)
LEFT JOIN precurations_new p ON p.precuration_schema_id = cs.id
LEFT JOIN curations_new c ON c.workflow_pair_id = wp.id
GROUP BY 
    cs.id, cs.name, cs.version, cs.schema_type, cs.institution, cs.is_active,
    cs.scoring_configuration->>'engine'
ORDER BY curations_using_schema DESC, last_used_date DESC;

-- User Activity and Workload Dashboard
CREATE VIEW user_workload_dashboard AS
SELECT 
    u.id as user_id,
    u.name,
    u.email,
    u.role,
    u.institution,
    array_length(u.assigned_scopes, 1) as assigned_scope_count,
    
    -- Scope assignments
    (SELECT string_agg(s.display_name, ', ' ORDER BY s.display_name) 
     FROM scopes s WHERE s.id = ANY(u.assigned_scopes)) as assigned_scope_names,
    
    -- Current workload as curator
    COUNT(DISTINCT gsa.gene_id) as genes_assigned_as_curator,
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.status = 'draft') as draft_curations,
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.status = 'submitted') as submitted_curations,
    
    -- Current workload as reviewer
    COUNT(DISTINCT r.id) FILTER (WHERE r.reviewer_id = u.id AND r.status = 'pending') as pending_reviews,
    COUNT(DISTINCT r.id) FILTER (WHERE r.reviewer_id = u.id AND r.due_date < NOW()) as overdue_reviews,
    
    -- Productivity metrics (last 30 days)
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.created_at >= NOW() - INTERVAL '30 days') as curations_created_30d,
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.submitted_at >= NOW() - INTERVAL '30 days') as curations_submitted_30d,
    COUNT(DISTINCT r.id) FILTER (WHERE r.reviewer_id = u.id AND r.reviewed_at >= NOW() - INTERVAL '30 days') as reviews_completed_30d,
    
    -- Quality metrics
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.status = 'approved') as approved_curations_total,
    COUNT(DISTINCT c.id) FILTER (WHERE c.created_by = u.id AND c.status = 'rejected') as rejected_curations_total,
    COUNT(DISTINCT r.id) FILTER (WHERE r.reviewer_id = u.id AND r.status = 'approved') as reviews_approved_total,
    
    -- Time metrics
    AVG(EXTRACT(days FROM (c.submitted_at - c.created_at))) FILTER (WHERE c.created_by = u.id AND c.submitted_at IS NOT NULL) as avg_curation_time_days,
    AVG(EXTRACT(days FROM (r.reviewed_at - r.assigned_at))) FILTER (WHERE r.reviewer_id = u.id AND r.reviewed_at IS NOT NULL) as avg_review_time_days,
    
    -- Recent activity
    u.last_login,
    GREATEST(MAX(c.updated_at), MAX(r.reviewed_at)) as last_activity_date
    
FROM users_new u
LEFT JOIN gene_scope_assignments gsa ON gsa.assigned_curator_id = u.id AND gsa.is_active = true
LEFT JOIN curations_new c ON c.created_by = u.id
LEFT JOIN reviews r ON r.reviewer_id = u.id
WHERE u.is_active = true
GROUP BY u.id, u.name, u.email, u.role, u.institution, u.assigned_scopes, u.last_login
ORDER BY last_activity_date DESC NULLS LAST;

-- Active Curations Summary with Verdict Distribution
CREATE VIEW active_curations_summary AS
SELECT 
    ac.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    ac.scope_id,
    s.name as scope_name,
    s.display_name as scope_display_name,
    
    -- Active curation details
    ac.curation_id,
    c.computed_verdict,
    c.computed_summary,
    c.evidence_data,
    c.computed_scores,
    
    -- Workflow information
    wp.name as workflow_pair_name,
    cs.name as schema_name,
    cs.scoring_configuration->>'engine' as scoring_engine,
    
    -- Attribution
    creator.name as curator_name,
    approver.name as approver_name,
    ac.activated_at,
    activator.name as activator_name,
    
    -- Scores (extracted from computed_scores JSONB)
    (c.computed_scores->>'total_score')::numeric as total_score,
    (c.computed_scores->>'genetic_evidence_score')::numeric as genetic_score,
    (c.computed_scores->>'experimental_evidence_score')::numeric as experimental_score,
    
    -- Evidence counts
    jsonb_array_length(c.evidence_data->'genetic_evidence'->'case_level_data') as case_level_count,
    jsonb_array_length(c.evidence_data->'experimental_evidence'->'function') as functional_evidence_count,
    
    -- Time metrics
    EXTRACT(days FROM (ac.activated_at - c.created_at)) as total_curation_time_days,
    ac.activated_at as last_updated
    
FROM active_curations ac
JOIN genes_new g ON ac.gene_id = g.id
JOIN scopes s ON ac.scope_id = s.id
JOIN curations_new c ON ac.curation_id = c.id
JOIN workflow_pairs wp ON c.workflow_pair_id = wp.id
JOIN curation_schemas cs ON wp.curation_schema_id = cs.id
LEFT JOIN users_new creator ON c.created_by = creator.id
LEFT JOIN users_new approver ON c.approved_by = approver.id
LEFT JOIN users_new activator ON ac.activated_by = activator.id
WHERE ac.archived_at IS NULL
ORDER BY ac.activated_at DESC;

-- ========================================
-- MAINTENANCE AND MONITORING VIEWS  
-- ========================================

-- System Health and Performance Monitoring
CREATE VIEW system_health_metrics AS
SELECT 
    'Schema Repository' as component,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    MAX(created_at) as last_activity
FROM curation_schemas

UNION ALL

SELECT 
    'Workflow Pairs' as component,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    MAX(created_at) as last_activity
FROM workflow_pairs

UNION ALL

SELECT 
    'Active Scopes' as component,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    MAX(created_at) as last_activity
FROM scopes

UNION ALL

SELECT 
    'Gene Assignments' as component,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    MAX(assigned_at) as last_activity
FROM gene_scope_assignments

UNION ALL

SELECT 
    'Active Users' as component,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    MAX(last_login) as last_activity
FROM users_new;

-- Data Quality and Integrity Checks
CREATE VIEW data_integrity_checks AS
SELECT 
    'Curations without Reviews' as check_name,
    COUNT(*) as issue_count,
    'Curations in review status without assigned reviewer' as description
FROM curations_new c
WHERE c.status = 'in_review' 
AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.curation_id = c.id AND r.status = 'pending')

UNION ALL

SELECT 
    'Review Assignment Violations' as check_name,
    COUNT(*) as issue_count,
    'Reviews assigned to same person who created the curation (4-eyes violation)' as description
FROM reviews r
JOIN curations_new c ON r.curation_id = c.id
WHERE r.reviewer_id = c.created_by

UNION ALL

SELECT 
    'Overdue Reviews' as check_name,
    COUNT(*) as issue_count,
    'Reviews past their due date' as description
FROM reviews r
WHERE r.status = 'pending' AND r.due_date < NOW()

UNION ALL

SELECT 
    'Orphaned Active Curations' as check_name,
    COUNT(*) as issue_count,
    'Active curations pointing to non-approved curations' as description
FROM active_curations ac
JOIN curations_new c ON ac.curation_id = c.id
WHERE c.status != 'approved'

UNION ALL

SELECT 
    'Scope Access Violations' as check_name,
    COUNT(*) as issue_count,
    'Users working in scopes they are not assigned to' as description
FROM curations_new c
JOIN users_new u ON c.created_by = u.id
WHERE NOT (c.scope_id = ANY(u.assigned_scopes));

-- Comments for documentation
COMMENT ON VIEW workflow_complete_overview IS 'Complete multi-stage workflow status for all gene-scope assignments';
COMMENT ON VIEW scope_statistics IS 'Performance metrics and activity statistics for each clinical scope';
COMMENT ON VIEW review_compliance_dashboard IS '4-eyes principle compliance monitoring and review management';
COMMENT ON VIEW schema_usage_analytics IS 'Schema adoption and performance metrics across the platform';
COMMENT ON VIEW user_workload_dashboard IS 'Individual user workload and productivity metrics';
COMMENT ON VIEW active_curations_summary IS 'Summary of all active curations with verdict and score details';
COMMENT ON VIEW system_health_metrics IS 'Overall system health and component activity monitoring';
COMMENT ON VIEW data_integrity_checks IS 'Data quality validation and integrity issue detection';