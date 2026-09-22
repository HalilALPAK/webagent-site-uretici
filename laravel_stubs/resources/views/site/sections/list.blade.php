@php
    use App\Support\SiteConfig as S;
    $body = S::bodyField($meta);
    $dateField = collect($meta['fields'])->firstWhere('type', 'date');
    $tag = collect(S::metaFields($meta))->whereIn('type', ['select', 'relation'])->first();
@endphp
<div class="post-list">
    @foreach ($records as $r)
        @php
            $date = $dateField ? S::format($r, $dateField) : $r->created_at?->translatedFormat('j F Y');
            $tagValue = $tag ? S::format($r, $tag) : null;
        @endphp
        <a href="{{ url($meta['name'].'/'.$r->getKey()) }}" @class(['post', 'reveal', 'post-lead' => $loop->first])>
            @if ($loop->first && $meta['image_field'])
                @include('site.partials.media', ['r' => $r, 'meta' => $meta, 'ratio' => 'ratio-16-10'])
            @endif
            <div class="post-body">
                <span class="post-meta">{{ $date }}@if ($tagValue) · {{ $tagValue }}@endif</span>
                <h3>{{ S::title($r, $meta) }}</h3>
                @if ($body && $r->{$body['name']})
                    <p>{{ S::excerpt($r->{$body['name']}, $loop->first ? 220 : 130) }}</p>
                @endif
            </div>
        </a>
    @endforeach
</div>
