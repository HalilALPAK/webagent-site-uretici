# Web Agent — Rakip Analizinden Çok Ajanlı Site Üretimi

Bir **sektör** girersiniz. Ajan topluluğu rakip siteleri bulur, tarar ve modüllerini çıkarır. Sonra
bunlardan bir modül stratejisi kurar ve size çalışır durumda bir **PHP / Laravel 13** projesi üretir:
ziyaretçi sitesi (Blade), **Filament** admin paneli, JSON API ve SQLite veritabanı.
Görsel dil [DESIGN.md](DESIGN.md) rehberinden gelir.

## Masaüstü uygulaması (WebAgent.exe)

> Uygulamayı **kullanacak kişi** için hazırlanmış kurulum ve kullanım kılavuzu: [dist/README.md](dist/README.md)

`dist/WebAgent.exe` tek dosyadır, çift tıklayınca kendi penceresinde açılır:

1. **İlk kurulum** (yalnızca ilk açılışta): PHP 8.4, Composer ve Laravel + Filament temel projesi
   `Belgeler\WebAgent	ools` klasörüne indirilir. İndirilen dosyalar SHA-256 ile doğrulanır, yönetici yetkisi gerekmez.
2. **Sihirbaz:**
   - İşletme adı, sektör, şehir, bilinen rakipler ve özel istekler
   - **Mevcut siteniz** (varsa): adresini yazarsanız Miras Ajanı oradan gerçek bilgileri (iletişim, hakkımızda,
     hizmet/ürün listesi, çalışma saatleri) ve **fotoğrafları** devralır; eksik bilgiler rapora yazılır
   - **Logonuz** (isteğe bağlı): yüklerseniz başlıkta, footer'da, favicon'da ve yönetim panelinde kullanılır;
     yüklemezseniz marka adının baş harfinden şık bir işaret üretilir
   - Telefon, e-posta ve adres (boş bırakılırsa mevcut siteden alınır, o da yoksa örnek bilgi yazılır)
   - **Görünüm:** küçük site maketleri arasından seçim — *Ajan karar versin / Aydınlık ve sade / Koyu /
     Canlı ve renkli / Çok sade*. Seçim sektör ön ayarının üzerine yazar; Tasarım Ajanı renkleri, yazı
     tiplerini ve bölüm düzenlerini bunun içinde belirler (bkz. [DESIGN.md](DESIGN.md) §4b)
   - Yapay zekâ bağlantısı: Claude Code oturumu ya da API anahtarı
   - Sitenin verisi: yerel SQLite ya da sunucudaki MySQL (bağlantı testi dahil)
3. **Analiz:** Ajanların çalışması canlı izlenir.
4. **Plan raporu:** Site kurulmadan önce ne yapılacağı, mevcut sitenizden nelerin devralındığı, **sizden
   istenecek gerçek bilgiler** (fotoğraf, fiyat, çalışma saatleri…) ve dikkat edilecekler (örnek içerik,
   lisans, harici entegrasyon gerektiren modüller) tek ekranda listelenir. Rapor `.md` olarak indirilebilir;
   onaylayınca görsel seçimine geçilir.
5. **Görseller:** Her görsel grubu (ör. "Şubelerimiz") için:
   - hepsine birden hazır görsel atanabilir,
   - toplu yükleme yapılabilir,
   - grup tek tuşla boşaltılabilir,
   - ya da her görsel ayrı ayrı değiştirilebilir (başka öner / yükle / kaldır).
   Mevcut sitenizden alınan fotoğraflar bu listede **önce** önerilir. Uygulama kapatılsa bile bu adıma geri dönülebilir.
6. **Siteyi oluştur:** Laravel sitesi kurulur ve test edilir. "Siteyi başlat", "Yönetim paneli" ve "Klasörü aç" düğmeleri gelir.

Üretilen siteler `Belgeler\WebAgent\output` klasörüne yazılır. Exe'yi yeniden üretmek için:

```bash
pip install pyinstaller pywebview
python build_exe.py        # → dist/WebAgent.exe
```

Pencere açmadan (test/sunucu) çalıştırmak için `WEBAGENT_HEADLESS=1` ortam değişkenini verin.

