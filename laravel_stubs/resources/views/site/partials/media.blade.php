{{-- beklenen: $r, $meta; opsiyonel: $ratio (css sınıfı) --}}
@php use App\Support\SiteConfig as S; $img = S::image($r, $meta); $title = S::title($r, $meta); @endphp
<div class="media {{ $ratio ?? 'ratio-4-3' }}">
    @if ($img)
        <img src="{{ $img }}" alt="{{ $title }}" loading="lazy" width="800" height="600">
    @else
        <div class="media-fallback"><span>{{ S::initial($title) }}</span></div>
    @endif
</div>
