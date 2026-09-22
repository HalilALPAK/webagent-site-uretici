<?php

namespace App\Support;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\HtmlString;
use Illuminate\Support\Str;

/**
 * site.json'u (Web Agent'ın ürettiği site tanımı) okuyan yardımcı.
 * Tüm şablonlar ve kontrolcüler site yapısını buradan öğrenir.
 */
class SiteConfig
{
    protected static ?array $site = null;

    public static function all(): array
    {
        return static::$site ??= json_decode(file_get_contents(base_path('site.json')), true);
    }

    public static function get(string $key, mixed $default = null): mixed
    {
        return data_get(static::all(), $key, $default);
    }

    public static function theme(string $key, mixed $default = null): mixed
    {
        return data_get(static::all(), "theme.$key", $default);
    }

    /** @return array<int, array> */
    public static function entities(): array
    {
        return static::all()['entities'];
    }

    public static function entity(string $name): ?array
    {
        return collect(static::entities())->firstWhere('name', $name);
    }

    public static function publicEntity(string $name): ?array
    {
        $entity = static::entity($name);

        return ($entity && $entity['public']) ? $entity : null;
    }

    /** @return class-string<Model> */
    public static function modelClass(array $entity): string
    {
        return 'App\\Models\\'.$entity['model'];
    }

    public static function query(array $entity): Builder
    {
        $class = static::modelClass($entity);
        // Haber/blog gibi listeler en yeni önce; diğerleri eklenme sırasıyla (şubeler, ürünler, ekip…)
        $query = static::display($entity['name']) === 'list' ? $class::query()->latest('id') : $class::query()->oldest('id');
        $relations = collect($entity['fields'])->where('type', 'relation')->pluck('method')->all();

        return $relations ? $query->with($relations) : $query;
    }

    public static function display(string $entity): string
    {
        $row = collect(static::theme('entity_displays', []))->firstWhere('entity', $entity);

        return $row['display'] ?? 'cards';
    }

    /** Menü: en fazla 4 varlık + kalan yere menüde gösterilecek sayfalar (toplam en fazla 5). */
    public static function nav(): array
    {
        $items = [];
        $labels = collect(static::theme('nav_labels', []))->pluck('label', 'entity');
        foreach (static::theme('nav_entities', []) as $name) {
            if ($e = static::publicEntity($name)) {
                $items[] = ['label' => $labels[$name] ?? $e['label_plural'], 'url' => url('/'.$e['name']), 'active' => request()->is($e['name'].'*')];
            }
        }
        foreach (static::get('pages', []) as $page) {
            if (count($items) >= 5) {
                break;
            }
            if ($page['in_nav']) {
                $items[] = ['label' => $page['title'], 'url' => url('/p/'.$page['slug']), 'active' => request()->is('p/'.$page['slug'])];
            }
        }

        return $items;
    }

    public static function column(array $field): string
    {
        return $field['column'] ?? $field['name'];
    }

    public static function title(Model $record, array $entity): string
    {
        return (string) ($record->{$entity['title_field']} ?? '#'.$record->getKey());
    }

    /** Görsel yokken gösterilecek baş harf; "Dr.", "Uzm." gibi unvanları atlar. */
    public static function initial(string $text): string
    {
        foreach (preg_split('/\s+/u', trim($text)) as $word) {
            if ($word !== '' && ! str_ends_with($word, '.')) {
                return mb_strtoupper(mb_substr($word, 0, 1));
            }
        }

        return mb_substr($text, 0, 1);
    }

    public static function image(?Model $record, array $entity): ?string
    {
        if (! $record || ! ($field = $entity['image_field'] ?? null)) {
            return null;
        }

        return static::url($record->{$field});
    }

    public static function url(?string $path): ?string
    {
        if (! $path) {
            return null;
        }

        // Yüklenen dosyalar her zaman public/uploads altında durur ve /uploads adresinden sunulur.
        // (Disk örneği panel tanımı sırasında erken çözülebildiği için Storage::url'e bağlanmıyoruz.)
        return Str::startsWith($path, ['http://', 'https://', '/']) ? $path : '/uploads/'.ltrim($path, '/');
    }

