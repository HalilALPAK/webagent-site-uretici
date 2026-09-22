"""Yayın Ajanı: üretilen Laravel sitesini kullanıcının kendi sunucusuna yükler.

Akış:
  1. Paket    — proje tek bir ZIP'e konur, sunucuya özel `.env` (adres, veritabanı) eklenir.
  2. Aktarım  — ZIP + tek kullanımlık `installer.php` FTP/FTPS/SFTP ile web köküne atılır.
  3. Kurulum  — tarayıcıdan installer çağrılır: ZIP'i açar, kodu web kökünün dışına taşır,
                public dosyalarını köke koyar, (MySQL ise) tabloları kurup içeriği yükler,
                izinleri ayarlar, sonra ZIP'i ve kendini siler.
  4. Kontrol  — site ve yönetim paneli açılıyor mu, installer gerçekten silinmiş mi diye bakılır.

Paylaşımlı hostingde uygulama kodu web kökünün dışında tutulur; dışarı yalnızca public klasörü açılır.
"""
from __future__ import annotations

import re
import secrets
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

# Sunucuya gitmeyecek dosyalar (yerel geliştirme kalıntıları)
SKIP_DIRS = {".git", "node_modules", "__pycache__", "tests"}
SKIP_FILES = {".env", "run.bat", "qa-junit.xml", ".gitignore"}
SKIP_SUFFIX = {".log"}


@dataclass
class Target:
    """Kullanıcının sunucu bilgileri."""
    method: str            # ftp | ftps | sftp
    host: str
    port: int
    username: str
    password: str
    remote_dir: str        # web kökü, ör. /public_html
    site_url: str          # https://firma.com
    db: dict               # {"type": "sqlite"} ya da MySQL bilgileri (sunucudan görünen host ile)


# ============================================================ paket

