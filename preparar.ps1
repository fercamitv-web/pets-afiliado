#requires -Version 7.0
<#
  preparar.ps1 - faz tudo que da para automatizar no setup.
  Uso: pwsh -ExecutionPolicy Bypass -File .\preparar.ps1
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Titulo($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($t)     { Write-Host "  [ok] $t" -ForegroundColor Green }
function Aviso($t)  { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Erro($t)   { Write-Host "  [x]  $t" -ForegroundColor Red }

function Instalar($id, $cmd) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) { Ok "$cmd presente"; return }
    Aviso "instalando $cmd via winget..."
    winget install --id $id --accept-source-agreements --accept-package-agreements --silent
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Pedir($rotulo) {
    while ($true) {
        $v = (Read-Host "  $rotulo").Trim()
        if ($v) { return $v }
        Erro "vazio, tente de novo"
    }
}

Titulo "1/6 Ferramentas"
Instalar "Python.Python.3.12" "python"
Instalar "Git.Git" "git"
Instalar "GitHub.cli" "gh"

Titulo "2/6 Login no GitHub"
gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Aviso "vai abrir o navegador para autorizar o gh. Clique em 'Authorize'."
    gh auth login --hostname github.com --git-protocol https --web
}
$usuario = (gh api user --jq .login).Trim()
Ok "autenticado como $usuario"

Titulo "3/6 Ambiente virtual"
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip -q
& $py -m pip install -r requirements.txt -q
if (Test-Path "requirements-dev.txt") { & $py -m pip install -r requirements-dev.txt -q }
Ok "dependencias instaladas"

$valores = @{}

Titulo "4/6 OpenRouter"
$valores["LLM_API_KEY"] = Pedir "Cole a API key do OpenRouter (sk-or-...)"
$env:LLM_API_KEY = $valores["LLM_API_KEY"]
$modelo = (& $py scripts\testar_chave.py).Trim()
if ($LASTEXITCODE -ne 0) { Erro "a chave nao respondeu. Confira em openrouter.ai/keys"; exit 1 }
$valores["LLM_MODEL"] = $modelo
Ok "modelo :free validado: $modelo"

Titulo "5/6 Telegram"
$valores["TELEGRAM_BOT_TOKEN"] = Pedir "Cole o token do bot (@BotFather)"
$env:TELEGRAM_BOT_TOKEN = $valores["TELEGRAM_BOT_TOKEN"]
Aviso "Abra o Telegram e mande um 'oi' para o seu bot. Vou escutar por 2 minutos..."
$chatid = (& $py scripts\pegar_chatid.py).Trim()
if ($LASTEXITCODE -ne 0) { Erro "nao recebi a mensagem. Mande um 'oi' e rode de novo."; exit 1 }
$valores["TELEGRAM_CHAT_ID"] = $chatid
Ok "chat.id capturado sozinho: $chatid"

$valores["INDEXNOW_KEY"] = (& $py -c "import secrets;print(secrets.token_hex(16))").Trim()
Ok "INDEXNOW_KEY gerada"

Titulo "6/6 GitHub, secrets e workflow"
($valores.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n" |
    Set-Content ".env" -Encoding utf8
$valores.GetEnumerator() | ForEach-Object {
    [Environment]::SetEnvironmentVariable($_.Key, $_.Value, "Process")
}
@"
.venv/
__pycache__/
*.pyc
.env
agente.log
"@ | Set-Content ".gitignore" -Encoding utf8

foreach ($d in "content", "data", "public") { New-Item -ItemType Directory -Force $d | Out-Null }
if (-not (Test-Path "data\pautas.json"))     { "[]" | Set-Content "data\pautas.json" -Encoding utf8 }
if (-not (Test-Path "data\publicados.json")) { "[]" | Set-Content "data\publicados.json" -Encoding utf8 }

if (-not (Test-Path ".git")) { git init -q }
git branch -M main
git add -A
git commit -q -m "inicio do projeto" 2>$null

$repo = "pets-afiliado"
if (gh repo view "$usuario/$repo" *> $null) {
    git remote set-url origin "https://github.com/$usuario/$repo.git" 2>$null
    git push -q -u origin main
} else {
    gh repo create $repo --public --source=. --push --description "Site de afiliados automatico" | Out-Null
}
Ok "repo em https://github.com/$usuario/$repo"

foreach ($s in "LLM_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "INDEXNOW_KEY") {
    gh secret set $s --repo "$usuario/$repo" --body $valores[$s] | Out-Null
    Ok "secret $s gravado"
}
gh variable set LLM_MODEL --repo "$usuario/$repo" --body $valores["LLM_MODEL"] | Out-Null
Ok "variable LLM_MODEL gravada"

& $py scripts\run.py --artigos 1
gh workflow run daily.yml --repo "$usuario/$repo"
Ok "workflow disparado"

Write-Host "`nTudo pronto. Confira o Telegram." -ForegroundColor Green
Write-Host "Falta 1 passo manual: conectar o repo ao Cloudflare Pages" -ForegroundColor Yellow
Write-Host "  dash.cloudflare.com > Workers & Pages > Create > Pages > Connect to Git"
Write-Host "  Build command: exit 0     Output directory: public"