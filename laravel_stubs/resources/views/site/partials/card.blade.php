@php
    use App\Support\SiteConfig as S;
    $price = S::priceField($meta);
    $body = S::bodyField($meta);
    $tag = collect(S::metaFields($meta))->whereIn('type', ['select', 'relation'])->first();
    $tagValue = $tag ? S::format($r, $tag) : null;
    $facts = collect(S::metaFields($meta, 3))->filter(fn ($f) => $f !== $tag && $f['type'] !== 'price');
@endphp
<a href="{{ url($meta['name'].'/'.$r->getKey()) }}" @class(['card', 'reveal', 'card-text-only' => ! $meta['image_field']])>
    @if ($meta['image_field'])
        <div class="card-media">
            @include('site.partials.media', ['r' => $r, 'meta' => $meta])
            {{-- görselin üstünde etiket ve fiyat: kart daha canlı ve okunur olur --}}
            @if ($tagValue)<span class="badge badge-float">{{ $tagValue }}</span>@endif
            @if ($price && ($pv = S::format($r, $price)))<span class="price-float">{{ $pv }}</span>@endif
            <span class="card-shine" aria-hidden="true"></span>
        </div>
    @endif
    <div class="card-body">
        @if ($tagValue && ! $meta['image_field'])
            <span class="badge">{{ $tagValue }}</span>
        @endif
        <h3 class="card-title">{{ S::title($r, $meta) }}</h3>
        @if ($body && $r->{$body['name']})
            <p class="card-text">{{ S::excerpt($r->{$body['name']}, 110) }}</p>
        @endif
        @if ($facts->isNotEmpty())
            <ul class="card-facts">
                @foreach ($facts as $f)
                    @if ($v = S::format($r, $f))
                        <li><span>{{ $f['label'] }}</span>{{ $v }}</li>
                    @endif
                @endforeach
            </ul>
        @endif
        <div class="card-foot">
            @if ($price && ($pv = S::format($r, $price)) && ! $meta['image_field'])
                <span class="price">{{ $pv }}</span>
            @endif
            <span class="card-more">İncele <span aria-hidden="true">→</span></span>
        </div>
    </div>
</a>
