# Creates ONLY a new BurhanKARADUMAN/RadiantDAQ public repository. No existing repos are modified.
$ErrorActionPreference = 'Stop'
$owner = 'BurhanKARADUMAN'
$name = 'RadiantDAQ'
$repo = "$owner/$name"
$root = $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git not found. Restart PowerShell after installing Git.' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) not found. Restart PowerShell after installing GitHub CLI.' }
Push-Location $root
try {
    Write-Host "Publishing a NEW repository only: $repo" -ForegroundColor Cyan
    & gh auth status
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI authentication failed. Run gh auth login.' }
    $user = & gh api user --jq '.login'
    if ($LASTEXITCODE -ne 0 -or $user.Trim() -ne $owner) { throw "Active GitHub user is not $owner. Aborting." }
    # PowerShell 5.1 treats native stderr as a terminating error when
    # $ErrorActionPreference is Stop; gh repo view on a missing repo emits stderr.
    # Instead list accessible repositories (success exit code, even if this one does not exist).
    $existingNames = @( & gh repo list $owner --limit 1000 --json name --jq '.[].name' )
    if ($LASTEXITCODE -ne 0) { throw 'Unable to list repositories safely. Aborting.' }
    if ($existingNames -contains $name) { throw "The repository $repo already exists. To protect existing content, this script will NOT overwrite it." }
    if (Test-Path (Join-Path $root '.git')) { throw 'This folder already contains .git. Aborting to avoid changing an existing worktree.' }
    & git init -b main
    if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
    & git config user.name $owner
    $uid = & gh api user --jq '.id'
    if ($LASTEXITCODE -ne 0) { throw 'Could not retrieve GitHub user id.' }
    & git config user.email "${uid}+${owner}@users.noreply.github.com"
    & git add .
    if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
    & git commit -m 'feat: initialize RadiantDAQ synthetic detector readout research toolkit'
    if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }
    & gh repo create $repo --public --source . --remote origin --push --description 'Reproducible scintillator-SiPM readout, timing and PET instrumentation research toolkit (synthetic MVP)'
    if ($LASTEXITCODE -ne 0) { throw 'gh repo create/push failed. Check GitHub repo state before retrying.' }
    Write-Host "PUBLISHED: https://github.com/$repo" -ForegroundColor Green
} finally {
    Pop-Location
}
