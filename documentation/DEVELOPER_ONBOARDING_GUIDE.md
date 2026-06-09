# CloudVisor Developer Onboarding Guide

## Welcome to the CloudVisor Team! 👋

This guide will get you productive in 2-3 hours. Follow each section sequentially.

---

## Phase 1: Environment Setup (30 minutes)

### Step 1.1: Prerequisites

Verify you have installed:

```bash
# Check versions
docker --version          # 20.10+
docker-compose --version  # 2.0+
git --version            # 2.30+
node --version           # 18.x+
python --version         # 3.12+

# Install missing tools
# macOS
brew install docker docker-compose node python

# Ubuntu
sudo apt-get install docker.io docker-compose nodejs python3.12

# Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

### Step 1.2: Clone & Configure

```bash
# Clone repository
git clone https://github.com/cloudvisor/cloudvisor.git
cd cloudvisor

# Configure environment
cp .env.example .env

# Edit .env with secure values
nano .env  # or your editor

# Key values to change:
# POSTGRES_PASSWORD=your-password
# NEO4J_PASSWORD=your-password
# ELASTIC_PASSWORD=your-password
```

### Step 1.3: Start Local Environment

```bash
# Build all services (first time only, ~10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Wait 30-60 seconds for services to be healthy
# Monitor logs
docker-compose logs -f

# Expected: All services show "Up (healthy)"
docker-compose ps
```

### Step 1.4: Verify Installation

```bash
# Test health endpoints
curl http://localhost:8080/auth/health

# Expected response:
# {"status": "healthy", "service": "auth"}

# Open in browser
open http://localhost:8080

