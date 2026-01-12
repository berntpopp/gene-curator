# Critical Bugs and Fixes

## Bug #1: "No Role" - Membership Not Created

### Root Cause
Backend logs show `Retrieved user scopes | count=0` when querying user's scope memberships.
The scope creation endpoint calls `scope_membership_crud.create_invitation()` but the membership
is not persisting or not meeting the query criteria (`is_active=true AND accepted_at IS NOT NULL`).

### Investigation Needed
1. Check if `scope_membership_crud.create_invitation()` is actually being called
2. Verify database transaction is committing
3. Check if there's an exception being swallowed
4. Verify the user_id being used matches between scope creation and membership query

### Fix Location
- **Backend**: `backend/app/api/v1/endpoints/scopes.py` lines 88-103
- **Backend**: `backend/app/crud/scope_membership.py` line 100-128

### Temporary Workaround
Manually create the membership via API:
```bash
curl -X POST http://localhost:8051/api/v1/scopes/bc5c951e-a90a-4ed3-8fde-88f104c7d88f/invitations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID_HERE",
    "role": "admin"
  }'
```

## Bug #2: Missing Gene Addition Flow

### Root Cause
The "Assign Genes" button in `GeneList.vue` and `AssignGenesDrawer.vue` assumes genes already
exist in the catalog. There's NO UI to:
1. Add individual genes to the gene catalog
2. Bulk import genes from files/lists
3. Link genes to scopes BEFORE assigning to curators

### Current Flow (BROKEN)
```
User creates scope → Assign Genes button → ERROR: No genes to assign
```

### Required Flow
```
1. Add genes to catalog (POST /genes or POST /genes/bulk)
2. Link genes to scope (via gene assignments or scope_genes table)
3. Assign genes to curators (POST /gene-assignments)
```

### API Endpoints Available
- `POST /genes` - Create single gene
- `POST /genes/bulk` - Bulk create genes
- `POST /gene-assignments` - Assign gene to curator in scope
- `POST /gene-assignments/bulk` - Bulk assign

### Required Components
1. **AddGenesDrawer.vue** - Add genes to catalog
   - Single gene form (HGNC ID, Symbol, Name, Chromosome, Location)
   - Bulk import (CSV/TSV with HGNC IDs)
   - Gene search/validation via HGNC API

2. **Update AssignGenesDrawer.vue** - Fetch genes for scope
   - Change from global gene list to scope-specific genes
   - Add "No genes? Add genes first" message with link

3. **GeneList.vue Enhancement**
   - Add "Add Genes to Scope" button (separate from "Assign Genes")
   - Shows genes linked to scope (not just assigned ones)

### Implementation Priority
1. **HIGH**: Create AddGenesDrawer.vue for adding genes
2. **HIGH**: Update GeneList.vue to show "Add Genes" button
3. **MEDIUM**: Add bulk gene import functionality
4. **LOW**: HGNC API integration for validation

## Testing Plan

### Test Bug #1 Fix
1. Create new scope as logged-in user
2. Verify membership created in database
3. Navigate to scope dashboard
4. Verify role badge shows "admin" (not "No role")
5. Verify "Members" tab shows creator as admin

### Test Bug #2 Fix
1. Create new scope
2. Click "Add Genes to Scope" button
3. Add single gene (BRCA1: HGNC:1100)
4. Verify gene appears in gene list
5. Click "Assign Genes" button
6. Verify BRCA1 appears in dropdown
7. Assign to curator
8. Verify assignment created successfully

## API Testing Commands

### Check User's Scopes
```bash
curl http://localhost:8051/api/v1/scopes/ \
  -H "Authorization: Bearer $TOKEN"
```

### Check Scope Members
```bash
curl http://localhost:8051/api/v1/scopes/SCOPE_ID/members \
  -H "Authorization: Bearer $TOKEN"
```

### Add Gene to Catalog
```bash
curl -X POST http://localhost:8051/api/v1/genes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hgnc_id": "HGNC:1100",
    "approved_symbol": "BRCA1",
    "approved_name": "BRCA1 DNA repair associated",
    "chromosome": "17",
    "location": "17q21.31"
  }'
```

### Bulk Add Genes
```bash
curl -X POST http://localhost:8051/api/v1/genes/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "genes": [
      {"hgnc_id": "HGNC:1100", "approved_symbol": "BRCA1", ...},
      {"hgnc_id": "HGNC:1101", "approved_symbol": "BRCA2", ...}
    ],
    "skip_duplicates": true
  }'
```

## Next Steps
1. Fix membership creation bug in scope creation endpoint
2. Create AddGenesDrawer.vue component
3. Add "Add Genes" button to GeneList.vue
4. Test complete workflow: Create scope → Add genes → Assign genes → Start curation
