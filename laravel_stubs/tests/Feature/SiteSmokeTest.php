<?php

namespace Tests\Feature;

use App\Models\Message;
use App\Models\Subscriber;
use App\Models\User;
use App\Support\SiteConfig;
use Illuminate\Foundation\Testing\RefreshDatabase;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

/**
 * Web Agent QA ajanının çalıştırdığı uçtan uca test.
 * site.json'daki her sayfa, varlık ve admin kaynağı ayrı bir test vakası olarak raporlanır.
 */
class SiteSmokeTest extends TestCase
{
    use RefreshDatabase;

    protected bool $seed = true;

    private static function site(): array
    {
        return json_decode(file_get_contents(__DIR__.'/../../site.json'), true);
    }

    public static function publicPaths(): array
    {
        $site = self::site();
        $paths = ['ana sayfa' => ['/'], 'iletişim' => ['/contact'], 'arama' => ['/search?q=a'], 'görsel kaynakları' => ['/credits']];
        foreach ($site['pages'] as $p) {
            $paths['sayfa '.$p['slug']] = ['/p/'.$p['slug']];
        }
        foreach ($site['entities'] as $e) {
            if ($e['public']) {
                $paths['liste '.$e['name']] = ['/'.$e['name']];
                $paths['api '.$e['name']] = ['/api/'.$e['name']];
            }
        }

        return $paths;
    }

    public static function entities(): array
    {
        $out = [];
        foreach (self::site()['entities'] as $e) {
            $out[$e['name']] = [$e['name']];
        }

        return $out;
    }

    public static function adminSlugs(): array
    {
        $out = ['mesajlar' => ['messages'], 'aboneler' => ['subscribers']];
        foreach (self::site()['entities'] as $e) {
            $out[$e['name']] = [$e['slug']];
        }

        return $out;
    }

    #[DataProvider('publicPaths')]
    public function test_public_page_opens(string $path): void
    {
        $this->get($path)->assertOk();
    }

    #[DataProvider('entities')]
    public function test_entity_detail_opens(string $name): void
    {
        $meta = SiteConfig::entity($name);
        $record = SiteConfig::modelClass($meta)::query()->first();
        if (! $record) { // içerik üretilemediyse tablo boş olabilir; boş liste sayfası yine açılmalı
            $meta['public'] ? $this->get("/$name")->assertOk() : $this->get("/$name")->assertNotFound();

            return;
        }
        if ($meta['public']) {
            $this->get("/$name/{$record->getKey()}")->assertOk()->assertSee(e(SiteConfig::title($record, $meta)), false);
        } else {
            $this->get("/$name")->assertNotFound();
        }
    }

    public function test_unknown_page_is_404(): void
    {
        $this->get('/olmayan-sayfa-xyz')->assertNotFound();
    }

    public function test_contact_form_saves_message(): void
    {
        $this->post('/contact', ['name' => 'Deneme', 'email' => 'a@b.com', 'body' => 'Merhaba, bu bir test.'])
            ->assertRedirect('/contact');
        $this->assertSame(1, Message::count());
        $this->post('/contact', ['name' => '', 'email' => 'x', 'body' => ''])->assertSessionHasErrors(['name', 'email', 'body']);
    }

    public function test_newsletter_subscribes(): void
    {
        $this->post('/newsletter', ['email' => 'abone@example.com'])->assertRedirect();
        $this->assertSame(1, Subscriber::count());
    }

    public function test_admin_requires_login(): void
    {
        $this->get('/admin')->assertRedirect('/admin/login');
        $this->get('/admin/login')->assertOk();
    }

    #[DataProvider('adminSlugs')]
    public function test_admin_resource_pages_open(string $slug): void
    {
        $this->actingAs(User::first());
        $this->get('/admin')->assertOk();
        $this->get("/admin/$slug")->assertOk();
        $this->get("/admin/$slug/create")->assertOk();

        $meta = collect(self::site()['entities'])->firstWhere('slug', $slug);
        $class = $meta ? SiteConfig::modelClass($meta) : ($slug === 'messages' ? Message::class : Subscriber::class);
        if ($record = $class::query()->first()) {
            $this->get("/admin/$slug/{$record->getKey()}/edit")->assertOk();
        }
    }
}