# Login with default credentials
# Email: admin@cloudvisor.io
# Password: AdminPass123!
```

---

## Phase 2: Understand the Codebase (1 hour)

### Step 2.1: Project Layout

Read this first: [TECHNICAL_DOCUMENTATION.md](./TECHNICAL_DOCUMENTATION.md)

**Focus on:**
- Section: "Project Structure"
- Section: "Architecture & Design"
- Section: "Core Workflows"

### Step 2.2: Key Services Overview

| Service | Port | Purpose | Start Here |
|---------|------|---------|------------|
| **Auth** | 8002 | User authentication & RBAC | `services/auth/README.md` |
| **API** | 8005 | Public REST API gateway | `services/api/README.md` |
| **Connector** | 8000 | Cloud asset discovery | `services/connector/README.md` |
| **Graph** | 8001 | Asset relationship graph | `services/graph/README.md` |
| **Policy** | 8003 | Rego rule evaluation | `services/policy/README.md` |
| **Alert** | 8004 | Finding ingestion & notifications | `services/alert/README.md` |
| **Copilot** | 8010 | AI assistant | `services/copilot/README.md` |
| **Web** | 3000 | Frontend dashboard | `apps/web/README.md` |

### Step 2.3: Essential Concepts

**Concepts you MUST understand:**

1. **Multi-Tenancy**
   - Every user belongs to an organization
   - PostgreSQL RLS enforces org isolation
   - All queries automatically filtered by org_id

2. **Event-Driven Architecture**
   - Services communicate via Kafka topics
   - Loose coupling, high scalability
   - Events: assets.discovered, finding.raw, finding.created, etc.

3. **Repository Pattern**
   - Data access abstraction layer
   - `services/*/app/repositories/` contains query logic
   - Enables easy mocking for tests

4. **Common Data Model (CDM)**
   - All cloud resources normalized to unified format
   - Enables cross-cloud queries
   - Located in: `services/connector/app/core/cdm.py`

**Read:**
- Architecture Diagrams: [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md)
- Security Review: [SECURITY_REVIEW.md](./SECURITY_REVIEW.md)

---

## Phase 3: Set Up Your IDE (30 minutes)

### Step 3.1: Backend IDE (Python)

**VSCode Extensions:**

```
Python (Microsoft)
Pylance
Black Formatter
Ruff
Pytest
```

**Settings (.vscode/settings.json):**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  }
}
```

**Virtual Environment (Optional but Recommended):**

```bash
cd services/api
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3.2: Frontend IDE (TypeScript/React)

**VSCode Extensions:**

```
ES7+ React/Redux/React-Native snippets (dsznajder)
Prettier - Code formatter
ESLint
Tailwind CSS IntelliSense
Thunder Client (API testing)
```

**Settings (.vscode/settings.json):**

```json
{
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "tailwindCSS.experimental.classRegex": [
    ["clsx\\(([^)]*)\\)", "(?:'|\"|`)([^']*)(?:'|\"|`)"]
  ]
}
```

### Step 3.3: Database Tools (Optional)

**pgAdmin** (PostgreSQL UI):
- Already running at `http://localhost:8082`
- Username: admin@example.com
- Password: admin

**Neo4j Browser** (Graph UI):
- Running at `http://localhost:7474`
- Username: neo4j
- Password: (from .env NEO4J_PASSWORD)

**Elasticsearch** (Query tool):
```bash
curl -X GET "http://localhost:9200/findings/_search?pretty"
```

---

## Phase 4: Make Your First Change (45 minutes)

### Scenario: Add a new field to Findings

#### Step 4.1: Backend Database Schema

```python
# services/alert/app/models/alert.py

class FindingModel(Base):
    # ... existing fields ...
    
    # Add new field: custom_tags (for user annotations)
    custom_tags: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

#### Step 4.2: Create Database Migration

```bash
cd services/alert

# Create migration
alembic revision --autogenerate -m "Add custom_tags to findings"

# Review migration file (alembic/versions/xxxx_add_custom_tags.py)
# Should show:
#   op.add_column('findings', sa.Column('custom_tags', sa.JSON(), nullable=False))

# Apply migration
alembic upgrade head
```

#### Step 4.3: Update API Schema

```python
# services/alert/app/schemas/response.py

class FindingResponse(BaseModel):
    id: str
    title: str
    # ... other fields ...
    custom_tags: dict
    
    class Config:
        from_attributes = True  # SQLAlchemy to Pydantic
```

#### Step 4.4: Update Repository Method

```python
# services/alert/app/repositories/finding_repository.py

class FindingRepository(BaseRepository[FindingModel]):
    async def update_finding(self, org_id: str, finding_id: str, update_data: dict) -> Finding:
        stmt = select(FindingModel).where(
            (FindingModel.organization_id == org_id) &
            (FindingModel.id == finding_id)
        )
        result = await self.session.execute(stmt)
        finding = result.scalar_one()
        
        # Update allowed fields
        for key, value in update_data.items():
            if key in ['custom_tags', 'status', 'assignee_id']:
                setattr(finding, key, value)
        
        await self.session.commit()
        return finding
```

#### Step 4.5: Update API Endpoint

```python
# services/alert/app/api/findings.py

@router.patch("/findings/{finding_id}")
async def update_finding(
    finding_id: str,
    update: FindingUpdateRequest,  # Include custom_tags field
    repo: FindingRepository = Depends(get_finding_repo),
):
    """Update finding (status, tags, assignee, etc.)"""
    updated = await repo.update_finding(
        org_id=request.state.org_id,
        finding_id=finding_id,
        update_data=update.dict(exclude_unset=True)
    )
    return {"data": updated}
```

#### Step 4.6: Test Your Change

```bash
# 1. Restart affected services (hot reload might not work)
docker-compose restart cv-alert

# 2. Test via API
curl -X PATCH http://localhost:8080/v1/findings/finding_123 \
  -H "Authorization: Bearer $(your-jwt-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "custom_tags": {"reviewed": true, "team": "security"}
  }'

# 3. Verify in database
docker-compose exec postgres psql -U cvadmin -d cloudvisor -c \
  "SELECT custom_tags FROM findings WHERE id='finding_123';"

# 4. Write unit test
# services/alert/tests/unit/test_finding_repository.py
@pytest.mark.asyncio
async def test_update_finding_custom_tags(db_session):
    repo = FindingRepository(db_session, FindingModel)
    finding = await repo.create(Finding(...))
    
    updated = await repo.update_finding(
        org_id=finding.organization_id,
        finding_id=finding.id,
        update_data={"custom_tags": {"key": "value"}}
    )
    
    assert updated.custom_tags == {"key": "value"}
```

---

## Phase 5: Running Services Locally (30 minutes)

### Option A: Run All Services (Docker Compose) - Recommended for Beginners

```bash
docker-compose up -d

# Monitor all services
docker-compose logs -f

# Restart a single service (hot reload)
docker-compose restart cv-api

# View service logs only
docker-compose logs -f cv-auth
```

### Option B: Run Individual Services - Advanced Development

**Terminal 1: Auth Service**

```bash
cd services/auth
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# Service at http://localhost:8002
# Auto-reloads on code change
# API docs at http://localhost:8002/docs
```

**Terminal 2: API Service**

```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8005

# Depends on auth service being up
# Restart auth service for changes there
```

**Terminal 3: Frontend**

```bash
cd apps/web
npm run dev

# Frontend at http://localhost:3000
# Hot reload enabled
# API proxied through localhost:8080 (nginx)
```

### Debugging Tips

```bash
# View service logs
docker-compose logs cv-auth --tail 100 -f

# Enter service container
docker-compose exec cv-auth bash
python -m pdb -c continue main.py  # Start debugger

# Check if port is in use
lsof -i :8005  # macOS
netstat -tlnp | grep 8005  # Linux

# Reset everything (careful!)
docker-compose down -v  # Remove volumes
docker-compose up -d   # Start fresh
```

---

## Phase 6: Testing (30 minutes)

### Backend Tests

```bash
# Run all tests for a service
docker-compose exec cv-auth pytest tests/ -v

# Run specific test file
docker-compose exec cv-auth pytest tests/unit/test_auth.py -v

# Run with coverage
docker-compose exec cv-auth pytest --cov=app tests/

# Generate coverage report
docker-compose exec cv-auth coverage html
open htmlcov/index.html
```

### Frontend Tests

```bash
cd apps/web

# Run all tests
npm test

# Watch mode (re-run on changes)
npm test -- --watch

# Coverage report
npm test -- --coverage
open coverage/index.html
```

### Writing Tests

**Backend (pytest):**

```python
# services/auth/tests/unit/test_auth_service.py

@pytest.mark.asyncio
async def test_password_verification(auth_service):
    """Test password hashing and verification."""
    password = "TestPassword123!"
    
    # Hash
    hashed = auth_service.hash_password(password)
    assert hashed != password
    
    # Verify correct password
    assert auth_service.verify_password(password, hashed) is True
    
    # Verify wrong password
    assert auth_service.verify_password("WrongPassword", hashed) is False
```

**Frontend (Vitest + React Testing Library):**

```typescript
// apps/web/__tests__/components/Badge.test.tsx

import { render, screen } from '@testing-library/react';
import { SeverityBadge } from '@/components/ui/Badge';

describe('SeverityBadge', () => {
  it('renders CRITICAL with red color', () => {
    render(<SeverityBadge severity="CRITICAL" />);
    
    const badge = screen.getByRole('generic', { hidden: false });
    expect(badge).toHaveClass('bg-red-50');
    expect(badge).toHaveTextContent('CRITICAL');
  });
});
```

---

## Phase 7: Common Tasks (Quick Reference)

### Adding a New API Endpoint

```python
# services/api/app/api/v1/findings.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/findings", tags=["findings"])

class FindingFilter(BaseModel):
    severity: str
    limit: int = 50

@router.get("")
async def list_findings(
    filter: FindingFilter = Depends(),
    repo: FindingRepository = Depends(get_finding_repo),
):
    """List findings with filters."""
    findings = await repo.find_by_severity(
        org_id=request.state.org_id,
        severity=filter.severity,
        limit=filter.limit
    )
    
    return {
        "data": findings,
        "meta": {"total": len(findings), "took_ms": 123}
    }

# Include router in main app
# services/api/app/main.py
app.include_router(router)
```

### Adding a Kafka Consumer

```python
# services/alert/app/consumers/finding_consumer.py

from faust import App

app = App('finding-consumer')

@app.agent(topics=['finding.raw'])
async def consume_findings(stream):
    """Process raw findings from Policy service."""
    async for finding in stream:
        print(f"Processing finding: {finding['rule_id']}")
        
        # 1. Deduplicate
        fingerprint = compute_fingerprint(finding)
        existing = await repo.find_by_fingerprint(fingerprint)
        
        # 2. Create or update
        if existing:
            await repo.update(existing.id, finding)
            event = 'finding.seen_again'
        else:
            finding = await repo.create(finding)
            event = 'finding.created'
        
        # 3. Publish event
        await producer.send(event, finding.dict())
```

### Adding a Database Model

```python
# services/alert/app/models/alert.py

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class MyNewModel(Base):
    __tablename__ = "my_new_table"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

### Debugging API Issues

```bash
# 1. Check service health
curl http://localhost:8080/auth/health

# 2. Check logs
docker-compose logs -f cv-api

# 3. Test endpoint directly
curl http://localhost:8005/health -v

# 4. Check if port is listening
lsof -i :8005

# 5. Inspect running container
docker-compose exec cv-api bash
pip list  # Check installed packages
python -c "import app; print(app.__version__)"
```

---

## Phase 8: Getting Help

### Resources

| Resource | Location | Use Case |
|----------|----------|----------|
| API Docs | http://localhost:8080/v1/docs | Explore endpoints |
| Code docs | [TECHNICAL_DOCUMENTATION.md](./TECHNICAL_DOCUMENTATION.md) | Deep dives |
| Architecture | [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md) | System design |
| Security | [SECURITY_REVIEW.md](./SECURITY_REVIEW.md) | Security guidelines |
| Service READMEs | `services/*/README.md` | Service-specific info |

### Communication Channels

```
Slack:
  #engineering         - General discussion
  #architecture        - System design
  #security            - Security questions
  #devops              - Infrastructure
  #help-wanted         - Questions & answers

