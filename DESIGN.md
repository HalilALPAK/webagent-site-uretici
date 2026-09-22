# Tasarım Rehberi — Üretilen Siteler

Bu dosyanın iki okuru var:

1. **Tasarım Ajanı:** Her sitede bu rehberi okur ve `site.json` içindeki `theme` bölümünü doldurur.
2. **Laravel şablonları** (`laravel_stubs/`): Buradaki kuralları uygular.

Rehberi değiştirirseniz sonraki üretimler buna göre şekillenir. Şablonların uyguladığı kurallarda (token'lar,
bileşenler) bir değişiklik yaparsanız şablonlara da yansıtın.

---

## 1. Önceki sitelerde neden kötü göründü

İlk sürümlerin somut hatalarını tekrarlamamak için:

| Sorun | Neden kötü | Kural |
|---|---|---|
| Menüde 13 link | Göz nereye bakacağını bilemiyor, mobilde taşıyor | Ana menüde **en fazla 5 link + 1 CTA butonu**. Gerisi footer'a |
| Ana sayfada 7 bölüm, hepsi aynı kart ızgarası | Monoton; hiçbir bölüm öne çıkmıyor | Ana sayfa **en fazla 5 içerik bölümü**. Her bölüm farklı bir düzen kullanır (§5) |
| Rastgele stok fotoğraflar (picsum, loremflickr) | Otel sitesinde kedi heykeli ya da kırmızı boşluklu görsel çıkıyor; güveni öldürür | Görseller **anahtar kelimeyle** seçilir (§7). Görsel yoksa tipografik kart kullanılır |
| Başlık fontu gövdede de kullanıldı (Cormorant) | Dekoratif serif, küçük boyutta okunmuyor | **Başlık ve gövde fontu ayrı**. Gövde her zaman okunaklı bir sans-serif |
| Hero'da görsel yok, modül adları "chip" olarak dizildi | İç yapıyı pazarlama metni gibi gösteriyor, amatör duruyor | Hero'da güçlü görsel ya da net tipografi olur. Modül/teknik adlar kullanıcıya gösterilmez |
| Bir sürü uzun CTA ("Odaları İncele ve Rezervasyon Yap") | Buton metni cümle gibi | CTA metni **en fazla 3 kelime**, fiille başlar |
| Her şey aynı ağırlıkta | Hiyerarşi yok | Sayfa başına **tek bir birincil aksiyon**. Diğer butonlar ikincil stilde |

---

## 2. İlkeler

1. **Önce hiyerarşi, sonra süs.** Her ekranda ziyaretçi 3 saniyede şunları anlamalı: ne sunuluyor, neden bu marka, ne yapmalı.
2. **Az renk, çok boşluk.** Nötr zemin (%60), marka rengi (%30, başlıklar/yüzeyler), vurgu rengi (%10, yalnızca CTA ve önemli detaylar).
3. **Sektörün diliyle konuş.** Otel sitesi dergi gibi, klinik sitesi sakin ve güven veren, SaaS sitesi keskin ve net görünmeli (§4).
4. **Tutarlılık.** Aynı türde öğe her yerde aynı görünür: aynı radius, aynı gölge, aynı buton.
5. **Mobil önce.** Tasarım 375 px'te kurulur, geniş ekranlarda nefes alır.

---

## 3. Tasarım token'ları

Şablonlar bu token'ları CSS değişkenleri olarak kullanır. Tasarım Ajanı yalnızca `theme` içindeki değerleri seçer.

### Renk
| Token | Kullanım | Kural |
|---|---|---|
| `primary` | Başlıklar, koyu yüzeyler (footer, CTA bandı), linkler | Beyaz metinle kontrast ≥ 4.5:1 (koyu ton seçin) |
| `accent` | Birincil buton, fiyat, küçük vurgular | `primary`'den belirgin farklı ton ailesi. Asla gövde metni rengi değil |
| `surface` | Sayfa zemini | Saf beyaz yerine hafif sıcak/soğuk kırık beyaz (ör. `#faf8f5`, `#f8fafc`) |
| `ink` | Gövde metni | Saf siyah değil (ör. `#1c1917`, `#0f172a`) |
| `muted` | İkincil metin | `ink`'in %60 tonu civarı, zeminde kontrast ≥ 4.5:1 |

