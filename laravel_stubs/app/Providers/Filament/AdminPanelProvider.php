<?php

namespace App\Providers\Filament;

use App\Filament\Widgets\SiteStats;
use App\Support\SiteConfig;
use Filament\Http\Middleware\Authenticate;
use Filament\Http\Middleware\AuthenticateSession;
use Filament\Http\Middleware\DisableBladeIconComponents;
use Filament\Http\Middleware\DispatchServingFilamentEvent;
use Filament\Navigation\NavigationItem;
use Filament\Pages\Dashboard;
use Filament\Panel;
use Filament\PanelProvider;
use Filament\Support\Colors\Color;
use Filament\Support\Icons\Heroicon;
use Filament\Widgets\AccountWidget;
use Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse;
use Illuminate\Cookie\Middleware\EncryptCookies;
use Illuminate\Foundation\Http\Middleware\PreventRequestForgery;
use Illuminate\Routing\Middleware\SubstituteBindings;
use Illuminate\Session\Middleware\StartSession;
use Illuminate\View\Middleware\ShareErrorsFromSession;

class AdminPanelProvider extends PanelProvider
{
    public function panel(Panel $panel): Panel
    {
        return $panel
            ->default()
            ->id('admin')
            ->path('admin')
            ->login()
            ->brandName(SiteConfig::get('site_name'))
            ->brandLogo(SiteConfig::logo())
            ->brandLogoHeight('2.1rem')
            ->favicon(SiteConfig::logo())
            ->colors([
                'primary' => self::brandPalette(SiteConfig::theme('primary', '#1f2937')),
                'gray' => Color::Stone,
            ])
            ->font(SiteConfig::theme('font_body', 'Inter'))
            ->navigationGroups(['İçerik', 'Operasyon', 'Etkileşim'])
            ->navigationItems([
                NavigationItem::make('Siteyi görüntüle')
                    ->url('/', shouldOpenInNewTab: true)
                    ->icon(Heroicon::OutlinedArrowTopRightOnSquare)
                    ->sort(100),
            ])
            ->sidebarCollapsibleOnDesktop()
            ->discoverResources(in: app_path('Filament/Resources'), for: 'App\Filament\Resources')
            ->discoverPages(in: app_path('Filament/Pages'), for: 'App\Filament\Pages')
            ->pages([
                Dashboard::class,
            ])
            ->widgets([
                AccountWidget::class,
                SiteStats::class,
            ])
            ->middleware([
                EncryptCookies::class,
                AddQueuedCookiesToResponse::class,
                StartSession::class,
                AuthenticateSession::class,
                ShareErrorsFromSession::class,
                PreventRequestForgery::class,
                SubstituteBindings::class,
                DisableBladeIconComponents::class,
                DispatchServingFilamentEvent::class,
            ])
            ->authMiddleware([
                Authenticate::class,
            ]);
    }

    /**
     * Filament'in paleti yalnızca rengin tonunu (hue) alıp doygunluğu sabit yüksek tutar; koyu/ağır
     * marka renkleri bu yüzden parlak çıkar. Burada markanın kendi doygunluğu korunur.
     */
    private static function brandPalette(string $hex): array
    {
        [, $chroma, $hue] = sscanf(Color::convertToOklch($hex), 'oklch(%f %f %f)');
        $steps = [50 => 0.97, 100 => 0.94, 200 => 0.88, 300 => 0.76, 400 => 0.56, 500 => 0.48,
            600 => 0.42, 700 => 0.37, 800 => 0.32, 900 => 0.27, 950 => 0.2];
        $palette = [];
        foreach ($steps as $shade => $lightness) {
            // açık tonlarda doygunluğu azalt, koyu tonlarda markanınkini koru
            $c = round(min($chroma, 0.16) * ($shade <= 200 ? 0.35 : ($shade <= 400 ? 0.75 : 1)), 4);
            $palette[$shade] = "oklch($lightness $c $hue)";
        }

        return $palette;
    }
}
