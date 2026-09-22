# Web Agent

**Sektörünüzü yazın, rakipleriniz analiz edilsin, size özel bir web siteniz olsun.**

Web Agent bir masaüstü uygulamasıdır. İşletmenizin adını ve sektörünü girersiniz; yapay zekâ ajanları
rakip siteleri bulup inceler, hangi bölümlerin gerektiğine karar verir, içerikleri yazar ve size
**yönetim paneli olan, veritabanına bağlı, çalışır durumda bir web sitesi** üretir.

---

## İndirme

| | |
|---|---|
| **İndir** | **[⬇ WebAgent.exe](https://github.com/HalilALPAK/webagent-site-uretici/releases/latest/download/WebAgent.exe)** |
| Sürüm | 1.0 · 21.09.2026 |
| Boyut | 38 MB (tek dosya, kurulum gerektirmez) |
| Sistem | Windows 10 / 11, 64-bit |
| SHA-256 | `dd66e61f4f49a4f9f70fa65ec0d95c33d33664526662aa6c296cbc7931f0913c` |

Tüm sürümler ve değişiklik notları: [github.com/HalilALPAK/webagent-site-uretici/releases](https://github.com/HalilALPAK/webagent-site-uretici/releases)

> **İndirdiğiniz dosyayı doğrulamak için** PowerShell'de:
> `Get-FileHash .\WebAgent.exe -Algorithm SHA256`
> Çıkan değer yukarıdaki SHA-256 ile aynı olmalıdır.

---

## İlk çalıştırma

1. `WebAgent.exe` dosyasına çift tıklayın.
2. Windows **"Bilgisayarınız korundu"** uyarısı gösterebilir (uygulama dijital imzalı olmadığı için normaldir):
   **Ek bilgi → Yine de çalıştır**.
3. Uygulama kendi penceresinde açılır.
4. **İlk açılışta bir kurulum ekranı** gelir: siteleri üretmek için gereken PHP, Composer ve Laravel
   bileşenleri indirilir (yaklaşık 150 MB, internet hızınıza göre 2-5 dakika). Yönetici yetkisi istenmez,
   her şey `Belgeler\WebAgent\tools` klasörüne kurulur. Bu yalnızca bir kez olur.

---

## Nasıl kullanılır

### 1. Bilgileri girin
Kısa bir sihirbaz sizden şunları ister:

- **İşletme adı ve sektör** (zorunlu) — ör. "Mavikıyı Diş Kliniği", "diş kliniği"
- **Şehir**, bildiğiniz rakip siteler, özel istekleriniz
- **Mevcut siteniz** (varsa) — adresini yazarsanız iletişim bilgileriniz, hizmet listeniz ve
  **fotoğraflarınız** oradan alınır
- **Logonuz** (isteğe bağlı) — yüklemezseniz adınızın baş harfinden şık bir logo üretilir
- **Görünüm** — küçük site maketleri arasından seçersiniz: *aydınlık, koyu, canlı, çok sade* ya da
  *"ajan karar versin"*
- **Yapay zekâ bağlantısı** — bilgisayarınızdaki Claude Code oturumu ya da Claude API anahtarı
- **Verinin yeri** — bu bilgisayarda (SQLite) ya da sunucunuzdaki MySQL

### 2. Ajanlar çalışır (5-10 dakika)
Rakipleriniz bulunur, siteleri gezilir, hangi modüllerin kaç rakipte olduğu çıkarılır, size uygun
bölümler seçilir, tasarım belirlenir ve içerikler yazılır. Ekranda hangi ajanın ne yaptığını canlı
izlersiniz.

### 3. Planı okursunuz
Site kurulmadan önce bir **plan raporu** gelir: ne yapılacak, mevcut sitenizden ne alındı,
**sizden hangi gerçek bilgiler istenecek** (fotoğraf, fiyat, çalışma saatleri) ve nelere dikkat
edilmeli. Raporu dosya olarak indirebilirsiniz. Onaylayınca devam eder.

### 4. Görselleri seçersiniz
Her görsel grubu için (ör. "Şubelerimiz", "Hekimlerimiz") üç seçeneğiniz var:

- **Hepsine hazır görsel** — tek tuşla gruptaki tüm görseller doldurulur
- **Toplu yükle** — kendi fotoğraflarınız sırayla yerleşir
- Her görseli tek tek değiştirin: **↻ Başka** (yeni öneri), **⬆ Yükle**, **✕** (boş bırak)

Mevcut sitenizden alınan fotoğraflar listede önce önerilir.

### 5. Siteniz kurulur ve test edilir
"Siteyi oluştur" dediğinizde site kurulur, veritabanı hazırlanır ve **otomatik testlerden geçirilir**.
Sonra şu düğmeler gelir: **Siteyi başlat**, **Yönetim paneli**, **Klasörü aç**.

---

## Ürettiği site

- **Ziyaretçi sitesi** — büyük giriş görseli, ürün/hizmet kartları, galeri, müşteri yorumları, SSS,
  ekip, blog, arama, iletişim formu ve bülten. Telefonda da düzgün görünür.
- **Yönetim paneli** (`/admin`) — Türkçe. İçerik ekleme/düzenleme, görsel yükleme, gelen mesajlar,
  bülten aboneleri ve özet panosu. Giriş bilgileri iş sayfasında yazar.
- **Veritabanı** — SQLite ya da sunucunuzdaki MySQL.
- **JSON API** (`/api/...`) — mobil uygulama veya başka bir sistem veriyi buradan çekebilir.
- Teknoloji: **PHP / Laravel 13 + Filament**. Standart bir Laravel projesi olduğu için herhangi bir
  yazılımcı devralıp geliştirebilir.

---

## Site hazır olduktan sonra

**Siteyi düzenleyin:** İş sayfasındaki "✏️ Siteyi düzenle" kutusuna kendi cümlenizle yazarsınız:
*"şubelere açılış saati ekle"*, *"ana sayfada yorumları en üste al"*, *"rengi daha koyu yap"*.
Değişiklik uygulanırken **veriniz silinmez**; her değişiklikten önce yedek alınır.

**Sunucunuza yükleyin:** "🌐 Siteyi kendi sunucunuza yükleyin" bölümüne FTP/FTPS/SFTP bilgilerinizi
ve alan adınızı girersiniz. Site paketlenip sunucunuza yüklenir, orada kurulur ve açılıp açılmadığı
kontrol edilir. Sunucunuzda **PHP 8.3+** ve **zip** eklentisi gerekir.

---

## Dosyalarınız nerede?

Her şey **`Belgeler\WebAgent`** klasöründe:

```
Belgeler\WebAgent\
├── output\        üretilen siteler (her site kendi klasöründe)
├── data\jobs\     iş geçmişi ve seçimleriniz
├── tools\         PHP, Composer, Laravel bileşenleri
└── webagent.log   sorun olursa buraya bakın
```

Uygulamayı silmek için: `WebAgent.exe` dosyasını ve bu klasörü silmeniz yeterlidir. Kayıt defterine
(registry) hiçbir şey yazılmaz.

---

## Sık karşılaşılanlar

**Pencere açılmıyor.** `Belgeler\WebAgent\webagent.log` dosyasının son satırlarına bakın. Windows'un
WebView2 bileşeni eksikse uygulama siteyi varsayılan tarayıcınızda açar.

**Kurulum yarıda kaldı.** İnterneti kontrol edip "Tekrar dene" düğmesine basın; indirilen dosyalar
imzalarıyla doğrulandığı için yarım kalan kurulum baştan alınır.

**"Claude Code bulunamadı" yazıyor.** Ya bu bilgisayara Claude Code kurup giriş yapın ya da
sihirbazın yapay zekâ adımında bir Claude API anahtarı girin.

**Site açılmıyor / boş geliyor.** Site klasöründeki `run.bat` dosyasını çalıştırıp hata mesajını
okuyun. Bir sitenin kendi testlerini `php artisan test` ile de çalıştırabilirsiniz.

---

## Bilmeniz gerekenler

- **İçerik örnektir.** Ajanların yazdığı ürün açıklamaları, fiyatlar ve müşteri yorumları
  **gerçek değildir**. Yayına almadan önce yönetim panelinden kendi bilgilerinizle değiştirin.
  Uydurma yorum ve istatistikleri yayında bırakmak yanıltıcı reklam sayılabilir.
- **Hazır görseller lisanslıdır.** Openverse'ten gelen fotoğraflar ticari kullanıma açık Creative
  Commons lisanslıdır ve atıfları sitenizdeki "Görsel kaynakları" sayfasında listelenir. Bu sayfayı
  kaldırmayın ya da fotoğrafları kendi fotoğraflarınızla değiştirin.
- **Harici entegrasyonlar yok.** Ödeme altyapısı (iyzico/Stripe), Google Haritalar ve WhatsApp gibi
  servisler için ayrıca anlaşma ve kurulum gerekir; site bunları hazır içermez.
- **İnternet gerekir.** Analiz, içerik ve görsel önerileri internet üzerinden çalışır.
- **Kullanım hakkı.** Claude Code seçeneğinde her site üretimi aboneliğinizin kullanım hakkından
  düşer; API anahtarı seçeneğinde kullandığınız kadar ücretlendirilirsiniz.

---

## Geliştiriciler için

Kaynak kod, ajanların nasıl çalıştığı, tasarım rehberi ve testler için projenin ana klasöründeki
[README.md](https://github.com/HalilALPAK/webagent-site-uretici/blob/master/README.md) ve [DESIGN.md](https://github.com/HalilALPAK/webagent-site-uretici/blob/master/DESIGN.md) dosyalarına bakın.
Exe'yi yeniden üretmek: `python build_exe.py`