GitHub:
  Issues               - Bug reports
  Discussions          - Architecture questions
  Pull Requests        - Code review
```

### Common Questions

**Q: My service won't start**
A: Check logs (`docker-compose logs cv-service`), verify .env, check port conflicts

**Q: Tests are failing**
A: Clear Docker volumes (`docker-compose down -v`), rebuild (`docker-compose build`)

**Q: Database changed but migrations weren't run**
A: Run `alembic upgrade head` in that service

**Q: How do I add a new service?**
A: Create `services/myservice/`, add Dockerfile, define in docker-compose.yml

**Q: Frontend can't reach backend**
A: Ensure Nginx is running, check CORS headers in response

---

## Your First Week Checklist

- [ ] **Day 1:** Complete Phase 1-3 (environment, codebase, IDE)
- [ ] **Day 1:** Make your first change (Phase 4)
- [ ] **Day 2:** Run services locally, debug issues
- [ ] **Day 2-3:** Write unit tests for your changes
- [ ] **Day 3:** Read full architecture docs
- [ ] **Day 4:** Make a code review on a peer's PR
- [ ] **Day 5:** Deploy your first feature to dev environment

---

## Style Guide & Conventions

### Python

```python
# Follow PEP 8 + Black formatting
# Use type hints everywhere

def find_findings_by_severity(
    org_id: str,
    severity: str,
) -> List[Finding]:
    """Brief one-liner description.
    
    Args:
        org_id: Organization ID (UUID string)
        severity: Severity level (CRITICAL, HIGH, etc.)
    
    Returns:
        List of findings sorted by created_at (DESC)
    
    Raises:
        ValueError: If severity not in allowed values
    """
    if severity not in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
        raise ValueError(f"Invalid severity: {severity}")
    
    return findings
