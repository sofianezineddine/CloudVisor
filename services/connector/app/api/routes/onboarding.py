"""Onboarding endpoints for cloud provider setup guides."""

from fastapi import APIRouter

from app.schemas import OnboardingResponse
from app.services.onboarding_templates import AWS_CLOUDFORMATION_TEMPLATE

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/aws/template", response_model=OnboardingResponse)
async def get_aws_template() -> OnboardingResponse:
    """Get CloudFormation template for AWS onboarding."""
    return OnboardingResponse(
        provider="aws",
        instructions="""## AWS CloudFormation Setup

1. **Download the CloudFormation template** from this endpoint
2. **Get your CloudVisor Account ID** and **External ID** from your CloudVisor dashboard
3. **Create the stack** in AWS CloudFormation console:
   - Go to CloudFormation → Create stack → With new resources
   - Upload the template file
   - Enter your CloudVisor Account ID and External ID
   - Acknowledge IAM capabilities
   - Click "Create stack"
4. **Copy the Role ARN** from the stack outputs
5. **Add the account** in CloudVisor using the Role ARN

**Security Note:** The External ID prevents confused deputy attacks. Never share it publicly.
""",
        template=AWS_CLOUDFORMATION_TEMPLATE,
    )


@router.get("/azure/instructions", response_model=OnboardingResponse)
async def get_azure_instructions() -> OnboardingResponse:
    """Get Azure service principal setup instructions."""
    instructions = """## Azure Service Principal Setup

### Option 1: Using Azure CLI (Recommended)

1. **Login to Azure:**
   ```bash
   az login
   ```

2. **Set your subscription:**
   ```bash
   az account set --subscription "Your Subscription Name or ID"
   ```

3. **Create the service principal:**
   ```bash
   az ad sp create-for-rbac \\
     --name "CloudVisor-ReadOnly" \\
     --role "Reader" \\
     --scopes "/subscriptions/YOUR-SUBSCRIPTION-ID" \\
     --years 1
   ```

4. **Note down these values from the output:**
   - `appId` → This is your **Client ID**
   - `password` → This is your **Client Secret**
   - `tenant` → This is your **Tenant ID**
   - Your subscription ID is your **Subscription ID**

5. **Add the account** in CloudVisor using these values

### Option 2: Using Azure Portal

1. Go to **Azure Active Directory** → **App registrations** → **New registration**
2. Name: `CloudVisor-ReadOnly`
3. Click **Register**
4. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
5. Add `User.Read` (if needed for user context)
6. Go to **Certificates & secrets** → **New client secret** → Create
7. Go to **Subscriptions** → Select your subscription → **Access control (IAM)**
8. **Add** → **Add role assignment** → **Reader** → Select your app
9. Copy these values for CloudVisor:
   - **Application (client) ID**
   - **Directory (tenant) ID**
   - **Client Secret value** (only shown once!)
   - **Subscription ID**

### Required Permissions

The Reader role grants:
- ✅ Read access to all resources
- ✅ Read access to resource groups
- ✅ Read access to storage accounts
- ❌ No write/delete permissions
- ❌ No role assignment permissions

**Security Note:** Rotate the client secret periodically. CloudVisor only needs Reader access.
"""
    return OnboardingResponse(
        provider="azure",
        instructions=instructions,
    )


