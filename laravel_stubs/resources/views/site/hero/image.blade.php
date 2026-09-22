@php use App\Support\SiteConfig as S; $t = S::all()['theme']; $img = S::url($t['hero_image'] ?? null); @endphp
<section class="hero hero-image">
    @if ($img)
        <img class="hero-bg" src="{{ $img }}" alt="" fetchpriority="high">
    @endif
    <div class="hero-shade" aria-hidden="true"></div>
    <div class="container hero-content">
        <span class="eyebrow eyebrow-light">{{ $t['hero_eyebrow'] }}</span>
        <h1>{{ S::get('hero.headline') }}</h1>
        <p class="lead">{{ S::get('hero.subheadline') }}</p>
        <div class="hero-actions">
            <a href="{{ $t['primary_cta_link'] }}" class="btn btn-accent btn-lg">{{ $t['primary_cta_text'] }}</a>
            <a href="{{ route('contact') }}" class="btn btn-ghost-light btn-lg">Bize ulaşın</a>
        </div>
    </div>
</section>
