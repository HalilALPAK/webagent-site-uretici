{{-- beklenen: $section (eyebrow, title, subtitle), $meta --}}
@php use App\Support\SiteConfig as S; @endphp
<div class="section-head reveal">
    <div>
        @if (! empty($section['eyebrow']))
            <span class="eyebrow eyebrow-line">
                <x-site-icon :name="S::icon($meta['module_key'] ?? '')" />
                {{ $section['eyebrow'] }}
            </span>
        @endif
        <h2 class="deco-title">{{ $section['title'] ?? $meta['label_plural'] }}</h2>
        @if (! empty($section['subtitle']))
            <p class="section-sub">{{ $section['subtitle'] }}</p>
        @endif
    </div>
    <a href="{{ url('/'.$meta['name']) }}" class="link-arrow">Tümünü gör <span aria-hidden="true">→</span></a>
</div>