def _env_for_server(site_dir: Path, target: Target) -> str:
    """Yereldeki .env'i sunucu için uyarlar: adres, veritabanı, hata ayıklama kapalı."""
    lines: list[str] = []
    drop = {"APP_ENV", "APP_DEBUG", "APP_URL", "DB_CONNECTION", "DB_HOST", "DB_PORT", "DB_DATABASE",
            "DB_USERNAME", "DB_PASSWORD", "PUBLIC_PATH", "LOG_LEVEL"}
    for line in (site_dir / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and line.split("=", 1)[0].strip() in drop:
            continue
        lines.append(line)

    def q(v: object) -> str:
        return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'

    url = target.site_url.rstrip("/")
    # PUBLIC_PATH sunucudaki kurulum betiği tarafından yazılır: FTP'deki yol ile
    # sunucudaki gerçek dosya yolu çoğu hostingde farklıdır.
    lines += ["APP_ENV=production", "APP_DEBUG=false", f"APP_URL={q(url)}", "LOG_LEVEL=error"]
    if target.db.get("type") == "mysql":
        lines += ["DB_CONNECTION=mysql", f"DB_HOST={q(target.db['host'])}", f"DB_PORT={int(target.db.get('port') or 3306)}",
                  f"DB_DATABASE={q(target.db['database'])}", f"DB_USERNAME={q(target.db['username'])}",
                  f"DB_PASSWORD={q(target.db.get('password', ''))}"]
    else:
        lines += ["DB_CONNECTION=sqlite"]
    return "\n".join(lines) + "\n"


def build_package(site_dir: Path, target: Target, out_zip: Path) -> tuple[int, int]:
    """Projeyi ZIP'ler. Döndürür: (dosya sayısı, boyut)."""
    sqlite = target.db.get("type") != "mysql"
    count = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in site_dir.rglob("*"):
            rel = path.relative_to(site_dir)
            parts = set(rel.parts)
            if parts & SKIP_DIRS or path.name in SKIP_FILES or path.suffix in SKIP_SUFFIX:
                continue
            if path.is_dir():
                continue
            if rel.as_posix() == "database/database.sqlite" and not sqlite:
                continue  # MySQL'e kurulacaksa yerel veritabanı gitmesin
            skip_dirs = {("storage", "logs"), ("bootstrap", "cache"), ("storage", "framework", "cache"),
                         ("storage", "framework", "sessions"), ("storage", "framework", "views")}
            if rel.parts[:2] in skip_dirs or rel.parts[:3] in skip_dirs:
                continue
            z.write(path, rel.as_posix())
            count += 1
        z.writestr(".env", _env_for_server(site_dir, target))
        # Laravel'in önbellek klasörleri boş da olsa bulunmalı
        for keep in ("storage/logs/.gitignore", "bootstrap/cache/.gitignore", "storage/framework/cache/data/.gitignore",
                     "storage/framework/sessions/.gitignore", "storage/framework/views/.gitignore"):
            z.writestr(keep, "*\n!.gitignore\n")
    return count, out_zip.stat().st_size


INSTALLER_TEMPLATE = r"""<?php
/**
 * Web Agent tek kullanımlık kurulum betiği. Çalıştıktan sonra kendini ve ZIP'i siler.
 * Uygulama kodu web kökünün DIŞINA açılır; burada yalnızca public dosyaları kalır.
 */
header('Content-Type: application/json; charset=utf-8');
@set_time_limit(900);
@ini_set('memory_limit', '512M');

$TOKEN = '{token}';
$ZIP   = __DIR__ . '/{zip_name}';
$SLUG  = '{slug}';
$MIGRATE = {migrate};

function out($ok, $message, $log = []) {
    echo json_encode(['ok' => $ok, 'message' => $message, 'log' => $log], JSON_UNESCAPED_UNICODE);
    exit;
}
if (!hash_equals($TOKEN, $_GET['token'] ?? '')) { http_response_code(403); out(false, 'Geçersiz anahtar.'); }
if (!is_file($ZIP)) { out(false, 'Yükleme paketi bulunamadı: ' . basename($ZIP)); }
if (!class_exists('ZipArchive')) { out(false, 'Sunucuda PHP zip eklentisi yok; hosting firmanızdan açmasını isteyin.'); }
if (version_compare(PHP_VERSION, '8.3', '<')) { out(false, 'Sunucuda PHP ' . PHP_VERSION . ' var; Laravel 13 için en az 8.3 gerekli.'); }

$log = ['PHP ' . PHP_VERSION];
$root = __DIR__;                       // web kökü
$parent = dirname($root);
$appDir = (is_writable($parent) ? $parent : $root) . '/webagent-app-' . $SLUG;
$inWebRoot = strpos($appDir, $root) === 0;

// 1) eski kurulumu temizle
$rrmdir = function ($dir) use (&$rrmdir) {
    if (!is_dir($dir)) return;
    foreach (scandir($dir) as $f) {
        if ($f === '.' || $f === '..') continue;
        $p = "$dir/$f";
        is_dir($p) ? $rrmdir($p) : @unlink($p);
    }
    @rmdir($dir);
};
$rrmdir($appDir);
if (!@mkdir($appDir, 0755, true) && !is_dir($appDir)) { out(false, "Klasör oluşturulamadı: $appDir"); }

// 2) paketi aç
$zip = new ZipArchive();
if ($zip->open($ZIP) !== true) { out(false, 'Paket açılamadı.'); }
if (!$zip->extractTo($appDir)) { $zip->close(); out(false, 'Paket çıkarılamadı (disk kotası ya da izin).'); }
$log[] = $zip->numFiles . ' dosya çıkarıldı';
$zip->close();

// 3) public/* dosyalarını web köküne taşı, index.php'yi uygulama klasörüne bağla
$publicDir = "$appDir/public";
$move = function ($src, $dst) use (&$move) {
    foreach (scandir($src) as $f) {
        if ($f === '.' || $f === '..') continue;
        if (is_dir("$src/$f")) {
            if (!is_dir("$dst/$f")) @mkdir("$dst/$f", 0755, true);
            $move("$src/$f", "$dst/$f");
            @rmdir("$src/$f");
        } else {
            @rename("$src/$f", "$dst/$f");
        }
    }
};
$move($publicDir, $root);
file_put_contents($root . '/index.php', "<?php\n\$appDir = " . var_export($appDir, true) . ";\n"
    . "require \$appDir . '/vendor/autoload.php';\n"
    . "\$app = require \$appDir . '/bootstrap/app.php';\n"
    . "\$app->handleRequest(Illuminate\\Http\\Request::capture());\n");
$log[] = 'public dosyaları web köküne taşındı';

// 3b) sunucudaki gerçek web kökünü .env'e yaz (yüklenen görseller buraya kaydedilir)
$envFile = "$appDir/.env";
$env = is_file($envFile) ? file_get_contents($envFile) : '';
$env = preg_replace('/^PUBLIC_PATH=.*$/m', '', $env);
$env = rtrim($env) . PHP_EOL . 'PUBLIC_PATH="' . addcslashes($root, '\\"') . '"' . PHP_EOL;
file_put_contents($envFile, $env);

// 4) uygulama klasörü web kökünün içindeyse dışarıdan erişimi kapat
if ($inWebRoot) {
    file_put_contents($appDir . '/.htaccess', "Require all denied\nDeny from all\n");
    $log[] = 'UYARI: uygulama klasörü web kökünün içinde (üst klasöre yazılamadı); .htaccess ile kapatıldı';
}

// 5) izinler
@chmod("$appDir/storage", 0775);
foreach (['storage/app', 'storage/framework', 'storage/logs', 'bootstrap/cache', 'storage/framework/cache',
          'storage/framework/sessions', 'storage/framework/views', 'storage/framework/cache/data'] as $d) {
    if (!is_dir("$appDir/$d")) @mkdir("$appDir/$d", 0775, true);
    @chmod("$appDir/$d", 0775);
}
if (!is_file("$appDir/database/database.sqlite")) @touch("$appDir/database/database.sqlite");
@chmod("$appDir/database/database.sqlite", 0664);
if (!is_dir("$root/uploads")) @mkdir("$root/uploads", 0775, true);

// 6) Laravel'i ayağa kaldır: önbellekleri temizle, gerekirse tabloları kur ve içeriği yükle
require $appDir . '/vendor/autoload.php';
$app = require $appDir . '/bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();
$run = function ($command) use ($kernel, &$log) {
    $code = $kernel->call($command);
    $output = trim($kernel->output());
    $log[] = "» $command" . ($output ? ': ' . substr(preg_replace('/\s+/', ' ', $output), 0, 300) : '');
    return $code;
};
try {
    $run('config:clear');
    $run('view:clear');
    if ($MIGRATE) {
        if ($run('migrate:fresh --seed --force') !== 0) { out(false, 'Veritabanı kurulumu başarısız.', $log); }
    }
} catch (Throwable $e) {
    out(false, 'Laravel başlatılamadı: ' . $e->getMessage(), $log);
}

// 7) izleri temizle
@unlink($ZIP);
@unlink(__FILE__);
out(true, 'Kurulum tamamlandı.', $log);
"""


def build_installer(zip_name: str, token: str, slug: str, migrate: bool) -> str:
    return INSTALLER_TEMPLATE.replace("{token}", token).replace("{zip_name}", zip_name) \
        .replace("{slug}", slug).replace("{migrate}", "true" if migrate else "false")


# ============================================================ aktarım

class Uploader:
    """FTP / FTPS / SFTP üzerinden dosya gönderir."""

    def __init__(self, target: Target):
        self.t = target
        self.conn = None
        self.sftp = None

    def __enter__(self) -> "Uploader":
        t = self.t
        if t.method == "sftp":
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(t.host, port=t.port or 22, username=t.username, password=t.password, timeout=30)
            self.conn, self.sftp = client, client.open_sftp()
        else:
            from ftplib import FTP, FTP_TLS
            self.conn = (FTP_TLS if t.method == "ftps" else FTP)()
            self.conn.connect(t.host, t.port or 21, timeout=30)
            self.conn.login(t.username, t.password)
            if t.method == "ftps":
                self.conn.prot_p()
            self.conn.set_pasv(True)
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self.sftp:
                self.sftp.close()
            self.conn.close() if self.sftp else self.conn.quit()
        except Exception:
            pass

    def put(self, local: Path, remote_name: str) -> None:
        remote_dir = self.t.remote_dir.rstrip("/") or "/"
        if self.sftp:
            self.sftp.put(str(local), f"{remote_dir}/{remote_name}")
        else:
            self.conn.cwd(remote_dir)
            with local.open("rb") as f:
                self.conn.storbinary(f"STOR {remote_name}", f, blocksize=1 << 16)

    def listdir(self) -> list[str]:
        remote_dir = self.t.remote_dir.rstrip("/") or "/"
        if self.sftp:
            return self.sftp.listdir(remote_dir)
        self.conn.cwd(remote_dir)
        return self.conn.nlst()


# ============================================================ ajan

class DeployAgent:
    """İş akışına bağlı yayın adımı (kendi günlüğünü job'a yazar)."""

    name = "Yayın Ajanı"

    def __init__(self, job, site_dir: Path):
        self.job = job
        self.site_dir = site_dir

    def log(self, message: str, level: str = "info") -> None:
        self.job.log(self.name, message, level)

    def run(self, target: Target) -> dict:
        slug = re.sub(r"[^a-z0-9-]", "", self.site_dir.name.lower())[:40] or "site"
        token = secrets.token_hex(16)
        zip_name = f"webagent-{secrets.token_hex(4)}.zip"
        installer_name = f"webagent-install-{secrets.token_hex(4)}.php"
        staging = self.site_dir.parent / f".deploy-{self.job.id}"
        staging.mkdir(exist_ok=True)
        zip_path = staging / zip_name
        migrate = target.db.get("type") == "mysql" or not (self.site_dir / "database" / "database.sqlite").exists()

        self.log("Paket hazırlanıyor…")
        count, size = build_package(self.site_dir, target, zip_path)
        installer_path = staging / installer_name
        installer_path.write_text(build_installer(zip_name, token, slug, migrate), encoding="utf-8")
        self.log(f"{count} dosya paketlendi ({size / 1e6:.1f} MB).", "ok")

        self.log(f"{target.method.upper()} ile {target.host} sunucusuna yükleniyor… (birkaç dakika sürebilir)")
        with Uploader(target) as up:
            up.put(zip_path, zip_name)
            up.put(installer_path, installer_name)
        self.log("Paket sunucuya yüklendi, kurulum başlatılıyor…", "ok")

        base = target.site_url.rstrip("/")
        try:
            r = httpx.get(f"{base}/{installer_name}", params={"token": token}, timeout=900, follow_redirects=True)
            result = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise RuntimeError(
                f"Kurulum betiği çalıştırılamadı ({e}). Site adresi doğru mu ve klasör web kökü mü? "
                f"Elle denemek için: {base}/{installer_name}?token={token}"
            )
        for line in result.get("log", []):
            self.log(line)
        if not result.get("ok"):
            raise RuntimeError(result.get("message", "Kurulum başarısız."))

        checks = self.verify(base, installer_name)
        self.log("Yayın tamamlandı: " + base, "ok")
        zip_path.unlink(missing_ok=True)
        installer_path.unlink(missing_ok=True)
        staging.rmdir()
        return {"url": base, "admin_url": f"{base}/admin", "checks": checks,
                "database": "MySQL" if migrate else "SQLite (dosya)", "host": target.host}

    def verify(self, base: str, installer_name: str) -> list[str]:
        checks: list[str] = []
        with httpx.Client(timeout=30, follow_redirects=False) as c:
            r = c.get(base + "/")
            checks.append(f"Ana sayfa: {r.status_code}")
            if r.status_code != 200:
                raise RuntimeError(f"Site açılmıyor (HTTP {r.status_code}). Sunucu günlüklerine bakın.")
            r = c.get(base + "/admin")
            checks.append(f"Yönetim paneli: {r.status_code}")
            r = c.get(f"{base}/{installer_name}")
            ok = r.status_code in (403, 404, 410)
            checks.append("Kurulum betiği silindi" if ok else f"UYARI: kurulum betiği hâlâ erişilebilir ({r.status_code})")
            if not ok:
                self.log(f"Kurulum betiği sunucudan silinemedi, elle silin: {installer_name}", "warn")
        for line in checks:
            self.log(line, "ok" if "UYARI" not in line else "warn")
        return checks