## Siteyi sonradan değiştirme (Revizyon Ajanı)

Site hazır olduktan sonra iş sayfasındaki **"✏️ Siteyi düzenle"** kutusuna ne istediğinizi kendi cümlenizle yazarsınız:

> *şubelere açılış saati ekle · ana sayfada yorumları en üste al · rengi daha koyu yap · SSS bölümünü kaldır · kampanyalar diye yeni bölüm aç*

Revizyon Ajanı site tanımını günceller, İnşa Ajanı değişikliği **veriyi silmeden** uygular ve testler yeniden çalışır:

- Yeni tablo/alanlar veritabanına **eklenir** (mevcut kayıtlar olduğu gibi kalır; yönetim panelinden eklediğiniz içerik korunur).
- Kaldırılan bölümler sitede görünmez olur ama **verisi silinmez** (tablo ve sütunlar durur).
- Her revizyondan önce site tanımı ve veritabanı `.revisions/<tarih>` klasörüne yedeklenir.
- Yeni bölüm görsel içeriyorsa görsel seçim ekranı yalnızca **yeni** görseller için tekrar sorar.

## Siteyi kendi sunucunuza yükleme

Site hazır olduğunda iş sayfasındaki **"Siteyi kendi sunucunuza yükleyin"** bölümünden yayına alabilirsiniz:

- **Bağlantı:** FTP, FTPS ya da SFTP (SSH). Sunucu, kullanıcı, şifre, web klasörü (ör. `/public_html`) ve alan adınız.
- **Veri:** "Dosya olarak yükle (SQLite)" ile buradaki içerik olduğu gibi taşınır; ya da sunucudaki **MySQL**
  veritabanı kullanılır (tablolar sunucuda kurulur, içerik oraya yüklenir).
- **Nasıl çalışır:** Proje tek bir ZIP olarak yüklenir (binlerce dosyayı tek tek atmaktan çok daha hızlı),
  sunucuda tek kullanımlık bir kurulum betiği çalışır: paketi açar, uygulama kodunu **web kökünün dışına**
  koyar, yalnızca `public` dosyalarını dışarı açar, `.env`'i yazar, gerekiyorsa veritabanını kurar, izinleri
  ayarlar ve sonra kendini siler. Ardından site, yönetim paneli ve betiğin silindiği otomatik kontrol edilir.
- **Sunucu gereksinimi:** PHP 8.3+ ve `zip` eklentisi. Apache için gereken `.htaccess` pakette gelir
  (Nginx kullanıyorsanız kök dizini `public` klasörüne yönlendirmeniz gerekir).
- Şifreler diske yazılmaz; sunucu adresi gibi alanlar bir sonraki yükleme için hatırlanır.

### Firebase

Firebase doğrudan desteklenmiyor: üretilen yönetim paneli (Filament) Laravel'in ilişkisel veritabanı
katmanına bağlı, Firestore ise farklı bir model. Seçenekler:

- Veriyi MySQL'de tutup Firebase'i yalnızca giriş, bildirim ve dosya depolama için kullanmak,
- Laravel'i Google Cloud Run + Cloud SQL üzerinde barındırmak,
- Ya da Firestore'a göre ayrı bir üretici (ör. Next.js) yazmak — bu, ikinci bir şablon seti ve yönetim paneli demektir.

Üretilen sitede zaten salt okunur bir **JSON API** (`/api/...`) var; mobil uygulama ya da başka bir sistem
veriyi oradan çekebilir.

## Ajan topluluğu

```
Keşif ─▶ [Tarayıcı ▶ Analist] × N rakip (paralel) ─▶ Stratejist ─▶ Mimar ─▶ Tasarım
      ─▶ İçerik × varlık (paralel) ─▶ İnşa (Laravel) ─▶ QA (PHPUnit)
```