Kurallar:
- Zemin ve metin renkleri hex olarak verilir ve WCAG AA kontrastını sağlar.
- Neon/doygun renkler (ör. `#00ff00`) yalnızca teknoloji/oyun sektöründe ve sadece vurgu olarak kullanılır.
- Gradient en fazla iki durak ve aynı ton ailesinden olur. Gökkuşağı gradient yasak.

### Tipografi
- **İki font:** `font_heading` (karakter) + `font_body` (okunaklılık). İkisi de Google Fonts'ta olmalı ve Türkçe karakterleri (ğ, ş, ı, İ) desteklemeli.
- Gövde: 16–18 px, satır yüksekliği 1.6–1.7, satır uzunluğu en fazla 70 karakter.
- Ölçek (yaklaşık 1.25 oran): `h1` 44–64 px (mobilde 34–40), `h2` 32–40, `h3` 20–24, küçük metin 14.
- Başlıklarda `letter-spacing: -0.02em`. Büyük harf "eyebrow" etiketlerde `+0.12em`.

Önerilen eşleşmeler (hepsi Türkçe destekli):

| Karakter | Başlık | Gövde |
|---|---|---|
| Zarif / lüks | Playfair Display, Cormorant Garamond, DM Serif Display | Inter, Manrope, Nunito Sans |
| Sıcak / samimi | Fraunces, Lora | Source Sans 3, Nunito Sans |
| Modern / kurumsal | Plus Jakarta Sans, Manrope, Outfit | Inter, Plus Jakarta Sans |
| Güçlü / enerjik | Bebas Neue (yalnız başlık), Archivo Black, Sora | Inter, Archivo |
| Teknik / SaaS | Space Grotesk, Sora | Inter, IBM Plex Sans |

### Boşluk, radius ve gölge
- Boşluk ölçeği 4'ün katları: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128.
- Bölümler arası dikey boşluk masaüstünde 96–128 px, mobilde 64 px.
- `radius`: `none` (0), `soft` (8 px), `round` (16 px), `pill` (butonlar tam yuvarlak). Sektöre göre seçilir, sitenin her yerinde aynı kalır.
- Gölge: sadece hover ve yüzen öğeler için, yumuşak (`0 10px 30px -12px rgba(0,0,0,.18)`). Kalın siyah gölge yasak.

---

## 4. Sektör ön ayarları (`theme.preset`)

Tasarım Ajanı en yakın ön ayarı seçer, sonra marka ve rakiplere göre renkleri ince ayarlar.

| Preset | Uygun sektörler | Palet (primary / accent / surface) | Fontlar | Radius | Hero | Görsel üslubu |
|---|---|---|---|---|---|---|
| `luxury` | Butik otel, fine dining, mücevher, gelinlik | `#1f2a2e` / `#b08d57` / `#faf7f2` | Playfair Display + Inter | none | `image` | Sıcak ışık, dar alan derinliği, insanlar ikinci planda |
| `wellness` | Klinik, diş, spa, psikolog, fizyoterapi | `#134e4a` / `#f59e0b` / `#f7faf9` | Fraunces + Nunito Sans | round | `split` | Aydınlık, doğal ışık, gülümseyen insanlar, beyaz/yeşil |
| `corporate` | Hukuk, danışmanlık, finans, sigorta, B2B | `#0f2742` / `#c2410c` / `#f8fafc` | Plus Jakarta Sans + Inter | soft | `split` | Mimari, ofis, portre; soğuk tonlar |
| `bold` | Spor salonu, otomotiv, etkinlik, inşaat | `#111111` / `#ef4444` / `#ffffff` | Archivo Black + Inter | none | `image` | Yüksek kontrast, hareket, yakın plan |
| `tech` | SaaS, ajans, yazılım, startup | `#0b1020` / `#6366f1` / `#ffffff` | Space Grotesk + Inter | round | `centered` | Ürün ekranları, soyut şekiller; stok fotoğraf az |
| `warm` | Kafe, restoran, pastane, çiçekçi, el yapımı | `#3f2a1e` / `#d97706` / `#fbf6ef` | Fraunces + Source Sans 3 | round | `image` | Yemek/ürün yakın plan, doğal doku |
| `fresh` | E-ticaret, moda, kozmetik, eğitim, çocuk | `#1e1b4b` / `#ec4899` / `#ffffff` | Outfit + Inter | pill | `split` | Temiz arka plan, ürün odaklı, canlı ama kontrollü |
| `nature` | Emlak, tarım, turizm, kamp, organik | `#1c3d2e` / `#ca8a04` / `#f6f7f2` | Lora + Manrope | soft | `image` | Geniş açı manzara, gün ışığı |

