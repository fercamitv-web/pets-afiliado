#requires -Version 7.0
<#
  setup.ps1 - monta o projeto pets-afiliado do zero no Windows.
  Uso:  pwsh -File .\setup.ps1
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Titulo($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($t)     { Write-Host "  [ok] $t" -ForegroundColor Green }
function Aviso($t)  { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Erro($t)   { Write-Host "  [x]  $t" -ForegroundColor Red }

Titulo "1/7 Pre-requisitos"
$faltando = @()
foreach ($c in "python", "git", "gh") {
    if (Get-Command $c -ErrorAction SilentlyContinue) { Ok $c } else { $faltando += $c }
}
if ($faltando.Count) {
    Erro "Instale antes de continuar: $($faltando -join ', ')"
    Write-Host "  python -> https://python.org/downloads"
    Write-Host "  git    -> https://git-scm.com/download/win"
    Write-Host "  gh     -> https://cli.github.com"
    exit 1
}
if (-not (gh auth status 2>$null)) { Aviso "Rode 'gh auth login' e execute de novo."; exit 1 }

Titulo "2/7 Ambiente virtual"
if (-not (Test-Path ".venv")) { python -m venv .venv; Ok "venv criado" } else { Ok "venv ja existe" }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip -q
& $py -m pip install -r requirements.txt -q
if (Test-Path "requirements-dev.txt") { & $py -m pip install -r requirements-dev.txt -q }
Ok "dependencias instaladas"

Titulo "3/7 Credenciais"
$valores = @{}
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match "=" } | ForEach-Object {
        $k, $v = $_ -split "=", 2
        $valores[$k.Trim()] = $v.Trim()
    }
    Ok ".env reaproveitado"
}
function Perguntar($chave, $rotulo, $obrigatorio) {
    if ($valores[$chave]) { return $valores[$chave] }
    $v = Read-Host "  $rotulo"
    if ($obrigatorio -and [string]::IsNullOrWhiteSpace($v)) { Erro "$chave vazio"; exit 1 }
    return $v
}
$valores["LLM_API_KEY"]        = Perguntar "LLM_API_KEY"        "OpenRouter API key (sk-or-...)" $true
$valores["TELEGRAM_BOT_TOKEN"] = Perguntar "TELEGRAM_BOT_TOKEN" "Token do bot (@BotFather)"    $true
$valores["TELEGRAM_CHAT_ID"]   = Perguntar "TELEGRAM_CHAT_ID"   "Seu chat.id (getUpdates)"     $true
$valores["LLM_MODEL"]          = Perguntar "LLM_MODEL"          "Modelo :free do OpenRouter"   $false
if (-not $valores["LLM_MODEL"]) { $valores["LLM_MODEL"] = "deepseek/deepseek-chat-v3-0324:free" }
if (-not $valores["INDEXNOW_KEY"]) {
    $valores["INDEXNOW_KEY"] = (& $py -c "import secrets;print(secrets.token_hex(16))").Trim()
}
($valores.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n" |
    Set-Content ".env" -Encoding utf8
$valores.GetEnumerator() | ForEach-Object {
    [Environment]::SetEnvironmentVariable($_.Key, $_.Value, "Process")
}
Ok ".env gravado"

Titulo "4/7 Estrutura"
foreach ($d in "content", "data", "scripts", "skills", "public", "tests", ".github\workflows") {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}
if (-not (Test-Path "data\pautas.json"))     { "[]" | Set-Content "data\pautas.json" -Encoding utf8 }
if (-not (Test-Path "data\publicados.json")) { "[]" | Set-Content "data\publicados.json" -Encoding utf8 }
@"
.venv/
__pycache__/
*.pyc
.env
agente.log
"@ | Set-Content ".gitignore" -Encoding utf8
Ok "pastas e .gitignore prontos"

Titulo "5/7 Testes"
if (Test-Path "tests\test_sistema.py") {
    & $py -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { Erro "testes falharam"; exit 1 }
    Ok "suite passou"
}

Titulo "6/7 Primeira rodada"
& $py scripts\run.py --artigos 1
Ok "confira o aviso no seu Telegram"

Titulo "7/7 GitHub, secrets e workflow"
git branch -M main 2>$null
if (-not (Test-Path ".git")) { git init -q }
git add -A
git commit -q -m "inicio do projeto" 2>$null
$usuario = (gh api user --jq .login).Trim()
$repo = "pets-afiliado"
if (gh repo view "$usuario/$repo" 2>$null) {
    git remote set-url origin "https://github.com/$usuario/$repo.git" 2>$null
    git push -q -u origin main
} else {
    gh repo create $repo --public --source=. --push --description "Site de afiliados automatico" | Out-Null
}
foreach ($s in "LLM_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "INDEXNOW_KEY") {
    gh secret set $s --repo "$usuario/$repo" --body $valores[$s] | Out-Null
    Ok "secret $s"
}
gh variable set LLM_MODEL --repo "$usuario/$repo" --body $valores["LLM_MODEL"] | Out-Null
Ok "variable LLM_MODEL"
gh workflow run daily.yml --repo "$usuario/$repo"
Ok "workflow disparado"

Write-Host "`nPronto." -ForegroundColor Green
Write-Host "Repo:      https://github.com/$usuario/$repo"
Write-Host "Actions:   https://github.com/$usuario/$repo/actions"
Write-Host "`nFalta so uma coisa: conectar o repo ao Cloudflare Pages" -ForegroundColor Yellow
Write-Host "  dash.cloudflare.com > Workers & Pages > Create > Pages > Connect to Git"
Write-Host "  Build command: exit 0     Output directory: public"