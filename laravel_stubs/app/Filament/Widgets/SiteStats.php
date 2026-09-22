<?php

namespace App\Filament\Widgets;

use App\Models\Message;
use App\Models\Subscriber;
use App\Support\SiteConfig;
use Filament\Support\Icons\Heroicon;
use Filament\Widgets\StatsOverviewWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class SiteStats extends StatsOverviewWidget
{
    protected static ?int $sort = 1;

    protected int|string|array $columnSpan = 'full';

    protected function getStats(): array
    {
        $stats = [
            Stat::make('Okunmamış mesaj', Message::where('is_read', false)->count())
                ->description('Toplam '.Message::count().' mesaj')
                ->icon(Heroicon::OutlinedEnvelope)
                ->color('primary'),
            Stat::make('Bülten abonesi', Subscriber::count())
                ->icon(Heroicon::OutlinedUserGroup),
        ];

        foreach (array_slice(SiteConfig::entities(), 0, 6) as $entity) {
            $class = SiteConfig::modelClass($entity);
            $stats[] = Stat::make($entity['label_plural'], $class::count())
                ->description($entity['public'] ? 'Sitede yayında' : 'Sadece yönetimde');
        }

        return $stats;
    }
}
