# Gene Curator Development Setup Guide

This guide provides detailed instructions for setting up the Gene Curator development environment.

## System Requirements

### Required Software
- **Docker Desktop**: Version 4.0+ with Docker Compose v2
- **Git**: For version control
- **Make**: For convenience commands (optional but recommended)

### Recommended Software
- **VS Code**: With Docker and Python extensions
- **DBeaver**: For database management and queries
- **Postman**: For API testing

### System Resources
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space for Docker images and data
- **CPU**: Multi-core processor recommended for development

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/halbritter-lab/gene-curator.git
cd gene-curator
```

### 2. Environment Configuration

Create environment file from template:
```bash
cp .env.example .env
```

**Important**: Update the `.env` file with secure passwords for production use. The default values are suitable for development only.

### 3. Start Development Environment

#### Option A: Using Make (Recommended)
```bash
make dev
```

#### Option B: Using Docker Compose Directly
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 4. Verify Installation

Check that all services are running:
```bash
make status
# or
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

Test service health:
```bash
make health
# or manually
curl http://localhost:8000/health
```

## Service URLs

Once running, access the services at:

- **API Documentation**: http://localhost:8000/docs
- **API Root**: http://localhost:8000/
- **Database**: localhost:5454 (PostgreSQL)
- **Redis Cache**: localhost:6379 (optional)

## Development Workflow

### Database Operations

```bash
# Initialize database with schema and sample data
make db-init

# Reset database completely
make db-reset

# Access PostgreSQL shell
make db-shell

# View database logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs postgres
```

### Backend Development

```bash
# View backend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend

# Access backend shell
make backend-shell

# Run tests
make test-backend

# Run linting
make lint

# Format code
make format
```

### Code Quality

The project includes comprehensive code quality tools:

```bash
# Run all linting
make lint

# Format all code
make format

# Run all tests
make test
```

## Database Schema

### ClinGen Compliance Features

The database includes several ClinGen-specific features:

1. **Automatic Scoring Triggers**: Calculate evidence scores per SOP v11
2. **Verdict Classification**: Determine curation verdicts automatically
3. **Provenance Tracking**: SHA-256 hashes for record verification
4. **Change Auditing**: Complete audit log of all modifications

### Sample Data

The development database includes:

#### Users
- **Admin**: `admin@gene-curator.org` / `admin123`
- **Curator**: `curator@gene-curator.org` / `curator123`
- **Viewer**: `viewer@gene-curator.org` / `viewer123`

#### Genes
- **PKD1**: Polycystic kidney disease 1 gene
- **PKD2**: Polycystic kidney disease 2 gene
- **NPHP1**: Nephronophthisis 1 gene

#### Sample Curation
- **PKD1 Curation**: Complete curation with ClinGen evidence demonstrating automatic scoring

### Testing the ClinGen Scoring Engine

Test the automatic scoring system:

```sql
-- Connect to database
make db-shell

-- Test scoring function
SELECT 
    g.approved_symbol,
    c.genetic_evidence_score,
    c.experimental_evidence_score,
    c.total_score,
    c.verdict
FROM curations c
JOIN genes g ON c.gene_id = g.id
WHERE c.mondo_id = 'MONDO:0009691';
```

Expected output should show PKD1 with calculated scores and verdict.

## API Development

### Testing API Endpoints

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test detailed health (includes database and ClinGen engine)
curl http://localhost:8000/api/v1/health/detailed

# View API documentation
open http://localhost:8000/docs
```

### Adding New Endpoints

1. Create endpoint file in `backend/app/api/v1/endpoints/`
2. Add router to `backend/app/api/v1/api.py`
3. Create corresponding Pydantic schemas in `backend/app/schemas/`
4. Add database operations in `backend/app/crud/`

## Troubleshooting

### Common Issues

#### Port Conflicts
If ports 5454, 8000, or 3000 are in use:
1. Stop conflicting services
2. Modify ports in `docker-compose.dev.yml`
3. Update documentation URLs accordingly

#### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs postgres

# Restart database service
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart postgres

# Reset database completely
make db-reset
```

#### Backend Issues
```bash
# Check backend logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs backend

# Rebuild backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build backend

# Access backend shell for debugging
make backend-shell
```

### Cleanup

Remove all containers and data:
```bash
make clean
# or
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v --remove-orphans
docker system prune -f
```

## Development Tools Integration

### VS Code Setup

Recommended extensions:
- Docker
- Python
- SQLAlchemy
- PostgreSQL

Workspace settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./backend/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "sqltools.connections": [
        {
            "name": "Gene Curator Dev",
            "driver": "PostgreSQL",
            "server": "localhost",
            "port": 5454,
            "database": "gene_curator_dev",
            "username": "dev_user",
            "password": "dev_password"
        }
    ]
}
```

### Database GUI Access

**DBeaver Configuration**:
- Host: `localhost`
- Port: `5454`
- Database: `gene_curator_dev`
- Username: `dev_user`
- Password: `dev_password`

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Review Sample Data**: Connect to database and examine the sample curation
3. **Test ClinGen Features**: Verify automatic scoring is working
4. **Start Development**: Choose your work stream (API, Frontend, or Database enhancements)

For detailed development guidance, see the work stream documentation in the `plan/` directory.