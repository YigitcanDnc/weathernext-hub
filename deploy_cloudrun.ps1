param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectId,
  [string]$Region = "europe-west1",
  [string]$ServiceName = "weathernext-api"
)

Write-Host "=== Google Cloud Run Deployment ($ServiceName -> $ProjectId / $Region) ===" -ForegroundColor Cyan

gcloud config set project $ProjectId
gcloud services enable run.googleapis.com cloudbuild.googleapis.com earthengine.googleapis.com bigquery.googleapis.com

gcloud run deploy $ServiceName `
  --source . `
  --region $Region `
  --allow-unauthenticated `
  --memory 512Mi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 3 `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId"

Write-Host "`nDeployment tamamlandi! Yukaridaki Service URL'yi not edin." -ForegroundColor Green
