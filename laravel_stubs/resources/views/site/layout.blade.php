@php
    use App\Support\SiteConfig as S;
    $t = S::all()['theme'];
    $overlay = request()->routeIs('home') && $t['hero_variant'] === 'image';
@endphp
<!doctype html>
<html lang="{{ S::get('language', 'tr') }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', S::get('site_name').' — '.S::get('tagline'))</title>
    <meta name="description" content="@yield('description', S::get('meta_description'))">
    <meta property="og:title" content="@yield('title', S::get('site_name'))">
    <meta property="og:description" content="@yield('description', S::get('meta_description'))">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="{{ S::fontsUrl() }}">
    <link rel="stylesheet" href="{{ asset('css/site.css') }}?v={{ S::assetVersion('css/site.css') }}">
    @if (S::logo())<link rel="icon" href="{{ S::logo() }}">@endif
    <style>
        :root {
            --primary: {{ $t['primary'] }};
            --accent: {{ $t['accent'] }};
            --surface: {{ $t['surface'] }};
            --ink: {{ $t['ink'] }};
            --font-heading: '{{ $t['font_heading'] }}', Georgia, serif;
            --font-body: '{{ $t['font_body'] }}', system-ui, -apple-system, sans-serif;
        }
    </style>
</head>
<body class="radius-{{ $t['radius'] }} preset-{{ $t['preset'] }} mode-{{ $t['mode'] ?? 'light' }} {{ $overlay ? 'has-overlay-header' : '' }}">
<a class="skip-link" href="#main">İçeriğe geç</a>

<header class="site-header" data-header>
    <div class="container header-inner">
        <a href="{{ url('/') }}" class="logo">
            @if (S::logo())
                <img src="{{ S::logo() }}" alt="{{ S::get('site_name') }}" class="logo-img">
            @else
                <span class="logo-mark" aria-hidden="true">{{ S::initial(S::get('site_name')) }}</span>
            @endif
            <span class="logo-text">{{ S::get('site_name') }}</span>
        </a>

        <nav class="main-nav" id="main-nav" aria-label="Ana menü">
            @foreach (S::nav() as $item)
                <a href="{{ $item['url'] }}" @class(['active' => $item['active']])>{{ $item['label'] }}</a>
            @endforeach
            <a href="{{ route('contact') }}" class="nav-mobile-only">İletişim</a>
        </nav>

        <div class="header-actions">
            @if (S::get('search'))
                <a href="{{ route('search') }}" class="icon-btn" aria-label="Sitede ara">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
                </a>
            @endif
            <a href="{{ $t['primary_cta_link'] }}" class="btn btn-primary btn-sm header-cta">{{ $t['primary_cta_text'] }}</a>
            <button class="menu-toggle" type="button" aria-controls="main-nav" aria-expanded="false" aria-label="Menüyü aç" data-menu-toggle>
                <span></span><span></span>
            </button>
        </div>
    </div>
</header>

<main id="main">
    @yield('content')
</main>

@include('site.partials.footer')

<script src="{{ asset('js/site.js') }}" defer></script>
</body>
</html>
