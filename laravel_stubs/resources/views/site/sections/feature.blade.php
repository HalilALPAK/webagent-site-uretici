@php use App\Support\SiteConfig as S; $body = S::bodyField($meta); $price = S::priceField($meta); @endphp
<div class="feature-list">
    @foreach ($records as $r)
        <article class="feature-row reveal">
            @if ($meta['image_field'])
                <a href="{{ url($meta['name'].'/'.$r->getKey()) }}" class="feature-media" tabindex="-1" aria-hidden="true">
                    <span class="feature-frame" aria-hidden="true"></span>
                    @include('site.partials.media', ['r' => $r, 'meta' => $meta, 'ratio' => 'ratio-5-4'])
                </a>
            @endif
            <div class="feature-body">
                <span class="feature-index">{{ str_pad($loop->iteration, 2, '0', STR_PAD_LEFT) }}</span>
                <h3><a href="{{ url($meta['name'].'/'.$r->getKey()) }}">{{ S::title($r, $meta) }}</a></h3>
                @if ($body && $r->{$body['name']})
                    <p>{{ S::excerpt($r->{$body['name']}, 260) }}</p>
                @endif
                <ul class="facts-inline">
                    @foreach (S::metaFields($meta, 4) as $f)
                        @if ($f['type'] !== 'price' && ($v = S::format($r, $f)))
                            <li><span>{{ $f['label'] }}</span>{{ $v }}</li>
                        @endif
                    @endforeach
                </ul>
                <div class="feature-actions">
                    @if ($price && ($pv = S::format($r, $price)))
                        <span class="price price-lg">{{ $pv }}</span>
                    @endif
                    <a href="{{ url($meta['name'].'/'.$r->getKey()) }}" class="btn btn-secondary">Detayları gör</a>
                </div>
            </div>
        </article>
    @endforeach
</div>