---

## 4b. Kullanıcının seçtiği görünüm (`theme.mode` + `style`)

Sihirbazda kullanıcı bir **görünüm** seçer; bu, sektör ön ayarının üzerine yazar. Tasarım Ajanı buna uymak zorundadır.

| Stil | `mode` | Kural |
|---|---|---|
| `auto` | ajan seçer | Sektör ön ayarı neyse o. Kullanıcı tercih belirtmemiştir |
| `light` | `light` | Aydınlık kırık beyaz zemin, koyu metin. Renk ölçülü: yalnızca CTA ve küçük vurgular |
| `dark` | `dark` | Koyu zemin (`surface` L≈0.12), açık metin. **`primary` açık bir marka tonudur** (koyu zeminde başlık ve link rengi olarak okunur), `accent` canlı kalır |
| `colorful` | `light` | Canlı, doygun `accent`; `primary` de renkli (gri/lacivert değil). Rozetler, fiyatlar ve CTA belirgin |
| `minimal` | `light` | Neredeyse renksiz: `primary` koyu nötr, `accent` tek bir sakin ton. Bol boşluk, ince çizgiler, `radius: none` ya da `soft` |

Koyu modda kontrast kuralları ters çalışır:
- `surface` koyu, `ink` açık; `ink`/`surface` kontrastı ≥ 7.
- `primary` **koyu zeminde** okunmalı: `primary`/`surface` kontrastı ≥ 4.5. (Aydınlık modda kural `primary` ile beyaz metin arasındadır.)
- Beyaz zemin varsayan hiçbir renk kodlanmaz; şablonlar `--paper`, `--alt`, `--line` değişkenlerini kullanır ve
  bu değişkenler koyu modda `body.mode-dark` altında yeniden tanımlanır.

## 5. Sayfa anatomisi

### Menü
- Logo (marka adı, başlık fontunda) solda.
- Ortada ya da sağda en fazla 5 link: en önemli 3–4 içerik türü + "Hakkımızda". Menü etiketleri tek satırda kalır (en fazla 2–3 kelime); 1100 px altında menü hamburger'e döner.
- Sağda tek birincil CTA butonu (ör. "Rezervasyon", "Randevu Al", "Teklif Al").
- Hero `image` ise menü şeffaf başlar, kaydırınca opak olur.

### Hero (`theme.hero_variant`)
- `image`: Tam genişlik görsel, altta koyu gradient örtü (`linear-gradient(to top, rgba(0,0,0,.65), transparent 60%)`), metin sol altta, beyaz. Otel, restoran ve yaşam tarzı sektörleri için.
- `split`: Solda metin, sağda büyük görsel (4:5 ya da kare), zemin `surface`. Hizmet sektörleri için.
- `centered`: Ortalanmış büyük başlık, altında iki buton ve güven göstergeleri. Görsel opsiyonel. Teknoloji için.

Her hero'da şunlar bulunur:
- Eyebrow: kısa etiket, ör. "Galata · İstanbul".
- Başlık: 4–9 kelime; fayda ya da duygu anlatır, sektör adını tekrarlamaz.
- Alt metin: en fazla 2 cümle.
- 1 birincil ve en fazla 1 ikincil buton.

### Güven şeridi (hero'nun hemen altı)
3–4 kısa kanıt: "4.9 ★ misafir puanı", "2010'dan beri", "Ücretsiz iptal". `theme.trust_items` ile verilir. Uydurma istatistik yazılmaz: örnek değerler yayından önce müşteriyle doğrulanacak şekilde yer tutucu olarak işaretlenir.

