@php use App\Support\SiteConfig as S; $t = S::all()['theme']; @endphp
<section class="hero hero-centered">
    <div class="hero-glow" aria-hidden="true"></div>
    <span class="decor-grid" aria-hidden="true"></span>
    <div class="container narrow hero-content">
        <span class="eyebrow">{{ $t['hero_eyebrow'] }}</span>
        <h1>{{ S::get('hero.headline') }}</h1>
        <p class="lead">{{ S::get('hero.subheadline') }}</p>
        <div class="hero-actions">
            <a href="{{ $t['primary_cta_link'] }}" class="btn btn-accent btn-lg">{{ $t['primary_cta_text'] }}</a>
            <a href="{{ route('contact') }}" class="btn btn-secondary btn-lg">Bize ulaşın</a>
        </div>
    </div>
</section>