    /** Uzun metin alanı (özet/açıklama/cevap için ilk text/richtext alanı). */
    public static function bodyField(array $entity): ?array
    {
        return collect($entity['fields'])->first(fn ($f) => in_array($f['type'], ['text', 'richtext']));
    }

    /** Kart altında gösterilecek kısa bilgiler. */
    public static function metaFields(array $entity, int $limit = 3): array
    {
        return collect($entity['fields'])
            ->filter(fn ($f) => $f['show_in_list'] && $f['name'] !== $entity['title_field']
                && ! in_array($f['type'], ['image', 'text', 'richtext']))
            ->take($limit)->values()->all();
    }

    public static function priceField(array $entity): ?array
    {
        return collect($entity['fields'])->firstWhere('type', 'price');
    }

    public static function format(Model $record, array $field): ?string
    {
        $value = $record->{static::column($field)};
        if ($value === null || $value === '') {
            return null;
        }

        return match ($field['type']) {
            'price' => number_format((float) $value, 0, ',', '.').' '.static::currency(),
            'float' => rtrim(rtrim(number_format((float) $value, 2, ',', '.'), '0'), ','),
            'bool' => $value ? 'Evet' : 'Hayır',
            'date' => $value instanceof \DateTimeInterface ? $value->translatedFormat('j F Y') : (string) $value,
            'relation' => ($related = $record->{$field['method']})
                ? (string) $related->{static::entity($field['relation'])['title_field'] ?? 'id'}
                : null,
            default => (string) $value,
        };
    }

    public static function currency(): string
    {
        return static::get('currency') ?: (str_starts_with(static::get('language', 'tr'), 'tr') ? '₺' : '$');
    }

    public static function md(?string $text): HtmlString
    {
        return new HtmlString(Str::markdown($text ?? '', ['html_input' => 'strip', 'allow_unsafe_links' => false]));
    }

    public static function excerpt(?string $text, int $limit = 140): string
    {
        return Str::limit(trim(preg_replace('/\s+/', ' ', strip_tags(Str::markdown($text ?? '')))), $limit);
    }

    /** Modül anahtarına göre küçük çizgi ikon adı (resources/views/components/site-icon.blade.php). */
    public static function icon(string $moduleKey): string
    {
        $map = [
            'rooms' => 'home', 'locations_map' => 'pin', 'booking_appointment' => 'calendar',
            'gallery' => 'photo', 'blog_news' => 'news', 'faq' => 'question',
            'testimonials_reviews' => 'chat', 'team' => 'users', 'pricing_plans' => 'tag',
            'product_catalog' => 'bag', 'shopping_cart' => 'bag', 'events' => 'ticket',
            'services' => 'sparkles', 'campaigns_discounts' => 'star', 'jobs_careers' => 'briefcase',
            'downloads_documents' => 'doc', 'press' => 'news', 'awards' => 'star',
        ];

        return $map[$moduleKey] ?? 'spark';
    }

    /** Yüklenen logo (varsa) — başlıkta, footer'da ve yönetim panelinde kullanılır. */
    public static function logo(): ?string
    {
        return static::url(static::get('branding.logo'));
    }

    /** Tarayıcı önbelleğini kıran sürüm damgası (dosya bulunamazsa site yine açılır). */
    public static function assetVersion(string $file): string
    {
        $path = public_path($file);

        return (string) (is_file($path) ? filemtime($path) : 1);
    }

    public static function fontsUrl(): string
    {
        $families = collect([static::theme('font_heading', 'Inter'), static::theme('font_body', 'Inter')])
            ->unique()
            ->map(fn ($f) => 'family='.str_replace(' ', '+', $f).':wght@400;500;600;700')
            ->implode('&');

        return "https://fonts.googleapis.com/css2?$families&display=swap";
    }
}