@router.get("/gcp/instructions", response_model=OnboardingResponse)
async def get_gcp_instructions() -> OnboardingResponse:
    """Get GCP service account setup instructions."""
    instructions = """## GCP Service Account Setup

### Prerequisites
- Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Have Owner or Editor role on the project

### Step 1: Create Service Account

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR-PROJECT-ID

# Create the service account
gcloud iam service-accounts create cloudvisor-ro \\
  --display-name="CloudVisor Read Only" \\
  --project=YOUR-PROJECT-ID
```

### Step 2: Grant Viewer Role

```bash
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \\
  --member="serviceAccount:cloudvisor-ro@YOUR-PROJECT-ID.iam.gserviceaccount.com" \\
  --role="roles/viewer"
```

### Step 3: Create and Download Key

```bash
# Create key file
gcloud iam service-accounts keys create cloudvisor-key.json \\
  --iam-account="cloudvisor-ro@YOUR-PROJECT-ID.iam.gserviceaccount.com"
```

### Step 4: Upload to CloudVisor

1. Go to CloudVisor dashboard
2. Click "Connect Account" → Google Cloud
3. Upload the `cloudvisor-key.json` file
4. Verify the connection

### Required Permissions

The Viewer role (`roles/viewer`) grants:
- ✅ Read access to all resources
- ✅ Read access to IAM policies
- ✅ Read access to Cloud Asset Inventory
- ❌ No write/delete permissions
- ❌ No role assignment permissions

### Security Best Practices

1. **Store the key securely** - Treat it like a password
2. **Rotate keys periodically** - Create new keys and delete old ones
3. **Use workload identity** - If running in GKE, prefer workload identity over keys
4. **Limit scope** - Only grant access to specific projects, not the entire organization

**Security Note:** The JSON key file contains sensitive credentials. Never commit it to version control.
"""
    return OnboardingResponse(
        provider="gcp",
        instructions=instructions,
    )


@router.get("/oci/instructions", response_model=OnboardingResponse)
async def get_oci_instructions() -> OnboardingResponse:
    """Get OCI setup instructions."""
    instructions = """## Oracle Cloud Infrastructure (OCI) Setup

### Prerequisites
- OCI CLI installed (`pip install oci-cli`)
- Have Administrator or IAM Admin role in the tenancy

### Step 1: Generate API Signing Key

```bash
# Generate private key
openssl genrsa -out ~/.oci/oci_api_key.pem 2048

# Set permissions
chmod go-rwx ~/.oci/oci_api_key.pem

# Generate public key
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem
```

### Step 2: Upload Public Key to OCI

1. Go to **Identity & Security** → **Users** → Select your user
2. Click **API Keys** → **Add API Key**
3. Choose **Paste public key**
4. Paste the contents of `~/.oci/oci_api_key_public.pem`
5. Click **Add**
6. **Note down the fingerprint** shown after adding

### Step 3: Create IAM Policy for Read-Only Access

1. Go to **Identity & Security** → **Policies**
2. Click **Create Policy**
3. Name: `CloudVisorReadOnlyPolicy`
4. Policy statements:
   ```
   Allow group CloudVisorUsers to read all-resources in tenancy
   Allow group CloudVisorUsers to inspect all-resources in tenancy
   Allow group CloudVisorUsers to read buckets in tenancy
   Allow group CloudVisorUsers to read objectstorage-namespaces in tenancy
   Allow group CloudVisorUsers to read volume-family in tenancy
   Allow group CloudVisorUsers to read network-family in tenancy
   Allow group CloudVisorUsers to read database-family in tenancy
   Allow group CloudVisorUsers to read compute-family in tenancy
   ```

### Step 4: Create Group and Add User

1. Go to **Identity & Security** → **Groups** → **Create Group**
2. Name: `CloudVisorUsers`
3. Add your user to this group
4. Attach the `CloudVisorReadOnlyPolicy` to the group

### Step 5: Collect Configuration Values

From the API Key page, note these values:
- **User OCID**
- **Fingerprint**
- **Tenancy OCID**
- **Region** (e.g., `us-ashburn-1`)

### Step 6: Add to CloudVisor

1. Go to CloudVisor dashboard
2. Click "Connect Account" → Oracle Cloud
3. Enter these values:
   - User OCID
   - Fingerprint
   - Tenancy OCID
   - Region
   - Upload the private key file (`oci_api_key.pem`)
4. Verify the connection

### Required Permissions Summary

| Permission | Required | Purpose |
|------------|----------|---------|
| read all-resources | ✅ | Resource inventory |
| inspect all-resources | ✅ | Resource metadata |
| read buckets | ✅ | Object storage |
| read objectstorage-namespaces | ✅ | Storage namespaces |
| read volume-family | ✅ | Block storage |
| read network-family | ✅ | VCNs, subnets, security lists |
| read database-family | ✅ | Autonomous databases |
| read compute-family | ✅ | Instances |

**Security Note:** Only read/inspect permissions are required. No write/delete permissions are needed.
"""
    return OnboardingResponse(
        provider="oci",
        instructions=instructions,
    )