```

### TypeScript/React

```typescript
// Use React functional components with hooks
// Use TypeScript strict mode

interface Finding {
  id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  title: string;
}

export const FindingCard: React.FC<{ finding: Finding }> = ({finding}) => {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  return (
    <div className={`border-l-4 border-${finding.severity.toLowerCase()}`}>
      <h3>{finding.title}</h3>
      {/* ... */}
    </div>
  );
};
```

### Git Commits

```
Type: Brief description (imperative, <50 chars)

Longer explanation if needed.
- Bullet point 1
- Bullet point 2

Fixes #123
Related-To #456
```

Examples:
- `feat: Add custom_tags field to findings`
- `fix: Prevent duplicate findings from being ingested twice`
- `docs: Update API documentation with new endpoint`
- `test: Add integration test for finding deduplication`

---

## Next Steps

1. ✅ Complete this guide
2. 📖 Read [TECHNICAL_DOCUMENTATION.md](./TECHNICAL_DOCUMENTATION.md)
3. 🏗️ Explore [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md)
4. 🔒 Review [SECURITY_REVIEW.md](./SECURITY_REVIEW.md)
5. 💻 Create your first feature branch
6. 🧪 Write tests for your code
7. 📝 Submit a PR for code review

---

**Welcome aboard! We're excited to have you on the team.** 🚀

Questions? Reach out on Slack #help-wanted or create an issue on GitHub.

---

**Last Updated:** January 2025  
**Version:** 1.0
