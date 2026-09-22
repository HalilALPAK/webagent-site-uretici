@php use App\Support\SiteConfig as S; $role = collect(S::metaFields($meta))->first(fn ($f) => in_array($f['type'], ['string', 'select'])); @endphp
<div class="grid grid-4 team">
    @foreach ($records as $r)
        <a href="{{ url($meta['name'].'/'.$r->getKey()) }}" class="person reveal">
            @include('site.partials.media', ['r' => $r, 'meta' => $meta, 'ratio' => 'ratio-4-5'])
            <strong>{{ S::title($r, $meta) }}</strong>
            @if ($role && ($rv = S::format($r, $role)))<span>{{ $rv }}</span>@endif
        </a>
    @endforeach
</div>