| Ajan | LLM | Görev |
|---|---|---|
| Miras | ✓ | Kullanıcının mevcut sitesini tarar: iletişim bilgileri, kurumsal metin, hizmet/ürün listesi ve fotoğraflar devralınır; bulunamayanlar rapora "sizden istenecekler" olarak yazılır |
| Keşif | ✓ (web_search) | Sektördeki rakiplerin resmi sitelerini bulur (verdiğiniz URL'ler önce kullanılır) |
| Tarayıcı | – | Ana sayfa + en ilgili 5 iç sayfayı gezer. robots.txt'e uyar. Menü, footer, form alanları, başlıklar, teknoloji (WordPress, Shopify…) ve özellik sinyallerini (sepet, randevu, arama…) toplar |
| Analist | ✓ | Her site için modülleri **kanıtlarıyla**, içerik türlerini, güçlü ve zayıf yanları çıkarır |
| Stratejist | ✓ | Özellik matrisini (hangi modül kaç rakipte var) kurar, `must / should / differentiator` önceliğiyle modül seti seçer |
| Mimar | ✓ | Modülleri veritabanı varlıklarına, alanlara ve sayfalara çevirir. Çıktı kodla doğrulanıp düzeltilir |
| Tasarım | ✓ | [DESIGN.md](DESIGN.md)'yi okuyup tema seçer: kullanıcının seçtiği görünüm (aydınlık/koyu/renkli/sade), sektör ön ayarı, renkler, font çifti, hero tipi, menü (en fazla 5 link), ana sayfa bölümleri ve düzenleri. Kontrast, font ayrımı, CTA uzunluğu gibi ölçülebilir kurallar kodla da zorlanır |
| İçerik | ✓ | Her varlık için özgün örnek kayıtlar ve görsel anahtar kelimeleri yazar |
| İnşa | – | Laravel + Filament temel projesini kopyalar. Her tablo için migration, Eloquent modeli ve Filament kaynağı üretir. Openverse'ten CC lisanslı görselleri indirir, veritabanını kurup örnek içeriği yükler |
| Rapor | ✓ | Üretimden önce planı yazar: ne kurulacak, mevcut siteden ne geldi, sizden ne istenecek, hangi riskler var |
| QA | – | `php artisan test` ile her sayfayı, her tabloyu, iletişim formunu ve her admin sayfasını (liste, oluştur, düzenle) test eder |

Ajanlar ortak bir **kara tahta** (`data/jobs/<id>.json`) üzerinden haberleşir. Arayüz bu dosyayı canlı izler.

## Kurulum

```bash
pip install -r requirements.txt
python setup_laravel.py     # bir kez: taşınabilir PHP 8.4 + Composer + Laravel/Filament temel projesi (tools/)
python run.py               # http://127.0.0.1:8000
```

`setup_laravel.py` yönetici yetkisi istemez; her şeyi `tools/` klasörüne kurar ve indirilen dosyaları SHA-256 ile doğrular.
Eski Python motoruyla üretmek isterseniz `.env` içine `WEBAGENT_STACK=python` yazın.

### Claude'a bağlanma: iki seçenek

| Arka uç | Gerekli | Nasıl çalışır |
|---|---|---|
| **claude-code** (anahtar yoksa varsayılan) | Claude Code'a giriş yapılmış olması (VS Code eklentisi yeterli) | Ajanlar `claude -p` ile yerel Claude Code oturumunuzu kullanır. Web araması Claude Code'un WebSearch aracıyla yapılır |
| **api** | `.env` içinde `ANTHROPIC_API_KEY` | Claude API doğrudan çağrılır (`anthropic` SDK). Güvenlik reddinde yedek model otomatik devreye girer |

Seçim `.env` içindeki `WEBAGENT_BACKEND` ile yapılır (`auto`, `api`, `claude-code`). `claude` PATH'te yoksa
VS Code eklentisinin içindeki `claude.exe` otomatik bulunur. Bulunamazsa yolunu `CLAUDE_CLI_PATH` ile verin.

Komut satırından da çalışır:

```bash
python cli.py "diş kliniği" --location İstanbul --urls https://rakip1.com https://rakip2.com
```

## Üretilen site (`output/<slug>-<id>/`) — Laravel 13

- **Ziyaretçi sitesi (Blade):** dekoratif zeminler, kart üstü rozet/fiyat balonları, ikonlu bölüm başlıkları,
  kaydırınca beliren animasyonlar ve logo desteğiyle; DESIGN.md'ye göre hero (görselli / bölünmüş / ortalı), güven şeridi, farklı düzenlerde ana sayfa bölümleri (kart, öne çıkan satırlar, liste, galeri, yorumlar, SSS, ekip, rakamlar), liste ve detay sayfaları, arama, iletişim formu, bülten ve `/credits` görsel atıfları. Mobil uyumlu; sayfalar JS olmadan da çalışır
- **Admin paneli (Filament, `/admin`):** Her tablo için form (ilişki seçimi, görsel yükleme, markdown editörü) ve filtreli, aranabilir tablo. Ayrıca gelen mesajlar (okunmamış rozetiyle), bülten aboneleri ve özet panosu. Panel marka renginde ve Türkçe
- **JSON API:** `/api/<varlık>` ve `/api/<varlık>/<id>` (salt okunur, sayfalı, `?q=` arama)
- **Veritabanı:** SQLite (`database/database.sqlite`); MySQL'e geçmek için `.env`'de `DB_CONNECTION` değiştirilmesi yeterli

Kod yapısı:

```
app/Models/*.php                  her tablo için Eloquent modeli (üretilir)
app/Filament/Resources/*          her tablo için admin kaynağı (üretilir)
database/migrations/*             her tablo için migration (üretilir)
app/Http/Controllers/SiteController.php, app/Support/SiteConfig.php, routes/web.php
resources/views/site/*            Blade şablonları        public/css/site.css  tasarım sistemi
site.json                         yapı + tema             seed.json            örnek içerik
tests/Feature/SiteSmokeTest.php   uçtan uca test
```

Çalıştırmak için platformdaki **▶ Siteyi Başlat** düğmesini kullanın ya da sitenin klasöründeki `run.bat`'ı açın
(http://127.0.0.1:8100). Admin e-posta ve şifresi sitenin `.env` dosyasında (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) ve platformun görev sayfasında yazar.

## Testler (API anahtarı gerekmez)

```bash
python tests/test_pipeline_offline.py    # sahte LLM ile tüm ajan hattı + Laravel inşası + QA
python tests/test_ui_flow.py             # arayüz: görsel seçme/yükleme → siteyi oluştur
python tests/test_deploy_local.py        # yayın: yerel FTP + web sunucusu benzetimiyle sunucuya yükleme
python tests/test_revision_offline.py    # revizyon: veri korunuyor mu, yeni alan geliyor mu
python site_engine/tests/smoke_test.py   # örnek site üzerinde motor testi
```

## Klasörler

```
webagent/        platform: ajanlar, orkestratör, Claude istemcisi, arayüz
laravel_stubs/   her Laravel sitesine kopyalanan ortak dosyalar (kontrolcü, Blade, CSS, seeder, test)
DESIGN.md        Tasarım Ajanı'nın ve şablonların uyduğu tasarım rehberi
tools/           taşınabilir PHP, Composer ve Laravel temel projesi (setup_laravel.py kurar)
site_engine/     eski Python motoru (WEBAGENT_STACK=python)
output/          üretilen siteler
data/jobs/       görev durumları (kara tahta)
```

## Notlar

- Model: `claude-opus-5` (`WEBAGENT_MODEL` ile değiştirilebilir). Yapılandırılmış çıktılar Pydantic şemalarıyla doğrulanır. Güvenlik reddi durumunda sunucu taraflı yedek model (`fallbacks: "default"`) devreye girer.
- Ajanlar rakiplerden yalnızca **modül ve yapı** fikri alır. Metin, marka ve görsel kopyalamaz; içerik özgün üretilir. Örnek görseller Openverse'ten gelen Creative Commons lisanslı fotoğraflardır. Atıfları sitenin `/credits` sayfasında listelenir. Yayından önce kendi görsellerinizle değiştirin; bazı fotoğraflarda fotoğrafçı filigranı bulunabilir.
- Ödeme altyapısı (iyzico/Stripe) ve üyelik gibi harici entegrasyon isteyen modüller admin'den yönetilen veri olarak modellenir, gerçek entegrasyon içermez.
