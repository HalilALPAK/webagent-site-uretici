@php
    use App\Support\SiteConfig as S;
    $body = S::bodyField($meta);
    $rating = collect($meta['fields'])->first(fn ($f) => in_array($f['type'], ['int', 'float']) && preg_match('/rating|puan|score|yildiz|star/i', $f['name']));
    $sub = collect(S::metaFields($meta))->first(fn ($f) => ! in_array($f['type'], ['int', 'float', 'price', 'bool']) && $f !== $rating);
@endphp
<div class="grid grid-3 quotes">
    @foreach ($records as $r)
        <figure class="quote reveal">
            <span class="quote-mark" aria-hidden="true">”</span>
            @if ($rating && ($score = (float) $r->{$rating['name']}))
                @php $stars = (int) round($score > 5 ? $score / 2 : $score); @endphp
                <div class="stars" aria-label="{{ $stars }} / 5">{{ str_repeat('★', $stars) }}<span>{{ str_repeat('★', max(0, 5 - $stars)) }}</span></div>
            @endif
            <blockquote>“{{ S::excerpt($body ? $r->{$body['name']} : '', 280) }}”</blockquote>
            <figcaption>
                <span class="avatar" aria-hidden="true">{{ S::initial(S::title($r, $meta)) }}</span>
                <span><strong>{{ S::title($r, $meta) }}</strong>
                    @if ($sub && ($sv = S::format($r, $sub)))<small>{{ $sv }}</small>@endif
                </span>
            </figcaption>
        </figure>
    @endforeach
</div>