### İçerik bölümleri (`entity.display`)
Ana sayfaya en fazla 5 varlık çıkar (`show_on_home`). Art arda iki bölüm aynı `display`'i kullanmaz; zemin rengi `surface` ile beyaz arasında değişir.

| display | Ne zaman | Görünüm |
|---|---|---|
| `cards` | Ürün, oda, hizmet, paket | 3 sütun kart. Görsel 4:3, başlık, 1 satır özet, fiyat/etiket |
| `feature` | 2–4 öne çıkan öğe (ör. süitler, ana hizmetler) | Görsel ve metnin sırayla yer değiştirdiği büyük satırlar |
| `list` | Blog, haber, basın, etkinlik | Tarih + başlık + özet satırları, ince ayraçlar; ilk öğe büyük |
| `gallery` | Galeri, portfolyo, projeler | Masonry benzeri ızgara, hover'da başlık |
| `testimonials` | Yorumlar, referanslar | Büyük tırnak işareti, alıntı, isim; 3'lü ızgara |
| `faq` | SSS | Açılır-kapanır `<details>` listesi, iki sütun (solda başlık/açıklama) |
| `team` | Ekip, doktorlar, avukatlar | Yuvarlak ya da 4:5 portre, isim, unvan |
| `stats` | Rakamlar, başarılar | Büyük rakamlar, kısa açıklama; koyu zemin |

### CTA bandı
`primary` zeminli tam genişlik bant: bir cümlelik davet ve bir buton. Sayfada en fazla bir kez, footer'dan hemen önce.

### Footer
Koyu (`primary`) zemin. 4 sütun: marka + kısa açıklama, keşfet linkleri, kurumsal sayfalar, iletişim. Menüye sığmayan tüm linkler buraya konur.

---

## 5b. Görsel zenginlik (şablonların uyguladığı)

Site "düz" görünmesin diye şablonlarda sabit olarak şunlar var; tasarım ajanının ek bir şey yapmasına gerek yok:

- **Dekoratif zeminler:** hero'da marka renginden yumuşak ışık lekeleri, `centered` hero'da ince ızgara deseni,
  CTA bandında noktalı desen. `minimal` ve `corporate` ön ayarlarında kısılır.
- **Bölüm geçişleri:** açık/koyu bölümler arasında hafif eğimli kesim.
- **Kartlar:** görselin üstünde kategori rozeti ve fiyat balonu, altında koyulaşan gradient, hover'da ışık
  geçişi, yükselme ve kısa bilgi satırları (metrekare, süre, kategori gibi).
- **Başlıklar:** ikonlu "eyebrow" etiketi, başlık metninin arkasında vurgu renginde fosforlu şerit.
- **Öne çıkan satırlar:** numara rozeti ve görselin arkasında kayık çerçeve.
- **Hareket:** bölümler kaydırdıkça beliriyor; `prefers-reduced-motion` açıksa tüm hareket kapanır.
- **Logo:** kullanıcı logo yüklediyse başlıkta, footer'da, favicon'da ve yönetim panelinde kullanılır.
  Yüklemediyse marka adının baş harfinden gradientli bir işaret üretilir.

## 6. Bileşenler

- **Buton:** Birincil = `accent` zemin + beyaz metin (kontrastı düşükse koyu metin); ikincil = şeffaf zemin + 1.5 px kenarlık. Yükseklik 44–52 px, yatay iç boşluk 24 px, font 600.
- **Kart:** Kenarlık `1px solid rgba(0,0,0,.06)` ya da gölgesiz düz zemin. Hover'da `translateY(-4px)` ve yumuşak gölge; görsel hafif (1.04) büyür.
- **Etiket/rozet:** Küçük harf, 12–13 px, `accent`'in %12 opak zemini üzerine `accent`'in koyu tonu.
- **Fiyat:** Rakam büyük ve kalın, para birimi ve "başlayan fiyat" gibi ek küçük ve `muted`.
- **Form:** Etiket her zaman görünür (placeholder etiket yerine geçmez). Alan yüksekliği 48 px, odak halkası `accent`, hata metni alanın altında kırmızı.
- **İkon:** Tek set (satır içi SVG, çizgi kalınlığı 1.5). Emoji kullanılmaz.

