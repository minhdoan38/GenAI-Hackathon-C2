param(
    [string]$BillingAccount = "01E09E-F5D59F-28BA1C",
    [string]$Amount = "250000VND"
)

$ErrorActionPreference = "Stop"
$gcloud = (Get-Command gcloud.cmd -ErrorAction Stop).Source
$name = "CityMind AI MVP"
$existing = & $gcloud billing budgets list --billing-account $BillingAccount --filter "displayName='$name'" --format "value(name)"
if ($LASTEXITCODE -ne 0) { throw "Could not list billing budgets" }

if ($existing) {
    Write-Host "Budget already exists: $existing"
    exit 0
}

& $gcloud billing budgets create --billing-account $BillingAccount --display-name $name --budget-amount $Amount --threshold-rule percent=0.50 --threshold-rule percent=0.90 --threshold-rule percent=1.00
if ($LASTEXITCODE -ne 0) { throw "Budget creation failed" }
