param(
    [string]$Project = "citymind-ai-500910",
    [string]$Region = "us-central1",
    [string]$Bucket = "citymind-ai-500910-report-images"
)

$ErrorActionPreference = "Stop"
$gcloud = (Get-Command gcloud.cmd -ErrorAction Stop).Source

function Invoke-Gcloud {
    & $gcloud @args
    if ($LASTEXITCODE -ne 0) { throw "gcloud command failed" }
}

function Ensure-ServiceAccount([string]$Name, [string]$DisplayName) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $gcloud iam service-accounts describe "$Name@$Project.iam.gserviceaccount.com" --project $Project *> $null
    $exists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousPreference
    if (-not $exists) {
        Invoke-Gcloud iam service-accounts create $Name --display-name $DisplayName --project $Project
    }
}

function Ensure-Secret([string]$Name, [int]$Bytes = 32) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $gcloud secrets describe $Name --project $Project *> $null
    $exists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousPreference
    if ($exists) { return }

    $randomBytes = New-Object byte[] $Bytes
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) }
    finally { $generator.Dispose() }
    $value = [Convert]::ToBase64String($randomBytes)
    $temp = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllText($temp, $value)
        Invoke-Gcloud secrets create $Name --replication-policy automatic --data-file $temp --project $Project
    }
    finally {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    }
}

Invoke-Gcloud config set project $Project
Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com bigquery.googleapis.com storage.googleapis.com

Ensure-ServiceAccount "citymind-backend" "CityMind backend"
Ensure-ServiceAccount "citymind-frontend" "CityMind frontend"
Ensure-Secret "citymind-officer-api-key"
Ensure-Secret "citymind-dashboard-password" 18
Ensure-Secret "citymind-session-secret"

$backendSa = "citymind-backend@$Project.iam.gserviceaccount.com"
$frontendSa = "citymind-frontend@$Project.iam.gserviceaccount.com"

foreach ($role in @("roles/aiplatform.user", "roles/bigquery.dataEditor", "roles/bigquery.jobUser", "roles/storage.objectAdmin")) {
    Invoke-Gcloud projects add-iam-policy-binding $Project --member "serviceAccount:$backendSa" --role $role --condition None --quiet
}

Invoke-Gcloud secrets add-iam-policy-binding citymind-officer-api-key --member "serviceAccount:$backendSa" --role roles/secretmanager.secretAccessor --project $Project
Invoke-Gcloud secrets add-iam-policy-binding citymind-officer-api-key --member "serviceAccount:$frontendSa" --role roles/secretmanager.secretAccessor --project $Project
Invoke-Gcloud secrets add-iam-policy-binding citymind-dashboard-password --member "serviceAccount:$frontendSa" --role roles/secretmanager.secretAccessor --project $Project
Invoke-Gcloud secrets add-iam-policy-binding citymind-session-secret --member "serviceAccount:$frontendSa" --role roles/secretmanager.secretAccessor --project $Project

Invoke-Gcloud run deploy citymind-api --source backend --region $Region --service-account $backendSa --allow-unauthenticated --min-instances 0 --max-instances 3 --concurrency 40 --cpu 1 --memory 512Mi --timeout 120 --set-env-vars "APP_ENV=production,GOOGLE_CLOUD_PROJECT=$Project,GOOGLE_CLOUD_LOCATION=$Region,GEMINI_MODEL=gemini-2.5-flash,BIGQUERY_DATASET=citymind,BIGQUERY_REPORTS_TABLE=reports,ENABLE_BIGQUERY=true,ENABLE_IMAGE_STORAGE=true,GCS_BUCKET_NAME=$Bucket,ENABLE_URBAN_CONTEXT=false,REPORT_RATE_LIMIT_PER_MINUTE=5,CORS_ORIGINS=https://invalid.local" --set-secrets "OFFICER_API_KEY=citymind-officer-api-key:latest" --project $Project --quiet

$backendUrl = & $gcloud run services describe citymind-api --region $Region --project $Project --format "value(status.url)"
if (-not $backendUrl) { throw "Backend URL not found" }

Invoke-Gcloud run deploy citymind-web --source frontend --region $Region --service-account $frontendSa --allow-unauthenticated --min-instances 0 --max-instances 2 --concurrency 40 --cpu 1 --memory 512Mi --timeout 60 --set-env-vars "BACKEND_API_URL=$backendUrl" --set-secrets "OFFICER_API_KEY=citymind-officer-api-key:latest,OFFICER_DASHBOARD_PASSWORD=citymind-dashboard-password:latest,SESSION_SECRET=citymind-session-secret:latest" --project $Project --quiet

$frontendUrl = & $gcloud run services describe citymind-web --region $Region --project $Project --format "value(status.url)"
if (-not $frontendUrl) { throw "Frontend URL not found" }

Invoke-Gcloud run services update citymind-api --region $Region --update-env-vars "CORS_ORIGINS=$frontendUrl" --project $Project --quiet

Write-Host "Frontend: $frontendUrl"
Write-Host "Backend:  $backendUrl"
Write-Host "Read login password: gcloud secrets versions access latest --secret=citymind-dashboard-password --project=$Project"