---

## 7. Görseller

- İçerik Ajanı her kayıt için görseli tarif eden **İngilizce 2–3 anahtar kelime** üretir (`image_keywords`, ör. `boutique hotel room`, `dental clinic interior`).
- İnşa ajanı bu anahtar kelimelerle **Openverse**'te (ticari kullanıma açık Creative Commons lisanslı fotoğraflar) arama yapar. Görseller indirilip 1400–2000 px'e küçültülür, her kayda farklı bir görsel atanır.
- CC BY lisansı atıf ister. Atıflar sitede `/credits` ("Görsel kaynakları") sayfasında otomatik listelenir. Bu sayfa kaldırılmamalıdır.
- Rastgele görsel servisleri (picsum, loremflickr) kullanılmaz; konu dışı fotoğraf, hiç fotoğraf olmamasından kötüdür.
- Görsel yüklenemezse `primary`→`accent` gradient zemin üzerine başlığın baş harfi gösterilir (tipografik kart).
- En-boy oranları: kart 4:3, hero `image` 16:9 (mobilde 4:5), `split` hero 4:5, ekip 4:5, galeri serbest.
- Hero görselinin üzerindeki metin her zaman gradient örtüyle okunur kılınır.
- **Yayından önce tüm yer tutucu görseller gerçek görsellerle değiştirilmelidir.** Admin panelinde her görsel alanı yükleme destekler.

---

## 8. Metin (mikro kopya)

- Başlıklar fayda anlatır. Kötü: "Hizmetlerimiz". İyi: "Her gülüş için doğru tedavi".
- Bölüm başlıklarının üstünde kısa eyebrow etiketi, altında en fazla 1 cümle açıklama olur.
- CTA fiille başlar ve en fazla 3 kelimedir: "Rezervasyon yap", "Randevu al", "Menüyü gör".
- "Lorem ipsum", "Test", "Örnek içerik" gibi metinler yasak. Örnek içerik gerçekçi ama uydurma olduğu açık olmayan kişisel veri içermez.
- Rakip metinleri, marka adları ve sloganları kopyalanmaz.

---

## 9. Erişilebilirlik ve performans

- Kontrast AA. Odak halkaları görünür. Tüm görsellerde `alt` bulunur. Yalnızca renkle bilgi verilmez.
- Görseller `loading="lazy"` ve boyut belirtilerek yüklenir. Fontlar `display=swap` ile ve en fazla 2 aile/4 ağırlık.
- JavaScript yalnızca gerektiğinde (mobil menü, sticky header). Sayfa JS olmadan da kullanılabilir.
- `prefers-reduced-motion` açıksa animasyonlar kapanır.

---

## 10. Admin paneli (Filament)

- Panel rengi markanın `primary` rengini, panel başlığı marka adını kullanır.
- Kaynaklar (resource) gruplanır: **İçerik** (public varlıklar), **Operasyon** (rezervasyon, randevu gibi public olmayanlar), **Etkileşim** (mesajlar, aboneler).
- Liste tablolarında görsel sütunu küçük küçük resim (thumbnail) olarak gösterilir. `select` alanları renkli rozet olur; arama ve filtreler açıktır.

---

## 11. Tasarım Ajanı kontrol listesi

`theme` çıktısını vermeden önce:
- [ ] Preset sektöre uygun mu? Renkler rakiplerden ayırt edilebilir mi?
- [ ] `primary` beyaz metinle ve `ink` `surface` üzerinde AA kontrast sağlıyor mu?
- [ ] Başlık ve gövde fontu farklı mı? Gövde fontu sans-serif mi?
- [ ] Menüde en fazla 5 link var mı? `nav_entities` seçildi mi?
- [ ] Ana sayfada en fazla 5 bölüm var mı? Art arda aynı `display` yok mu?
- [ ] Hero başlığı 4–9 kelime, CTA'lar en fazla 3 kelime mi?
- [ ] Güven şeridi öğeleri kısa mı ve uydurma kesin iddia içermiyor mu?
