<?php

namespace App\Providers;

use Illuminate\Support\Facades\Date;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        // Yayında public klasörü web kökündedir (kod web kökünün dışındadır)
        if ($path = env('PUBLIC_PATH')) {
            $this->app->usePublicPath($path);
        }

        // Yüklenen dosyalar doğrudan public/uploads altına yazılır (Windows'ta symlink gerekmez).
        // register aşamasında ayarlanır: paneller ve diskler boot'tan önce çözülebiliyor.
        config([
            'filesystems.disks.public.root' => public_path('uploads'),
            'filesystems.disks.public.url' => '/uploads',
        ]);
    }

    public function boot(): void
    {
        Date::setLocale(config('app.locale'));
    }
}
