@php use App\Support\SiteConfig as S; $t = S::all()['theme']; $img = S::url($t['hero_image'] ?? null); @endphp
<section class="hero hero-split">
    <span class="decor-blob decor-blob-1" aria-hidden="true"></span>
    <span class="decor-blob decor-blob-2" aria-hidden="true"></span>
    <div class="container hero-split-inner">
        <div class="hero-copy">
            <span class="eyebrow">{{ $t['hero_eyebrow'] }}</span>
            <h1>{{ S::get('hero.headline') }}</h1>
            <p class="lead">{{ S::get('hero.subheadline') }}</p>
            <div class="hero-actions reveal">
                <a href="{{ $t['primary_cta_link'] }}" class="btn btn-accent btn-lg">{{ $t['primary_cta_text'] }}</a>
                <a href="{{ route('contact') }}" class="btn btn-secondary btn-lg">Bize ulaşın</a>
            </div>
        </div>
        <div class="hero-visual">
            <div class="hero-visual-accent" aria-hidden="true"></div>
            @if ($img)
                <img src="{{ $img }}" alt="{{ S::get('site_name') }}" fetchpriority="high">
            @else
                <div class="media-fallback"><span>{{ mb_substr(S::get('site_name'), 0, 1) }}</span></div>
            @endif
        </div>
    </div>
</section>
